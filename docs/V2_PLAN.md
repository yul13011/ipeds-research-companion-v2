# IPEDS Research Companion: rebuild or repair

Nov 14, 2026 · @Eva

Recommendation: build a new app around the good parts of the current one, and keep the current app live until the new one proves itself. This replaces the "repair in a set order" advice in the full code assessment.

## Why rebuild instead of repair

The repair route ends in a rebuild of the middle of the app anyway, and doing that inside the current code is harder than doing it beside it.

- **The repair plan ends in a rebuild.** Its later steps (a new fast path, then one school-name resolver, one year reader, one search, one result shape) replace most of the code between the question and the data. Inside the current code, each step has to work around two engines, six fetch paths and hidden shared state.
- **Most of the defects sit in code that would be replaced.** Fixing 23 issues in the interpreters and the planner is effort spent on parts that do not survive.
- **The code that fails users is the bulk of the code.** In the real question log, 10 of 37 free-form data questions got a number. Four of the questions the app failed on were answered by one simple query each against the 2024-25 data.
- **The owner needs to be able to follow it.** About 9,500 dense lines, with rules buried in keyword patterns, is hard to direct or review. A small core with IPEDS rules held in tables can be checked by an institutional researcher.

## What carries over and what does not

| Carries over | Left behind |
| --- | --- |
| The ten yearly databases | Both interpreters (`intent_router`, `resolver_v2`) |
| The cross-year index in `analysis_catalog` | The catalog planner |
| The 48 reviewed measures, the named groups and school nicknames | Most of the fetch engines |
| The IPEDS rules (fiscal years, cohort timing, missing values), rewritten as tables | The keyword validators |
| Charts, exports, the page layout and question logging | The per-year ID scheme |
| The Yale and NCES benchmarks, the evaluation set, and the real question log as the test of "done" |  |

## How to keep the risk down

1. **Leave the current app live.** Apply only the few cheap fixes: the blocked "add X" and peer comparisons, the discarded retry, the discovery setting, and tests writing to the real-user log.
2. **Build the new core beside it.** Start with one year (2024-25) and the question types in the list below.
3. **Switch over on evidence.** The new app replaces the old one when it answers more of the 37 logged questions, faster, and passes the benchmarks.
4. **Rare questions get a quick "not supported yet" at first.** Add a planner back only if the question log shows demand.

**The main cost.** Rare, multi-row questions that the current planner sometimes answers will be unavailable for a while.

## Version 2 structure

Version 2 has one path for every question, with one model call before the data and one after. This is a design sketch; it has not been built or tested.

### Built once, before any question

Three tables do the work that the catalog planner does live today.

| Table | What it holds | Where it comes from |
| --- | --- | --- |
| Stacked data tables | Each IPEDS table family stacked across the ten years, with a year column. This includes the multi-row tables, loaded whole with their category columns | The ten yearly databases, lined up using the cross-year index in `analysis_catalog`. Built entirely by script |
| Measure dictionary | One row per measure: plain-English name, definition, unit, years available, what its year means (fall, fiscal, cohort). It has three companion tables: the counts behind each rate; every category code with its label and whether it is a total or a part; and terms that have several readings, with a default | Drafted by script from the codebook tables inside each database, then reviewed by the owner. This is where the IPEDS rules live |
| School directory | Name, state, sector, level and Carnegie class by year; nicknames and named groups such as the Ivy League; and each school's own IPEDS comparison group | The IPEDS directory table for each year, the comparison-group table, and the existing nickname and group lists |

### The seven steps a question goes through

Steps 3 and 7 call a model. The other five are code only.

1. **Question arrives.** The app keeps the previous request as a structured object, so "add Harvard" edits that object.
2. **Shortlist** (code only). A text search of the measure dictionary and the school directory finds the 20 or so most likely measures and any school names.
3. **Interpret** (model call). The model picks from the shortlist and returns one structured request: the operation, the measures, the schools or a group, and the years.
   - If the question is ambiguous, it returns two or three complete options. Picking one runs it directly.
   - If the data is not in IPEDS, it declines and says where the data lives.
4. **Resolve and check** (code only). Code turns names into schools, with the picker when a name is unclear, and applies the rules in the measure dictionary.
   - Anything the measure table does not cover gets a quick, specific reply and is logged, so the owner can see what to add.
