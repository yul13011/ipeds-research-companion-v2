"""Part 5b gap list: what the dictionary needs before it works across all ten years. Reads only; loads nothing.

    python scripts/gaps_5b.py        writes docs/reports/stage5b/*.csv and prints a summary

Writes:
  columns_by_year.csv       every table.column the dictionary names, and the years it is missing
  measure_years.csv         every first-version measure: the years with data (at least one school with a value)
  fixed_years.csv           dictionary cells written with a fixed year that will need an offset from the release year
  code_changes.csv          category codes the dictionary uses that are absent, or new, in an earlier year
  directory_by_year.csv     schools, national universe, comparison groups, closures and name changes per year
  cost_aid_map.csv          the 2024-25 cost and aid variables matched to the earlier tables (by name, then by title)
  cost_aid_values.csv       where an old and a new table report the same aid year: schools whose values differ
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

OUT = ROOT / "docs" / "reports" / "stage5b"
YEAR = re.compile(r"(?:19|20)\d\d(?:-\d\d)?")
OLD = ["IC_AY", "IC_PY", "SFA_P1", "SFA_P2", "DRVIC", "IC"]   # IC: some charges moved from IC to COST1 in 2024-25
NEW = ["COST1", "COST2_FINANCIALAID", "COST2_NETPRICE", "SFA", "DRVCOST"]


def write(name, rows, fields):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
    q = lambda sql, *a: db.execute(sql, a).fetchall()
    years = [y for (y,) in q("SELECT year FROM _releases ORDER BY year")]
    latest = years[-1]
    cols_in = defaultdict(set)                          # (TABLE, COLUMN) -> years the column exists
    for t, c, y in q("SELECT c.local_table, UPPER(c.column), t.year FROM _columns c JOIN _tables t "
                     "ON t.source_table = c.source_table AND t.release = c.release"):
        cols_in[(t.upper(), c)].add(y)
    tables_in = defaultdict(set)
    for t, y in q("SELECT local_table, year FROM _tables"):
        tables_in[t.upper()].add(y)

    # 1. every table.column the dictionary names, and the years it is missing
    named = defaultdict(set)
    for t, v, first in q('SELECT "table", variable, in_first_version FROM dict_measures'):
        if first == "yes":
            named[(t.upper(), v.upper())].add("measures.csv")
    for t, c in q('SELECT DISTINCT "table", "column" FROM dict_category_codes'):
        named[(t.upper(), c.upper())].add("category_codes.csv")
    for t, c in q('SELECT DISTINCT "table", "column" FROM dict_school_groups WHERE "table" IS NOT NULL AND "column" IS NOT NULL'):
        for col in (x.strip() for x in c.split(",") if x.strip()):
            named[(t.upper(), col.upper())].add("school_groups.csv")
    for row in q("SELECT numerator, denominator FROM dict_rates"):
        for ref in row:
            if ref and "." in ref:
                t, _, c = ref.partition(".")
                named[(t.upper(), c.upper())].add("rates.csv")
    out = []
    for (t, c), where in sorted(named.items()):
        have = cols_in.get((t, c), set())
        missing = [y for y in years if y not in have]
        if missing:
            out.append(dict(table=t, column=c, named_in="; ".join(sorted(where)), years_present=" ".join(map(str, sorted(have))),
                            years_missing=" ".join(map(str, missing)),
                            table_missing=" ".join(str(y) for y in missing if y not in tables_in.get(t, set()))))
    write("columns_by_year.csv", out, ["table", "column", "named_in", "years_present", "years_missing", "table_missing"])
    n_named, n_gap = len(named), len(out)

    # 2. years with data, for every first-version measure
    measures = q('SELECT "table", variable, COALESCE(plain_name, title) FROM dict_measures WHERE in_first_version = \'yes\'')
    by_table = defaultdict(list)
    for t, v, n in measures:
        by_table[t].append((v, n))
    rows = []
    for t, vs in sorted(by_table.items()):
        have = {c for (tt, c), ys in cols_in.items() if tt == t.upper()}
        present = [v for v, _ in vs if v.upper() in have]
        data = defaultdict(set)
        if present:
            for i in range(0, len(present), 200):
                part = present[i:i + 200]
                sql = ", ".join(f'COUNT("{v}")' for v in part)
                for r in q(f'SELECT year, {sql} FROM main."{t}" GROUP BY year'):
                    for v, n in zip(part, r[1:]):
                        if n:
                            data[v].add(r[0])
        for v, name in vs:
            ys = sorted(data.get(v, set()))
            rows.append(dict(measure=f"{t}.{v}", name=name, years=" ".join(map(str, ys)), n_years=len(ys),
                             missing=" ".join(str(y) for y in years if y not in ys)))
    write("measure_years.csv", rows, ["measure", "name", "years", "n_years", "missing"])
    n_all = sum(1 for r in rows if r["n_years"] == len(years))
    n_latest_only = sum(1 for r in rows if r["years"] == str(latest))

    # 3. cells written with a fixed year
    fixed = []
    for r in q('SELECT "table", period, caveat FROM dict_year_meaning'):
        for col, val in zip(("period", "caveat"), r[1:]):
            if val and YEAR.search(val):
                fixed.append(dict(file="year_meaning.csv", key=r[0], column=col, value=val))
    for t, v, title, period in q('SELECT "table", variable, title, period FROM dict_measures WHERE in_first_version = \'yes\''):
        if period and YEAR.search(period):
            fixed.append(dict(file="measures.csv", key=f"{t}.{v}", column="period", value=period))
        if title and YEAR.search(title):
            fixed.append(dict(file="measures.csv", key=f"{t}.{v}", column="title", value=title))
    for term, reading, statement in q("SELECT term, reading, statement FROM dict_terms"):
        if statement and YEAR.search(statement):
            fixed.append(dict(file="terms.csv", key=f"{term} / {reading}", column="statement", value=statement))
    write("fixed_years.csv", fixed, ["file", "key", "column", "value"])

    # 4. category codes: absent or new in an earlier year, against the codes the dictionary uses (the latest year's)
    codes = defaultdict(set)
    for t, c, code in q('SELECT "table", UPPER("column"), code FROM dict_category_codes'):
        codes[(t, c)].add(str(code))
    seen = defaultdict(lambda: defaultdict(set))
    for t, c, code, y in q('SELECT local_table, UPPER("column"), code, year FROM value_labels'):
        if (t, c) in codes:
            seen[(t, c)][y].add(str(code).strip())
    changes = []
    for key, by_year in sorted(seen.items()):
        for y in years[:-1]:
            if y not in by_year:
                continue
            gone = sorted(codes[key] - by_year[y])
            new = sorted(by_year[y] - codes[key])
            if gone or new:
                changes.append(dict(table=key[0], column=key[1], year=y, n_dictionary_codes_absent=len(gone),
                                    absent=" ".join(gone[:25]), n_codes_only_then=len(new), only_then=" ".join(new[:25])))
    write("code_changes.csv", changes, ["table", "column", "year", "n_dictionary_codes_absent", "absent",
                                         "n_codes_only_then", "only_then"])

    # 5. the school directory over time
    universe = dict(q("SELECT year, COUNT(*) FROM group_membership WHERE group_name = 'National universe' GROUP BY year"))
    cg = dict(q("SELECT year, COUNT(DISTINCT UNITID) FROM main.CUSTOMCGIDS GROUP BY year"))
    flags = {y: sum(1 for (t, c), ys in cols_in.items() if t == "FLAGS" and c.startswith("PRCH_") and y in ys) for y in years}
    names = {u: n for u, n in q("SELECT UNITID, INSTNM FROM main.HD WHERE year = ?", latest)}
    rows, prev = [], None
    for y in years:
        here = {u: n for u, n in q("SELECT UNITID, INSTNM FROM main.HD WHERE year = ?", y)}
        row = dict(year=y, schools=len(here), national_universe=universe.get(y, 0), with_comparison_group=cg.get(y, 0),
                   parent_child_flag_columns=flags[y])
        if prev is not None:
            row["gone_since_last_year"] = len(set(prev) - set(here))
            row["new_since_last_year"] = len(set(here) - set(prev))
            row["renamed_since_last_year"] = sum(1 for u in set(prev) & set(here) if prev[u].strip().lower() != here[u].strip().lower())
        rows.append(row)
        prev = here
    write("directory_by_year.csv", rows, ["year", "schools", "national_universe", "with_comparison_group",
                                          "parent_child_flag_columns", "gone_since_last_year", "new_since_last_year",
                                          "renamed_since_last_year"])
    merged_cols = [c for (t, c) in cols_in if t == "HD" and c in ("NEWID", "DEATHYR", "CLOSEDAT", "CYACTIVE", "POSTSEC", "PSEFLAG")]

    # 6. cost and aid: the 2024-25 variables matched to the earlier tables
    title, title_any = {}, {}
    for tn, v, ti, y in q("SELECT UPPER(TableName), UPPER(VarName), varTitle, year FROM main.VARTABLE"):
        title[(tn, v, y)] = ti or ""
        title_any.setdefault((v, y), ti or "")         # the codebook may file a variable under another table name
    look = lambda tn, v, y: title.get((tn, v, y)) or title_any.get((v, y), "")
    src = {(t, y): s.upper() for t, s, y in q("SELECT local_table, source_table, year FROM _tables")}
    strip = lambda s: re.sub(r"\s+", " ", YEAR.sub("{YEAR}", s or "").lower()).strip()
    old_vars = {}
    for t in OLD:
        y = max(y for y in tables_in.get(t, {0}) if y < latest)   # the last earlier year that has the table
        for (tt, c), ys in cols_in.items():
            if tt == t and y in ys:
                old_vars[(t, c)] = (y, look(src.get((t, y)), c, y))
    mapping, pairs = [], []
    for t in NEW:
        for (tt, c), ys in sorted(cols_in.items()):
            if tt != t or latest not in ys or c in ("UNITID", "YEAR"):
                continue
            new_title = look(src.get((t, latest)), c, latest)
            same_name = [(ot, oc) for (ot, oc) in old_vars if oc == c]
            same_title = [(ot, oc) for (ot, oc), (_, ott) in old_vars.items() if strip(ott) and strip(ott) == strip(new_title)]
            exact = [(ot, oc) for (ot, oc), (_, ott) in old_vars.items()      # same aid year: the same title, naming a year
                     if ott and YEAR.search(new_title) and strip(ott) == strip(new_title)
                     and YEAR.findall(ott) == YEAR.findall(new_title)]
            base = lambda name: re.sub(r"\d$", "", name)      # the name without its year digit
            exact.sort(key=lambda m: base(m[1]) != base(c))
            name_and_title = [m for m in same_name if m in same_title]
            nearest = ""
            if exact:                                   # the same figure for the same year: the year digit in the
                old, how = exact[0], "same title and year"   # name moves with the release (CHG1AY3 -> CHG1AY2)
            elif name_and_title:
                old, how = name_and_title[0], "same name and title (the year moves with the release)"
            elif same_title:
                old, how = same_title[0], "same title, different name"
            elif same_name:
                old, how = same_name[0], "same name, different title: check"
            else:                                       # suggest the old title sharing the most words, for review
                words = lambda x: set(re.findall(r"[a-z]+", strip(x))) - {"year", "the", "of", "and", "or", "a"}
                nw = words(new_title)
                best = max(old_vars.items(), key=lambda kv: len(nw & words(kv[1][1])) / max(1, len(nw | words(kv[1][1]))),
                           default=None)
                score = len(nw & words(best[1][1])) / max(1, len(nw | words(best[1][1]))) if best else 0
                old, how = None, "no match"
                nearest = f"{best[0][0]}.{best[0][1]}: {best[1][1]} ({score:.0%} shared words)" if best and score >= 0.6 else ""
            mapping.append(dict(new=f"{t}.{c}", new_title=new_title, old=f"{old[0]}.{old[1]}" if old else "",
                                old_title=old_vars[old][1] if old else "", match=how, nearest_wording=nearest,
                                same_aid_year="yes" if old and old in exact else ""))
            for ot, oc in exact[:1]:                    # the best match only
                pairs.append((t, c, ot, oc, old_vars[(ot, oc)][0], new_title))
    write("cost_aid_map.csv", mapping, ["new", "new_title", "old", "old_title", "match", "same_aid_year", "nearest_wording"])
    values = []
    for t, c, ot, oc, oy, ti in pairs:
        a = dict(q(f'SELECT UNITID, "{c}" FROM main."{t}" WHERE year = ? AND "{c}" IS NOT NULL', latest))
        b = dict(q(f'SELECT UNITID, "{oc}" FROM main."{ot}" WHERE year = ? AND "{oc}" IS NOT NULL', oy))
        both = a.keys() & b.keys()
        differ = [u for u in both if abs(float(a[u]) - float(b[u])) > 0.5] if both and all(
            isinstance(a[u], (int, float)) and isinstance(b[u], (int, float)) for u in both) else \
            [u for u in both if str(a[u]) != str(b[u])]
        values.append(dict(new=f"{t}.{c}", old=f"{ot}.{oc}", old_year=oy, title=ti, schools_in_both=len(both),
                           schools_differ=len(differ), example=", ".join(f"{u}: {b[u]} -> {a[u]}" for u in sorted(differ)[:3])))
    write("cost_aid_values.csv", values, ["new", "old", "old_year", "title", "schools_in_both", "schools_differ", "example"])

    from collections import Counter
    print(f"dictionary columns missing in some year: {n_gap} of {n_named}")
    print(f"first-version measures: {len(rows and measures)}; with data in all ten years: {n_all}; in the latest year only: {n_latest_only}")
    print(f"cells with a fixed year: {len(fixed)} ({dict(Counter(f['file'] + ' ' + f['column'] for f in fixed))})")
    print(f"category columns whose codes change in an earlier year: {len({(c['table'], c['column']) for c in changes})}")
    print("directory:", [(r["year"], r["schools"], r["national_universe"], r["with_comparison_group"]) for r in rows[-10:]] if False else "")
    print("HD closure/merger columns:", merged_cols)
    print(f"cost and aid: {len(mapping)} new variables; matches: {dict(Counter(m['match'] for m in mapping))}; "
          f"same aid year pairs checked: {len(values)}; pairs with any school differing: {sum(1 for v in values if v['schools_differ'])}")


if __name__ == "__main__":
    main()
