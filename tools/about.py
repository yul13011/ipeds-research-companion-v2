"""Figures the page states about itself, read from the data rather than typed in (Part 6b):
the releases held, and the benchmark match rates from the latest benchmark run."""
import csv
import sqlite3

import config

# Statuses that count as a match. "within 0.1%" and "within 0.1 point" are the benchmark scripts' own tolerances
# for published figures rounded differently.
MATCHED = ("match", "within 0.1%", "within 0.1 point")
SOURCES = {"Yale": "Yale University figures", "NCES": "NCES national & sector aggregates"}


def releases(db_path=None):
    """[(year, release folder, status)] for every release in the local database, oldest first."""
    db = sqlite3.connect(f"file:{(db_path or config.LOCAL_DB.as_posix())}?mode=ro", uri=True)
    try:
        return db.execute("SELECT year, release, status FROM _releases ORDER BY year").fetchall()
    finally:
        db.close()


def releases_line(db_path=None):
    """"10 annual releases · 2015–16 Final through 2024–25 Provisional", as version 1 words it."""
    held = releases(db_path)
    name = lambda y, status: f"{y}–{(y + 1) % 100:02d} {status.capitalize()}"
    return f"{len(held)} annual releases · {name(held[0][0], held[0][2])} through {name(held[-1][0], held[-1][2])}"


def match_rates(path=None):
    """[(source, description, matched, compared)] from the latest benchmark file. Compared = matched + differs;
    questions the app declines or does not cover are not compared (the caption says so)."""
    path = path or config.BENCHMARKS
    if not path.exists():
        return []
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    out = []
    for source, description in SOURCES.items():
        mine = [r["status"] for r in rows if r["source"] == source]
        matched = sum(s in MATCHED for s in mine)
        compared = matched + sum(s == "differs" for s in mine)
        if compared:
            out.append((source, description, matched, compared))
    return out
