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

You decide what to set up, leave aside, or record as a comparability break. Each change goes into the dictionary folder with a dated line in `dictionary/DECISIONS.md`. When a new release is added, also give it a place in the year rules: `year_meaning.csv` must cover the new year for every table (the build says which do not), and any code IPEDS changed needs `years` (and, where the same information moved, `same_as`) in `category_codes.csv`. Then reload the dictionary. For the yearly update, run the full rebuild (about 30 minutes):

```bash
python build/build_dictionary.py --full
```

For a small change between updates, `python build/build_dictionary.py` reruns only what the change affects.

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

## The hosted app (Render), from Part 6f

The Render service `IPEDS-research_companion` (Oregon, 0.5 CPU, 512 MB) has a **4 GB persistent disk** at `/var/data`. It holds one copy of one version's data at a time (owner decision, 2026-11-27):
- version 2's database is 3.27 GB (3.04 GiB);
- version 1's 70 files are 3.13 GB (2.92 GiB);
- both together don't fit.
So switching either way removes the other version's data first. The app returning to the disk downloads its own data again from Hugging Face.

### Version 1's settings (the way back; read from the dashboard, 2026-11-27)

| Setting | Version 1 |
| --- | --- |
| Repository, branch | `yul13011/IPEDS-research_companion`, `main` (live commit `43b994d`) |
| Build command | `pip install -r prototype/requirements.txt` |
| Start command | `streamlit run prototype/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false` (the dashboard shows only the start; copy the full text before the switch) |
| Its environment | `ANTHROPIC_API_KEY`, `IPEDS_DATA_DIR` (its data folder, `/var/data/ipeds` in its runbook), `IPEDS_DATASET_REPO` (`yul13011/ipeds-data`), `IPEDS_GSHEETS_CREDENTIALS`, `IPEDS_QUESTIONS_SHEET`, `PYTHON_VERSION` (`3.11.9` in its runbook; write down the real value before the switch) |
| Auto-Deploy | On Commit |

Version 1's variables stay in place while version 2 runs; version 2 never reads them. **The one shared name is `PYTHON_VERSION`:** version 2 sets it to `3.12.10`, and switching back sets it back.

### Version 2's settings

| Setting | Value |
| --- | --- |
| Build command | `pip install -r requirements.txt` |
| Start command | `python serve.py` |
| `PYTHON_VERSION` | `3.12.10` |
| `IPEDS_V2_DATASET_REPO` | `yul13011/ipeds-v2-data` |
| `IPEDS_V2_DATASET_REVISION` | the dataset commit id |
| `IPEDS_V2_DATA_DIR` | `/var/data/v2` |
| `IPEDS_LOG_DIR` | `/var/data/v2/logs` |
| `IPEDS_DAILY_USD` | `2` |
| `IPEDS_CONVERSATION_QUESTIONS` | `40` |
| `IPEDS_V2_QUESTIONS_SHEET` | version 2's question sheet: its address (not version 1's) |
| `IPEDS_V2_GSHEETS_CREDENTIALS` | secret: the service account's JSON key (version 1's account, the same key as `IPEDS_GSHEETS_CREDENTIALS`) |

### Switching to version 2

The app is unavailable for a few minutes: from removing version 1's data (step 5) until version 2 is live (step 7), about 3 to 6 minutes (download about 1 minute, plus the build).

1. **Environment → Edit:** add version 2's values above, except `PYTHON_VERSION`. Save with **"Save only"**, not a deploy option.
2. **Settings → Build & Deploy:**
   - Source: Edit → `yul13011/ipeds-research-companion-v2`, branch `main`.
   - Build command: `pip install -r requirements.txt`.
   - Start command: `python serve.py`.
   - If a deploy starts by itself, open **Events** and cancel it before going on.
3. **Environment:** change `PYTHON_VERSION` to `3.12.10`, again with **Save only**.
4. **Shell tab** (still version 1's running instance, with the disk attached). Check what's there:

        echo $IPEDS_DATA_DIR
        du -sh /var/data/*
        df -h /var/data

   The first line should print version 1's folder (expected `/var/data/ipeds`), and `du` should show it at about 2.9G.
5. **Still in the Shell:** remove that folder, using the path the first line printed. The app stops answering from here until step 7.

        rm -rf /var/data/ipeds
        df -h /var/data

   `df` should now show at least 3.4G available. If it doesn't, stop and tell Claude before deploying.
6. **Manual Deploy → Deploy latest commit.**
7. **Logs:** `[serve] downloading yul13011/ipeds-v2-data …`, then `downloaded 3.04 GB in … s`, then `index ready`, then the Streamlit lines and Live.
8. Open https://ipeds-research-companion.onrender.com, ask one question, and check that a row appears in version 2's sheet.

### Switching back to version 1

The app is unavailable from step 3 until version 1's data has downloaded, which happens on the **first page view** after the deploy: about 5 to 10 minutes in all. That first visit waits for the 2.92 GiB download, so open it yourself.

1. **Settings → Build & Deploy:** Source back to `yul13011/IPEDS-research_companion`, branch `main`; build and start commands back to version 1's (table above). Cancel any deploy that starts by itself.
2. **Environment:** `PYTHON_VERSION` back to version 1's value, with **Save only**. Version 2's variables can stay.
3. **Shell** (version 2's instance): check, then remove version 2's data, keeping its logs:

        du -sh /var/data/v2/*
        rm -rf /var/data/v2/b97be26c66f5940ec881155ef5dc2667b2737f4d
        df -h /var/data

   Use the folder named after the version in `IPEDS_V2_DATASET_REVISION`. Don't remove `/var/data/v2/logs`.
4. **Manual Deploy → Deploy latest commit.**
5. Open the link yourself and wait while version 1 downloads its data. The page shows a loading state, and the Logs tab shows the download. Then ask a test question.

If version 2's instance won't start (so there's no Shell), deploy version 1 anyway (steps 1, 2, 4). Then open version 1's Shell and remove the v2 folder before opening the page. Version 1's download only starts on the first page view, so there's time to do this.

### Next year's data update (a short outage)

The disk can't hold two versions of version 2's data, and `serve.py` keeps each version in its own folder. So the old copy must be removed before the new one downloads. The app is unavailable for about 3 to 6 minutes.
1. Publish the new database: `.venv\Scripts\python.exe scripts/publish_dataset.py` (needs `huggingface_hub` in `.venv` and your Hugging Face login). It prints the new commit id.
2. **Environment:** set `IPEDS_V2_DATASET_REVISION` to the new id, with **Save only**.
3. **Shell:** `rm -rf /var/data/v2/<old commit id>`, then `df -h /var/data` (at least 3.4G available). Keep `/var/data/v2/logs`.
4. **Manual Deploy.** The new version downloads (about 1 minute) and the app comes back.

The same applies when the 2024-25 provisional release is replaced by its final version.

### The hosted log

Version 2's Google Sheet, one row per turn; the disk log at `/var/data/v2/logs` on the host is the backup.
- Download the sheet as CSV (File → Download → CSV).
- Then `.venv\Scripts\python.exe scripts/hosted_log.py <file.csv>` writes `docs/hosted_questions.csv` (untracked) for choosing new real users' questions.
