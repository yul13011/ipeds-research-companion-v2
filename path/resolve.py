"""Step 4, Resolve and check. Code only.

Turns the model's reply into one of these outcomes:
    ready         a plan that fetch can run
    clarify       a question with option buttons; each option is a complete request
    picker        a school name the user needs to choose
    decline       the app cannot do this; says what was missing (logged)
    wrong_reading the model named something that was not on its shortlist (logged)
    failure       no usable reply from the model (logged)

Every rule comes from a dictionary table: term readings and defaults, default rows, rate rows,
breakdown sets, school groups and settings. Nothing here reads the user's wording.
"""
import copy
import json
import re

from path import shortlist as sl
from path import trend
from path.request import apply_edit, fill_years, is_trend, used_ids

CLOSEST_MATCHES = 3                 # how many of the best shortlisted measures a "not found" answer names


class Dictionary:
    """Read-only lookups into the dictionary tables and the directory, for one question."""

    def __init__(self, db, db_path):
        self.db, self.db_path = db, db_path
        self.year = db.execute("SELECT MAX(year) FROM directory").fetchone()[0]

    def q(self, sql, *args):
        return self.db.execute(sql, args).fetchall()

    def one(self, sql, *args):
        rows = self.q(sql, *args)
        return rows[0] if rows else None

    def setting(self, term, reading=None):
        sql = "SELECT condition, statement FROM dict_terms WHERE kind='setting' AND term=? AND "
        row = self.one(sql + "reading=?", term, reading) if reading else self.one(sql + "is_default='yes'", term)
        return row or (None, None)

    def members(self, group):
        return {u for (u,) in self.q("SELECT unitid FROM group_membership WHERE group_name=? AND year=?", group, self.year)}

    def name(self, unitid):
        """Today's name; for a school no longer in IPEDS, its last name."""
        row = self.one("SELECT INSTNM FROM directory WHERE UNITID=? AND year<=? ORDER BY year DESC", unitid, self.year)
        return row[0] if row else str(unitid)


def first_present(*layers):
    """The precedence rule. A value can come from several places; the first layer that has it wins:
        1. what the user stated (the request itself)
        2. a reading the user chose for a term
        3. values already decided, carried over when a summary measure switches to its detailed one
        4. a dictionary default, which only fills what is still empty
    Each layer is {key: value}. Every place in resolve that merges values uses this function."""
    out = {}
    for layer in layers:
        for key, value in (layer or {}).items():
            out.setdefault(key.upper() if isinstance(key, str) else key, value)
    return out


def rows_of(m):
    return {p["column"].upper(): p["code"] for p in m.get("row") or []}


def as_row(layer):
    return [dict(column=k, code=str(v)) for k, v in layer.items()]


def outcome(kind, **parts):
    return dict(kind=kind, **parts)


class _Blank(dict):
    def __missing__(self, key):
        return ""


def say(d, key, **fields):
    """A message to the user, written from the "message" rows of terms.csv."""
    return (d.setting("message", key)[1] or "").format_map(_Blank(fields)).strip()


def decline(d, key, request=None, wanted="", closest=None, pointer=None, log=None, **fields):
    """A decline, by kind (`key`, a "message" row). `closest` is {"text", "request"}: an alternative built from the
    request in hand, offered after the message and stored for "what can you show instead?". The model's own words,
    if any, go to `log` and are never shown."""
    message = say(d, key, **fields)
    if pointer:
        message += " " + say(d, "not collected source", pointer=pointer)
    if closest and closest.get("text"):
        message += " " + say(d, "instead", closest=closest["text"])
    return outcome("decline", message=message, missing=key, request=request, wanted=wanted, closest=closest,
                   pointer=pointer, reason=message, log=log)


def retired(d, measure_id):
    """For a variable IPEDS no longer collects: {first, last, after} for the "retired" messages (release years, and the
    successor sentence), from measure_years and the approved rows of measure_history.csv. None if it is still collected."""
    years = [y for (y,) in d.q("SELECT year FROM measure_years WHERE measure = ? ORDER BY year", measure_id)]
    if not years or years[-1] >= d.year:
        return None
    then = lambda y: f"{y}-{(y + 1) % 100:02d}"
    successor = d.one("SELECT m.shown_name, h.status FROM dict_measure_history h JOIN dict_measures m "
                      "ON m.\"table\" || '.' || m.variable = h.measure WHERE "
                      "UPPER(h.earlier_table || '.' || h.earlier_variable) = UPPER(?) AND h.status <> 'rejected' "
                      "ORDER BY h.status = 'in use' DESC", measure_id)   # a rejected match is no successor
    if successor and successor[1] != "in use":          # a successor waiting for the owner's review: say neither
        after = ""
    else:
        after = say(d, "retired replaced", successor=successor[0]) if successor else say(d, "retired gone")
    one = " one year" if years[0] == years[-1] else ""   # the message for a single release
    return dict(first=then(years[0]), last=then(years[-1]), after=after, one=one)


def label_of(request, d, names):
    """How a request's measures are named in a message: the reading the user chose, or the measures themselves."""
    for r in request.get("readings") or []:
        row = d.one("SELECT COUNT(*) FROM dict_terms WHERE term=? AND reading=? AND kind='measure'", r["term"], r["reading"])
        if row and row[0] > 1:
            return r["reading"].lower()
    names = list(dict.fromkeys(names))
    if len(names) <= 2:
        return " and ".join(names)
    return f"{names[0]} and {len(names) - 1} other figures"


def without(request, **changes):
    r = copy.deepcopy(request)
    r.update(changes)
    return r


def closest_matches(short):
    names = [m["name"] for m in (short or {}).get("measures", []) if m.get("set_up")][:CLOSEST_MATCHES]
    return "; ".join(names)


