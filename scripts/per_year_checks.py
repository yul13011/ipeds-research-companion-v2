"""Part 5b gap list: run the dictionary's tests of category rows, summary-to-detailed links and breakdown sets in each
year, not only the latest. Run it on a COPY of the database: the tests rebuild the dictionary's derived tables for each year in turn.

    python scripts/per_year_checks.py COPY.sqlite     writes docs/reports/stage5b/per_year_checks.csv
"""
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import build_dictionary as bd

OUT = ROOT / "docs" / "reports" / "stage5b"


def at_year(db, year):
    for (t,) in db.execute("SELECT DISTINCT local_table FROM main._tables").fetchall():
        db.execute(f'DROP VIEW IF EXISTS temp."{t}"')
        db.execute(f'CREATE TEMP VIEW "{t}" AS SELECT * FROM main."{t}" WHERE year = {int(year)}')


def main():
    path = sys.argv[1]
    db = sqlite3.connect(path)
    db.isolation_level = None                           # explicit transactions, so each year can be rolled back
    years = [y for (y,) in db.execute("SELECT year FROM _releases ORDER BY year")]
    if len(sys.argv) > 2:                               # optional: only these years
        years = [y for y in years if str(y) in sys.argv[2].split(",")]
    rows = []
    for y in years:
        db.execute("BEGIN")
        at_year(db, y)
        row = dict(year=y)
        try:
            problems = bd.build_row_keys(db)
            row["row_key_problems"] = "; ".join(problems)
            if True:                                    # the link and set tests run even when a table's keys fail
                bd.build_detail_links(db)
                bd.build_breakdown_sets(db)
                links = dict(db.execute("SELECT status, COUNT(*) FROM detail_links GROUP BY 1").fetchall())
                sets = dict(db.execute("SELECT status, COUNT(*) FROM breakdown_sets GROUP BY 1").fetchall())
                row.update(links_loaded=links.get("loaded", 0), links_failed=links.get("failed", 0),
                           links_failed_list=" ".join(m for (m,) in db.execute("SELECT measure FROM detail_links WHERE status='failed'")),
                           sets_loaded=sets.get("loaded", 0), sets_additive=sets.get("additive", 0), sets_failed=sets.get("failed", 0),
                           sets_failed_list="; ".join(f"{s} ({t})" for s, t in db.execute(
                               "SELECT set_name, \"table\" FROM breakdown_sets WHERE status='failed' ORDER BY 2, 1")))
        except Exception as e:                          # a table or column missing in that year
            row["error"] = f"{type(e).__name__}: {e}"[:300]
        if db.in_transaction:                           # some builders commit on their own; the copy is disposable
            db.execute("ROLLBACK")
        rows.append(row)
        print(y, {k: v for k, v in row.items() if not k.endswith("_list")})
    OUT.mkdir(parents=True, exist_ok=True)
    fields = ["year", "row_key_problems", "links_loaded", "links_failed", "sets_loaded", "sets_additive", "sets_failed",
              "error", "links_failed_list", "sets_failed_list"]
    old = {}
    if (OUT / "per_year_checks.csv").exists():          # keep the years not run this time
        old = {r["year"]: r for r in csv.DictReader(open(OUT / "per_year_checks.csv", encoding="utf-8"))}
    for r in rows:
        old[str(r["year"])] = r
    rows = [old[k] for k in sorted(old)]
    with open(OUT / "per_year_checks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
