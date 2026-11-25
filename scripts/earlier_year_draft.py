"""Part 6.0, review point: the draft of two new measures.csv columns for the measures held as earlier-year columns.

    python scripts/earlier_year_draft.py     writes docs/reports/stage6/earlier_year_draft.csv and prints a summary

Some tables hold one figure for several years as separate columns, whose names differ only in a last digit (NPGRN2,
NPGRN1, NPGRN0: net price for {Y-1}, {Y-2}, {Y-3}). Such a set of columns is a family. In each family, the release's own
figure is the column with the latest period; the others are earlier-year columns. For every member of a family the
draft gives:
    own_column   the family's own column, TABLE.VARIABLE (the measure itself for the own column)
    years_back   how many years before the own column's period this column's period starts (0 for the own column)
A measure with no other year in its table (a family of one, such as the guaranteed tuition increase) is not an
earlier-year column and is left out. A row is marked unsure, with the reason, where the pattern does not hold cleanly:
two columns with the same period, a last digit that does not run in the same order as the periods, or titles that differ by more than
the year. Nothing here is loaded until the owner approves it.
"""
import csv
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config

OUT = ROOT / "docs" / "reports" / "stage6"


def start(period):
    """'{Y-2}-{Y-1:yy}' -> -2: the period's first year, counted from the release year."""
    m = re.match(r"\{Y([+-]\d+)?\}", period or "")
    return int(m.group(1) or 0) if m else None


def bare(title):
    """A title without its years, to compare the members of a family."""
    return " ".join(re.sub(r"\b(19|20)\d\d(-\d{2,4})?\b|\bprior year\b|\bcurrent year\b", "", title or "",
                           flags=re.I).split()).strip(" ,-").lower()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
    rows = db.execute('SELECT "table", variable, title, period FROM dict_measures WHERE period LIKE \'{Y%\'').fetchall()
    families = defaultdict(list)
    for table, var, title, period in rows:
        if start(period) is None:
            continue
        stem = var[:-1] if var[-1:].isdigit() else var
        families[(table, stem)].append(dict(table=table, variable=var, title=title, period=period, at=start(period),
                                            digit=var[-1] if var[-1:].isdigit() else ""))
    out = []
    for (table, stem), members in sorted(families.items()):
        why = []
        if len(members) == 1:                           # one year only: not an earlier-year column
            continue
        if len({m["at"] for m in members}) < len(members):
            why.append("two columns with the same period")
        by_digit = sorted((m for m in members if m["digit"]), key=lambda m: m["digit"])
        if [m["at"] for m in by_digit] != sorted(m["at"] for m in by_digit):
            why.append("the last digit does not run in the same order as the periods")
        if len({bare(m["title"]) for m in members}) > 1:
            why.append("the titles differ by more than the year")
        own = max(members, key=lambda m: m["at"])
        for m in sorted(members, key=lambda m: -m["at"]):
            out.append(dict(table=table, variable=m["variable"], title=m["title"], period=m["period"],
                            own_column=f"{table}.{own['variable']}", years_back=own["at"] - m["at"],
                            sure="no" if why else "yes", why="; ".join(why)))
    with open(OUT / "earlier_year_draft.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    by_table = defaultdict(Counter)
    for r in out:
        kind = ("unsure" if r["sure"] == "no" else "own column" if r["years_back"] == 0 else f"{r['years_back']} back")
        by_table[r["table"]][kind] += 1
    print(f"{len(out)} measures in {len({r['own_column'] for r in out})} families")
    for t, c in sorted(by_table.items()):
        print(f"  {t}: {dict(sorted(c.items()))}")
    print("unsure:" if any(r["sure"] == "no" for r in out) else "unsure: none")
    for r in out:
        if r["sure"] == "no":
            print(f"  {r['table']}.{r['variable']} | {r['period']} | {r['title'][:70]} | {r['why']}")


if __name__ == "__main__":
    main()
