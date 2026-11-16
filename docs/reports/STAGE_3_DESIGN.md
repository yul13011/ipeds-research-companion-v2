# Stage 3 design note: the structured request

Nov 16, 2026

This is the design for the question path, for your approval. No Stage 3 code has been written. The request below is the one object that the model fills in and that code reads; everything else follows from it. Four small dictionary additions are needed before it can work, listed at the end.

## The fields of the structured request

| Field | What it holds |
| --- | --- |
| `operation` | One of twelve: lookup, compare, rank, list, breakdown, group_total, group_rate, split, count_schools, school_vs_group, define, data_exists |
| `measures` | A list. Each item is one measure from the shortlist, written `TABLE.VARIABLE`, with an optional `row` (see below). A term reading that shows several measures, such as the cost profile, is several items |
| `schools` | A list of schools. Each has the name as the user wrote it and the ID the model picked from the shortlist, or no ID when the shortlist had no clear match (code then shows the picker) |
| `groups` | A list of group names from the shortlist. A school must be in all of them. Empty means the national universe for a group operation |
| `peers_of` | For "its peers": the school whose comparison group is wanted. Code decides which kind of peers from the `peers` term |
| `condition` | For list: a comparison and a number, such as at least 30. It applies to the first measure |
| `breakdown` | The name of a breakdown set, plus any changed fixed value, such as bachelor's degrees only |
| `split_by` | For split: sector, level or control |
| `sort` | For rank: highest or lowest, and how many |
| `year` | The year as the user stated it, or nothing, plus the kind the user meant if they said (fall, fiscal year, entering cohort, class year). Code turns this into a period using `year_meaning.csv` |
| `topic` | For define and data_exists: the measure, term or outside-IPEDS topic picked from the shortlist |
| `edit` | For a follow-up: a small change to the previous request (add schools, remove schools, replace schools, swap measure, change year, change sort, go back). When present, the other fields hold only what changed. Code applies it to the stored previous request |
| `options` | When the question is ambiguous: two or three complete requests, each with a short label. Choosing one runs it directly |
| `decline` | When nothing fits: the reason, what the model would have asked for, and what was missing (a measure, a group, or a kind of calculation). This goes to the decline log |

Two fields are reserved and not built: `formula` and `category_sets`. They slot in beside `measures` and `breakdown` without changing the other fields.

The model does not write the "Interpreted as" line. Code builds it from the dictionary: the measure's plain name, each group's statement, the term's statement and the period. So nothing in that line can be invented.

## Naming a single category row

A measure in a multi-row table needs to say which row. The `row` part of a measure item does this: it names category columns and codes, picked from category rows in the shortlist.

- **Transfer-in students:** measure `EFA.EFTOTLT`, row `EFALEVEL = 19` ("All students, Undergraduate, Other degree-seeking, Transfer-ins").
- **Bachelor's degrees in computer science:** measure `C_A.CTOTALT`, row `AWLEVEL = 5` and `CIPCODE = 11`.

Code then checks the row. Every category column that keys the table must have exactly one value. A column the request does not name takes its default from the dictionary (first major, in the second example). If a column has no default and the request does not name it, the question gets a clarifying question listing the choices, not a guess. This needs the first dictionary addition below.

## The nine example questions, filled in

**a. "What was Yale's admission rate?"**
operation lookup · measures `DRVADM.DVADM01` · schools Yale (130794) · year not stated.
Code: uses the latest period for that table, fall 2024, and states it.

**b. "Compare six-year graduation rates at RIT, WPI and Drexel."**
operation compare · measures `DRVGR.GBA6RTT` · schools RIT (195003), WPI (168421), Drexel (212054).

**c. "Which public four-year colleges in Texas have the highest retention rate?"**
operation rank · measures `EFD.RET_PCF` · groups "Public, 4-year or above", "State: Texas" · sort highest, 10.
Code: the `retention` term's default is the full-time rate. Missing values are excluded and the answer says how many.

**d. "Show Yale's undergraduate enrollment by race and ethnicity."**
operation breakdown · measures `EFA.EFTOTLT` with row `EFALEVEL = 2` · schools Yale · breakdown "By race and ethnicity".

**e. "What is the graduation rate across all public two-year colleges?"**
operation group_rate · measures `DRVGR.GRRTTOT` · groups "Public, 2-year".
Code: every school in the group is two-year, so the `graduation rate` term's default applies without asking. `rates.csv` gives the counts (completers over adjusted cohort, `GRTYPE` 30 over 29), which are summed and then divided. This needs the second dictionary addition below.

**f. "How many bachelor's degrees by field did Yale award?"**
operation breakdown · measures `C_A.CTOTALT` · schools Yale · breakdown "Degrees by field of study" with `AWLEVEL = 5`.
Code: confirms that the set passed its test at bachelor's degrees, first major.

