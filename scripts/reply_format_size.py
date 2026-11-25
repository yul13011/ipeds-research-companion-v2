"""Part 5g: what takes up the reply format's size, and which restructure frees room (owner decision, 2026-11-24).

    python scripts/reply_format_size.py            the size of each part of the reply shape (no API call)
    python scripts/reply_format_size.py --probe    also asks the API which variants it accepts (one tiny call each)

The API compiles the reply shape into a grammar and refuses one that is too large. It does not say how large, so the
size is measured in what the shape is made of (characters, fixed lists of allowed values, choices between types,
lists) and the limit is found by probing: each variant is sent with a one-word question.
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from path import request as rq

BASE = rq.reply_schema()
STRING = {"type": "string"}


def stats(schema):
    """Characters, allowed values in fixed lists (enums), choices between types (anyOf), lists, and objects."""
    out = dict(chars=len(json.dumps(schema)), enum_values=0, unions=0, lists=0, objects=0)
    def walk(x):
        if isinstance(x, dict):
            out["enum_values"] += len(x.get("enum", []))
            out["unions"] += "anyOf" in x
            out["lists"] += x.get("type") == "array"
            out["objects"] += x.get("type") == "object"
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(schema)
    return out


def table():
    item = BASE["properties"]["requests"]["items"]["properties"]
    rows = [("whole reply shape", stats(BASE))]
    rows += [(f"request.{k}", stats(v)) for k, v in item.items()]
    rows += [(f"reply.{k}", stats(v)) for k, v in BASE["properties"].items() if k != "requests"]
    print(f"{'part':28} {'chars':>6} {'enum values':>11} {'unions':>6} {'lists':>5} {'objects':>7}")
    for name, s in rows:
        print(f"{name:28} {s['chars']:>6} {s['enum_values']:>11} {s['unions']:>6} {s['lists']:>5} {s['objects']:>7}")


def with_fields(schema, add=None, drop=()):
    s = copy.deepcopy(schema)
    it = s["properties"]["requests"]["items"]
    for k in drop:
        it["properties"].pop(k)
        it["required"].remove(k)
    for k, v in (add or {}).items():
        it["properties"][k] = v
        it["required"].append(k)
    return s


def no_unions(schema):
    """Every "value or null" choice written as the value alone: "" or 0 or an empty list stands for none."""
    s = copy.deepcopy(schema)
    def walk(x):
        if isinstance(x, dict):
            for k, v in list(x.items()):
                if isinstance(v, dict) and "anyOf" in v:
                    kept = [o for o in v["anyOf"] if o != {"type": "null"}]
                    x[k] = kept[0] if len(kept) == 1 else v
                walk(x[k])
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(s)
    return s


def tags_as_text(schema, kinds):
    """The tags of the named kinds as plain text, checked by code, instead of fixed lists of allowed tags."""
    s = copy.deepcopy(schema)
    first = {f"{rq.TAG_RANGES[k][0]}1" for k in kinds}
    def walk(x):
        if isinstance(x, dict):
            if x.get("enum") and x["enum"][0] in first:
                x.pop("enum")
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(s)
    return s


EXPLAIN = {"explain": {"type": "array", "items": STRING}, "general": STRING}
FORMULA = {"formula": {"anyOf": [{"type": "object", "properties": {"kind": {"type": "string", "enum": [
    "ratio", "difference", "percent change", "share of total"]}, "measures": {"type": "array", "items": STRING}},
    "required": ["kind", "measures"], "additionalProperties": False}, {"type": "null"}]}}

VARIANTS = {
    "today's shape": BASE,
    "today's shape + explain + general": with_fields(BASE, EXPLAIN),
    "A. no value-or-null choices, + explain + general": with_fields(no_unions(BASE), EXPLAIN),
    "B. tags as checked text, + explain + general": with_fields(tags_as_text(BASE, rq.TAG_RANGES), EXPLAIN),
    "C. measure and row tags as text only, + explain + general": with_fields(tags_as_text(BASE, ["measures", "rows"]), EXPLAIN),
    "B + explain + general + formula": with_fields(tags_as_text(BASE, rq.TAG_RANGES), dict(EXPLAIN, **FORMULA)),
    "C + explain + general + formula": with_fields(tags_as_text(BASE, ["measures", "rows"]), dict(EXPLAIN, **FORMULA)),
    "A + explain + general + formula": with_fields(no_unions(BASE), dict(EXPLAIN, **FORMULA)),
}


def probe():
    from path import interpret
    print(f"\n{'variant':60} {'chars':>6} {'enum':>5} {'unions':>6}  API")
    for name, schema in VARIANTS.items():
        s = stats(schema)
        try:
            interpret.call_api("Reply with an empty request.", "test", config.MODELS["Haiku"], schema)
            verdict = "accepted"
        except Exception as e:                          # the API's refusal, shortened
            verdict = "refused" if "too large" in str(e) else f"error: {str(e)[:60]}"
        print(f"{name:60} {s['chars']:>6} {s['enum_values']:>5} {s['unions']:>6}  {verdict}")


if __name__ == "__main__":
    table()
    if "--probe" in sys.argv:
        probe()
