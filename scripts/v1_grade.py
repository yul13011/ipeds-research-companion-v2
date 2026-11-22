"""Version 1 beside version 2 on the logged questions, graded against the same expectations file.

    python scripts/v1_grade.py [v2 run folder name, default haiku]

Version 1 is not rerun. Its recorded outcome comes from docs/question_log.csv: the outcome class, which route served
it, the interpretation it wrote (for some rows), and how many rows it returned. No session IDs or times are read
out of the log. The log has no answer values, measures or schools, so a version 1 answer can be checked only for
its outcome class, plus its interpretation where one was written. Questions whose expected decline rests on the
one-year slice (trend questions, years outside 2024-25) are not comparable: version 1 held ten years.
Writes docs/reports/stage4/v1_vs_v2.csv and prints the summary used in the report.
"""
import csv
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config

RUN = sys.argv[1] if len(sys.argv) > 1 else "haiku"
V1_CLASS = {"answered": "answer", "needs_clarification": "clarify", "refused": "decline", "error_app": "error", "error_api": "error"}


def norm(text):
    return " ".join(unicodedata.normalize("NFKC", text).replace("’", "'").replace("–", "-").split()).lower()


def main():
    log = list(csv.DictReader(open(ROOT / "docs" / "question_log.csv", encoding="utf-8-sig")))
    tq = list(csv.DictReader(open(ROOT / "docs" / "test_questions.csv", encoding="utf-8")))
    used, v1 = set(), {}
    for t in tq:                                       # match in order, by question text
        for i, row in enumerate(log):
            if i not in used and norm(row["question"]) == norm(t["question"]):
                used.add(i)
                v1[(t["conversation"], t["turn"])] = row
                break
    exp = {(r["case"], r["turn"]): r for r in csv.DictReader(open(ROOT / "docs" / "stage4" / "expectations.csv", encoding="utf-8"))
           if r["source"] == "log"}
    v2 = {(r["case"], r["turn"]): r for r in csv.DictReader(open(ROOT / "docs" / "reports" / "stage4" / f"scorecard_{RUN}.csv",
                                                                encoding="utf-8")) if r["source"] == "log"}
    review = {(r["conversation"], r["turn"]): r for r in csv.DictReader(open(ROOT / "docs" / "stage4" / "v1_review.csv",
                                                                              encoding="utf-8"))}
    out = []
    for key, e in exp.items():
        row = v1.get(key)
        if row is None:
            continue
        got = V1_CLASS.get(row["outcome"], row["outcome"])
        expect = set(e["expect"].split("|")) - {""}
        years = e["category"] == "trend" or ("not in the slice" in e["note"] and re.search(r"(?:19|20)\d\d", e["note"]))
        if e["category"] in ("greeting", "test", "chart", "context", "display"):
            grade = "not scored"
        elif years:
            grade = "not comparable (version 1 held ten years)"
        elif got == "error":
            grade = "error"
        elif got == "answer" and row["n_rows"] in ("", "0") and row["served_by"] not in ("conversation", "data discovery", "curated FAQ"):
            grade = "answered with no rows"
        elif got in expect:
            grade = {"answer": "answered as expected (figures not checkable)", "decline": "declined as expected",
                     "clarify": "clarifying question"}[got]
        elif got == "clarify":
            grade = "clarifying question"
        else:
            grade = f"{got} where {'/'.join(sorted(expect))} was expected"
        if key in review:                              # a judgment of version 1's written interpretation
            grade = review[key]["v1_grade"]
        s = v2.get(key, {})
        out.append(dict(conversation=key[0], turn=key[1], category=e["category"], question=row["question"], expect=e["expect"],
                        v1_outcome=row["outcome"], v1_route=row["served_by"], v1_rows=row["n_rows"],
                        v1_interpreted=row["interpreted_as"], v1_grade=grade, v1_why=review.get(key, {}).get("why", ""),
                        v2_outcome=s.get("got", ""), v2_grade=s.get("score", ""), v2_why=s.get("why", "")))
    path = ROOT / "docs" / "reports" / "stage4" / "v1_vs_v2.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print("logged questions matched:", len(v1), "of", len(tq), "; with an expectation:", len(out))
    for cat in ("scored", "trend"):
        rows = [r for r in out if r["category"] == cat]
        print(f"\n{cat} (n={len(rows)})\n  version 1:", dict(Counter(r["v1_grade"] for r in rows)),
              "\n  version 2:", dict(Counter(r["v2_grade"] for r in rows)))
    print("\nversion 1 routes on scored questions:", dict(Counter(r["v1_route"] or "(none)" for r in out if r["category"] == "scored")))


if __name__ == "__main__":
    main()
