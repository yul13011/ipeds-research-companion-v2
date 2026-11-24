"""Stage 1: build the local database of stacked IPEDS tables.

What it does, in plain terms:
  - Opens each yearly IPEDS database READ-ONLY, in place (nothing is copied or changed there).
  - Copies every table into one local database, adding a `year` column.
  - Names each local table by its "family" across years, taken from the cross-year index
    (source ADM2024 -> local ADM, source F2324_F1A -> local F_F1A), so that the same table
    from another year lands in the same local table with a different `year`.
  - Cleans the values as it copies, using the release's own codebook as the rule: trims text,
    turns special codes such as -1 "Not reported" into missing, and stores as numbers the
    columns the codebook calls numeric (see load_release for the exact rules).
  - Records what was loaded in `_tables` and what was cleaned in `_columns`, `_special_codes`
    and `_conversion_failures`, and checks that every table has as many rows as its source.

`year` is the IPEDS release year (2024 for the 2024-25 release). What that year MEANS for a
given table (fall, fiscal year, cohort) is a dictionary matter and is not decided here.

Run:  python build/build_data.py
"""
import csv
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

RULES_FILE = config.DICTIONARY / "special_codes.csv"

REGISTRY = """
CREATE TABLE IF NOT EXISTS _tables (
    local_table  TEXT,     -- name in this database, e.g. ADM
    source_table TEXT,     -- name in the yearly database, e.g. ADM2024
    family       TEXT,     -- cross-year family from the index, e.g. ADM{YEAR}
    kind         TEXT,     -- 'data' or 'codebook'
    release      TEXT,     -- e.g. IPEDS_2024-25_Provisional
    year         INTEGER,  -- release year, e.g. 2024
    source_rows  INTEGER,
    loaded_rows  INTEGER,
    n_columns    INTEGER,  -- columns in the source table (not counting `year`)
    has_unitid   INTEGER,  -- 1 if the table is keyed by school
    PRIMARY KEY (source_table, release));
CREATE TABLE IF NOT EXISTS _columns (        -- one row per column: what cleaning was applied
    local_table TEXT, source_table TEXT, release TEXT, column TEXT,
    source_type       TEXT,     -- how the yearly database stored it
    codebook_type     TEXT,     -- N (numeric) or A (text) from the codebook; blank if not listed
    stored_type       TEXT,     -- how this database stores it
    text_to_number    INTEGER,  -- 1 if the source stored a codebook-numeric column as text
    source_nonmissing INTEGER,  -- cells with a value in the source
    n_padded          INTEGER,  -- text cells that had surrounding spaces removed
    n_blank           INTEGER,  -- empty or all-space text cells, now missing
    n_special         INTEGER,  -- cells holding a special code, now missing
    n_failed          INTEGER,  -- cells that should be numbers but are not; kept as text and listed
    loaded_nonmissing INTEGER,  -- cells with a value in this database
    PRIMARY KEY (source_table, release, column));
CREATE TABLE IF NOT EXISTS _special_codes (  -- every special code the codebook lists for a column
    local_table TEXT, source_table TEXT, release TEXT, column TEXT,
    code TEXT, label TEXT,
    applies_by TEXT,            -- 'codebook label' or 'table and column': which kind of rule covers it
    decision TEXT,              -- 'missing' = turned into missing; 'keep' = left as it is
    shown_as TEXT,              -- the reason shown to a user, e.g. Not applicable
    n_cells INTEGER,
    PRIMARY KEY (source_table, release, column, code));
CREATE TABLE IF NOT EXISTS _missing_reasons (  -- FOR DISPLAY ONLY. Why one school's value is missing.
    local_table TEXT, year INTEGER, unitid INTEGER, column TEXT, code TEXT, reason TEXT);
CREATE INDEX IF NOT EXISTS ix_missing_reasons ON _missing_reasons (local_table, unitid, column, year);
CREATE TABLE IF NOT EXISTS _conversion_failures (
    local_table TEXT, source_table TEXT, release TEXT, column TEXT, value TEXT, n_cells INTEGER);
CREATE TABLE IF NOT EXISTS _releases (       -- one row per year held: which release it came from
    year INTEGER PRIMARY KEY, release TEXT, status TEXT, source_file TEXT, loaded_at TEXT, seconds REAL);
"""


