"""Stage 2: load the dictionary folder into the local database and build the school directory.

What it does, in plain terms:
  1. Copies each CSV table in dictionary/ into the database as dict_<name>, unchanged.
  2. Checks every reference in those tables against the real data (does this measure exist? this
     column? this school?). If anything is wrong it stops and lists every problem. It never guesses.
  3. Builds three tables the question path reads:
       value_labels      every coded value and its IPEDS label, from the codebook
       directory         one row per school: name, city, state, and every grouping column that
                         school_groups.csv names (sector, level, control, Carnegie class, and so on)
       group_list        every group a user can name, with its definition and number of schools
       group_membership  which schools are in each group
       row_keys          for each multi-row table, the category columns that pick out one row per school,
                         and the default code of each (category_codes.csv, `default`)
       breakdown_sets    every named breakdown, tested: do its parts add up to its total?
       breakdown_parts   the parts of each breakdown that passed
       breakdown_slices  for sets in tables keyed by several category columns: every value of the
                         other columns at which the set adds up (bachelor's degrees by field,
                         undergraduates by age), not only the default

No IPEDS convention is decided in this file. It only applies what the dictionary tables say.

Run:  python build/build_dictionary.py     (fast; run after any change to a dictionary table,
                                            except special_codes.csv, which needs build_data.py)
"""
import csv
import itertools
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

TABLES = ["measures", "terms", "school_groups", "group_members", "school_nicknames",
          "rates", "category_codes", "year_meaning", "outside_ipeds", "special_codes"]
IDENTITY = ["INSTNM", "IALIAS", "CITY", "STABBR"]          # always in the directory, from HD
FILTER_KINDS = ("column", "universe")                       # groups defined by codes in directory columns
METHODS = ("sum of counts", "weighted average")            # how a rates.csv row combines schools; see README
ADDITIVE = "sum of parts"                                   # a breakdown set with no total row or column in the data


def split(cell, sep=","):
    return [x.strip() for x in (cell or "").split(sep) if x.strip()]


