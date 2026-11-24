"""Tests for Stage 3, the question path. No test calls the API: every model reply is a saved file in
tests/replies/ or is written here. Logs go to a temporary folder, never the shared log.

Run:  python -m unittest discover -s tests -v
"""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from latest import latest_only  # the tests' own expected figures use the latest year only
from path import answer, interpret, request as rq, shortlist, show
from path.log import Log

DB = config.LOCAL_DB.as_posix()
REPLIES = Path(__file__).with_name("replies")


def req(op, **parts):
    r = rq.empty(op)
    r.update(parts)
    return r


def M(i, row=()):
    return dict(id=i, row=[dict(column=c, code=v) for c, v in row])


def S(name, i):
    return dict(name=name, id=i)


def reply_request(r):
    return dict(kind="request", request=r, edit=None, options=[], chosen=[], decline=None)


def reply_edit(changes, values):
    return dict(kind="edit", request=None, options=[], chosen=[], decline=None,
                edit=dict(changes=[dict(field=f, action=a) for f, a in changes], values=values))


def saved(call_reply):
    """A stand-in for the API call that returns a fixed reply."""
    return lambda system, user, model, schema=None: (json.dumps(call_reply), {"input_tokens": 1000, "output_tokens": 100})


class Request(unittest.TestCase):
    def test_period_patterns_fill_from_the_release_year(self):
        self.assertEqual(rq.fill_years("July 1, {Y-1} - June 30, {Y}", 2024), "July 1, 2023 - June 30, 2024")
        self.assertEqual(rq.fill_years("Academic year {Y}-{Y+1:yy}", 2015), "Academic year 2015-16")
        self.assertEqual(rq.fill_years("{Y-1}-{Y:yy}", 2000), "1999-00")
        self.assertEqual(rq.fill_years("Fall 2024", 2015), "Fall 2024")            # no pattern words: unchanged
        self.assertIsNone(rq.fill_years(None, 2024))

    def setUp(self):
        self.base = req("schools", measures=[M("DRVGR.GBA6RTT")], schools=[S("RIT", 195003), S("WPI", 168421)])

    def test_add_remove_replace(self):
        added = rq.apply_edit(self.base, dict(changes=[dict(field="schools", action="add")],
                                              values=req("schools", schools=[S("Drexel", 212054), S("RIT", 195003)])), [])
        self.assertEqual([s["id"] for s in added["schools"]], [195003, 168421, 212054])      # no duplicate RIT
        removed = rq.apply_edit(added, dict(changes=[dict(field="schools", action="remove")],
                                            values=req("schools", schools=[S("WPI", 168421)])), [])
        self.assertEqual([s["id"] for s in removed["schools"]], [195003, 212054])
        swapped = rq.apply_edit(self.base, dict(changes=[dict(field="measures", action="replace")],
                                                values=req("schools", measures=[M("DRVADM.DVADM01")])), [])
        self.assertEqual(swapped["measures"], [M("DRVADM.DVADM01")])
        self.assertEqual(swapped["schools"], self.base["schools"])                            # everything else kept

    def test_any_field_can_change(self):
        edit = dict(changes=[dict(field="operation", action="replace"), dict(field="groups", action="replace"),
                             dict(field="sort", action="replace")],
                    values=req("rank", groups=["State: Texas"], sort=dict(order="lowest", limit=5)))
        new = rq.apply_edit(self.base, edit, [])
        self.assertEqual((new["operation"], new["groups"], new["sort"]["order"]), ("rank", ["State: Texas"], "lowest"))
        cleared = rq.apply_edit(new, dict(changes=[dict(field="sort", action="remove")], values=None), [])
        self.assertIsNone(cleared["sort"])

    def test_back_restores_the_request_before(self):
        later = req("schools", measures=[M("DRVADM.DVADM01")])
        self.assertEqual(rq.apply_edit(later, dict(changes=[dict(field="schools", action="back")], values=None),
                                       [self.base, later]), self.base)

    TAGS = {"M1": ("measures", "DRVADM.DVADM01"), "M2": ("measures", "EFA.EFTOTLT"), "S1": ("schools", 130794),
            "G1": ("groups", "State: Ohio"), "R1": ("rows", ("EFA", "EFALEVEL", "2")), "B1": ("sets", ("By gender", "EFA")),
            "T1": ("readings", ("ranking guard", "Include all schools")), "O1": ("outside", "Loan default rates")}

    def test_schema_stays_within_the_api_limit(self):
        """The API allows at most 16 fields that can be empty (union-typed); the tag ranges are fixed."""
        text = json.dumps(rq.REPLY_SCHEMA)
        self.assertLessEqual(text.count('"anyOf"'), 16)
        self.assertNotIn('"none"', text.lower())
        self.assertIn('"M64"', text)
        self.assertNotIn('"M65"', text)

    def test_tag_not_on_the_shortlist_is_reported(self):
        wire = dict(label="", operation="schools", measures=[dict(measure="M40", row=[])], schools=[], groups=[], peers_of=None,
                    conditions=[], breakdown=None, split_by=None, sort=None, year=dict(stated=None, kind=None), topic=None,
                    outside=None, readings=[])
        reply = rq.from_wire(dict(kind="request", requests=[wire], changes=[], chosen=[], decline=None), self.TAGS)
        self.assertEqual(reply["unknown_tags"], ["M40"])

    def test_tags_map_back_to_ids(self):
        wire = dict(label="", operation="breakdown", measures=[dict(measure="M2", row=["R1"])], schools=[dict(name="Yale", school="S1"),
                    dict(name="Somewhere", school=None)], groups=["G1"], peers_of=None, conditions=[], breakdown=dict(set="B1", fixed=[]),
                    split_by=None, sort=None, year=dict(stated=None, kind=None), topic=None, outside=None, readings=["T1"])
        r = rq.request_from_wire(wire, self.TAGS)
        self.assertEqual(r["measures"], [M("EFA.EFTOTLT", [("EFALEVEL", "2")])])
        self.assertEqual([s["id"] for s in r["schools"]], [130794, None])
        self.assertEqual((r["groups"], r["breakdown"]["set"], r["readings"]),
                         (["State: Ohio"], "By gender", [dict(term="ranking guard", reading="Include all schools")]))
        self.assertEqual(rq.request_from_wire(dict(wire, outside="O1", measures=[]), self.TAGS)["topic"], "Loan default rates")
        back = rq.to_wire(r, self.TAGS)
        self.assertEqual((back["measures"][0]["measure"], back["schools"][0]["school"], back["groups"]), ("M2", "S1", ["G1"]))
        reply = rq.from_wire(dict(kind="options", requests=[dict(wire, label="A"), dict(wire, label="B")], changes=[],
                                  chosen=[], decline=None), self.TAGS)
        self.assertEqual([o["label"] for o in reply["options"]], ["A", "B"])
        reply = rq.from_wire(dict(kind="edit", requests=[wire], changes=[dict(field="schools", action="add")], chosen=[],
                                  decline=None), self.TAGS)
        self.assertEqual(reply["edit"]["values"], r)

    def test_request_shape_appears_once_in_the_reply_shape(self):
        self.assertEqual(json.dumps(rq.REPLY_SCHEMA).count('"peers_of": {'), 1)

    def test_schema_is_strict_everywhere(self):
        def walk(node):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    self.assertFalse(node["additionalProperties"])
                    self.assertEqual(sorted(node["required"]), sorted(node["properties"]))
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
        walk(rq.REPLY_SCHEMA)


@unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built")
class Shortlist(unittest.TestCase):
    def test_finds_schools_groups_and_measures(self):
        s = shortlist.shortlist("Which public four-year colleges in Texas have the highest retention rate?", DB)
        self.assertIn("State: Texas", [g["name"] for g in s["groups"]])
        self.assertIn("Public, 4-year or above", [g["name"] for g in s["groups"]])
        self.assertIn("EFD.RET_PCF", [m["id"] for m in s["measures"]])
        s = shortlist.shortlist("Compare RIT, WPI and FRCC", DB)
        self.assertLessEqual({195003, 168421, 127200}, {x["id"] for x in s["schools"]})        # by IPEDS alias

    def test_measures_set_up_come_first(self):
        s = shortlist.shortlist("What was Yale's admission rate?", DB)
        flags = [m["set_up"] for m in s["measures"] if not m.get("retired")]
        self.assertLessEqual(flags.count(False), shortlist.NOT_SET_UP)
        self.assertLessEqual(sum(bool(m.get("retired")) for m in s["measures"]), shortlist.RETIRED)
        self.assertIn("DRVADM.DVADM01", [m["id"] for m in s["measures"]])

    def test_a_matched_term_brings_its_measures(self):
        s = shortlist.shortlist("How many faculty does Yale have?", DB)
        self.assertIn("EAP.EAPTOT", [m["id"] for m in s["measures"]])
        faculty = next(t for t in s["terms"] if t["term"] == "faculty")
        self.assertEqual(faculty["always_ask"], "yes")

    def test_previous_request_is_carried(self):
        earlier = req("schools", measures=[M("DRVGR.GBA6RTT")], schools=[S("RIT", 195003)], groups=["State: Ohio"],
                      readings=[dict(term="graduation rate", reading="Bachelor's degree within six years")])
        s = shortlist.shortlist("add Northeastern", DB, [earlier])
        ids = shortlist.ids(s)
        self.assertLessEqual(rq.used_ids(earlier)["measure"], ids["measure"])
        self.assertIn(195003, ids["school"])
        self.assertIn("State: Ohio", ids["group"])
        self.assertIn(("graduation rate", "Bachelor's degree within six years"), ids["reading"])


@unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built")
class Interpret(unittest.TestCase):
    def setUp(self):
        self.short = shortlist.shortlist("What was Yale's admission rate?", DB)
        self.good = reply_request(req("schools", measures=[M("DRVADM.DVADM01")], schools=[S("Yale", 130794)]))

    def test_one_retry_then_a_plain_failure(self):
        replies = iter(["not json", json.dumps(self.good)])
        reply, meta = interpret.interpret("q", self.short, call=lambda s, u, m, x=None: (next(replies), {"input_tokens": 10, "output_tokens": 5}))
        self.assertEqual((reply, meta["attempts"], meta["error"]), (self.good, 2, None))
        reply, meta = interpret.interpret("q", self.short, call=lambda s, u, m, x=None: ("{}", {"input_tokens": 10, "output_tokens": 5}))
        self.assertIsNone(reply)
        self.assertEqual(meta["attempts"], 2)
        self.assertIn("KeyError", meta["error"])

    def test_reply_missing_its_part_is_retried(self):
        broken = dict(self.good, request=None)
        reply, meta = interpret.interpret("q", self.short, call=saved(broken))
        self.assertIsNone(reply)
        self.assertIn("without its request", meta["error"])

    def test_prompt_shows_the_shortlist_only(self):
        seen = {}
        def call(system, user, model, schema=None):
            seen["text"] = system + user
            seen["schema"] = schema
            return json.dumps(self.good), {"input_tokens": 1000, "output_tokens": 100}
        _, meta = interpret.interpret("What was Yale's admission rate?", self.short, call=call, model="claude-haiku-5-5")
        self.assertIn("Percent admitted, total", seen["text"])
        self.assertNotIn("DRVADM.DVADM01", seen["text"])                   # tags, not IDs
        self.assertEqual(seen["schema"], rq.REPLY_SCHEMA)                  # the same shape for every question
        self.assertLess(meta["prompt_words"], 2500)
        self.assertAlmostEqual(meta["cost_usd"], (1000 * 0.10 + 100 * 0.50) / 1e6)


@unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built")
class Path_(unittest.TestCase):
    """The whole path, from saved replies to the page, checked against figures computed here from the data."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.log = Log(cls.dir.name)
        cls.db = latest_only(sqlite3.connect(f"file:{DB}?mode=ro", uri=True))

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.dir.cleanup()

    def v(self, sql, *args):
        return self.db.execute(sql, args).fetchone()[0]

    def ask(self, question, reply, state=None):
        state = {} if state is None else state
        return answer.ask(question, state, self.log, call=saved(reply)), state

    def saved_case(self, name, state=None):
        case = json.loads((REPLIES / f"{name}.json").read_text(encoding="utf-8"))
        return self.ask(case["question"], case["reply"], state)

    def column(self, page, name):
        i = page["table"]["columns"].index(name)
        return [r[i] for r in page["table"]["rows"]]

    # ---- the nine questions of the design note
    def test_a_lookup(self):
        page, _ = self.saved_case("a_yale_admission")
        self.assertEqual(page["table"]["rows"], [["Yale University", f"{self.v('SELECT DVADM01 FROM DRVADM WHERE UNITID=130794')}%"]])
        self.assertIn("Fall 2024", page["interpreted"])
        self.assertIn("provisional", page["warnings"][0])

    def test_b_compare_and_i_add_a_school(self):
        page, state = self.saved_case("b_compare_grad")
        expected = [f"{self.v('SELECT GBA6RTT FROM DRVGR WHERE UNITID=?', u)}%" for u in (195003, 168421, 212054)]
        self.assertEqual([r[1] for r in page["table"]["rows"]], expected)
        page, _ = self.saved_case("i_add_northeastern", state)
        self.assertEqual([r[0] for r in page["table"]["rows"]][-1], "Northeastern University")
        self.assertEqual(len(page["table"]["rows"]), 4)

    def test_c_rank_with_the_guard(self):
        page, _ = self.saved_case("c_rank_retention")
        self.assertEqual(page["table"]["rows"][0][1], "The University of Texas at Austin")
        self.assertEqual(len(page["table"]["rows"]), 10)
        self.assertTrue(all(int(r[4].replace(",", "")) >= 30 for r in page["table"]["rows"]))
        self.assertIn("fewer than 30 in the denominator", page["notes"][0])
        self.assertIn("top 10", page["interpreted"])

    def test_d_breakdown_stored_as_columns(self):
        page, _ = self.saved_case("d_yale_race")
        rows = {r[0]: int(r[1].replace(",", "")) for r in page["table"]["rows"]}
        self.assertEqual(rows.pop("Total"), 6814)
        self.assertEqual(sum(rows.values()), 6814)
        self.assertEqual(len(rows), 9)

    def test_e_group_rate_from_counts(self):
        page, _ = self.saved_case("e_group_grad")
        members = ("(SELECT unitid FROM group_membership WHERE group_name='Public, 2-year' AND unitid IN "
                   "(SELECT unitid FROM group_membership WHERE group_name='National universe'))")
        num = self.v(f"SELECT SUM(a.GRTOTLT) FROM GR a JOIN GR b USING (UNITID) WHERE a.GRTYPE=30 AND b.GRTYPE=29 "
                     f"AND a.GRTOTLT IS NOT NULL AND b.GRTOTLT > 0 AND a.UNITID IN {members}")
        den = self.v(f"SELECT SUM(b.GRTOTLT) FROM GR a JOIN GR b USING (UNITID) WHERE a.GRTYPE=30 AND b.GRTYPE=29 "
                     f"AND a.GRTOTLT IS NOT NULL AND b.GRTOTLT > 0 AND a.UNITID IN {members}")
        self.assertEqual(page["table"]["rows"][0][1], f"{100 * num / den:.1f}%")
        self.assertEqual(page["counts"]["rows"][0][1:], [f"{num:,}", f"{den:,}"])
        self.assertIn("bachelor's degrees are classified by IPEDS as four-year", " ".join(page["warnings"]))
        self.assertIn("students who entered in fall 2021, status as of August 31, 2024", page["interpreted"])
        self.assertIn("limited to the national universe", page["interpreted"])

    def test_f_breakdown_with_a_changed_fixed_value(self):
        page, _ = self.saved_case("f_yale_degrees_field")
        rows = {r[0]: int(r[1].replace(",", "")) for r in page["table"]["rows"]}
        total = self.v("SELECT CTOTALT FROM C_A WHERE unitid=130794 AND AWLEVEL=5 AND MAJORNUM=1 AND CIPCODE='99'")
        self.assertEqual(rows.pop("Total"), total)
        self.assertEqual(sum(rows.values()), total)
        self.assertIn("Bachelor's degree", page["interpreted"])

    def test_g_school_against_its_peers(self):
        page, _ = self.saved_case("g_frcc_peers")
        self.assertIn("own IPEDS comparison group (36 schools)", page["interpreted"])
        self.assertEqual(page["counts"]["rows"][0], ["Front Range Community College", "Full-time retention rate, 2024", "1", "1"])
        self.assertIn("rests on 1 students, fewer than 30", " ".join(page["warnings"]))     # shown, not hidden

    def test_h_data_not_in_ipeds(self):
        page, _ = self.saved_case("h_ai_policies")
        self.assertEqual(page["message"], "IPEDS has no data on AI policies.")       # no pointer invented

    # ---- rules
    def test_tag_off_the_shortlist_is_a_wrong_reading(self):
        wire = dict(label="", operation="schools", measures=[dict(measure="M64", row=[])], schools=[dict(name="Yale", school="S1")],
                    groups=[], peers_of=None, conditions=[], breakdown=None, split_by=None, sort=None,
                    year=dict(stated=None, kind=None), topic=None, outside=None, readings=[])
        page, _ = self.ask("What was Yale's admission rate?", dict(kind="request", requests=[wire], changes=[], chosen=[], decline=None))
        self.assertEqual(page["kind"], "wrong_reading")

    def test_name_not_on_the_shortlist_is_a_wrong_reading(self):
        page, _ = self.ask("What was Yale's admission rate?",
                           reply_request(req("schools", measures=[M("SFA.UPGRNTP")], schools=[S("Yale", 130794)])))
        self.assertEqual(page["kind"], "wrong_reading")
        last = json.loads((Path(self.dir.name) / "questions.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(last["outcome"], "wrong_reading")
        self.assertIn("SFA.UPGRNTP", json.dumps(last["detail"]))
        self.assertIn("DRVADM.DVADM01", last["shortlist"].values())             # the shortlist is logged, tag by tag

    def test_log_lines_carry_the_conversation_and_turn(self):
        wrong = reply_request(req("schools", measures=[M("SFA.UPGRNTP")], schools=[S("Yale", 130794)]))
        state = {}
        self.ask("What was Yale's admission rate?", wrong, state)
        self.ask("What was Yale's admission rate?", wrong, state)
        self.ask("What was Yale's admission rate?", wrong, {})                  # a new conversation
        rows = [json.loads(x) for x in (Path(self.dir.name) / "questions.jsonl").read_text(encoding="utf-8").splitlines()[-3:]]
        self.assertEqual([r["turn"] for r in rows], [1, 2, 1])
        self.assertEqual(rows[0]["conversation"], rows[1]["conversation"])
        self.assertNotEqual(rows[1]["conversation"], rows[2]["conversation"])

    def test_unclear_school_opens_the_picker(self):
        state = {}
        page, _ = self.ask("How many degrees did Marian University award?",
                           reply_request(req("schools", measures=[M("DRVC.BASDEG")], schools=[S("Marian University", None)])), state)
        self.assertEqual(page["kind"], "picker")
        self.assertGreaterEqual(sum("Marian University" in label for _, label in page["candidates"]), 2)
        unitid = page["candidates"][0][0]
        page = answer.pick_school(unitid, state, self.log)
        self.assertEqual(page["kind"], "answer")

    def test_always_ask_term_and_option_buttons(self):
        state = {}
        page, _ = self.ask("How many faculty does Yale have?",
                           reply_request(req("schools", measures=[M("EAP.EAPTOT")], schools=[S("Yale", 130794)])), state)
        self.assertEqual((page["kind"], page["options"]), ("clarify", ["Instructional staff", "All staff with faculty status"]))
        page = answer.choose(0, dict(state), self.log)                       # a button runs the option directly
        self.assertEqual(page["table"]["columns"], ["School", "Total", "Full-time", "Part-time"])
        self.assertEqual(page["table"]["rows"][0][1:], ["3,800", "2,995", "805"])
        self.assertIn("Counts include medical school staff", page["interpreted"])
        typed = dict(kind="choose", request=None, edit=None, options=[], chosen=[1], decline=None)
        page, _ = self.ask("the second one", typed, state)                   # a typed reply is matched to the options
        self.assertEqual(page["table"]["rows"][0][1], "5,735")

    def test_mixed_levels_ask_and_split(self):
        state = {}
        page, _ = self.ask("What is the graduation rate in Ohio?",
                           reply_request(req("group", measures=[M("DRVGR.GRRTTOT")], groups=["State: Ohio"])), state)
        self.assertEqual(page["kind"], "clarify")
        self.assertEqual(page["options"], ["Four-year schools only", "Two-year schools only", "Both shown separately"])
        page = answer.choose(2, state, self.log)
        self.assertEqual(len(page["table"]["rows"]), 2)
        self.assertTrue(page["table"]["rows"][0][0].startswith("Four or more years"))

    def test_year_outside_the_data_is_declined_and_logged(self):
        page, _ = self.ask("Yale's admission rate in 2015",
                           reply_request(req("schools", measures=[M("DRVADM.DVADM01")], schools=[S("Yale", 130794)],
                                             year=dict(stated="2015", kind=None))))
        self.assertEqual(page["kind"], "decline")
        self.assertIn("for Academic year Fall 2024 only, so I can't show 2015", page["message"])
        last = json.loads((Path(self.dir.name) / "declines.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(last["missing"], "years")

    def test_average_with_no_rate_row_is_declined_for_a_group(self):
        page, _ = self.ask("Average federal loan at private colleges",
                           reply_request(req("group", measures=[M("SFA.UFLOANA")], groups=["Private not-for-profit"])))
        self.assertEqual(page["kind"], "decline")
        self.assertIn("Instead, I can show each school's figure, ranked.", page["message"])

    def test_group_average_from_counts(self):
        page, _ = self.ask("What is the average Pell grant?", reply_request(req("group", measures=[M("SFA.UPGRNTA")])))
        self.assertEqual(page["table"]["rows"][0][1], "$5,300")             # NCES 5,300
        self.assertIn("national universe", page["interpreted"])

    def test_finance_is_split_by_reporting_form(self):
        page, _ = self.ask("Core expenses per FTE student nationally",
                           reply_request(req("group", measures=[M("rate:Core expenses per FTE student")])))
        self.assertEqual(len(page["table"]["rows"]), 3)
        self.assertEqual(page["table"]["rows"][0][1], "$32,973")
        self.assertIn("different accounting standards", page["interpreted"])

    def test_group_total_is_a_sum(self):
        page, _ = self.ask("Total fall enrollment", reply_request(req("group", measures=[M("DRVEF.ENRTOT")])))
        expected = self.v("SELECT SUM(ENRTOT) FROM DRVEF WHERE UNITID IN (SELECT unitid FROM group_membership "
                          "WHERE group_name='National universe')")
        self.assertEqual(page["table"]["rows"][0][1], f"{expected:,}")

    def test_declined_group(self):
        page, _ = self.ask("Graduation rate at women's colleges",
                           reply_request(req("group", measures=[M("DRVGR.GRRTTOT")], groups=["women's colleges"])))
        self.assertEqual(page["kind"], "decline")
        self.assertTrue(page["message"].startswith("IPEDS has no flag for this group."))

    def test_data_exists_yes_and_not_set_up(self):
        page, _ = self.ask("Do you have data on admission rates?",
                           reply_request(req("data_exists", measures=[M("DRVADM.DVADM01")], topic="admission rates")))
        self.assertTrue(page["message"].startswith("Yes."))
        page, _ = self.ask("Do you have data on calendar systems?",
                           reply_request(req("data_exists", measures=[M("IC.CALSYS")], topic="calendar systems")))
        self.assertTrue(page["message"].startswith("Yes."))                    # set up in part 5b2

    def test_edits_now_for_texas_rank_them_break_down(self):
        state = {}
        self.ask("Fall enrollment in Ohio", reply_request(req("group", measures=[M("DRVEF.ENRTOT")], groups=["State: Ohio"])), state)
        page, _ = self.ask("now for Texas", reply_edit([("groups", "replace")], req("group", groups=["State: Texas"])), state)
        self.assertIn("Texas", page["interpreted"])
        page, _ = self.ask("rank them", reply_edit([("operation", "replace")], req("rank")), state)
        self.assertEqual(page["table"]["columns"][:2], ["Rank", "School"])
        self.ask("Yale undergraduates", reply_request(req("schools", measures=[M("EFA.EFTOTLT", [("EFALEVEL", "2")])],
                                                          schools=[S("Yale", 130794)])), state)
        page, _ = self.ask("break that down by gender", reply_edit(
            [("operation", "replace"), ("breakdown", "replace")], req("breakdown", breakdown=dict(set="By gender", fixed=[]))), state)
        rows = {r[0]: r[1] for r in page["table"]["rows"]}
        self.assertEqual(rows["Total"], "6,814")

    # ---- change order after Stage 3
    def test_cohort_period_from_offsets(self):
        page, _ = self.saved_case("b_compare_grad")
        self.assertIn("students who entered in fall 2018, status as of August 31, 2024", page["interpreted"])
        two_year = self.v("SELECT UNITID FROM directory WHERE ICLEVEL=2 AND UNITID IN (SELECT UNITID FROM DRVGR WHERE GRRTTOT IS NOT NULL) LIMIT 1")
        name = self.v("SELECT INSTNM FROM directory WHERE UNITID=?", two_year)
        page, _ = self.ask(f"Graduation rate at Yale and {name}", reply_request(req(
            "schools", measures=[M("DRVGR.GRRTTOT")], schools=[S("Yale", 130794), S(name, two_year)],
            readings=[dict(term="graduation rate", reading="Total cohort within 150% of normal time")])))
        self.assertIn("fall 2018 (four or more years schools) or fall 2021 (at least 2 but less than 4 years schools)",
                      page["interpreted"])

    def test_universe_applies_to_every_group_figure_unless_asked(self):
        count = lambda page: int(page["table"]["rows"][0][1].replace(",", ""))
        page, _ = self.ask("How many public two-year colleges are there?",
                           reply_request(req("count_schools", groups=["Public, 2-year"])))
        inside = count(page)
        self.assertEqual(inside, self.v("SELECT COUNT(*) FROM group_membership a JOIN group_membership b USING (unitid) "
                                        "WHERE a.group_name='Public, 2-year' AND b.group_name='National universe'"))
        self.assertIn("limited to the national universe", page["interpreted"])
        page, _ = self.ask("How many public two-year colleges are there, all institutions?",
                           reply_request(req("count_schools", groups=["Public, 2-year"],
                                             readings=[dict(term="national universe", reading="All institutions")])))
        self.assertEqual(count(page), self.v("SELECT COUNT(*) FROM group_membership WHERE group_name='Public, 2-year'"))
        self.assertGreater(count(page), inside)

    def test_word_notes_move_to_definitions(self):
        page, _ = self.saved_case("c_rank_retention")
        self.assertNotIn("State schools", page["interpreted"])
        self.assertIn('"State schools" and "public universities" mean public four-year.', page["definitions"][0]["notes"])

    def test_plain_names_and_user_facing_statements(self):
        page, _ = self.saved_case("d_yale_race")
        self.assertTrue(page["interpreted"].startswith("Fall enrollment, All students, Undergraduate total"))
        statements = [s for (s,) in self.db.execute("SELECT DISTINCT statement FROM dict_terms WHERE statement IS NOT NULL")]
        self.assertFalse([s for s in statements if s.startswith("State ")])          # no instructions to the app left
        shown = {}                                                              # every name shown for two or more
        for t, v, name in self.db.execute('SELECT "table", variable, shown_name FROM dict_measures'):   # measures, after
            shown.setdefault(" ".join((name or "").lower().split()), []).append(f"{t}.{v}")   # the subjects, is listed
        clashing = {n for n, ms in shown.items() if len(ms) > 1}
        self.assertEqual(clashing, {n for (n,) in self.db.execute("SELECT name FROM main.name_clashes")})

    def test_tests_never_write_to_the_shared_log(self):
        shared = config.LOG_DIR
        before = {p.name: p.stat().st_size for p in shared.glob("*.jsonl")} if shared.exists() else {}
        self.ask("What was Yale's admission rate?",
                 reply_request(req("schools", measures=[M("DRVADM.DVADM01")], schools=[S("Yale", 130794)])))
        after = {p.name: p.stat().st_size for p in shared.glob("*.jsonl")} if shared.exists() else {}
        self.assertEqual(before, after)


@unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built")
class RealReplies(unittest.TestCase):
    """What the model actually returned in the live smoke test of 2026-11-16 (tests/replies/real_*.json), replayed.
    Where the old format let the model write something tags now rule out, the file keeps both."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.log = Log(cls.dir.name)
        cls.states = {}

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def run_case(self, name):
        case = json.loads((REPLIES / f"real_{name}.json").read_text(encoding="utf-8"))
        state = self.states.setdefault(name, {}) if not case.get("after") else self.states[case["after"].replace("real_", "")]
        page = answer.ask(case["question"], state, self.log, call=saved(case["reply"]))
        self.assertEqual(page["kind"], case["expect"], name)
        return page

    def test_all_nine(self):
        for name in ["a_yale_admission", "b_compare_grad", "c_rank_retention", "e_group_grad", "f_yale_degrees_field",
                     "g_frcc_peers", "h_ai_policies", "i_add_northeastern"]:
            self.run_case(name)

    def test_d_summary_measure_switches_to_the_detailed_one(self):
        page = self.run_case("d_yale_race")                         # the model chose undergraduate enrollment, DRVEF.EFUG
        rows = {r[0]: r[1] for r in page["table"]["rows"]}
        self.assertEqual(rows["Total"], "6,814")
        self.assertIn("Undergraduate enrollment has no breakdown of its own, so it is broken down using Fall enrollment, "
                      "All students, Undergraduate total", page["interpreted"])


    def run_second(self, name):
        case = json.loads((REPLIES / f"real2_{name}.json").read_text(encoding="utf-8"))
        return answer.ask(case["question"], {}, self.log, call=saved(case["reply"]))

    def test_d2_reading_then_switch_keeps_the_detailed_measure(self):
        """Live reply: undergraduate enrollment (summary), the race set and the reading 'Undergraduate fall enrollment'."""
        page = self.run_second("d_yale_race")
        self.assertEqual(page["kind"], "answer")
        self.assertEqual({r[0]: r[1] for r in page["table"]["rows"]}["Total"], "6,814")
        self.assertIn("broken down using Fall enrollment, All students, Undergraduate total", page["interpreted"])

    def test_f2_switch_keeps_the_bachelors_level(self):
        """Live reply: bachelor's degrees (summary) with the field breakdown; the set's default level must not win."""
        page = self.run_second("f_yale_degrees_field")
        rows = {r[0]: int(r[1].replace(",", "")) for r in page["table"]["rows"]}
        db = latest_only(sqlite3.connect(f"file:{DB}?mode=ro", uri=True))
        bachelors = db.execute("SELECT CTOTALT FROM C_A WHERE unitid=130794 AND AWLEVEL=5 AND MAJORNUM=1 AND CIPCODE='99'").fetchone()[0]
        db.close()
        self.assertEqual(rows.pop("Total"), bachelors)
        self.assertEqual(sum(rows.values()), bachelors)
        self.assertNotIn("Degrees total", page["interpreted"])


    def test_flagged_school_gets_the_related_campus_note(self):
        page = answer.ask("Southern University and A & M College enrollment", {}, self.log, call=saved(reply_request(req(
            "schools", measures=[M("DRVEF.ENRTOT")], schools=[S("Southern University and A & M College", 160621)]))))
        self.assertIn("together with its related campuses: Southern University Law Center", " ".join(page["warnings"]))
        page = answer.ask("Southern University Law Center enrollment", {}, self.log, call=saved(reply_request(req(
            "schools", measures=[M("DRVEF.ENRTOT")], schools=[S("Southern University Law Center", 440916)]))))
        self.assertIn("with its parent campus, Southern University and A & M College", " ".join(page["warnings"]))