def model_decline(reply, short, d):
    """A decline from the model. The kind decides the message; the model's own explanation goes to the log only.
    "IPEDS does not collect this" needs an outside-IPEDS row; any other "not in IPEDS" becomes "not found"."""
    x, request = reply["decline"], reply.get("request")
    log = dict(reason=x.get("reason"), wanted=x.get("wanted"), closest=x.get("closest"), missing=x.get("missing"))
    missing = x.get("missing")
    if request and missing == "years" and request["measures"]:
        got = resolve_request(request, d, short)        # the app's own year check: answers what it can, or says why not
        return dict(got, log=log) if got["kind"] != "ready" else got
    if request and missing == "measure" and request["measures"] and all(
            (d.one("SELECT in_first_version FROM dict_measures WHERE \"table\" || '.' || variable = ?", m["id"]) or ("",))[0] != "yes"
            for m in request["measures"] if not m["id"].startswith("rate:")):
        got = resolve_request(request, d, short)        # every measure it found is collected but not set up
        if got["kind"] == "decline":
            return dict(got, log=log)
    topic = (request or {}).get("topic")
    outside = d.one("SELECT what_to_say, pointer FROM dict_outside_ipeds WHERE topic=?", topic) if topic else None
    if outside and request["measures"] and request["operation"] not in ("define", "data_exists"):
        got = resolve_request(request, d, short)        # the outside row covers only its part: answer the rest
        if got["kind"] == "ready":
            return dict(got, log=log)
    if outside:
        return decline(d, "not collected", request, say=outside[0], pointer=outside[1], log=log)
    if request and missing == "group" and request["groups"]:
        got = resolve_request(request, d, short)        # the group's own entry says why it is not available
        if got["kind"] == "decline":
            return dict(got, log=log)
        if request["measures"]:
            return decline(d, "group", request, log=log, closest=dict(text="the same figure for all U.S. schools",
                                                                      request=without(request, groups=[])))
    if request and missing == "breakdown" and request["breakdown"] and request["measures"]:
        return decline(d, "breakdown", request, log=log, closest=dict(text="the figure without the breakdown",
                                                                      request=without(request, breakdown=None)))
    if missing in ("calculation", "not a data question", "other"):
        return decline(d, missing, request, log=log)
    if missing == "years":
        return decline(d, "other", request, log=log)
    matches = closest_matches(short)                    # measure, not in IPEDS without an outside row, anything else
    message_closest = dict(text=None, matches=matches)
    out = decline(d, "not found", request, log=log, closest=message_closest)
    if matches:
        out["message"] += " " + say(d, "closest matches", matches=matches)
    out["search_miss"] = True
    return out


def resolve(reply, short, state, db, db_path):
    """`state` holds the conversation: "history" (earlier requests, oldest first) and "pending" (options shown)."""
    d = Dictionary(db, db_path)
    if reply is None:
        return outcome("failure", message=say(d, "could not read"))
    if reply.get("unknown_tags"):                       # a tag that was not on this question's shortlist
        return outcome("wrong_reading", message=say(d, "could not read"), detail={"tags not on the shortlist": reply["unknown_tags"]})
    kind = reply["kind"]
    if kind == "decline":
        bad = off_shortlist(reply["request"], short) if reply.get("request") else None
        if bad:
            return outcome("wrong_reading", message=say(d, "could not read"), detail=bad)
        return model_decline(reply, short, d)
    if kind == "about_decline":                         # "why not?", "where can I find that?", "what can you show instead?"
        return about_decline(reply, state, d)
    if kind == "choose":
        pending = state.get("pending") or []
        picked = [pending[i]["request"] for i in reply["chosen"] if 0 <= i < len(pending)]
        if not picked:
            return outcome("wrong_reading", message=say(d, "which option"), detail="choose")
        results = [resolve_request(r, d, None) for r in picked]       # options were checked when they were shown
        return results[0] if len(results) == 1 else outcome("many", outcomes=results)
    if kind == "options":
        good = [o for o in reply["options"] if not off_shortlist(o["request"], short)]
        if not good:
            return outcome("wrong_reading", message=say(d, "could not read"), detail=off_shortlist(reply["options"][0]["request"], short))
        return outcome("clarify", question="Which did you mean?", options=good)
    request = reply["request"]
    if kind == "edit" and state.get("pending"):        # a change made while options are open applies to every option
        options = []
        for o in state["pending"]:
            changed = apply_edit(o["request"], reply["edit"], [o["request"]])
            year = changed["year"]["stated"] if changed["year"] != o["request"]["year"] else None
            options.append(dict(label=o["label"] + (f" ({year})" if year else ""), request=changed))
        return outcome("clarify", question=say(d, "which did you mean"), options=options)
    if kind == "edit":
        history = state.get("history") or []
        if not history:
            return outcome("wrong_reading", message=say(d, "nothing to change"), detail="edit")
        request = apply_edit(history[-1], reply["edit"], history)    # the shortlist carries the previous request's items
    out = resolve_request(request, d, short, new_question=kind == "request")
    if out["kind"] == "clarify" and "request" not in out:
        out["request"] = request                        # kept as the previous request while the question is open
    return out


def about_decline(reply, state, d):
    """A question about the last decline, answered from what was stored with it."""
    last = state.get("last_decline")
    about = (reply.get("decline") or {}).get("about") or "why"
    if not last:
        return outcome("about", message=say(d, "why none"))
    if about == "where":
        return outcome("about", message=say(d, "not collected source", pointer=last["pointer"]) if last.get("pointer")
                       else say(d, "where none"))
    if about == "instead":
        closest = last.get("closest") or {}
        if closest.get("request"):
            return dict(resolve_request(closest["request"], d, None), instead=say(d, "instead", closest=closest["text"]))
        if closest.get("matches"):
            return outcome("about", message=say(d, "closest matches", matches=closest["matches"]))
        return outcome("about", message=say(d, "instead none"))
    return outcome("about", message=last["message"])


def off_shortlist(request, short):
    """Whatever the request names that was not on the shortlist shown to the model, or None."""
    if short is None:
        return None
    have, used = sl.ids(short), used_ids(request)
    bad = {k: sorted(map(str, used[k] - have[k])) for k in used if used[k] - have[k]}
    return bad or None


