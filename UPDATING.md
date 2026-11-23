# Updating the data each year

Each year IPEDS publishes two releases:
- the **provisional** data for the newest year;
- the **final** data for the year before, which replaces its provisional release.

This runbook adds the new provisional release and replaces last year's provisional release with its final version. All years are kept; there is no rolling window. The database grows by about 300 MB a year.

Commands are run from this folder (`ipeds-research-companion-v2`) in a terminal.

## What the project can do and what it can't yet

| Step | Run by | Notes |
| --- | --- | --- |
| 1. Download from NCES | You | Not scripted |
| 2. Convert Access to SQLite | Version 1's converter, for now | Moves into version 2 before version 1 is retired |
| 3. Add to the cross-year index | Version 1's indexer, for now | Moves into version 2 before version 1 is retired |
| 4. Change the release list | You (one edit to `config.py`) | |
| 5. Load the releases and check the dictionary | This project (`build/build_data.py --release`) | |
| 6. Review the gap list | You | |
| 7. Tests, benchmarks, question set | This project | |
| 8. Release note | This project (draft) and you | |
| 9. Publish | Later stage (Render) | |

## The steps

### 1. Download the new releases

From NCES IPEDS (Data Center → Access databases), download:
- the new provisional release, for example `IPEDS_2025-26_Provisional`;
- the final version of last year's release, for example `IPEDS_2024-25_Final`.

### 2. Convert them to SQLite

Use version 1's converter, which writes one folder per release under `..\agent-redesign\data\annual\` (for example `..\agent-redesign\data\annual\IPEDS_2025-26_Provisional\IPEDS202526.sqlite`). It also writes a row-count check, `table_checks.csv`; every table should say `verified = true`.

The folder name must end in `_Provisional` or `_Final`. The build reads the year (from `2025-26`) and the status from it.

### 3. Add them to the cross-year index

Use version 1's indexer, which updates `..\agent-redesign\data\analysis_catalog.sqlite`. Every table of the new release must have a family there. The build stops and lists any table that has none.

### 4. Change the release list in `config.py`

In `RELEASES`:
- replace last year's provisional line with its final version;
- add the new provisional line.

```python
    ("IPEDS_2024-25_Final", "IPEDS202425.sqlite", 2024),         # was IPEDS_2024-25_Provisional
    ("IPEDS_2025-26_Provisional", "IPEDS202526.sqlite", 2025),   # new
```

There is one line per year, and the year must match the folder name; the build checks both.

### 5. Load the releases

Replace last year's provisional release with its final version:

```bash
python build/build_data.py --release IPEDS_2024-25_Final
```

Add the new provisional release:

```bash
python build/build_data.py --release IPEDS_2025-26_Provisional
```

Each command does the following:
1. Removes every row of that release's year from every table, so a replaced release leaves nothing behind. It does the same for the year's records of cleaning and missing-value reasons.
2. Loads the release, cleaning it with that year's own codebook.
3. Checks that every table has as many rows as its source.
4. Rebuilds the dictionary tables, checking every dictionary rule against the data. If anything does not fit, it stops with a list of problems.

Each command takes about 30 to 35 minutes, most of it the dictionary step, which tests every year. It prints, for example, `IPEDS_2024-25_Final: 56 tables loaded; replaced IPEDS_2024-25_Provisional`.

To rebuild everything from scratch instead (all releases in `config.py`; about 30 minutes for ten years, plus 30 for the dictionary):

```bash
python build/build_data.py
```

The app must not be running against the database while it is rebuilt from scratch, because the rebuild deletes the file first. Stop the chat page, rebuild, then start it again.

### 6. Review the gap list

The stacking report shows what changed:

```bash
python scripts/stack_report.py
```

The every-year rate check compares each rate with the NCES trend files and checks IPEDS's ready-made rates against the counts:

```bash
python scripts/rates_by_year.py
```

It writes to `docs/reports/stage5a/`:
- row counts per table and year against the source;
- columns that change type;
- tables present only in some years;
- variables added, retired or renamed.

You decide what to set up, leave aside, or record as a comparability break. Each change goes into the dictionary folder with a dated line in `dictionary/DECISIONS.md`. When a new release is added, also give it a place in the year rules: `year_meaning.csv` must cover the new year for every table (the build says which do not), and any code IPEDS changed needs `years` (and, where the same information moved, `same_as`) in `category_codes.csv`. Then reload the dictionary (about 30 minutes):

```bash
python build/build_dictionary.py
```

### 7. Tests, benchmarks and the question set

```bash
python -m unittest discover -s tests -v
```

```bash
python scripts/benchmarks.py
```

Add the new year's NCES figures to the benchmarks as known answers. Then rerun the question set, which costs a few cents per run. Run it twice, as agreed for judging wrong readings:

```bash
python scripts/stage4_run.py --yes --model haiku
```

### 8. Release note

Write a short note with:
- how much last year's figures moved between provisional and final;
- what is new;
- any comparability break.

### 9. Publish

Later stage: publish the new database to Render and switch the app over.

## Checking which releases are loaded

```bash
python -c "import sqlite3, config; print(*sqlite3.connect(config.LOCAL_DB).execute('SELECT year, release, status FROM _releases ORDER BY year'), sep='\n')"
```