def status_of(release):
    """'provisional' or 'final', from the release folder name (IPEDS_2024-25_Provisional)."""
    low = release.lower()
    if low.endswith("_provisional"):
        return "provisional"
    if low.endswith("_final"):
        return "final"
    raise ValueError(f"{release}: the folder name must end in _Provisional or _Final")


def year_of(release):
    """2024 for IPEDS_2024-25_Provisional."""
    m = re.match(r"IPEDS_(\d{4})-\d{2}_", release)
    if not m:
        raise ValueError(f"{release}: not a release folder name like IPEDS_2024-25_Final")
    return int(m.group(1))


def remove_year(out, year):
    """Delete every row of one release year from every stacked table and every record, so a replaced release
    leaves nothing behind. Tables and columns stay; only that year's rows go."""
    out.executescript(REGISTRY)
    old = [r for (r,) in out.execute("SELECT DISTINCT release FROM _tables WHERE year = ?", (year,))]
    for (t,) in out.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
        cols = {r[1].lower() for r in out.execute(f'PRAGMA table_info("{t}")')}
        if t in ("_columns", "_special_codes", "_conversion_failures"):
            continue                                    # keyed by release name; cleared below
        if "year" in cols:
            out.execute(f'DELETE FROM "{t}" WHERE year = ?', (year,))
    for release in old:
        for log in ("_columns", "_special_codes", "_conversion_failures", "_tables"):
            out.execute(f"DELETE FROM {log} WHERE release = ?", (release,))
    out.execute("DELETE FROM _releases WHERE year = ?", (year,))
    out.commit()
    return old


def local_name(family):
    """ADM{YEAR} -> ADM; F{YYPAIR}_F1A -> F_F1A; COST2_{YEAR}_NETPRICE -> COST2_NETPRICE; VARTABLE24 -> VARTABLE."""
    name = re.sub(r"\{[A-Z0-9]+\}", "", family)
    if name == family:                       # codebook tables carry a bare two-digit year
        name = re.sub(r"\d\d$", "", name)
    return re.sub(r"_+", "_", name).strip("_").upper()


def families_from_catalog(catalog_path, release):
    """Read {source table: (family, kind)} for one release from the cross-year index."""
    con = sqlite3.connect(f"file:{Path(catalog_path).as_posix()}?mode=ro", uri=True)
    rows = con.execute("SELECT table_name, family, kind FROM tables WHERE release_id = ?", (release,)).fetchall()
    con.close()
    return {t: (fam, "codebook" if kind == "source_metadata" else "data") for t, fam, kind in rows}