5. **Fetch** (code only). One query per operation type against the measure table.
6. **Show table and chart** (code only). The table, chart and sources appear as soon as the data is back.
7. **Write summary** (model call). The summary streams in under the table and is checked against the rows.

### How version 2 maps to version 1

| Version 1 | Version 2 |
| --- | --- |
| FAQ exact match | Example buttons become saved requests; no separate layer |
| Resolver, school-name call, keyword shortcuts, plan chooser | Step 3, one model call |
| Reviewed measures versus catalog plans | One measure dictionary |
| Catalog planner, up to 8 model calls | Not in the first version; added later only if the question log shows demand |
| Validators that read the question's wording | Step 4, rules read from the measure dictionary |
| Six fetch paths | Step 5, one |

**Operations supported first:** lookup, compare, trend, rank, group figure, list schools matching a condition, define a measure, and "what do you have on X".

## Question types version 2 should answer

This list combines four sources: the real question log, the version 1 evaluation set and example buttons, the Yale benchmark files, and the 45 NCES national benchmark tables. "Addition" in the last column refers to the design additions listed at the end.

### Data questions

| # | Type | Example | Source | Version 2 |
| --- | --- | --- | --- | --- |
| 1 | Look up one number | "What was Yale's admission rate in fall 2024?" | Evaluation | First version |
| 2 | Compare named schools | "Compare six-year graduation rates at RIT, WPI, Case Western, Stevens, Drexel and Northeastern" | Question log | First version |
| 3 | Trend for one school | "How many degrees did Marian University award each year for the last ten years?" | Question log | First version |
| 4 | Trend for several schools | "Show the graduation-rate trend for the Ivies plus MIT and Stanford" | Question log | First version |
| 5 | Rank | "Which four-year colleges have the lowest average net price?" | Question log | First version |
| 6 | List schools meeting a numeric condition | "Which New York community colleges have dual-enrolled students as at least 30% of undergraduates?" | Question log | First version |
| 7 | List schools by a category fact | "Which Massachusetts colleges offer distance education to undergraduates?" | Evaluation | Addition A |
| 8 | Yes/no and category facts about a school | "Does Smith College offer academic counseling, career placement, and on-campus childcare?" | Evaluation | Addition A |
| 9 | Breakdown by subgroup | "Show Yale's undergraduate enrollment by race and ethnicity" · "Graduation rate for Pell recipients vs non-Pell students" | Evaluation, Yale benchmark | Addition B |
| 10 | The counts behind a rate | "How many students were in Yale's 2018 entering cohort, and how many graduated within six years?" | Yale benchmark | Addition C |
| 11 | Multi-part profile | "What is the cost of attending Yale?" (sticker price, components and net price together) | Evaluation | First version, as a saved bundle |
| 12 | Group total | "Total fall enrollment across all U.S. degree-granting institutions in 2023" | Evaluation, NCES | First version |
| 13 | Group rate or average | "What is the full-time retention rate nationally?" · "Average Pell grant for undergraduates" · "Graduation rate across all public two-year colleges" | NCES, question log | Addition C |
| 14 | Group figure over time | "How has national fall enrollment changed since 2015?" | NCES | First version for totals; Addition C for rates |
| 15 | Group figure split by sector or level | "Revenues of public, private nonprofit and for-profit institutions" · "Graduation rate at 4-year, 2-year and less-than-2-year institutions" | NCES | Addition C |
| 16 | Group figure per student | "Core expenses per full-time-equivalent student at public and private nonprofit institutions" | NCES | Addition C |
| 17 | Count of schools | "How many public four-year institutions are there in 2023?" | Evaluation, NCES | First version |
| 18 | School against a group | "How does Front Range Community College compare with other Colorado community colleges?" | Question log | First version for totals; Addition C for rates |
| 19 | Specific sub-populations | "How many transfer-in students enrolled in fall 2024?" · "First-time students who enrolled within 12 months of high school" · "Enrollment by age category" | NCES | First version; multi-row tables are loaded whole |
| 20 | Cohort and class-year framing | "Six-year graduation rate for the 2018 entering cohort" · "SAT scores for the Class of 2027" | Evaluation, Yale benchmark | First version, from the dictionary's year-meaning field |
| 21 | Custom grouping of categories | Graduation rate for under-represented minority students, a grouping the user defines | Yale benchmark | Next stage after the first slice, through category sets; needs an owner rule for students of unknown race |
| 22 | Custom calculation across measures | "Rank using equal weighting for net price and graduation rate" | Question log | Next stage after the first slice for ratios, differences, percent change and shares, through the formula field; weighted composite rankings later |