def resolve_request(request, d, short, new_question=False):
    """Check one request against the shortlist and the dictionary, and build the plan."""
    bad = off_shortlist(request, short)
    if bad:
        return outcome("wrong_reading", message=say(d, "could not read"), detail=bad, request=request)
    for i, s in enumerate(request["schools"]):
        if s["id"] is None:
            return outcome("picker", name=s["name"], index=i, request=request, candidates=sl.search_schools(s["name"], d.db_path))
    ask = state_or_school(request, d) if new_question else None
    if ask:
        return ask
    request = copy.deepcopy(request)
    op = request["operation"]
    plan = dict(operation=op, request=request, measures=[], schools=[dict(id=s["id"], name=d.name(s["id"])) for s in request["schools"]],
                members=None, scope=None, conditions=[], breakdown=None, split=None, sort=None, guard=None,
                statements=[], caveats=[], word_notes=[], topic=None, small_cohort=None)
    if op in ("define", "data_exists"):
        return topic_plan(plan, request, d, short)
    stop = apply_readings(request, d, plan)              # 1 and 2: stated values, then chosen readings
    if stop:
        return stop
    if request["breakdown"]:
        switch_to_detail(request, d, plan)              # 3: carries over every row, level and reading decided
    for step in (scope, level_defaults):                # 4: defaults fill what is still empty
        stop = step(request, d, plan)
        if stop:
            return stop
    not_set_up, no_years, gone = [], [], []
    for m in request["measures"]:
        got = measure(m, d, request["year"], trend=is_trend(request["year"]))
        if got["kind"] == "need_row":
            return row_question(request, m, got)
        if got["kind"] == "not_set_up":
            not_set_up.append(got)
            continue
        if got["kind"] == "retired":
            gone.append(got)
            continue
        if got["kind"] == "row_choice":                 # a category column named as the figure
            if any(x["id"] != m["id"] and x["id"].partition(".")[0] == got["table"] for x in request["measures"]):
                continue                                # a figure of the same table is named too: it is the answer
            return figure_question(request, m, got, d)
        if got["kind"] != "ready":
            return dict(got, request=request)
        if got["measure"]["years"]["held"] is False:
            no_years.append(got["measure"])
            continue
        plan["measures"].append(got["measure"])
        gone_too = got["measure"].get("retired")       # in a trend: read in the years IPEDS collected it, and say so
        if gone_too:
            plan["statements"].append(say(d, "retired" + gone_too["one"], what=got["measure"]["name"],
                                          **{k: v for k, v in gone_too.items() if k != "one"}))
        for said in got["measure"].get("row_statements", []):
            if said not in plan["statements"]:
                plan["statements"].append(said)
    if not plan["measures"] and no_years:               # none of the years asked for is held
        names = label_of(request, d, [m["name"] for m in no_years])
        held = "; ".join(dict.fromkeys(m["period"] for m in no_years))
        return decline(d, "years", request, wanted=request["year"]["stated"], what=names, held=held,
                       asked=request["year"]["stated"],
                       closest=dict(text=f"{names} for {held}", request=without(request, year=dict(stated=None, kind="latest"))))
    if not plan["measures"] and gone and not not_set_up:
        first = gone[0]
        return decline(d, "retired" + first["one"], request, wanted=first["id"], what=first["name"], first=first["first"],
                       last=first["last"], after=first["after"])
    for got in gone:                                    # answer the rest, and say what is left out
        plan["statements"].append(say(d, "retired partly" + got["one"], what=got["name"], first=got["first"],
                                      last=got["last"], after=got["after"]))
    if not plan["measures"] and not_set_up:
        first = not_set_up[0]
        near = first.get("closest")
        closest = dict(text=near["text"], request=without(request, measures=[dict(id=near["measure"], row=[])])) if near else None
        return decline(d, "not set up", request, wanted=first["id"], what=first["name"], closest=closest)
    for got in not_set_up:                              # answer the rest, and say what is left out
        plan["statements"].append(say(d, "not set up partly", what=got["name"]))
    if no_years:
        plan["statements"].append(say(d, "years", what=label_of(request, d, [m["name"] for m in no_years]),
                                      held="; ".join(dict.fromkeys(m["period"] for m in no_years)), asked=request["year"]["stated"]))
    partly = [m for m in plan["measures"] if m["years"]["missing"]]
    if partly:
        missing = sorted({y for m in partly for y in m["years"]["missing"]})
        plan["statements"].append(say(d, "years partly", what=label_of(request, d, [m["name"] for m in partly]),
                                      held="; ".join(dict.fromkeys(m["period"] for m in partly)),
                                      missing=", ".join(missing), verb="is" if len(missing) == 1 else "are"))
    pair_measures(plan, d, request["year"])
    for c in request["conditions"]:
        got = measure({"id": c["measure"], "row": []}, d, None)
        if got["kind"] != "ready":
            return dict(got, request=request)
        condition, row = paired(got["measure"], d, request["year"])   # one measure per kind of school, as for figures
        if row is not None:
            pair_statements(plan, d, condition)
        for part in condition.get("parts") or [condition]:          # each measure's own statements (the pension note)
            for said in part.get("row_statements", []):
                if said not in plan["statements"]:
                    plan["statements"].append(said)
        same = [x for x in plan["conditions"] if x["measure"]["id"] == condition["id"] and x["comparison"] == c["comparison"]
                and x["value"] == c["value"]]
        if not same:                                    # one condition per form, paired into one, is one condition
            plan["conditions"].append(dict(measure=condition, comparison=c["comparison"], value=c["value"]))
    covered = plan["members"] if plan["members"] is not None else {s["id"] for s in plan["schools"]}
    for m in plan["measures"] + [c["measure"] for c in plan["conditions"]]:
        m["period"] = cohort_period(m, covered, d) or m["period"]
    op = request["operation"]                          # a chosen reading may have changed it (split by level)
    if not plan["measures"] and op not in ("count_schools", "list"):
        return decline(d, "no measure", request)
    if op == "schools" and not plan["schools"]:
        return decline(d, "no school", request)
    if op == "school_vs_group" and (not plan["schools"] or plan["members"] is None):
        return decline(d, "needs a comparison group", request)

    if request["breakdown"]:
        stop = breakdown(request, plan, d)
        if stop:
            return stop
    elif op == "breakdown":
        return decline(d, "no breakdown", request)
    if op in ("group", "split", "school_vs_group") or (op == "breakdown" and plan["members"] is not None):
        stop = group_method(plan, d)
        if stop:
            return stop
    elif op in ("schools", "rank", "list") and any(m.get("form") for m in plan["measures"]) and \
            (op != "schools" or len(plan["schools"]) > 1):   # schools compared on finance lines: the forms differ
        said = d.setting("different reporting forms")[1]
        if said not in plan["statements"]:
            plan["statements"].append(said)
    if op == "split":
        reading = request["split_by"] or d.one("SELECT reading FROM dict_terms WHERE term='split by' AND is_default='yes'")[0]
        column, statement = d.setting("split by", reading)
        plan["split"] = column.partition(".")[2]
        plan["statements"].append(statement)
    if op == "rank":
        rank_plan(request, plan, d)
    if op == "school_vs_group" and plan["measures"][0]["rates"]:
        threshold = int(re.findall(r"\d+", d.setting("ranking guard")[0])[0])
        plan["small_cohort"] = dict(threshold=threshold, text=d.setting("small cohort")[1])
    plan["campus_notes"] = dict(d.q("SELECT condition, statement FROM dict_terms WHERE term='related campus'"))
    if is_trend(request["year"]):                       # over several years: choose them, and how a group counts schools
        if op not in trend.OPERATIONS or (op == "breakdown" and len(plan["schools"]) > 1):
            return decline(d, "trend operation", request, closest=dict(
                text=say(d, "trend operation instead"), request=without(request, year=dict(request["year"], start=None,
                                                                                           end=None, last=None, change=False))))
        stop = trend.plan(request, plan, d, lambda key, **f: say(d, key, **f))
        if stop:
            return stop
    outside = d.one("SELECT what_to_say, pointer FROM dict_outside_ipeds WHERE topic=?", request["topic"]) \
        if request.get("topic") else None
    if outside:                                         # a part of the question IPEDS lacks, named beside the answer
        plan["statements"].append(say(d, "not collected partly", say=outside[0]) +
                                  (" " + say(d, "not collected source", pointer=outside[1]) if outside[1] else ""))
    return outcome("ready", plan=plan, request=request)


