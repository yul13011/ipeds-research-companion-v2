"""The structured request: the one object the model fills in and code reads.

A request is a plain dictionary made of independent parts. Any operation works with any
measure and any group; no part is specific to one kind of question.

    operation   what to do (OPERATIONS below)
    measures    measures picked from the shortlist: {"id": "DRVGR.GBA6RTT", "row": [{"column", "code"}]}
                `row` names a single category row in a multi-row table; unnamed columns take their default
    schools     schools named by the user: {"name": as written, "id": UNITID from the shortlist, or null}
    groups      group names from the shortlist; a school must be in all of them
    plus_schools  schools added to the group's list ("the Ivies plus MIT and Stanford"), even outside the group
    peers_of    the UNITID whose peers are wanted ("its peers")
    conditions  filters on a measure: {"measure", "comparison", "value"}
    breakdown   a breakdown set from the shortlist, and any fixed value the user changed
    split_by    sector, level or control
    sort        highest or lowest, and how many
    year        the year as the user stated it, and the kind of year if they said; for a trend, the first and
                last calendar years named (start, end), or the last N years (last), whether only the change between
                two years is wanted (change), and whose schools a group counts (membership: each year, or today).
                The model names the kind of span (SPANS); code keeps only the fields that span uses
    topic       for define and data_exists: an ID from the shortlist, or the user's topic in plain words
    explain     for define: the concepts (reviewed explanations) and glossary entries that explain the word asked about
    general     for define, only when nothing on the shortlist explains it: the model's own short explanation, shown
                labelled as general knowledge, not IPEDS documentation
    readings    the reading the user chose for a term with several readings: {"term", "reading"}

Reserved for the next stage, not built: `formula` (ratio, difference, percent change, share of
total across measures) and `category_sets` (several categories of one breakdown combined). Both
are new fields beside `measures` and `breakdown`; nothing here changes when they are added.
"""
import copy
import re

OPERATIONS = {
    "schools": "show one or more measures for one or more named schools",
    "rank": "rank the schools in a group (or the nation) on one measure",
    "list": "list the schools in a group (or the nation) that meet one or more conditions",
    "breakdown": "split one measure into the categories of a breakdown set, for schools or a group",
    "group": "one figure for a whole group (or the nation): a total, or a rate or average computed from counts",
    "split": "a group figure shown separately by sector, level or control",
    "count_schools": "count the schools in a group (or the nation), optionally meeting conditions",
    "school_vs_group": "one school's value beside a group figure (its peers, or a named group)",
    "define": "the definition of a measure or term",
    "data_exists": "what data exists on a topic, and for which years",
}
LIST_FIELDS = ("measures", "schools", "groups", "plus_schools", "conditions", "readings")
SCALAR_FIELDS = ("operation", "peers_of", "breakdown", "split_by", "sort", "year", "topic")
COMPARISONS = (">", ">=", "<", "<=", "=", "!=")
YEAR_KINDS = ("fall", "fiscal year", "academic year", "aid year", "entering cohort", "class year", "calendar year", "latest")
MISSING = ("measure", "group", "calculation", "breakdown", "not in IPEDS", "not a data question", "other")   # never
                                                # "years": the code alone decides which years are held (2026-11-25)
MEMBERSHIP = ("each year", "today")         # a group over time: each year's own schools (default), or today's schools
SPANS = ("one year", "from a year on", "a range of years", "the last N years", "the change between two years")


