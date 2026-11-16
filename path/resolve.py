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
import re

from path import shortlist as sl
from path.request import apply_edit, used_ids

WRONG = "Sorry, I could not read that question reliably. Could you ask it another way?"


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
        row = self.one("SELECT INSTNM FROM directory WHERE UNITID=?", unitid)
        return row[0] if row else str(unitid)


def outcome(kind, **parts):
    return dict(kind=kind, **parts)


def decline(message, missing, request=None, wanted="", closest=""):
    if closest and closest not in message:
        message += f" The closest thing I can do: {closest}."
    return outcome("decline", message=message, missing=missing, request=request, wanted=wanted, closest=closest)


def resolve(reply, short, state, db, db_path):
    """`state` holds the conversation: "history" (earlier requests, oldest first) and "pending" (options shown)."""
    d = Dictionary(db, db_path)
    if reply is None:
        return outcome("failure", message="Sorry, I could not read that question. Please try asking it another way.")
    kind = reply["kind"]
    if kind == "decline":
        x = reply["decline"]
        return decline(x["reason"], x["missing"], wanted=x["wanted"], closest=x["closest"])
    if kind == "choose":
        pending = state.get("pending") or []
        picked = [pending[i]["request"] for i in reply["chosen"] if 0 <= i < len(pending)]
        if not picked:
            return outcome("wrong_reading", message="Sorry, I could not tell which option you meant.", detail="choose")
        results = [resolve_request(r, d, None) for r in picked]       # options were checked when they were shown
        return results[0] if len(results) == 1 else outcome("many", outcomes=results)
    if kind == "options":
        good = [o for o in reply["options"] if not off_shortlist(o["request"], short)]
        if not good:
            return outcome("wrong_reading", message=WRONG, detail=off_shortlist(reply["options"][0]["request"], short))
        return outcome("clarify", question="Which did you mean?", options=good)
    request = reply["request"]
    if kind == "edit":
        history = state.get("history") or []
        if not history:
            return outcome("wrong_reading", message="There is no earlier question to change.", detail="edit")
        request = apply_edit(history[-1], reply["edit"], history)    # the shortlist carries the previous request's items
    return resolve_request(request, d, short)


def off_shortlist(request, short):
    """Whatever the request names that was not on the shortlist shown to the model, or None."""
    if short is None:
        return None
    have, used = sl.ids(short), used_ids(request)
    bad = {k: sorted(map(str, used[k] - have[k])) for k in used if used[k] - have[k]}
    return bad or None


def resolve_request(request, d, short):
    """Check one request against the shortlist and the dictionary, and build the plan."""
    bad = off_shortlist(request, short)
    if bad:
        return outcome("wrong_reading", message=WRONG, detail=bad, request=request)
    for i, s in enumerate(request["schools"]):
        if s["id"] is None:
            return outcome("picker", name=s["name"], index=i, request=request, candidates=sl.search_schools(s["name"], d.db_path))
    request = copy.deepcopy(request)
    op = request["operation"]
    plan = dict(operation=op, request=request, measures=[], schools=[dict(id=s["id"], name=d.name(s["id"])) for s in request["schools"]],
                members=None, scope=None, conditions=[], breakdown=None, split=None, sort=None, guard=None,
                statements=[], caveats=[], word_notes=[], topic=None, small_cohort=None)
    if op in ("define", "data_exists"):
        return topic_plan(plan, request, d)

    for step in (apply_readings, scope, level_defaults):
        stop = step(request, d, plan)
        if stop:
            return stop
    for m in request["measures"]:
        got = measure(m, d, request["year"])
        if got["kind"] == "need_row":
            return row_question(request, m, got)
        if got["kind"] != "ready":
            return dict(got, request=request)
        plan["measures"].append(got["measure"])
    for c in request["conditions"]:
        got = measure({"id": c["measure"], "row": []}, d, None)
        if got["kind"] != "ready":
            return dict(got, request=request)
        plan["conditions"].append(dict(measure=got["measure"], comparison=c["comparison"], value=c["value"]))
    covered = plan["members"] if plan["members"] is not None else {s["id"] for s in plan["schools"]}
    for m in plan["measures"] + [c["measure"] for c in plan["conditions"]]:
        m["period"] = cohort_period(m, covered, d) or m["period"]
    op = request["operation"]                          # a chosen reading may have changed it (split by level)
    if not plan["measures"] and op not in ("count_schools", "list"):
        return decline("The question did not name a measure the app has.", "measure", request)
    if op == "schools" and not plan["schools"]:
        return decline("The question did not name a school.", "group", request)
    if op == "school_vs_group" and (not plan["schools"] or plan["members"] is None):
        return decline("A comparison needs one school and a group: its peers, or a named group.", "group", request)

    if request["breakdown"]:
        stop = breakdown(request, plan, d)
        if stop:
            return stop
    elif op == "breakdown":
        return decline("The question did not name a breakdown.", "breakdown", request)
    if op in ("group", "split", "school_vs_group") or (op == "breakdown" and plan["members"] is not None):
        stop = group_method(plan, d)
        if stop:
            return stop
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
    return outcome("ready", plan=plan, request=request)