SCHOOL_OPTIONS = 3


def state_or_school(request, d):
    """A name that is both a state and a school ("Michigan"): ask which, as the "state or school" setting says.
    Asked for a new question whose only group is a state, with no school named, when a school is called by the
    state's name: the setting's condition lists those name patterns ("University of {state}"). Not asked when the
    question counts or lists schools, which only a group can answer."""
    if request["schools"] or len(request["groups"]) != 1 or \
            request["operation"] in ("count_schools", "list", "define", "data_exists"):
        return None
    group = request["groups"][0]
    row = d.one("SELECT parent, statement FROM group_list WHERE group_name=?", group)
    condition, question = d.setting("state or school")
    if not row or row[0] != "State" or not question:
        return None
    state = group.partition(": ")[2]
    found = []
    for pattern in (p.strip() for p in (condition or "").split(";") if p.strip()):
        name = pattern.format(state=state)
        for u, n in d.q("SELECT UNITID, INSTNM FROM directory WHERE year = ? AND (INSTNM = ? OR INSTNM LIKE ?) ORDER BY INSTNM",
                        d.year, name, name + "-%"):
            if u not in {f["id"] for f in found}:
                found.append(dict(id=u, name=n))
    found = found[:SCHOOL_OPTIONS]
    if not found:
        return None
    options = [dict(label=row[1] or group, request=request)]
    for s in found:
        r = copy.deepcopy(request)
        r["groups"], r["schools"] = [], [dict(name=s["name"], id=s["id"])]
        if r["operation"] in ("group", "split"):
            r["operation"] = "schools"
        options.append(dict(label=s["name"], request=r))
    return outcome("clarify", question=question.format(state=state), options=options)


def paired(m, d, year):
    """The measure, or (when a term reading names one measure per kind of school, terms.csv applies_to) one measure
    made of those parts, each school taking the part that applies to it. Returns (measure, the reading or None)."""
    row = d.one("SELECT term, reading FROM dict_terms WHERE measure=? AND COALESCE(applies_to, '') <> '' "
                "AND status='in use' ORDER BY rowid", m["id"])
    if not row:
        return m, None
    parts = []
    for mid, applies, shown in d.q("SELECT measure, applies_to, shown_as FROM dict_terms WHERE term=? AND reading=? "
                                   "AND COALESCE(applies_to, '') <> '' AND status='in use' ORDER BY rowid", *row):
        got = dict(kind="ready", measure=m) if mid == m["id"] else measure({"id": mid, "row": []}, d, year)
        if got["kind"] == "ready":
            parts.append(dict(got["measure"], applies_to=applies, members=d.members(applies), shown_as=shown))
    if len(parts) < 2:
        return m, None
    return dict(parts[0], name=parts[0]["shown_as"] or parts[0]["name"], parts=parts,
                rates=[r for p in parts for r in p["rates"]]), row


def pair_statements(plan, d, m):
    """The statements for a measure made of parts: the kinds of school it covers, and, when the parts are lines of
    different finance forms, the reporting-forms statement (the measures are not strictly comparable)."""
    covered = plan["members"] if plan["members"] is not None else {s["id"] for s in plan["schools"]}
    kinds = [p["applies_to"] for p in m["parts"] if p["members"] & covered]
    said = [d.setting("kind of school", "Measure by kind of school")[1]] if len(kinds) > 1 else []
    said = [s.format(kinds=", ".join(p["applies_to"] for p in m["parts"])) for s in said if s]
    if len({p.get("form") for p in m["parts"] if p.get("form")}) > 1:
        said.append(d.setting("different reporting forms")[1])
    for s in said:
        if s not in plan["statements"]:
            plan["statements"].append(s)


def pair_measures(plan, d, year):
    """Each measure that a term reading pairs by kind of school becomes one measure of parts (see paired); a group
    with more than one kind is shown separately for each."""
    out, done = [], set()
    for m in plan["measures"]:
        new, row = paired(m, d, year)
        if row is None:
            out.append(m)
            continue
        if row in done:
            continue
        done.add(row)
        out.append(new)
        pair_statements(plan, d, new)
    plan["measures"] = out


def cohort_rule(m, covered, d):
    """The entering-cohort rule for a measure, as (kind, offset from the release year): the measure's own, otherwise its
    table's, for the first school level the schools cover (year_meaning.csv entering_cohort). None if it has none."""
    own = d.one("SELECT entering_cohort FROM dict_measures WHERE \"table\" || '.' || variable = ?", m["id"])
    table_rule = d.one('SELECT entering_cohort FROM dict_year_meaning WHERE "table"=?', m.get("period_table"))
    rule = (own and own[0]) or (table_rule and table_rule[0])
    if not rule:
        return None
    parts = [p.strip().partition(" for ") for p in rule.split(";")]
    pick = next((t for t, _, g in parts if not g or covered & d.members(g)), parts[0][0])
    kind, offset = pick.rsplit(" ", 1)
    return kind, int(offset)


def cohort_period(m, covered, d, year=None):
    """'students who entered in fall 2018, status as of August 31, 2024', from offsets to the release year.

    The measure's own entering_cohort wins; otherwise the table's, which may differ by school level.
    Where the schools asked about span levels, each cohort is named with its level. `year`: the release year (default
    the latest), for a trend."""
    year_ = year or d.year
    own = d.one('SELECT entering_cohort FROM dict_measures WHERE "table" || \'.\' || variable = ?', m["id"])
    table_rule = d.one('SELECT entering_cohort, period FROM dict_year_meaning WHERE "table"=?', m["period_table"])
    rule = (own and own[0]) or (table_rule and table_rule[0])
    if not rule:
        return None
    cohorts = []
    for part in rule.split(";"):
        text, _, group = part.strip().partition(" for ")
        kind, offset = text.rsplit(" ", 1)
        entered = year_ + int(offset)
        label = f"fall {entered}" if kind == "fall" else f"{entered}-{str(entered + 1)[2:]}"
        if not group or covered & d.members(group):
            cohorts.append((label, group))
    if not cohorts:
        return None
    named = cohorts[0][0] if len(cohorts) == 1 or len({c for c, _ in cohorts}) == 1 else \
        " or ".join(f"{c} ({g.lower()} schools)" for c, g in dict.fromkeys(cohorts))
    status = fill_years(table_rule[1], year_)
    status = status[0].lower() + status[1:] if status else ""
    status = status.replace("status of student as of", "status as of")
    return d.setting("cohort period")[1].format(cohort=named, status=status)


