"""Tests for Stage 1 (build/build_data.py).

Two groups:
  - BuildLogic: runs the build on tiny made-up databases in a temporary folder. Always runs.
  - RealDatabase: checks the real local database against the real 2024-25 source.
    Skipped if the local database has not been built yet.

Run:  python -m unittest discover -s tests -v
"""
import csv
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from latest import latest_only  # the tests' own expected figures use the latest year only
from build import build_data

RULES = ({("-1", "Not reported"): ("missing", "Not reported"), ("-2", "Not applicable"): ("missing", "Not applicable"),
          ("-2", "Not classified"): ("keep", "")},
         {("ADM", "SYSNAME"): {"-2": ("missing", "Not applicable")}})


def make_source(path, year, extra_column=False):
    """A made-up yearly database: two data tables and the two codebook tables the cleaning reads.

    ADM has one of everything the cleaning must handle:
      NAME    text, padded and blank
      APPLCN  a count with a missing value and a true zero
      NETPR   a real negative number (codebook lists no special code for it)
      POLICY  a coded column with -1 Not reported and -2 Not applicable
      CLASS   a coded column whose -2 label is marked 'keep'
      FTE     codebook-numeric but stored as text, with one value that will not convert
      SYSNAME text holding -2 with no codebook entry; covered by a table-and-column rule
    """
    yy = str(year)[2:]
    con = sqlite3.connect(path)
    extra = ", NEWCOL INTEGER" if extra_column else ""
    con.execute(f"CREATE TABLE ADM{year} (UNITID INTEGER, NAME TEXT, APPLCN INTEGER, NETPR INTEGER, "
                f"POLICY INTEGER, CLASS INTEGER, FTE TEXT, SYSNAME TEXT{extra})")
    rows = [(1, "Alpha College   ", 100, -500, 1, 5, "12.50 ", "State System  "),
            (2, " ", None, 2000, -1, -2, "7", "-2   "),
            (3, "Gamma", 0, -2, -2, 3, "n/a", "-2")]
    con.executemany(f"INSERT INTO ADM{year} VALUES (?,?,?,?,?,?,?,?{',9' if extra_column else ''})", rows)
    con.execute(f"CREATE TABLE GR{year} (UNITID INTEGER, GRTYPE INTEGER, GRTOTLT INTEGER)")
    con.executemany(f"INSERT INTO GR{year} VALUES (?,?,?)", [(1, 2, 80), (1, 3, 60), (2, 2, 40), (2, 3, None)])
    con.execute(f"CREATE TABLE varTable{yy} (TableName TEXT, VarName TEXT, DataType TEXT)")
    con.executemany(f"INSERT INTO varTable{yy} VALUES (?,?,?)",
                    [(f"ADM{year}", v, t) for v, t in [("NAME", "A"), ("APPLCN", "N"), ("NETPR", "N"),
                                                       ("POLICY", "N"), ("CLASS", "N"), ("FTE", "N")]])
    con.execute(f"CREATE TABLE valueSets{yy} (TableName TEXT, VarName TEXT, Codevalue TEXT, ValueLabel TEXT)")
    con.executemany(f"INSERT INTO valueSets{yy} VALUES (?,?,?,?)",
                    [(f"ADM{year}", "POLICY", "1", "Required"), (f"ADM{year}", "POLICY", "-1 ", "Not reported"),
                     (f"ADM{year}", "POLICY", "-2", "Not applicable"), (f"ADM{year}", "CLASS", "-2", "Not classified")])
    con.commit()
    con.close()
    return {f"ADM{year}": ("ADM{YEAR}", "data"), f"GR{year}": ("GR{YEAR}", "data"),
            f"varTable{yy}": (f"VARTABLE{yy}", "codebook"), f"valueSets{yy}": (f"VALUESETS{yy}", "codebook")}