def obj(**props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


# The shape the model must reply in. The model answers in tags (M1, S1, G1, R1, B1, T1, O1), so it cannot type
# an ID wrongly. The tag ranges are the same for every question, so the shape never changes and the API can cache
# it with the instructions; a tag that is not on the question's shortlist is rejected by resolve as a wrong reading.
# Unused fields are empty: "" for a tag, a fixed choice or text, 0 for a number, an empty list. None of these can be
# a real value (checked field by field, 2026-11-25). The shape has no "value or null" choices: those, not its length
# or its lists of tags, are what made the API's grammar too large (Part 5g, scripts/reply_format_size.py). The request
# shape appears once, as the items of `requests`: one item for a new question, one holding an edit's new values, or
# two or three options with labels. from_wire() maps tags back to real IDs and "" or 0 to None.
TAG_RANGES = {"measures": ("M", 64), "schools": ("S", 16), "groups": ("G", 20), "rows": ("R", 64), "sets": ("B", 32),
              "readings": ("T", 24), "outside": ("O", 4), "concepts": ("C", 4), "glossary": ("D", 4)}
STRING, INTEGER = {"type": "string"}, {"type": "integer"}


def one_of(tags):
    """A field that takes one tag from the list."""
    return {"type": "string", "enum": tags}


def or_none(choice):
    """A tag or fixed choice that may be left empty: "" means none."""
    return {"type": "string", "enum": [""] + choice["enum"]}


def reply_schema():
    """The structured-output schema, the same for every question."""
    of = lambda kind: one_of([f"{TAG_RANGES[kind][0]}{i}" for i in range(1, TAG_RANGES[kind][1] + 1)])
    of_explain = one_of([f"{TAG_RANGES[k][0]}{i}" for k in ("concepts", "glossary") for i in range(1, TAG_RANGES[k][1] + 1)])
    request = obj(
        label=STRING,
        operation={"type": "string", "enum": list(OPERATIONS)},
        measures={"type": "array", "items": obj(measure=of("measures"), row={"type": "array", "items": of("rows")})},
        schools={"type": "array", "items": obj(name=STRING, school=or_none(of("schools")))},
        groups={"type": "array", "items": of("groups")},
        plus_schools={"type": "array", "items": of("schools")},   # added to the group's list
        peers_of=or_none(of("schools")),
        conditions={"type": "array", "items": obj(measure=of("measures"), comparison={"type": "string", "enum": list(COMPARISONS)},
                                                  value=STRING)},
        breakdown=obj(set=or_none(of("sets")), fixed={"type": "array", "items": of("rows")}),   # set "": none
        split_by=or_none({"enum": ["sector", "level", "control"]}),
        sort=obj(order=or_none({"enum": ["highest", "lowest"]}), limit=INTEGER),          # order "": none; limit 0: all
        year=obj(stated=STRING, kind=or_none({"enum": list(YEAR_KINDS)}),
                 span={"type": "string", "enum": list(SPANS)}, start=INTEGER, end=INTEGER, last=INTEGER,
                 membership={"type": "string", "enum": list(MEMBERSHIP)}),   # 0: not given
        topic=STRING,
        outside=or_none(of("outside")),
        readings={"type": "array", "items": of("readings")},
        explain={"type": "array", "items": of_explain},          # define: the C and D tags that explain the word
        general=STRING,                                          # define, as a last resort: a short explanation
    )
    return obj(
        kind={"type": "string", "enum": ["request", "edit", "options", "choose", "decline", "about_decline", "search",
                                         "several"]},
        search_words=STRING,                    # kind search: the words to look for (plain text, never nullable)
        requests={"type": "array", "items": request},
        changes={"type": "array", "items": obj(
            field={"type": "string", "enum": list(LIST_FIELDS + SCALAR_FIELDS)},
            action={"type": "string", "enum": ["add", "remove", "replace", "back"]})},
        chosen={"type": "array", "items": INTEGER},
        decline=obj(reason=STRING, wanted=STRING, missing=or_none({"enum": list(MISSING)}), closest=STRING,   # read only
                    about=or_none({"enum": ["why", "where", "instead"]})),                      # for kind decline
    )


def request_from_wire(r, tags, unknown=None):
    """One request as the model wrote it, in tags, turned into the request the code uses (real IDs, None for unused).
    Tags that are not on this question's shortlist are added to `unknown`."""
    def look(t, kind):
        if t in tags and tags[t][0] == kind:
            return tags[t][1]
        if t and unknown is not None:
            unknown.append(t)
        return None
    def rows_for(table, tag_list):
        pairs = [look(t, "rows") for t in tag_list or []]
        return [dict(column=p[1], code=p[2]) for p in pairs if p and (table is None or p[0] == table)]
    measures = []
    for m in r.get("measures") or []:
        mid = look(m["measure"], "measures")
        if mid:
            measures.append(dict(id=mid, row=rows_for(mid.partition(".")[0] if "." in mid else None, m.get("row"))))
    breakdown = r.get("breakdown")
    set_key = look(breakdown["set"], "sets") if breakdown and breakdown.get("set") else None
    sort = r.get("sort")
    outside = look(r.get("outside"), "outside") if r.get("outside") else None
    def explained(t):                                   # a concept (C) or glossary (D) tag
        if t in tags and tags[t][0] in ("concepts", "glossary"):
            return dict(kind=tags[t][0], key=tags[t][1])
        if unknown is not None:
            unknown.append(t)
    return dict(
        operation=r["operation"], measures=measures,
        schools=[dict(name=s["name"], id=look(s.get("school"), "schools")) for s in r.get("schools") or []],
        plus_schools=[u for u in (look(t, "schools") for t in r.get("plus_schools") or []) if u],
        groups=[g for g in (look(t, "groups") for t in r.get("groups") or []) if g],
        peers_of=look(r.get("peers_of"), "schools") if r.get("peers_of") else None,
        conditions=[dict(measure=look(c["measure"], "measures"), comparison=c["comparison"], value=c["value"])
                    for c in r.get("conditions") or [] if look(c["measure"], "measures")],
        breakdown=dict(set=set_key[0], fixed=rows_for(set_key[1], breakdown.get("fixed"))) if set_key else None,
        split_by=r.get("split_by") or None,
        sort=dict(order=sort["order"], limit=sort.get("limit") or None) if sort and sort.get("order") else None,
        year=year_from_wire(r.get("year") or {}),
        topic=outside or (r.get("topic") or "").strip() or None,
        readings=[dict(term=x[0], reading=x[1]) for x in (look(t, "readings") for t in r.get("readings") or []) if x],
        explain=[x for x in map(explained, r.get("explain") or []) if x] if r["operation"] == "define" else [],
        general=(r.get("general") or "").strip() or None if r["operation"] == "define" else None,
    )


def from_wire(reply, tags=None):
    """The model's reply in the form the code uses: request, edit, options, chosen and decline, unused parts None.

    A reply already in that form (the saved replies the tests use) passes through unchanged."""
    if "requests" not in reply:
        return copy.deepcopy(reply)
    kind = reply["kind"]
    unknown = []
    items = [request_from_wire(r, tags or {}, unknown) for r in reply["requests"]]
    labels = [no_tags(r.get("label")) or f"Option {i + 1}" for i, r in enumerate(reply["requests"])]
    return dict(kind=kind, search_words=(reply.get("search_words") or "").strip() or None,
                request=items[0] if kind in ("request", "decline") and items else None,
                edit=dict(changes=reply["changes"], values=items[0] if items else None) if kind == "edit" else None,
                options=[dict(label=l, request=r) for l, r in zip(labels, items)] if kind == "options" else [],
                several=items if kind == "several" else [],     # two or three requests, answered together
                chosen=reply.get("chosen") or [],
                decline=({k: (v or None) if k in ("missing", "about") else v for k, v in reply["decline"].items()}
                         if reply.get("decline") else None) if kind in ("decline", "about_decline") else None,
                unknown_tags=sorted(set(unknown)))


def no_tags(label):
    """An option label as the user sees it: the model's tags (M7, S4) are taken out."""
    return re.sub(r"\s*\(?\b[MSGRBTOCD]\d{1,2}\b\)?", "", label or "").strip()


REPLY_SCHEMA = reply_schema()


def to_wire(r, tags):
    """A request written in this question's tags, for showing the previous request in the prompt."""
    if not r:
        return r
    back = {(kind, key): t for t, (kind, key) in tags.items()}
    t = lambda kind, key: back.get((kind, key), str(key))
    table = lambda mid: mid.partition(".")[0]
    return dict(
        operation=r["operation"],
        measures=[dict(measure=t("measures", m["id"]), row=[t("rows", (table(m["id"]), p["column"], p["code"])) for p in m["row"]])
                  for m in r["measures"]],
        schools=[dict(name=s["name"], school=t("schools", s["id"]) if s["id"] else None) for s in r["schools"]],
        plus_schools=[t("schools", u) for u in r.get("plus_schools") or []],
        groups=[t("groups", g) for g in r["groups"]],
        peers_of=t("schools", r["peers_of"]) if r["peers_of"] else None,
        conditions=[dict(measure=t("measures", c["measure"]), comparison=c["comparison"], value=c["value"]) for c in r["conditions"]],
        breakdown=dict(set=r["breakdown"]["set"], fixed=[f"{p['column']} = {p['code']}" for p in r["breakdown"]["fixed"]])
        if r["breakdown"] else None,
        split_by=r["split_by"], sort=r["sort"], year=r["year"], topic=r["topic"],
        explain=[t(x["kind"], x["key"]) for x in r.get("explain") or []], general=r.get("general") or "",
        readings=[t("readings", (x["term"], x["reading"])) for x in r["readings"]],
    )


def no_year():
    return {"stated": None, "kind": None, "span": None, "start": None, "end": None, "last": None, "change": False,
            "membership": None}


def year_from_wire(y):
    """The year part of a request as the model wrote it, with every field present. The model names the kind of span
    (SPANS) and writes 0 for a year it was not given; the span decides which of start, end and last count."""
    out = no_year()
    out.update({k: (y.get(k) or (False if k == "change" else None)) for k in out})
    span = y.get("span")
    if span:                                            # the span the model named decides; the rest is cleared
        keep = {"one year": ("start", "end"), "from a year on": ("start",), "a range of years": ("start", "end"),
                "the last N years": ("last",), "the change between two years": ("start", "end")}[span]
        for k in ("start", "end", "last"):
            if k not in keep:
                out[k] = None
        out["change"] = span == "the change between two years"
    return out


def is_trend(year):
    """A request over several years: from a year on, a range, the last N years, or the change between two years."""
    if not year:
        return False
    if year.get("span"):
        return year["span"] != "one year"
    return bool(year.get("start") or year.get("last") or year.get("change"))


def by_year(year):
    """Does the request need its years chosen release by release: a trend, or one named year (which may be earlier
    than the latest release)?"""
    return is_trend(year) or bool(year and year.get("span") == "one year" and year.get("start"))


def covers(cell, year):
    """Does a dictionary `years` cell ('2015-2019', '2015-2017, 2020', or blank for every year) cover this year?"""
    if not cell:
        return True
    for part in (x.strip() for x in cell.split(",") if x.strip()):
        first, _, last = part.partition("-")
        if int(first) <= year <= int(last or first):
            return True
    return False


def empty(operation="schools"):
    """A request with every part present and empty."""
    return {"operation": operation, "measures": [], "schools": [], "groups": [], "peers_of": None, "conditions": [],
            "breakdown": None, "split_by": None, "sort": None, "year": no_year(), "topic": None,
            "readings": [], "explain": [], "general": None, "plus_schools": []}


def same(a, b):
    """Two items of a list field are the same item if their IDs (or names) match."""
    if isinstance(a, dict):
        key = ("id" if a.get("id") is not None else "name") if "name" in a else next(iter(a))
        return a.get(key) == b.get(key)
    return a == b


def apply_edit(previous, edit, history):
    """Apply a follow-up edit to the previous request. `history` is the list of earlier requests, oldest first.

    add / remove / replace work on every list field; replace (or remove, which clears) on every other field.
    "back" restores the request before the previous one.
    """
    new = copy.deepcopy(previous)
    values = edit.get("values") or empty()
    for change in edit["changes"]:
        field, action = change["field"], change["action"]
        if action == "back":
            return copy.deepcopy(history[-2]) if len(history) >= 2 else new
        if field in LIST_FIELDS:
            given = values.get(field) or []
            if action == "add":
                new[field] += [x for x in given if not any(same(x, y) for y in new[field])]
            elif action == "remove":
                new[field] = [y for y in new[field] if not any(same(x, y) for x in given)]
            else:
                new[field] = copy.deepcopy(given)
        else:
            new[field] = copy.deepcopy(values.get(field)) if action != "remove" else empty()[field]
    return new


def used_ids(request):
    """Every dictionary ID a request names, by kind, for the check that each was on the shortlist."""
    ids = {"measure": set(), "school": set(), "group": set(), "row": set(), "set": set(), "reading": set(),
           "explanation": {(x["kind"], x["key"]) for x in request.get("explain") or []}}
    for m in request["measures"]:
        ids["measure"].add(m["id"])
        for pair in m["row"]:
            ids["row"].add((m["id"].partition(".")[0], pair["column"].upper(), pair["code"]))
    for c in request["conditions"]:
        ids["measure"].add(c["measure"])
    ids["school"] |= {s["id"] for s in request["schools"] if s["id"] is not None}
    ids["school"] |= set(request.get("plus_schools") or [])
    if request["peers_of"] is not None:
        ids["school"].add(request["peers_of"])
    ids["group"] |= set(request["groups"])
    if request["breakdown"]:
        ids["set"].add(request["breakdown"]["set"])
    ids["reading"] |= {(r["term"], r["reading"]) for r in request["readings"]}
    return ids


def fill_years(text, year):
    """Period text in the dictionary is written from the release year: {Y} is the release year, {Y-1} and {Y+1}
    count from it, and {Y:yy} gives the last two digits. fill_years("July 1, {Y-1} - June 30, {Y}", 2024)
    -> "July 1, 2023 - June 30, 2024"."""
    def one(m):
        y = year + int(m.group(1) or 0)
        return f"{y % 100:02d}" if m.group(2) else str(y)
    return re.sub(r"\{Y([+-]\d+)?(:yy)?\}", one, text) if text else text