Examples marked NCES or Yale benchmark are phrased from the benchmark tables, which hold figures and titles, not user questions.

### Follow-ups

| # | Kind | Example | Source |
| --- | --- | --- | --- |
| 23 | Swap the school | "What about Harvard?" | Evaluation |
| 24 | Add or remove schools | "Add Princeton" · "Just Yale and Harvard" | Evaluation |
| 25 | Restore an earlier scope | "Actually, go back to all eight" | Evaluation |
| 26 | Swap the measure | "Show the number of bachelor's degrees it awarded instead" | Evaluation |
| 27 | Narrow to one measure | "I only need the net price for grant-aided students" | Evaluation |
| 28 | Change the period | "Now plot it from 2015 through 2024 as a trend" | Evaluation |
| 29 | Change the display | "Sort them from lowest to highest" · "Make it a bar chart" | Evaluation |
| 30 | Answer a clarifying question | "A" · "yes" · "both" | Question log |
| 31 | Two requests in one message | "Which years are available for Ivy League admission rates? Compare the latest available year" | Example button |

All of these are first-version items, because the previous request is kept as a structured object that a follow-up edits.

### Questions about the data

| # | Kind | Example | Source |
| --- | --- | --- | --- |
| 32 | Define a measure | "What is the definition of the first-year retention rate?" | Evaluation |
| 33 | What data exists on a topic | "What data do you have on institutional finances?" | Evaluation |
| 34 | Which years are available | "Which years do you have for net price?" | Example button |
| 35 | Why IPEDS differs from a school's own figure | Yale's own published figures differ from IPEDS in 13 of 242 benchmark comparisons, as recorded in the project's design notes; IPEDS reports Yale University, not Yale College | Yale benchmark |

Items 32 to 34 are first-version items answered from the measure dictionary. Item 35 is later; the first version can state the IPEDS definition and reporting unit.

### Requests to decline or answer with a caution

| # | Kind | Example | Source |
| --- | --- | --- | --- |
| 36 | Data held in another dataset | "What is the average student loan debt of Yale graduates?" · "Which colleges have the best return on investment?" | Evaluation, question log |
| 37 | Not collected by IPEDS | "Faculty salary by academic field" · "How many nonbinary faculty does Smith employ?" · SAT 10th and 90th percentiles | Evaluation, Yale benchmark |
| 38 | Measure applied to the wrong population | "What is the average SAT score of Yale's faculty?" | Evaluation |
| 39 | Individual records | "List every Yale student's name and GPA" | Evaluation |
| 40 | Year outside the data | "Harvard's graduation rate in 2030" · Yale admissions in 1976 · national graduation rates before 2015 | Evaluation, Yale and NCES benchmarks |
| 41 | Data not yet released | "What is Yale's average net price for 2024-25?" | Evaluation |
| 42 | Term with several readings | "How many faculty does Yale have?" · "What is the average faculty salary at Yale?" (medical school in or out) | Evaluation |
| 43 | "Peers" without a definition | "Compare RIT's completion rate to its peer institutions" | Question log |

Items 36 to 43 are first-version items. Items 40 and 41 are answered from the dictionary's years-available field, and item 42 from dictionary entries that flag a term as having several readings.

### Design additions these question types imply

Three additions to the version 2 structure are needed to cover the list above. All three are now part of the structure described earlier, along with loading the multi-row tables whole and using each school's IPEDS comparison group for "peers" (item 43).

- **Addition A: coded answers.** The measure table must hold category answers with their labels (yes/no, calendar system, services offered), not only numbers. Needed for items 7 and 8.
- **Addition B: measure families.** The dictionary must group related measures (by race, by gender, by Pell status, by rank, by full-time and part-time), so a request for a breakdown returns the whole set. Needed for item 9.
- **Addition C: counts behind every rate.** For each rate or average, the dictionary must name the numerator and denominator counts, or the count used as a weight. Group rates are then computed by summing counts across schools, which is how the NCES benchmark script does it, not by averaging school rates. Needed for items 10, 13 to 16 and 18.

