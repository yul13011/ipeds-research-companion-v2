"""Tests for Stage 2 (build/build_dictionary.py and the dictionary folder).

Two groups:
  - LoaderLogic: a tiny made-up database and dictionary folder in a temporary directory. Always runs.
  - RealDictionary: the real dictionary folder against the real local database. Skipped if not built.

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
from build import build_dictionary as bd


def headers():
    """Column names of each dictionary table, read from the real folder so the fixture cannot drift."""
    out = {}
    for name in bd.TABLES:
        with open(config.DICTIONARY / f"{name}.csv", newline="", encoding="utf-8") as f:
            out[name] = next(csv.reader(f))
    return out


SCHOOLS = [  # UNITID, name, city, state, SECTOR, PSET4FLG, CONFNO1, CONFNO2
    (1, "Alpha University", "Austin", "TX", 1, 1, 107, None),
    (2, "Beta College", "Boston", "MA", 2, 1, None, 107),
    (3, "Gamma Community College", "Austin", "TX", 4, 1, None, None),
    (4, "Delta Institute", "San Juan", "PR", 1, 1, None, None),
    (5, "Epsilon System Office", "Boston", "MA", 0, 1, None, None)]

GOOD = {
    "measures": [dict(table="DRVADM", variable="DVADM01", title="Percent admitted", in_first_version="yes"),
                 dict(table="ENR", variable="CNT", title="Students", format="Cont", data_type="N"),
                 dict(table="ENR", variable="MEN", title="Men", format="Cont", data_type="N", breakdown_set="By gender", set_total="CNT"),
                 dict(table="ENR", variable="WOMEN", title="Women", format="Cont", data_type="N", breakdown_set="By gender", set_total="CNT"),
                 dict(table="ENR", variable="AID", title="Aided", format="Cont", data_type="N", breakdown_set="By aid", set_total="CNT"),
                 dict(table="ENR", variable="NOAID", title="Not aided", format="Cont", data_type="N", breakdown_set="By aid", set_total="CNT")],
    "terms": [dict(term="admission rate", words="admission rate", kind="measure", reading="Percent admitted",
                   measure="DRVADM.DVADM01", is_default="yes", always_ask="no")],
    "school_groups": [
        dict(group="Public four-year", kind="column", table="HD", column="SECTOR", codes="1"),
        dict(group="Any four-year or two-year public", kind="column", table="HD", column="SECTOR", codes="1, 4"),
        dict(group="Big Ten", kind="column", table="IC", column="CONFNO1, CONFNO2", codes="107"),
        dict(group="State", kind="any value", table="HD", column="STABBR", codes="any", statement="State"),
        dict(group="Universe", kind="universe", table="HD", column="STABBR", codes="TX, MA"),
        dict(group="Universe", kind="universe", table="HD", column="SECTOR", codes="1, 2, 4"),
        dict(group="Pair", kind="member list"),
        dict(group="Has enrollment rows", kind="has rows", table="ENR"),
        dict(group="Women's colleges", kind="none", status="decline", statement="IPEDS has no flag for this group.")],
    "group_members": [dict(group="Pair", unitid="1"), dict(group="Pair", unitid="2")],
    "school_nicknames": [dict(nickname="alpha", kind="direct", unitid="1")],
    "rates": [dict(rate="Admission rate", rate_measure="DRVADM.DVADM01", numerator="DRVADM.ADMSSN", denominator="DRVADM.APPLCN")],
    "category_codes": [
        dict(table="ENR", column="LEVEL", code="1", label="All students", role="total"),
        dict(table="ENR", column="LEVEL", code="2", label="Undergraduate", role="part", breakdown_set="By level", set_total="1", set_fixed="STUDY = 1"),
        dict(table="ENR", column="LEVEL", code="3", label="Graduate", role="part", breakdown_set="By level", set_total="1", set_fixed="STUDY = 1"),
        dict(table="ENR", column="LEVEL", code="4", label="Full-time", role="part", breakdown_set="By attendance", set_total="1", set_fixed="STUDY = 1"),
        dict(table="ENR", column="LEVEL", code="5", label="Part-time", role="part", breakdown_set="By attendance", set_total="1", set_fixed="STUDY = 1"),
        dict(table="ENR", column="LEVEL", code="6", label="Online", role="part", breakdown_set="By mode", set_total="sum of parts"),
        dict(table="ENR", column="LEVEL", code="7", label="In person", role="part", breakdown_set="By mode", set_total="sum of parts")],
    "outside_ipeds": [], "special_codes": [],
    "year_meaning": [dict(table=t, year="2024", kind="fall", period="Fall 2024") for t in ("HD", "IC", "DRVADM", "ENR")],
}


def make_database(path):
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE _tables (local_table TEXT, source_table TEXT, kind TEXT, year INTEGER);
        INSERT INTO _tables VALUES ('HD','HD2024','data',2024), ('IC','IC2024','data',2024), ('DRVADM','DRVADM2024','data',2024),
                                   ('ENR','ENR2024','data',2024);
        -- ENR: one row per school, level and study group. School 1 adds up everywhere. At school 2 the attendance
        -- rows do not add up (4 + 5 is not 10) and the aid columns do not add up. The last row has no detail at all.
        CREATE TABLE ENR (year INTEGER, UNITID INTEGER, LEVEL INTEGER, STUDY INTEGER, CNT INTEGER, MEN INTEGER, WOMEN INTEGER,
                          AID INTEGER, NOAID INTEGER);
        INSERT INTO ENR VALUES (2024,1,1,1,100,40,60,30,70), (2024,1,2,1,80,30,50,20,60), (2024,1,3,1,20,10,10,10,10),
                               (2024,1,4,1,70,30,40,30,40), (2024,1,5,1,30,10,20,0,30), (2024,1,2,2,999,499,500,1,998),
                               (2024,2,1,1,10,4,6,5,6),     (2024,2,2,1,10,4,6,5,6),    (2024,2,4,1,4,2,2,2,2),
                               (2024,2,5,1,5,2,3,3,2),      (2024,2,6,1,7,NULL,NULL,NULL,NULL);
        CREATE TABLE HD (year INTEGER, UNITID INTEGER, INSTNM TEXT, IALIAS TEXT, CITY TEXT, STABBR TEXT, SECTOR INTEGER, PSET4FLG INTEGER);
        CREATE TABLE IC (year INTEGER, UNITID INTEGER, CONFNO1 INTEGER, CONFNO2 INTEGER);
        CREATE TABLE DRVADM (year INTEGER, UNITID INTEGER, DVADM01 INTEGER, ADMSSN INTEGER, APPLCN INTEGER);
        CREATE TABLE VALUESETS (year INTEGER, TableName TEXT, VarName TEXT, Codevalue TEXT, ValueLabel TEXT);
        INSERT INTO VALUESETS VALUES (2024,'HD2024','STABBR','TX','Texas'), (2024,'HD2024','STABBR','MA','Massachusetts'),
                                     (2024,'HD2024','SECTOR','1','Public, 4-year or above');""")
    for u, name, city, st, sector, t4, c1, c2 in SCHOOLS:
        con.execute("INSERT INTO HD VALUES (2024,?,?,NULL,?,?,?,?)", (u, name, city, st, sector, t4))
        con.execute("INSERT INTO IC VALUES (2024,?,?,?)", (u, c1, c2))
    con.commit()
    con.close()


