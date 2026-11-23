"""Reload the dictionary by rerunning only what a change affects (owner decision, 2026-11-22).

The build remembers a fingerprint of each dictionary file and of each loaded release (table `_dictionary_state`).
On the next run it compares, and:
  - wording only (messages and term wording, statements, outside-IPEDS rows, nicknames, comparability breaks, and
    the wording columns of measures and category rows): reloads those tables, with no data checks (seconds);
    synonyms are wording too, and the app rebuilds its search index when the dictionary's fingerprint changes;
  - a measure's other columns: rechecks that measure (its links, its breakdown-set columns, its years);
  - category codes, breakdown exceptions, or a table's parent-and-child rule: retests that table, in the affected years;
  - school groups and members: rebuilds the directory and the groups;
  - rates and measure history: recounts the years of the measures they name;
  - a new or replaced release: that year's full checks;
  - special_codes.csv: needs the full data build (build_data.py).
A full rebuild (`python build/build_dictionary.py --full`) runs everything; it must give the same results, and a test
checks that. If a run stops part way, the next run is a full rebuild.
"""
import hashlib
import sqlite3
from pathlib import Path

WORDING_FILES = {"terms", "outside_ipeds", "school_nicknames", "comparability_breaks"}
MEASURE_STRUCTURE = ("table", "variable", "format", "data_type", "rows_per_school", "unit", "reporting_form",
                     "in_first_version", "detailed_measure", "breakdown_set", "set_total")
CODE_WORDING = ("synonyms", "statement", "in_latest")          # category rows: changes here retest nothing


def fingerprints(db, folder, bd):
    out = {f"file:{n}": hashlib.sha1((Path(folder) / f"{n}.csv").read_bytes()).hexdigest() for n in bd.TABLES}
    try:
        out.update({f"data:{y}": str(at) for y, at in db.execute("SELECT year, loaded_at FROM _releases")})
    except sqlite3.OperationalError:                # a database built before releases were recorded: one fingerprint
        out.update({f"data:{y}": str(n) for y, n in db.execute("SELECT year, COUNT(*) FROM _tables GROUP BY year")})
    return out


def stored(db):
    db.execute("CREATE TABLE IF NOT EXISTS _dictionary_state (item TEXT PRIMARY KEY, fingerprint TEXT)")
    return dict(db.execute("SELECT item, fingerprint FROM _dictionary_state"))


def usable(db):
    """True when the last build finished, so its results can be updated in part."""
    return stored(db).get("status") == "finished"


def mark(db, status, fresh=None, only=None):
    """Record the build's status, and (when finished) the fingerprints it was built from. With `only` (one table
    reloaded on its own), only that table's fingerprint is updated."""
    stored(db)                                      # makes the table on a first build
    if fresh:
        keep = {k: v for k, v in fresh.items() if only is None or k == f"file:{only}"}
        db.executemany("INSERT OR REPLACE INTO _dictionary_state VALUES (?, ?)", list(keep.items()))
    db.execute("INSERT OR REPLACE INTO _dictionary_state VALUES ('status', ?)", (status,))
    db.commit()