def supports(d, measure_id, set_name):
    table, _, column = measure_id.partition(".")
    return d.one("SELECT 1 FROM breakdown_sets WHERE set_name=? AND \"table\"=? AND status IN ('loaded', 'additive') AND "
                 "((stored_as='rows' AND measure=?) OR (stored_as='columns' AND total=?))", set_name, table, column, column)


def switch_to_detail(request, d, plan):
    """A breakdown asked for on a summary measure with no breakdown of its own uses the measure's detailed equivalent
    (measures.csv, detailed_measure), and says so."""
    for m in request["measures"]:
        if supports(d, m["id"], request["breakdown"]["set"]):
            continue
        link = d.one("SELECT detailed, rows FROM detail_links WHERE measure=? AND status='loaded'", m["id"])
        if not link:
            continue
        detailed, rows = link[0], json.loads(link[1])
        table = detailed.partition(".")[0]
        labels = [label for k, v in rows.items() for (label,) in
                  d.q('SELECT label FROM dict_category_codes WHERE in_latest = \'yes\' AND "table"=? AND UPPER("column")=UPPER(?) AND code=? AND '
                      '"default" IS NULL', table, k, str(v))]
        names = dict(d.q('SELECT "table" || \'.\' || variable, shown_name FROM dict_measures '
                         'WHERE "table" || \'.\' || variable IN (?, ?)', m["id"], detailed))
        plan["statements"].append(d.setting("detailed measure")[1].format(
            summary=names.get(m["id"], m["id"]), detailed=", ".join([names.get(detailed, detailed)] + labels)))
        for unitid, summary, value in d.q("SELECT unitid, summary, detailed FROM detail_link_exceptions WHERE measure=?", m["id"]):
            if unitid in {s["id"] for s in request["schools"]}:
                plan["caveats"].append(d.setting("detail differs")[1].format(
                    school=d.name(unitid), summary=f"{summary:,.0f}", detailed="no row" if value is None else f"{value:,.0f}"))
        m["id"], m["row"] = detailed, as_row(first_present(rows_of(m), rows))


def topic_plan(plan, request, d, short=None):
    """define and data_exists: which of the three answers applies is decided by the dictionary."""
    found = []
    for m in request["measures"]:
        row = d.one('SELECT m."table", m.variable, m.shown_name, m.long_description, m.in_first_version, '
                    'm.unit, COALESCE(m.period, y.period) FROM dict_measures m JOIN dict_year_meaning y ON y."table" = m."table" '
                    'WHERE m."table" || \'.\' || m.variable = ?', m["id"])
        if row:
            found.append(dict(zip(("table", "variable", "name", "definition", "set_up", "unit", "period"), row)))
            found[-1]["period"] = fill_years(found[-1]["period"], d.year)
            gone = retired(d, m["id"])
            if gone:                                    # data that existed is never "not found"
                found[-1]["retired"] = say(d, "retired" + gone["one"], what=found[-1]["name"], **gone)
    outside = d.one("SELECT topic, what_to_say, pointer FROM dict_outside_ipeds WHERE topic=?", request["topic"] or "")
    plan["topic"] = dict(asked=request["topic"], measures=found,
                         outside=dict(zip(("topic", "say", "pointer"), outside)) if outside else None)
    if not found and not outside:                       # nothing matched: "not found", never "IPEDS does not collect"
        matches = closest_matches(short)
        plan["topic"]["not_found"] = say(d, "not found topic", topic=request["topic"] or "that") + \
            (" " + say(d, "closest matches", matches=matches) if matches else "")
        plan["search_miss"] = True
    elif outside:
        plan["topic"]["say"] = say(d, "not collected", say=outside[1]) + \
            (" " + say(d, "not collected source", pointer=outside[2]) if outside[2] else "")
    return outcome("ready", plan=plan, request=request)


# ---------------------------------------------------------------- terms
def term_readings(d, term):
    return d.q("SELECT reading, kind, measure, condition, is_default, default_for, always_ask, statement, shown_as "
               "FROM dict_terms WHERE term=? AND status='in use' ORDER BY rowid", term)


def with_reading(request, d, term, reading):
    """A copy of the request with one term reading applied."""
    r = copy.deepcopy(request)
    rows = [x for x in term_readings(d, term) if x[0] == reading]
    measures = [dict(id=x[2], row=row_from(x[3])) for x in rows if x[1] == "measure" and x[2]]
    if measures:
        r["measures"] = measures
    for x in rows:
        if x[1] == "group" and x[2] and (x[3] or "")[:1] in "<>":     # a cut-off, such as admission rate < 25
            comparison, value = x[3].split()
            r["conditions"].append(dict(measure=x[2], comparison=comparison, value=value))
    r["readings"] = [y for y in r["readings"] if y["term"] != term] + [dict(term=term, reading=reading)]
    return r


def row_from(condition):
    """'EAPCAT = 21000' -> [{"column": "EAPCAT", "code": "21000"}]."""
    if condition and "=" in condition and condition[:1] not in "<>":
        column, _, code = condition.partition("=")
        return [dict(column=column.strip(), code=code.strip())]
    return []


def fill_reading(request, d, term, reading):
    """Apply a chosen reading under the precedence rule: a measure the user stated wins over the reading's, and the
    reading only fills rows and measures that are still empty."""
    rows = term_readings(d, term)
    picked = [x for x in rows if x[0] == reading]
    offered = {x[2]: row_from(x[3]) for x in picked if x[1] == "measure" and x[2]}
    in_term = {x[2] for x in rows if x[2]}
    stated = {m["id"]: m for m in request["measures"]}
    if offered and stated.keys() & offered.keys():      # the reading covers a stated measure: merge, stated rows first
        merged = [dict(id=mid, row=as_row(first_present(rows_of(stated.get(mid, {})), rows_of({"row": extra}))))
                  for mid, extra in offered.items()]
        request["measures"] = merged + [m for m in request["measures"] if m["id"] not in offered]
    elif offered and not stated.keys() & in_term:       # no measure of this term stated yet: the reading fills it
        request["measures"] += [dict(id=mid, row=extra) for mid, extra in offered.items()]
    for x in picked:                                    # a cut-off, such as admission rate < 25, adds a condition
        if x[1] == "group" and x[2] and (x[3] or "")[:1] in "<>":
            comparison, value = x[3].split()
            condition = dict(measure=x[2], comparison=comparison, value=value)
            if condition not in request["conditions"]:
                request["conditions"].append(condition)


