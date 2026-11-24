"""Write docs/DATABASE.md: an inventory of the local database (data/ipeds_v2.sqlite).

    python scripts/database_inventory.py

Run after each full rebuild (build_data.py and build_dictionary.py --full call it). Every table is listed with its layer,
what it holds, its key columns, its number of columns and rows, and, for survey and codebook tables, the releases present
and the rows in each. Row counts are counted from the tables themselves, not taken from the build's own records.
"""
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config

LAYERS = ["survey data", "IPEDS codebook", "dictionary", "build result", "housekeeping"]

# What each table outside the survey data holds, and its key columns. The survey tables are described from
# year_meaning.csv (their subject and IPEDS title) and keyed by UNITID, year and their row keys (row_keys).
CODEBOOK = {
    "FILENAMES": ("Each release's data files, with their titles and the fields that pick one row", "year, fileName"),
    "NEWVARIABLES": ("Variables new in each release", "year, TableName, VarName"),
    "SECTIONTABLE": ("The survey sections of each data file", "year, fileName, sectionNumber"),
    "TABLES": ("Each release's tables: survey, title, years covered and release date", "year, TableName"),
    "TABLES19_RV": ("A list of revised tables in the 2019-20 release's codebook; it has no rows", "year, TableName"),
    "VALUESETS": ("The codebooks' code labels for every coded variable", "year, TableName, varName, Codevalue"),
    "VARTABLE": ("Every variable of every table, with its title and format", "year, TableName, varName"),
}
DICTIONARY = {
    "dict_measures": ("Every measure: table, variable, title, unit, period, plain name and set-up status", "table, variable"),
    "dict_terms": ("Words people use, their readings and the measures each reading names; settings and messages",
                   "term, reading, measure"),
    "dict_school_groups": ("Named school groups and how each is defined", "group"),
    "dict_group_members": ("Groups defined by a list of schools", "group, unitid"),
    "dict_school_nicknames": ("Nicknames and abbreviations for schools", "nickname"),
    "dict_rates": ("Rates and averages computed from counts: numerator, denominator and method", "rate, applies_to"),
    "dict_category_codes": ("The category rows of multi-row tables, with labels, defaults and the years each applies",
                            "table, column, code"),
    "dict_year_meaning": ("What the year of each table means: its period, cohort rule, subject and title", "table"),
    "dict_outside_ipeds": ("Topics IPEDS does not collect, and where to look instead", "topic"),
    "dict_special_codes": ("How IPEDS's special codes (-1, -2, ...) are read", "code"),
    "dict_measure_history": ("Earlier names of each measure, so a trend continues across a renaming", "measure, earlier_table, earlier_variable"),
    "dict_comparability_breaks": ("Definition changes and context notes shown on trends that cross them", "kind, tables, first_release"),
    "dict_word_abbreviations": ("Abbreviated words in school names and what they mean (st: state or saint)", "abbreviation, means"),
    "dict_breakdown_exceptions": ("Schools whose breakdown is shown despite parts not adding up, by owner decision",
                                  "breakdown_set, table, year, unitid"),
}
BUILD = {
    "directory": ("One row per school and year: name, location, sector, level, Carnegie and other directory fields", "year, UNITID"),
    "group_list": ("Every school group the app can use, with its definition and size", "group_name"),
    "group_membership": ("Which schools belong to each group in each year", "group_name, year, unitid"),
    "row_keys": ("For each multi-row table, the columns that pick one row and their default codes (latest year)", "table, column"),
    "detail_links": ("Summary measures linked to the detailed table they can be broken down through", "measure"),
    "detail_link_exceptions": ("Schools where a summary and its detailed figure differ, with the reason", "measure, unitid"),
    "breakdown_sets": ("Tested breakdown sets, per measure, with their total and status (latest year)", "set_name, table, measure"),
    "breakdown_parts": ("The parts of each breakdown set", "set_name, table, part"),
    "breakdown_slices": ("Breakdown sets tested at other fixed values (a slice)", "set_name, table, measure, slice"),
    "year_checks": ("Row keys, detail links and breakdown sets tested in every year", "year, kind, name, table, measure"),
    "measure_years": ("Where each measure is stored in each year, and how many schools have a value", "measure, year"),
    "rate_years": ("Whether each rate's counts exist in each year", "rate, applies_to, year"),
    "year_titles": ("Each measure's title in each year's codebook", "measure, year"),
    "measure_checks": ("Measures flagged by the build: never a value, codes without labels, no way to pick one row", "measure, check"),
    "name_clashes": ("Shown names still shared by more than one measure", "name"),
    "value_labels": ("Code labels for coded columns, from the codebooks, by year", "local_table, column, code, year"),
    "_missing_reasons": ("Why a school has no value in a cell (not applicable, not reported): for display only, never calculated",
                         "local_table, year, unitid, column"),
}
HOUSEKEEPING = {
    "_tables": ("Every table loaded from each release: source name, kind, rows read and loaded", "local_table, year"),
    "_columns": ("Every column loaded from each release, with its types and what cleaning did to it", "local_table, release, column"),
    "_releases": ("The releases loaded, provisional or final, and when", "year"),
    "_special_codes": ("The special codes found in each column of each release, and how each was treated", "local_table, release, column, code"),
    "_conversion_failures": ("Values that failed to convert during cleaning (expected to be empty)", "local_table, release, column, value"),
    "_dictionary_state": ("Fingerprints of the dictionary files and data, so the fast build knows what changed", "item"),
    "sqlite_stat1": ("SQLite's own statistics for its query planner", "tbl, idx"),
}


