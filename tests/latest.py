"""For the tests' own expected-value queries: see each stacked table at the year the app answers from.

The app filters every query by year. The tests check its answers against figures they compute themselves with
plain SQL; on a database holding ten years, that SQL would mix years. latest_only() gives the test's connection
temporary views, under the same names, that hold only the latest year (SQLite reads temporary views before the
stored tables of the same name). The app's own connections are not touched.
"""

DERIVED = ("directory", "group_membership", "_missing_reasons")


def latest_only(db):
    tables = [t for (t,) in db.execute("SELECT DISTINCT local_table FROM main._tables")] + list(DERIVED)
    for t in tables:
        db.execute(f'DROP VIEW IF EXISTS temp."{t}"')
        db.execute(f'CREATE TEMP VIEW "{t}" AS SELECT * FROM main."{t}" WHERE year = (SELECT MAX(year) FROM main._tables)')
    return db
