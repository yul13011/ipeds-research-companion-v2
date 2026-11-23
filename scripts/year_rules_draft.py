"""Part 5b gap list: draft the period text as patterns counted from the release year, for review. Changes nothing.

    python scripts/year_rules_draft.py      writes docs/reports/stage5b/year_rules_draft.csv

Pattern words: {Y} is the release year (2024 for the 2024-25 release); {Y-1} and {Y+1} count from it; {Y:yy} and
{Y+1:yy} are the last two digits ("24", "25"). Each draft is shown filled in for 2024 (it must equal today's text)
and for 2015, so the pattern can be checked by eye.
"""
import csv
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config

OUT = ROOT / "docs" / "reports" / "stage5b"
BASE = 2024


def pattern(text):
    """2024 -> {Y}, 2023 -> {Y-1}, 2025 -> {Y+1}; a two-digit year after a dash -> {Y:yy} or {Y+1:yy}."""
    def full(m):
        d = int(m.group(0)) - BASE
        return "{Y}" if d == 0 else f"{{Y{d:+d}}}"
    out = re.sub(r"(?<=-)(\d\d)\b", lambda m: "{Y:yy}" if int(m.group(1)) == BASE % 100 else
                 ("{Y+1:yy}" if int(m.group(1)) == (BASE + 1) % 100 else ("{Y-1:yy}" if int(m.group(1)) == (BASE - 1) % 100 else m.group(0))), text)
    return re.sub(r"(?:19|20)\d\d", full, out)


def fill(p, year):
    def one(m):
        off = int(m.group(1) or 0)
        y = year + off
        return f"{y % 100:02d}" if m.group(2) else str(y)
    return re.sub(r"\{Y([+-]\d+)?(:yy)?\}", one, p)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
    rows = []
    for t, period, cohort in db.execute('SELECT "table", period, entering_cohort FROM dict_year_meaning ORDER BY "table"'):
        p = pattern(period or "")
        rows.append(dict(file="year_meaning.csv", key=t, column="period", today=period, draft=p, filled_2024=fill(p, 2024),
                         filled_2015=fill(p, 2015), same_as_today="yes" if fill(p, 2024) == period else "NO",
                         note="entering cohort already an offset: " + cohort if cohort else ""))
    for t, v, period in db.execute('SELECT "table", variable, period FROM dict_measures WHERE in_first_version = \'yes\' '
                                   "AND period IS NOT NULL ORDER BY 1, 2"):
        p = pattern(period)
        rows.append(dict(file="measures.csv", key=f"{t}.{v}", column="period", today=period, draft=p, filled_2024=fill(p, 2024),
                         filled_2015=fill(p, 2015), same_as_today="yes" if fill(p, 2024) == period else "NO", note=""))
    with open(OUT / "year_rules_draft.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "key", "column", "today", "draft", "filled_2024", "filled_2015", "same_as_today", "note"])
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "period cells;", sum(r["same_as_today"] == "NO" for r in rows), "do not reproduce today's text")
    for r in rows[:6] + [r for r in rows if r["file"] == "measures.csv"][:4]:
        print(f"  {r['key']:<28} {r['today']:<42} -> {r['draft']:<44} 2015: {r['filled_2015']}")


if __name__ == "__main__":
    main()
