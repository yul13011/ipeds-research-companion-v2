# Claude Code prompt: build the first slice of version 2

Paste everything below the line into Claude Code, opened in this project folder (`ipeds-research-companion-v2`).

Before pasting, make sure the `docs` folder holds: `V2_PLAN.md`, `V1_ASSESSMENT.md`, `dictionary_review.xlsx` and `question_log.csv`.

---

You are building the first slice of version 2 of the IPEDS Research Companion, a chat app that answers plain-English questions about U.S. colleges from federal IPEDS data. I am the owner: a statistician and former institutional researcher, strong in R, moderate in SQL, not a software engineer. Explain decisions to me in plain language.

HOW WE WORK
- Planning happens outside this session. docs/V2_PLAN.md is the design. You build to it; you do not redesign it.
- If I ask a question or want to talk something through, answer and stop. Do not change any file unless I say "go".
- If I ask for a new feature or a change in behaviour, do not build it. Write a short proposal: which step of the flow and which table it touches, and what it would cost. Then wait.
- No special-case patches. If a question is answered wrongly, the fix belongs in a dictionary table or in the general step, with a test. Never add a rule for one phrasing.
- After each stage, write a report to docs/reports/STAGE_<n>.md: what you built, test results, line counts, open questions. I take that report away for review before you continue.
- First task before Stage 1: create CLAUDE.md in this folder containing these working rules and the RULES section below, so every later session starts with them.

READ FIRST, IN THIS ORDER
1. docs/V2_PLAN.md: why we are rebuilding, the version 2 structure, the 43 question types, the test results, the version 1 feature list with what belongs in this slice, and the decisions that need my input.
2. docs/V1_ASSESSMENT.md: what was wrong with version 1. Read it so you do not repeat those patterns.
3. docs/dictionary_review.xlsx: my reviewed decisions. This is the source of truth for names, defaults, rates, category totals, year meanings, the national universe, topics outside IPEDS, and school groups.
4. docs/question_log.csv: real user questions. These are part of the test set.

WHERE THINGS ARE
- This folder is the new project. Build everything here.
- Version 1 is at ..\agent-redesign. Treat it as READ-ONLY. Never edit, move or delete anything there.
- The data is at ..\agent-redesign\data. Read the 2024-25 database in place at data\annual\IPEDS_2024-25_Provisional\IPEDS202425.sqlite and the cross-year index at data\analysis_catalog.sqlite. Do not copy the 3 GB of data into this folder or into git.
- Version 1's benchmarks are at ..\agent-redesign\Test cases and ..\agent-redesign\evaluations (run_nces_aggregate_benchmarks.py, run_yale_benchmarks.py, eval_set.py). Reuse their reference values and specifications, not their pipeline code.

SCOPE OF THIS FIRST SLICE
One year only: the 2024-25 release. The goal is to measure how well the new question path works before building further.

In this slice:
- A plain chat page (Streamlit, as in version 1) with follow-up questions and a way to clear the conversation.
- An "Interpreted as" line showing how each question was read.
- A results table, with an option to show the underlying counts and data status.
- Warnings for provisional data and missing values.
- "Definitions & sources" for each result: scope, period, definition, calculation and source tables.
- A school picker when a name is unclear.
- Clarifying questions with option buttons; choosing an option runs that option directly.
- Declines for data not in IPEDS, and answers to "what data do you have on X" and "define X".

Not in this slice (they come later, carried over from version 1): charts and the Format chart panel, chart edits by chat, chart and data downloads, the written summary, the Explore IPEDS page, the "Need ideas?" panel, the extract builder, the About page, trends across years. Also not in this slice, planned for the next stage: a formula field (ratio, difference, percent change, share of total across measures) and category sets (combining several categories of one breakdown). Do not build them now, but shape the structured request so they can be added as new fields without restructuring it.

BUILD, IN FOUR STAGES. STOP AND REPORT TO ME AFTER EACH STAGE.

Stage 1. Data tables.
- Write a build script that creates one local database for the slice containing every 2024-25 IPEDS data table with a year column added, including the multi-row tables with their category columns. Structure it so the other nine years can be stacked in later.
- Check row counts against the source and report them.

