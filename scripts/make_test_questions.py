"""Regenerate docs/test_questions.csv from the raw question log (docs/question_log.csv, untracked).

    python scripts/make_test_questions.py

Keeps only the question text, numbered by conversation (one per session, in log order) and turn. No session IDs or
times are written. A question already asked earlier in the log is kept with repeat = yes, as before, except where a
whole conversation is only a repeat of a question listed in SKIP (the owner's instruction of 2026-11-22: skip the
repeated Yale admission-rate question); such a conversation is left out and later conversations are numbered on.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_FROM_ROW = 108                    # the skip applies to rows added after the first 107 (the earlier file is unchanged)
SKIP = {"What was Yale’s admission rate in fall 2024?"}


def main():
    log = list(csv.DictReader(open(ROOT / "docs" / "question_log.csv", encoding="utf-8-sig")))
    sessions, seen, out = {}, set(), []
    turns = {}
    for i, row in enumerate(log, 1):
        q = " ".join(row["question"].split())          # trimmed, line breaks as spaces, as in the earlier file
        repeat = q in seen
        seen.add(q)
        sid = row["session_id"]
        if i >= SKIP_FROM_ROW and sid not in sessions and q in SKIP and repeat:
            rest = [r for r in log[i:] if r["session_id"] == sid]
            if not rest:                        # the whole conversation is this one repeated question
                continue
        if sid not in sessions:
            sessions[sid] = len(sessions) + 1
        turns[sid] = turns.get(sid, 0) + 1
        out.append(dict(conversation=sessions[sid], turn=turns[sid], question=q, repeat="yes" if repeat else "no"))
    with open(ROOT / "docs" / "test_questions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["conversation", "turn", "question", "repeat"])
        w.writeheader()
        w.writerows(sorted(out, key=lambda r: (r["conversation"], r["turn"])))
    print(len(out), "rows in", len(sessions), "conversations")


if __name__ == "__main__":
    main()