def q(db, sql, *args):
    return db.execute(sql, args).fetchall()


def inventory(db_path):
    db = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    try:
        names = [n for (n,) in q(db, "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        kinds = dict(q(db, "SELECT DISTINCT local_table, kind FROM _tables"))
        meaning = {t: (s, ti) for t, s, ti in q(db, 'SELECT "table", subject, title FROM dict_year_meaning')}
        keys = {}
        for t, c in q(db, 'SELECT "table", "column" FROM row_keys ORDER BY rowid'):
            for part in c.split(","):
                keys.setdefault(t, []).append(part.strip())
        latest = {t: y for t, y in q(db, "SELECT local_table, MAX(year) FROM _tables GROUP BY 1")}
        out = []
        for name in names:
            columns = [r[1] for r in q(db, f'PRAGMA table_info("{name}")')]
            rows = q(db, f'SELECT COUNT(*) FROM "{name}"')[0][0]
            by_release = None
            if kinds.get(name) == "data":
                layer = "survey data"
                subject, title = meaning.get(name, (None, None))
                held = (subject or name) + (f": {title}" if title and title != subject else "")
                key = ", ".join(["UNITID", "year"] + [k for k in keys.get(name, []) if k not in ("UNITID", "year")])
            elif kinds.get(name) == "codebook":
                layer = "IPEDS codebook"
                held, key = CODEBOOK.get(name, ("IPEDS codebook table", "year"))
            elif name in DICTIONARY:
                layer, (held, key) = "dictionary", DICTIONARY[name]
            elif name in BUILD:
                layer, (held, key) = "build result", BUILD[name]
            elif name in HOUSEKEEPING:
                layer, (held, key) = "housekeeping", HOUSEKEEPING[name]
            elif name.startswith("dict_"):
                layer, held, key = "dictionary", "Dictionary table (not yet described here)", ""
            else:
                layer, held, key = "build result", "Not yet described here", ""
            if layer in ("survey data", "IPEDS codebook") and "year" in columns:
                by_release = q(db, f'SELECT year, COUNT(*) FROM "{name}" GROUP BY year ORDER BY year')
            out.append(dict(name=name, layer=layer, held=held, key=key, n_columns=len(columns), rows=rows,
                            by_release=by_release, latest=latest.get(name)))
        releases = q(db, "SELECT year, release, status FROM _releases ORDER BY year")
        return out, releases
    finally:
        db.close()


def label(y):
    return f"{y}-{(y + 1) % 100:02d}"


def markdown(tables, releases, size, seconds):
    years = [y for y, _, _ in releases]
    lines = ["# The local database: inventory", "",
             "Written by `scripts/database_inventory.py` after each full rebuild. Do not edit by hand; run the script again.", "",
             f"`data/ipeds_v2.sqlite`, generated {time.strftime('%Y-%m-%d')}.", "",
             "| | |", "| --- | ---: |",
             f"| Tables | {len(tables):,} |",
             f"| Rows | {sum(t['rows'] for t in tables):,} |",
             f"| File size | {size / 1e9:.2f} GB ({size:,} bytes) |",
             f"| Releases | {len(releases)} ({label(years[0])} to {label(years[-1])}) |" if years else "| Releases | none |", ""]
    lines += ["Tables and rows by layer:", "", "| Layer | Tables | Rows |", "| --- | ---: | ---: |"]
    for layer in LAYERS:
        mine = [t for t in tables if t["layer"] == layer]
        lines.append(f"| {layer} | {len(mine):,} | {sum(t['rows'] for t in mine):,} |")
    lines += ["", "Releases loaded:", "", "| Release year | Release | Status |", "| --- | --- | --- |"]
    lines += [f"| {label(y)} | {r} | {s} |" for y, r, s in releases]
    lines += ["", "The layers:",
              "- **survey data:** the IPEDS survey tables, one per survey file, stacked across releases (a `year` column holds the release year: 2024 for 2024-25). Each is described by its subject and IPEDS's title in the latest release that has it;",
              "- **IPEDS codebook:** the codebook tables that come with each release (tables, variables, code labels);",
              "- **dictionary:** the CSV tables of the `dictionary` folder, loaded as they are (`dict_` + the file name);",
              "- **build result:** tables the build works out from the data and the dictionary (directory, groups, tests in every year, the years of each measure);",
              "- **housekeeping:** the build's own records (what was loaded and cleaned, fingerprints for the fast build) and SQLite's statistics.", ""]
    for layer in LAYERS:
        mine = [t for t in tables if t["layer"] == layer]
        if not mine:
            continue
        lines += [f"## {layer[0].upper() + layer[1:]} ({len(mine)} tables, {sum(t['rows'] for t in mine):,} rows)", ""]
        per_release = layer in ("survey data", "IPEDS codebook")
        head = ["Table", "What it holds", "Key columns", "Columns", "Rows"]
        if per_release:
            head += ["Releases"] + [label(y) for y in years]
        lines += ["| " + " | ".join(head) + " |", "| " + " | ".join(["---"] * 3 + ["---:"] * (len(head) - 3)) + " |"]
        for t in mine:
            row = [f"`{t['name']}`", t["held"].replace("|", "/"), t["key"], f"{t['n_columns']:,}", f"{t['rows']:,}"]
            if per_release:
                counts = dict(t["by_release"] or [])
                present = [y for y in years if counts.get(y)]
                row.append(f"{len(present)}" + (f" ({label(present[0])} to {label(present[-1])})" if present else ""))
                row += [f"{counts[y]:,}" if counts.get(y) else "" for y in years]
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    lines += [f"Counted in {seconds:.0f} seconds."]
    return "\n".join(lines) + "\n"


def write(db_path=None, out_path=None):
    db_path = Path(db_path or config.LOCAL_DB)
    out_path = Path(out_path or ROOT / "docs" / "DATABASE.md")
    start = time.time()
    tables, releases = inventory(db_path)
    out_path.write_text(markdown(tables, releases, os.path.getsize(db_path), time.time() - start), encoding="utf-8")
    return out_path, tables


if __name__ == "__main__":
    path, tables = write()
    print(f"{path}: {len(tables)} tables, {sum(t['rows'] for t in tables):,} rows")