def apply_readings(request, d, plan):
    """Apply the readings the user chose; ask where a measure term must ask; collect each term's statement."""
    for chosen in list(request["readings"]):
        fill_reading(request, d, chosen["term"], chosen["reading"])
    done = {r["term"] for r in request["readings"]}
    for m in request["measures"]:
        for (term,) in d.q("SELECT DISTINCT term FROM dict_terms WHERE measure=? AND kind='measure' AND status='in use'", m["id"]):
            rows = term_readings(d, term)
            if term not in done and any(x[6] == "yes" for x in rows):
                readings = list(dict.fromkeys(x[0] for x in rows if x[1] == "measure"))
                return outcome("clarify", question=f'"{term}" can mean different things. Which did you mean?',
                               options=[dict(label=r, request=with_reading(request, d, term, r)) for r in readings])
            statement = rows[0][7]
            when = d.one("SELECT statement_when FROM dict_terms WHERE term=? AND kind='measure' LIMIT 1", term)
            if when and when[0] == "chosen" and term not in done:
                statement = None                        # shown only when the model chose this term's reading
            if statement and statement not in plan["statements"]:
                plan["statements"].append(statement)
            shown = {x[2]: x[8] for x in rows if x[2]}
            m["shown_as"] = shown.get(m["id"])
    return None


def level_defaults(request, d, plan):
    """A term whose default depends on the school, such as graduation rate by level: use it, or ask when schools mix."""
    named = {s["id"] for s in request["schools"]}
    covered = named if named and plan.get("group_defaulted") else \
        plan["members"] if plan["members"] is not None else named
    chosen = {r["term"] for r in request["readings"]}
    for m in request["measures"]:
        for (term,) in d.q("SELECT DISTINCT term FROM dict_terms WHERE measure=? AND default_for IS NOT NULL", m["id"]):
            if term in chosen:
                continue
            rows = term_readings(d, term)
            fits = {}
            for x in rows:
                if x[4] == "yes" and x[5] and x[1] == "measure":
                    inside = covered & d.members(x[5])
                    if inside:
                        fits.setdefault(x[2], set()).update(inside)
            if len(fits) == 1:
                m["id"] = next(iter(fits))
            elif len(fits) > 1:
                mixed = [x[0] for x in rows if x[6] == "mixed levels"]
                return outcome("clarify", question=f'These schools are of more than one level, and "{term}" differs by level. '
                               "Which do you want?", options=[dict(label=r, request=with_reading(request, d, term, r)) for r in mixed])
    return None


# ---------------------------------------------------------------- which schools
def scope(request, d, plan):
    """The schools a question covers: named groups, peers, or the national universe."""
    names = list(request["groups"])
    for r in request["readings"]:                       # a chosen reading that narrows or splits the group
        row = d.one("SELECT default_for, condition FROM dict_terms WHERE term=? AND reading=? AND kind='group'", r["term"], r["reading"])
        if row and row[1] == "only this group" and row[0]:
            names.append(row[0])
        elif row and row[1] == "split by level":
            request["operation"], request["split_by"] = "split", "level"
            plan["operation"] = "split"
    for name in list(names):                            # a group defined per school (its own comparison group) is "its peers"
        if d.one("SELECT kind FROM group_list WHERE group_name=?", name) == ("per school",):
            names.remove(name)
            if request["peers_of"] is None and request["schools"]:
                request["peers_of"] = request["schools"][0]["id"]
    if request["peers_of"] is not None:
        stop = peers(request, d, plan)
        if stop:
            return stop
    if not names and plan["members"] is None and (request["operation"] == "schools" or
                                                  (request["operation"] == "breakdown" and request["schools"])):
        return None                                     # named schools only: no group figure; a breakdown with no
                                                        # school and no group takes the default group, as any group figure
    chosen = next((r["reading"] for r in request["readings"] if r["term"] == "national universe"), None)
    universe, universe_statement = d.setting("national universe", chosen) if chosen else d.setting("national universe")
    if not names and plan["members"] is None:
        names = [d.setting("no group stated")[0]]
        plan["statements"].append(d.setting("no group stated")[1])
        plan["group_defaulted"] = True
    plan["group_names"] = list(names) + ([universe] if universe != "all" and universe not in names else [])
    members, parts = None, []
    for name in names:
        row = d.one("SELECT statement, caveat, status, word_note FROM group_list WHERE group_name=?", name)
        if row is None:
            return decline(d, "unknown group", request, what=name)
        statement, caveat, status, note = row
        if status == "decline":
            national = dict(text="the same figure for all U.S. schools",
                            request=without(request, groups=[g for g in request["groups"] if g != name]))
            return decline(d, "group not available", request, wanted=name, statement=statement,
                           closest=national if request["measures"] else None)
        found = d.members(name)
        members = found if members is None else members & found
        parts.append((statement or name).rstrip("."))
        if caveat:
            plan["caveats"].append(caveat)
        if note:
            plan["word_notes"].append(note)
    if members is not None:
        plan["members"] = members if plan["members"] is None else plan["members"] & members
    if universe != "all" and universe not in names:     # every group figure stays inside the national universe
        plan["members"] &= d.members(universe)
        plan["statements"].append(universe_statement)
    elif universe == "all":
        plan["statements"].append(universe_statement)
    plan["scope"] = "; ".join(([plan["scope"]] if plan["scope"] else []) + parts)
    return None


