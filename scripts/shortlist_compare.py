"""Compare shortlists from two builds of the dictionary, with no model call.

    python scripts/shortlist_compare.py BEFORE.sqlite [AFTER.sqlite]     two dictionary builds, the current search code
    python scripts/shortlist_compare.py --code OLD_shortlist.py           an earlier search code, the current build

Questions: the nine design questions (tests/replies), every distinct logged question, and every eval-set turn.
Each is shortlisted on its own (no earlier request carried, which the live path would add for follow-ups).
"The right measure" for a question is any of: the measure IDs in docs/stage4/expectations.csv, the measures of the
saved design reply, and the measures of turns graded a correct answer in the latest Haiku run.
Writes docs/reports/stage4/shortlist_compare.csv and prints what dropped out and where one table crowds the list.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "agent-redesign" / "evaluations"))
import config
from path import shortlist
from path.request import from_wire

SET_UP = shortlist.SET_UP


def questions():
    for p in sorted((ROOT / "tests" / "replies").glob("*.json")):
        if p.name.startswith("real"):
            continue
        case = json.loads(p.read_text(encoding="utf-8"))
        r = case["reply"].get("request") or (case["reply"].get("edit") or {}).get("values") or {}
        yield "design", p.stem, "1", case["question"], {m["id"] for m in r.get("measures") or [] if m.get("id")}
    seen = set()
    for r in csv.DictReader(open(ROOT / "docs" / "test_questions.csv", encoding="utf-8")):
        if r["question"] not in seen:
            seen.add(r["question"])
            yield "log", r["conversation"], r["turn"], r["question"], set()
    import eval_set
    cases = eval_set.all_cases() if callable(getattr(eval_set, "all_cases", None)) else eval_set.CASES
    for c in cases:
        for i, t in enumerate(c["turns"], 1):
            yield "eval", c["id"], str(i), t["q"], set()


def right_measures():
    out = {}
    for r in csv.DictReader(open(ROOT / "docs" / "stage4" / "expectations.csv", encoding="utf-8")):
        if r["measures"] and not r["measures"].startswith("*"):
            out.setdefault((r["source"], r["case"], r["turn"]), set()).update(r["measures"].split("|"))
    turns = {(t["source"], str(t["case"]), str(t["turn"])): t for t in
             map(json.loads, (config.LOG_DIR / "stage4" / "haiku" / "turns.jsonl").read_text(encoding="utf-8").splitlines())}
    for r in csv.DictReader(open(ROOT / "docs" / "reports" / "stage4" / "scorecard_haiku.csv", encoding="utf-8")):
        t = turns.get((r["source"], r["case"], r["turn"]))
        if r["score"] == "correct answer" and t:
            for q in t["requests"]:
                out.setdefault((r["source"], r["case"], r["turn"]), set()).update(m["id"] for m in q["measures"])
    return out


def ranked(question, db, module=shortlist):
    s = module.shortlist(question, db)
    ids = [m["id"] for m in s["measures"]]
    tables = Counter(i.partition(".")[0] for i in ids[:SET_UP])
    return ids, tables


def main():
    old = shortlist
    if sys.argv[1] == "--code":                         # an earlier version of the search, on the current build
        import importlib.util
        spec = importlib.util.spec_from_file_location("shortlist_old", sys.argv[2])
        old = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old)
        before = after = config.LOCAL_DB.as_posix()
    else:
        before, after = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else config.LOCAL_DB.as_posix()
    right = right_measures()
    rows = []
    for source, case, turn, question, saved in questions():
        want = (right.get((source, case, turn)) or set()) | saved
        b_ids, b_tab = ranked(question, before, old)
        a_ids, a_tab = ranked(question, after)
        dropped = sorted(m for m in want if m in b_ids and m not in a_ids)
        gained = sorted(m for m in want if m not in b_ids and m in a_ids)
        missing_both = sorted(m for m in want if m not in b_ids and m not in a_ids)
        top_b, top_a = (b_tab.most_common(1) or [("", 0)])[0], (a_tab.most_common(1) or [("", 0)])[0]
        crowded = top_a[1] >= 10 and top_a[1] - b_tab.get(top_a[0], 0) >= 3
        rows.append(dict(source=source, case=case, turn=turn, question=question, right=";".join(sorted(want)),
                         dropped=";".join(dropped), gained=";".join(gained), missing_both=";".join(missing_both),
                         new_in_list=len(set(a_ids) - set(b_ids)), top_table_before=f"{top_b[0]} {top_b[1]}",
                         top_table_after=f"{top_a[0]} {top_a[1]}", crowded="yes" if crowded else ""))
    path = ROOT / "docs" / "reports" / "stage4" / "shortlist_compare.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} questions; with a known right measure: {sum(1 for r in rows if r['right'])}; "
          f"shortlist changed: {sum(1 for r in rows if r['new_in_list'])}")
    for label, key in (("DROPPED", "dropped"), ("GAINED", "gained"), ("MISSING IN BOTH", "missing_both")):
        hit = [r for r in rows if r[key]]
        print(f"\n{label}: {len(hit)}")
        for r in hit:
            print(f"  {r['source']} {r['case']}.{r['turn']} {r['question'][:70]} -> {r[key]}")
    hit = [r for r in rows if r["crowded"]]
    print(f"\nCROWDED (one table holds 10+ of the {SET_UP} set-up slots, 3+ more than before): {len(hit)}")
    for r in hit:
        print(f"  {r['source']} {r['case']}.{r['turn']} {r['question'][:70]} | before {r['top_table_before']} | after {r['top_table_after']}")


if __name__ == "__main__":
    main()
