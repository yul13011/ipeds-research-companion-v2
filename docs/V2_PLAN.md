# IPEDS Research Companion, version 2: plan

Started Nov 14, 2026 · reorganised Nov 25, 2026, at the end of Stage 5 · @Eva

This is the plan for version 2. It says what version 2 is, how it works, what it must answer, and what is built in each stage. Owner decisions, with their dates and reasons, are in `dictionary/DECISIONS.md`. Each stage's detailed instructions are in its work order, and its results in `docs/reports/`. Section 14 lists where everything is.

---

## 1. Purpose and principles

**Purpose.** Version 2 answers questions about U.S. colleges and universities from IPEDS data, accurately, for institutional researchers and anyone else who uses the data. It replaces version 1, which stays live until version 2 has proved itself. Version 2 is also the base for version 3, a conversational research companion (section 12).

**Priorities.** Accuracy first, then speed, then cost.

**Principles.**

1. **A workflow, not an agent.** Every question goes through the same fixed steps (section 4). The AI does one job: working out what the user means.
2. **The AI never produces a number or writes SQL.** It chooses only from real dictionary entries on a shortlist. The app's own code checks its choices, applies the owner's conventions and produces every figure.
3. **The code decides facts about the data.** Which years are held, whether IPEDS collects something, which schools are in a group: these come from the code and the dictionary, never from the AI's judgment.
4. **Conventions live in one place.** Every IPEDS convention is a row in the `dictionary` folder, with a line in `DECISIONS.md`. Nothing else holds conventions: not code, not prompts, not `CLAUDE.md` (section 5.2).
5. **No rules for one phrasing.** No keyword or regular-expression rules on the user's wording. When a phrasing fails, the fix is in the dictionary, the search or the general design, decided in planning.
6. **Every statement can be checked.** "Interpreted as" is written by code; every figure carries its source; numbers in AI-written text are checked against the table; general knowledge is labelled as such.
7. **No growth by patches.** Changes are planned in chat, written as a work order or change order, and tested before they are built on.

---

## 2. Roadmap at a glance

| Stage | What it delivers | Status |
| --- | --- | --- |
| 1–4 | The first slice: the question path on the 2024-25 release, the dictionary, tests and benchmarks | Done Nov 21, 2026 |
| 5 | All ten years and trends; understanding badly written questions; written summary; explaining terms and concepts | Done Nov 25, 2026 |
| 6 | Fixes found in Stage 5; follow-ups real users need; version 1 features (without the extract builder and chart formatting); hosting; then publishing version 2 at the existing Render link | Next |
| 7 | Flexibility: groups from confirmed lists, the formula field and category sets, comparing and suggesting measures, web search; data extracts; chart formatting; a self-contained data pipeline | After the switch |
| Version 3 | A conversational research companion built on version 2 | After version 2 |

The order of stages 6 and 7 was swapped on Nov 24, 2026: users get version 2, with version 1's features, before the flexibility work, which is not needed to start using it.

---

## 3. How the work is organised

Planning and building are kept apart, so version 2 does not grow by patches.

- **Planning happens in chat.** Ideas, new features and design changes are discussed there first. The outcome is an update to this plan and a written work order or change order.
- **Claude Code builds to the work order.** Its standing instructions: answer questions without changing files; propose instead of build when asked for a new feature; never add a rule for one phrasing.
- **Each part ends with a written report** in `docs/reports/`, reviewed in chat before the next part starts.
- **Testing cadence.** The question set runs once per change order and twice at the end of each part, with a trial API call before every full run. Model readings are judged over two runs against a 90% threshold; path defects must never appear.
- **Building.** A fast incremental build for everyday changes; a full rebuild before every push, at the end of each stage, and for yearly updates.
- **Pushing.** Only after the owner approves a report, after a history check for keys, logs, data and email addresses.
- **Location.** The folder `ipeds-research-companion-v2`, beside version 1, with its own GitHub repository. The database stays in OneDrive. Version 1 and its Google Sheet log are never modified, and tests never write to any shared log.

---

## 4. How the app understands a question

**The principle.** The AI does one job: working out what the user means. It chooses only from real dictionary entries and never produces a number. The app's own code checks its choices, applies the owner's conventions and produces every figure.

### 4.1 Built once, before any question

| Table | What it holds | Where it comes from |
| --- | --- | --- |
| Stacked data tables | Each IPEDS table family stacked across the ten releases, with a year column; multi-row tables loaded whole with their category columns | The ten yearly databases, lined up with the cross-year index. Built entirely by script |
| Measure dictionary | One row per measure: name, definition, unit, years held, what its year means, with companion tables for the counts behind each rate, category codes, and terms with several readings | Drafted by script from each year's codebook, reviewed by the owner |
| School directory | Name, state, sector, level and Carnegie class by year; nicknames and named groups; each school's IPEDS comparison group | The IPEDS directory table for each year, the comparison-group table, and the nickname and group lists |
| Glossary and concepts | The official IPEDS glossary (2025-26 edition, 612 entries) and an owner-reviewed concepts table (26 concepts) | `docs/sources` and the dictionary folder (Stage 5, part 5f) |