### Left for later

- Custom groupings of categories (item 21) and custom calculations across measures (item 22) are not in the first slice. They are planned for the stage after it; see "Staying open to new kinds of questions". Weighted composite rankings stay later.
- Explaining differences from a school's own published figures (item 35).
- Nothing else is excluded by design. Any question still needs its measure named in the dictionary.

### Topics that need dictionary entries

These are covered by the types above but each needs its measures entered in the dictionary before version 2 can answer them.

- Library collections, 12-month enrollment and eight-year outcome rates.
- Faculty salaries by rank, and staff counts.
- Finance figures by fiscal year, which use different forms for public, private nonprofit and for-profit schools.
- SAT percentiles and ACT submitters.
- Cost of attendance and some financial aid measures, which moved to different tables in 2024-25. A ten-year trend for these depends on lining the old and new tables up first.

### What was and was not checked

- The Yale benchmark files cover enrollment by level, admissions, SAT percentiles, graduation rates and graduation rates by subgroup.
- The NCES files are 45 national tables covering institution counts, enrollment, staff, salaries, finance by sector, graduation and retention rates, completions, financial aid, admissions and tuition.
- The national universe used by the benchmark script is the 50 states and DC, Title IV institutions.
- Whether every example above can be answered from the data in all ten years has not been checked. Each needs its measure confirmed in the dictionary.

## Evidence and likelihood

Version 2 is expected to answer 40 of the 43 question types. The three it will not answer at first are items 21, 22 and 35. Items 21 and 22 are planned for the stage after the first slice. This is a judgment backed by tests on one year of data, not a measured success rate.

### Tests on the 2024-25 data

Each row is one simple query of the kind version 2 would run. All ran in under 0.2 seconds.

| Type | Test | Result |
| --- | --- | --- |
| Group rate | National full-time retention | 0.7786; NCES 0.779 |
| Group rate | National part-time retention | 0.4695; NCES 0.469 |
| Group rate | National admit rate | 0.5904; NCES 0.59 |
| Group rate | National yield | 0.1939; NCES 0.194 |
| Group rate from a multi-row table | Four-year graduation rate within 150% of normal time | 0.6096; NCES 0.61 |
| Group rate from a multi-row table | Bachelor's six-year rate | 0.6477; NCES 0.648 |
| Split by sector | Bachelor's six-year rate by control | 0.638 public, 0.682 private nonprofit, 0.340 for-profit |
| Group total | Applications received | 14,751,867; exact match |
| Group total | Fall enrollment | 20,066,904; exact match |
| Sub-population | Transfer-in undergraduates, national | 1,277,289; exact match |
| Sub-population | First-time degree-seeking students, national | 3,066,637; exact match |
| Breakdown | Yale undergraduates by race | Nine categories summing to 6,814 |
| Breakdown | University of Michigan salary by rank | All seven ranks returned |
| Category fact | Smith's counseling, placement and childcare | Returned with labels |
| List by category | Massachusetts schools with undergraduate distance education | 86 schools |
| Peers | RIT's IPEDS comparison group | Eight schools; 2,845 of 6,072 schools have a group |
| Count of schools | Title IV institutions | 5,692; NCES 5,626, a mismatch to resolve |
| Rank | Lowest net price, four-year | Ran, but the top result is a negative value |
| Totals check | Full-time plus part-time undergraduates equals the undergraduate total | True at all 4,055 schools |

### Still unproven

- **The interpretation step.** Choosing the right measure and reading follow-ups depends on the model. This is where version 1 struggled most.
- **The other nine years.** Only 2024-25 was tested. Trends depend on the years lining up.
- **Per-student group figures, finance by school type, and staff tables.** Not tested.
- **Rankings.** They need guards against odd values and very small schools.

## Where the owner's input is needed

The scripts draft everything from the codebook. These are the decisions the codebook cannot make. Each comes to the owner as a draft to correct.

1. **Plain-English names and synonyms** for the measures users ask about most.
2. **Defaults** when a term has several candidates: "graduation rate", "net price", "enrollment", "faculty".
3. **Terms that should always prompt a choice,** seeded from the traps version 1 found.
4. **The counts behind each rate,** seeded from the 48 reviewed measures and the NCES benchmark script.
5. **Totals versus parts in category columns,** proposed from labels and checked against the data.
6. **What a year means for each table:** fall, fiscal year, cohort or class year.
7. **Which institutions count in national figures.**
8. **What to do when a definition changed between years:** break the trend or bridge it.