def peers(request, d, plan):
    """"Its peers": the school's own IPEDS comparison group by default; ask when it has none."""
    school = request["peers_of"]
    rows = d.q("SELECT reading, condition, is_default, statement FROM dict_terms WHERE term='peers' ORDER BY rowid")
    chosen = next((r["reading"] for r in request["readings"] if r["term"] == "peers"), None)
    has_group = school in d.members("Has an IPEDS comparison group")
    pick = next((x for x in rows if x[0] == chosen), None) or next((x for x in rows if x[2] == "yes" and has_group), None)
    if pick is None:
        others = [x[0] for x in rows if x[2] != "yes"]
        return outcome("clarify", question=f"{d.name(school)} has no IPEDS comparison group. Which schools should it be compared with?",
                       options=[dict(label=o, request=dict(copy.deepcopy(request), readings=request["readings"] +
                                                           [dict(term="peers", reading=o)])) for o in others])
    if pick[1] == "comparison group":
        plan["members"] = {u for (u,) in d.q("SELECT CGUNITID FROM CUSTOMCGIDS WHERE UNITID=? AND year=?", school, d.year)}
        plan["scope"] = f"{d.name(school)}'s own IPEDS comparison group ({len(plan['members'])} schools)"
        plan["statements"].append(pick[3])
        plan["peer_members"] = set(plan["members"])     # in a trend, today's comparison group for every year
    elif pick[1] == "same state and sector":
        state, sector = d.one("SELECT STABBR, SECTOR FROM directory WHERE UNITID=? AND year=?", school, d.year)
        plan["members"] = {u for (u,) in d.q("SELECT UNITID FROM directory WHERE year=? AND STABBR=? AND SECTOR=? AND UNITID<>?", d.year,
                                              state, sector, school)}
        plan["scope"] = f"schools in the same state and sector as {d.name(school)}"
        plan["peer_members"] = set(plan["members"])
    else:
        return decline(d, "needs a comparison group", request)
    if not plan["schools"]:
        plan["schools"] = [dict(id=school, name=d.name(school))]
    return None


# ---------------------------------------------------------------- measures
def measure(m, d, year, trend=False):
    """One measure: its table, column, rows, period, unit, form, and the rate rows behind it. In a trend (`trend`), a
    measure IPEDS no longer collects is still read for the years it was collected."""
    if m["id"].startswith("rate:"):
        name = m["id"][5:]
        numerator, unit = d.one("SELECT numerator, unit FROM dict_rates WHERE rate=?", name)
        info = dict(id=m["id"], name=name, table=None, column=None, rows={}, unit=unit or "computed from counts",
                    definition=name, source=None, own_period=None, form=None, period_table=numerator.partition(".")[0])
    else:
        row = d.one('SELECT "table", variable, shown_name, unit, reporting_form, in_first_version, '
                    'period, long_description, statement FROM dict_measures WHERE "table" || \'.\' || variable = ?', m["id"])
        if row is None:
            return decline(d, "not found")
        table, column, name, unit, form, set_up, own_period, definition, said = row
        if d.one('SELECT 1 FROM dict_category_codes WHERE "table" = ? AND UPPER("column") = UPPER(?) AND in_latest = \'yes\'',
                 table, column):                        # a category column picks rows; it is never the figure shown
            summable = [u.strip() for u in (d.setting("summable units")[0] or "").split(",")]
            figures = d.q('SELECT "table" || \'.\' || variable, shown_name FROM dict_measures WHERE "table" = ? '
                          f"AND in_first_version = 'yes' AND unit IN ({', '.join('?' * len(summable))}) ORDER BY rowid LIMIT 4",
                          table, *summable)
            return outcome("row_choice", id=m["id"], name=name, table=table, figures=figures)
        if not d.one("SELECT 1 FROM measure_years WHERE measure = ? AND n_values > 0", m["id"]):
            return decline(d, "no values", what=name)   # in no year has any school a value: never "not found" or zero
        gone = retired(d, m["id"])
        if gone and not trend:                          # IPEDS collected it once: say when, and what replaced it
            return outcome("retired", id=m["id"], name=name, **gone)
        if set_up != "yes":                             # the nearest set-up measure of the same table, as an alternative
            near = d.one('SELECT "table" || \'.\' || variable, shown_name FROM dict_measures '
                         'WHERE "table"=? AND in_first_version=\'yes\' ORDER BY rowid LIMIT 1', table)
            return outcome("not_set_up", id=m["id"], name=name,
                           closest=dict(text=near[1], request=None, measure=near[0]) if near else None)
        source = d.one("SELECT source_table FROM _tables WHERE local_table=? AND year<=? ORDER BY year DESC", table, d.year)[0]
        info = dict(id=m["id"], name=name, table=table, column=column, rows={}, unit=unit, form=form,
                    definition=definition, source=source, own_period=own_period, period_table=table)
        if gone:
            info["retired"] = gone
        if said:                                        # a measure's own statement, shown whenever it is used
            info.setdefault("row_statements", []).append(said)
        given = rows_of(m)
        info["given"] = given
        keys = d.q('SELECT "column", default_code, default_label FROM row_keys WHERE "table"=?', table) if not gone else \
            [(c, v, None) for c, v in given.items()]    # a table no longer collected has no row keys today: the rows asked for
        decided = first_present(given, {k: v for k, v, _ in keys if v is not None})
        for column_, default, _ in keys:
            code = decided.get(column_.upper())
            if code is None:
                options = d.q('SELECT code, label FROM dict_category_codes WHERE in_latest = \'yes\' AND "table"=? AND "column"=? ORDER BY rowid',
                              table, column_)
                return outcome("need_row", name=name, column=column_, options=options)
            info["rows"][column_] = code
            said = d.one('SELECT statement FROM dict_category_codes WHERE in_latest = \'yes\' AND "table"=? AND "column"=? AND code=?', table, column_, code)
            if said and said[0]:
                info.setdefault("row_statements", []).append(said[0])
            if code != default:                         # a row the user asked for is named in "Interpreted as"
                label = d.one('SELECT label FROM dict_category_codes WHERE in_latest = \'yes\' AND "table"=? AND "column"=? AND code=?', table, column_, code)
                info.setdefault("row_labels", []).append(label[0] if label else f"{column_} {code}")
    info["shown_as"] = m.get("shown_as")
    kind, period, caveat, flag = d.one('SELECT kind, period, caveat, parent_child_flag FROM dict_year_meaning WHERE "table"=?',
                                       info["period_table"])
    info.update(period=fill_years(info["own_period"] or period, d.year), period_pattern=info["own_period"] or period,
                period_kind=kind, caveat=caveat, rates=rate_rows(d, info),
                parent_child=[c.strip().partition(".")[2] for c in flag.split(";")] if flag else None)
    info["years"] = dict(held=True, missing=[])        # which of the years asked for are held
    if year and year.get("stated") and year.get("kind") != "latest" and not is_trend(year):
        stated = set(re.findall(r"(?:19|20)\d\d", year["stated"]))
        shown = set(re.findall(r"(?:19|20)\d\d", info["period"] or "")) | {str(d.year)}
        if not stated & shown:
            info["years"] = dict(held=False, missing=sorted(stated))
        elif not stated <= shown:
            info["years"] = dict(held=True, missing=sorted(stated - shown))
    return outcome("ready", measure=info)


