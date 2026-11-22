"""Part 5a: what stacking the ten releases found. Reads the local database only; changes nothing.

    python scripts/stack_report.py            writes docs/reports/stage5a/*.csv and prints the summary

Writes:
  rows_by_table_year.csv   loaded rows per local table and year, against the source table's row count
  type_changes.csv         columns stored as a number in some years and as text in others
  tables_by_year.csv       tables present only in some years
  variables_by_year.csv    variables added, retired, or renamed (a retired variable and a new one with the same
                           codebook title in the next year) between consecutive years, per table
"""
import csv
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config

OUT = ROOT / "docs" / "reports" / "stage5a"


def write(name, rows, fields):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def norm(title):
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower().replace("20", "")).strip()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
    years = [y for (y,) in db.execute("SELECT year FROM _releases ORDER BY year")]

    # 1. rows per table and year, against the source
    reg = db.execute("SELECT local_table, source_table, kind, year, source_rows, loaded_rows FROM _tables ORDER BY local_table, year").fetchall()
    write("rows_by_table_year.csv", [dict(local_table=t, source_table=s, kind=k, year=y, source_rows=a, loaded_rows=b,
                                          match="yes" if a == b else "NO") for t, s, k, y, a, b in reg],
          ["local_table", "source_table", "kind", "year", "source_rows", "loaded_rows", "match"])
    mismatches = [r for r in reg if r[4] != r[5]]

    # 2. columns whose stored type changes between years
    types = defaultdict(dict)
    for t, r, c, st in db.execute("SELECT c.local_table, t.year, c.column, c.stored_type FROM _columns c "
                                  "JOIN _tables t ON t.source_table = c.source_table AND t.release = c.release"):
        types[(t, c.upper())][r] = st
    changes = []
    for (t, c), by in sorted(types.items()):
        kinds = {("number" if s in ("INTEGER", "REAL", "NUMERIC", "FLOAT", "DOUBLE") else "text") for s in by.values()}
        if len(kinds) > 1:
            changes.append(dict(local_table=t, column=c, **{str(y): by.get(y, "") for y in years}))
    write("type_changes.csv", changes, ["local_table", "column"] + [str(y) for y in years])

    # 3. tables present only in some years
    present = defaultdict(set)
    for t, y, k in db.execute("SELECT local_table, year, kind FROM _tables"):
        present[(t, k)].add(y)
    partial = [dict(local_table=t, kind=k, years=" ".join(map(str, sorted(ys))), missing=" ".join(map(str, sorted(set(years) - ys))))
               for (t, k), ys in sorted(present.items()) if set(ys) != set(years)]
    write("tables_by_year.csv", partial, ["local_table", "kind", "years", "missing"])

    # 4. variables added, retired or renamed between consecutive years
    cols = defaultdict(lambda: defaultdict(set))
    for t, y, c in db.execute("SELECT c.local_table, t.year, UPPER(c.column) FROM _columns c "
                              "JOIN _tables t ON t.source_table = c.source_table AND t.release = c.release WHERE t.kind = 'data'"):
        cols[t][y].add(c)
    titles = {}
    for table, var, title, y in db.execute("SELECT UPPER(TableName), UPPER(VarName), varTitle, year FROM VARTABLE"):
        titles[(table, var, y)] = title
    src = {(t, y): s.upper() for t, s, k, y, _, _ in reg}
    changes_v = []
    for t, by in sorted(cols.items()):
        ys = sorted(by)
        for a, b in zip(ys, ys[1:]):
            gone, new = by[a] - by[b], by[b] - by[a]
            t_gone = {v: norm(titles.get((src.get((t, a)), v, a))) for v in gone}
            t_new = {v: norm(titles.get((src.get((t, b)), v, b))) for v in new}
            renamed = {}
            for v, tt in t_gone.items():
                match = [w for w, tw in t_new.items() if tt and tw == tt and w not in renamed.values()]
                if len(match) == 1:
                    renamed[v] = match[0]
            for v in sorted(gone):
                changes_v.append(dict(local_table=t, from_year=a, to_year=b, change="renamed" if v in renamed else "retired",
                                      variable=v, new_name=renamed.get(v, ""), title=titles.get((src.get((t, a)), v, a), "")))
            for v in sorted(new - set(renamed.values())):
                changes_v.append(dict(local_table=t, from_year=a, to_year=b, change="added", variable=v, new_name="",
                                      title=titles.get((src.get((t, b)), v, b), "")))
    write("variables_by_year.csv", changes_v, ["local_table", "from_year", "to_year", "change", "variable", "new_name", "title"])

    from collections import Counter
    print(f"years: {years}")
    print(f"tables x years: {len(reg)}; row-count mismatches: {len(mismatches)}")
    print(f"columns whose stored type changes between years: {len(changes)}")
    print(f"tables present only in some years: {len(partial)}")
    print("variable changes between consecutive years:", dict(Counter(r['change'] for r in changes_v)))
    print("size:", f"{config.LOCAL_DB.stat().st_size / 1e9:.2f} GB")
    for r in db.execute("SELECT year, release, status, seconds FROM _releases ORDER BY year"):
        print("  ", r)


if __name__ == "__main__":
    main()