class LoaderLogic(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.dir.name)
        self.db_path = self.tmp / "db.sqlite"
        make_database(self.db_path)
        self.heads = headers()

    def tearDown(self):
        self.dir.cleanup()

    def build(self, **changes):
        """Write the made-up dictionary (with any changed tables) and run the loader."""
        tables = {**GOOD, **changes}
        for name in bd.TABLES:
            with open(self.tmp / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=self.heads[name], restval="")
                w.writeheader()
                w.writerows(tables[name])
        bd.build(self.db_path, self.tmp)
        return sqlite3.connect(self.db_path)

    def members(self, db, group):
        return [u for (u,) in db.execute("SELECT unitid FROM group_membership WHERE group_name=? ORDER BY unitid", (group,))]

    def test_tables_are_loaded_unchanged(self):
        db = self.build()
        self.assertEqual(db.execute('SELECT "group", unitid FROM dict_group_members').fetchall(), [("Pair", "1"), ("Pair", "2")])
        self.assertIsNone(db.execute("SELECT caveat FROM dict_school_groups LIMIT 1").fetchone()[0])  # empty cell is missing
        db.close()

    def test_group_by_one_code_and_by_several_codes(self):
        db = self.build()
        self.assertEqual(self.members(db, "Public four-year"), [1, 4])
        self.assertEqual(self.members(db, "Any four-year or two-year public"), [1, 3, 4])
        db.close()

    def test_group_matching_any_of_several_columns(self):
        db = self.build()
        self.assertEqual(self.members(db, "Big Ten"), [1, 2])   # school 1 by football, school 2 by basketball
        db.close()

    def test_group_with_several_rows_must_meet_all_of_them(self):
        db = self.build()
        self.assertEqual(self.members(db, "Universe"), [1, 2, 3])   # not Puerto Rico, not the system office
        self.assertEqual(db.execute("SELECT n_schools FROM group_list WHERE group_name='Universe'").fetchone()[0], 3)
        db.close()

    def test_each_value_becomes_its_own_group_with_the_codebook_label(self):
        db = self.build()
        self.assertEqual(self.members(db, "State: Texas"), [1, 3])
        self.assertEqual(db.execute("SELECT parent, words FROM group_list WHERE group_name='State: Texas'").fetchone(), ("State", "TX"))
        self.assertEqual(self.members(db, "State: PR"), [4])        # no codebook label: the value itself
        db.close()

    def test_member_list_and_declined_group(self):
        db = self.build()
        self.assertEqual(self.members(db, "Pair"), [1, 2])
        self.assertEqual(db.execute("SELECT status, n_schools FROM group_list WHERE group_name=\"Women's colleges\"").fetchone(),
                         ("decline", 0))
        db.close()

    def test_two_groups_combine_by_intersecting(self):
        """'Public four-year colleges in Texas' is the schools in both groups."""
        db = self.build()
        both = db.execute("SELECT a.unitid FROM group_membership a JOIN group_membership b USING (unitid, year) "
                          "WHERE a.group_name='Public four-year' AND b.group_name='State: Texas'").fetchall()
        self.assertEqual(both, [(1,)])
        db.close()

    def test_directory_has_identity_and_every_grouping_column(self):
        db = self.build()
        cols = [r[1] for r in db.execute("PRAGMA table_info(directory)")]
        self.assertEqual(cols, ["year", "UNITID", "INSTNM", "IALIAS", "CITY", "STABBR", "SECTOR", "CONFNO1", "CONFNO2"])
        self.assertEqual(db.execute("SELECT COUNT(*) FROM directory").fetchone()[0], 5)   # a 'has rows' group adds no join
        self.assertEqual(db.execute("SELECT COUNT(*) FROM directory").fetchone()[0], 5)
        db.close()

    def test_group_of_schools_that_have_rows_in_a_table(self):
        db = self.build()
        self.assertEqual(self.members(db, "Has enrollment rows"), [1, 2])
        db.close()

    def sets(self, db, name):
        return db.execute("SELECT measure, n_tested, n_ok, status FROM breakdown_sets WHERE set_name=? ORDER BY measure", (name,)).fetchall()

    def test_row_set_that_adds_up_is_loaded_using_only_its_fixed_rows(self):
        db = self.build()
        # School 1's STUDY = 2 row (999) is outside the fixed rows and must not be counted.
        self.assertEqual(self.sets(db, "By level")[1], ("CNT", 2, 2, "loaded"))
        self.assertEqual(db.execute("SELECT part, label FROM breakdown_parts WHERE set_name='By level' ORDER BY part").fetchall(),
                         [("2", "Undergraduate"), ("3", "Graduate")])
        db.close()

    def test_row_set_that_does_not_add_up_is_not_loaded(self):
        db = self.build()
        self.assertEqual(self.sets(db, "By attendance")[1], ("CNT", 2, 1, "failed"))   # school 2: 4 + 5 is not 10
        # The result is kept per count column: MEN happens to add up at both schools, so only MEN may use this set.
        self.assertEqual([r for r in self.sets(db, "By attendance") if r[0] == "MEN"], [("MEN", 2, 2, "loaded")])
        db.close()

    def test_additive_set_has_nothing_to_test_and_is_loaded(self):
        db = self.build()
        self.assertEqual({r[3] for r in self.sets(db, "By mode")}, {"additive"})
        self.assertEqual(db.execute("SELECT COUNT(*) FROM breakdown_parts WHERE set_name='By mode'").fetchone()[0], 2)
        db.close()

    def test_column_set_is_tested_on_every_row_with_detail(self):
        db = self.build()
        row = db.execute("SELECT n_tested, n_ok, n_no_detail, status FROM breakdown_sets WHERE set_name='By gender'").fetchone()
        self.assertEqual(row, (10, 10, 1, "loaded"))            # the row with no men or women reported is not a failure
        row = db.execute("SELECT n_tested, n_ok, status FROM breakdown_sets WHERE set_name='By aid'").fetchone()
        self.assertEqual(row, (10, 8, "failed"))                # both of school 2's all-students rows: 5 + 6 is not 10
        self.assertEqual(db.execute("SELECT COUNT(*) FROM breakdown_parts WHERE set_name='By aid'").fetchone()[0], 0)
        db.close()

    def test_set_whose_rows_disagree_about_the_total_stops_the_build(self):
        codes = [dict(r) for r in GOOD["category_codes"]]
        codes[1]["set_total"] = "9"
        self.assertProblem("do not all name the same total", category_codes=codes)

    def assertProblem(self, text, **changes):
        with self.assertRaises(ValueError) as caught:
            self.build(**changes)
        self.assertIn(text, str(caught.exception))

    def test_unknown_measure_stops_the_build(self):
        self.assertProblem("NOPE is not a column", measures=GOOD["measures"] + [dict(table="DRVADM", variable="NOPE")])

    def test_term_pointing_to_a_measure_not_in_the_list_stops_the_build(self):
        self.assertProblem("not in measures.csv", terms=[dict(term="x", reading="y", measure="DRVADM.ADMSSN", is_default="yes", always_ask="no")])

    def test_term_with_no_default_and_no_question_stops_the_build(self):
        self.assertProblem("neither asks the user nor has a default",
                           terms=[dict(term="x", reading="y", measure="DRVADM.DVADM01", is_default="no", always_ask="no")])

    def test_group_code_that_never_occurs_stops_the_build(self):
        self.assertProblem("code 9 never occurs", school_groups=[dict(group="Bad", kind="column", table="HD", column="SECTOR", codes="9")])

    def test_unknown_school_in_a_member_list_stops_the_build(self):
        self.assertProblem("school 99 in 'Pair' is not in the directory", group_members=GOOD["group_members"] + [dict(group="Pair", unitid="99")])

    def test_data_table_without_a_year_meaning_stops_the_build(self):
        self.assertProblem("no row for data table IC", year_meaning=[r for r in GOOD["year_meaning"] if r["table"] != "IC"])


@unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built; run python build/build_data.py")
class RealDictionary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
        if not cls.db.execute("SELECT 1 FROM sqlite_master WHERE name='group_list'").fetchone():
            raise unittest.SkipTest("dictionary not loaded; run python build/build_dictionary.py")

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def n(self, group):
        return self.db.execute("SELECT n_schools FROM group_list WHERE group_name=?", (group,)).fetchone()[0]

    def test_folder_holds_exactly_the_agreed_files(self):
        found = sorted(p.name for p in config.DICTIONARY.iterdir())
        self.assertEqual(found, sorted([f"{t}.csv" for t in bd.TABLES] + ["DECISIONS.md", "README.md"]))

    def test_database_copy_matches_the_csv_files(self):
        for name in bd.TABLES:
            with open(config.DICTIONARY / f"{name}.csv", newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))[1:]
            self.assertEqual(self.db.execute(f"SELECT COUNT(*) FROM dict_{name}").fetchone()[0], len(rows), name)

    def test_dictionary_fits_the_data(self):
        db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
        self.assertEqual(bd.check(db), [])
        db.close()

    def test_directory_covers_every_school(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*), COUNT(DISTINCT UNITID) FROM directory").fetchone(), (6072, 6072))
        cols = {r[1] for r in self.db.execute("PRAGMA table_info(directory)")}
        self.assertLessEqual({"INSTNM", "STABBR", "SECTOR", "ICLEVEL", "CONTROL", "OBEREG", "LOCALE", "INSTSIZE", "HBCU", "TRIBAL",
                              "LANDGRNT", "C21BASIC", "CARNEGIERSCH", "F1SYSNAM", "RELAFFIL", "OPENADMP", "CONFNO1", "CONFNO4"}, cols)

    def test_national_universe_matches_nces(self):
        self.assertEqual(self.n("National universe"), 5626)

    def test_census_regions_follow_the_owner_state_lists(self):
        regions = ["Northeast", "Midwest", "South", "West"]
        states = {}
        for r in regions:
            got = {s for (s,) in self.db.execute("SELECT DISTINCT d.STABBR FROM group_membership m JOIN directory d "
                                                 "ON d.UNITID = m.unitid WHERE m.group_name=?", (r,))}
            states[r] = got
        self.assertEqual(states["Northeast"], set("CT ME MA NH RI VT NJ NY PA".split()))
        self.assertEqual(len(states["South"]), 17)
        self.assertEqual(sum(len(s) for s in states.values()), 51)             # 50 states and DC, each in one region
        self.assertEqual(len(set().union(*states.values())), 51)
        self.assertNotEqual(self.n("South"), self.n("Southeast"))              # the BEA region is a separate group

    def test_size_words_use_the_owner_cut_offs(self):
        self.assertEqual(self.n("Small"), self.db.execute("SELECT COUNT(*) FROM directory WHERE INSTSIZE IN (1, 2)").fetchone()[0])
        self.assertEqual(self.n("Large"), self.db.execute("SELECT COUNT(*) FROM directory WHERE INSTSIZE IN (4, 5)").fetchone()[0])

    def test_named_lists(self):
        self.assertEqual([self.n(g) for g in ("Ivy League", "Ivy Plus", "Seven Sisters", "Flagship universities")], [8, 12, 6, 53])

    def test_conference_matches_any_of_the_four_columns(self):
        football_only = self.db.execute("SELECT COUNT(*) FROM directory WHERE CONFNO1 = 104").fetchone()[0]
        self.assertGreater(self.n("Athletic conference: Big East Conference"), football_only)

    def test_all_religious_affiliations_are_loaded(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM group_list WHERE parent='Religious affiliation'").fetchone()[0], 63)

    def test_declined_groups_have_no_members_and_say_why(self):
        rows = self.db.execute("SELECT group_name, n_schools, statement FROM group_list WHERE status='decline'").fetchall()
        self.assertEqual(len(rows), 4)
        for name, n, statement in rows:
            self.assertEqual((n, statement), (0, "IPEDS has no flag for this group."), name)

    def test_groups_combine(self):
        """'Public two-year colleges in the Southeast' is the schools in both groups."""
        n = self.db.execute("SELECT COUNT(*) FROM group_membership a JOIN group_membership b USING (unitid, year) "
                            "WHERE a.group_name='Public, 2-year' AND b.group_name='Southeast'").fetchone()[0]
        self.assertEqual(n, self.db.execute("SELECT COUNT(*) FROM directory WHERE SECTOR=4 AND OBEREG=5").fetchone()[0])
        self.assertGreater(n, 0)

    def test_rates_from_counts_match_nces(self):
        """Every rate with an NCES figure: sum the counts over the national universe, then divide."""
        universe = "(SELECT unitid FROM group_membership WHERE group_name='National universe')"
        rows = self.db.execute("SELECT rate, numerator, denominator, category_column, numerator_code, denominator_code, "
                               "nces_figure FROM dict_rates WHERE nces_figure IS NOT NULL").fetchall()
        self.assertEqual(len(rows), 11)
        for rate, num, den, cat, n_code, d_code, nces in rows:
            (nt, nc), (dt, dc) = num.split("."), den.split(".")
            wn = f' AND "{cat}" = {n_code}' if cat else ""
            wd = f' AND "{cat}" = {d_code}' if cat else ""
            a, b = self.db.execute(
                f'SELECT SUM(n.v), SUM(d.v) FROM (SELECT UNITID, "{nc}" v FROM "{nt}" WHERE UNITID IN {universe}{wn}) n '
                f'JOIN (SELECT UNITID, "{dc}" v FROM "{dt}" WHERE UNITID IN {universe}{wd}) d USING (UNITID) '
                "WHERE n.v IS NOT NULL AND d.v IS NOT NULL").fetchone()
            decimals = len(nces.partition(".")[2])
            self.assertEqual(round(a / b, decimals), float(nces), rate)

    def test_breakdown_sets_stored_as_rows_all_add_up(self):
        """Each draft set is loaded for its table's main count column, at every school tested."""
        main = {"Fall enrollment by level": "EFTOTLT", "Fall enrollment by attendance status": "EFTOTLT",
                "Fall enrollment by age": "EFAGE09", "First-time students by state of residence": "EFRES01",
                "Awards by level": "CTOTALT", "Degrees by field of study": "CTOTALT",
                "Outcome measures by Pell status": "OMACHRT", "Full-time instructional staff by rank": "SAINSTT",
                "Staff by occupation": "EAPTOT"}
        for name, measure in main.items():
            tested, ok, status = self.db.execute("SELECT n_tested, n_ok, status FROM breakdown_sets WHERE set_name=? AND measure=?",
                                                 (name, measure)).fetchone()
            self.assertEqual((status, tested), ("loaded", ok), name)
            self.assertGreater(tested, 2000, name)

    def test_a_rate_column_is_not_offered_as_a_breakdown_of_counts(self):
        """Percentages do not add up, so the set is not loaded for them."""
        status = self.db.execute("SELECT status FROM breakdown_sets WHERE set_name='Outcome measures by Pell status' "
                                 "AND measure='OMAWDP8'").fetchone()[0]
        self.assertEqual(status, "failed")

    def test_breakdown_sets_stored_as_columns(self):
        race = dict(self.db.execute("SELECT \"table\", status FROM breakdown_sets WHERE set_name='By race and ethnicity'"))
        self.assertEqual(set(race.values()), {"loaded"})
        self.assertLessEqual({"EFA", "C_A", "GR", "EFFY", "S_IS"}, set(race))
        gender = dict(self.db.execute("SELECT \"table\", status FROM breakdown_sets WHERE set_name='By gender'"))
        self.assertEqual(set(gender.values()), {"loaded"})
        self.assertEqual(self.db.execute("SELECT status, n_parts FROM breakdown_sets WHERE set_name='Degrees by level'").fetchone(),
                         ("additive", 6))
        # Yale's undergraduates by race add up to the undergraduate total in the plan's test table.
        parts = [v for (v,) in self.db.execute("SELECT part FROM breakdown_parts WHERE set_name='By race and ethnicity' AND \"table\"='EFA'")]
        total = self.db.execute(f"SELECT {' + '.join(parts)} FROM EFA WHERE UNITID=130794 AND EFALEVEL=2").fetchone()[0]
        self.assertEqual((len(parts), total), (9, 6814))

    def test_change_order_of_2026_11_15(self):
        q = lambda sql: self.db.execute(sql).fetchall()
        self.assertEqual(q("SELECT DISTINCT status, always_ask, statement FROM dict_terms WHERE term='faculty'"),
                         [("in use", "yes", "Counts include medical school staff.")])
        self.assertEqual(q("SELECT EAPTOT, EAPFT, EAPPT FROM EAP WHERE UNITID=130794 AND EAPCAT IN (21000, 10010) ORDER BY EAPCAT"),
                         [(5735, 4688, 1047), (3800, 2995, 805)])
        self.assertEqual(q("SELECT COUNT(*) FROM dict_terms WHERE term='degrees'"), [(6,)])
        self.assertEqual(q("SELECT is_default, default_for FROM dict_terms WHERE term='peers' AND condition='comparison group'"),
                         [("yes", "Has an IPEDS comparison group")])
        self.assertEqual(self.n("Has an IPEDS comparison group"),
                         q("SELECT COUNT(DISTINCT UNITID) FROM CUSTOMCGIDS WHERE UNITID IN (SELECT UNITID FROM HD)")[0][0])
        self.assertEqual(q("SELECT COUNT(*) FROM dict_terms WHERE term='graduation rate' AND always_ask='mixed levels'"), [(3,)])
        words = dict(q("SELECT codes, words FROM dict_school_groups WHERE \"column\"='SECTOR'"))
        self.assertIn("public universities", words["1"])
        self.assertIn("private universities", words["2"])
        self.assertIn("private colleges", q("SELECT words FROM dict_school_groups WHERE \"column\"='CONTROL' AND codes='2'")[0][0])

    def test_out_of_state_tuition_sits_beside_the_default_reading(self):
        """Same schools report both, and out-of-state is never below the default (in-district) figure."""
        a = self.db.execute("SELECT SUM(c.chg3ay3 IS NOT NULL AND t.TUFEYR3 IS NULL), SUM(c.chg3ay3 IS NULL AND t.TUFEYR3 IS NOT NULL), "
                            "SUM(c.chg3ay3 < t.TUFEYR3), SUM(c.chg3ay3 IS NOT NULL) FROM COST1 c LEFT JOIN DRVCOST t USING (UNITID)").fetchone()
        self.assertEqual(a[:3], (0, 0, 0))
        self.assertGreater(a[3], 3000)

    def test_every_table_states_its_period(self):
        blank = self.db.execute("SELECT \"table\" FROM dict_year_meaning WHERE period IS NULL OR kind IS NULL OR kind='needs review'").fetchall()
        self.assertEqual(blank, [])

    def test_missing_reasons_are_never_referenced_by_the_dictionary(self):
        """The display-only side table must not be named as a measure, count or group column."""
        for table, col in [("measures", '"table"'), ("rates", "numerator"), ("rates", "denominator"), ("school_groups", '"table"')]:
            n = self.db.execute(f"SELECT COUNT(*) FROM dict_{table} WHERE {col} LIKE '%missing_reasons%'").fetchone()[0]
            self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main()