def cohort_period(m, covered, d):
    """'students who entered in fall 2018, status as of August 31, 2024', from offsets to the release year.

    The measure's own entering_cohort wins; otherwise the table's, which may differ by school level.
    Where the schools asked about span levels, each cohort is named with its level."""
    own = d.one('SELECT entering_cohort FROM dict_measures WHERE "table" || \'.\' || variable = ?', m["id"])
    table_rule = d.one('SELECT entering_cohort, period FROM dict_year_meaning WHERE "table"=?', m["period_table"])
    rule = (own and own[0]) or (table_rule and table_rule[0])
    if not rule:
        return None
    cohorts = []
    for part in rule.split(";"):
        text, _, group = part.strip().partition(" for ")
        kind, offset = text.rsplit(" ", 1)
        year = d.year + int(offset)
        label = f"fall {year}" if kind == "fall" else f"{year}-{str(year + 1)[2:]}"
        if not group or covered & d.members(group):
            cohorts.append((label, group))
    if not cohorts:
        return None
    named = cohorts[0][0] if len(cohorts) == 1 or len({c for c, _ in cohorts}) == 1 else \
        " or ".join(f"{c} ({g.lower()} schools)" for c, g in dict.fromkeys(cohorts))
    status = table_rule[1]
    status = status[0].lower() + status[1:] if status else ""
    status = status.replace("status of student as of", "status as of")
    return d.setting("cohort period")[1].format(cohort=named, status=status)


def topic_plan(plan, request, d):
    """define and data_exists: which of the three answers applies is decided by the dictionary."""
    found = []
    for m in request["measures"]:
        row = d.one('SELECT m."table", m.variable, COALESCE(m.plain_name, m.title), m.long_description, m.in_first_version, '
                    'm.unit, COALESCE(m.period, y.period) FROM dict_measures m JOIN dict_year_meaning y ON y."table" = m."table" '
                    'WHERE m."table" || \'.\' || m.variable = ?', m["id"])
        if row:
            found.append(dict(zip(("table", "variable", "name", "definition", "set_up", "unit", "period"), row)))
    outside = d.one("SELECT topic, what_to_say, pointer FROM dict_outside_ipeds WHERE topic=?", request["topic"] or "")
    plan["topic"] = dict(asked=request["topic"], measures=found,
                         outside=dict(zip(("topic", "say", "pointer"), outside)) if outside else None)
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


def apply_readings(request, d, plan):
    """Apply the readings the user chose; ask where a measure term must ask; collect each term's statement."""
    for chosen in list(request["readings"]):
        if any(x[1] == "measure" or (x[1] == "group" and (x[3] or "")[:1] in "<>")
               for x in term_readings(d, chosen["term"]) if x[0] == chosen["reading"]):
            request.update(with_reading(request, d, chosen["term"], chosen["reading"]))
    done = {r["term"] for r in request["readings"]}
    for m in request["measures"]:
        for (term,) in d.q("SELECT DISTINCT term FROM dict_terms WHERE measure=? AND kind='measure' AND status='in use'", m["id"]):
            rows = term_readings(d, term)
            if term not in done and any(x[6] == "yes" for x in rows):
                readings = list(dict.fromkeys(x[0] for x in rows if x[1] == "measure"))
                return outcome("clarify", question=f'"{term}" can mean different things. Which did you mean?',
                               options=[dict(label=r, request=with_reading(request, d, term, r)) for r in readings])
            statement = rows[0][7]
            if statement and statement not in plan["statements"]:
                plan["statements"].append(statement)
            shown = {x[2]: x[8] for x in rows if x[2]}
            m["shown_as"] = shown.get(m["id"])
    return None


def level_defaults(request, d, plan):
    """A term whose default depends on the school, such as graduation rate by level: use it, or ask when schools mix."""
    covered = plan["members"] if plan["members"] is not None else {s["id"] for s in request["schools"]}
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
    if request["peers_of"] is not None:
        stop = peers(request, d, plan)
        if stop:
            return stop
    if not names and plan["members"] is None and request["operation"] in ("schools", "breakdown"):
        return None                                     # named schools only: no group figure
    chosen = next((r["reading"] for r in request["readings"] if r["term"] == "national universe"), None)
    universe, universe_statement = d.setting("national universe", chosen) if chosen else d.setting("national universe")
    if not names and plan["members"] is None:
        names = [d.setting("no group stated")[0]]
        plan["statements"].append(d.setting("no group stated")[1])
    members, parts = None, []
    for name in names:
        row = d.one("SELECT statement, caveat, status, word_note FROM group_list WHERE group_name=?", name)
        if row is None:
            return decline(f'"{name}" is not a group the app knows.', "group", request)
        statement, caveat, status, note = row
        if status == "decline":
            return decline(statement, "group", request, wanted=name)
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
    elif pick[1] == "same state and sector":
        state, sector = d.one("SELECT STABBR, SECTOR FROM directory WHERE UNITID=?", school)
        plan["members"] = {u for (u,) in d.q("SELECT UNITID FROM directory WHERE STABBR=? AND SECTOR=? AND UNITID<>?",
                                              state, sector, school)}
        plan["scope"] = f"schools in the same state and sector as {d.name(school)}"
    else:
        return decline("Name the schools to compare with, and ask again.", "group", request)
    if not plan["schools"]:
        plan["schools"] = [dict(id=school, name=d.name(school))]
    return None