class Precedence(unittest.TestCase):
    def test_first_layer_wins_and_defaults_only_fill(self):
        from path.resolve import first_present
        self.assertEqual(first_present({"awlevel": "5"}, {"AWLEVEL": "12", "MAJORNUM": "1"}, {"CIPCODE": "99", "MAJORNUM": "2"}),
                         {"AWLEVEL": "5", "MAJORNUM": "1", "CIPCODE": "99"})


class ChangeOrder1121(unittest.TestCase):
    """The change order of 2026-11-21: defects A to F, net-price group averages, state-or-school names, categories."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.log = Log(cls.dir.name)
        cls.db = latest_only(sqlite3.connect(f"file:{DB}?mode=ro", uri=True))
        cls.NET = [M("COST2_NETPRICE.NPIST2"), M("COST2_NETPRICE.NPGRN2")]
        cls.READ = [dict(term="net price", reading="Students awarded grant or scholarship aid")]

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.dir.cleanup()

    def ask(self, question, reply, state=None):
        return answer.ask(question, {} if state is None else state, self.log, call=saved(reply))

    def members(self, group):
        return {u for (u,) in self.db.execute("SELECT unitid FROM group_membership WHERE group_name=?", (group,))}

    def test_a_net_price_ranking_uses_the_measure_for_each_kind_of_school(self):
        page = self.ask("Compare net price for grant-aided students across the Ivy League",
                        reply_request(req("rank", measures=self.NET, groups=["Ivy League"], readings=self.READ)))
        self.assertEqual(len(page["table"]["rows"]), 8)                     # was empty: the public column was ranked

    def test_a_empty_ranking_says_so(self):
        page = self.ask("Rank administrative units by enrollment",
                        reply_request(req("rank", measures=[M("DRVEF.ENRTOT")], groups=["Administrative Unit"])))
        self.assertEqual(page["table"]["rows"], [])
        self.assertTrue(any(n.startswith("No school in") for n in page["notes"]))

    def test_net_price_group_average_is_weighted_by_the_cohort(self):
        page = self.ask("Average net price for grant-aided students in the Ivy League",
                        reply_request(req("group", measures=self.NET, groups=["Ivy League"], readings=self.READ)))
        ivy = self.members("Ivy League")
        rows = self.db.execute("SELECT n.NPGRN2, c.GRNTN2 FROM COST2_NETPRICE n JOIN COST2_FINANCIALAID c USING (UNITID, year) "
                               "WHERE n.NPGRN2 IS NOT NULL AND c.GRNTN2 > 0 AND n.UNITID IN (%s)" % ",".join(map(str, ivy))).fetchall()
        expected = sum(a * b for a, b in rows) / sum(b for _, b in rows)
        self.assertEqual(len(page["table"]["rows"]), 1)                     # all private: one figure
        self.assertEqual(page["table"]["rows"][0][1], show.fmt((expected, "average")))

    def test_net_price_group_mixing_public_and_private_is_split_with_a_statement(self):
        page = self.ask("Average net price for grant-aided students in Ohio",
                        reply_request(req("group", measures=self.NET, groups=["State: Ohio"], readings=self.READ)))
        labels = [r[0] for r in page["table"]["rows"]]
        self.assertEqual(len(labels), 2)
        self.assertTrue(any("(Public)" in x for x in labels) and any("(Private, nonprofit or for-profit)" in x for x in labels))
        self.assertIn("kind of school", page["interpreted"])

    def test_b_topic_outside_ipeds_has_no_empty_table(self):
        page = self.ask("Any variable that shows economic mobility", reply_request(req(
            "data_exists", topic="Earnings after graduation; return on investment; economic mobility")))
        self.assertEqual(page["table"]["columns"], [])
        self.assertIn("College Scorecard", page["message"])

    def test_c_level_check_covers_the_named_schools(self):
        names = [S("Worcester Polytechnic Institute", 168421), S("Case Western Reserve University", 201645),
                 S("Drexel University", 212054)]
        page = self.ask("Graduation rate at Worcester Polytechnic Institute, Case Western Reserve University and Drexel University",
                        reply_request(req("school_vs_group", measures=[M("DRVGR.GBA6RTT")], schools=names)))
        self.assertNotEqual(page["kind"], "clarify")                        # all four-year: no level question

    def test_d_rate_from_counts_is_shown_as_a_percent(self):
        page = self.ask("Award within eight years, Outcome Measures, national",
                        reply_request(req("group", measures=[M("rate:Award within eight years (Outcome Measures)")])))
        self.assertEqual(page["table"]["rows"][0][1], "47.3%")              # NCES 47.3; was "$0"

    def test_e_a_chosen_reading_wins_over_the_level_default(self):
        page = self.ask("Graduation rate within 150% of normal time at four-year schools", reply_request(req(
            "group", measures=[M("DRVGR.GRRTTOT")], groups=["Four or more years"],
            readings=[dict(term="graduation rate", reading="Total cohort within 150% of normal time")])))
        self.assertEqual(page["table"]["rows"][0][1], "61.0%")             # NCES 61; the bachelor's rate would be 64.8

    def test_f_latest_year_is_not_a_stated_year(self):
        page = self.ask("Dual enrollment, most recent year, all colleges", reply_request(req(
            "group", measures=[M("EFFY_HS.EFYTOTLT")], year=dict(stated="most recent year", kind="latest"))))
        self.assertEqual(page["kind"], "answer")

    def test_state_or_school_name_asks(self):
        page = self.ask("Michigan enrollment", reply_request(req("group", measures=[M("DRVEF.ENRTOT")], groups=["State: Michigan"])))
        self.assertEqual(page["kind"], "clarify")
        self.assertIn("University of Michigan-Ann Arbor", page["options"])
        page = self.ask("How many colleges are in Michigan?", reply_request(req("count_schools", groups=["State: Michigan"])))
        self.assertEqual(page["kind"], "answer")                            # counting schools: only the state makes sense

    def test_one_measure_at_two_category_rows_keeps_both_columns(self):
        page = self.ask("How many full-time and part-time instructional staff did Yale have in Fall 2024?", reply_request(req(
            "schools", schools=[S("Yale", 130794)],
            measures=[M("S_OC.HRTOTLT", [("STAFFCAT", "2210")]), M("S_OC.HRTOTLT", [("STAFFCAT", "3210")])])))
        ft, pt = [self.db.execute("SELECT HRTOTLT FROM S_OC WHERE UNITID=130794 AND STAFFCAT=?", (c,)).fetchone()[0]
                  for c in (2210, 3210)]
        self.assertEqual(page["table"]["rows"][0][1:], [f"{ft:,}", f"{pt:,}"])

    def test_per_school_group_means_its_peers(self):
        page = self.ask("compare RIT's completion rate to its peer institutions", reply_request(req(
            "school_vs_group", measures=[M("DRVGR.GBA6RTT")], groups=["IPEDS comparison group"], peers_of=195003)))
        self.assertEqual(len(page["table"]["rows"]), 2)                     # RIT, and its comparison group

    def test_staff_total_says_it_excludes_graduate_assistants_and_offers_them(self):
        page = self.ask("How many staff did Yale employ in fall 2024?",
                        reply_request(req("schools", measures=[M("S_OC.HRTOTLT")], schools=[S("Yale", 130794)])))
        self.assertIn("excludes graduate assistants", page["interpreted"])
        page = self.ask("How many graduate assistants did Yale have in fall 2024?", reply_request(req(
            "schools", measures=[M("S_OC.HRTOTLT", [("STAFFCAT", "4400")])], schools=[S("Yale", 130794)])))
        ga = self.db.execute("SELECT HRTOTLT FROM S_OC WHERE UNITID=130794 AND STAFFCAT=4400").fetchone()[0]
        self.assertEqual(page["table"]["rows"][0][1], f"{ga:,}")
        self.assertNotIn("excludes graduate assistants", page["interpreted"])

    def test_go_back_restores_the_whole_earlier_request(self):
        state = {}
        q = "Compare net price for grant-aided students across the Ivy League"
        self.ask(q, reply_request(req("rank", measures=self.NET, groups=["Ivy League"], readings=self.READ)), state)
        narrow = dict(kind="edit", request=None, options=[], chosen=[], decline=None,
                      edit=dict(changes=[dict(field="operation", action="replace"), dict(field="groups", action="remove"),
                                         dict(field="schools", action="add")],
                                values=dict(rq.empty("schools"), schools=[S("Yale", 130794), S("Harvard", 166027)])))
        page = self.ask(q + " Just Yale and Harvard.", narrow, state)
        self.assertEqual(len(page["table"]["rows"]), 2)
        back = dict(kind="edit", request=None, options=[], chosen=[], decline=None,
                    edit=dict(changes=[dict(field="schools", action="back")], values=rq.empty("schools")))
        page = self.ask(q + " Actually, go back to all eight.", back, state)
        self.assertEqual(page["table"]["columns"][0], "Rank")              # the operation comes back too
        self.assertEqual(len(page["table"]["rows"]), 8)

    def test_shortlist_shows_where_a_breakdown_is_held(self):
        s = shortlist.shortlist("Yale fall undergraduate enrollment by race and ethnicity", DB)
        ug = next(m for m in s["measures"] if m["id"] == "DRVEF.EFUG")
        self.assertEqual(ug["detail_held"], "All students, Undergraduate total")
        text, _ = interpret.render(s, None, None, "q")
        self.assertIn("held at All students, Undergraduate total", text)
        self.assertIn("unless `row` names another", text)                   # column sets keep the measure's row

    def test_undergrad_and_grad_shorthand_reach_the_shortlist(self):
        s = shortlist.shortlist("Show Yale's undergrad population by race and ethnicity", DB)
        self.assertIn(("EFA", "2"), {(r["table"], r["code"]) for r in s["rows"]})    # the undergraduate row
        s = shortlist.shortlist("How many grad students did Yale enroll?", DB)
        self.assertIn("DRVEF12.E12GRAD", [m["id"] for m in s["measures"]])
        s = shortlist.shortlist("What is the grad rate at RIT?", DB)
        self.assertIn("DRVGR.GRRTTOT", [m["id"] for m in s["measures"]])

    def test_shorthand_reaches_the_shortlist(self):
        cases = {"What is the universe with the lowest net cost?": "COST2_NETPRICE.NPGRN2",
                 "What is Yale's SFR?": "EFD.STUFACR",
                 "Spending per student at public universities": "rate:Core expenses per FTE student",
                 "How many freshmen did Yale enroll?": "DRVEF12.E12UG1ST"}
        for question, wanted in cases.items():
            self.assertIn(wanted, [m["id"] for m in shortlist.shortlist(question, DB)["measures"]], question)

    def test_first_time_and_retention_statements(self):
        page = self.ask("How many freshmen did Yale enroll?",
                        reply_request(req("schools", measures=[M("DRVEF12.E12UG1ST")], schools=[S("Yale", 130794)])))
        self.assertIn("first-year transfer students are not included", page["interpreted"])
        page = self.ask("What is the persistence rate nationally?", reply_request(req("group", measures=[M("EFD.RET_PCF")])))
        self.assertIn("IPEDS calls this the retention rate", page["interpreted"])

    def test_low_income_is_a_term_with_its_statement(self):
        page = self.ask("Share of low-income students at Yale", reply_request(req(
            "schools", measures=[M("SFA.UPGRNTP")], schools=[S("Yale", 130794)],
            readings=[dict(term="low-income", reading="Percent of undergraduates awarded Pell grants")])))
        self.assertIn("IPEDS does not measure income", page["interpreted"])
        page = self.ask("Percent of undergraduates awarded Pell grants at Yale", reply_request(req(
            "schools", measures=[M("SFA.UPGRNTP")], schools=[S("Yale", 130794)])))
        self.assertNotIn("IPEDS does not measure income", page["interpreted"])   # only when the reading was chosen

    def test_ranking_weights_names_and_caps_one_table(self):
        s = shortlist.shortlist("How many applicants did Yale have?", DB)
        main = [m for m in s["measures"] if m["set_up"]][:shortlist.SET_UP]
        self.assertEqual(main[0]["id"], "ADM.APPLCN")                       # was crowded out by the table title
        s = shortlist.shortlist("What about part time student persistence", DB)   # no table clearly wins: the cap holds
        tables = [m["table"] or "rate" for m in s["measures"] if m["set_up"]][:shortlist.SET_UP]
        self.assertLessEqual(max(tables.count(t) for t in tables), shortlist.PER_TABLE)
        s = shortlist.shortlist("How many of Yale's admitted students submitted ACT scores for fall 2024?", DB)
        self.assertIn("ADM.ACTNUM", [m["id"] for m in s["measures"]])      # a sixth admissions measure, let in by score

    def test_word_endings_offering_and_enrollment(self):
        self.assertEqual(shortlist.words("offering enrollment enrolled"), ["offer", "enroll", "enroll"])
        s = shortlist.shortlist("Do Smith, Mount Holyoke, and Wellesley offer bachelor's and master's degrees?", DB)
        self.assertIn("HD.UGOFFER", [m["id"] for m in s["measures"]])

    def test_urm_is_outside_ipeds(self):
        s = shortlist.shortlist("What share of students are URM at Yale?", DB)
        self.assertIn("Underrepresented minority (URM) students", [o["topic"] for o in s["outside"]])

    def test_shortlist_shows_category_columns(self):
        s = shortlist.shortlist("How many full-time and part-time instructional staff did Yale have in Fall 2024?", DB)
        staff = next(m for m in s["measures"] if m["id"] == "S_OC.HRTOTLT")
        self.assertEqual(staff["categories"][0]["column"].upper(), "STAFFCAT")
        text, _ = interpret.render(s, None, None, "q")
        self.assertIn("categories by STAFFCAT (default: Grand Total)", text)


def reply_decline(missing, request=None, about=None):
    return dict(kind="about_decline" if about else "decline", request=request, edit=None, options=[], chosen=[],
                decline=dict(reason="model's own reason, for the log", wanted="", missing=missing,
                             closest="model's own suggestion", about=about))


DEGREES = [M(f"DRVC.{c}") for c in ("ASCDEG", "BASDEG", "MASDEG", "DOCDEGRS", "DOCDEGPP", "DOCDEGOT")]
DEGREE_READING = [dict(term="degrees", reading="Degrees by level")]


class Stage50(unittest.TestCase):
    """Part 5.0: misspellings, the four answers, code-written messages, kept declines, questions about them,
    partial answers."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.log = Log(cls.dir.name)

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def ask(self, question, reply, state):
        return answer.ask(question, state, self.log, call=saved(reply))

    def test_misspelling_rules(self):
        v = {4: {"tech", "yale"}, 9: {"admission"}, 7: {"college"}}
        self.assertIn("tech", shortlist.corrected("wsu tehc", v))         # four letters: a swap of neighbours
        self.assertNotIn("tech", shortlist.corrected("tach", v))          # four letters: no substitution
        self.assertIn("yale", shortlist.corrected("Yael", v))
        self.assertIn("college", shortlist.corrected("colege", v))        # six letters: one letter off
        self.assertNotIn("college", shortlist.corrected("colige", v))     # ... not two
        self.assertIn("admission", shortlist.corrected("admisisons", v))  # nine letters: up to two

    def test_misspelled_questions_reach_the_right_items(self):
        s = shortlist.shortlist("what data do you have on admisisons", DB)
        self.assertIn("DRVADM.DVADM01", [m["id"] for m in s["measures"]])
        s = shortlist.shortlist("what was the fall enrollment for wsu tehc", DB)
        ids = [x["id"] for x in s["schools"]]
        self.assertEqual(ids[0], 156107)                                  # WSU Tech
        self.assertNotIn(229115, ids)                                     # never Texas Tech

    def test_messages_have_no_internal_words(self):
        db = latest_only(sqlite3.connect(f"file:{DB}?mode=ro", uri=True))
        for (text,) in db.execute("SELECT statement FROM dict_terms WHERE term='message'"):
            self.assertNotRegex(text.lower(), r"shortlist|\btag\b|dictionary|\bm\d+\b")
        db.close()

    def test_not_in_ipeds_without_an_outside_row_is_not_found(self):
        state = {}
        page = self.ask("What is the summer melt rate at Yale?", reply_decline("not in IPEDS", req("schools", schools=[S("Yale", 130794)])), state)
        self.assertNotIn("IPEDS does not", page["message"])
        self.assertTrue(page["message"].startswith("I couldn't find data matching that."))
        self.assertNotIn("model's own", page["message"])                   # the model's words go to the log only
        row = json.loads((Path(self.dir.name) / "questions.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        self.assertTrue(row["search_miss"])
        self.assertEqual(row["model_explanation"]["reason"], "model's own reason, for the log")

    def test_data_exists_with_nothing_found_is_not_found(self):
        page = self.ask("what data do you have on summer melt", reply_request(req("data_exists", topic="summer melt")), {})
        self.assertNotIn("does not collect", page["message"])
        self.assertIn("I couldn't find data on summer melt", page["message"])

    def test_decline_is_kept_and_a_follow_up_edits_it(self):
        state = {}
        q = "How many degrees did Marian University award over the last ten years?"
        page = self.ask(q, reply_decline("years", req("schools", measures=DEGREES, schools=[S("Marian University", 151786)],
                                                      readings=DEGREE_READING, year=dict(stated="last ten years", kind=None))), state)
        self.assertEqual(page["kind"], "decline")
        self.assertIn("degrees by level", page["message"])                 # not just "Associate's degree"
        self.assertNotIn("Associate's degree", page["message"])
        edit = dict(kind="edit", request=None, options=[], chosen=[], decline=None,
                    edit=dict(changes=[dict(field="year", action="replace")],
                              values=dict(rq.empty("schools"), year=dict(stated="2023-24", kind=None))))
        page = self.ask(q + " show 2023-24", edit, state)
        self.assertEqual(page["kind"], "answer")
        self.assertEqual(page["table"]["rows"][0][0], "Marian University")

    def test_why_where_and_instead(self):
        state = {}
        page = self.ask("What's the ROI for Yale?", reply_decline("not in IPEDS", req(
            "data_exists", topic="Earnings after graduation; return on investment; economic mobility")), state)
        self.assertIn("IPEDS does not collect earnings", page["message"])
        page = self.ask("What's the ROI for Yale? Where can I find that?", reply_decline("other", about="where"), state)
        self.assertIn("College Scorecard", page["message"])
        state = {}
        self.ask("Graduation rate for Hispanic-serving institutions", reply_request(req(
            "group", measures=[M("DRVGR.GRRTTOT")], groups=["Hispanic-serving institutions (HSIs)"])), state)
        page = self.ask("Graduation rate for Hispanic-serving institutions. Why not?", reply_decline("other", about="why"), state)
        self.assertIn("IPEDS has no flag for this group", page["message"])
        page = self.ask("Graduation rate for Hispanic-serving institutions. Where can I find that?",
                        reply_decline("other", about="where"), state)
        self.assertEqual(page["message"], "I don't have another source to point you to for this.")
        state = {}
        q = "Enrollment at Yale in 1990"
        page = self.ask(q, reply_request(req("schools", measures=[M("DRVEF.ENRTOT")], schools=[S("Yale", 130794)],
                                             year=dict(stated="1990", kind=None))), state)
        self.assertEqual(page["kind"], "decline")
        page = self.ask(q + " What can you show me instead?", reply_decline("other", about="instead"), state)
        self.assertEqual(page["kind"], "answer")                           # the years held, run
        self.assertTrue(page["message"].startswith("Instead, I can show"))

    def test_part_of_the_years_held_is_answered(self):
        page = self.ask("Yale admission rate in 2015 and 2024", reply_request(req(
            "schools", measures=[M("DRVADM.DVADM01")], schools=[S("Yale", 130794)], year=dict(stated="2015 and 2024", kind=None))), {})
        self.assertEqual(page["kind"], "answer")
        self.assertIn("2015 is not available", page["interpreted"])

    def test_a_measure_set_up_in_part_5b2_is_answered_beside_another(self):
        page = self.ask("Yale enrollment and its library physical book count", reply_request(req(
            "schools", measures=[M("DRVEF.ENRTOT"), M("AL.LPBOOKS")], schools=[S("Yale", 130794)])), {})
        self.assertEqual(page["kind"], "answer")
        self.assertNotIn("isn't set up", page["interpreted"])                   # every measure is set up (part 5b2)

    def test_an_edit_while_options_are_open_applies_to_every_option(self):
        base = req("schools", measures=DEGREES, readings=DEGREE_READING, year=dict(stated="last ten years", kind=None))
        state = {"pending": [dict(label="Marian University, Indianapolis", request=dict(base, schools=[S("Marian University", 151786)])),
                             dict(label="Marian University, Fond du Lac", request=dict(base, schools=[S("Marian University", 239080)]))]}
        edit = dict(kind="edit", request=None, options=[], chosen=[], decline=None,
                    edit=dict(changes=[dict(field="year", action="replace")],
                              values=dict(rq.empty("schools"), year=dict(stated="2023-24", kind=None))))
        page = self.ask("How many degrees did Marian University award? show 2023-24", edit, state)
        self.assertEqual(page["kind"], "clarify")
        self.assertEqual(page["options"], ["Marian University, Indianapolis (2023-24)", "Marian University, Fond du Lac (2023-24)"])
        self.assertTrue(all(o["request"]["year"]["stated"] == "2023-24" for o in state["pending"]))

    def test_a_model_decline_of_a_named_group_uses_the_group_entry(self):
        state = {}
        page = self.ask("Graduation rate for Hispanic-serving institutions", reply_decline("group", req(
            "group", measures=[M("DRVGR.GRRTTOT")], groups=["Hispanic-serving institutions (HSIs)"])), state)
        self.assertTrue(page["message"].startswith("IPEDS has no flag for this group."))
        page = self.ask("Graduation rate for Hispanic-serving institutions. Why not?", reply_decline("other", about="why"), state)
        self.assertTrue(page["message"].startswith("IPEDS has no flag for this group."))

    def test_school_vs_group_shows_every_named_school(self):
        page = self.ask("Graduation rate at WPI and Drexel beside RIT's peers", reply_request(req(
            "school_vs_group", measures=[M("DRVGR.GBA6RTT")], peers_of=195003,
            schools=[S("Worcester Polytechnic Institute", 168421), S("Drexel University", 212054)])), {})
        names = [r[0] for r in page["table"]["rows"]]
        self.assertIn("Worcester Polytechnic Institute", names)
        self.assertIn("Drexel University", names)                          # not silently dropped

    def test_option_labels_never_show_tags(self):
        self.assertEqual(rq.no_tags("Smith College (S4)"), "Smith College")
        self.assertEqual(rq.no_tags("Admission rate M1 for G2"), "Admission rate for")
        self.assertEqual(rq.no_tags("Fall 2024 enrollment"), "Fall 2024 enrollment")

    def test_an_edit_while_the_school_picker_is_open_asks_again_with_the_change(self):
        state = {}
        q = "How many degrees did Marian University award over the last ten years?"
        page = self.ask(q, reply_request(req("schools", measures=DEGREES, readings=DEGREE_READING,
                                             schools=[dict(name="Marian University", id=None)],
                                             year=dict(stated="last ten years", kind=None))), state)
        self.assertEqual(page["kind"], "picker")
        edit = dict(kind="edit", request=None, options=[], chosen=[], decline=None,
                    edit=dict(changes=[dict(field="year", action="replace")],
                              values=dict(rq.empty("schools"), year=dict(stated="2023-24", kind=None))))
        page = self.ask(q + " show 2023-24", edit, state)
        self.assertEqual(page["kind"], "picker")                           # still which Marian, now for 2023-24
        page = answer.pick_school(151786, state, self.log)
        self.assertEqual(page["kind"], "answer")
        self.assertEqual(page["table"]["rows"][0][0], "Marian University")

    def test_an_outside_row_covers_only_its_part(self):
        topic = "Graduation rates by major"
        request = req("group", measures=[M("DRVEF.ENRTOT")], topic=topic)
        q = "total fall enrollment, and graduation rates by major"
        for reply in (reply_request(request), reply_decline("not in IPEDS", request)):
            page = self.ask(q, reply, {})
            self.assertEqual(page["kind"], "answer")                       # the part IPEDS has is answered
            self.assertIn("not by major", page["interpreted"])             # and the part it lacks is named

    def test_choosing_an_option_clears_the_pending_question(self):
        state = {"pending": [dict(label="A", request=req("schools", measures=[M("DRVEF.ENRTOT")], schools=[S("Yale", 130794)]))]}
        answer.choose(0, state, self.log)
        self.assertIsNone(state["pending"])


class ReleaseLabel(unittest.TestCase):
    """Part 5a: each year's figures are labelled with their release, provisional or final."""

    def test_label_and_warning_follow_the_status(self):
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE _releases (year INTEGER, release TEXT, status TEXT, source_file TEXT, loaded_at TEXT, seconds REAL)")
        db.executemany("INSERT INTO _releases VALUES (?,?,?,?,?,?)", [(2023, "IPEDS_2023-24_Final", "final", "", "", 0),
                                                                      (2024, "IPEDS_2024-25_Provisional", "provisional", "", "", 0)])
        self.assertEqual(answer.release(db)["status"], "provisional")             # the latest year by default
        self.assertEqual(answer.release(db, 2023)["status"], "final")
        self.assertEqual(show.release_label(answer.release(db)), "IPEDS 2024-25 release (provisional)")
        self.assertEqual(show.release_label(answer.release(db, 2023)), "IPEDS 2023-24 release (final)")

    def test_an_answer_names_its_release(self):
        log = Log(tempfile.mkdtemp())
        page = answer.ask("What was Yale's admission rate?", {}, log, call=saved(reply_request(req(
            "schools", measures=[M("DRVADM.DVADM01")], schools=[S("Yale", 130794)]))))
        self.assertEqual(page["data_release"], "Figures from the IPEDS 2024-25 release (provisional).")
        self.assertTrue(any("provisional and may change" in w for w in page["warnings"]))


class Show(unittest.TestCase):
    def test_formats(self):
        self.assertEqual([show.fmt(c) for c in [(5, "percent"), (77.86, "percent"), (5300.4, "average"), (20066904, "count"),
                                                 (14, "ratio"), None]], ["5%", "77.9%", "$5,300", "20,066,904", "14", "no value"])


class Retired(unittest.TestCase):
    """Part 5b addition: variables IPEDS collected in earlier releases only. Never "not found"."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.log = Log(cls.dir.name)

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def run_request(self, request):
        return answer.run_direct(request, {}, self.log, DB, question="[test]")

    def test_retired_with_a_successor(self):
        page = self.run_request(req("schools", measures=[M("IC.ENRHSST")], schools=[S("Yale", 130794)]))
        self.assertEqual(page["kind"], "decline")
        self.assertRegex(page["message"], r"^IPEDS collected .+ in 2023-24 only\. It was replaced by .+\.$")

    def test_retired_with_no_successor(self):
        page = self.run_request(req("schools", measures=[M("IC_PCCAMPUSES.CAMPUSID")], schools=[S("Yale", 130794)]))
        self.assertRegex(page["message"], r"^IPEDS collected .+ to 2023-24\. It is no longer collected\.$")

    def test_retired_with_an_approved_successor_and_a_rejected_one(self):
        page = self.run_request(req("schools", measures=[M("DRVF.F1INSTPS")], schools=[S("Yale", 130794)]))
        self.assertRegex(page["message"], r"^IPEDS collected .+ in 2015-16 only\. It was replaced by Salaries and wages .+\.$")
        page = self.run_request(req("schools", measures=[M("HD.CARNEGIE")], schools=[S("Yale", 130794)]))   # rejected
        self.assertTrue(page["message"].endswith("It is no longer collected."), page["message"])

    def test_retired_beside_a_current_measure_is_named_and_the_rest_answered(self):
        page = self.run_request(req("schools", measures=[M("DRVADM.DVADM01"), M("IC.ENRHSST")], schools=[S("Yale", 130794)]))
        self.assertEqual(page["kind"], "answer")
        self.assertIn("IPEDS collected", page["interpreted"])                # named in "Interpreted as"

    def test_a_category_column_is_a_row_choice_never_the_figure(self):
        """Part 5b2 decision 1, from the instructional-staff question: the model named the coded full-/part-time column
        (S_OC.FTPT) as the figure, once for each staff row, and the answer showed the words Full-time, Part-time."""
        logged = req("schools", schools=[S("Yale University", 130794)], year=dict(stated="Fall 2024", kind="fall"),
                     measures=[M("S_OC.FTPT", [("STAFFCAT", "3210")]), M("S_OC.FTPT", [("STAFFCAT", "2210")])])
        page = self.run_request(logged)
        self.assertEqual(page["kind"], "clarify")                            # which figure, never the codes
        self.assertIn("is not a figure", page["message"])
        self.assertIn("Staff headcount, from the occupation table", page["options"])   # the table's total, by its plain name
        state = {"pending": None}
        answer.run_direct(logged, state, self.log, DB, "[test]")
        chosen = answer.choose(page["options"].index("Staff headcount, from the occupation table"), state, self.log, DB)
        self.assertEqual(chosen["kind"], "answer")
        values = [v for row in chosen["table"]["rows"] for v in row[1:]]
        self.assertEqual(len(values), 2)                                       # part-time and full-time staff ...
        self.assertTrue(all(v.replace(",", "").isdigit() for v in values))   # ... as counts, not the words
        short = shortlist.shortlist("How many full-time and part-time instructional staff did Yale have in Fall 2024?", DB)
        self.assertNotIn("S_OC.FTPT", [m["id"] for m in short["measures"]])  # never offered as a measure

    def test_earlier_net_price_and_tuition_take_the_measure_for_each_kind_of_school(self):
        """Part 5b2 decision 2, from the Haiku runs: the model picked the in-state net price for Wellesley (private) and
        the program-year tuition for Smith (academic calendar); both showed no value."""
        page = self.run_request(req("schools", measures=[M("COST2_NETPRICE.NPIST1")], schools=[S("Wellesley College", 168218)]))
        self.assertEqual(page["kind"], "answer")
        self.assertNotEqual(page["table"]["rows"][0][-1], "no value")          # the private-school net price, 2022-23
        page = self.run_request(req("schools", measures=[M("COST1.chg1py2")], schools=[S("Smith College", 167835)]))
        self.assertEqual(page["kind"], "answer")
        self.assertNotEqual(page["table"]["rows"][0][-1], "no value")          # the academic-year tuition, 2023-24

    def test_other_charges_take_the_measure_for_each_calendar(self):
        """Decision of 2026-11-23 (item 1), from the Mount Holyoke room-and-board question: the model picked the
        program-year food and housing column, which an academic-calendar school leaves empty."""
        page = self.run_request(req("schools", measures=[M("COST1.chg5py2")], schools=[S("Mount Holyoke College", 166939)]))
        self.assertEqual(page["kind"], "answer")
        self.assertNotEqual(page["table"]["rows"][0][-1], "no value")          # the academic-year charge, 2023-24

    def test_a_condition_uses_each_schools_own_finance_form(self):
        """Decision of 2026-11-23 (item 2), from "How many schools have negative net worth and which are they?": each
        school is tested on its own form's measure, and the list is grouped by form."""
        page = self.run_request(req("list", conditions=[dict(measure="F_F1A.F1A18", comparison="<", value=0)]))
        self.assertEqual(page["kind"], "answer")
        table = page["table"]
        self.assertEqual(table["columns"][:2], ["Kind of school", "Measure"])
        forms = [r[0] for r in table["rows"]]
        self.assertEqual(forms, sorted(forms, key=["Reports on the GASB finance form", "Reports on the FASB finance form",
                                                  "Reports on the for-profit finance form"].index))   # grouped by form
        self.assertEqual({r[1].split(": ")[-1] for r in table["rows"]}, {"Net position", "Total net assets", "Total equity"})
        self.assertTrue(all(r[-1].startswith("$-") for r in table["rows"]))     # each below zero on its own measure
        text = page["interpreted"]
        self.assertIn("Fiscal year 2024", text)
        self.assertIn("different accounting standards", text)                  # not strictly comparable
        self.assertIn("pension", text)                                          # the note on net position (dictionary)
        self.assertIn("excluding administrative offices", text)                 # system offices left out, and said

    def test_codes_without_labels_and_measures_without_values(self):
        """Decisions of 2026-11-23: a code the codebook does not label is shown as the code, with the note "IPEDS gives
        no label for this code"; a measure with no value in any year is "IPEDS has no values for this measure"."""
        from path import fetch
        data = fetch.Data(sqlite3.connect(f"file:{DB}?mode=ro", uri=True))
        self.assertEqual(data.label("HD", "SECTOR", 1.0), data.label("HD", "SECTOR", 1))   # 1.0 is code 1
        self.assertFalse(getattr(data, "unlabelled", False))
        self.assertEqual(data.label("HD", "SECTOR", 987), 987)                            # no label: the code itself
        self.assertTrue(data.unlabelled)
        page = self.run_request(req("schools", measures=[M("COST1.CHG10AY0")], schools=[S("Yale", 130794)]))
        self.assertEqual(page["kind"], "decline")
        self.assertTrue(page["message"].startswith("IPEDS has no values for this measure"))

    def test_both_after_options_runs_every_option(self):
        """Decision of 2026-11-23: "both" after the app has offered options resolves against those options."""
        base = req("schools", measures=[M("DRVADM.DVADM01")])
        state = {"pending": [dict(label="Yale University", request=dict(base, schools=[S("Yale", 130794)])),
                             dict(label="Harvard University", request=dict(base, schools=[S("Harvard", 166027)]))]}
        reply = dict(kind="choose", request=None, edit=None, options=[], chosen=[0, 1], decline=None)
        page = answer.ask("both", state, self.log, call=saved(reply))
        self.assertEqual(page["kind"], "many")                               # one answer per option chosen
        self.assertEqual([p["kind"] for p in page["pages"]], ["answer", "answer"])

    def test_a_breakdown_with_no_school_and_no_group_takes_the_default_group(self):
        """Part 5b2 Haiku run, conversation 62: a breakdown naming no school and no group stopped with an error."""
        page = self.run_request(req("breakdown", measures=[M("DRVEF.ENRTOT")], breakdown=dict(set="By gender", fixed=[])))
        self.assertIn(page["kind"], ("answer", "decline"))                   # never an error

    def test_what_data_exists_for_a_retired_variable(self):
        page = self.run_request(req("data_exists", measures=[M("IC_PCCAMPUSES.CAMPUSID")], topic="branch campus IDs"))
        self.assertTrue(page["message"].startswith("IPEDS collected"))

    def test_retired_variables_rank_below_current_ones(self):
        short = shortlist.shortlist("branch campus locations listed on College Navigator", DB)
        kinds = [bool(m.get("retired")) for m in short["measures"]]
        self.assertIn(True, kinds)                                  # found, so never "not found" ...
        self.assertLessEqual(sum(kinds), shortlist.RETIRED)          # ... at most two ...
        self.assertEqual(kinds, sorted(kinds))                       # ... and all after the current measures


def Y(**parts):
    y = rq.no_year()
    y.update(parts)
    return y


class Trends(unittest.TestCase):
    """Part 5c: a school, several schools or a group over time, with the trend rules decided in Part 5b."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.log = Log(cls.dir.name)
        cls.db = sqlite3.connect(DB)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.dir.cleanup()

    def run_request(self, request, state=None):
        return answer.run_direct(request, {} if state is None else state, self.log, DB, question="[test]")

    def column(self, page, i=2):
        return [row[i] for row in page["table"]["rows"]]

    # ---- choosing the years
    def test_years_are_chosen_by_the_period_each_figure_covers(self):
        from path.trend import choose
        years = list(range(2015, 2025))
        self.assertEqual(choose(Y(start=2015), "Fall {Y}", years), years)
        self.assertEqual(choose(Y(start=2020), "Fall {Y}", years), list(range(2020, 2025)))
        self.assertEqual(choose(Y(last=5), "Fall {Y}", years), list(range(2020, 2025)))
        self.assertEqual(choose(Y(start=2016, end=2018), "Fall {Y}", years), [2016, 2017, 2018])
        self.assertEqual(choose(Y(start=2015, end=2024, change=True), "Fall {Y}", years), [2015, 2024])
        # aid figures cover the year before their release: 2018 reaches back to the 2017-18 aid year (2018 release)
        self.assertEqual(choose(Y(start=2018), "July 1, {Y-1} - June 30, {Y}", years)[0], 2018)
        self.assertEqual(choose(Y(start=2030), "Fall {Y}", years), [])

    def test_entering_cohorts_are_matched_by_cohort(self):
        """Log 4.3: "cohorts 2009 through 2018" for the bachelor's six-year rate are the 2015 to 2024 releases (fall -6,
        year_meaning.csv entering_cohort), and each row names its cohort."""
        page = self.run_request(req("schools", measures=[M("DRVGR.GBA6RTT")], schools=[S("Yale", 130794)],
                                    year=Y(stated="2009 through 2018", kind="entering cohort", start=2009, end=2018)))
        rows = page["table"]["rows"]
        self.assertEqual([r[0][:7] for r in rows], [f"{y}-{(y + 1) % 100:02d}" for y in range(2015, 2025)])
        self.assertEqual(rows[0][1], "students who entered in fall 2009, status as of August 31, 2015")
        self.assertIn("fall 2009", page["interpreted"])
        self.assertIn("fall 2018", page["interpreted"])

    def test_a_rate_computed_from_counts_over_time(self):
        """Log 58.7: a rate with no table of its own (core expenses per FTE student, counts from DRVF and DRVEF12)
        crashed the break notes. Each year divides that year's counts, and the breaks of the counts' tables apply."""
        page = self.run_request(req("schools", measures=[M("rate:Core expenses per FTE student")],
                                    schools=[S("RIT", 195003), S("WPI", 168421)], year=Y(stated="ten years", last=10)))
        self.assertEqual(page["kind"], "answer")
        self.assertEqual(len(page["table"]["rows"]), 10)
        self.assertTrue(all(c.startswith("$") for r in page["table"]["rows"] for c in r[2:]), page["table"]["rows"][:2])

    def test_earlier_codes_are_read_through_same_as(self):
        """Graduate students are EFFYALEV 12 from 2020-21 and EFFYLEV 4 before (category_codes.csv same_as)."""
        from path.trend import year_rows
        self.assertEqual(year_rows(self.db, "EFFY", {"EFFYALEV": "12"}, 2024), {"EFFYALEV": "12"})
        self.assertEqual(year_rows(self.db, "EFFY", {"EFFYALEV": "12"}, 2017), {"EFFYLEV": "4"})
        self.assertIsNone(year_rows(self.db, "EFFY", {"EFFYALEV": "3"}, 2017))     # no such row before 2020-21

    # ---- the owner's two test questions
    def test_yale_pell_since_2015_has_all_ten_years(self):
        """o50: the all-undergraduate Pell measure, the trend default, covers all ten releases."""
        page = self.run_request(req("schools", measures=[M("SFA.UPGRNTP")], schools=[S("Yale", 130794)],
                                    year=Y(stated="since 2015", start=2015)))
        self.assertEqual(page["kind"], "answer")
        self.assertEqual(page["table"]["columns"][:2], ["Year", "Period"])
        self.assertEqual(len(page["table"]["rows"]), 10)
        self.assertNotIn("not collected", self.column(page))
        latest = self.db.execute("SELECT UPGRNTP FROM SFA WHERE UNITID = 130794 AND year = 2024").fetchone()[0]
        self.assertEqual(self.column(page)[-1], show.fmt((latest, "percent")))
        self.assertEqual(page["chart"]["kind"], "line")
        self.assertIn("releases 2015-16 to 2024-25", page["data_release"])

    def test_degree_seeking_pell_starts_in_its_own_first_year(self):
        """o50: the degree-seeking split starts in the 2022-23 release; the earlier years are named as not collected,
        never zero, and never filled from the all-undergraduate measure."""
        page = self.run_request(req("schools", measures=[M("SFA.UDGPGRNTP")], schools=[S("Front Range", 127200)],
                                    year=Y(stated="since 2015", start=2015)))
        values = self.column(page)
        self.assertEqual(values[:7], ["not collected"] * 7)
        self.assertTrue(all(v.endswith("%") for v in values[7:]), values)
        self.assertIn("IPEDS did not collect", " ".join(page["notes"]))
        self.assertIn("2015-16 to 2021-22", " ".join(page["notes"]))
        self.assertEqual(len(page["table"]["columns"]), 3)                   # one measure, never mixed

    # ---- groups
    def test_group_counts_each_years_own_schools_and_offers_todays(self):
        state = {}
        page = self.run_request(req("group", measures=[M("DRVEF.ENRTOT")], groups=["State: Connecticut"],
                                    year=Y(stated="2015 to 2024", start=2015, end=2024, change=True)), state)
        self.assertIn("belonged to it that year", page["interpreted"])
        self.assertEqual(page["offers"], ["Today's schools only"])
        each = self.column(page)
        today = answer.take_offer(0, state, self.log, DB)
        self.assertIn("only the schools that belong to it today", today["interpreted"])
        self.assertEqual(self.column(today)[1], each[1])                     # 2024-25: the same schools
        self.assertNotEqual(self.column(today)[0], each[0])                  # 2015-16: schools that closed or merged
        self.assertEqual(page["table"]["rows"][-1][0], "Change")

    def test_group_counts_match_each_years_own_membership(self):
        page = self.run_request(req("group", measures=[M("DRVEF.ENRTOT")], groups=["State: Connecticut"],
                                    year=Y(stated="2016 to 2017", start=2016, end=2017)))
        for y, shown in zip((2016, 2017), self.column(page)):
            total = self.db.execute("SELECT SUM(e.ENRTOT) FROM DRVEF e WHERE e.year = ? AND e.UNITID IN (SELECT unitid FROM "
                                    "group_membership WHERE year = ? AND group_name = 'State: Connecticut') AND e.UNITID IN "
                                    "(SELECT unitid FROM group_membership g WHERE year = ? AND group_name = "
                                    "(SELECT condition FROM dict_terms WHERE term = 'national universe' AND is_default = 'yes'))",
                                    (y, y, y)).fetchone()[0]
            self.assertEqual(shown, show.fmt((total, "count")))

    def test_national_retention_trend_matches_nces(self):
        """A rate computed from counts, year by year, matches the NCES Trend Generator figures (rates_by_year.csv)."""
        import csv
        with open(Path(__file__).resolve().parents[1] / "docs" / "reports" / "stage5b" / "rates_by_year.csv", encoding="utf-8") as f:
            nces = {int(r["release_year"]): float(r["nces"]) for r in csv.DictReader(f)
                    if r["rate"] == "Full-time retention rate" and not r["applies_to"] and r["status"] == "match"}
        page = self.run_request(req("group", measures=[M("EFD.RET_PCF")], year=Y(stated="since 2015", start=2015)))
        got = dict(zip([int(r[0][:4]) for r in page["table"]["rows"]], self.column(page)))
        self.assertGreaterEqual(len(nces), 5)
        for y, figure in nces.items():
            self.assertAlmostEqual(float(got[y].rstrip("%")), figure, delta=0.051, msg=y)

    def test_peers_are_todays_comparison_group_in_every_year(self):
        page = self.run_request(req("school_vs_group", measures=[M("COST2_NETPRICE.NPGRN2")], schools=[S("Yale", 130794)],
                                    peers_of=130794, year=Y(stated="since 2020", start=2020)))
        self.assertIn("today's comparison group, used for every year", page["interpreted"])
        self.assertEqual(page["offers"], [])
        self.assertEqual(len(page["table"]["columns"]), 4)                   # Year, Period, Yale, its peers

    # ---- gaps, breaks and notes
    def test_pandemic_note_goes_by_the_period_a_figure_covers(self):
        page = self.run_request(req("schools", measures=[M("DRVEF.ENRTOT")], schools=[S("Yale", 130794)],
                                    year=Y(stated="since 2019", start=2019)))
        marked = {r[0].split()[0]: "*" in r[0] for r in page["table"]["rows"]}
        self.assertEqual(marked, {"2019-20": False, "2020-21": True, "2021-22": True, "2022-23": False, "2023-24": False,
                                  "2024-25": False})                         # fall 2020 and fall 2021 only
        self.assertTrue(any("pandemic" in n for n in page["notes"]))

    def test_a_break_is_noted_only_when_the_trend_crosses_it(self):
        crossing = self.run_request(req("schools", measures=[M("DRVEF12.E12GRAD")], schools=[S("Yale", 130794)],
                                        year=Y(stated="2018 to 2021", start=2018, end=2021)))
        self.assertTrue(any("12-month enrollment" in n for n in crossing["notes"]), crossing["notes"])
        after = self.run_request(req("schools", measures=[M("DRVEF12.E12GRAD")], schools=[S("Yale", 130794)],
                                     year=Y(stated="the last two years", last=2)))
        self.assertFalse(any("12-month enrollment" in n for n in after["notes"]), after["notes"])

    def test_graduate_headcount_before_2020_comes_from_the_detailed_table(self):
        page = self.run_request(req("schools", measures=[M("DRVEF12.E12GRAD")], schools=[S("Yale", 130794)],
                                    year=Y(stated="since 2015", start=2015)))
        self.assertNotIn("not collected", self.column(page))
        detail = [n for n in page["notes"] if "detailed table" in n]
        self.assertEqual(len(detail), 1)
        self.assertIn("2015-16 to 2019-20", detail[0])
        graduate_2017 = self.db.execute("SELECT EFYTOTLT FROM EFFY WHERE UNITID = 130794 AND year = 2017 AND EFFYLEV = 4").fetchone()[0]
        self.assertEqual(self.column(page)[2], show.fmt((graduate_2017, "count")))

    def test_a_retired_measure_is_read_in_the_years_ipeds_collected_it(self):
        page = self.run_request(req("schools", measures=[M("IC_PCCAMPUSES.CAMPUSID")], schools=[S("Yale", 130794)],
                                    year=Y(stated="since 2015", start=2015)))
        self.assertEqual(page["kind"], "answer")
        self.assertIn("IPEDS collected", page["interpreted"])
        self.assertEqual(self.column(page)[-1], "not collected")             # a gap, never zero
        self.assertNotIn("0", self.column(page))

    def test_school_names_today_with_earlier_names_and_mergers(self):
        page = self.run_request(req("schools", measures=[M("DRVEF.ENRTOT")], schools=[S("ASU", 104151)],
                                    year=Y(stated="since 2015", start=2015)))
        self.assertEqual(page["table"]["columns"][2], "Arizona State University Campus Immersion")
        self.assertTrue(any("(then: Arizona State University-Tempe" in n for n in page["notes"]), page["notes"])
        page = self.run_request(req("schools", measures=[M("DRVEF.ENRTOT")], schools=[S("Lyme", 129686)],
                                    year=Y(stated="since 2015", start=2015)))
        self.assertIn("Lyme Academy College of Fine Arts merged into University of New Haven in 2016-17.", page["notes"])

    def test_change_between_two_years_in_points_and_percent(self):
        page = self.run_request(req("schools", measures=[M("SFA.UPGRNTP"), M("DRVEF.ENRTOT")], schools=[S("Yale", 130794)],
                                    year=Y(stated="2015 to 2024", start=2015, end=2024, change=True)))
        change = page["table"]["rows"][-1]
        self.assertEqual(change[0], "Change")
        self.assertRegex(change[2], r"^[+-]\d+\.\d points$")
        self.assertRegex(change[3], r"^[+-][\d,]+ \([+-]\d+\.\d%\)$")

    def test_breakdown_over_time_and_a_year_without_it(self):
        page = self.run_request(req("breakdown", measures=[M("EFFY.EFYTOTLT")], schools=[S("Yale", 130794)],
                                    breakdown=dict(set="By race and ethnicity", fixed=[]), year=Y(stated="since 2022", start=2022)))
        self.assertEqual(page["table"]["columns"][-1], "Total")
        self.assertTrue(all(r[-1] != "no value" for r in page["table"]["rows"]))
        # a year whose breakdown check failed: the total only, with the message (the real data has no such year for a
        # set loaded today, so the check's answer is replaced for one year)
        from path import fetch, resolve, trend

        class OneYearFails:
            def __init__(self, db):
                self.db = db

            def execute(self, sql, args=()):
                if "FROM year_checks" in sql and args[2] == 2023:
                    return self.db.execute("SELECT 'failed'")
                return self.db.execute(sql, args)

        d = resolve.Dictionary(self.db, DB)
        out = resolve.resolve_request(req("breakdown", measures=[M("EFFY.EFYTOTLT")], schools=[S("Yale", 130794)],
                                          breakdown=dict(set="By race and ethnicity", fixed=[]),
                                          year=Y(stated="since 2022", start=2022)), d, None)
        result = fetch.fetch(out["plan"], OneYearFails(self.db))
        row_2023 = next(r for r in result["rows"] if r[0].startswith("2023-24"))
        self.assertTrue(all(c == "not collected" for c in row_2023[2:-1]), row_2023)
        self.assertIsNotNone(row_2023[-1])
        self.assertTrue(any(n.startswith('The breakdown "By race and ethnicity" isn\'t available for 2023-24') and
                            n.endswith("The total is shown.") for n in result["notes"]), result["notes"])

    def test_questions_a_trend_cannot_answer_yet_are_declined_with_the_latest_year_offered(self):
        page = self.run_request(req("rank", measures=[M("DRVEF.ENRTOT")], groups=["State: Connecticut"],
                                    year=Y(stated="since 2018", start=2018)))
        self.assertEqual(page["kind"], "decline")
        self.assertIn("over several years", page["message"])
        self.assertIn("the latest year", page["message"])

    def test_a_follow_up_changes_the_period(self):
        first = req("schools", measures=[M("DRVEF.ENRTOT")], schools=[S("Yale", 130794)], year=Y(stated="since 2015", start=2015))
        edited = rq.apply_edit(first, dict(changes=[dict(field="year", action="replace")],
                                           values=dict(rq.empty(), year=Y(stated="the last three years", last=3))), [first])
        page = self.run_request(edited)
        self.assertEqual([r[0][:7] for r in page["table"]["rows"]], ["2022-23", "2023-24", "2024-25"])
        self.assertEqual(edited["schools"], first["schools"])

    def test_the_trend_fields_come_through_from_the_model(self):
        y = rq.year_from_wire({"stated": "since 2015", "start": 2015, "kind": None})
        self.assertTrue(rq.is_trend(y))
        self.assertEqual((y["end"], y["last"], y["change"], y["membership"]), (None, None, False, None))
        self.assertFalse(rq.is_trend(rq.year_from_wire({"stated": "2023-24"})))
        year = rq.REPLY_SCHEMA["properties"]["requests"]["items"]["properties"]["year"]["properties"]
        for field in ("span", "start", "end", "last", "membership"):     # no nullable trend fields: with them the API
            self.assertNotIn("anyOf", year[field])                      # refused the reply shape as too large
        self.assertIsNone(rq.year_from_wire({"start": 0, "end": 0, "last": 0})["start"])
        one = rq.year_from_wire({"stated": "2022-23", "span": "one year", "start": 2022, "end": 2023, "last": 0})
        self.assertFalse(rq.is_trend(one))                                   # a single year, even with years written
        since = rq.year_from_wire({"span": "from a year on", "start": 2015, "end": 2024})
        self.assertEqual((since["start"], since["end"]), (2015, None))
        self.assertTrue(rq.year_from_wire({"span": "the change between two years", "start": 2015, "end": 2024})["change"])

    def test_a_single_year_question_is_unchanged(self):
        page = self.run_request(req("schools", measures=[M("DRVEF.ENRTOT")], schools=[S("Yale", 130794), S("Harvard", 166027)]))
        self.assertEqual(page["table"]["columns"][0], "School")
        self.assertEqual(page["chart"]["kind"], "bar")                       # a comparison: bars
        self.assertEqual(len(page["chart"]["points"]), 2)


if __name__ == "__main__":
    unittest.main()