### 4.2 The flow

1. **The question arrives.** Long dashes are turned into ordinary hyphens. The app keeps the previous request, so a follow-up edits it.
2. **Find candidates** (code). The search picks about 20 likely measures, plus matching schools, groups, terms, category rows, breakdowns, concepts and glossary entries. This is the shortlist; each item gets a short tag.
3. **Interpret** (one AI call, Haiku). The AI reads the question and the shortlist and fills in a structured request: what to do, which measures, which schools or group, which years. It uses only tags from the shortlist. If the question is ambiguous it offers two or three readings; if nothing fits, it says so.
4. **Check and apply the rules** (code). Code rejects any tag not on the shortlist, decides whether the years are held, and applies the dictionary's conventions in a fixed order: what the user said wins over a chosen reading, which wins over a dictionary default. This is where the app stops to ask, with a school picker or option buttons.
5. **Get the numbers** (code). One query routine per operation.
6. **Show the answer** (code). "Interpreted as", written by code from the dictionary; then the table or single-number tile, notes, warnings, and definitions and sources.
7. **Write a summary** (a second AI call). Two or three sentences about the table. Code checks that every number in it appears in the table, or the summary is dropped. No summary for "what data exists" answers, definitions, declines or clarifying questions.

**Operations.** Look up, compare, trend, rank, list, breakdown, group figure, split by sector or level, count of schools, school against a group, define, and "what data exists". Trends and ranking by change were added in Stage 5.

**The reply format.** The structured request has a fixed shape that the API enforces. In Stage 5 it reached the API's size limit; it was restructured so that "none" is written as an empty value rather than a "value or null" choice, which freed room for the explanation fields and the planned formula field.

### 4.3 Finding the right candidates

The AI can only choose what the search finds. The code steps run on every question and are merged into one shortlist. The AI's own search runs only when nothing on that shortlist fits, and the web search only when that also fails.

| Step | How it's done | What it does | Catches | Status |
| --- | --- | --- | --- | --- |
| Word search | Python code, no LLM | Matches the question's words to dictionary names, synonyms, titles and descriptions, after trimming word endings. A match in a measure's own name counts more than one in its table's title, and one table cannot fill the list | Most questions | Built |
| Synonyms | Owner-reviewed dictionary rows, used by the code | Everyday words added to dictionary entries: undergrad, COA, FT and PT, admit rate | Common shorthand | Built; grows from the logs |
| Misspelling tolerance | Python code, no LLM | Matches words a letter or two off, in measure words and school names | "admisisons", "Yael" | Built (5.0) |
| Meaning search | A small local meaning model | Was to match by meaning, not spelling | — | Evaluated in 5d and **not adopted**: the AI's own search plus dictionary rows did better |
| The AI's own search | LLM, through a function call to the app's search | When nothing fits, the AI rewrites the question in IPEDS terms and searches again, at most twice | Nicknames, abbreviations, indirect phrasing | Built (5d); took the badly written set from 68% to about 95% |
| Web search | LLM, through a function call to web search | When all else fails, learns what an unfamiliar term means; anything found is shown with its source, and a list of schools is confirmed by the user | ROI, AAU members | Stage 7 (section 10) |

**Learning from misses.** Every time the right measure does not reach the shortlist, it is logged; the owner reviews the log and adds missing words as synonyms.

### 4.4 When nothing fits

A question about data the app cannot find gets one of four answers, and the app says which:

1. **Yes.** The matching measures and the years held.
2. **IPEDS collects it, but it is not set up in the app.** Rare since Stage 5, when every measure was set up.
3. **IPEDS does not collect it.** Only when the owner-reviewed `outside_ipeds.csv` lists the topic, with a pointer to another source if it names one.
4. **Not found.** Nothing matched the words used. The app suggests rephrasing or offers the closest matches, and logs a search miss.

A fifth case covers retired variables: "IPEDS collected X from … to …".

The app never decides on its own that IPEDS lacks something: a failed search is not evidence that the data does not exist. When years are not held, the code says so and points to the NCES Data Center. Messages to users are written by code from the dictionary; the AI's own explanation of a decline goes to the log only.

### 4.5 Conventions

What a word means is decided by the dictionary, never by the AI or by code: defaults for terms with several meanings ("graduation rate", "faculty"), terms that always prompt a choice, group definitions ("the Northeast", "state schools", "small"), and what each period means. The AI identifies which term or group the user meant; the dictionary supplies its meaning; "Interpreted as" states it. Every convention sentence shown to users has a test behind it.

### 4.6 Explaining terms

A "what does X mean" question is answered from, in order: the concepts table; the glossary entry, labelled with its edition and followed by the app's own rule for the word; then measure definitions with their period, year caveat and comparability notes. A general explanation from the AI is shown only when none of these covers the word, labelled as not from IPEDS documentation, logged, and never shown if it contains a number. The glossary's Carnegie entries describe the 2000 and 2005 editions and are marked historical. An explanation never says on its own whether IPEDS collects something.

### 4.7 Conversation memory