Stage 2. Dictionary and directory.
- Load docs/dictionary_review.xlsx into tables: measures; the counts behind each rate; category codes with total-or-part flags; terms with several readings and their defaults; year meaning per table; the national universe definition; topics outside IPEDS; school groups.
- Build the school directory from the HD table: name, state, sector, level, control, Carnegie class, plus nicknames and named groups carried over from version 1 (prototype/catalog.py) and each school's comparison group from the CUSTOMCGIDS table. Add the grouping columns listed in the workbook's "School groups" tab (region, sector, control, level, locale, size, HBCU, tribal, land-grant, Carnegie classes, system, religious affiliation, open admission, athletic conference), so a user can name a group such as "public two-year colleges in the Southeast" and the app filters on those columns. Use my decisions in that tab for words with no exact IPEDS category, such as "the Northeast" or "liberal arts colleges".
- Where the workbook is missing a decision you need, do not guess. List the gaps and ask me.

Stage 3. The question path. Steps 2 to 6 of the flow in V2_PLAN.md.
- Shortlist: a text search over the measure dictionary and school directory. Code only.
- Interpret: ONE model call that picks from the shortlist and returns one structured request: operation, measures, schools or a group filter, years as the user stated them plus the kind of year, and any edit to the previous request. If the question is ambiguous it returns two or three complete options.
- The structured request is made of independent parts (operation, measure, schools or group, breakdown, year). Any operation must work with any measure and any group. Never write a template for one whole question.
- Resolve and check: code turns names into schools and applies the dictionary rules. Anything not covered gets a quick, specific reply and is logged.
- When no operation fits the question, decline plainly, name the closest thing the app can do, and write a row to a decline log: the question, what the model wanted to request, and what was missing (a measure, a group, or a kind of calculation).
- Fetch: one query template per operation. Operations for this slice: lookup, compare, rank, list schools meeting a condition, breakdown by category, group total, group rate (sum the counts, never average school rates), split a group figure by sector or level, count schools, school against a group, define a measure, what data exists on a topic.
- Show: the items listed under "In this slice".
- Keep the previous request as a structured object so follow-ups (add a school, swap the measure, narrow, go back) edit it.

Questions about what data exists ("do you have data on X?"). Give one of three answers, and say which:
  1. Yes: name the matching measures from the dictionary and the years available.
  2. IPEDS collects it but it is not set up in this app yet: say so plainly.
  3. IPEDS does not collect it: say so, and point elsewhere ONLY if the "Outside IPEDS" table in the workbook names a source. Never invent a source or a pointer from general knowledge.
The full measure list in the workbook covers every IPEDS variable in the release, so a topic with no match in it is case 3, not case 2.

Stage 4. Measure it.
- Tests against known answers: reproduce the 2024 values in the NCES benchmark files and the test table in V2_PLAN.md, and the 2024 Yale benchmark values.
- Run every question in docs/question_log.csv and the single-year questions in version 1's eval_set.py through the path. For each, record: the structured request the model produced, whether the measure and schools were right, the answer, and the time taken.
- Give me a scorecard: how many got a correct answer, a correct decline, a clarifying question, or a wrong reading. List every wrong reading with the question and what went wrong.
- Summarise the decline log: declines grouped by what was missing, so I can see which additions would unlock the most questions.

RULES
- The model never writes SQL and never produces a number. Every figure comes from a query built by code from the structured request.
- No keyword or regular-expression rules that read the user's wording to decide meaning. Meaning comes from the one model call; rules come from the dictionary tables.
- IPEDS knowledge lives in the dictionary tables, not in code.
- One clear module per step of the flow. Keep the whole question path small enough for me to read; tell me the line count after each stage.
- Write a test for each piece as you build it, and run the tests before reporting a stage as done.
- Missing values are never treated as zero. Rankings exclude missing and non-positive values where a positive value is expected, and say so.
- Logging: write each question, the structured request, the outcome and the time taken to a local log file, and each decline to the local decline log. Do not write to the version 1 Google Sheet. Tests must never write to any shared log.
- Never commit secrets. The API key stays in an environment variable or an untracked secrets file. Add data files and secrets to .gitignore before the first commit.
- Do not commit or push unless I tell you to.
- If something in V2_PLAN.md turns out not to work against the real data, stop and tell me before changing the design.

START by reading the four documents, then tell me your understanding of the task in a few sentences, list anything unclear, and wait for my go-ahead before creating CLAUDE.md and starting Stage 1.