def special_code_rules(path=None):
    """The owner-reviewed rules in dictionary/special_codes.csv, as two lookups.

    by_label:  {(code, codebook label): (decision, shown_as)}   applies wherever the codebook uses that label
    by_column: {(TABLE, COLUMN): {code: (decision, shown_as)}}  applies to one named table and column
    A code that neither lookup covers is left as it is.
    """
    by_label, by_column = {}, {}
    with open(path or RULES_FILE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rule = (r["decision"].strip(), r["shown_as"].strip())
            if r["applies_by"].strip() == "codebook label":
                by_label[(r["code"].strip(), r["label"].strip())] = rule
            else:
                by_column.setdefault((r["table"].strip().upper(), r["column"].strip().upper()), {})[r["code"].strip()] = rule
    return by_label, by_column


def read_codebook(out, names):
    """From the release's own codebook tables: which columns are numeric, and each column's special codes.

    Returns ({(TABLE, COLUMN): 'N' or 'A'}, {(TABLE, COLUMN): {code: label}}), keys in upper case.
    A special code is a negative code that the codebook lists, with a label, for that column.
    """
    by_local = {local: source for source, local in names.items()}
    types, codes = {}, {}
    if "VARTABLE" in by_local:
        for t, v, d in out.execute(f'SELECT TableName, VarName, DataType FROM src."{by_local["VARTABLE"]}"'):
            types[(t.strip().upper(), v.strip().upper())] = (d or "").strip().upper()
    if "VALUESETS" in by_local:
        for t, v, code, label in out.execute(
                f'SELECT TableName, VarName, Codevalue, ValueLabel FROM src."{by_local["VALUESETS"]}" '
                "WHERE TRIM(Codevalue) LIKE '-%'"):
            codes.setdefault((t.strip().upper(), v.strip().upper()), {})[code.strip()] = (label or "").strip()
    return types, codes


def literal(code, is_text):
    """A special code written safely into SQL: a quoted string for text columns, a number otherwise."""
    return "'" + code.replace("'", "''") + "'" if is_text else repr(float(code))


def column_plan(table, local, cols, types, codes, rules):
    """For each column of one source table: how it will be stored and the SQL that cleans it."""
    by_label, by_column = rules
    plan = []
    for col, stype in cols:
        key = (table.upper(), col.upper())
        is_text = stype == "TEXT"
        to_number = is_text and types.get(key) == "N"
        expr = f"NULLIF(TRIM(\"{col}\"), '')" if is_text else f'"{col}"'     # rule 1: trim; blank is missing
        # Special codes for this column: {code: (label, which rule, decision, reason shown)}
        found = {c: (label, "codebook label") + by_label.get((c, label), ("keep", ""))
                 for c, label in codes.get(key, {}).items()}
        for c, rule in by_column.get((local.upper(), col.upper()), {}).items():
            found[c] = ("", "table and column") + rule
        drop = [c for c, f in found.items() if f[2] == "missing"]
        clean = expr
        if drop:                                                              # rule 2: approved special codes
            listed = ", ".join(literal(c, is_text) for c in drop)
            clean = f"CASE WHEN {expr} IN ({listed}) THEN NULL ELSE {expr} END"
        plan.append(dict(col=col, stype=stype, ctype=types.get(key, ""), is_text=is_text, to_number=to_number,
                         stored="NUMERIC" if to_number else stype,           # rule 3: codebook-numeric text
                         expr=expr, clean=clean, found=found, drop=drop))
    return plan


def record_reasons(out, table, local, year, plan, unitid):
    """Keep, for display only, why each school's value is missing (Not applicable, Not reported)."""
    out.execute("DELETE FROM _missing_reasons WHERE local_table = ? AND year = ?", (local, year))
    for p in plan:
        for code in p["drop"]:
            out.execute(f'INSERT INTO _missing_reasons SELECT ?, ?, "{unitid}", ?, ?, ? FROM src."{table}" '
                        f'WHERE {p["expr"]} = {literal(code, p["is_text"])}',
                        (local, year, p["col"], code, p["found"][code][3]))


def record_cleaning(out, table, local, release, year, plan):
    """Count what the cleaning did to each column, from the source and from the result, and store it."""
    asks = []                                                     # (column plan, what, code, SQL on the source)
    for p in plan:
        c = f'"{p["col"]}"'
        asks.append((p, "source", None, f"COUNT({c})"))
        if p["is_text"]:
            asks.append((p, "padded", None, f"SUM({c} <> TRIM({c}) AND TRIM({c}) <> '')"))
            asks.append((p, "blank", None, f"SUM(TRIM({c}) = '')"))
        for code in p["found"]:
            asks.append((p, "code", code, f"SUM({p['expr']} = {literal(code, p['is_text'])})"))
    counts, loaded = [], []
    for i in range(0, len(asks), 400):
        counts += out.execute(f'SELECT {", ".join(a[3] for a in asks[i:i + 400])} FROM src."{table}"').fetchone()
    for i in range(0, len(plan), 400):
        part = ", ".join(f'COUNT("{p["col"]}")' for p in plan[i:i + 400])
        loaded += out.execute(f'SELECT {part} FROM "{local}" WHERE year = ?', (year,)).fetchone()

    stats = {p["col"]: dict(source=0, padded=0, blank=0, special=0) for p in plan}
    for (p, what, code, _), n in zip(asks, counts):
        n = n or 0
        if what == "code":
            label, applies_by, decision, shown_as = p["found"][code]
            out.execute("INSERT INTO _special_codes VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (local, table, release, p["col"], code, label, applies_by, decision, shown_as, n))
            if decision == "missing":
                stats[p["col"]]["special"] += n
        else:
            stats[p["col"]][what] = n
    for p, n_loaded in zip(plan, loaded):
        failed = 0
        if p["to_number"]:                                        # anything still text did not convert
            c = f'"{p["col"]}"'
            for value, n in out.execute(f"SELECT {c}, COUNT(*) FROM \"{local}\" WHERE year = ? "
                                        f"AND typeof({c}) = 'text' GROUP BY 1", (year,)).fetchall():
                out.execute("INSERT INTO _conversion_failures VALUES (?,?,?,?,?,?)",
                            (local, table, release, p["col"], value, n))
                failed += n
        s = stats[p["col"]]
        out.execute("INSERT INTO _columns VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (local, table, release, p["col"], p["stype"], p["ctype"], p["stored"], int(p["to_number"]),
                     s["source"], s["padded"], s["blank"], s["special"], failed, n_loaded))


def load_release(out, source_path, release, year, families, rules=None):
    """Copy every table of one yearly database into `out`, stacked by family and cleaned.

    Cleaning, all driven by the release's own codebook:
      1. Text is trimmed; an empty or all-space text cell becomes missing.
      2. A special code (such as -1 "Not reported") becomes missing when dictionary/special_codes.csv
         says so: either the codebook lists that code for that column with a label marked 'missing',
         or the table and column are named there. Any other negative number (a negative net price)
         is untouched. The reason is kept per school in _missing_reasons, for display only.
      3. A column the codebook calls numeric (DataType N) but the source stored as text is stored
         as a number. A value that will not convert is kept as text and listed, never dropped.
    Returns the registry rows.
    """
    rules = special_code_rules() if rules is None else rules
    out.executescript(REGISTRY)
    out.execute("ATTACH DATABASE ? AS src", (f"file:{Path(source_path).as_posix()}?mode=ro",))
    try:
        source_tables = [r[0] for r in out.execute(
            "SELECT name FROM src.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        missing = [t for t in source_tables if t not in families]
        if missing:
            raise ValueError(f"Tables not in the cross-year index for {release}: {missing}")
        names = {t: local_name(families[t][0]) for t in source_tables}
        clashes = {n for n in names.values() if list(names.values()).count(n) > 1}
        if clashes:
            raise ValueError(f"Two source tables map to the same local table: {sorted(clashes)}")
        types, codes = read_codebook(out, names)
        for log in ("_columns", "_special_codes", "_conversion_failures"):
            out.execute(f"DELETE FROM {log} WHERE release = ?", (release,))

        report = []
        for table in source_tables:
            family, kind = families[table]
            local = names[table]
            cols = [(r[1], (r[2] or "").upper()) for r in out.execute(f'PRAGMA src.table_info("{table}")')]
            if any(c.lower() == "year" for c, _ in cols):
                raise ValueError(f"{table} already has a column called year")
            plan = column_plan(table, local, cols, types, codes, rules)

            # Create the stacked table on first sight; add any column a later year introduces.
            out.execute(f'CREATE TABLE IF NOT EXISTS "{local}" (year INTEGER NOT NULL)')
            have = {r[1].lower() for r in out.execute(f'PRAGMA table_info("{local}")')}
            for p in plan:
                if p["col"].lower() not in have:
                    out.execute(f'ALTER TABLE "{local}" ADD COLUMN "{p["col"]}" {p["stored"]}')

            # Re-running a year replaces that year's rows; it never duplicates them.
            out.execute(f'DELETE FROM "{local}" WHERE year = ?', (year,))
            col_list = ", ".join(f'"{p["col"]}"' for p in plan)
            cleaned = ", ".join(p["clean"] for p in plan)
            out.execute(f'INSERT INTO "{local}" (year, {col_list}) SELECT ?, {cleaned} FROM src."{table}"', (year,))

            unitid = next((c for c, _ in cols if c.lower() == "unitid"), None)
            has_unitid = unitid is not None
            if has_unitid:
                out.execute(f'CREATE INDEX IF NOT EXISTS "ix_{local}_unitid" ON "{local}" (UNITID, year)')
                record_reasons(out, table, local, year, plan, unitid)
            record_cleaning(out, table, local, release, year, plan)

            source_rows = out.execute(f'SELECT COUNT(*) FROM src."{table}"').fetchone()[0]
            loaded_rows = out.execute(f'SELECT COUNT(*) FROM "{local}" WHERE year = ?', (year,)).fetchone()[0]
            row = (local, table, family, kind, release, year, source_rows, loaded_rows, len(cols), int(has_unitid))
            out.execute("INSERT OR REPLACE INTO _tables VALUES (?,?,?,?,?,?,?,?,?,?)", row)
            report.append(row)
        out.commit()
    finally:
        out.execute("DETACH DATABASE src")
    return report


def add_release(out, release, filename=None, source_data=None, catalog=None):
    """Add one release, or replace the release already held for its year (a provisional release by its final
    version, or a corrected file). Every row of that year is removed first, then the release is loaded.
    Returns (registry rows, releases removed)."""
    year = year_of(release)
    status = status_of(release)
    source_data = Path(source_data or config.SOURCE_DATA)
    filename = filename or next((f for r, f, _ in config.RELEASES if r == release), None)
    if filename is None:
        raise ValueError(f"{release} is not listed in config.RELEASES")
    path = source_data / "annual" / release / filename
    if not path.exists():
        raise FileNotFoundError(path)
    start = time.time()
    removed = remove_year(out, year)
    families = families_from_catalog(catalog or config.CATALOG, release)
    report = load_release(out, path, release, year, families)
    out.execute("INSERT OR REPLACE INTO _releases VALUES (?,?,?,?,datetime('now'),?)",
                (year, release, status, str(path), round(time.time() - start, 1)))
    out.commit()
    return report, removed


def build(local_db=None, releases=None, source_data=None, catalog=None):
    """Build the whole local database from scratch, every release in config.RELEASES. Returns the registry rows."""
    local_db = Path(local_db or config.LOCAL_DB)
    local_db.parent.mkdir(parents=True, exist_ok=True)
    if local_db.exists():
        local_db.unlink()
    out = sqlite3.connect(local_db, uri=True)
    report = []
    years = [year_of(r) for r, _, _ in (releases or config.RELEASES)]
    if len(set(years)) != len(years):
        raise ValueError("config.RELEASES lists more than one release for the same year")
    for release, filename, year in (releases or config.RELEASES):
        if year != year_of(release):
            raise ValueError(f"{release}: the year in config ({year}) does not match the folder name")
        report += add_release(out, release, filename, source_data, catalog)[0]
    out.execute("ANALYZE")
    out.commit()
    out.close()
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build the local database, or add or replace one release.")
    parser.add_argument("--release", help="add or replace this one release (a folder name in config.RELEASES)")
    args = parser.parse_args()
    start = time.time()
    if args.release:
        out = sqlite3.connect(config.LOCAL_DB, uri=True)  # uri: the source is attached read-only by address
        rows, removed = add_release(out, args.release)
        out.execute("ANALYZE")
        out.commit()
        out.close()
        print(f"{args.release}: {len(rows)} tables loaded" + (f"; replaced {', '.join(removed)}" if removed else ""))
    else:
        rows = build()
    return rows, start


if __name__ == "__main__":
    rows, start = main()
    bad = [r for r in rows if r[6] != r[7]]
    print(f"{'local table':<22}{'source table':<26}{'kind':<10}{'source rows':>12}{'loaded rows':>12}  ok")
    for r in rows:
        print(f"{r[0]:<22}{r[1]:<26}{r[3]:<10}{r[6]:>12,}{r[7]:>12,}  {'yes' if r[6] == r[7] else 'NO'}")
    print(f"\n{len(rows)} tables, {sum(r[6] for r in rows):,} source rows, {sum(r[7] for r in rows):,} loaded rows, "
          f"{len(bad)} mismatches, {time.time() - start:.0f} seconds")
    con = sqlite3.connect(config.LOCAL_DB)
    print("Cleaning: %d columns stored as numbers instead of text; %d text cells trimmed; %d blank cells and "
          "%d special-code cells set to missing; %d cells failed to convert" % con.execute(
              "SELECT SUM(text_to_number), SUM(n_padded), SUM(n_blank), SUM(n_special), SUM(n_failed) FROM _columns").fetchone())
    con.close()
    if not bad:                                   # then load the dictionary folder and build the school directory
        from build import build_dictionary
        loaded = build_dictionary.build()
        print(f"Dictionary: {len(loaded)} tables loaded, {sum(loaded.values()):,} rows")
        sys.path.insert(0, str(config.ROOT / "scripts"))     # after the data are rebuilt: rewrite docs/DATABASE.md
        import database_inventory
        print(f"Inventory: {database_inventory.write()[0]}")
    print(f"Local database: {config.LOCAL_DB} ({config.LOCAL_DB.stat().st_size / 1e6:.0f} MB)")
    sys.exit(1 if bad else 0)