def figure_question(request, m, got, d):
    """A category column was named as the figure: ask which figure of its table, keeping the rows asked for."""
    options = []
    for figure, label in got["figures"]:
        r = copy.deepcopy(request)
        for x in r["measures"]:                         # every use of the column, each with its own rows
            if x["id"] == m["id"]:
                x["id"] = figure
        options.append(dict(label=label, request=r))
    return outcome("clarify", question=say(d, "row choice", what=got["name"]), options=options)


def row_question(request, m, got):
    """Ask which category row, with each option a complete request."""
    options = []
    for code, label in got["options"][:12]:
        r = copy.deepcopy(request)
        target = next(x for x in r["measures"] if x["id"] == m["id"])
        target["row"] = [p for p in target["row"] if p["column"].upper() != got["column"].upper()] + [dict(column=got["column"], code=code)]
        options.append(dict(label=label, request=r))
    return outcome("clarify", question=f'"{got["name"]}" is reported by category. Which one?', options=options)


def rate_rows(d, info):
    """The counts behind a rate or average: one entry per rates.csv row."""
    by_name = info["id"].startswith("rate:")
    rows = d.q("SELECT rate, numerator, denominator, category_column, numerator_code, denominator_code, method, applies_to "
               "FROM dict_rates WHERE status NOT LIKE 'Pending%' AND " + ("rate=?" if by_name else "rate_measure=?"),
               info["name"] if by_name else info["id"])
    out = []
    for rate, num, den, cat, ncode, dcode, method, applies in rows:
        form = d.one('SELECT reporting_form FROM dict_measures WHERE "table" || \'.\' || variable = ?', num)
        out.append(dict(rate=rate, numerator=num, denominator=den, category=cat, numerator_code=ncode, denominator_code=dcode,
                        method=method, applies_to=applies, members=d.members(applies) if applies else None,
                        form=form[0] if form else None))
    return out


def group_method(plan, d):
    """How each measure becomes one figure for a group: a sum, or counts summed and then divided."""
    summable = {u.strip() for u in (d.setting("summable units")[0] or "").split(",")}
    forms_statement = d.setting("different reporting forms")[1]
    out = []
    for m in plan["measures"]:
        if m["rates"]:
            m["method"] = "rate"
            live = [r for r in m["rates"] if r["members"] is None or plan["members"] & r["members"]]
            m["rates"] = live or m["rates"]
            if len(live) > 1 and not m.get("parts"):    # a measure by kind of school already has its statement
                plan["statements"].append(forms_statement if any(r["form"] for r in live)
                                          else d.setting("kind of school", "Rate by kind of school")[1])
            out.append(m)
        elif m["unit"] in summable:
            m["method"] = "sum"
            out.append(m)
            if m["form"]:                               # the same concept on the other finance forms
                for (other,) in d.q("SELECT b.measure FROM dict_terms a JOIN dict_terms b ON a.term = b.term AND "
                                    "a.reading = b.reading AND a.shown_as = b.shown_as WHERE a.measure = ? AND b.measure <> ?",
                                    m["id"], m["id"]):
                    got = measure({"id": other, "row": []}, d, None)
                    if got["kind"] == "ready":
                        out.append(dict(got["measure"], method="sum"))
                if len(out) > 1 and forms_statement not in plan["statements"]:
                    plan["statements"].append(forms_statement)
        else:
            return decline(d, "calculation average", plan["request"], what=m["name"], unit=m["unit"] or "a value",
                           closest=dict(text="each school's figure, ranked",
                                        request=without(plan["request"], operation="rank", sort=None)))
        if m["caveat"] and m["caveat"] not in plan["caveats"]:
            plan["caveats"].append(m["caveat"])
    plan["measures"] = out
    return None


def breakdown(request, plan, d):
    """A named, tested breakdown set, at the fixed values the request asks for."""
    m, b = plan["measures"][0], request["breakdown"]
    row = d.one('SELECT stored_as, "column", total, fixed FROM breakdown_sets WHERE set_name=? AND "table"=? '
                "AND (measure=? OR stored_as='columns') AND status IN ('loaded', 'additive')", b["set"], m["table"], m["column"])
    if row is None:
        return decline(d, "breakdown not tested", request, set=b["set"], what=m["name"],
                       closest=dict(text=f"{m['name']} without the breakdown", request=without(request, breakdown=None)))
    stored_as, column, total, fixed = row
    parts = d.q('SELECT part, label FROM breakdown_parts WHERE set_name=? AND "table"=?', b["set"], m["table"])
    info = dict(set=b["set"], stored_as=stored_as, column=column, total=total, parts=parts, fixed={})
    if stored_as == "rows":
        defaults = {k.strip().upper(): v.strip() for k, _, v in (x.partition("=") for x in (fixed or "").split(";")) if k.strip()}
        stated = {p["column"].upper(): p["code"] for p in b["fixed"]}
        decided = {k: v for k, v in m.get("given", {}).items() if k != column.upper()}
        layered = first_present(stated, decided, defaults)
        info["fixed"] = {k: str(layered[k]) for k in list(defaults) + [k for k in stated if k not in defaults]}
        if info["fixed"]:
            where = "; ".join(f"{k} = {v}" for k, v in info["fixed"].items())
            ok = d.one('SELECT status FROM breakdown_slices WHERE set_name=? AND "table"=? AND measure=? AND slice=?',
                       b["set"], m["table"], m["column"], where)
            if not ok or ok[0] != "loaded":
                return decline(d, "breakdown does not add up", request, set=b["set"], where=where)
        for key in list(m["rows"]):                     # the set's own column and fixed columns replace the defaults
            if key.upper() == column.upper() or key.upper() in info["fixed"]:
                del m["rows"][key]
    info["fixed_labels"] = [label for k, v in info["fixed"].items() for (label,) in
                            d.q('SELECT label FROM dict_category_codes WHERE in_latest = \'yes\' AND "table"=? AND UPPER("column")=? AND code=?',
                                m["table"], k, v)]
    plan["breakdown"] = info
    return None


def rank_plan(request, plan, d):
    limit = (request["sort"] or {}).get("limit")
    if not limit:
        number, statement = d.setting("top with no number")
        limit = int(number)
        plan["statements"].append(statement)
    plan["sort"] = dict(order=(request["sort"] or {}).get("order") or "highest", limit=limit)
    if plan["measures"][0]["rates"]:
        chosen = next((r["reading"] for r in request["readings"] if r["term"] == "ranking guard"), None)
        condition, statement = d.setting("ranking guard", chosen) if chosen else d.setting("ranking guard")
        plan["guard"] = int(re.findall(r"\d+", condition)[0])
        plan["statements"].append(statement)
    plan["statements"].append("Schools with no value, or a value of zero or below, are left out of the ranking.")
    plan["empty_ranking"] = d.setting("empty ranking")[1]