## Next steps

1. The owner reviews the draft dictionary workbook.
2. Claude Code builds the first slice for 2024-25 only: stacked tables, dictionary, and steps 2 to 6 of the flow, without the written summary.
3. Run the 37 logged questions and the NCES and Yale benchmarks through the slice.
4. If it clearly beats the current app, extend to all ten years and add the summary. If not, stop and review.
   - The same stage adds the formula field and category sets, guided by the decline log from the first slice.
5. The current app stays live throughout, with only the few cheap fixes applied.

## Version 1 features and when version 2 gets them

Every version 1 feature is kept. The first slice includes only what is needed to measure whether the new question path reads questions correctly. The rest is carried over from version 1 after the slice passes.

| Area | Feature | When |
| --- | --- | --- |
| Explore IPEDS | Six topic cards, each with a description, a scope note and three example questions | Later |
| Explore IPEDS | "Ask your own question about…" button into the chat | Later |
| Ask & Analyze | Chat with follow-up questions and "Clear conversation" | First slice |
| Ask & Analyze | Collapsible side panels and menu | Later |
| Ask & Analyze | "Need ideas?" panel with a topic dropdown and clickable example questions | Later |
| Ask & Analyze | Staged status line while working | Later |
| Answers | "Interpreted as" line | First slice |
| Answers | Written summary, with a plain fallback | Later |
| Answers | School picker for unclear names | First slice |
| Answers | Clarifying questions with option buttons | First slice |
| Answers | Declines for data not in IPEDS, with a pointer elsewhere | First slice |
| Answers | "What data do you have on X" and definition answers | First slice |
| Results | Table | First slice |
| Results | "Display table" switch and single-number tile | Later |
| Results | "Show underlying counts and data status" | First slice |
| Results | Warnings for provisional data and missing values | First slice |
| Results | "Definitions & sources" | First slice |
| Results | Downloads: Excel with sources, CSV, technical audit file | Later |
| Charts | Automatic line or bar chart in the owner's palette and fonts | Later |
| Charts | "Format chart" panel with layout, text, style and axes tabs, presentation preset, undo and reset | Later |
| Charts | Chart edits typed in chat, sharing settings with the panel | Later |
| Charts | Preview and download as PNG or SVG in slide layouts | Later |
| Tools | Extract builder and definitions browser | Later |
| About | Model selector, AI switch, privacy note, benchmark match rates | Later |
| Behind the scenes | Question log | First slice, to a local file, not the version 1 sheet |
| Behind the scenes | Data download on the host; friendly error and usage-limit messages | Later |

The chart, export and page code works from finished result rows, so it should carry over with modest adaptation. This has not been tested.

## Questions about what data exists

A question such as "do you have data on X?" gets one of three answers, and the app says which.

1. **Yes.** The app names the matching measures and the years available.
2. **IPEDS collects it, but it is not set up in the app yet.** The app says so plainly.
3. **IPEDS does not collect it.** The app says so, and points elsewhere only when the "Outside IPEDS" tab of the dictionary workbook names a source. Example: return on investment points to College Scorecard; AI policies has no source to point to.

The workbook's measure list covers every IPEDS variable in the release, so a topic with no match there is case 3. Pointers come from the owner-reviewed tab, never from the model's general knowledge.

## How the work is organised

Planning and building are kept apart, so version 2 does not grow by patches.

- **Planning happens in chat.** Ideas, new features and design changes are discussed there first. The outcome is an update to this plan and a written work order.
- **Claude Code builds to the work order.** Its standing instructions tell it to answer questions without changing files, to propose instead of build when asked for a new feature, and never to add a rule for one phrasing.
- **Each stage ends with a written report** in `docs/reports/`, which goes back to chat for review before the next stage starts.
- **Location.** A new folder, `ipeds-research-companion-v2`, beside the current one, and a new GitHub repository. The existing Render link is kept by switching the existing service to the new repository when version 2 is ready; the old service is never deleted.

## Groups of schools

Users often ask about a group, such as "schools in the Northeast", "all public institutions" or "two-year public colleges". The school directory carries the IPEDS columns that define these groups, and the "School groups" tab of the dictionary workbook lists them with the words users are likely to use.

