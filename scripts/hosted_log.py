"""The hosted question log, turned into new real users' questions for the scorecard (Part 6f).

    .venv\\Scripts\\python.exe scripts/hosted_log.py <sheet.csv> [--out docs/hosted_questions.csv]

Reads version 2's question sheet, downloaded as CSV (Google Sheets: File -> Download -> CSV), and writes one row per typed question, in the form
of docs/test_questions.csv (conversation, turn, question, repeat), plus the outcome and seconds for review. Session
codes and times are not copied: conversations are numbered in the order they began. Button presses ([option] ...)
and limit messages are left out. The owner chooses which rows to add to the test set.
"""
import argparse
import csv


def rows(sheet_csv):
    seen, number, out = {}, 0, []
    for r in csv.DictReader(open(sheet_csv, encoding="utf-8-sig")):
        question = r.get("question") or ""
        if question.startswith("[") or (r.get("outcome") or "").startswith("limit_"):
            continue
        if r.get("conversation") not in seen:
            number += 1
            seen[r.get("conversation")] = dict(number=number, turns=0, asked=set())
        c = seen[r.get("conversation")]
        c["turns"] += 1
        out.append(dict(conversation=f"h{c['number']}", turn=c["turns"], question=question,
                        repeat="yes" if question.strip().lower() in c["asked"] else "no",
                        outcome=r.get("outcome"), seconds=r.get("seconds")))
        c["asked"].add(question.strip().lower())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_csv")
    ap.add_argument("--out", default="docs/hosted_questions.csv")
    a = ap.parse_args()
    found = rows(a.sheet_csv)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["conversation", "turn", "question", "repeat", "outcome", "seconds"])
        w.writeheader()
        w.writerows(found)
    print(f"{len(found)} questions in {len({r['conversation'] for r in found})} conversations -> {a.out}")


if __name__ == "__main__":
    main()