class BuildLogic(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.dir.name)
        self.out = sqlite3.connect(self.tmp / "out.sqlite", uri=True)
        self.fams = {}

    def tearDown(self):
        self.out.close()
        self.dir.cleanup()

    def load(self, year, **kw):
        src = self.tmp / f"src{year}.sqlite"
        if not src.exists():
            self.fams[year] = make_source(src, year, **kw)
        return build_data.load_release(self.out, src, f"R{year}", year, self.fams[year], rules=RULES)

    def column(self, col, table="ADM", year=2024):
        return [r[0] for r in self.out.execute(f"SELECT {col} FROM {table} WHERE year=? ORDER BY UNITID", (year,))]

    def test_local_names(self):
        cases = {"ADM{YEAR}": "ADM", "F{YYPAIR}_F1A": "F_F1A", "GR200_{YY}": "GR200", "C{YEAR}_A": "C_A",
                 "C{YEAR}DEP": "CDEP", "EF{YEAR}A_DIST": "EFA_DIST", "COST2_{YEAR}_NETPRICE": "COST2_NETPRICE",
                 "COST1_{YEAR}": "COST1", "IC{YEAR}MISSION": "ICMISSION", "VARTABLE24": "VARTABLE",
                 "DRVEF12{YEAR}": "DRVEF12"}
        for family, expected in cases.items():
            self.assertEqual(build_data.local_name(family), expected)

    def test_year_column_and_row_counts(self):
        report = self.load(2024)
        self.assertEqual({r[0] for r in report}, {"ADM", "GR", "VARTABLE", "VALUESETS"})
        for r in report:
            self.assertEqual(r[6], r[7], f"{r[1]}: source and loaded row counts differ")
        self.assertEqual(self.out.execute("SELECT DISTINCT year FROM GR").fetchall(), [(2024,)])
        self.assertEqual(self.out.execute("SELECT COUNT(*) FROM GR").fetchone()[0], 4)  # multi-row table kept whole

    def test_missing_stays_missing_and_zero_stays_zero(self):
        self.load(2024)
        self.assertEqual(self.column("APPLCN"), [100, None, 0])

    def test_text_is_trimmed_and_blank_becomes_missing(self):
        self.load(2024)
        self.assertEqual(self.column("NAME"), ["Alpha College", None, "Gamma"])
        self.assertEqual(self.out.execute("SELECT n_padded, n_blank FROM _columns WHERE column='NAME'").fetchone(), (1, 1))

    def test_approved_special_codes_become_missing(self):
        self.load(2024)
        self.assertEqual(self.column("POLICY"), [1, None, None])
        log = self.out.execute("SELECT code, decision, n_cells FROM _special_codes WHERE column='POLICY' ORDER BY code").fetchall()
        reasons = self.out.execute("SELECT unitid, reason FROM _missing_reasons WHERE column='POLICY' ORDER BY unitid").fetchall()
        self.assertEqual(reasons, [(2, "Not reported"), (3, "Not applicable")])
        self.assertEqual(log, [("-1", "missing", 1), ("-2", "missing", 1)])

    def test_special_code_marked_keep_is_left_alone_and_counted(self):
        self.load(2024)
        self.assertEqual(self.column("CLASS"), [5, -2, 3])
        self.assertEqual(self.out.execute("SELECT decision, n_cells FROM _special_codes WHERE column='CLASS'").fetchall(),
                         [("keep", 1)])

    def test_table_and_column_rule_covers_codes_the_codebook_does_not_list(self):
        self.load(2024)
        self.assertEqual(self.column("SYSNAME"), ["State System", None, None])
        self.assertEqual(self.out.execute("SELECT applies_by, n_cells FROM _special_codes WHERE column='SYSNAME'").fetchall(),
                         [("table and column", 2)])
        self.assertEqual(self.out.execute("SELECT COUNT(*) FROM _missing_reasons WHERE column='SYSNAME'").fetchone()[0], 2)

    def test_real_negative_numbers_are_untouched(self):
        """-2 in a column where the codebook lists no special code is a real value."""
        self.load(2024)
        self.assertEqual(self.column("NETPR"), [-500, 2000, -2])

    def test_numbers_stored_as_text_become_numbers(self):
        self.load(2024)
        self.assertEqual(self.column("FTE")[:2], [12.5, 7])
        self.assertEqual(self.column("typeof(FTE)")[:2], ["real", "integer"])
        self.assertEqual(self.out.execute("SELECT SUM(FTE) FROM ADM WHERE UNITID < 3").fetchone()[0], 19.5)

    def test_value_that_will_not_convert_is_reported_not_dropped(self):
        self.load(2024)
        self.assertEqual(self.column("FTE")[2], "n/a")  # still there
        self.assertEqual(self.out.execute("SELECT column, value, n_cells FROM _conversion_failures").fetchall(),
                         [("FTE", "n/a", 1)])
        self.assertEqual(self.out.execute("SELECT n_failed FROM _columns WHERE column='FTE'").fetchone()[0], 1)

    def test_second_year_stacks_and_new_columns_are_added(self):
        self.load(2024)
        self.load(2023, extra_column=True)
        self.assertEqual(self.out.execute("SELECT year, COUNT(*) FROM ADM GROUP BY year ORDER BY year").fetchall(),
                         [(2023, 3), (2024, 3)])
        # The column that exists only in 2023 is missing, not zero, for 2024.
        self.assertEqual(self.out.execute("SELECT DISTINCT NEWCOL FROM ADM WHERE year=2024").fetchall(), [(None,)])
        self.assertEqual(self.out.execute("SELECT COUNT(*) FROM _tables").fetchone()[0], 8)

    def test_rerunning_a_year_does_not_duplicate(self):
        self.load(2024)
        before = [self.out.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("ADM", "_tables", "_columns", "_special_codes", "_conversion_failures", "_missing_reasons")]
        self.load(2024)
        after = [self.out.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                 for t in ("ADM", "_tables", "_columns", "_special_codes", "_conversion_failures", "_missing_reasons")]
        self.assertEqual(before, after)

    def test_table_missing_from_index_is_an_error(self):
        src = self.tmp / "src2024.sqlite"
        fams = make_source(src, 2024)
        del fams["GR2024"]
        with self.assertRaises(ValueError):
            build_data.load_release(self.out, src, "R2024", 2024, fams, rules=RULES)

    def test_source_is_opened_read_only(self):
        src = self.tmp / "src2024.sqlite"
        fams = make_source(src, 2024)
        before = src.read_bytes()
        build_data.load_release(self.out, src, "R2024", 2024, fams, rules=RULES)
        self.assertEqual(src.read_bytes(), before)
        self.out.execute("ATTACH DATABASE ? AS src", (f"file:{src.as_posix()}?mode=ro",))
        with self.assertRaises(sqlite3.OperationalError):
            self.out.execute("DELETE FROM src.ADM2024")
        self.out.execute("DETACH DATABASE src")


@unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built; run python build/build_data.py")
class ReleaseSteps(unittest.TestCase):
    """Adding a release, and replacing a provisional release with its final version, on made-up releases."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        root = Path(self.dir.name)
        self.catalog = root / "catalog.sqlite"
        cat = sqlite3.connect(self.catalog)
        cat.execute("CREATE TABLE tables (release_id TEXT, table_name TEXT, family TEXT, kind TEXT)")
        self.releases = {}
        for release, year, drop_gr in [("IPEDS_2024-25_Final", 2024, False), ("IPEDS_2025-26_Provisional", 2025, False),
                                       ("IPEDS_2025-26_Final", 2025, True)]:
            folder = root / "annual" / release
            folder.mkdir(parents=True)
            fams = make_source(folder / "data.sqlite", year)
            if drop_gr:                                 # the final release has one table fewer and one row fewer
                src = sqlite3.connect(folder / "data.sqlite")
                src.execute(f"DROP TABLE GR{year}")
                src.execute(f"DELETE FROM ADM{year} WHERE UNITID = 3")
                src.commit()
                src.close()
                fams.pop(f"GR{year}")
            cat.executemany("INSERT INTO tables VALUES (?,?,?,?)",
                            [(release, t, f, "source_metadata" if k == "codebook" else "data") for t, (f, k) in fams.items()])
        cat.commit()
        cat.close()
        self.root = root
        self.out = sqlite3.connect(root / "local.sqlite", uri=True)

    def tearDown(self):
        self.out.close()
        self.dir.cleanup()

    def add(self, release):
        return build_data.add_release(self.out, release, "data.sqlite", self.root, self.catalog)

    def count(self, table, year):
        return self.out.execute(f'SELECT COUNT(*) FROM "{table}" WHERE year = ?', (year,)).fetchone()[0]

    def test_year_and_status_come_from_the_folder_name(self):
        self.assertEqual((build_data.year_of("IPEDS_2024-25_Provisional"), build_data.status_of("IPEDS_2024-25_Provisional")),
                         (2024, "provisional"))
        self.assertEqual(build_data.status_of("IPEDS_2015-16_Final"), "final")
        with self.assertRaises(ValueError):
            build_data.status_of("IPEDS_2015-16")

    def test_adding_a_new_year_keeps_the_others(self):
        self.add("IPEDS_2024-25_Final")
        before = self.count("ADM", 2024), self.count("GR", 2024)
        _, removed = self.add("IPEDS_2025-26_Provisional")
        self.assertEqual(removed, [])
        self.assertEqual((self.count("ADM", 2024), self.count("GR", 2024)), before)
        self.assertEqual(self.count("ADM", 2025), 3)
        self.assertEqual(self.out.execute("SELECT status FROM _releases WHERE year = 2025").fetchone()[0], "provisional")

    def test_replacing_a_provisional_release_leaves_no_rows_behind(self):
        self.add("IPEDS_2024-25_Final")
        self.add("IPEDS_2025-26_Provisional")
        self.assertEqual(self.count("GR", 2025), 4)
        _, removed = self.add("IPEDS_2025-26_Final")
        self.assertEqual(removed, ["IPEDS_2025-26_Provisional"])
        self.assertEqual(self.count("ADM", 2025), 2)                     # the final file's rows only
        self.assertEqual(self.count("GR", 2025), 0)                      # a table the final release lacks: nothing left
        self.assertEqual(self.count("GR", 2024), 4)                      # other years untouched
        self.assertEqual(self.count("_missing_reasons", 2025),
                         self.out.execute("SELECT COUNT(*) FROM _missing_reasons WHERE year = 2025").fetchone()[0])
        for log in ("_tables", "_columns", "_special_codes"):
            n = self.out.execute(f"SELECT COUNT(*) FROM {log} WHERE release = 'IPEDS_2025-26_Provisional'").fetchone()[0]
            self.assertEqual(n, 0, log)
        self.assertEqual(self.out.execute("SELECT release, status FROM _releases WHERE year = 2025").fetchone(),
                         ("IPEDS_2025-26_Final", "final"))

    def test_replacing_the_same_release_twice_gives_the_same_rows(self):
        self.add("IPEDS_2024-25_Final")
        first = self.count("ADM", 2024), self.count("GR", 2024)
        self.add("IPEDS_2024-25_Final")
        self.assertEqual((self.count("ADM", 2024), self.count("GR", 2024)), first)

    def test_a_release_not_on_disk_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            build_data.add_release(self.out, "IPEDS_2030-31_Final", "data.sqlite", self.root, self.catalog)


class RealDatabase(unittest.TestCase):
    RELEASE, FILENAME, YEAR = config.RELEASES[-1]

    @classmethod
    def setUpClass(cls):
        cls.source_dir = config.SOURCE_DATA / "annual" / cls.RELEASE
        cls.db = latest_only(sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True))
        cls.db.execute("ATTACH DATABASE ? AS src", (f"file:{(cls.source_dir / cls.FILENAME).as_posix()}?mode=ro",))
        cls.registry = cls.db.execute(
            "SELECT local_table, source_table, kind, source_rows, loaded_rows, n_columns FROM _tables WHERE release=?",
            (cls.RELEASE,)).fetchall()
        cls.columns = {}   # source table -> [(column, source_type, text_to_number)]
        for t, c, st, conv in cls.db.execute(
                "SELECT source_table, column, source_type, text_to_number FROM _columns WHERE release=? ORDER BY rowid",
                (cls.RELEASE,)):
            cls.columns.setdefault(t, []).append((c, st, conv))
        cls.dropped = {}   # (source table, column) -> [codes turned into missing]
        for t, c, code in cls.db.execute(
                "SELECT source_table, column, code FROM _special_codes WHERE release=? AND decision='missing'",
                (cls.RELEASE,)):
            cls.dropped.setdefault((t, c), []).append(code)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def source_expr(self, table, col, stype):
        """The value the source holds once cleaned, written independently of the build script."""
        expr = f"NULLIF(TRIM(\"{col}\"), '')" if stype == "TEXT" else f'"{col}"'
        codes = self.dropped.get((table, col))
        if codes:
            listed = ", ".join(f"'{c}'" if stype == "TEXT" else c for c in codes)
            expr = f"CASE WHEN {expr} IN ({listed}) THEN NULL ELSE {expr} END"
        return expr

    def test_every_source_table_is_loaded(self):
        source = {r[0] for r in self.db.execute("SELECT name FROM src.sqlite_master WHERE type='table'")}
        self.assertEqual(source, {r[1] for r in self.registry})
        self.assertEqual(len(self.registry), 56)
        self.assertEqual(sum(1 for r in self.registry if r[2] == "codebook"), 4)

    def test_row_counts_match_the_source_recounted_now(self):
        for local, source, _, _, _, _ in self.registry:
            src_n = self.db.execute(f'SELECT COUNT(*) FROM src."{source}"').fetchone()[0]
            loc_n = self.db.execute(f'SELECT COUNT(*) FROM "{local}" WHERE year=?', (self.YEAR,)).fetchone()[0]
            self.assertEqual(src_n, loc_n, source)

    def test_row_counts_match_the_original_access_file(self):
        """Version 1 recorded the row count of each table in the original NCES Access file."""
        with open(self.source_dir / "table_checks.csv", newline="") as f:
            access = {r["table"]: int(r["source_rows"]) for r in csv.DictReader(f)}
        loaded = {r[1]: r[4] for r in self.registry}
        self.assertEqual(access, loaded)

    def test_every_column_matches_the_cleaned_source(self):
        """For every column of every table: same number of non-missing values as the cleaned source,
        and for every numeric column (including those converted from text) the same total."""
        for local, source, _, _, _, n_columns in self.registry:
            cols = self.columns[source]
            self.assertEqual(len(cols), n_columns)
            stacked = [r[1] for r in self.db.execute(f'PRAGMA main.table_info("{local}")')]   # every year's columns
            self.assertEqual(stacked[0], "year")
            self.assertLessEqual({c.upper() for c, _, _ in cols}, {c.upper() for c in stacked}, source)   # names ignore case
            for i in range(0, len(cols), 150):
                chunk = cols[i:i + 150]
                numeric = [(c, st) for c, st, conv in chunk if st in ("INTEGER", "REAL") or conv]
                src_sql = [f"COUNT({self.source_expr(source, c, st)})" for c, st, _ in chunk]
                src_sql += [f"TOTAL({self.source_expr(source, c, st)})" for c, st in numeric]
                loc_sql = [f'COUNT("{c}")' for c, _, _ in chunk] + [f'TOTAL("{c}")' for c, _ in numeric]
                a = self.db.execute(f'SELECT {", ".join(src_sql)} FROM src."{source}"').fetchone()
                b = self.db.execute(f'SELECT {", ".join(loc_sql)} FROM "{local}" WHERE year=?', (self.YEAR,)).fetchone()
                names = [f"count {c}" for c, _, _ in chunk] + [f"total {c}" for c, _ in numeric]
                for name, x, y in zip(names, a, b):
                    self.assertEqual(x, y, f"{source} {name}")

    def test_nothing_is_lost_without_a_recorded_reason(self):
        """Source values = loaded values + blanks + special codes, for every column. Nothing else may vanish."""
        bad = self.db.execute(
            "SELECT source_table, column FROM _columns WHERE source_nonmissing <> loaded_nonmissing + n_blank + n_special"
        ).fetchall()
        self.assertEqual(bad, [])

    def test_converted_columns_hold_only_numbers(self):
        """The 42 codebook-numeric columns stored as text in the source: every value is now a number,
        with the same non-missing count and total as the source (where no special code was removed)."""
        converted = self.db.execute(
            "SELECT local_table, source_table, column, n_special FROM _columns WHERE text_to_number=1 AND release=?",
            (self.RELEASE,)).fetchall()
        self.assertEqual(len(converted), 42)
        for local, source, col, n_special in converted:
            kinds = {r[0] for r in self.db.execute(f'SELECT DISTINCT typeof("{col}") FROM "{local}"')}
            self.assertLessEqual(kinds, {"integer", "real", "null"}, f"{local}.{col}")
            if not n_special:
                a = self.db.execute(f"SELECT COUNT(NULLIF(TRIM(\"{col}\"), '')), TOTAL(\"{col}\") FROM src.\"{source}\"").fetchone()
                b = self.db.execute(f'SELECT COUNT("{col}"), TOTAL("{col}") FROM "{local}"').fetchone()
                self.assertEqual(a, b, f"{local}.{col}")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM _conversion_failures").fetchone()[0], 0)

    def test_every_codebook_numeric_column_is_stored_as_a_number(self):
        left = self.db.execute("SELECT local_table, column FROM _columns WHERE codebook_type='N' "
                               "AND stored_type NOT IN ('INTEGER','REAL','NUMERIC')").fetchall()
        self.assertEqual(left, [])

    def test_no_padded_or_blank_text_remains(self):
        for local, source, _, _, _, _ in self.registry:
            text = [c for c, st, conv in self.columns[source] if st == "TEXT" and not conv]
            if text:
                sql = " + ".join(f"SUM(\"{c}\" <> TRIM(\"{c}\") OR \"{c}\" = '')" for c in text)
                counts = self.db.execute(f'SELECT {sql.replace(" + ", ", ")} FROM "{local}"').fetchone()
                self.assertFalse(any(counts), f"{local}: {dict(zip(text, counts))}")

    def test_approved_special_codes_are_gone_and_real_negatives_remain(self):
        for (source, col), codes in self.dropped.items():
            local = next(r[0] for r in self.registry if r[1] == source)
            listed = ", ".join(f"'{c}'" for c in codes)
            n = self.db.execute(f'SELECT COUNT(*) FROM "{local}" WHERE CAST("{col}" AS TEXT) IN ({listed})').fetchone()[0]
            self.assertEqual(n, 0, f"{local}.{col}")
        # Negative net prices are real values, not codes: the lowest is unchanged from the source.
        a = self.db.execute("SELECT MIN(NPIST2), SUM(NPIST2 < 0) FROM src.COST2_2024_NetPrice").fetchone()
        b = self.db.execute("SELECT MIN(NPIST2), SUM(NPIST2 < 0) FROM COST2_NETPRICE").fetchone()
        self.assertEqual(a, b)
        self.assertLess(b[0], 0)

    def test_a_reason_is_kept_for_every_special_code_cell(self):
        """Display-only side table: one row per cell that a special code made missing."""
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM _missing_reasons").fetchone()[0],
                         self.db.execute("SELECT SUM(n_special) FROM _columns WHERE release=?", (self.RELEASE,)).fetchone()[0])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM _missing_reasons WHERE reason IS NULL OR reason = ''").fetchone()[0], 0)
        # A school that is not in a system: the name is missing and the reason says why.
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM HD WHERE F1SYSNAM IN ('-1', '-2')").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM HD WHERE F1SYSNAM IS NULL").fetchone()[0],
                         self.db.execute("SELECT COUNT(*) FROM _missing_reasons WHERE local_table='HD' AND column='F1SYSNAM'").fetchone()[0])

    def test_every_release_is_held_once_with_its_status_and_every_row(self):
        held = self.db.execute("SELECT year, release, status FROM _releases ORDER BY year").fetchall()
        self.assertEqual([(y, r) for y, r, _ in held], [(y, r) for r, _, y in config.RELEASES])
        for year, release, status in held:
            self.assertEqual(status, build_data.status_of(release))
            bad = self.db.execute("SELECT COUNT(*) FROM _tables WHERE year=? AND source_rows <> loaded_rows", (year,)).fetchone()[0]
            self.assertEqual(bad, 0, release)

    def test_known_values_from_the_plan(self):
        """Three figures from the test table in V2_PLAN.md, straight from the stacked tables."""
        q = lambda sql: self.db.execute(sql).fetchone()[0]
        self.assertEqual(q("SELECT COUNT(*) FROM HD WHERE year=2024"), 6072)
        self.assertEqual(q("SELECT COUNT(*) FROM HD WHERE year=2024 AND FIPS BETWEEN 1 AND 56 "
                           "AND PSET4FLG IN (1,3) AND SECTOR<>0"), 5626)
        self.assertEqual(q("SELECT COUNT(DISTINCT UNITID) FROM CUSTOMCGIDS WHERE year=2024"), 2845)


if __name__ == "__main__":
    unittest.main()
