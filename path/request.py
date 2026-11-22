"""The structured request: the one object the model fills in and code reads.

A request is a plain dictionary made of independent parts. Any operation works with any
measure and any group; no part is specific to one kind of question.

    operation   what to do (OPERATIONS below)
    measures    measures picked from the shortlist: {"id": "DRVGR.GBA6RTT", "row": [{"column", "code"}]}
                `row` names a single category row in a multi-row table; unnamed columns take their default
    schools     schools named by the user: {"name": as written, "id": UNITID from the shortlist, or null}
    groups      group names from the shortlist; a school must be in all of them
    peers_of    the UNITID whose peers are wanted ("its peers")
    conditions  filters on a measure: {"measure", "comparison", "value"}
    breakdown   a breakdown set from the shortlist, and any fixed value the user changed
    split_by    sector, level or control
    sort        highest or lowest, and how many
    year        the year as the user stated it, and the kind of year if they said
    topic       for define and data_exists: an ID from the shortlist, or the user's topic in plain words
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
LIST_FIELDS = ("measures", "schools", "groups", "conditions", "readings")
SCALAR_FIELDS = ("operation", "peers_of", "breakdown", "split_by", "sort", "year", "topic")
COMPARISONS = (">", ">=", "<", "<=", "=", "!=")
YEAR_KINDS = ("fall", "fiscal year", "academic year", "aid year", "entering cohort", "class year", "calendar year", "latest")
MISSING = ("measure", "group", "calculation", "breakdown", "years", "not in IPEDS", "not a data question", "other")


def obj(**props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


# The shape the model must reply in. The model answers in tags (M1, S1, G1, R1, B1, T1, O1), so it cannot type
# an ID wrongly. The tag ranges are the same for every question, so the shape never changes and the API can cache
# it with the instructions; a tag that is not on the question's shortlist is rejected by resolve as a wrong reading.
# Unused fields are null or empty lists. The request shape appears once, as the items of `requests`: one item for
# a new question, one holding an edit's new values, or two or three options with labels. from_wire() maps tags
# back to real IDs.
TAG_RANGES = {"measures": ("M", 64), "schools": ("S", 16), "groups": ("G", 20), "rows": ("R", 64), "sets": ("B", 32),
              "readings": ("T", 24), "outside": ("O", 4)}
STRING, INTEGER = {"type": "string"}, {"type": "integer"}


def one_of(tags):
    """A field that takes one tag from the list; with no tags of that kind, it can only be null."""
    return {"type": "string", "enum": tags} if tags else {"type": "null"}


def maybe(schema):
    return schema if schema == {"type": "null"} else {"anyOf": [schema, {"type": "null"}]}


def reply_schema():
    """The structured-output schema, the same for every question."""
    of = lambda kind: one_of([f"{TAG_RANGES[kind][0]}{i}" for i in range(1, TAG_RANGES[kind][1] + 1)])
    request = obj(
        label=STRING,
        operation={"type": "string", "enum": list(OPERATIONS)},
        measures={"type": "array", "items": obj(measure=of("measures"), row={"type": "array", "items": of("rows")})},
        schools={"type": "array", "items": obj(name=STRING, school=maybe(of("schools")))},
        groups={"type": "array", "items": of("groups")},
        peers_of=maybe(of("schools")),
        conditions={"type": "array", "items": obj(measure=of("measures"), comparison={"type": "string", "enum": list(COMPARISONS)},
                                                  value=STRING)},
        breakdown=maybe(obj(set=of("sets"), fixed={"type": "array", "items": of("rows")})),
        split_by=maybe({"type": "string", "enum": ["sector", "level", "control"]}),
        sort=maybe(obj(order={"type": "string", "enum": ["highest", "lowest"]}, limit=maybe(INTEGER))),
        year=obj(stated=maybe(STRING), kind=maybe({"type": "string", "enum": list(YEAR_KINDS)})),
        topic=maybe(STRING),
        outside=maybe(of("outside")),
        readings={"type": "array", "items": of("readings")},
    )
    return obj(
        kind={"type": "string", "enum": ["request", "edit", "options", "choose", "decline", "about_decline"]},
        requests={"type": "array", "items": request},
        changes={"type": "array", "items": obj(
            field={"type": "string", "enum": list(LIST_FIELDS + SCALAR_FIELDS)},
            action={"type": "string", "enum": ["add", "remove", "replace", "back"]})},
        chosen={"type": "array", "items": INTEGER},
        decline=maybe(obj(reason=STRING, wanted=STRING, missing={"type": "string", "enum": list(MISSING)}, closest=STRING,
                          about=maybe({"type": "string", "enum": ["why", "where", "instead"]}))),
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
    return dict(
        operation=r["operation"], measures=measures,
        schools=[dict(name=s["name"], id=look(s.get("school"), "schools")) for s in r.get("schools") or []],
        groups=[g for g in (look(t, "groups") for t in r.get("groups") or []) if g],
        peers_of=look(r.get("peers_of"), "schools") if r.get("peers_of") else None,
        conditions=[dict(measure=look(c["measure"], "measures"), comparison=c["comparison"], value=c["value"])
                    for c in r.get("conditions") or [] if look(c["measure"], "measures")],
        breakdown=dict(set=set_key[0], fixed=rows_for(set_key[1], breakdown.get("fixed"))) if set_key else None,
        split_by=r.get("split_by") or None,
        sort=dict(order=sort["order"], limit=sort.get("limit") or None) if sort else None,
        year=dict(stated=(r.get("year") or {}).get("stated") or None, kind=(r.get("year") or {}).get("kind") or None),
        topic=outside or r.get("topic") or None,
        readings=[dict(term=x[0], reading=x[1]) for x in (look(t, "readings") for t in r.get("readings") or []) if x],
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
    return dict(kind=kind,
                request=items[0] if kind in ("request", "decline") and items else None,
                edit=dict(changes=reply["changes"], values=items[0] if items else None) if kind == "edit" else None,
                options=[dict(label=l, request=r) for l, r in zip(labels, items)] if kind == "options" else [],
                chosen=reply.get("chosen") or [],
                decline=reply.get("decline") if kind in ("decline", "about_decline") else None,
                unknown_tags=sorted(set(unknown)))


def no_tags(label):
    """An option label as the user sees it: the model's tags (M7, S4) are taken out."""
    return re.sub(r"\s*\(?\b[MSGRBTO]\d{1,2}\b\)?", "", label or "").strip()


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
        groups=[t("groups", g) for g in r["groups"]],
        peers_of=t("schools", r["peers_of"]) if r["peers_of"] else None,
        conditions=[dict(measure=t("measures", c["measure"]), comparison=c["comparison"], value=c["value"]) for c in r["conditions"]],
        breakdown=dict(set=r["breakdown"]["set"], fixed=[f"{p['column']} = {p['code']}" for p in r["breakdown"]["fixed"]])
        if r["breakdown"] else None,
        split_by=r["split_by"], sort=r["sort"], year=r["year"], topic=r["topic"],
        readings=[t("readings", (x["term"], x["reading"])) for x in r["readings"]],
    )


def empty(operation="schools"):
    """A request with every part present and empty."""
    return {"operation": operation, "measures": [], "schools": [], "groups": [], "peers_of": None, "conditions": [],
            "breakdown": None, "split_by": None, "sort": None, "year": {"stated": None, "kind": None}, "topic": None,
            "readings": []}


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
    ids = {"measure": set(), "school": set(), "group": set(), "row": set(), "set": set(), "reading": set()}
    for m in request["measures"]:
        ids["measure"].add(m["id"])
        for pair in m["row"]:
            ids["row"].add((m["id"].partition(".")[0], pair["column"].upper(), pair["code"]))
    for c in request["conditions"]:
        ids["measure"].add(c["measure"])
    ids["school"] |= {s["id"] for s in request["schools"] if s["id"] is not None}
    if request["peers_of"] is not None:
        ids["school"].add(request["peers_of"])
    ids["group"] |= set(request["groups"])
    if request["breakdown"]:
        ids["set"].add(request["breakdown"]["set"])
    ids["reading"] |= {(r["term"], r["reading"]) for r in request["readings"]}
    return ids
