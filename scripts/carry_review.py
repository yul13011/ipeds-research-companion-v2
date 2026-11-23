"""Part 5b2: carry the manual review of a reviewed run over to new runs, where the new answer is the same reading.

    python scripts/carry_review.py haiku_5_0_third haiku_5b2_first haiku_5b2_second

A turn that needs a person's judgement (its expected measure is written as a concept) is carried over only when the
new run's answer used exactly the same measures, schools and groups as the reviewed run's answer to that turn. The
carried row says so. Every other such turn is printed for review by hand.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.argv, args = sys.argv[:1], sys.argv[1:]          # the grader reads its own arguments at import
sys.path.insert(0, str(ROOT / "scripts"))
import stage4_grade as g

reviewed, new_runs = args[0], args[1:]
FILE = ROOT / "docs" / "stage4" / "review.csv"
rows = list(csv.DictReader(open(FILE, encoding="utf-8")))
fields = list(rows[0])
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
        text = lambda turn: ((turn.get("page") or {}).get("kind"), (turn.get("page") or {}).get("message"))
        figures = lambda turn: ((turn.get("page") or {}).get("table") or {}).get("rows")
        same = old is not None and (text(old) == text(t) and text(t)[1] or      # the same reading and the same figures
                                    (g.ids(old) == g.ids(t) and text(old)[0] == text(t)[0] and t.get("requests")
                                     and figures(old) == figures(t)))
        if key in review and same:
            pass
        elif not e["measures"].startswith("*") or not t.get("requests"):
            continue                                # graded automatically
        if key in review and same:
            added.append(dict(review[key], model=run, why=(review[key]["why"] + " (same reading as " + reviewed + ")").strip()))
        else:
            by_hand.append((run, key, t["question"], sorted(g.ids(t)[0]), sorted(g.ids(t)[1]), sorted(g.ids(t)[2]),
                            (t.get("page") or {}).get("interpreted") or (t.get("page") or {}).get("message")))
with open(FILE, "a", encoding="utf-8", newline="") as f:
    csv.DictWriter(f, fieldnames=fields).writerows(added)
print(len(added), "carried over;", len(by_hand), "to review by hand")
for run, key, q, ms, ss, gs, text in by_hand:
    print(f"\n{run} {key}: {q}\n   measures {ms} schools {ss} groups {gs}\n   {str(text)[:300]}")
