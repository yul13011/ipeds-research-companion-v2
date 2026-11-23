"""Part 5b: did the student-aid totals change definition when the degree-seeking split began? Reads only.

    python scripts/aid_split_check.py     writes docs/reports/stage5b/aid_split_parts.csv and aid_split_national.csv

1. Parts against totals, school by school, in every year both exist: degree-seeking + non-degree-seeking = total.
2. National totals (each year's own national universe) of undergraduates in the aid cohort, Pell recipients, grant
   recipients and federal-loan recipients, with the change from the year before, and the aid cohort as a share of the
   12-month undergraduate headcount for the same July-to-June year (a definition change would move this share).
The release year is the database `year`: the 2022-23 release (year 2022) reports aid year 2021-22.
"""
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config

OUT = ROOT / "docs" / "reports" / "stage5b"
PARTS = [  # total, degree-seeking part, non-degree-seeking part, what it is
    ("SCUGRAD", "SCUGDGSK", "SCUGNDGS", "undergraduates in the aid cohort"),
    ("SCFA2", "SCFA2DG", "SCFA2ND", "undergraduates, fall cohort"),
    ("SCFY2", "SCFY2DG", "SCFY2ND", "undergraduates, full-year cohort"),
    ("UAGRNTN", "UDGAGRNTN", "UNDAGRNTN", "undergraduates awarded grant aid"),
    ("UPGRNTN", "UDGPGRNTN", "UNDPGRNTN", "undergraduates awarded Pell grants"),
    ("UFLOANN", "UDGFLOANN", "UNDFLOANN", "undergraduates awarded federal loans"),
]
TOTALS = [("SCUGRAD", "undergraduates in the aid cohort"), ("UPGRNTN", "Pell recipients"),
          ("UAGRNTN", "grant recipients"), ("UFLOANN", "federal-loan recipients")]


def table_for(db, column, year):
    row = db.execute("SELECT c.local_table FROM _columns c JOIN _tables t ON t.source_table = c.source_table AND "
                     "t.release = c.release WHERE UPPER(c.column) = ? AND t.year = ?", (column, year)).fetchone()
    return row[0] if row else None


def main():
    db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
    years = [y for (y,) in db.execute("SELECT year FROM _releases ORDER BY year")]
    parts = []
    for total, dg, nd, what in PARTS:
        for y in years:
            t = table_for(db, total, y)
            if not t or table_for(db, dg, y) != t or table_for(db, nd, y) != t:
                continue
            rows = db.execute(f'SELECT UNITID, "{total}", "{dg}", "{nd}" FROM main."{t}" WHERE year = ?', (y,)).fetchall()
            complete = [r for r in rows if None not in r[1:]]
            off = [r for r in complete if abs((r[2] + r[3]) - r[1]) > 0.5]
            parts.append(dict(total=total, parts=f"{dg} + {nd}", what=what, release_year=y, aid_year=f"{y - 1}-{y % 100:02d}",
                              schools=len(rows), with_all_three=len(complete), parts_differ=len(off),
                              examples="; ".join(f"{u}: {d:g} + {n:g} vs {tt:g}" for u, tt, d, n in off[:3])))
    with open(OUT / "aid_split_parts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(parts[0]))
        w.writeheader()
        w.writerows(parts)

    national = []
    prev = {}
    for y in years:
        universe = {u for (u,) in db.execute("SELECT unitid FROM group_membership WHERE group_name='National universe' AND year=?", (y,))}
        row = dict(release_year=y, aid_year=f"{y - 1}-{y % 100:02d}", schools_in_universe=len(universe))
        for col, what in TOTALS:
            t = table_for(db, col, y)
            vals = {u: v for u, v in db.execute(f'SELECT UNITID, "{col}" FROM main."{t}" WHERE year = ?', (y,)) if v is not None and u in universe}
            total = sum(vals.values())
            row[col] = round(total)
            row[f"{col}_schools"] = len(vals)
            row[f"{col}_change"] = f"{100 * (total / prev[col] - 1):+.1f}%" if prev.get(col) else ""
            prev[col] = total
        t = table_for(db, "UNDUPUG", y)
        ug = sum(v for u, v in db.execute(f'SELECT UNITID, UNDUPUG FROM main."{t}" WHERE year = ?', (y,)) if v and u in universe) if t else None
        row["ug_12month"] = round(ug) if ug else ""
        row["aid_cohort_share_of_12month"] = f"{100 * row['SCUGRAD'] / ug:.1f}%" if ug else ""
        row["pell_share_of_aid_cohort"] = f"{100 * row['UPGRNTN'] / row['SCUGRAD']:.1f}%"
        national.append(row)
    with open(OUT / "aid_split_national.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(national[0]))
        w.writeheader()
        w.writerows(national)

    print("parts against totals:")
    for p in parts:
        print(f"  {p['release_year']} (aid {p['aid_year']}) {p['total']:<8} = {p['parts']:<22} schools {p['with_all_three']:>5}, differ {p['parts_differ']:>4}  {p['examples'][:70]}")
    print("national totals:")
    for r in national:
        print(f"  {r['release_year']} aid {r['aid_year']}: cohort {r['SCUGRAD']:>10,} ({r['SCUGRAD_change']:>6})  Pell {r['UPGRNTN']:>9,} ({r['UPGRNTN_change']:>6})"
              f"  grant {r['UAGRNTN']:>9,} ({r['UAGRNTN_change']:>6})  loan {r['UFLOANN']:>9,} ({r['UFLOANN_change']:>6})"
              f"  cohort/12-month ug {r['aid_cohort_share_of_12month']:>6}  Pell/cohort {r['pell_share_of_aid_cohort']}")


if __name__ == "__main__":
    main()