# ---------------------------------------------------------------- measures
def measure(m, d, year):
    """One measure: its table, column, rows, period, unit, form, and the rate rows behind it."""
    if m["id"].startswith("rate:"):
        name = m["id"][5:]
        numerator = d.one("SELECT numerator FROM dict_rates WHERE rate=?", name)[0]
        info = dict(id=m["id"], name=name, table=None, column=None, rows={}, unit="computed from counts",
                    definition=name, source=None, own_period=None, form=None, period_table=numerator.partition(".")[0])
    else:
        row = d.one('SELECT "table", variable, COALESCE(plain_name, title), unit, reporting_form, in_first_version, '
                    'period, long_description FROM dict_measures WHERE "table" || \'.\' || variable = ?', m["id"])
        if row is None:
            return decline(f"{m['id']} is not a measure in the dictionary.", "measure")
        table, column, name, unit, form, set_up, own_period, definition = row
        if set_up != "yes":
            return decline(f'IPEDS collects "{name}", but it is not set up in this app yet.', "measure", wanted=m["id"])
        source = d.one("SELECT source_table FROM _tables WHERE local_table=? AND year=?", table, d.year)[0]
        info = dict(id=m["id"], name=name, table=table, column=column, rows={}, unit=unit, form=form,
                    definition=definition, source=source, own_period=own_period, period_table=table)
        given = {p["column"].upper(): p["code"] for p in m["row"]}
        for column_, default, _ in d.q('SELECT "column", default_code, default_label FROM row_keys WHERE "table"=?', table):
            code = given.get(column_.upper(), default)
            if code is None:
                options = d.q('SELECT code, label FROM dict_category_codes WHERE "table"=? AND "column"=? ORDER BY rowid',
                              table, column_)
                return outcome("need_row", name=name, column=column_, options=options)
            info["rows"][column_] = code
            if code != default:                         # a row the user asked for is named in "Interpreted as"
                label = d.one('SELECT label FROM dict_category_codes WHERE "table"=? AND "column"=? AND code=?', table, column_, code)
                info.setdefault("row_labels", []).append(label[0] if label else f"{column_} {code}")
    info["shown_as"] = m.get("shown_as")
    kind, period, caveat = d.one('SELECT kind, period, caveat FROM dict_year_meaning WHERE "table"=?', info["period_table"])
    info.update(period=info["own_period"] or period, period_kind=kind, caveat=caveat, rates=rate_rows(d, info))
    if year and year.get("stated"):
        stated = set(re.findall(r"(?:19|20)\d\d", year["stated"]))
        shown = set(re.findall(r"(?:19|20)\d\d", info["period"] or "")) | {str(d.year)}
        if not stated or len(stated) > 2 or not stated <= shown:
            return decline(f"This first version holds one IPEDS release: {info['name']} is for {info['period']}. "
                           f"It cannot show {year['stated']}.", "years", wanted=year["stated"])
    return outcome("ready", measure=info)


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
            if len(live) > 1:
                plan["statements"].append(forms_statement if any(r["form"] for r in live)
                                          else "Shown separately for each kind of school the rate is defined for.")
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
            return decline(f'"{m["name"]}" is reported as {m["unit"] or "a value"} for each school, and the dictionary has no '
                           "counts to combine it across schools.", "calculation", plan["request"],
                           closest="list or rank each school's figure")
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
        return decline(f'There is no tested breakdown "{b["set"]}" for {m["name"]}.', "breakdown", request)
    stored_as, column, total, fixed = row
    parts = d.q('SELECT part, label FROM breakdown_parts WHERE set_name=? AND "table"=?', b["set"], m["table"])
    info = dict(set=b["set"], stored_as=stored_as, column=column, total=total, parts=parts, fixed={})
    if stored_as == "rows":
        info["fixed"] = {k.strip(): v.strip() for k, _, v in (x.partition("=") for x in (fixed or "").split(";")) if k.strip()}
        info["fixed"].update({p["column"].upper(): p["code"] for p in b["fixed"]})
        if info["fixed"]:
            where = "; ".join(f"{k} = {v}" for k, v in info["fixed"].items())
            ok = d.one('SELECT status FROM breakdown_slices WHERE set_name=? AND "table"=? AND measure=? AND slice=?',
                       b["set"], m["table"], m["column"], where)
            if not ok or ok[0] != "loaded":
                return decline(f'The breakdown "{b["set"]}" does not add up at {where}, so it is not shown.', "breakdown", request)
        for key in list(m["rows"]):                     # the set's own column and fixed columns replace the defaults
            if key.upper() == column.upper() or key.upper() in info["fixed"]:
                del m["rows"][key]
    info["fixed_labels"] = [label for k, v in info["fixed"].items() for (label,) in
                            d.q('SELECT label FROM dict_category_codes WHERE "table"=? AND UPPER("column")=? AND code=?',
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