def rows_of(db, name):
    cur = db.execute(f"SELECT * FROM dict_{name}")
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def update(db, folder, bd, only=None, verbose=False):
    """Bring the database up to date with the dictionary folder, rerunning only what changed. Returns a list of the
    steps taken, in plain words."""
    old, new = stored(db), fingerprints(db, folder, bd)
    files = [n for n in bd.TABLES if old.get(f"file:{n}") != new[f"file:{n}"]]
    if only is not None:
        files = [only]
    years = sorted(int(k[5:]) for k in new if k.startswith("data:") and old.get(k) != new[k])
    if only is not None:
        years = []
    if "special_codes" in files:
        raise ValueError("special_codes.csv changed: run the full data build, python build/build_data.py")
    if any(k.startswith("data:") and k not in new for k in old) or \
            (years and max(years) > max(int(k[5:]) for k in old if k.startswith("data:"))):
        return None                                 # a release removed, or a new latest year: rebuild everything
    if not files and not years:
        return ["nothing changed"]
    before = {n: rows_of(db, n) for n in files}
    bd.load_tables(db, folder, names=files)
    after = {n: rows_of(db, n) for n in files}
    steps = [f"reloaded {', '.join(f + '.csv' for f in files)}"] if files else []

    # what the change touches
    measures, tables, table_years, recount = set(), set(), {}, set()

    def widen(table, covered):                      # the years to retest a table in; None for every year
        tables.add(table)
        if table not in table_years or table_years[table] is not None:
            table_years[table] = None if covered is None else table_years.get(table, set()) | covered
    if "measures" in files:
        key = lambda r: f"{r['table']}.{r['variable']}".upper()
        was, now = {key(r): r for r in before["measures"]}, {key(r): r for r in after["measures"]}
        for k in was.keys() | now.keys():
            a, b = was.get(k), now.get(k)
            shape = lambda r: None if r is None else tuple(r.get(c) for c in MEASURE_STRUCTURE) + \
                ((r.get("title"), r.get("plain_name")) if r.get("breakdown_set") else ())   # part labels
            if shape(a) != shape(b):
                measures.add(f"{(b or a)['table']}.{(b or a)['variable']}")
    if "category_codes" in files:
        shape = lambda r: tuple((k, v) for k, v in sorted(r.items()) if k not in CODE_WORDING)
        changed = set(map(shape, before["category_codes"])) ^ set(map(shape, after["category_codes"]))
        for row in map(dict, changed):
            widen(row["table"], bd.years_in(row.get("years")))
    if "breakdown_exceptions" in files:
        for row in map(dict, set(map(lambda r: tuple(sorted(r.items())), before["breakdown_exceptions"])) ^
                       set(map(lambda r: tuple(sorted(r.items())), after["breakdown_exceptions"]))):
            widen(row["table"], {int(row["year"])})
    if "year_meaning" in files:                     # the parent-and-child rule decides which link differences pass
        flags = lambda rows: {(r["table"], r.get("parent_child_flag")) for r in rows}
        for t, _ in flags(before["year_meaning"]) ^ flags(after["year_meaning"]):
            widen(t, None)
    if "measure_history" in files:
        recount |= {r["measure"] for r in before["measure_history"] + after["measure_history"]}
    if "rates" in files:
        recount |= {r[c] for r in before["rates"] + after["rates"] for c in ("numerator", "denominator") if r.get(c)}

    wording = set(files) <= WORDING_FILES | {"measures", "category_codes", "year_meaning"} and \
        not (measures or tables or years or recount)
    problems = bd.check(db, wording_only=wording)
    if problems:
        raise ValueError("The dictionary does not fit the data:\n  " + "\n  ".join(problems))
    if wording:
        steps.append("wording only: no data checks")
    if years:
        bd.build_value_labels(db)
    if years or {"school_groups", "group_members"} & set(files):
        bd.build_directory(db)
        bd.build_groups(db)
        steps.append("rebuilt the directory and groups")
    all_years = [y for (y,) in db.execute("SELECT DISTINCT year FROM _tables ORDER BY year")]
    problems = []
    if years:
        problems += bd.test_years(db, years, bd.Scope(), verbose)
        steps.append(f"full checks for {', '.join(map(str, years))}")
    for t in sorted(tables):
        ys = all_years if table_years.get(t) is None else sorted(table_years[t] & set(all_years))
        problems += bd.test_years(db, ys, bd.Scope(tables={t}), verbose)
        steps.append(f"retested {t} in {len(ys)} year(s)")
    if measures:
        problems += bd.test_years(db, all_years, bd.Scope(measures=measures), verbose)
        steps.append(f"rechecked {len(measures)} measure(s)")
    if problems:
        raise ValueError("The dictionary does not fit the data:\n  " + "\n  ".join(problems))
    if years:
        bd.build_measure_years(db, years=years)
    if measures | recount:
        bd.build_measure_years(db, only=measures | recount)
        steps.append(f"recounted the years of {len(measures | recount)} measure(s)")
    if not wording:                                 # the measures, tables and years this change touched
        bd.build_measure_checks(db, only=measures | recount, tables=tables, years=years)
    bd.build_name_clashes(db)
    return steps
