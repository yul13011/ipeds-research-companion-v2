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
       detail_links      each summary measure's detailed equivalent, tested school by school
       breakdown_sets    every named breakdown, tested: do its parts add up to its total?
       breakdown_parts   the parts of each breakdown that passed
       breakdown_slices  for sets in tables keyed by several category columns: every value of the
                         other columns at which the set adds up (bachelor's degrees by field,
                         undergraduates by age), not only the default
       year_checks       the row-key, link and breakdown-set tests run in every year, each year with its own
                         category rows (category_codes.csv, `years`); the tables above hold the latest year
       measure_years     for every measure and year: where it is stored that year and how many values it has
       rate_years        for every rate and year: how many schools have each of its counts that year
       year_titles       each year's own codebook title for measures whose title names a year

No IPEDS convention is decided in this file. It only applies what the dictionary tables say.

Run:  python build/build_dictionary.py     (fast; run after any change to a dictionary table,
                                            except special_codes.csv, which needs build_data.py)
"""
import csv
import json
import itertools
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

TABLES = ["measures", "terms", "school_groups", "group_members", "school_nicknames",
          "rates", "category_codes", "year_meaning", "outside_ipeds", "special_codes", "measure_history",
          "comparability_breaks", "breakdown_exceptions"]
BREAK_KINDS = ("definition change", "context")              # comparability_breaks.csv `kind`
BREAK_STATUS = ("draft", "approved")                        # only approved rows may be shown
HISTORY_STATUS = ("in use", "to review", "rejected")       # measure_history.csv; only rows in use are used
IDENTITY = ["INSTNM", "IALIAS", "CITY", "STABBR"]          # always in the directory, from HD
FILTER_KINDS = ("column", "universe")                       # groups defined by codes in directory columns
METHODS = ("sum of counts", "weighted average")            # how a rates.csv row combines schools; see README
ADDITIVE = "sum of parts"                                   # a breakdown set with no total row or column in the data
MEMBERSHIP = ("", "as of latest year")                      # school_groups.csv `membership`; blank is each year's own list


def split(cell, sep=","):
    return [x.strip() for x in (cell or "").split(sep) if x.strip()]


class Scope:
    """What a run of the year tests covers. With no tables and no measures it covers everything (the full build).
    `tables`: category tables whose row keys, breakdown sets and links into them are retested.
    `measures`: measures (TABLE.VARIABLE) whose links and breakdown-set columns are retested."""

    def __init__(self, tables=None, measures=None):
        self.tables = None if tables is None else set(tables)
        self.measures = None if measures is None else {m.upper() for m in measures}

    @property
    def full(self):
        return self.tables is None and self.measures is None

    def has_table(self, table):
        return self.full or table in (self.tables or ())

    def has_measure(self, measure):
        return self.full or (measure or "").upper() in (self.measures or ())

    def has_link(self, summary, detailed):
        return self.full or self.has_measure(summary) or self.has_measure(detailed) or \
            self.has_table(detailed.partition(".")[0])


RESULTS = """
    CREATE {temp} TABLE IF NOT EXISTS row_keys ("table" TEXT, "column" TEXT, default_code TEXT, default_label TEXT,
                                                default_sum_of TEXT);
    CREATE {temp} TABLE IF NOT EXISTS detail_links (measure TEXT, detailed TEXT, rows TEXT, n_schools INTEGER,
                                                    n_agree INTEGER, n_flagged INTEGER, n_unexplained INTEGER, status TEXT);
    CREATE {temp} TABLE IF NOT EXISTS detail_link_exceptions (measure TEXT, unitid INTEGER, summary REAL, detailed REAL,
                                                              flag INTEGER);
    CREATE {temp} TABLE IF NOT EXISTS breakdown_sets (set_name TEXT, "table" TEXT, stored_as TEXT, "column" TEXT,
                                                      total TEXT, fixed TEXT, measure TEXT, n_parts INTEGER,
                                                      n_tested INTEGER, n_ok INTEGER, n_no_detail INTEGER, status TEXT);
    CREATE {temp} TABLE IF NOT EXISTS breakdown_parts (set_name TEXT, "table" TEXT, part TEXT, label TEXT);
    CREATE {temp} TABLE IF NOT EXISTS breakdown_slices (set_name TEXT, "table" TEXT, measure TEXT, slice TEXT,
                                                        n_tested INTEGER, n_ok INTEGER, status TEXT);"""
RESULT_TABLES = ("row_keys", "detail_links", "detail_link_exceptions", "breakdown_sets", "breakdown_parts",
                 "breakdown_slices")


def result_tables(db, temp=False, fresh=False):
    """The tables the year tests write. The latest year writes the stored tables the app reads; an earlier year
    writes temporary ones of the same names, read only to record its results. `fresh` empties the stored ones."""
    for t in RESULT_TABLES:
        if temp:
            db.execute(f'DROP TABLE IF EXISTS temp."{t}"')
        elif fresh:
            db.execute(f'DROP TABLE IF EXISTS main."{t}"')
    db.executescript(RESULTS.format(temp="TEMP" if temp else ""))
    if not temp:
        db.execute('CREATE INDEX IF NOT EXISTS ix_breakdown_slices ON breakdown_slices (set_name, "table", measure, slice)')


def years_in(cell):
    """'2015-2019' or '2015-2017, 2020' -> those years; blank -> None (every year). Raises ValueError if unreadable."""
    if not cell:
        return None
    out = set()
    for part in split(cell):
        first, _, last = part.partition("-")
        out |= set(range(int(first), int(last or first) + 1))
    return out


def in_years(cell, year):
    """Does a `years` cell cover this year? (Also an SQL function.) An unreadable cell covers nothing; check() names it."""
    try:
        covered = years_in(cell)
    except ValueError:
        return 0
    return 1 if covered is None or year in covered else 0


def load_tables(db, folder, names=None):
    """Step 1: each CSV becomes dict_<name>. Every column is text; an empty cell is missing. Category rows also get
    `in_latest`: whether the row's years cover the latest year, the year the app answers from."""
    for name in TABLES if names is None else names:
        with open(Path(folder) / f"{name}.csv", newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        header, body = rows[0], rows[1:]
        db.execute(f"DROP TABLE IF EXISTS dict_{name}")
        db.execute(f"CREATE TABLE dict_{name} ({', '.join(chr(34) + h + chr(34) + ' TEXT' for h in header)})")
        db.executemany(f"INSERT INTO dict_{name} VALUES ({', '.join('?' * len(header))})",
                       [[(c.strip() or None) for c in r] for r in body])
    db.create_function("in_years", 2, in_years)
    if names is not None and "category_codes" not in names:
        return
    db.execute("ALTER TABLE dict_category_codes ADD COLUMN in_latest TEXT")
    db.execute("UPDATE dict_category_codes SET in_latest = CASE WHEN in_years(years, (SELECT MAX(year) FROM _tables)) "
               "THEN 'yes' ELSE 'no' END")


def check(db, wording_only=False):
    """Step 2: every reference in the dictionary must exist in the data. Returns a list of problems. `wording_only`
    (a change to wording alone) leaves out the two checks that read the data rows: group codes and `same_as`."""
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
        if not wording_only and kind in FILTER_KINDS and table in data and all(c.upper() in data[table] for c in split(column)):
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
    for table, column, code, same in db.execute('SELECT "table", "column", code, same_as FROM dict_category_codes '
                                                "WHERE same_as IS NOT NULL").fetchall():
        other, _, other_code = same.partition("=")
        other, other_code = other.strip(), other_code.strip()
        where = f"category_codes.csv: {table}.{column} {code} same as '{same}'"
        if not other or not other_code:
            problems.append(f"{where} is not written COLUMN = code")
            continue
        exists(f"{table}.{other}", where)
        both_filled = column.upper() in data.get(table, ()) and other.upper() in data.get(table, ())
        if not wording_only and other.upper() != column.upper() and both_filled:
            for y, a, both, b in db.execute(       # where both columns are filled, the two rows must be the same rows
                    f'SELECT year, SUM(CAST("{column}" AS TEXT) = ?), SUM(CAST("{column}" AS TEXT) = ? AND CAST("{other}" '
                    f'AS TEXT) = ?), SUM(CAST("{other}" AS TEXT) = ?) FROM "{table}" WHERE "{column}" IS NOT NULL AND '
                    f'"{other}" IS NOT NULL GROUP BY year', (code, code, other_code, other_code)):
                if not a == both == b:
                    problems.append(f"{where}: in {y}, {a} rows have {column} {code} and {b} have {other} {other_code}, "
                                    f"but only {both} have both")
    for table, name, n in db.execute('SELECT "table", breakdown_set, COUNT(DISTINCT COALESCE(set_total, \'\') || \'|\' || '
                                     "COALESCE(set_fixed, '')) FROM dict_category_codes WHERE breakdown_set IS NOT NULL GROUP BY 1, 2"):
        if n > 1:
            problems.append(f"category_codes.csv: the rows of '{name}' in {table} do not all name the same total and fixed values")
    for table, name, total in db.execute('SELECT DISTINCT "table", breakdown_set, set_total FROM dict_measures WHERE breakdown_set IS NOT NULL'):
        if total != ADDITIVE:
            exists(f"{table}.{total}", f"measures.csv breakdown set '{name}'")
    for name in ("category_codes", "year_meaning", "measure_history"):
        for (cell,) in db.execute(f"SELECT DISTINCT years FROM dict_{name} WHERE years IS NOT NULL"):
            try:
                years_in(cell)
            except ValueError:
                problems.append(f"{name}.csv: years '{cell}' is not a year or a range such as 2015-2019")
    rules = db.execute('SELECT "table", years FROM dict_year_meaning').fetchall()
    for t, y in db.execute("SELECT DISTINCT local_table, year FROM _tables WHERE kind = 'data' ORDER BY 1, 2"):
        mine = [cell for table, cell in rules if table == t]
        if not mine:
            problems.append(f"year_meaning.csv: no row for data table {t}")
        elif not any(in_years(cell, y) for cell in mine):
            problems.append(f"year_meaning.csv: no row for data table {t} covers {y}")
    for measure, table, variable in db.execute("SELECT measure, earlier_table, earlier_variable FROM dict_measure_history"):
        if (measure or "").upper() not in measures:
            problems.append(f"measure_history.csv: {measure} is not in measures.csv")
        exists(f"{table}.{variable}", f"measure_history.csv {measure}")
    for kind, tables, status, first, start in db.execute(
            "SELECT kind, tables, status, first_release, period_from FROM dict_comparability_breaks"):
        if kind not in BREAK_KINDS or status not in BREAK_STATUS:
            problems.append(f"comparability_breaks.csv: kind must be one of {BREAK_KINDS} and status one of {BREAK_STATUS}")
        if not first and not start:
            problems.append("comparability_breaks.csv: a row needs a first release or a period it covers")
        for t in split(tables):
            if t not in data:
                problems.append(f"comparability_breaks.csv: {t} is not a data table")
    sets = {(t, s) for t, s in db.execute('SELECT "table", breakdown_set FROM dict_category_codes WHERE breakdown_set IS '
                                          'NOT NULL UNION SELECT "table", breakdown_set FROM dict_measures WHERE '
                                          "breakdown_set IS NOT NULL")}
    for name, table, year, unitid in db.execute('SELECT breakdown_set, "table", year, unitid FROM dict_breakdown_exceptions'):
        if (table, name) not in sets:
            problems.append(f"breakdown_exceptions.csv: '{name}' is not a breakdown set of {table}")
        if not db.execute("SELECT 1 FROM main.HD WHERE UNITID = ? AND year = ?", (int(unitid), int(year))).fetchone():
            problems.append(f"breakdown_exceptions.csv: school {unitid} is not in the directory for {year}")
    for table, column, code, summed, cell in db.execute('SELECT "table", "column", code, sum_of, years FROM '
                                                        "dict_category_codes WHERE sum_of IS NOT NULL").fetchall():
        rows_then = {c for c, ys in db.execute('SELECT code, years FROM dict_category_codes WHERE "table" = ? AND '
                                               '"column" = ? AND sum_of IS NULL', (table, column)) if ys == cell}
        for part in split(summed):                      # a summed row adds up rows of the same column and years
            if part not in rows_then:
                problems.append(f"category_codes.csv: {table}.{column} {code} adds up {part}, which has no row for {cell}")
    for measure, status in db.execute("SELECT measure, status FROM dict_measure_history"):
        if status not in HISTORY_STATUS:
            problems.append(f"measure_history.csv: {measure} has status '{status}'; it must be one of {HISTORY_STATUS}")
    for name, membership in db.execute('SELECT "group", membership FROM dict_school_groups'):
        if (membership or "") not in MEMBERSHIP:
            problems.append(f"school_groups.csv '{name}': membership must be blank or '{MEMBERSHIP[1]}'")
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
                values |= {str(v) for (v,) in db.execute(        # values seen in the year the app answers from;
                    f'SELECT DISTINCT "{col}" FROM directory WHERE "{col}" IS NOT NULL '   # groups for each year are 5b
                    "AND year = (SELECT MAX(year) FROM directory)")}
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
                db.execute(f"DELETE FROM group_membership WHERE group_name = ? AND NOT EXISTS (SELECT 1 FROM directory "
                           f"WHERE UNITID = group_membership.unitid AND year = group_membership.year AND {where})", (name,))
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
    latest = db.execute("SELECT MAX(year) FROM directory").fetchone()[0]
    for (name,) in db.execute('SELECT DISTINCT "group" FROM dict_school_groups WHERE membership = ?', (MEMBERSHIP[1],)).fetchall():
        db.execute("DELETE FROM group_membership WHERE group_name = ? AND year < ?", (name, latest))
        db.execute("INSERT INTO group_membership SELECT m.group_name, d.year, d.UNITID FROM group_membership m "   # the latest
                   "JOIN directory d ON d.UNITID = m.unitid AND d.year < ? WHERE m.group_name = ? AND m.year = ?",  # list, in
                   (latest, name, latest))                                                                           # every year
    db.execute("CREATE INDEX ix_group_membership ON group_membership (group_name, year, unitid)")
    db.execute("CREATE INDEX ix_group_membership_school ON group_membership (unitid, year)")
    db.execute("UPDATE group_list SET n_schools = (SELECT COUNT(*) FROM group_membership m WHERE m.group_name = "
               "group_list.group_name AND m.year = (SELECT MAX(year) FROM directory))")   # schools in the latest year
    db.execute('UPDATE group_list SET word_note = (SELECT MAX(word_note) FROM dict_school_groups g WHERE g."group" = group_list.group_name)')


def conditions(fixed):
    """'CIPCODE = 99; MAJORNUM = 1' -> SQL. The fixed values of the other category columns of a set."""
    parts = []
    for item in split(fixed, ";"):
        column, _, value = item.partition("=")
        parts.append(f"CAST(\"{column.strip()}\" AS TEXT) = '{value.strip()}'")
    return " AND ".join(parts) or "1=1"


def build_breakdown_sets(db, scope=Scope()):
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
    Only what `scope` covers is retested; its earlier results are replaced. Returns the sets stored as columns that
    were retested, {(set, table)}.
    """
    retested = set()

    def kept(name, table):                              # rows of schools the owner approved as exceptions are not
        quoted = name.replace("'", "''")                # tested (breakdown_exceptions.csv): their total is shown
        return (f"NOT EXISTS (SELECT 1 FROM dict_breakdown_exceptions e WHERE e.breakdown_set = '{quoted}' AND "
                f"e.\"table\" = '{table}' AND CAST(e.year AS INTEGER) = \"{table}\".year AND "
                f"CAST(e.unitid AS INTEGER) = \"{table}\".UNITID)")

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
        if not scope.has_table(table):                  # only the count columns of the measures in scope; a measure
            mine = [m.partition(".")[2] for m in scope.measures if m.partition(".")[0] == table.upper()]  # that is no
            for t in ("breakdown_sets", "breakdown_slices"):                                     # longer a count loses
                db.executemany(f'DELETE FROM {t} WHERE set_name=? AND "table"=? AND UPPER(measure)=?',  # its results
                               [(name, table, m) for m in mine])
            counts = [m for m in counts if scope.has_measure(f"{table}.{m}")]
            if not counts:
                db.execute('DELETE FROM breakdown_parts WHERE set_name=? AND "table"=?', (name, table))
                if db.execute('SELECT 1 FROM breakdown_sets WHERE set_name=? AND "table"=? AND status <> \'failed\'',
                              (name, table)).fetchone():
                    db.executemany("INSERT INTO breakdown_parts VALUES (?,?,?,?)", [(name, table, c, label) for c, label in parts])
                continue
        for t in ("breakdown_sets", "breakdown_slices"):
            db.executemany(f'DELETE FROM {t} WHERE set_name=? AND "table"=? AND measure=?', [(name, table, m) for m in counts])
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
                                  f"AND {kept(name, table)} GROUP BY UNITID, year)").fetchone()
                results = [(flat[2 * j] or 0, flat[2 * j + 1] or 0) for j in range(len(chunk))]
            for m, (tested, ok) in zip(chunk, results):
                status = "additive" if total == ADDITIVE else ("loaded" if tested and tested == ok else "failed" if tested else "no data")
                db.execute("INSERT INTO breakdown_sets VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           (name, table, "rows", column, total, fixed, m, len(parts), tested, ok, None, status))
            if keys and total != ADDITIVE:                  # the same test at every value of the other columns
                cols = ", ".join(f'"{k}"' for k in keys)
                for row in db.execute(f'SELECT {cols}, {summary} FROM (SELECT {cols}, {per_school} FROM "{table}" '
                                      f"WHERE {kept(name, table)} GROUP BY UNITID, year, {cols}) GROUP BY {cols}").fetchall():
                    where = "; ".join(f"{k} = {v}" for k, v in zip(keys, row))
                    for j, m in enumerate(chunk):
                        tested, ok = row[len(keys) + 2 * j] or 0, row[len(keys) + 2 * j + 1] or 0
                        if tested:
                            db.execute("INSERT INTO breakdown_slices VALUES (?,?,?,?,?,?,?)",
                                       (name, table, m, where, tested, ok, "loaded" if tested == ok else "failed"))
        db.execute('DELETE FROM breakdown_parts WHERE set_name=? AND "table"=?', (name, table))
        if db.execute('SELECT 1 FROM breakdown_sets WHERE set_name=? AND "table"=? AND status <> \'failed\'',
                      (name, table)).fetchone():        # loaded for at least one count column
            db.executemany("INSERT INTO breakdown_parts VALUES (?,?,?,?)", [(name, table, c, label) for c, label in parts])

    # Sets stored as columns: one result per set and table.
    for table, name, total in db.execute('SELECT DISTINCT "table", breakdown_set, set_total FROM dict_measures '
                                         "WHERE breakdown_set IS NOT NULL").fetchall():
        parts = db.execute('SELECT variable, COALESCE(plain_name, title) FROM dict_measures WHERE "table"=? AND breakdown_set=?',
                           (table, name)).fetchall()
        if not scope.has_table(table) and not any(scope.has_measure(f"{table}.{v}") for v in [p for p, _ in parts] + [total]):
            continue
        retested.add((name, table))
        db.execute('DELETE FROM breakdown_sets WHERE set_name=? AND "table"=? AND stored_as=\'columns\'', (name, table))
        db.execute('DELETE FROM breakdown_parts WHERE set_name=? AND "table"=?', (name, table))
        if total == ADDITIVE:
            tested = ok = no_detail = None
            status = "additive"
        else:
            added = " + ".join(f'COALESCE("{v}", 0)' for v, _ in parts)
            any_part = "COALESCE(" + ", ".join(f'"{v}"' for v, _ in parts) + ") IS NOT NULL"
            tested, ok, no_detail = db.execute(
                f'SELECT SUM({any_part}), SUM({any_part} AND {added} = "{total}"), SUM(NOT {any_part}) '
                f'FROM "{table}" WHERE "{total}" IS NOT NULL AND {kept(name, table)}').fetchone()
            status = "loaded" if tested and tested == ok else "failed" if tested else "no data"
        db.execute("INSERT INTO breakdown_sets VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                   (name, table, "columns", None, total, None, total if total != ADDITIVE else None, len(parts),
                    tested, ok, no_detail, status))
        if status != "failed":
            db.executemany("INSERT INTO breakdown_parts VALUES (?,?,?,?)", [(name, table, v, label) for v, label in parts])
    return retested


def build_row_keys(db, only=None):
    """For each multi-row table, find the fewest category columns that pick out one row per school, and check the
    defaults in category_codes.csv: one at most per key column, none on a column that only describes the row, and
    together they must pick out exactly one row per school. `only`: these tables (None for all). Returns a list of
    problems."""
    problems = []
    tables = {}
    for table, column in db.execute('SELECT DISTINCT "table", "column" FROM dict_category_codes ORDER BY rowid'):
        if only is None or table in only:
            tables.setdefault(table, []).append(column)
    db.executemany('DELETE FROM row_keys WHERE "table" = ?', [(t,) for t in tables])
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
        defaults = db.execute('SELECT "column", code, label, sum_of FROM dict_category_codes WHERE "table" = ? AND '
                              "\"default\" = 'yes'", (table,)).fetchall()
        for column in columns:
            mine = [(code, label, summed) for c, code, label, summed in defaults if c == column]
            if len(mine) > 1:
                problems.append(f"category_codes.csv: {table}.{column} has {len(mine)} default codes; it may have one")
            if mine and column not in key:
                problems.append(f"category_codes.csv: {table}.{column} only describes the row, so it takes no default")
            if column in key:
                db.execute("INSERT INTO row_keys VALUES (?,?,?,?,?)", (table, column, *(mine[0] if mine else (None, None, None))))
        chosen = [(c, code) for c, code, _, summed in defaults if c in key and not summed]
        if key and len(chosen) == len(key):                 # every key column has a default: one row per school?
            where = " AND ".join(f"CAST(\"{c}\" AS TEXT) = '{code}'" for c, code in chosen)
            most = db.execute(f'SELECT MAX(n) FROM (SELECT COUNT(*) n FROM "{table}" WHERE {where} GROUP BY UNITID, year)').fetchone()[0]
            if most and most > 1:
                problems.append(f"category_codes.csv: the defaults for {table} pick {most} rows for one school")
    return problems


def parse_detail(text):
    """'EFA.EFTOTLT where EFALEVEL = 2; MAJORNUM = 1' -> ('EFA', 'EFTOTLT', {'EFALEVEL': '2', 'MAJORNUM': '1'})."""
    ref, _, rest = text.partition(" where ")
    table, _, column = ref.strip().partition(".")
    rows = {k.strip(): v.strip() for k, _, v in (x.partition("=") for x in rest.split(";")) if k.strip()}
    return table, column, rows


def build_detail_links(db, latest=True, scope=Scope()):
    """For each summary measure with a detailed equivalent: do the two agree at every school? A school with a summary
    of 0 and no detailed row agrees (IPEDS reports no row for nothing). In an earlier year whose detailed table is
    keyed by other category columns, the link's rows are read through that year's category rows (`same_as`); only
    where the year holds no such row is the link recorded as not in that year's data. Only the links `scope` covers
    are retested. Returns a list of problems."""
    problems = []
    measures = {f"{t}.{v}".upper() for t, v in db.execute('SELECT "table", variable FROM dict_measures')}
    for table, column, text in db.execute('SELECT "table", variable, detailed_measure FROM dict_measures '
                                          "WHERE detailed_measure IS NOT NULL").fetchall():
        dt, dc, rows = parse_detail(text)
        if not scope.has_link(f"{table}.{column}", f"{dt}.{dc}"):
            continue
        for t in ("detail_links", "detail_link_exceptions"):
            db.execute(f"DELETE FROM {t} WHERE measure = ?", (f"{table}.{column}",))
        if not db.execute(f'SELECT 1 FROM "{table}" WHERE "{column}" IS NOT NULL LIMIT 1').fetchone():
            continue                                    # no values in this year: nothing to test
        keys = {c.upper() for (c,) in db.execute('SELECT "column" FROM row_keys WHERE "table"=?', (dt,))}
        if not latest and keys:                         # an earlier year: its own columns and codes for the same rows
            rows = same_rows(db, dt, rows)
            if rows is None or {k.upper() for k in rows} != keys:       # the information is not in that year's data
                db.execute("INSERT INTO detail_links VALUES (?,?,?,?,?,?,?,?)",
                           (f"{table}.{column}", f"{dt}.{dc}", json.dumps(parse_detail(text)[2]), None, None, None, None,
                            "not in this year's data"))
                continue
        if f"{dt}.{dc}".upper() not in measures or {k.upper() for k in rows} != keys:
            problems.append(f"measures.csv: {table}.{column} names '{text}', which is not a measure with one value "
                            f"for each of its category columns ({', '.join(sorted(keys))})")
            continue
        where = " AND ".join(f'CAST(d."{k}" AS TEXT) = ?' for k in rows)
        pairs = db.execute(f'SELECT s.UNITID, s."{column}", d."{dc}" FROM "{table}" s LEFT JOIN (SELECT * FROM "{dt}" d '
                           f'WHERE {where}) d ON d.UNITID = s.UNITID AND d.year = s.year WHERE s."{column}" IS NOT NULL',
                           list(rows.values())).fetchall()
        differ = [(u, s, x) for u, s, x in pairs if not (s == x or (s == 0 and x is None))]
        rule = db.execute('SELECT parent_child_flag FROM dict_year_meaning WHERE "table"=?', (dt,)).fetchone()
        flags = {}
        if rule and rule[0]:                            # schools IPEDS flags as reporting with a related campus
            flag_column = rule[0].split(";")[0].strip().partition(".")[2]
            flags = dict(db.execute(f'SELECT UNITID, "{flag_column}" FROM FLAGS WHERE "{flag_column}" IN (1, 2)').fetchall())
        flagged = [u for u, _, _ in differ if u in flags]
        unexplained = len(differ) - len(flagged)
        db.execute("INSERT INTO detail_links VALUES (?,?,?,?,?,?,?,?)",
                   (f"{table}.{column}", f"{dt}.{dc}", json.dumps(rows), len(pairs), len(pairs) - len(differ), len(flagged),
                    unexplained, "loaded" if unexplained == 0 else "failed"))
        db.executemany("INSERT INTO detail_link_exceptions VALUES (?,?,?,?,?)",
                       [(f"{table}.{column}", u, s, x, flags.get(u)) for u, s, x in differ])
    return problems


def same_rows(db, table, rows):
    """{'EFFYALEV': '12'} -> {'EFFYLEV': '4'}: the rows a request names, in the category columns of the year being
    tested, through the `same_as` cells of that year's category rows. A row the year has (same column and code) is
    kept as it is. None when some row has no counterpart that year."""
    out = {}
    for column, code in rows.items():
        if db.execute('SELECT 1 FROM dict_category_codes WHERE "table"=? AND UPPER("column")=? AND code=?',
                      (table, column.upper(), str(code))).fetchone():
            out[column] = code
            continue
        match = db.execute('SELECT "column", code FROM dict_category_codes WHERE "table"=? AND '
                           "REPLACE(UPPER(same_as), ' ', '') = ?", (table, f"{column}={code}".upper().replace(" ", ""))).fetchone()
        if not match:
            return None
        out[match[0]] = match[1]
    return out


def at_year(db, year=None, need=None):
    """See every stacked table, and the category rows, as of one year: temporary views and copies of the same names,
    which SQLite reads before the stored tables. The tables the tests read many times (`need`; by default those with
    category rows, and FLAGS) are copied once for the year, which is much faster than reading all ten years at each
    test. at_year(db) removes them."""
    tested = need if need is not None else \
        {t for (t,) in db.execute('SELECT DISTINCT "table" FROM main.dict_category_codes')} | {"FLAGS"}
    made = dict(db.execute("SELECT name, type FROM sqlite_temp_master WHERE type IN ('table', 'view')").fetchall())
    for (t,) in db.execute("SELECT DISTINCT local_table FROM main._tables").fetchall():
        if t in made:
            db.execute(f'DROP {made[t].upper()} temp."{t}"')
        if year is not None:
            kind = "TABLE" if t in tested else "VIEW"
            db.execute(f'CREATE TEMP {kind} "{t}" AS SELECT * FROM main."{t}" WHERE year = {int(year)}')
    db.execute("DROP TABLE IF EXISTS temp.dict_category_codes")
    if year is not None:                                    # the rows whose years cover this year, in file order
        db.execute("CREATE TEMP TABLE dict_category_codes AS SELECT * FROM main.dict_category_codes "
                   f"WHERE in_years(years, {int(year)}) ORDER BY rowid")


def record_year(db, year, scope=Scope(), keyed=None, column_sets=()):
    """Keep this year's results of the row-key, link and breakdown-set tests in year_checks, replacing that year's
    earlier results for what this run covered (`scope`; `keyed`, the tables whose row keys it built; `column_sets`,
    the sets stored as columns it retested). 'no data' means the table, or the column, has no values that year
    (IPEDS did not collect it then)."""
    def covered(kind, name, table, measure):
        if kind == "row key":
            return keyed is None or table in keyed
        if kind == "link":
            return scope.has_link(name, measure)
        return scope.has_table(table) or scope.has_measure(f"{table}.{measure}") or (name, table) in column_sets
    old = db.execute("SELECT rowid, kind, name, \"table\", measure FROM year_checks WHERE year = ?", (year,)).fetchall()
    db.executemany("DELETE FROM year_checks WHERE rowid = ?", [(r,) for r, *rest in old if covered(*rest)])
    rows_in = lambda t: db.execute(f'SELECT COUNT(DISTINCT UNITID) FROM "{t}"').fetchone()[0]
    out = []
    keys = {}
    for t, c, code, summed in db.execute('SELECT "table", "column", default_code, default_sum_of FROM row_keys').fetchall():
        if keyed is None or t in keyed:
            keys.setdefault(t, []).append((c, code, summed))
    for t, cols in keys.items():
        schools = rows_in(t)
        ok = None
        if all(code is not None for _, code, _ in cols):    # a summed default is found when its parts are
            where = " AND ".join(f"CAST(\"{c}\" AS TEXT) IN ({', '.join(repr(x) for x in split(summed))})" if summed
                                 else f"CAST(\"{c}\" AS TEXT) = '{code}'" for c, code, summed in cols)
            ok = db.execute(f'SELECT COUNT(DISTINCT UNITID) FROM "{t}" WHERE {where}').fetchone()[0]
        status = "no data" if not schools else "no default" if ok is None else "loaded" if ok else "default not found"
        out.append((year, "row key", ", ".join(c for c, _, _ in cols), t, None, status, schools, ok))
    for measure, detailed, n, agree, status in db.execute(
            "SELECT measure, detailed, n_schools, n_agree, status FROM detail_links").fetchall():
        if covered("link", measure, None, detailed):
            out.append((year, "link", measure, detailed.partition(".")[0], detailed, status, n, agree))
    empty = {}
    for name, t, m, n, ok, status in db.execute(
            'SELECT set_name, "table", measure, n_tested, n_ok, status FROM breakdown_sets').fetchall():
        if not covered("set", name, t, m):
            continue
        if t not in empty:
            empty[t] = rows_in(t) == 0
        no_data = empty[t] or (status == "failed" and not n)   # the table, or this column, has no values that year
        out.append((year, "set", name, t, m, "no data" if no_data else status, n, ok))
    db.executemany("INSERT INTO year_checks VALUES (?,?,?,?,?,?,?,?)", out)


def link_tables(db, scope):
    """The summary and detailed tables of the links `scope` covers."""
    out = set()
    for table, column, text in db.execute('SELECT "table", variable, detailed_measure FROM main.dict_measures '
                                          "WHERE detailed_measure IS NOT NULL").fetchall():
        dt, dc, _ = parse_detail(text)
        if scope.has_link(f"{table}.{column}", f"{dt}.{dc}"):
            out |= {table, dt}
    return out


def test_years(db, years, scope=Scope(), verbose=False):
    """Run the row-key, link and breakdown-set tests in each of `years`, for what `scope` covers. Each year sees its
    own rows and category rows; the latest year writes the result tables the app reads. Returns a list of problems."""
    latest = db.execute("SELECT MAX(year) FROM main._tables").fetchone()[0]
    keyed, need = None, None
    if not scope.full:                                  # the tables this run reads: its own, and those of its links
        linked = link_tables(db, scope)
        keyed = (scope.tables or set()) | {t for t in linked
                                          if db.execute('SELECT 1 FROM main.dict_category_codes WHERE "table"=?', (t,)).fetchone()}
        need = keyed | linked | {m.partition(".")[0] for m in scope.measures or ()} | {"FLAGS"}
    problems = []
    for year in sorted(years):
        started = time.time()
        at_year(db, year, need)
        result_tables(db, temp=year != latest)          # an earlier year writes temporary result tables
        found = build_row_keys(db, keyed)
        found += build_detail_links(db, year == latest, scope) if not found else []
        problems += [f"{year}: {p}" for p in found]
        if not found:
            column_sets = build_breakdown_sets(db, scope)
            record_year(db, year, scope, keyed, column_sets)
        for t in RESULT_TABLES:
            db.execute(f'DROP TABLE IF EXISTS temp."{t}"')
        if verbose:
            print(f"  {year}: tested in {time.time() - started:.0f} s", flush=True)
    at_year(db)
    return problems


def columns_by_year(db):
    """{(table, year): {COLUMN: stored name}}: the columns each release has. Without a column registry (the tests'
    made-up database), every stored column counts in every year."""
    stored = {}
    for (t,) in db.execute("SELECT DISTINCT local_table FROM main._tables").fetchall():
        stored[t] = {r[1].upper(): r[1] for r in db.execute(f'PRAGMA main.table_info("{t}")')}
    out = {}
    try:
        for t, c, y in db.execute("SELECT t.local_table, UPPER(c.column), t.year FROM _columns c JOIN _tables t "
                                  "ON t.source_table = c.source_table AND t.release = c.release"):
            if c in stored.get(t, {}):
                out.setdefault((t, y), {})[c] = stored[t][c]
    except sqlite3.OperationalError:
        for t, y in db.execute("SELECT DISTINCT local_table, year FROM main._tables"):
            out[(t, y)] = stored.get(t, {})
    return out


def build_measure_years(db, only=None, years=None):
    """measure_years: for every measure and year, where it is stored that year (measure_history.csv names the
    earlier tables of the reorganised cost and aid measures) and how many values it has. A year with no row is a
    year IPEDS did not collect it. rate_years: for every rate and year, how many values each of its counts has; a
    rate is available in a year only when every count has values. year_titles: each year's own codebook title for
    measures whose title names a year. `only` (measures) and `years` limit what is recounted; None for all."""
    if only is None and years is None:
        db.executescript("DROP TABLE IF EXISTS measure_years; DROP TABLE IF EXISTS year_titles;")
    db.executescript("""DROP TABLE IF EXISTS rate_years;
        CREATE TABLE IF NOT EXISTS measure_years (measure TEXT, year INTEGER, "table" TEXT, variable TEXT, n_values INTEGER);
        CREATE INDEX IF NOT EXISTS ix_measure_years ON measure_years (measure, year);
        CREATE TABLE rate_years (rate TEXT, rate_measure TEXT, applies_to TEXT, numerator TEXT, denominator TEXT,
                                 year INTEGER, numerator_values INTEGER, denominator_values INTEGER, available TEXT);
        CREATE TABLE IF NOT EXISTS year_titles (measure TEXT, year INTEGER, title TEXT);""")
    cols = columns_by_year(db)
    every = sorted({y for _, y in cols})
    years = every if years is None else sorted(set(years) & set(every))
    wanted_m = None if only is None else {m.upper() for m in only}
    history = {}                                            # rows marked "to review" are not used
    for m, t, v, cell in db.execute("SELECT measure, earlier_table, earlier_variable, years FROM dict_measure_history "
                                    "WHERE status = 'in use'"):
        history.setdefault(m.upper(), []).append((t, v, cell))
    measures = [f"{t}.{v}" for t, v in db.execute('SELECT "table", variable FROM dict_measures')]
    listed = {m.upper() for m in measures}                  # the counts behind each rate, listed as measures or not
    for (m,) in db.execute("SELECT numerator FROM dict_rates UNION SELECT denominator FROM dict_rates").fetchall():
        if m and m.upper() not in listed:
            measures.append(m)
            listed.add(m.upper())
    if wanted_m is not None:
        measures = [m for m in measures if m.upper() in wanted_m]
    gone = [(m, y) for m in measures for y in years]
    dropped = [(m, y) for m in (only or ()) if m.upper() not in listed for y in years]   # measures no longer listed
    for t in ("measure_years", "year_titles"):
        db.executemany(f"DELETE FROM {t} WHERE measure = ? AND year = ?", gone + dropped)
    for y in years:
        wanted = {}
        for m in measures:
            t, _, v = m.partition(".")
            column = cols.get((t, y), {}).get(v.upper())    # the measure's own column first; else an earlier name
            if not column:
                for et, ev, cell in history.get(m.upper(), []):
                    if in_years(cell, y) and cols.get((et, y), {}).get(ev.upper()):
                        t, v = et, ev
                        column = cols[(et, y)][ev.upper()]
                        break
            if column:
                wanted.setdefault(t, []).append((m, column))
        for t, items in wanted.items():
            for i in range(0, len(items), 200):
                chunk = items[i:i + 200]
                counts = db.execute(f'SELECT {", ".join(f"COUNT({chr(34)}{c}{chr(34)})" for _, c in chunk)} '
                                    f'FROM main."{t}" WHERE year = ?', (y,)).fetchone()
                db.executemany("INSERT INTO measure_years VALUES (?,?,?,?,?)",
                               [(m, y, t, c, n) for (m, c), n in zip(chunk, counts)])
    db.execute("""INSERT INTO rate_years
        SELECT r.rate, r.rate_measure, r.applies_to, r.numerator, r.denominator, y.year, n.n_values, d.n_values,
               CASE WHEN COALESCE(n.n_values, 0) > 0 AND COALESCE(d.n_values, 0) > 0 THEN 'yes' ELSE 'no' END
        FROM dict_rates r JOIN (SELECT DISTINCT year FROM measure_years) y
        LEFT JOIN measure_years n ON UPPER(n.measure) = UPPER(r.numerator) AND n.year = y.year
        LEFT JOIN measure_years d ON UPPER(d.measure) = UPPER(r.denominator) AND d.year = y.year""")
    db.execute("CREATE TEMP TABLE IF NOT EXISTS recounted (measure TEXT, year INTEGER)")
    db.execute("DELETE FROM recounted")
    db.executemany("INSERT INTO recounted VALUES (?, ?)", gone)
    try:
        db.execute("""INSERT INTO year_titles
            SELECT my.measure, my.year, MAX(v.varTitle) FROM measure_years my
            JOIN recounted r ON r.measure = my.measure AND r.year = my.year
            JOIN dict_measures m ON m."table" || '.' || m.variable = my.measure
            JOIN _tables t ON t.local_table = my."table" AND t.year = my.year
            JOIN VARTABLE v ON UPPER(v.TableName) = UPPER(t.source_table) AND UPPER(v.VarName) = UPPER(my.variable)
                           AND v.year = my.year
            WHERE m.title GLOB '*[12][09][0-9][0-9]*' GROUP BY my.measure, my.year""")
    except sqlite3.OperationalError:                        # no codebook in the tests' made-up database
        pass
    db.execute("DROP TABLE temp.recounted")


def build_measure_checks(db, only=None, tables=None, years=None):
    """measure_checks: every set-up measure, in every year it exists, checked for what it needs to be answered. Each
    problem is listed for the owner's review; the build does not stop for it.
      - never a value: no school has a value in any year;
      - codes without labels: a coded measure whose values in a year include codes the codebook does not label;
      - no way to pick one row: a table with several rows per school and no category rows to pick one, that year;
      - no reporting form: a finance line that does not say which form it is on.
    `only` (measures), `tables` and `years` limit the recheck to what a change touched; None rechecks everything."""
    if only is None and tables is None and years is None:
        db.execute("DROP TABLE IF EXISTS measure_checks")
    db.execute('CREATE TABLE IF NOT EXISTS measure_checks (measure TEXT, "check" TEXT, detail TEXT)')
    wanted = None
    if only is not None or tables is not None or years is not None:
        wanted = {m.upper() for m in (only or ())}
        wanted |= {f"{t}.{v}".upper() for t, v in db.execute('SELECT "table", variable FROM dict_measures') if t in (tables or ())}
        if years:                                   # a new or replaced release: every measure
            wanted |= {m.upper() for (m,) in db.execute("SELECT DISTINCT measure FROM measure_years")}
        db.executemany("DELETE FROM measure_checks WHERE UPPER(measure) = ?", [(m,) for m in wanted])
    seen = {}
    for m, y, t, v, n in db.execute('SELECT measure, year, "table", variable, n_values FROM measure_years ORDER BY year'):
        seen.setdefault(m, []).append((y, t, v, n))
    keyed = {(t, y) for t, y in db.execute("SELECT \"table\", year FROM year_checks WHERE kind = 'row key' AND "
                                           "status IN ('loaded', 'no default')")}
    out = []
    for table, variable, unit, per_school, form in db.execute(
            'SELECT "table", variable, unit, rows_per_school, reporting_form FROM dict_measures WHERE in_first_version = \'yes\''):
        m = f"{table}.{variable}"
        if wanted is not None and m.upper() not in wanted:
            continue
        mine = seen.get(m, [])
        if not any(n for *_, n in mine):
            out.append((m, "never a value", "no school has a value in any year"))
        if unit == "coded":
            for y, t, v, n in mine:
                if not n:
                    continue
                missing = db.execute(f'SELECT COUNT(DISTINCT CAST("{v}" AS TEXT)) FROM main."{t}" WHERE year = ? AND "{v}" IS '
                                     f'NOT NULL AND CAST("{v}" AS TEXT) NOT IN (SELECT code FROM value_labels WHERE '
                                     'local_table = ? AND "column" = ? AND year = ?)', (y, t, v.upper(), y)).fetchone()[0]
                if missing:
                    out.append((m, "codes without labels", f"{y}: {missing} code(s) the codebook does not label"))
        if (per_school or "").startswith("many"):
            gaps = [y for y, t, _, n in mine if n and (t, y) not in keyed]
            if gaps:
                out.append((m, "no way to pick one row", f"several rows per school, no category rows: {gaps[0]}-{gaps[-1]}"))
        if table.startswith("F_") and not form:
            out.append((m, "no reporting form", "a finance line must say which form it is on"))
    db.executemany("INSERT INTO measure_checks VALUES (?,?,?)", out)


def build_name_clashes(db):
    """name_clashes: names shown for more than one measure (the plain name, or else the IPEDS title, compared without
    case or extra spaces). Each is flagged for a plain name; the build does not stop for it."""
    db.executescript("""DROP TABLE IF EXISTS name_clashes;
        CREATE TABLE name_clashes (name TEXT, n INTEGER, measures TEXT);""")
    names = {}
    for t, v, title, plain in db.execute('SELECT "table", variable, title, plain_name FROM dict_measures ORDER BY rowid'):
        names.setdefault(" ".join((plain or title or "").lower().split()), []).append(f"{t}.{v}")
    db.executemany("INSERT INTO name_clashes VALUES (?,?,?)",
                   [(n, len(ms), "; ".join(ms)) for n, ms in names.items() if len(ms) > 1])


def full_build(db, folder, verbose=False):
    """Everything, from the dictionary folder: load, check, directory and groups, the tests in every year, the
    years of every measure. Stops with a list of problems if the dictionary does not fit the data."""
    load_tables(db, folder)
    problems = check(db)
    if problems:
        raise ValueError("The dictionary does not fit the data:\n  " + "\n  ".join(problems))
    build_value_labels(db)
    build_directory(db)
    build_groups(db)
    db.executescript("""DROP TABLE IF EXISTS year_checks;
        CREATE TABLE year_checks (year INTEGER, kind TEXT, name TEXT, "table" TEXT, measure TEXT, status TEXT,
                                  n_tested INTEGER, n_ok INTEGER);""")
    result_tables(db, fresh=True)
    years = [y for (y,) in db.execute("SELECT DISTINCT year FROM _tables ORDER BY year").fetchall()]
    problems = test_years(db, years, Scope(), verbose)
    if problems:
        raise ValueError("The dictionary does not fit the data:\n  " + "\n  ".join(problems))
    build_measure_years(db)
    build_measure_checks(db)
    build_name_clashes(db)


def build(local_db=None, folder=None, verbose=False, full=False, table=None):
    """Bring the database up to date with the dictionary folder. By default only what changed since the last build
    is rerun (build/changes.py); `full` reruns everything; `table` reloads that one dictionary table on its own.
    Returns the row count of each dictionary table."""
    from build import changes
    db = sqlite3.connect(local_db or config.LOCAL_DB)
    folder = folder or config.DICTIONARY
    try:
        db.create_function("in_years", 2, in_years)
        fresh = changes.fingerprints(db, folder, sys.modules[__name__])
        steps = None if full or not changes.usable(db) else             changes.update(db, folder, sys.modules[__name__], only=table, verbose=verbose)
        changes.mark(db, "in progress")
        if steps is None:
            full_build(db, folder, verbose)
            steps = ["full rebuild"]
        changes.mark(db, "finished", fresh, only=table)
        if verbose:
            print("; ".join(steps))
        return {name: db.execute(f"SELECT COUNT(*) FROM dict_{name}").fetchone()[0] for name in TABLES}
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Load the dictionary folder into the local database.")
    parser.add_argument("--full", action="store_true", help="rerun everything (before each part's final report and "
                        "for every yearly update)")
    parser.add_argument("--table", help="reload this one dictionary table, for example terms")
    args = parser.parse_args()
    for name, n in build(verbose=True, full=args.full, table=args.table).items():
        print(f"dict_{name:<18}{n:>7,} rows")
    con = sqlite3.connect(config.LOCAL_DB)
    print("directory: %d schools in the latest year, %d school-years, %d columns" % (
        con.execute("SELECT COUNT(*) FROM directory WHERE year = (SELECT MAX(year) FROM directory)").fetchone()[0],
        con.execute("SELECT COUNT(*) FROM directory").fetchone()[0],
                                                 len(con.execute("PRAGMA table_info(directory)").fetchall())))
    print("groups: %d, memberships: %d" % (con.execute("SELECT COUNT(*) FROM group_list").fetchone()[0],
                                           con.execute("SELECT COUNT(*) FROM group_membership").fetchone()[0]))
    print("detail links: " + ", ".join(f"{n} {s}" for s, n in con.execute("SELECT status, COUNT(*) FROM detail_links GROUP BY 1")))
    for (m,) in con.execute("SELECT measure FROM detail_links WHERE status = 'failed'"):
        print(f"  not loaded: {m} differs at a school IPEDS does not flag as reporting with a related campus")
    print("breakdown sets (set and count column): " + ", ".join(f"{n} {s}" for s, n in con.execute(
        "SELECT status, COUNT(*) FROM breakdown_sets GROUP BY 1")))
    con.close()