- **Follow-ups edit the previous request:** "add Northeastern", "now for Texas", "break that down by gender", "go back to all eight".
- **Clarifications are remembered:** "the second one" or "both" is read against the options offered.
- **Declined requests are remembered,** so "show 2023-24" after a declined ten-year question applies to the same school and measure.
- **Declines can be asked about:** "why not?", "where can I find that?", "what can you show instead?".
- **Answer what can be answered:** when part of a request is out of range, the app shows what it has and says what is missing.

Still to come, in Stage 6: follow-ups that refer to schools named several turns earlier, trends that name no measure, and a group plus named schools (section 9.3).

---

## 5. Data and dictionary

### 5.1 The database

`data/ipeds_v2.sqlite`, about 3.3 GB: 59 stacked survey tables keyed by school and year, plus codebook, dictionary, build-result and housekeeping tables. `year` is the release year. Ten releases, 2015-16 to 2024-25; the newest is provisional. The inventory is `docs/DATABASE.md`.

The dictionary sets up all 3,073 IPEDS measures in the ten releases, including 474 retired ones, with the years each is held. Finance lines are paired across the three finance forms where they play the same part.

### 5.2 One home for conventions

Every convention lives in the `dictionary` folder (decided Nov 15, 2026):

- **One plain table per kind of convention:** measures and synonyms, terms, school groups and members, nicknames, rates, category codes, year meaning, outside IPEDS, special codes, measure history, comparability breaks, breakdown exceptions, word abbreviations, the glossary and concepts.
- **One decision log,** `DECISIONS.md`, with a dated line per owner decision and its reason.
- **The model sees only the shortlist** for the current question, never whole tables.

**How a change is made.** Decided in chat, written as a change order; Claude Code changes the row, adds a line to the decision log, rebuilds and runs the tests. Bulk edits, such as many synonyms, are written into the table while Claude Code is idle, then rebuilt and tested.

### 5.3 Groups of schools

| Kind of group | IPEDS source | Examples |
| --- | --- | --- |
| Geography | State, eight BEA regions, locale, metro area, city, county | "in Texas", "New England", "rural colleges" |
| Control, level, sector | Control, level and their combination | "public", "for-profit", "community colleges" |
| Degree level | Degree-granting status, highest degree offered | "doctoral universities" |
| Designations | HBCU, tribal, land-grant, medical school, open admission, fully online, religious affiliation | "HBCUs", "Catholic colleges" |
| Systems | System name | "SUNY schools" |
| Athletic conference | Football conference | "Big Ten", "the Ivy League" |
| Carnegie | 2025 research designation, 2021 basic, 2025 institutional classification | "R1 universities" |
| Size | IPEDS size category | "large universities" |
| Comparison groups | Each school's own IPEDS comparison group | "its peers" |

