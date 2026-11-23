"""Part 5b: every rate in every year (owner decision 8). Reads only.

    python scripts/rates_by_year.py      writes docs/reports/stage5b/rates_by_year.csv, ready_made_by_year.csv
                                         and universe_by_year.csv

1. The national figure of each rates.csv row in each year, computed from its counts over that year's national
   universe (and the group the rate applies to), the way the app computes a group figure. Compared with the NCES
   Trend Generator files where they have a figure for that year.
2. Where IPEDS gives a ready-made rate for one school, that rate against the rate computed from the school's own
   counts, each year: how many schools differ by more than rounding.
3. The national universe in each year against the NCES count of institutions (question 1).
Where each count is stored in each year comes from measure_years (built by build_dictionary.py), so the
reorganised cost and aid measures are read from their earlier tables.
"""
import csv
import glob
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import openpyxl

import config
from benchmarks import source_year, TESTS

OUT = ROOT / "docs" / "reports" / "stage5b"
NCES_Q = {  # test specification: which NCES Trend Generator file publishes each rate (fractions; scaled to percent)
    "Full-time retention rate": 32, "Part-time retention rate": 33, "Admission rate": 102, "Admissions yield": 103,
    ("Graduation rate within 150% of normal time", "Four or more years"): 19, "Bachelor's six-year graduation rate": 20,
    ("Graduation rate within 150% of normal time", "At least 2 but less than 4 years"): 21,
    "Percent of undergraduates awarded Pell grants": 35, "Percent of undergraduates awarded federal loans": 37,
    "Percent of full-time first-time students awarded any aid": 34, "Award within eight years (Outcome Measures)": 200,
    "Average Pell grant": 36,
}


def nces_series(q):
    """{release year: published value} from one Trend Generator file."""
    path = glob.glob(str(TESTS / "NCES" / f"TrendGenerator-q{q}-*.xlsx"))
    out = {}
    if path:
        for cells in openpyxl.load_workbook(path[0], read_only=True, data_only=True).active.iter_rows(values_only=True):
            first = str(cells[0] or "").strip()
            if re.fullmatch(r"\d{4}(?:-\d{2,4})?", first) and len(cells) > 1 and isinstance(cells[1], (int, float)):
                out[source_year(q, first)] = float(cells[1])
    return out


def main():
    db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
    years = [y for (y,) in db.execute("SELECT DISTINCT year FROM measure_years ORDER BY year")]
    where = {(m, y): (t, v) for m, y, t, v in db.execute('SELECT measure, year, "table", variable FROM measure_years')}
    members = lambda g, y: {u for (u,) in db.execute("SELECT unitid FROM group_membership WHERE group_name=? AND year=?", (g, y))}

    def values(measure, y, column=None, code=None):
        loc = where.get((measure, y))
        if not loc:
            return None
        t, v = loc
        sql = f'SELECT UNITID, "{v}" FROM main."{t}" WHERE year = ? AND "{v}" IS NOT NULL'
        args = [y]
        if column:
            sql += f' AND CAST("{column}" AS TEXT) = ?'
            args.append(code)
        return dict(db.execute(sql, args).fetchall())

    rates, ready = [], []
    for rate, rate_measure, num, den, cat, ncode, dcode, method, applies, unit in db.execute(
            "SELECT rate, rate_measure, numerator, denominator, category_column, numerator_code, denominator_code, method, "
            "applies_to, unit FROM dict_rates").fetchall():
        q = NCES_Q.get((rate, applies)) or NCES_Q.get(rate)
        published = nces_series(q) if q else {}
        for y in years:
            n, d = values(num, y, cat, ncode), values(den, y, cat, dcode)
            row = dict(rate=rate, applies_to=applies or "", release_year=y, nces_question=f"q{q}" if q else "")
            if n is None or d is None:
                row["status"] = "not collected this year"
                rates.append(row)
                continue
            universe = members("National universe", y) & (members(applies, y) if applies else members("National universe", y))
            both = [u for u in universe if u in n and u in d and d[u] and d[u] > 0]
            if method == "weighted average":
                figure = sum(n[u] * d[u] for u in both) / sum(d[u] for u in both) if both else None
            else:
                figure = sum(n[u] for u in both) / sum(d[u] for u in both) if both else None
            shown = figure * 100 if figure is not None and unit == "percent" else figure
            row.update(schools=len(both), figure=round(shown, 2) if shown is not None else "")
            if y in published:
                expect = published[y] * 100 if unit == "percent" else published[y]
                diff = shown - expect if shown is not None else None
                tol = 0.05 if unit == "percent" else 0.5
                row.update(nces=round(expect, 2), difference=round(diff, 2) if diff is not None else "",
                           status="match" if diff is not None and abs(diff) <= tol else "differs")
            else:
                row["status"] = "no NCES figure"
            rates.append(row)
            if rate_measure and method != "weighted average":   # a weighted average's numerator is the school's own figure
                r = values(rate_measure, y)
                if r:
                    scale = 100 if unit == "percent" else 1
                    compared = [u for u in r if u in n and u in d and d[u] and d[u] > 0]
                    off = [u for u in compared if abs(r[u] - scale * n[u] / d[u]) > (0.5 if scale == 100 else 1)]
                    ready.append(dict(rate=rate, rate_measure=rate_measure, applies_to=applies or "", release_year=y,
                                      schools_compared=len(compared), differ_beyond_rounding=len(off),
                                      share=f"{100 * len(off) / len(compared):.1f}%" if compared else "",
                                      examples="; ".join(f"{u}: {r[u]:g} vs {scale * n[u] / d[u]:.1f}" for u in off[:3])))

    universe = []
    published = nces_series(1)
    for y in years:
        n = len(members("National universe", y))
        universe.append(dict(release_year=y, national_universe=n, nces=published.get(y, ""),
                             difference=n - published[y] if y in published else ""))

    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (("rates_by_year.csv", rates), ("ready_made_by_year.csv", ready), ("universe_by_year.csv", universe)):
        fields = list(dict.fromkeys(k for r in rows for k in r))
        with open(OUT / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    compared = [r for r in rates if r["status"] in ("match", "differs")]
    print(f"rates: {len(compared)} rate-years with an NCES figure, {sum(r['status'] == 'match' for r in compared)} match")
    for r in compared:
        if r["status"] == "differs":
            print(f"  differs: {r['rate']} {r['applies_to']} {r['release_year']}: {r['figure']} vs NCES {r['nces']}")
    print("ready-made rates, schools differing beyond rounding, by year:")
    for r in ready:
        if r["differ_beyond_rounding"]:
            print(f"  {r['rate_measure']} {r['release_year']}: {r['differ_beyond_rounding']} of {r['schools_compared']}")
    print("national universe:", [(r["release_year"], r["national_universe"], r["nces"]) for r in universe])


if __name__ == "__main__":
    main()