**g. "How does Front Range Community College compare with its peers on retention?"**
operation school_vs_group · measures `EFD.RET_PCF` · schools Front Range (127200) · peers_of Front Range.
Code: Front Range has its own IPEDS comparison group (36 schools), so the `peers` default applies and is stated. The group figure is a group rate from counts, not an average of school rates.

**h. "Do you have data on AI policies?"**
operation data_exists · topic "Institutional AI policies" (an outside-IPEDS row from the shortlist).
Code: answers "IPEDS does not collect it", with no pointer, because that row names none.

**i. Follow-up to (b): "add Northeastern".**
edit add schools: Northeastern University (167358).
Code: adds the school to the stored request from (b) and reruns it. The shortlist also holds Northeastern's Oakland and Professional Programs campuses; if the model returns no ID, the picker is shown.

## What the model is shown for one question

One call. About 1,400 words in, a short structured reply out.

| Part | Content | Rough words |
| --- | --- | ---: |
| Instructions | The twelve operations with one line each; the request fields; the rules (pick only from the shortlist, never write a number or SQL, return options when ambiguous, decline when nothing fits) | 450 |
| Conversation | The previous structured request, if any, and the user's new message | 80 |
| Measures | Up to 20: ID, plain name or title, table period | 300 |
| Terms | Any matched term with its readings, default and "always ask" flag | 100 |
| Schools | Up to 10 matched: name, city, state, ID, nickname kind | 80 |
| Groups | Up to 15 matched: name and statement | 150 |
| Category rows | Up to 15 matched rows from the shortlisted tables: column, code, label | 120 |
| Breakdown sets | The loaded sets for the shortlisted tables | 60 |
| Outside-IPEDS topics | Up to 5 matched | 60 |

The instructions hold no IPEDS conventions. Whole tables are never shown. The shortlist is a text search built by code over names, synonyms, titles, long descriptions, group words, school names, aliases and nicknames.

## Modules

One per step of the flow, in a folder called `path`, each with its own test file.

| Module | Step | What it does |
| --- | --- | --- |
| `request.py` | all | Defines the structured request, checks its shape, and applies an edit to the previous request |
| `shortlist.py` | 2 | Text search over the dictionary and directory. Code only |
| `interpret.py` | 3 | Builds the prompt, makes the one model call, and reads the reply into a request. The model name is a setting |
| `resolve.py` | 4 | Turns names into schools and groups, applies term defaults and "always ask", fills default rows, checks breakdown sets and periods. Returns a ready request, a clarifying question, a school picker, or a decline |
| `fetch.py` | 5 | One query template per operation. Builds SQL from the ready request and returns rows with their counts and sources |
| `show.py` | 6 | Builds "Interpreted as", the table, warnings, missing-value reasons and "Definitions & sources" from the rows and the dictionary |
| `log.py` | all | Writes the local question log and the decline log |
| `answer.py` | all | Runs the steps in order for one question; the only thing the page calls |
| `app.py` | page | The Streamlit chat page: messages, option buttons, school picker, clear conversation |

## Dictionary additions this design needs

These are conventions, so they are yours to decide. I have not made them.

1. **A default row for each category column.** A new column in `category_codes.csv` marking the one code used when a request does not name that column, such as "first major" or "all students". Without it, most questions about multi-row tables would need a clarifying question.
2. **Which schools each rate row applies to.** A new column in `rates.csv`. The 150% graduation rate now has two rows, four-year and two-year, both pointing at the same ready-made rate. The app needs to know which counts go with which schools.
3. **Defaults for unstated things.** When no year is stated, use the latest period. When no group is stated for a national figure, use the national universe. When "top" has no number, use 10. I would put these three in `terms.csv`.
4. **A guard for rankings.** The plan says rankings need a guard against very small schools. Options: none, a minimum cohort or enrollment size, or showing the count beside each value. Which do you want?

## Other findings since the last report

- **Lifting the one-code-one-set limit did not complicate the loader much:** one extra query and one small table. It does slow the dictionary reload from seconds to about a minute and a half, because the completions table is tested at 3,247 combinations of field and major. Every combination tested adds up.
- **Optional-year tables in this release:** only enrollment by age (`EFB`). Two others looked like candidates and are not:
  - **State of residence (`EFC`):** its title says "(optional)", but the codebook text says it is optional in odd-numbered years. Fall 2024 is a required year, and 5,386 schools reported.
  - **Staff by race and gender (`S_IS`, `S_NH`, `S_OC`):** the codebook says race and gender are optional in even-numbered years. In this release all 5,837 schools reported them and they add up, so I added no caveat. You may know whether that text is out of date.
- **Enrollment by major (`EFCP`)** has 2,186 schools. That is not optional reporting; it is collected for four-year schools and nine fields only, which the term's statement already says.
