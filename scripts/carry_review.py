"""Part 5b2: carry the manual review of a reviewed run over to new runs, where the new answer is the same reading.

    python scripts/carry_review.py haiku_5_0_third haiku_5b2_first haiku_5b2_second

A turn is carried over only when its answer is identical to the reviewed run's: operation, measures, schools,
groups, years and every figure on the page (owner rule, 2026-11-26). Every other turn that needs a person's
judgement is printed for review by hand. Each grade stores a fingerprint of the expectation it was judged against
(`expect_fp`); a grade is carried only while the fingerprint matches. After reviewing a run by hand, stamp it:

    python scripts/carry_review.py --stamp haiku_6b_first
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.argv, args = sys.argv[:1], sys.argv[1:]          # the grader reads its own arguments at import
sys.path.insert(0, str(ROOT / "scripts"))
import stage4_grade as g

FILE = ROOT / "docs" / "stage4" / "review.csv"
rows = list(csv.DictReader(open(FILE, encoding="utf-8")))
fields = list(rows[0])
if args[0] == "--stamp":                                # after reviewing a run by hand: stamp its grades with the
    for r in rows:                                      # fingerprint of the expectation they were judged against
        if r["model"] in args[1:] and not r.get("expect_fp"):
            r["expect_fp"] = g.fingerprint(g.EXP.get((r["source"], r["case"], r["turn"])))
    w = csv.DictWriter(open(FILE, "w", encoding="utf-8", newline=""), fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
    sys.exit(f"stamped {', '.join(args[1:])}")
reviewed, new_runs = args[0], args[1:]
done = {(r["model"], r["source"], r["case"], r["turn"]) for r in rows}
before = {(t["source"], str(t["case"]), str(t["turn"])): t for t in g.turns(reviewed)}
review = {(r["source"], r["case"], r["turn"]): r for r in rows if r["model"] == reviewed}
added, by_hand = [], []
for run in new_runs:
    for t in g.turns(run):
        key = (t["source"], str(t["case"]), str(t["turn"]))
        e = g.EXP.get(key)
        if not e or (run,) + key in done:
            continue
        old = before.get(key)
        # Owner rule 2026-11-26: carried only when the answer is identical: operation, measures, schools, years and
        # figures (the whole page, every part of a several-part answer); expectations changed in a part are checked by hand
        shape = lambda turn: [(r.get("operation"), json.dumps(r.get("year"), sort_keys=True)) for r in turn.get("requests") or []]
        page = lambda turn: json.dumps({k: v for k, v in (turn.get("page") or {}).items() if k != "seconds"}, sort_keys=True)
        same = old is not None and g.ids(old) == g.ids(t) and shape(old) == shape(t) and page(old) == page(t)
        same = same and key in review and review[key].get("expect_fp") == g.fingerprint(e)   # expectation unchanged
        # A hand grade that overrode the automatic one (Part 6b): a changed answer goes back to a person, not the grader
        old_auto = g.auto_reading(old, e) if old else (None, None)
        overrode = key in review and any(a is not None and {"yes": True, "no": False}.get(review[key][f]) not in (None, a)
                                         for a, f in zip(old_auto, ("measure_right", "schools_right")))
        if key in review and same:
            pass
        elif not overrode and (not e["measures"].startswith("*") or not t.get("requests")):
            continue                                # graded automatically
        if key in review and same:
            added.append(dict(review[key], model=run, expect_fp=g.fingerprint(e), why=(review[key]["why"] + " (same reading as " + reviewed + ")").strip()))
        else:
            by_hand.append((run, key, t["question"], sorted(g.ids(t)[0]), sorted(g.ids(t)[1]), sorted(g.ids(t)[2]),
                            (t.get("page") or {}).get("interpreted") or (t.get("page") or {}).get("message")))
with open(FILE, "a", encoding="utf-8", newline="") as f:
    csv.DictWriter(f, fieldnames=fields).writerows(added)
print(len(added), "carried over;", len(by_hand), "to review by hand")
for run, key, q, ms, ss, gs, text in by_hand:
    print(f"\n{run} {key}: {q}\n   measures {ms} schools {ss} groups {gs}\n   {str(text)[:300]}")
