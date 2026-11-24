"""Tests for Stage 2 (build/build_dictionary.py and the dictionary folder).

Two groups:
  - LoaderLogic: a tiny made-up database and dictionary folder in a temporary directory. Always runs.
  - RealDictionary: the real dictionary folder against the real local database. Skipped if not built.

Run:  python -m unittest discover -s tests -v
"""
import csv
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
ROOT = Path(__file__).resolve().parents[1]
from latest import latest_only  # the tests' own expected figures use the latest year only
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
    "rates": [dict(rate="Admission rate", rate_measure="DRVADM.DVADM01", numerator="DRVADM.ADMSSN", denominator="DRVADM.APPLCN", method="sum of counts")],
    "category_codes": [
        dict(table="ENR", column="LEVEL", code="1", label="All students", role="total", default="yes"),
        dict(table="ENR", column="STUDY", code="1", label="Main study", role="total", default="yes"),
        dict(table="ENR", column="STUDY", code="2", label="Other study", role="part"),
        dict(table="ENR", column="LEVEL", code="2", label="Undergraduate", role="part", breakdown_set="By level", set_total="1", set_fixed="STUDY = 1"),
        dict(table="ENR", column="LEVEL", code="3", label="Graduate", role="part", breakdown_set="By level", set_total="1", set_fixed="STUDY = 1"),
        dict(table="ENR", column="LEVEL", code="4", label="Full-time", role="part", breakdown_set="By attendance", set_total="1", set_fixed="STUDY = 1"),
        dict(table="ENR", column="LEVEL", code="5", label="Part-time", role="part", breakdown_set="By attendance", set_total="1", set_fixed="STUDY = 1"),
        dict(table="ENR", column="LEVEL", code="6", label="Online", role="part", breakdown_set="By mode", set_total="sum of parts"),
        dict(table="ENR", column="LEVEL", code="7", label="In person", role="part", breakdown_set="By mode", set_total="sum of parts")],
    "outside_ipeds": [], "special_codes": [], "measure_history": [], "comparability_breaks": [], "breakdown_exceptions": [],
    "year_meaning": [dict(table=t, years="2024", kind="fall", period="Fall {Y}") for t in ("HD", "IC", "DRVADM", "ENR")],
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
        bd.build(self.db_path, self.tmp, full=True)
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

    def test_fixed_values_are_a_default_and_every_other_value_is_tested(self):
        db = self.build()
        slices = db.execute("SELECT slice, n_tested, n_ok, status FROM breakdown_slices WHERE set_name='By level' "
                            "AND measure='CNT' ORDER BY slice").fetchall()
        # STUDY = 1 is the default and adds up at both schools. STUDY = 2 has a part row but no total row, so it
        # cannot be tested and is not offered.
        self.assertEqual(slices, [("STUDY = 1", 2, 2, "loaded")])
        bad = db.execute("SELECT status FROM breakdown_slices WHERE set_name='By attendance' AND measure='CNT'").fetchall()
        self.assertEqual(bad, [("failed",)])
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

    def test_row_keys_and_defaults(self):
        db = self.build()
        self.assertEqual(db.execute('SELECT "column", default_code FROM row_keys WHERE "table"=\'ENR\'').fetchall(),
                         [("LEVEL", "1"), ("STUDY", "1")])
        db.close()

    def test_two_defaults_for_one_column_stop_the_build(self):
        codes = [dict(r) for r in GOOD["category_codes"]]
        next(r for r in codes if r["column"] == "LEVEL" and r["code"] == "2")["default"] = "yes"   # LEVEL: two defaults
        self.assertProblem("has 2 default codes", category_codes=codes)

    def test_unknown_rate_method_stops_the_build(self):
        self.assertProblem("must be one of", rates=[dict(GOOD["rates"][0], method="median")])

    def test_rate_rows_sharing_a_measure_must_say_which_schools(self):
        rates = GOOD["rates"] + [dict(rate="Admission rate, other", rate_measure="DRVADM.DVADM01",
                                      numerator="DRVADM.ADMSSN", denominator="DRVADM.APPLCN", method="sum of counts")]
        self.assertProblem("each must say which schools it applies to", rates=rates)

    def test_set_whose_rows_disagree_about_the_total_stops_the_build(self):
        codes = [dict(r) for r in GOOD["category_codes"]]
        next(r for r in codes if r["column"] == "LEVEL" and r["code"] == "2")["set_total"] = "9"
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

    # ---- part 5b: the dictionary across years
    def add_2023(self):
        """A second, earlier year: the same schools, with level 2 of ENR reported under code 8 instead (a code
        that IPEDS changed), and school 3 not yet open."""
        con = sqlite3.connect(self.db_path)
        for t in ("HD", "IC", "DRVADM", "ENR"):
            con.execute(f"INSERT INTO _tables VALUES ('{t}', '{t}2023', 'data', 2023)")
            con.executescript(f"CREATE TEMP TABLE copy AS SELECT * FROM {t} WHERE year = 2024; UPDATE copy SET year = 2023; "
                              f"INSERT INTO {t} SELECT * FROM copy; DROP TABLE copy;")
        con.execute("UPDATE ENR SET LEVEL = 8 WHERE year = 2023 AND LEVEL = 2")
        con.execute("DELETE FROM HD WHERE year = 2023 AND UNITID = 3")
        con.commit()
        con.close()

    def test_years_of_category_rows_and_tests_in_every_year(self):
        self.add_2023()
        codes = [dict(r, years="2024") if r["code"] == "2" else dict(r) for r in GOOD["category_codes"]]
        codes.append(dict(table="ENR", column="LEVEL", code="8", label="Undergraduate", role="part", breakdown_set="By level",
                          set_total="1", set_fixed="STUDY = 1", years="2023"))
        db = self.build(category_codes=codes, year_meaning=[dict(r, years="2023-2024") for r in GOOD["year_meaning"]])
        status = dict(db.execute("SELECT year, status FROM year_checks WHERE name='By level' AND measure='CNT'").fetchall())
        self.assertEqual(status, {2023: "loaded", 2024: "loaded"})              # each year tested with its own codes
        self.assertEqual([p for (p,) in db.execute(       # the result tables hold the latest year's parts
"SELECT part FROM breakdown_parts WHERE set_name='By level' ORDER BY 1")], ["2", "3"])
        self.assertEqual(dict(db.execute("SELECT code, in_latest FROM dict_category_codes WHERE code IN ('2', '8')")),
                         {"2": "yes", "8": "no"})
        db.close()

    def test_year_meaning_must_cover_every_year(self):
        self.add_2023()
        self.assertProblem("no row for data table ENR covers 2023")

    def test_measure_years_and_rate_years(self):
        self.add_2023()
        con = sqlite3.connect(self.db_path)
        con.execute("INSERT INTO DRVADM VALUES (2024, 1, 50, 5, 10), (2023, 1, 50, NULL, 10)")   # 2023: no admits count
        con.commit()
        con.close()
        db = self.build(year_meaning=[dict(r, years="2023-2024") for r in GOOD["year_meaning"]])
        try:
            years = dict(db.execute("SELECT year, n_values FROM measure_years WHERE measure='DRVADM.DVADM01'").fetchall())
            self.assertEqual(years, {2023: 1, 2024: 1})
            rate = dict(db.execute("SELECT year, available FROM rate_years WHERE rate='Admission rate'").fetchall())
            self.assertEqual(rate, {2023: "no", 2024: "yes"})                  # a rate starts only once all its counts exist
        finally:
            db.close()

    def test_group_as_of_latest_year(self):
        self.add_2023()
        con = sqlite3.connect(self.db_path)
        con.execute("UPDATE HD SET SECTOR = 2 WHERE year = 2023 AND UNITID = 4")  # school 4 was private in 2023
        con.commit()
        con.close()
        groups = [dict(r) for r in GOOD["school_groups"]] + [dict(group="Public now", kind="column", table="HD", column="SECTOR",
                                                                   codes="1", membership="as of latest year")]
        db = self.build(school_groups=groups, year_meaning=[dict(r, years="2023-2024") for r in GOOD["year_meaning"]])
        each = [u for (u,) in db.execute("SELECT unitid FROM group_membership WHERE group_name='Public four-year' AND year=2023 ORDER BY 1")]
        latest = [u for (u,) in db.execute("SELECT unitid FROM group_membership WHERE group_name='Public now' AND year=2023 ORDER BY 1")]
        self.assertEqual((each, latest), ([1], [1, 4]))
        db.close()

    def old_column_setup(self, fill_2024=False):
        """2023 keeps the student level in another column, OLDLEV (codes 101-107), as 12-month enrollment did before
        2020-21. DRVADM.TOT is a summary of ENR.CNT at level 1, study 1."""
        self.add_2023()
        con = sqlite3.connect(self.db_path)
        con.executescript("""ALTER TABLE ENR ADD COLUMN OLDLEV INTEGER; ALTER TABLE DRVADM ADD COLUMN TOT INTEGER;
            UPDATE ENR SET LEVEL = 2 WHERE year = 2023 AND LEVEL = 8;
            UPDATE ENR SET OLDLEV = LEVEL + 100, LEVEL = NULL WHERE year = 2023;
            INSERT INTO DRVADM (year, UNITID, TOT) VALUES (2024, 1, 100), (2024, 2, 10), (2023, 1, 100), (2023, 2, 10);""")
        if fill_2024:                                   # both columns filled in 2024, so the claim can be checked
            con.execute("UPDATE ENR SET OLDLEV = LEVEL + 100 WHERE year = 2024")
        con.commit()
        con.close()

    def old_column_dictionary(self, same_as=True):
        codes = [dict(r, years="2024") if r["column"] == "LEVEL" else dict(r) for r in GOOD["category_codes"]]
        for r in GOOD["category_codes"]:
            if r["column"] == "LEVEL":
                codes.append(dict(r, column="OLDLEV", code=str(100 + int(r["code"])), years="2023", breakdown_set="",
                                  set_total="", set_fixed="", same_as=f"LEVEL = {r['code']}" if same_as else ""))
        measures = GOOD["measures"] + [dict(table="DRVADM", variable="TOT", title="Students", format="Cont", data_type="N",
                                            detailed_measure="ENR.CNT where LEVEL = 1; STUDY = 1")]
        return dict(category_codes=codes, measures=measures,
                    year_meaning=[dict(r, years="2023-2024") for r in GOOD["year_meaning"]])

    def test_link_is_tested_in_an_earlier_year_through_same_as(self):
        self.old_column_setup()
        db = self.build(**self.old_column_dictionary())
        try:
            status = dict(db.execute("SELECT year, status FROM year_checks WHERE kind='link' AND name='DRVADM.TOT'").fetchall())
            self.assertEqual(status, {2023: "loaded", 2024: "loaded"})
            self.assertEqual(db.execute("SELECT rows FROM detail_links WHERE measure='DRVADM.TOT'").fetchone()[0],
                             '{"LEVEL": "1", "STUDY": "1"}')              # the app's year keeps the dictionary's rows
        finally:
            db.close()

    def test_link_without_a_counterpart_is_not_in_that_years_data(self):
        self.old_column_setup()
        db = self.build(**self.old_column_dictionary(same_as=False))     # no same_as: the build cannot read 2023
        try:
            status = dict(db.execute("SELECT year, status FROM year_checks WHERE kind='link' AND name='DRVADM.TOT'").fetchall())
            self.assertEqual(status, {2023: "not in this year's data", 2024: "loaded"})
        finally:
            db.close()

    def test_same_as_is_checked_where_both_columns_are_filled(self):
        self.old_column_setup(fill_2024=True)
        self.build(**self.old_column_dictionary()).close()                # the claim holds in 2024: no problem
        con = sqlite3.connect(self.db_path)
        con.execute("UPDATE ENR SET OLDLEV = 109 WHERE year = 2024 AND UNITID = 2 AND LEVEL = 1")   # now it does not
        con.commit()
        con.close()
        self.assertProblem("but only 1 have both", **self.old_column_dictionary())

    def test_unreadable_years_stop_the_build(self):
        codes = [dict(r, years="from 2020") if r["code"] == "2" else dict(r) for r in GOOD["category_codes"]]
        self.assertProblem("years 'from 2020' is not a year", category_codes=codes)

    def test_set_up_measures_are_checked_and_flagged_for_review(self):
        con = sqlite3.connect(self.db_path)
        con.executescript("""ALTER TABLE HD ADD COLUMN LOCALE INTEGER; UPDATE HD SET LOCALE = 11 WHERE UNITID = 1;
            UPDATE HD SET LOCALE = 99 WHERE UNITID = 2;
            INSERT INTO VALUESETS VALUES (2024, 'HD2024', 'LOCALE', '11', 'City: large');""")
        con.commit()
        con.close()
        measures = GOOD["measures"] + [
            dict(table="DRVADM", variable="ADMSSN", title="Admissions", format="Cont", data_type="N", unit="count",
                 in_first_version="yes"),                                    # no school has a value
            dict(table="HD", variable="LOCALE", title="Locale", format="Disc", data_type="N", unit="coded",
                 in_first_version="yes"),                                    # code 99 has no label
            dict(table="ENR", variable="CNT", title="Students", format="Cont", data_type="N", unit="count",
                 rows_per_school="many rows per school", in_first_version="yes")]   # ENR has category rows: fine
        db = self.build(measures=[m for m in measures if not (m["table"] == "ENR" and m["variable"] == "CNT"
                                                               and "unit" not in m)])
        checks = {(m, c) for m, c, _ in db.execute("SELECT * FROM measure_checks")}
        self.assertIn(("DRVADM.ADMSSN", "never a value"), checks)
        self.assertIn(("HD.LOCALE", "codes without labels"), checks)
        self.assertNotIn(("ENR.CNT", "no way to pick one row"), checks)
        db.close()


