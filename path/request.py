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
YEAR_KINDS = ("fall", "fiscal year", "academic year", "aid year", "entering cohort", "class year", "calendar year")
MISSING = ("measure", "group", "calculation", "breakdown", "years", "not in IPEDS", "not a data question", "other")


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def obj(**props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


STRING = {"type": "string"}
PAIR = obj(column=STRING, code=STRING)
REQUEST_SCHEMA = obj(
    operation={"type": "string", "enum": list(OPERATIONS)},
    measures={"type": "array", "items": obj(id=STRING, row={"type": "array", "items": PAIR})},
    schools={"type": "array", "items": obj(name=STRING, id=nullable({"type": "integer"}))},
    groups={"type": "array", "items": STRING},
    peers_of=nullable({"type": "integer"}),
    conditions={"type": "array", "items": obj(measure=STRING, comparison={"type": "string", "enum": list(COMPARISONS)},
                                              value=STRING)},
    breakdown=nullable(obj(set=STRING, fixed={"type": "array", "items": PAIR})),
    split_by=nullable({"type": "string", "enum": ["sector", "level", "control"]}),
    sort=nullable(obj(order={"type": "string", "enum": ["highest", "lowest"]}, limit=nullable({"type": "integer"}))),
    year=obj(stated=nullable(STRING), kind=nullable({"type": "string", "enum": list(YEAR_KINDS)})),
    topic=nullable(STRING),
    readings={"type": "array", "items": obj(term=STRING, reading=STRING)},
)
EDIT_SCHEMA = obj(
    changes={"type": "array", "items": obj(
        field={"type": "string", "enum": list(LIST_FIELDS + SCALAR_FIELDS)},
        action={"type": "string", "enum": ["add", "remove", "replace", "back"]})},
    values=nullable(REQUEST_SCHEMA),
)
REPLY_SCHEMA = obj(
    kind={"type": "string", "enum": ["request", "edit", "options", "choose", "decline"]},
    request=nullable(REQUEST_SCHEMA),
    edit=nullable(EDIT_SCHEMA),
    options={"type": "array", "items": obj(label=STRING, request=REQUEST_SCHEMA)},
    chosen={"type": "array", "items": {"type": "integer"}},
    decline=nullable(obj(reason=STRING, wanted=STRING, missing={"type": "string", "enum": list(MISSING)},
                         closest=STRING)),
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
