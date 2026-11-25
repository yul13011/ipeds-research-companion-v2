"""After Stage 5 (proposal b): how do the earlier-year columns of one release compare with the figures the earlier
releases published for the same year?

Some tables hold a few earlier years as columns of their own: in release Y, net price for Y-1 (NPGRN2), Y-2 (NPGRN1)
and Y-3 (NPGRN0); tuition and charges for the next year (..3), this year (..2) and two before; and so on. The same year
was also published by the earlier release as its own latest column. This compares the two, school by school.

    python scripts/earlier_year_columns.py      prints the summary and writes docs/reports/stage5g/earlier_year_columns.csv;
                                                the school-by-school detail goes to logs/earlier_year_columns_detail.csv
                                                (untracked: it is data, not a result)
"""
import csv
import re
import sqlite3
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config

# (label, column in release Y, how many years back it is, the earlier release's own column for that year)
PAIRS = [
    ("Net price, grant-aided students, private (NPGRN)", "NPGRN1", 1, "NPGRN2"),
    ("Net price, grant-aided students, private (NPGRN)", "NPGRN0", 2, "NPGRN2"),
    ("Net price, grant-aided students, public (NPIST)", "NPIST1", 1, "NPIST2"),
    ("Net price, grant-aided students, public (NPIST)", "NPIST0", 2, "NPIST2"),
    ("Students awarded grant aid, full-time first-time (GISTN)", "GISTN1", 1, "GISTN2"),
    ("Published in-district tuition and fees (CHG1AY)", "CHG1AY2", 1, "CHG1AY3"),
    ("Published in-district tuition and fees (CHG1AY)", "CHG1AY1", 2, "CHG1AY3"),
    ("Tuition and fees, derived (TUFEYR)", "TUFEYR2", 1, "TUFEYR3"),
    ("Tuition and fees, derived (TUFEYR)", "TUFEYR1", 2, "TUFEYR3"),
]
EXAMPLES = {130794: "Yale University", 166027: "Harvard University", 204796: "Ohio State University-Main Campus",
            127200: "Front Range Community College"}


def main():
    db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
    year_of = {r: int(re.search(r"(\d{4})-", r).group(1)) for (r,) in db.execute("SELECT DISTINCT release FROM _columns")}
    where = {}
    for table, column, release in db.execute('SELECT local_table, UPPER("column"), release FROM _columns'):
        where[(column, year_of[release])] = table

    def values(column, year):
        table = where.get((column, year))
        if not table:
            return {}
        return {u: v for u, v in db.execute(f'SELECT UNITID, "{column}" FROM "{table}" WHERE year = ?', (year,))
                if isinstance(v, (int, float))}

    out, summary = [], []
    for label, col, back, own in PAIRS:
        pairs, examples = [], {}
        for y in range(2016, 2025):
            later, earlier = values(col, y), values(own, y - back)
            for u in later.keys() & earlier.keys():
                pairs.append((later[u], earlier[u]))
                if u in EXAMPLES and y == 2024:
                    examples[EXAMPLES[u]] = (later[u], earlier[u])
                out.append(dict(measure=label, column=f"{col} in release {y}", compared_with=f"{own} in release {y - back}",
                                unitid=u, later=later[u], earlier=earlier[u]))
        if not pairs:
            continue
        same = sum(a == b for a, b in pairs)
        rel = [abs(a - b) / abs(b) for a, b in pairs if b]
        summary.append((label, col, back, own, len(pairs), same, sum(r <= 0.01 for r in rel), statistics.median(rel) if rel else 0,
                        sum(r > 0.10 for r in rel), examples))
    with open(config.LOG_DIR / "earlier_year_columns_detail.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    with open(ROOT / "docs" / "reports" / "stage5g" / "earlier_year_columns.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["measure", "column in release Y", "years back", "compared with", "school-years", "identical",
                    "within 1%", "more than 10% apart", "median gap (%)"])
        for label, col, back, own, n, same, close, med, far, ex in summary:
            w.writerow([label, col, back, f"{own} of release Y-{back}", n, same, close, far, round(100 * med, 2)])
    for label, col, back, own, n, same, close, med, far, ex in summary:
        print(f"{label}: {col} (release Y) against {own} (release Y-{back}): {n} school-years; identical {same} ({100 * same / n:.1f}%);"
              f" within 1% {close} ({100 * close / n:.1f}%); more than 10% apart {far} ({100 * far / n:.1f}%); median gap {100 * med:.2f}%")
        for name, (a, b) in ex.items():
            print(f"    {name}, release 2024-25: {col} = {a:,.0f}; release {2024 - back}-{(2025 - back) % 100:02d} published {b:,.0f}")


if __name__ == "__main__":
    main()
