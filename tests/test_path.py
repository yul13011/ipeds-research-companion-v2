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
        flags = [m["set_up"] for m in s["measures"]]
        self.assertLessEqual(flags.count(False), shortlist.NOT_SET_UP)
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
        cls.db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

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
        self.assertIn("one IPEDS release", page["message"])
        last = json.loads((Path(self.dir.name) / "declines.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(last["missing"], "years")

    def test_average_with_no_rate_row_is_declined_for_a_group(self):
        page, _ = self.ask("Average federal loan at private colleges",
                           reply_request(req("group", measures=[M("SFA.UFLOANA")], groups=["Private not-for-profit"])))
        self.assertEqual(page["kind"], "decline")
        self.assertIn("list or rank each school's figure", page["message"])

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
        self.assertEqual((page["kind"], page["message"]), ("decline", "IPEDS has no flag for this group."))

    def test_data_exists_yes_and_not_set_up(self):
        page, _ = self.ask("Do you have data on admission rates?",
                           reply_request(req("data_exists", measures=[M("DRVADM.DVADM01")], topic="admission rates")))
        self.assertTrue(page["message"].startswith("Yes."))
        page, _ = self.ask("Do you have data on calendar systems?",
                           reply_request(req("data_exists", measures=[M("IC.CALSYS")], topic="calendar systems")))
        self.assertTrue(page["message"].startswith("IPEDS collects this, but it is not set up"))

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
        grand = self.v("SELECT COUNT(*) FROM dict_measures WHERE in_first_version='yes' AND title='Grand total' AND plain_name IS NULL")
        self.assertEqual(grand, 0)

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
        db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
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
        cls.db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
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

    def test_shortlist_shows_category_columns(self):
        s = shortlist.shortlist("How many full-time and part-time instructional staff did Yale have in Fall 2024?", DB)
        staff = next(m for m in s["measures"] if m["id"] == "S_OC.HRTOTLT")
        self.assertEqual(staff["categories"][0]["column"].upper(), "STAFFCAT")
        text, _ = interpret.render(s, None, None, "q")
        self.assertIn("categories by STAFFCAT (default: Grand Total)", text)


class Show(unittest.TestCase):
    def test_formats(self):
        self.assertEqual([show.fmt(c) for c in [(5, "percent"), (77.86, "percent"), (5300.4, "average"), (20066904, "count"),
                                                 (14, "ratio"), None]], ["5%", "77.9%", "$5,300", "20,066,904", "14", "no value"])


if __name__ == "__main__":
    unittest.main()