def load_tables(db, folder):
    """Step 1: each CSV becomes dict_<name>. Every column is text; an empty cell is missing."""
    for name in TABLES:
        with open(Path(folder) / f"{name}.csv", newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        header, body = rows[0], rows[1:]
        db.execute(f"DROP TABLE IF EXISTS dict_{name}")
        db.execute(f"CREATE TABLE dict_{name} ({', '.join(chr(34) + h + chr(34) + ' TEXT' for h in header)})")
        db.executemany(f"INSERT INTO dict_{name} VALUES ({', '.join('?' * len(header))})",
                       [[(c.strip() or None) for c in r] for r in body])


def check(db):
    """Step 2: every reference in the dictionary must exist in the data. Returns a list of problems."""
    problems = []
    data = {t: {r[1].upper() for r in db.execute(f'PRAGMA table_info("{t}")')}
            for (t,) in db.execute("SELECT DISTINCT local_table FROM _tables")}
    schools = {u for (u,) in db.execute("SELECT UNITID FROM HD")}

    def exists(ref, where):                                 # ref is TABLE.COLUMN
        table, _, column = (ref or "").partition(".")
        if column.upper() not in data.get(table, ()):
            problems.append(f"{where}: {ref} is not a column in the data")

    measures = set()
    for table, variable in db.execute("SELECT \"table\", variable FROM dict_measures"):
        exists(f"{table}.{variable}", "measures.csv")
        measures.add(f"{table}.{variable}".upper())

    group_names = {g for (g,) in db.execute('SELECT "group" FROM dict_school_groups')}
    for term, reading, measure, default_for in db.execute("SELECT term, reading, measure, default_for FROM dict_terms"):
        if measure and measure.upper() not in measures:
            problems.append(f"terms.csv: '{term}' / '{reading}' names {measure}, which is not in measures.csv")
        if default_for and default_for not in group_names:
            problems.append(f"terms.csv: '{term}' / '{reading}' is the default for '{default_for}', which is not a school group")
    for (term,) in db.execute("SELECT term FROM dict_terms GROUP BY term "
                              "HAVING MAX(always_ask) = 'no' AND MAX(is_default) = 'no'"):
        problems.append(f"terms.csv: '{term}' neither asks the user nor has a default reading")

    for name, kind, table, column, codes in db.execute('SELECT "group", kind, "table", "column", codes FROM dict_school_groups'):
        for col in split(column):
            exists(f"{table}.{col}", f"school_groups.csv '{name}'")
        if kind in FILTER_KINDS and table in data and all(c.upper() in data[table] for c in split(column)):
            present = set()
            for col in split(column):
                present |= {str(v) for (v,) in db.execute(f'SELECT DISTINCT "{col}" FROM "{table}"')}
            for code in split(codes):
                if code not in present:
                    problems.append(f"school_groups.csv '{name}': code {code} never occurs in {table}.{column}")
        if kind == "member list" and not db.execute('SELECT 1 FROM dict_group_members WHERE "group" = ?', (name,)).fetchone():
            problems.append(f"school_groups.csv '{name}' is a member list with no rows in group_members.csv")

    for group, unitid in db.execute('SELECT "group", unitid FROM dict_group_members'):
        if group not in group_names:
            problems.append(f"group_members.csv: '{group}' is not in school_groups.csv")
        if int(unitid) not in schools:
            problems.append(f"group_members.csv: school {unitid} in '{group}' is not in the directory")
    for nickname, unitid in db.execute("SELECT nickname, unitid FROM dict_school_nicknames WHERE unitid IS NOT NULL"):
        if int(unitid) not in schools:
            problems.append(f"school_nicknames.csv: '{nickname}' points to school {unitid}, which is not in the directory")

    for rate, rate_measure, num, den, cat in db.execute(
            "SELECT rate, rate_measure, numerator, denominator, category_column FROM dict_rates"):
        for ref in (num, den):
            exists(ref, f"rates.csv '{rate}'")
            if cat:
                exists(f"{ref.partition('.')[0]}.{cat}", f"rates.csv '{rate}'")
        if rate_measure and rate_measure.upper() not in measures:
            problems.append(f"rates.csv: '{rate}' names {rate_measure}, which is not in measures.csv")
    for rate, method in db.execute("SELECT rate, method FROM dict_rates"):
        if method not in METHODS:
            problems.append(f"rates.csv: '{rate}' has method '{method}'; it must be one of {', '.join(METHODS)}")
    for rate, applies_to in db.execute("SELECT rate, applies_to FROM dict_rates WHERE applies_to IS NOT NULL"):
        if applies_to not in group_names:
            problems.append(f"rates.csv: '{rate}' applies to '{applies_to}', which is not a school group")
    for key, n, n_scoped in db.execute("SELECT COALESCE(rate_measure, rate), COUNT(*), COUNT(applies_to) FROM dict_rates "
                                       "GROUP BY 1 HAVING COUNT(*) > 1"):
        if n_scoped < n:
            problems.append(f"rates.csv: {key} has {n} rows, so each must say which schools it applies to")

    for table, column in db.execute('SELECT DISTINCT "table", "column" FROM dict_category_codes'):
        exists(f"{table}.{column}", "category_codes.csv")
    for table, name, n in db.execute('SELECT "table", breakdown_set, COUNT(DISTINCT COALESCE(set_total, \'\') || \'|\' || '
                                     "COALESCE(set_fixed, '')) FROM dict_category_codes WHERE breakdown_set IS NOT NULL GROUP BY 1, 2"):
        if n > 1:
            problems.append(f"category_codes.csv: the rows of '{name}' in {table} do not all name the same total and fixed values")
    for table, name, total in db.execute('SELECT DISTINCT "table", breakdown_set, set_total FROM dict_measures WHERE breakdown_set IS NOT NULL'):
        if total != ADDITIVE:
            exists(f"{table}.{total}", f"measures.csv breakdown set '{name}'")
    covered = {t for (t,) in db.execute('SELECT "table" FROM dict_year_meaning')}
    for (t,) in db.execute("SELECT DISTINCT local_table FROM _tables WHERE kind = 'data'"):
        if t not in covered:
            problems.append(f"year_meaning.csv: no row for data table {t}")
    return problems


def build_value_labels(db):
    """Every coded value and its IPEDS label, keyed by the local table name. Straight from the codebook."""
    db.executescript("""
        DROP TABLE IF EXISTS value_labels;
        CREATE TABLE value_labels AS
          SELECT t.local_table, UPPER(v.VarName) AS "column", v.Codevalue AS code, v.ValueLabel AS label, v.year
          FROM VALUESETS v JOIN _tables t ON UPPER(t.source_table) = UPPER(v.TableName) AND t.year = v.year
          WHERE v.Codevalue IS NOT NULL;
        CREATE INDEX ix_value_labels ON value_labels (local_table, "column", code);""")


def build_directory(db):
    """One row per school and year: identity columns from HD plus every column school_groups.csv names."""
    wanted = {}                                             # table -> columns, in first-seen order
    for table, column in db.execute('SELECT "table", "column" FROM dict_school_groups '
                                    "WHERE kind NOT IN ('per school', 'has rows', 'has value') AND \"column\" IS NOT NULL"):
        for col in split(column):
            if col not in IDENTITY and col not in wanted.setdefault(table, []):
                wanted[table].append(col)
    select = ["HD.year", "HD.UNITID"] + [f"HD.{c}" for c in IDENTITY]
    joins = ""
    for table, cols in wanted.items():
        select += [f'"{table}"."{c}"' for c in cols]
        if table != "HD":
            joins += f' LEFT JOIN "{table}" ON "{table}".UNITID = HD.UNITID AND "{table}".year = HD.year'
    db.execute("DROP TABLE IF EXISTS directory")
    db.execute(f"CREATE TABLE directory AS SELECT {', '.join(select)} FROM HD{joins}")
    db.execute("CREATE UNIQUE INDEX ix_directory ON directory (UNITID, year)")


def condition(column, codes):
    """SQL for 'this school has one of these codes in any of these columns'."""
    listed = ", ".join("'" + c.replace("'", "''") + "'" for c in codes)
    return "(" + " OR ".join(f'CAST("{col}" AS TEXT) IN ({listed})' for col in split(column)) + ")"


def build_groups(db):
    """group_list: every group a user can name. group_membership: the schools in each."""
    db.executescript("""
        DROP TABLE IF EXISTS group_list;
        DROP TABLE IF EXISTS group_membership;
        CREATE TABLE group_list (group_name TEXT PRIMARY KEY, parent TEXT, kind TEXT, words TEXT, statement TEXT,
                                 caveat TEXT, status TEXT, priority TEXT, n_schools INTEGER, word_note TEXT);
        CREATE TABLE group_membership (group_name TEXT, year INTEGER, unitid INTEGER);""")
    rows = db.execute('SELECT "group", kind, words, "table", "column", codes, statement, caveat, status, priority '
                      "FROM dict_school_groups ORDER BY rowid").fetchall()
    seen = {}
    for name, kind, words, table, column, codes, statement, caveat, status, priority in rows:
        if kind == "any value":                             # each value of the column is its own group
            labels = {}
            for col in split(column):
                for code, label in db.execute('SELECT code, label FROM value_labels WHERE local_table = ? AND "column" = ?',
                                              (table, col.upper())):
                    labels.setdefault(code, label)
            values = set()
            for col in split(column):
                values |= {str(v) for (v,) in db.execute(f'SELECT DISTINCT "{col}" FROM directory WHERE "{col}" IS NOT NULL')}
            for value in sorted(values):
                label = labels.get(value, value)
                child = f"{name}: {label}"
                db.execute("INSERT OR IGNORE INTO group_list VALUES (?,?,?,?,?,?,?,?,NULL,NULL)",
                           (child, name, kind, value if value != label else None, f"{statement}: {label}", caveat, status, priority))
                db.execute(f"INSERT INTO group_membership SELECT ?, year, UNITID FROM directory WHERE {condition(column, [value])}", (child,))
            continue
        if name not in seen:
            db.execute("INSERT INTO group_list VALUES (?,?,?,?,?,?,?,?,NULL,NULL)",
                       (name, None, kind, words, statement, caveat, status, priority))
        if kind in FILTER_KINDS:
            where = condition(column, split(codes))
            if name in seen:                                # a second row of the same group narrows it (all rows must hold)
                db.execute(f"DELETE FROM group_membership WHERE group_name = ? AND unitid NOT IN "
                           f"(SELECT UNITID FROM directory WHERE {where})", (name,))
            else:
                db.execute(f"INSERT INTO group_membership SELECT ?, year, UNITID FROM directory WHERE {where}", (name,))
        elif kind == "has value":                           # schools with a value in the named column
            db.execute(f'INSERT INTO group_membership SELECT ?, d.year, d.UNITID FROM directory d JOIN "{table}" t '
                       f'ON t.UNITID = d.UNITID AND t.year = d.year WHERE t."{column}" IS NOT NULL', (name,))
        elif kind == "has rows":                            # schools with at least one row in the named table
            db.execute(f'INSERT INTO group_membership SELECT ?, year, UNITID FROM directory d WHERE EXISTS '
                       f'(SELECT 1 FROM "{table}" t WHERE t.UNITID = d.UNITID AND t.year = d.year)', (name,))
        elif kind == "member list":
            db.execute('INSERT INTO group_membership SELECT m."group", d.year, d.UNITID FROM dict_group_members m '
                       'JOIN directory d ON d.UNITID = CAST(m.unitid AS INTEGER) WHERE m."group" = ?', (name,))
        seen[name] = kind
    db.execute("CREATE INDEX ix_group_membership ON group_membership (group_name, year, unitid)")
    db.execute("CREATE INDEX ix_group_membership_school ON group_membership (unitid, year)")
    db.execute("UPDATE group_list SET n_schools = (SELECT COUNT(*) FROM group_membership m WHERE m.group_name = group_list.group_name)")
    db.execute('UPDATE group_list SET word_note = (SELECT MAX(word_note) FROM dict_school_groups g WHERE g."group" = group_list.group_name)')


def conditions(fixed):
    """'CIPCODE = 99; MAJORNUM = 1' -> SQL. The fixed values of the other category columns of a set."""
    parts = []
    for item in split(fixed, ";"):
        column, _, value = item.partition("=")
        parts.append(f"CAST(\"{column.strip()}\" AS TEXT) = '{value.strip()}'")
    return " AND ".join(parts) or "1=1"


def build_breakdown_sets(db):
    """Test every named breakdown set against the data. Only sets that add up are loaded.

    A set stored as ROWS (category_codes.csv) is tested for every count column of its table: at each
    school, do the part rows add up to the total row? It is loaded for the count columns that pass at
    every school. Where the set holds other category columns fixed, those values are only the default:
    the same test runs at every other value, and breakdown_slices records which values pass.
    A set stored as COLUMNS (measures.csv) is tested on every row of its table: do the
    part columns add up to the total column? Rows where IPEDS collects no detail at all (every part
    is missing) cannot be broken down; they are counted in n_no_detail and are not failures.
    A set whose total is 'sum of parts' has no total in the
    data, so there is nothing to test; the result shows a total computed by summing the parts.
    """
    db.executescript("""
        DROP TABLE IF EXISTS breakdown_sets;
        DROP TABLE IF EXISTS breakdown_parts;
        DROP TABLE IF EXISTS breakdown_slices;
        CREATE TABLE breakdown_slices (set_name TEXT, "table" TEXT, measure TEXT, slice TEXT,
                                       n_tested INTEGER, n_ok INTEGER, status TEXT);
        CREATE TABLE breakdown_sets (set_name TEXT, "table" TEXT, stored_as TEXT, "column" TEXT, total TEXT, fixed TEXT,
                                     measure TEXT, n_parts INTEGER, n_tested INTEGER, n_ok INTEGER,
                                     n_no_detail INTEGER, status TEXT);
        CREATE TABLE breakdown_parts (set_name TEXT, "table" TEXT, part TEXT, label TEXT);""")

    # Sets stored as rows: one result per count column of the table.
    for table, column, name, total, fixed in db.execute(
            'SELECT DISTINCT "table", "column", breakdown_set, set_total, set_fixed FROM dict_category_codes '
            "WHERE breakdown_set IS NOT NULL").fetchall():
        parts = db.execute('SELECT code, label FROM dict_category_codes WHERE "table"=? AND "column"=? AND breakdown_set=?',
                           (table, column, name)).fetchall()
        listed = ", ".join("'" + c.replace("'", "''") + "'" for c, _ in parts)
        code = f'CAST("{column}" AS TEXT)'
        counts = [m for (m,) in db.execute("SELECT variable FROM dict_measures WHERE \"table\"=? AND format='Cont' "
                                           "AND data_type='N'", (table,))]
        loaded = False
        keys = [item.partition("=")[0].strip() for item in split(fixed, ";")]   # the other category columns
        for i in range(0, len(counts), 100):
            chunk = counts[i:i + 100]
            if total == ADDITIVE:
                results = [(None, None)] * len(chunk)
            else:
                per_school = ", ".join(f'SUM(CASE WHEN {code} IN ({listed}) THEN "{m}" END) p{j}, '
                                       f'MAX(CASE WHEN {code} = \'{total}\' THEN "{m}" END) t{j}' for j, m in enumerate(chunk))
                summary = ", ".join(f"SUM(t{j} IS NOT NULL), SUM(t{j} IS NOT NULL AND COALESCE(p{j}, 0) = t{j})" for j in range(len(chunk)))
                flat = db.execute(f'SELECT {summary} FROM (SELECT {per_school} FROM "{table}" WHERE {conditions(fixed)} '
                                  "GROUP BY UNITID, year)").fetchone()
                results = [(flat[2 * j] or 0, flat[2 * j + 1] or 0) for j in range(len(chunk))]
            for m, (tested, ok) in zip(chunk, results):
                status = "additive" if total == ADDITIVE else ("loaded" if tested and tested == ok else "failed")
                loaded = loaded or status != "failed"
                db.execute("INSERT INTO breakdown_sets VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           (name, table, "rows", column, total, fixed, m, len(parts), tested, ok, None, status))
            if keys and total != ADDITIVE:                  # the same test at every value of the other columns
                cols = ", ".join(f'"{k}"' for k in keys)
                for row in db.execute(f'SELECT {cols}, {summary} FROM (SELECT {cols}, {per_school} FROM "{table}" '
                                      f"GROUP BY UNITID, year, {cols}) GROUP BY {cols}").fetchall():
                    where = "; ".join(f"{k} = {v}" for k, v in zip(keys, row))
                    for j, m in enumerate(chunk):
                        tested, ok = row[len(keys) + 2 * j] or 0, row[len(keys) + 2 * j + 1] or 0
                        if tested:
                            db.execute("INSERT INTO breakdown_slices VALUES (?,?,?,?,?,?,?)",
                                       (name, table, m, where, tested, ok, "loaded" if tested == ok else "failed"))
        if loaded:
            db.executemany("INSERT INTO breakdown_parts VALUES (?,?,?,?)", [(name, table, c, label) for c, label in parts])

    # Sets stored as columns: one result per set and table.
    for table, name, total in db.execute('SELECT DISTINCT "table", breakdown_set, set_total FROM dict_measures '
                                         "WHERE breakdown_set IS NOT NULL").fetchall():
        parts = db.execute('SELECT variable, COALESCE(plain_name, title) FROM dict_measures WHERE "table"=? AND breakdown_set=?',
                           (table, name)).fetchall()
        if total == ADDITIVE:
            tested = ok = no_detail = None
            status = "additive"
        else:
            added = " + ".join(f'COALESCE("{v}", 0)' for v, _ in parts)
            any_part = "COALESCE(" + ", ".join(f'"{v}"' for v, _ in parts) + ") IS NOT NULL"
            tested, ok, no_detail = db.execute(
                f'SELECT SUM({any_part}), SUM({any_part} AND {added} = "{total}"), SUM(NOT {any_part}) '
                f'FROM "{table}" WHERE "{total}" IS NOT NULL').fetchone()
            status = "loaded" if tested and tested == ok else "failed"
        db.execute("INSERT INTO breakdown_sets VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                   (name, table, "columns", None, total, None, total if total != ADDITIVE else None, len(parts),
                    tested, ok, no_detail, status))
        if status != "failed":
            db.executemany("INSERT INTO breakdown_parts VALUES (?,?,?,?)", [(name, table, v, label) for v, label in parts])


    db.execute('CREATE INDEX ix_breakdown_slices ON breakdown_slices (set_name, "table", measure, slice)')


def build_row_keys(db):
    """For each multi-row table, find the fewest category columns that pick out one row per school, and check the
    defaults in category_codes.csv: one at most per key column, none on a column that only describes the row, and
    together they must pick out exactly one row per school. Returns a list of problems."""
    db.executescript("""DROP TABLE IF EXISTS row_keys;
        CREATE TABLE row_keys ("table" TEXT, "column" TEXT, default_code TEXT, default_label TEXT);""")
    problems = []
    tables = {}
    for table, column in db.execute('SELECT DISTINCT "table", "column" FROM dict_category_codes ORDER BY rowid'):
        tables.setdefault(table, []).append(column)
    for table, columns in tables.items():
        rows = db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        key = None
        for size in range(1, len(columns) + 1):
            for combo in itertools.combinations(columns, size):
                cols = ", ".join(f'"{c}"' for c in combo)
                if db.execute(f'SELECT COUNT(*) FROM (SELECT 1 FROM "{table}" GROUP BY UNITID, year, {cols})').fetchone()[0] == rows:
                    key = combo
                    break
            if key:
                break
        if not key:
            problems.append(f"category_codes.csv: no set of category columns in {table} picks out one row per school")
            continue
        defaults = db.execute('SELECT "column", code, label FROM dict_category_codes WHERE "table" = ? AND "default" = \'yes\'',
                              (table,)).fetchall()
        for column in columns:
            mine = [(code, label) for c, code, label in defaults if c == column]
            if len(mine) > 1:
                problems.append(f"category_codes.csv: {table}.{column} has {len(mine)} default codes; it may have one")
            if mine and column not in key:
                problems.append(f"category_codes.csv: {table}.{column} only describes the row, so it takes no default")
            if column in key:
                db.execute("INSERT INTO row_keys VALUES (?,?,?,?)", (table, column, *(mine[0] if mine else (None, None))))
        chosen = [(c, code) for c, code, _ in defaults if c in key]
        if key and len(chosen) == len(key):                 # every key column has a default: one row per school?
            where = " AND ".join(f"CAST(\"{c}\" AS TEXT) = '{code}'" for c, code in chosen)
            most = db.execute(f'SELECT MAX(n) FROM (SELECT COUNT(*) n FROM "{table}" WHERE {where} GROUP BY UNITID, year)').fetchone()[0]
            if most and most > 1:
                problems.append(f"category_codes.csv: the defaults for {table} pick {most} rows for one school")
    return problems


def build(local_db=None, folder=None):
    """Load, check, then build. Stops with a list of problems if the dictionary does not fit the data."""
    db = sqlite3.connect(local_db or config.LOCAL_DB)
    try:
        load_tables(db, folder or config.DICTIONARY)
        problems = check(db)
        if problems:
            db.rollback()
            raise ValueError("The dictionary does not fit the data:\n  " + "\n  ".join(problems))
        build_value_labels(db)
        build_directory(db)
        build_groups(db)
        problems = build_row_keys(db)
        if problems:
            db.rollback()
            raise ValueError("The dictionary does not fit the data:\n  " + "\n  ".join(problems))
        build_breakdown_sets(db)
        db.commit()
        return {name: db.execute(f"SELECT COUNT(*) FROM dict_{name}").fetchone()[0] for name in TABLES}
    finally:
        db.close()


if __name__ == "__main__":
    for name, n in build().items():
        print(f"dict_{name:<18}{n:>7,} rows")
    con = sqlite3.connect(config.LOCAL_DB)
    print("directory: %d schools, %d columns" % (con.execute("SELECT COUNT(*) FROM directory").fetchone()[0],
                                                 len(con.execute("PRAGMA table_info(directory)").fetchall())))
    print("groups: %d, memberships: %d" % (con.execute("SELECT COUNT(*) FROM group_list").fetchone()[0],
                                           con.execute("SELECT COUNT(*) FROM group_membership").fetchone()[0]))
    print("breakdown sets (set and count column): " + ", ".join(f"{n} {s}" for s, n in con.execute(
        "SELECT status, COUNT(*) FROM breakdown_sets GROUP BY 1")))
    con.close()
