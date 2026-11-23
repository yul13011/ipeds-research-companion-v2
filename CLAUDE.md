# IPEDS Research Companion, version 2

A chat app that answers plain-English questions about U.S. colleges from federal IPEDS data.
This folder is the first slice of version 2: one year only (the 2024-25 release), built to
measure how well the new question path works before building further.

The owner is a statistician and former institutional researcher: strong in R, moderate in SQL,
not a software engineer. Explain decisions in plain language.

The full work order is in `docs/STAGE_1-4_WORK_ORDER.md`. The design is `docs/V2_PLAN.md`.
Owner decisions are in `dictionary/DECISIONS.md`.

## How we work

- Planning happens outside this session. `docs/V2_PLAN.md` is the design. Build to it; do not redesign it.
- If the owner asks a question or wants to talk something through, answer and stop. Do not change any file unless the owner says "go".
- If the owner asks for a new feature or a change in behaviour, do not build it. Write a short proposal: which step of the flow and which table it touches, and what it would cost. Then wait.
- No special-case patches. If a question is answered wrongly, the fix belongs in a dictionary table or in the general step, with a test. Never add a rule for one phrasing.
- After each stage, write a report to `docs/reports/STAGE_<n>.md`: what was built, test results, line counts, open questions. The owner takes that report away for review before work continues. Stop after each stage.

## One home for conventions

- The `dictionary` folder is the only source of conventions: measures and synonyms, terms, school groups, group members, nicknames, rates, category codes, year meaning, topics outside IPEDS, special codes. `dictionary/README.md` explains each table and column.
- No convention lives in code, in prompts, in this file or in any other file. If a convention is needed and no row covers it, do not guess: ask the owner.
- The build loads the folder into the database. The model is only ever shown the shortlist for the current question, never whole tables.
- Breakdowns use only the named, tested sets in `category_codes.csv` and `measures.csv` (`breakdown_set`). A breakdown with no loaded set is declined and logged. Draft sets are not used until the owner approves them; `dictionary/DECISIONS.md` says which are approved.
- A change to any convention comes from the owner as a change order. Then: change the row, add a dated line to `dictionary/DECISIONS.md`, rebuild, run the tests, and report.
- If the owner says a table was edited directly: rebuild and run the tests, and report what the build's checks found.
- The review workbook and the script that converted it are in `docs/archive`. Never read them for conventions and never re-run the script.

## Read first, in this order

1. `docs/V2_PLAN.md`: why we are rebuilding, the version 2 structure, the 43 question types, the test results, the version 1 feature list, and the decisions that need the owner's input.
2. `docs/V1_ASSESSMENT.md`: what was wrong with version 1. Do not repeat those patterns.
3. `dictionary/README.md` and `dictionary/DECISIONS.md`: the conventions and the decisions behind them.
4. `docs/test_questions.csv`: real user questions, with conversation number and turn order. Part of the test set.
5. `docs/reports/`: the stage reports so far.

## Where things are

- This folder is the new project. Build everything here. It is its own git repository; do not change anything in the outer repository.
- Version 1 is at `..\agent-redesign`. READ-ONLY. Never edit, move or delete anything there.
- The data is at `..\agent-redesign\data`. Read the 2024-25 database in place at `data\annual\IPEDS_2024-25_Provisional\IPEDS202425.sqlite` and the cross-year index at `data\analysis_catalog.sqlite`. Do not copy the 3 GB of data into this folder or into git.
- The local slice database is `data\ipeds_v2.sqlite`. It is untracked and rebuilt by the build.
- `docs/question_log.csv` is the raw question log. It is untracked; do not copy session IDs or times out of it.
- Version 1's benchmarks are at `..\agent-redesign\Test cases` and `..\agent-redesign\evaluations` (`run_nces_aggregate_benchmarks.py`, `run_yale_benchmarks.py`, `eval_set.py`). Reuse their reference values and specifications, not their pipeline code.

## Stages

1. Data tables. 2. Dictionary and directory. 3. The question path (steps 2 to 6 of the flow). 4. Measure it.
Details of each stage, the slice scope, and what is not in the slice are in `docs/STAGE_1-4_WORK_ORDER.md`.

## Rules

- The model never writes SQL and never produces a number. Every figure comes from a query built by code from the structured request.
- No keyword or regular-expression rules that read the user's wording to decide meaning. Meaning comes from the one model call; rules come from the dictionary tables.
- IPEDS knowledge lives in the dictionary tables, not in code.
- One clear module per step of the flow. Keep the whole question path small enough for the owner to read; report the line count after each stage.
- Write a test for each piece as it is built, and run the tests before reporting a stage as done.
- Missing values are never treated as zero. Rankings exclude missing and non-positive values where a positive value is expected, and say so.
- The table `_missing_reasons` is for display only ("not applicable" or "not reported" for one school). It must never enter a calculation.
- Logging: write each question, the structured request, the outcome and the time taken to a local log file, and each decline to the local decline log. Do not write to the version 1 Google Sheet. Tests must never write to any shared log.
- Never commit secrets. The API key stays in an environment variable or an untracked secrets file. Data files and secrets are in `.gitignore`.
- Do not commit or push unless the owner says to.
- If something in `V2_PLAN.md` turns out not to work against the real data, stop and tell the owner before changing the design.
- The structured request is made of independent parts (operation, measure, schools or group, breakdown, year). Any operation must work with any measure and any group. Never write a template for one whole question. Shape it so a formula field and category sets can be added later as new fields.

## Running things

- Full build (ten releases: data, cleaning, dictionary, directory; about an hour): `python build/build_data.py`. One release: `python build/build_data.py --release <folder>` (see `UPDATING.md`).
- Reload the dictionary after a change to any table except `special_codes.csv`: `python build/build_dictionary.py` reruns only what the change affects (seconds for wording, minutes for a measure or a table's category rows). One table on its own: `--table <name>`. Everything: `--full` (about 30 minutes; required before each part's final report and for every yearly update).
- Run the tests: `python -m unittest discover -s tests -v`
- Run the chat page: `streamlit run app.py` (needs `ANTHROPIC_API_KEY` set; the model is `IPEDS_MODEL`, default Sonnet)
- Live smoke test, only with the owner's approval (it costs money): `python scripts/smoke_test.py --yes`
- Cadence (owner decision, 2026-11-23): use the fast build path for routine changes; run a full rebuild (`--full`) only before a push to GitHub, at the end of each stage, and for yearly updates (its result must match the fast path, as tested). Run the question set on Haiku once per change order (`python scripts/stage4_run.py --yes --model haiku`), and twice only at the end of a part, when the scorecard is judged.
- The question path is in `path/`, one module per step: request, shortlist, interpret, resolve, fetch, show, log, answer.