Words with no exact IPEDS category ("the Northeast", "private", "state schools", "selective", "small") are settled by owner rows in `school_groups.csv`. Groups IPEDS does not flag (Hispanic-serving institutions, women's colleges, flagships, named associations) need a hand-kept list or, from Stage 7, a list the user confirms.

**Membership over time.** Each year counts that year's member schools, as NCES does, unless the user asks for today's schools only (offered as a button under a group trend). Two exceptions use one list for every year: Carnegie groups use their 2024-25 members (decision 6d), and "its peers" is the school's comparison group as of the latest year. The answer states which rule it used.

---

## 6. Question types version 2 should answer

Combined from the real question log, the version 1 evaluation set and example buttons, the Yale benchmark files, the 45 NCES national benchmark tables and owner testing.

### 6.1 Data questions

| # | Type | Example | When |
| --- | --- | --- | --- |
| 1 | Look up one number | "What was Yale's admission rate in fall 2024?" | Built |
| 2 | Compare named schools | "Compare six-year graduation rates at RIT, WPI, Case Western, Stevens, Drexel and Northeastern" | Built |
| 3 | Trend for one school | "How many degrees did Marian University award each year for the last ten years?" | Built (Stage 5) |
| 4 | Trend for several schools | "Show the graduation-rate trend for the Ivies plus MIT and Stanford" | Built for named schools; a group plus named schools in Stage 6 |
| 5 | Rank | "Which four-year colleges have the lowest average net price?" | Built |
| 6 | List schools meeting a numeric condition | "Which New York community colleges have dual-enrolled students as at least 30% of undergraduates?" | Built |
| 7 | List schools by a category fact | "Which Massachusetts colleges offer distance education to undergraduates?" | Built |
| 8 | Yes/no and category facts about a school | "Does Smith College offer academic counseling, career placement, and on-campus childcare?" | Built |
| 9 | Breakdown by subgroup | "Yale's undergraduate enrollment by race and ethnicity" · "Graduation rate for Pell recipients vs non-Pell students" | Built |
| 10 | The counts behind a rate | "How many students were in Yale's 2018 entering cohort, and how many graduated within six years?" | Built |
| 11 | Multi-part profile | "What is the cost of attending Yale?" | Built, as a dictionary term whose reading is several measures (the "cost" profile) |
| 12 | Group total | "Total fall enrollment across all U.S. degree-granting institutions in 2023" | Built |
| 13 | Group rate or average | "What is the full-time retention rate nationally?" | Built, from summed counts |
| 14 | Group figure over time | "How has national fall enrollment changed since 2015?" | Built (Stage 5) |
| 15 | Group figure split by sector or level | "Revenues of public, private nonprofit and for-profit institutions" | Built |
| 16 | Group figure per student | "Core expenses per FTE student at public and private nonprofit institutions" | Built |
| 17 | Count of schools | "How many public four-year institutions are there in 2023?" | Built |
| 18 | School against a group | "How does Front Range Community College compare with other Colorado community colleges?" | Built |
| 19 | Specific sub-populations | "Transfer-in students enrolled in fall 2024" · "Enrollment by age category" | Built |
| 20 | Cohort and class-year framing | "Six-year graduation rate for the 2018 entering cohort" | Built, from the year-meaning table |
| 21 | Custom grouping of categories | Graduation rate for a user-defined set of race and ethnicity categories | Stage 7 (category sets); needs an owner rule for unknown race |
| 22 | Custom calculation across measures | "Rank using equal weighting for net price and graduation rate" | Stage 7 for ratios, differences, percent change and shares (formula field); weighted composites later |
| 50 | Request a data extract | "A spreadsheet of graduation rates for Big Ten schools since 2015, with Carnegie class" | Stage 7 |

### 6.2 Follow-ups

| # | Kind | Example |
| --- | --- | --- |
| 23 | Swap the school | "What about Harvard?" |
| 24 | Add or remove schools | "Add Princeton" · "Just Yale and Harvard" |
| 25 | Restore an earlier scope | "Actually, go back to all eight" |
| 26 | Swap the measure | "Show the number of bachelor's degrees it awarded instead" |
| 27 | Narrow to one measure | "I only need the net price for grant-aided students" |
| 28 | Change the period | "Now plot it from 2015 through 2024 as a trend" |
| 29 | Change the display | "Sort them from lowest to highest" · "Make it a bar chart" (sorting built; chart edits typed in chat are declined until Stage 7, section 10) |
| 30 | Answer a clarifying question | "A" · "yes" · "both" |
| 31 | Two requests in one message | "Which years are available for Ivy League admission rates? Compare the latest available year" (not built: one part is answered; Stage 6, change order 1 (a)) |
| 48 | Respond to a decline by changing the request | "Show 2023-24" · "Use the closest one, then" |
| 49 | Ask about a decline | "Why not?" · "Where can I find that data?" |

Built, apart from items 29 (chart edits) and 31, and the Stage 6 gaps in section 4.7.

### 6.3 Questions about the data

| # | Kind | Example | When |
| --- | --- | --- | --- |
| 32 | Define a measure | "What is the definition of the first-year retention rate?" | Built |
| 33 | What data exists on a topic | "What data do you have on institutional finances?" | Built |
| 34 | Which years are held | "Which years do you have for net price?" | Stage 6, change order 1 |
| 35 | Why IPEDS differs from a school's own figure | Yale's own figures differ from its IPEDS reports in some years | Later; the app states the IPEDS definition and reporting unit |
| 44 | Explain a concept or term | "What does FTE mean?" · "What is an adjusted cohort?" | Built (5f) |
| 45 | Explain how IPEDS measures something, and its limits | "Why doesn't the IPEDS graduation rate count transfer students?" | Built (5f) |
| 46 | Compare similar measures | "Graduation rate or Outcome Measures award rate: which should I use?" | Stage 7 |
| 47 | Suggest measures that fit an intention | "How can I tell how well a college serves low-income students?" | Stage 7 |

### 6.4 Requests to decline or answer with a caution

| # | Kind | Example |
| --- | --- | --- |
| 36 | Data held in another dataset | "Average student loan debt of Yale graduates" · "Best return on investment" |
| 37 | Not collected by IPEDS | "Faculty salary by academic field" · SAT 10th and 90th percentiles |
| 38 | Measure applied to the wrong population | "Average SAT score of Yale's faculty" |
| 39 | Individual records | "List every Yale student's name and GPA" |
| 40 | Year outside the data | "Harvard's graduation rate in 2030" · Yale admissions in 1976 |
| 41 | Data not yet released | "Yale's average net price for 2024-25" |
| 42 | Term with several readings | "How many faculty does Yale have?" |
| 43 | "Peers" without a definition | "Compare RIT's completion rate to its peer institutions" |

All built. Item 40 is decided by the code from the years each measure is held.

---

## 7. New kinds of calculation

The model never writes SQL, so the app answers only questions that fit an operation it has. This is how version 2 stays flexible within that rule.

**What needs no new code.** The request is made of independent parts (operation, measure, schools or group, breakdown, years), so any operation works with any measure and any group. A new measure is a dictionary row; a new group is a row in the groups table; a new combination needs nothing.

**What exists now.** One query template per operation, never one per question; a useful decline naming the closest thing the app can do; a decline log that the owner reviews, from which new operations are added through planning.

**Stage 7.**

- **Formula field.** Simple arithmetic on dictionary measures: a ratio, a difference, a percent change, or a share. Code checks the measures and units and builds the query; for a group, counts are summed before dividing. Covers most of item 22. The reply format has room for it since Stage 5.
- **Category sets.** Several categories of one breakdown combined, with counts summed and the rate recomputed. Covers item 21.

**Later.** Weighted composite rankings, which need each measure put on a common scale first.

**Not planned.** A fallback where the model writes SQL. Revisit only if the decline log shows many questions the additions above cannot reach.

---

## 8. Stages 1 to 5: what was built

Details are in each stage's report in `docs/reports/`.

### 8.1 Stages 1–4: the first slice (2024-25 only)

Done Nov 21, 2026. The question path, dictionary, tests and benchmarks on one release.

- **Known answers.** All covered Yale figures and most NCES figures matched; the rest differed by provisional data or known definitions (graduate assistants in staff counts; administrative offices in average salary).
- **Real questions.** 93% of 102 scored questions right or acceptable on Haiku.
- **Model.** Haiku read as well as Sonnet at about a fifteenth of the cost. Haiku is the default; Sonnet is a setting.
- **Version 1 beside version 2.** On 42 logged questions, version 2 had no errors or empty answers (version 1 had 5) and asked far fewer clarifying questions.

### 8.2 Stage 5: ten years, phrasing, summary, explanations

Done Nov 25, 2026.

| Part | What it did | Result |
| --- | --- | --- |
| 5.0 | Fixes from owner testing: misspellings, "not found", messages written by code, remembered declines, questions about declines, partial answers | 96% |
| 5a | Stacked the ten releases; adding or replacing a release is one tested step (`UPDATING.md`); provisional labels | 554 source tables, 33.5 million rows, stacked into 59 survey tables |
| 5b | Dictionary across years: years held, year rules, changed codes, successors, comparability breaks, directory over time | 83 of 88 rate-years match NCES; national universe exact |
| 5b2 | Set up every measure, including retired ones; finance forms | 3,073 measures, 474 retired |
| 5c | Trends, and ranking by change | 92–93% |
| 5d | Understanding any phrasing: the AI's own search; meaning search evaluated and not adopted | Badly written set from 68% to about 95%; groups 14 of 14 |
| 5e | Written summary with number check; status line; single-number tile; finance pairings | 94.9% and 96.6%; 267 of 278 summaries kept |
| 5f | Explaining terms: glossary (612 entries), concepts table (26), order of sources | All 10 explanation questions answered from the concepts table |
| 5g | Measuring; reply-format restructure; only the code decides which years are held | See below |

**Stage 5 against the success test** (final runs, Nov 25):

| Test | Result |
| --- | --- |
| Benchmarks across ten years | Met: 231 of 251 NCES figures match or are within 0.1%; the rest are the known staff definitions and one provisional figure. Yale: 108 match; the 12 others are years where Yale's own files disagree with its IPEDS report |
| At least 90% right or acceptable, trends included | Met: 91.9% and 92.6% of 149 |
| No false "IPEDS does not collect this" | Met |
| 10 seconds a turn, 20 with a search | 6 and 5 of 236 turns over; median about 6.5 seconds |

Other rows on the scorecard: real users' questions 84.8% (56 of 66); the 118 questions shared with Part 5e 94.1% and 94.9%; badly written set 96.4% and 98.2%. A question-set run costs about $0.26. The question path grew from 2,020 to 3,668 lines (trend step new; resolve.py now 30% of the path); 313 tests.

**Decisions made in Stage 5 that change earlier plans.**

- Meaning search not adopted (5d).
- Speed: 10 seconds a turn, 20 with a search, replacing "typical questions under 5 seconds"; each run reports the median.
- Imputed figures are shown as IPEDS publishes them, without a label; the imputation concept explains this. Revisit if the question log shows users confused by it.
- Every scorecard reports four rows: the full set, real users' questions, the same 118 questions as Part 5e, and the badly written set.

---

## 9. Stage 6: ready for users

**Goal.** Version 2 replaces version 1 at the existing link, https://ipeds-research-companion.onrender.com/, once it does everything version 1 does and passes the switch test (9.7). There is no separate beta link: the existing Render service is switched to the version 2 repository (decided Nov 25, 2026).

### 9.1 Change order 1: fixes found in Stage 5

Proposals in `docs/reports/STAGE_6_CHANGE_ORDER_1_PROPOSALS.md`.

- **(a) Which years are held.** Every "what data exists" answer gets a "Years held" column, naming any gaps; "which years do you have?" is read as that kind of question (item 34).
- **(b) Trends and earlier-year columns.** A trend takes each year from that year's own release. Earlier-year columns inside one table (in tuition, grant aid, net price and cost of attendance) are used only for years the releases don't cover, such as net price before 2015-16, labelled with the release they came from. Where a release's figure and a later revision differ, the year's own release is shown, as in NCES trend tables.

### 9.2 Hosting

- **Hosting.** The existing Render service, switched to the version 2 repository when the switch test is met. The database is published as a separate version 2 dataset on Hugging Face, holding only IPEDS data and the dictionary; version 1's dataset is untouched. Hosting is set up and tested before the switch, so the switch itself is quick and can be reversed.
- **Spending guard.** A daily limit on questions or API spend, with a friendly usage-limit message.
- **Question log.** Version 2's own Google Sheet, separate from version 1's (which is never touched), one row per turn, written only on the host; the disk log stays as the backup. Tests and question-set runs never write to it (owner decision, Nov 27, 2026).
- **Secrets.** The API key is a secret in the host's settings, never in the repository.
- **Labels.** The provisional label on 2024-25 figures (built in 5a; checked again on the host).
- **Speed.** Measured again on the host.
- **After the switch.** New users' questions from the version 2 log are added to the real users' set on the scorecard.

### 9.3 What real users need

Found in Stage 5's real users' questions:

- **A group plus named schools,** such as "the Ivies plus MIT and Stanford" (item 4).
- **Trends that name no measure** ("show a 10-year trend"): ask which figure, instead of "not found".
- **Follow-ups that refer to schools named several turns earlier.**

### 9.4 Version 1 features

| Area | Feature | Status |
| --- | --- | --- |
| Explore IPEDS | Six topic cards, each with a description, a scope note and three example questions | Stage 6 |
| Explore IPEDS | "Ask your own question about…" button into the chat | Stage 6 |
| Ask & Analyze | Chat with follow-up questions and "Clear conversation" | Built |
| Ask & Analyze | Collapsible side panels and menu | A collapsible sidebar with the model selector, summary switch and "Clear conversation" is built; version 1's panels and menu in Stage 6 |
| Ask & Analyze | "Need ideas?" panel with topic dropdown and example questions | Stage 6 |
| Ask & Analyze | Staged status line while working | Built (5e) |
| Answers | "Interpreted as", school picker, clarifying questions, declines with pointers, "what data do you have", definitions | Built |
| Answers | Written summary | Built (5e) |
| Results | Table, single-number tile, underlying counts and data status, warnings, definitions and sources | Built |
| Results | "Display table" switch | Stage 6 |
| Results | Downloads: Excel with sources, CSV | Stage 6 (6c); the technical audit file moves to Stage 7 (owner decision, Nov 26, 2026: launch first) |
| Charts | Automatic line or bar chart in the owner's palette and fonts | Built (5c): a line over the years for a trend, bars for a one-year comparison, in version 1's palette and font |
| Charts | "Format chart" panel, chart edits typed in chat, preview and download as PNG or SVG | Left out until Stage 7 (owner decision, Nov 26, 2026) |
| Tools | Definitions browser | Built in 6b; hidden with the whole analysis tools panel until Stage 7 (owner decision, Nov 27, 2026; an approved difference from version 1) |
| Tools | Extract builder | Left out until Stage 7, with data extracts (owner decision, Nov 25, 2026) |
| About | Model selector, AI switch, privacy note, benchmark match rates | Model selector and written-summary switch built (sidebar); the rest Stage 6 |
| Behind the scenes | Question log | Disk log; on the host, also version 2's own Google Sheet (9.2) |
| Behind the scenes | Data download on the host; friendly error and usage-limit messages | With hosting (9.2) |

### 9.5 Data extracts

Moved to Stage 7 (section 10.1) on Nov 25, 2026, to be built after version 2 is published. Version 1's extract builder is not carried over in the meantime.

### 9.6 Before version 1 is retired

Moved to Stage 7 (section 10.3) on Nov 26, 2026. Until then, version 2 still uses version 1's converter and cross-year index to add a release, so version 1's data folder must be kept.

### 9.7 The switch test

The Render link is switched to version 2 when all of these hold:

1. The version 1 features above are in place, except the extract builder, chart formatting, the technical audit file and the analysis tools panel with the definitions browser (Stage 7).
2. The success test from Stage 5 is met (Part 6b's two runs).
3. Real users' questions are at least 90% right or acceptable (Part 6b's two runs).
4. Version 2 runs on the host without unresolved errors. Owner decision, Nov 26, 2026 (launch first): there is no separate test service. The live service is switched and tested straight after, with one full question-set run against the live app, and switched back if needed (version 1's data stays on the disk).
5. The speed limits are met on the host: 10 seconds a turn, 20 with a search, including the first answer after the app has been idle.
6. The owner has tested the hosted app with 10 to 15 questions of her choosing.

A few days after the switch, version 2's hosted log is reviewed for errors, slow turns and wrong readings, and any fixes go into one change order.

The existing Render service is switched to the new repository; it is never deleted. Version 1's repository and data stay as they are, so the switch can be reversed.

---

## 10. Stage 7: flexibility, data extracts, chart formatting and the data pipeline

- **Groups from a list the user confirms,** which the web search depends on.
- **The formula field and category sets** (section 7).
- **Comparing similar measures and suggesting measures for a goal** (items 46 and 47). These need "use when" and "limits" notes on about 100 key measures, drafted for the owner to review.
- **Web search to understand unfamiliar questions,** the last step of the search ladder (section 4.3), with the safeguards in section 4.4. Confirmed web lists and reviewed topics are added to the dictionary over time, so web search becomes a way to find what to add, not a permanent source.

| Area | Examples | What the search does |
| --- | --- | --- |
| Unfamiliar terms and jargon | ROI, summer melt, stop-outs, swirl, DFW rate, gainful employment, the 90/10 rule | Learns the meaning, then checks whether an IPEDS variable measures it |
| Topics outside IPEDS | Earnings, student debt, campus crime, athletics budgets, research spending | Confirms IPEDS does not cover it and finds where the data lives (College Scorecard, Clery data, EADA, NSF HERD) |
| Fields of study | STEM, data science, nursing, pre-med | Finds the official field codes behind the term |
| School names | Mizzou, Ole Miss, SCAD, renamed or merged schools, foreign universities | Finds the official name, or establishes the school is not in IPEDS |
| Groups of schools | AAU members, Public Ivies, Hispanic-serving institutions, Jesuit colleges, COFHE | Finds a membership list to propose, with its source |
| Staff and student categories | Adjuncts, TAs, postdocs, non-traditional students | Maps the term to the nearest IPEDS category |
| Figures from other sources | U.S. News graduation rates, Common Data Set acceptance rates | Explains how that definition differs from IPEDS |
| Policies and events | Test-optional schools, the Pell expansion, schools that closed this year | Works out what is meant and what IPEDS can show |

When web search explains a topic that `outside_ipeds.csv` does not list, the app says it found no IPEDS variable for it, says what IPEDS does cover, and logs the topic for review. Pointers to other sources found on the web are labelled as unreviewed.


### 10.1 Data extracts

Moved from Stage 6 on Nov 25, 2026. Users download data for their own research, asking in plain language or through a builder panel (item 50):

- **One row per school,** or per school and year, with the IPEDS ID and name.
- **The requested measures,** following the same dictionary rules as answers: right periods, missing values blank, never zero.
- **School characteristics the user picks** (sector, control, level, state, city, region, Carnegie class, size, system), from the directory for the same year as the data.
- **A documentation sheet:** each column's definition, period and source table, notes, the group definition used, and the date produced.

The extract uses the same code that builds answers, so an extract and an on-screen answer always agree. To decide when built: the layout for several years, the format (Excel, CSV, or both), and limits for very large requests.


### 10.2 Chart formatting

Moved from Stage 6 on Nov 26, 2026: version 1's "Format chart" panel (layout, text, style and axes tabs, presentation preset, undo and reset), chart edits typed in chat sharing settings with the panel (follow-up item 29), and preview and download as PNG or SVG in slide layouts. The automatic chart is already built.


### 10.3 A self-contained data pipeline

Moved from Stage 6 on Nov 26, 2026. Bring the Access-to-SQLite converter and the cross-year index into version 2, with a tested way to add a new release to the index, so version 2 no longer depends on version 1's data folder. **Deadline:** before the next IPEDS release is added (section 11) and before version 1's folder is removed.

### 10.4 Moved from Stage 6 to publish sooner

Owner decision, Nov 26, 2026: version 2 is published as soon as possible; everything not needed for launch waits for Stage 7.
- **The faculty question:** a question naming "instructional staff" still asks which reading is meant. Proposed fix in the resolve step (`docs/reports/STAGE_6_B_DECISIONS.md`, item 1).
- **Log 4.6:** a trend with no figure keeps the previous request's school and operation (`resolve.no_measure`). Proposed fix in the same report, item 2, with removal of Part 6a's instruction line.
- **The 73 expectations that name no schools or no measure,** and the grader's `operation` column and `none` marker (same report, item 3; `docs/reports/STAGE_6_EXPECTATION_GAPS.csv`).
- **A review of the instruction prompt** (2,496 words against the 2,500 limit).
- **Extra question-set runs:** before launch, Part 6b's two runs stand; one full run is made against the live app after the switch.
- **The technical audit file download** (version 1's third download).
- **The analysis tools panel and the definitions browser:** hidden (Nov 27, 2026); the code is kept and turned on with `config.TOOLS_PANEL`.

---

## 11. Keeping the app up to date

Each year IPEDS publishes the provisional data for the newest year and the final data for the year before, which replaces its provisional release. The app is updated each time.

1. Download the new releases from NCES (Access databases).
2. Convert them to SQLite.
3. Add them to the cross-year index.
4. In the settings file, replace last year's provisional release with its final version and add the new provisional release.
5. Run the build. It cleans each year with that year's codebook and checks every dictionary rule against the data, stopping with a list of problems if anything does not fit.
6. The owner reviews the gap list: new variables, changed codes, new comparability breaks. Each change goes into the dictionary with a line in `DECISIONS.md`.
7. Run the tests and benchmarks, adding the new year's NCES figures as known answers, and rerun the question set.
8. Write a release note: how much last year's figures moved between provisional and final, and what is new.
9. Publish the new data to the host and switch the app over.

**All years are kept;** there is no rolling window. The database grows by about 300 MB a year. Adding or replacing a release is one tested step, written up in `UPDATING.md`. The owner's work is mainly the review in step 6: a day or two a year, longer when IPEDS redesigns a survey.

---

## 12. Version 3 and later items

### 12.1 A research companion

**The aim.** Version 2 is an accurate lookup tool. Version 3 is a conversation partner for anyone using data to inform education decisions: researchers, higher-education professionals, IT staff in education, graduate students. Users can talk through a research idea, ask what IPEDS can and cannot tell them, and have results explained. It should feel as conversational as a general AI assistant, with one difference: every statement about data is grounded in IPEDS.

**Feasibility.**

| Piece | Feasibility | Notes |
| --- | --- | --- |
| Natural, flexible conversation | High | What language models do best |
| Every number grounded in IPEDS | High, if enforced in code | Code checks every number in AI-written text against data results |
| Knowing what IPEDS has and lacks | Medium-high | Depends on dictionary coverage and the search |
| Flexible analyses | Medium | Limited by the set of tested operations, which grows from the logs |
| Explaining and interpreting results | Medium | General knowledge must be labelled; no causal claims from IPEDS data |

**How it is built: the workflow becomes the toolbox.**

1. **A conversational layer** that discusses, explains, asks, proposes analyses and interprets results, likely on a stronger model.
2. **Grounded tools, the only way the AI touches data or makes claims about IPEDS:** data tools (version 2's operations, later research operations), knowledge tools (what IPEDS has, the glossary, outside IPEDS, comparability breaks, year rules), and context tools (web search, labelled).
3. **Grounding enforced in code:** every number must match a data tool's result; claims about what IPEDS has must come from the knowledge tools; every figure carries its source.
4. **Three kinds of statement, visibly distinct:** IPEDS data, IPEDS documentation, and general context.
5. **Multi-step analyses shown as a plan** for the user to confirm.
6. **The fast path stays** for quick lookups.

**Built on version 2, not rebuilt.** It lives in the same repository, as a new phase with its own stages and work orders. Reworking needed: operations wrapped as tools; results carrying their source; possibly a chat page beyond Streamlit; memory, logging, cost limits and sign-in for a public audience.

**Habits in version 2 that keep version 3 easy** (standing rules since Stage 5):

1. Each operation is a clean function with structured input and output, and no chat-page code inside it.
2. Every result carries its source: table, year, definition and statements.
3. The number check is a general component that can check any AI-written text against any result.
4. "What data exists" is a self-contained step that can be called on its own.
5. Logs record a conversation identifier with each turn.

**Risks.** Fluent but wrong answers; descriptive results read as causal; harder testing; cost and access at scale.

### 12.2 Later items, not yet scheduled

- **Why a value is missing.** Load the per-figure IPEDS flags (the "X" columns, about 1,500 per release) so the app can say whether a blank is not applicable or not reported, tell an implied zero from a real zero, and label imputed figures one by one. A change to the data build and a full rebuild.
- **Explaining differences from a school's own figures** (item 35).
- **Weighted composite rankings.**
- **Tidying `resolve.py`,** now 30% of the question path, if it keeps growing.

---

## 13. Background: why version 2 was a rebuild

Decided Nov 14, 2026, from the version 1 assessment (`docs/V1_ASSESSMENT.md`).

- **The repair plan ended in a rebuild anyway.** Its later steps replaced most of the code between the question and the data, inside code with two engines, six fetch paths and hidden shared state.
- **Most defects sat in code that would be replaced.**
- **The code that failed users was the bulk of the code.** In the real question log, 10 of 37 free-form data questions got a number; several of the failures were answerable by one simple query.
- **The owner needs to be able to follow it.** About 9,500 dense lines with rules buried in keyword patterns is hard to direct; a small core with IPEDS rules held in tables can be checked by an institutional researcher.

**Carried over from version 1:** the ten yearly databases, the cross-year index, the 48 reviewed measures, named groups and nicknames, the IPEDS rules (rewritten as tables), the Yale and NCES benchmarks, the evaluation set and the real question log; the chart and local question logging (built in Stage 5), and exports and the page layout (Stage 6). **Left behind:** both interpreters, the catalog planner, most fetch engines, the keyword validators and the per-year ID scheme.

**How version 2 maps to version 1.** FAQ exact match → saved requests behind example buttons. Resolver, school-name call, keyword shortcuts and plan chooser → one AI call. Reviewed measures versus catalog plans → one measure dictionary. Catalog planner → not rebuilt; added only if the decline log shows demand. Validators reading the question's wording → rules read from the dictionary. Six fetch paths → one per operation.

---

## 14. Where to find things

| What | Where |
| --- | --- |
| Owner decisions | `dictionary/DECISIONS.md` |
| Conventions | `dictionary/` (README explains each table) |
| Work orders | `docs/STAGE_1-4_WORK_ORDER.md`, `docs/STAGE_5_WORK_ORDER.md` |
| Reports | `docs/reports/` |
| Database inventory | `docs/DATABASE.md` |
| Adding a release | `UPDATING.md` |
| Version 1 assessment | `docs/V1_ASSESSMENT.md` |
| Sources (glossary, IPEDS overview) | `docs/sources/` |
| Test sets | `docs/test_questions.csv`, `docs/owner_questions.csv`, `docs/stage4/`, the badly written set; the raw question log stays untracked |