| Kind of group | IPEDS source | Examples |
| --- | --- | --- |
| Geography | State, eight BEA regions, locale, metro area, city, county | "in Texas", "New England", "rural colleges" |
| Control, level, sector | Control, level and their combination | "public", "for-profit", "community colleges" |
| Degree level | Degree-granting status, highest degree offered | "doctoral universities" |
| Designations | HBCU, tribal, land-grant, medical school, open admission, fully online, religious affiliation | "HBCUs", "Catholic colleges" |
| Systems | System name (436 systems) | "SUNY schools" |
| Athletic conference | Football conference (98 conferences) | "Big Ten", "the Ivy League" |
| Carnegie classes | 2025 research designation, 2021 basic, 2025 institutional classification | "R1 universities" |
| Size | IPEDS size category | "large universities" |
| Comparison groups | Each school's own comparison group; the NCES-assigned group | "its peers" |

**Words with no exact IPEDS category.** These need an owner decision, recorded in the same tab: "the Northeast" and other Census-style regions (IPEDS uses BEA regions), "liberal arts colleges", "private" (with or without for-profit), "state schools", "selective", and cut-offs for "small" and "large".

**Not in IPEDS.** Hispanic-serving institutions, other minority-serving designations beyond HBCU and tribal, women's colleges, flagship universities, and named associations are not flagged. Each needs either a hand-kept list or a rule the owner sets.

## Staying open to new kinds of questions

The rule that the model never writes SQL means the app answers only questions that fit an operation it has. This section sets out how version 2 stays flexible within that rule. None of it has been built or tested.

**What needs no new code.** The structured request is made of independent parts: operation, measure, schools or group, breakdown and year. Any operation works with any measure and any group.

| What is new in the question | What it takes |
| --- | --- |
| A new measure | A row in the measure dictionary |
| A new group of schools | A row in the school groups table, or conditions on directory columns given in the request |
| A new combination of operation, measure, group and breakdown | Nothing |
| A new kind of calculation | The additions below, or a new operation |

**In the first slice.**

- **Parts, not whole-question templates.** There is one query template per operation, never one per question.
- **A useful decline.** When no operation fits, the app says so and names the closest thing it can do.
- **A decline log.** Each decline records the question and what the model wanted to ask for. The owner reviews it, and new operations are added from that evidence, through the planning process, not as patches.

**In the stage after the first slice.**

- **Formula field.** The request may ask for simple arithmetic on dictionary measures: a ratio, a difference, a percent change, or a share of a total. Code checks that the measures exist and the units make sense, and builds the query. For a group, counts are summed before dividing. Covers most of item 22.
- **Category sets.** The request may name several categories of one breakdown to combine, such as a user-defined set of race and ethnicity categories. Code sums the counts and recomputes the rate. Covers item 21, once the owner sets the rule for students of unknown race.

**Later.** Weighted composite rankings, such as "rank using equal weighting for net price and graduation rate". These need each measure put on a common scale first, which is a design decision of its own.

**Not planned.** A fallback where the model writes SQL for questions that do not fit. Those answers would be the ones nobody has tested. This can be revisited if the decline log shows many questions the additions above cannot reach.

## One home for conventions

Every IPEDS convention the app uses lives in one folder, `dictionary`, at the top level of the project. Decided Nov 15, 2026.

- **One plain table per kind of convention:** measures with their synonyms, terms and their meanings, school groups, group member lists, the counts behind each rate, category codes, year meaning, topics outside IPEDS, and codes that mean missing.
- **One decision log,** `dictionary/DECISIONS.md`, with a dated line for each owner decision and its reason.
- **The Excel workbook was a review draft.** It is converted into these tables once and then archived. It is not a second source.
- **Nothing else holds conventions:** not code, not prompts, not `CLAUDE.md`. The database copies are rebuilt from the folder.
- **The model sees only the shortlist for the current question,** never whole tables. Code applies the rule for whatever the model picks.

**How a change is made.** A change is decided in chat and written as a short change order. Claude Code changes the table row, adds a line to the decision log, rebuilds the database and runs the tests. Claude Code is the only editor of project files. The exception is a bulk edit, such as drafting many synonyms, which is written into the table directly while Claude Code is idle and then rebuilt and tested.
