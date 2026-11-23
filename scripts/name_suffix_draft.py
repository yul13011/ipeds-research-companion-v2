"""Proposal (not applied): tell apart the measures that still share a shown name after the table subjects, using
IPEDS's own long descriptions. Owner decision 2026-11-23, item 3: "show me examples before applying it".

    python scripts/name_suffix_draft.py     writes docs/reports/stage5b2/name_suffix_draft.csv

The rule: for each measure in a group that shares a name, take the shortest run of words (one to five) from its own
long description that appears in none of the others' descriptions, and add it in brackets: "name (words)". Only the
codebook's wording is read. A group is resolved when every member gets words of its own.
"""
import csv
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config

STOP = {"the", "of", "and", "or", "a", "an", "in", "for", "to", "by", "is", "are", "this", "that", "who", "which",
        "with", "on", "at", "as", "be", "were", "was", "data", "number", "institution", "students"}


def words(text):
    return re.findall(r"[a-z0-9][a-z0-9'-]*", (text or "").lower())


def own_words(mine, others):
    """The shortest run of words in `mine` found in none of `others` (runs must not start or end on a common word)."""
    text = words(mine)
    others = [" ".join(words(o)) for o in others]
    for n in range(1, 6):
        for i in range(len(text) - n + 1):
            run = text[i:i + n]
            if run[0] in STOP or run[-1] in STOP:
                continue
            phrase = " ".join(run)
            if all(f" {phrase} " not in f" {o} " for o in others):
                return phrase
    return None


def main():
    db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
    desc = {f"{t}.{v}": (s, d) for t, v, s, d in db.execute(
        'SELECT "table", variable, shown_name, long_description FROM dict_measures')}
    out, resolved = [], 0
    groups = [ms.split("; ") for (ms,) in db.execute("SELECT measures FROM name_clashes ORDER BY n DESC, name")]
    for ms in groups:
        got = {m: own_words(desc[m][1], [desc[o][1] for o in ms if o != m]) for m in ms}
        ok = all(got.values()) and len(set(got.values())) == len(ms)
        resolved += ok
        for m in ms:
            out.append(dict(measure=m, shown_name=desc[m][0], proposed=f"{desc[m][0]} ({got[m]})" if got[m] else "",
                            resolved="yes" if ok else "no", description=(desc[m][1] or "")[:220]))
    with open(ROOT / "docs" / "reports" / "stage5b2" / "name_suffix_draft.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"{resolved} of {len(groups)} shared names resolved by the rule")


if __name__ == "__main__":
    main()
