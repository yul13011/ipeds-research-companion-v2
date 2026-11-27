# Stage 6, Parts 6f and 6c: hosting and downloads (before the switch)

## In short

- Version 2 is ready to switch: the dataset is published, the start-up, spending guard, log download and downloads are built, and the tests pass. What's left is the Render steps (yours), then the run against the live app.
- **Launch first (owner decision, 2026-11-26):** everything not needed for launch is in plan section 10.4 (Stage 7).

## What was built

- **The dataset `yul13011/ipeds-v2-data`** (public): `ipeds_v2.sqlite` (3.27 GB), its SHA-256 file and a README.
  - **Version:** `b97be26c66f5940ec881155ef5dc2667b2737f4d`.
  - **Upload:** 52 s, with `huggingface_hub` in `.venv` only. You were already signed in, so no sign-in step was needed.
  - **No local paths:** before uploading, the `_releases` table's file paths, which held your Windows user folder, were made relative (`annual/<release>/<file>`), in the build and in the local database. Nothing reads that column.
  - **Yearly update:** `scripts/publish_dataset.py` (see `UPDATING.md`).
- **`serve.py`, the start command on the host:**
  - downloads the fixed dataset version once onto the disk and checks its checksum;
  - builds the search index and shortlists the Explore examples in the background, in the same process the page uses;
  - starts Streamlit.
  - Locally: index ready in 3.6 s, warm-up done in 7.6 s, and the page loaded.
  - **Changed from the proposal:** the warm-up shortlists the examples but doesn't fetch their data, because there are no stored requests for them. The run on the host will show whether the first answer still needs more.
  - **Variable names:** version 2's data variables are named `IPEDS_V2_…`, because version 1 already uses `IPEDS_DATA_DIR` and `IPEDS_DATASET_REPO` on the same service. Switching back then needs no edits.
- **The spending guard:**
  - **Daily limit:** spend is added up from every model call (the question and the summary) in `spend.json` beside the log, and resets at midnight Eastern.
  - **Per conversation:** counts typed questions; "Clear conversation" starts a new count.
  - **When a limit is reached:** the approved message, no model call, and a log line (`limit_daily`, `limit_conversation`).
  - Off locally, on through the host's variables.
- **The owner's log download:** About → Owner → passphrase → a zip of the log files. It's shown only when `IPEDS_OWNER_PASSPHRASE` is set; the passphrase is compared in constant time. `scripts/hosted_log.py` turns the log into scorecard rows without session codes or times.
- **Part 6c, downloads:** "Download Data" under each answer with a table, as in version 1:
  - **Excel:** sheets Data, Underlying counts (when there are any), Notes and Sources;
  - **CSV.**
  - Both are made from the answer's own page object when clicked, so the summary is included. Version 1's formula guard is kept (`tools/downloads.py`, adapted from version 1's `exports.py`; rewritten for version 2's page object).

## Tests

- **12 new (11 in `tests/test_launch.py`, 1 in `tests/test_app.py`):**
  - downloads for a trend, a group figure and a breakdown match the screen cell for cell, and their notes and sources match too;
  - the formula guard;
  - the two limits, with no model call;
  - a new day starts at zero;
  - the download checked and done once, and a wrong checksum keeps nothing;
  - the log zip and the hosted-log rows;
  - on the page, "Download Data" shows and the daily-limit message appears.
- **The full suite:** 387 tests, all passing.
- **The real download:** fetching the published dataset with `serve.ensure_data` took 58 s for 3.27 GB on this connection, and the checksum matched.

## Line counts

- **The question path:** 4,049 lines (+48: the guard in `answer.py`, the spend in `log.py`, a lock in `shortlist.py` so the warm-up and a first question never build two indexes).
- **The page and tools:** 784 lines.
- **New outside them:** `serve.py` 86, `tools/downloads.py` 77, `scripts/hosted_log.py` 49, `scripts/publish_dataset.py` 46.
- **The instruction prompt:** 2,496 words against the 2,500 limit (unchanged).

## Not done yet

- The switch (your Render steps).
- After it: one full question-set run against the live app; speed, including the first answer after idle; your 10 to 15 question checklist.