RESULTS = ["row_keys", "detail_links", "detail_link_exceptions", "breakdown_sets", "breakdown_parts", "breakdown_slices",
           "year_checks", "measure_years", "rate_years", "year_titles", "group_list", "group_membership", "directory",
           "name_clashes", "value_labels", "measure_checks"]


class FasterBuild(unittest.TestCase):
    """Part 5b decision: a build that reruns only what changed must leave the database exactly as a full build from
    the same dictionary would. Each test starts from a full build of a two-year made-up database, makes one kind of
    change, runs the faster build, and compares every dictionary and result table with a full build."""
    build, add_2023 = LoaderLogic.build, LoaderLogic.add_2023
    old_column_setup, old_column_dictionary = LoaderLogic.old_column_setup, LoaderLogic.old_column_dictionary

    def setUp(self):
        LoaderLogic.setUp(self)
        self.addCleanup(self.dir.cleanup)
        self.old_column_setup()                         # two years, the level under another column in 2023
        con = sqlite3.connect(self.db_path)
        con.executescript("""CREATE TABLE _releases (year INTEGER, release TEXT, status TEXT, source_file TEXT,
                                                     loaded_at TEXT, seconds REAL);
            INSERT INTO _releases VALUES (2023, 'R2023', 'final', '', 't1', 0), (2024, 'R2024', 'provisional', '', 't1', 0);""")
        con.commit()
        con.close()
        self.pristine = self.tmp / "pristine.sqlite"   # the data before any build, for the full build to compare with
        Path(self.pristine).write_bytes(Path(self.db_path).read_bytes())
        self.start = self.old_column_dictionary()
        self.build(**self.start).close()

    def write(self, **tables):
        tables = {**GOOD, **self.start, **tables}
        for name in bd.TABLES:
            with open(self.tmp / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=self.heads[name], restval="")
                w.writeheader()
                w.writerows(tables[name])

    def snapshot(self, path):
        con = sqlite3.connect(path)
        out = {}
        for t in [f"dict_{n}" for n in bd.TABLES] + RESULTS:
            out[t] = sorted(tuple("" if v is None else str(v) for v in r) for r in con.execute(f'SELECT * FROM "{t}"'))
        con.close()
        return out

    def same_as_full(self, edit_data=None):
        """Run the faster build on the database, a full build on a fresh copy, and compare."""
        steps = []
        from build import changes
        real = changes.update
        changes.update = lambda *a, **k: steps.extend(real(*a, **k) or ["full rebuild"]) or steps
        try:
            bd.build(self.db_path, self.tmp)
        finally:
            changes.update = real
        if edit_data:
            edit_data(self.pristine)
        bd.build(self.pristine, self.tmp, full=True)
        fast, full = self.snapshot(self.db_path), self.snapshot(self.pristine)
        for t in full:
            self.assertEqual(fast[t], full[t], f"{t} differs after: {'; '.join(steps)}")
        return steps

    def test_wording_change_reloads_in_seconds_with_no_data_checks(self):
        terms = [dict(r, statement="Admission rate is admits divided by applicants.") for r in GOOD["terms"]]
        measures = [dict(r, synonyms="acceptance rate") if r["variable"] == "DVADM01" else dict(r) for r in self.start["measures"]]
        steps = self.write(terms=terms, measures=measures) or self.same_as_full()
        self.assertIn("wording only: no data checks", steps)
        self.assertFalse([s for s in steps if s.startswith(("retested", "rechecked", "full"))], steps)

    def test_category_change_retests_only_that_table(self):
        codes = [dict(r, breakdown_set="", set_total="", set_fixed="") if r["code"] == "5" else dict(r)
                 for r in self.start["category_codes"]]
        steps = self.write(category_codes=codes) or self.same_as_full()
        self.assertTrue(any(s.startswith("retested ENR in 1 year") for s in steps), steps)   # only 2024 rows changed

    def test_change_to_one_table_leaves_the_other_tables_sets_alone(self):
        """A table-scoped retest (here DRVADM's parent-and-child rule) must pass over the breakdown sets of other
        tables (ENR) without touching them. It stopped with an error before (found on the real database)."""
        meaning = [dict(r, parent_child_flag="FLAGS.PRCH_ADM; FLAGS.IDX_ADM") if r["table"] == "DRVADM" else dict(r)
                   for r in self.start["year_meaning"]]
        steps = self.write(year_meaning=meaning) or self.same_as_full()
        self.assertTrue(any(s.startswith("retested DRVADM") for s in steps), steps)

    def test_a_run_that_stops_part_way_makes_the_next_run_a_full_rebuild(self):
        """A run that loads a table and then stops (here on a category row naming a column that does not exist) must
        not leave the next run comparing the new rows with themselves."""
        bad = self.start["category_codes"] + [dict(table="ENR", column="NOPE", code="1", label="x", role="part")]
        self.write(category_codes=bad)
        with self.assertRaises(ValueError):
            bd.build(self.db_path, self.tmp)
        codes = [dict(r, breakdown_set="", set_total="", set_fixed="") if r["code"] == "5" else dict(r)
                 for r in self.start["category_codes"]]
        steps = self.write(category_codes=codes) or self.same_as_full()
        self.assertEqual(steps, [])                     # the faster path was not used: the run was a full rebuild

    def test_measure_change_rechecks_only_that_measure(self):
        measures = [dict(r, format="Disc") if r["variable"] == "AID" else dict(r) for r in self.start["measures"]]
        steps = self.write(measures=measures) or self.same_as_full()
        self.assertIn("rechecked 1 measure(s)", steps)

    def test_replaced_release_runs_that_years_checks(self):
        def edit(path):
            con = sqlite3.connect(path)
            con.execute("UPDATE ENR SET CNT = 101 WHERE year = 2023 AND UNITID = 1 AND OLDLEV = 101")
            con.execute("UPDATE _releases SET loaded_at = 't2' WHERE year = 2023")
            con.commit()
            con.close()
        edit(self.db_path)
        self.write()
        steps = self.same_as_full(edit_data=edit)
        self.assertIn("full checks for 2023", steps)

    def test_one_table_reloaded_on_its_own(self):
        terms = [dict(r, statement="Changed.") for r in GOOD["terms"]]
        codes = [dict(r, label=r["label"] + " (changed)") for r in self.start["category_codes"]]
        self.write(terms=terms, category_codes=codes)
        bd.build(self.db_path, self.tmp, table="terms")             # only terms: the category change waits
        con = sqlite3.connect(self.db_path)
        self.assertEqual(con.execute("SELECT statement FROM dict_terms").fetchone()[0], "Changed.")
        self.assertNotIn("(changed)", con.execute("SELECT group_concat(label) FROM dict_category_codes").fetchone()[0])
        con.close()
        self.same_as_full()                                          # the next run applies the rest


@unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built; run python build/build_data.py")
class RealDictionary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = latest_only(sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True))
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
        db = latest_only(sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True))
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
        self.assertEqual(len(rows), 12)
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

    def test_a_request_may_change_the_fixed_values(self):
        """Bachelor's degrees by field and undergraduates by age: the set adds up at those values too."""
        def slice_of(name, measure, where):
            return self.db.execute("SELECT n_tested, n_ok, status FROM breakdown_slices WHERE set_name=? AND measure=? AND slice=?",
                                   (name, measure, where)).fetchone()
        for name, measure, where in [("Degrees by field of study", "CTOTALT", "AWLEVEL = 5; MAJORNUM = 1"),
                                     ("Degrees by field of study", "CTOTALT", "AWLEVEL = 12; MAJORNUM = 1"),
                                     ("Fall enrollment by age", "EFAGE09", "LSTUDY = 2"),
                                     ("Fall enrollment by age", "EFAGE09", "LSTUDY = 5"),
                                     ("Staff by occupation", "EAPTOT", "FACSTAT = 0")]:
            tested, ok, status = slice_of(name, measure, where)
            self.assertEqual((status, tested), ("loaded", ok), f"{name} at {where}")
            self.assertGreater(tested, 1000)
        # Yale's bachelor's degrees by field add up to its bachelor's total.
        parts = ", ".join("'" + p + "'" for (p,) in self.db.execute(
            "SELECT part FROM breakdown_parts WHERE set_name='Degrees by field of study'"))
        by_field, total = self.db.execute(
            f"SELECT SUM(CASE WHEN CIPCODE IN ({parts}) THEN CTOTALT END), MAX(CASE WHEN CIPCODE='99' THEN CTOTALT END) "
            "FROM C_A WHERE unitid=130794 AND AWLEVEL=5 AND MAJORNUM=1").fetchone()
        self.assertEqual(by_field, total)
        self.assertGreater(total, 1000)

    def test_optional_year_table_carries_a_caveat(self):
        rows = self.db.execute('SELECT "table", caveat FROM dict_year_meaning WHERE caveat IS NOT NULL').fetchall()
        self.assertEqual([t for t, _ in rows], ["EFB"])
        self.assertIn("2,576 of 5,842", rows[0][1])
        self.assertEqual(self.db.execute("SELECT COUNT(DISTINCT UNITID) FROM EFB").fetchone()[0], 2576)
        self.assertEqual(self.db.execute("SELECT COUNT(DISTINCT UNITID) FROM EFA").fetchone()[0], 5842)

    def test_a_rate_column_is_not_offered_as_a_breakdown_of_counts(self):
        """Percentages do not add up, so the set is not loaded for them."""
        status = self.db.execute("SELECT status FROM breakdown_sets WHERE set_name='Outcome measures by Pell status' "
                                 "AND measure='OMAWDP8'").fetchone()[0]
        self.assertEqual(status, "failed")

    def test_retired_variables_carry_the_releases_they_appeared_in(self):
        """Every retired variable is in measures.csv, not set up, and its years_available match the data."""
        def spans(ys):
            out = []
            for y in ys:
                out = out[:-1] + [(out[-1][0], y)] if out and y == out[-1][1] + 1 else out + [(y, y)]
            return ", ".join(f"{a}-{b}" if a != b else str(a) for a, b in out)
        rows = self.db.execute("SELECT \"table\" || '.' || variable, years_available, in_first_version FROM dict_measures "
                               "WHERE years_available IS NOT NULL").fetchall()
        self.assertGreater(len(rows), 400)
        for measure, cell, set_up in rows:
            years = [y for (y,) in self.db.execute("SELECT year FROM main.measure_years WHERE measure = ? ORDER BY year",
                                                   (measure,))]
            not_set_up = ("IC.TUITVRY1", "IC.TUITVRY2", "IC.TUITVRY3")       # no codebook entry: owner, 2026-11-23
            self.assertEqual((cell, set_up), (spans(years), "no" if measure in not_set_up else "yes"), measure)
            self.assertNotIn(2024, years, measure)

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

    def test_units(self):
        rows = self.db.execute("SELECT \"table\", variable, format, unit FROM dict_measures WHERE in_first_version='yes'").fetchall()
        self.assertEqual({u for *_, u in rows} - {None}, {"count", "dollars", "percent", "average", "ratio", "coded"})
        unit = {(t, v): u for t, v, _, u in rows}
        self.assertEqual(unit[("DRVEF", "ENRTOT")], "count")
        self.assertEqual(unit[("SFA", "UPGRNTT")], "dollars")
        self.assertEqual(unit[("DRVGR", "GBA6RTT")], "percent")
        self.assertEqual(unit[("EFD", "STUFACR")], "ratio")
        self.assertEqual(unit[("DRVCOST", "TUFEYR3")], "average")        # a published price is per student
        self.assertEqual(unit[("DRVF", "F1ENDMFT")], "average")          # per FTE
        self.assertEqual(unit[("HD", "SECTOR")], "coded")
        self.assertIsNone(unit[("ADM", "SATVR25")])                       # percentile score: not summable
        # A number is blank only when the rules say it is not a quantity (an ID number, a test-score percentile, a map
        # coordinate) or it is on the owner's review list of units the rules could not decide.
        review = {r["measure"] for r in csv.DictReader(open(ROOT / "docs" / "reports" / "stage5b2" / "unit_review.csv",
                                                            encoding="utf-8"))}
        titles = dict(((t, v), f"{ti} {(d or '')[:400]}") for t, v, ti, d in self.db.execute(   # text fields have no unit
            "SELECT \"table\", variable, title, long_description FROM dict_measures WHERE data_type <> 'A'"))
        quantity = re.compile(r"percentile|latitude|longitude|unitid|identif|id number|institution id|ipedsid|fips|zip", re.I)
        missing = [(t, v) for t, v, f, u in rows if f == "Cont" and u is None and (t, v) in titles
                   and not quantity.search(titles[(t, v)] or "")
                   and f"{t}.{v}" not in review and t != "HD"]
        self.assertEqual(missing, [])
        summable = self.db.execute("SELECT condition FROM dict_terms WHERE term='summable units'").fetchone()[0]
        self.assertEqual(summable, "count, dollars")

    def test_every_measure_named_by_a_term_or_rate_is_in_the_first_version(self):
        left = self.db.execute("SELECT t.measure FROM dict_terms t JOIN dict_measures m ON UPPER(m.\"table\" || '.' || m.variable) "
                               "= UPPER(t.measure) WHERE m.in_first_version <> 'yes'").fetchall()
        self.assertEqual(left, [])

    def test_default_rows(self):
        keys = {(t, c): d for t, c, d in self.db.execute('SELECT "table", "column", default_code FROM row_keys')}
        self.assertEqual(keys[("C_A", "MAJORNUM")], "1")
        self.assertEqual(keys[("EFA", "EFALEVEL")], "1")
        self.assertEqual(keys[("EAP", "EAPCAT")], "10000")
        self.assertEqual([k for k, d in keys.items() if d is None], [("C_C", "AWLEVELC"), ("EFCP", "EFCIPLEV"), ("GR", "GRTYPE")])
        self.assertNotIn(("EAP", "OCCUPCAT"), keys)                      # describes the row; the key is EAPCAT
        # With the defaults, Yale has one row in the fall enrollment table: all students, 15,564.
        self.assertEqual(self.db.execute("SELECT EFTOTLT FROM EFA WHERE UNITID=130794 AND EFALEVEL=1").fetchall(), [(15564,)])

    def test_rates_say_which_schools_they_apply_to(self):
        rows = dict(self.db.execute("SELECT rate, applies_to FROM dict_rates WHERE rate_measure='DRVGR.GRRTTOT'"))
        self.assertEqual(set(rows.values()), {"Four or more years", "At least 2 but less than 4 years"})

    def test_settings_for_unstated_things_and_the_ranking_guard(self):
        got = dict(self.db.execute("SELECT term, condition FROM dict_terms WHERE kind='setting' AND is_default='yes'"))
        self.assertEqual(got["no year stated"], "latest")
        self.assertEqual(got["no group stated"], "National universe")
        self.assertEqual(got["top with no number"], "10")
        self.assertEqual(got["ranking guard"], "denominator >= 30")
        self.assertIsNotNone(self.db.execute("SELECT 1 FROM group_list WHERE group_name='National universe'").fetchone())

    def ratio(self, num, den, where="", universe="national"):
        """Sum of numerators over sum of denominators, over schools with both, in a universe."""
        schools = ("(SELECT unitid FROM group_membership WHERE group_name='National universe')" if universe == "national"
                   else "(SELECT UNITID FROM HD WHERE FIPS BETWEEN 1 AND 56 AND PSET4FLG IN (1, 3))")
        (nt, nc), (dt, dc) = num.split("."), den.split(".")
        a, b = self.db.execute(f'SELECT SUM(n.v), SUM(d.v) FROM (SELECT UNITID, "{nc}" v FROM "{nt}" WHERE UNITID IN {schools}{where}) n '
                               f'JOIN (SELECT UNITID, "{dc}" v FROM "{dt}" WHERE UNITID IN {schools}{where}) d USING (UNITID) '
                               "WHERE n.v IS NOT NULL AND d.v IS NOT NULL").fetchone()
        return a / b

    def test_core_expenses_per_fte_student(self):
        rows = self.db.execute("SELECT numerator, denominator, applies_to FROM dict_rates WHERE rate = 'Core expenses per FTE student'").fetchall()
        self.assertEqual(len(rows), 3)
        self.assertEqual({d for _, d, _ in rows}, {"DRVEF12.FTE12MN"})
        # NCES publishes public and private nonprofit together: each school has values on one form only.
        a, b = self.db.execute("SELECT SUM(COALESCE(r.F1COREXP, r.F2COREXP)), SUM(e.FTE12MN) FROM DRVF r JOIN DRVEF12 e USING (UNITID) "
                               "JOIN directory d USING (UNITID) WHERE d.CONTROL IN (1, 2) AND r.UNITID IN "
                               "(SELECT unitid FROM group_membership WHERE group_name='National universe') "
                               "AND COALESCE(r.F1COREXP, r.F2COREXP) IS NOT NULL AND e.FTE12MN IS NOT NULL").fetchone()
        self.assertEqual(round(a / b), 38376)
        self.assertEqual(round(self.ratio("DRVF.F1COREXP", "DRVEF12.FTE12MN")), 32973)

    def test_average_salary(self):
        all_ranks = " AND ARANK = 7"
        self.assertEqual(round(self.ratio("SAL_IS.SAEQ9OT", "SAL_IS.SATOTLT", all_ranks, universe="with offices")), 100224)  # NCES
        self.assertEqual(round(self.ratio("SAL_IS.SAEQ9OT", "SAL_IS.SATOTLT", all_ranks)), 100254)                          # app universe
        ranks = self.db.execute("SELECT numerator_code FROM dict_rates WHERE rate LIKE 'Average salary%' ORDER BY numerator_code").fetchall()
        self.assertEqual([r for (r,) in ranks], ["1", "2", "3", "4", "5", "6", "7"])
        # The ready-made school figure equals outlays over staff at every school.
        differ = self.db.execute("SELECT COUNT(*) FROM DRVHR h JOIN SAL_IS s USING (UNITID) WHERE s.ARANK = 7 AND s.SATOTLT > 0 "
                                 "AND ABS(h.SALTOTL - s.SAEQ9OT * 1.0 / s.SATOTLT) > 1").fetchone()[0]
        self.assertEqual(differ, 0)

    def test_net_price_weights_line_up_and_are_approved(self):
        rows = self.db.execute("SELECT numerator, denominator, method, status FROM dict_rates WHERE rate LIKE 'Average net price%'").fetchall()
        self.assertEqual(len(rows), 4)                          # grant-aided and Title IV, public and private
        self.assertEqual({(m, s.split(":")[0]) for _, _, m, s in rows}, {("weighted average", "Approved 2026-11-21")})
        for avg, count in [(n, d) for n, d, _, _ in rows]:
            (at, ac), (ct, cc) = avg.split("."), count.split(".")
            missing = self.db.execute(f'SELECT COUNT(*) FROM "{at}" a LEFT JOIN "{ct}" c USING (UNITID) '
                                      f'WHERE a."{ac}" IS NOT NULL AND (c."{cc}" IS NULL OR c."{cc}" = 0)').fetchone()[0]
            self.assertEqual(missing, 0, avg)

    def test_finance_reporting_forms(self):
        counts = [self.n(f"Reports on the {f} finance form") for f in ("GASB", "FASB", "for-profit")]
        expected = [self.db.execute(f"SELECT COUNT(*) FROM DRVF WHERE {c} IS NOT NULL").fetchone()[0]
                    for c in ("F1COREXP", "F2COREXP", "F3COREXP")]
        self.assertEqual(counts, expected)
        forms = dict(self.db.execute("SELECT variable, reporting_form FROM dict_measures WHERE \"table\" = 'DRVF' AND variable LIKE '%COREXP'"))
        self.assertEqual(forms, {"F1COREXP": "GASB", "F2COREXP": "FASB", "F3COREXP": "for-profit"})
        unformed = self.db.execute("SELECT COUNT(*) FROM dict_measures WHERE \"table\" IN ('DRVF', 'F_F1A', 'F_F2', 'F_F3') "
                                   "AND reporting_form IS NULL AND format = 'Cont'").fetchone()[0]
        self.assertEqual(unformed, 0)
        rule = self.db.execute("SELECT condition, statement FROM dict_terms WHERE term='different reporting forms'").fetchone()
        self.assertEqual(rule[0], "split by reporting_form")
        self.assertIn("different accounting standards", rule[1])

    def test_detail_links(self):
        rows = self.db.execute("SELECT measure, detailed, n_schools, n_agree FROM detail_links WHERE status='loaded'").fetchall()
        self.assertEqual(len(rows), 54)
        unexplained = self.db.execute("SELECT COUNT(*) FROM detail_link_exceptions WHERE flag IS NULL").fetchone()[0]
        self.assertEqual(unexplained, 0)                             # every difference is at a parent or child campus
        link = {m: (d, n, a) for m, d, n, a in rows}
        self.assertEqual(link["DRVEF.EFUG"][0], "EFA.EFTOTLT")
        for measure, (_, n, agree) in link.items():                 # only a few campuses reporting together differ
            self.assertGreaterEqual(agree, n - 9, measure)
        yale = self.db.execute("SELECT EFUG FROM DRVEF WHERE UNITID=130794").fetchone()[0]
        self.assertEqual(yale, self.db.execute("SELECT EFTOTLT FROM EFA WHERE UNITID=130794 AND EFALEVEL=2").fetchone()[0])

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
