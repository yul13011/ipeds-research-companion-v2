# Stage 5, part 5b2: set up every measure

Date: 2026-11-23. Decisions are recorded in `dictionary/DECISIONS.md` under "2026-11-22: Part 5b approved; decisions on the Part 5b report" and the two headings before it. Working files are in `docs/reports/stage5b2/`.

## Summary

- **Every measure is set up:** all 3,073 in `measures.csv`, the 474 retired variables included. The 2,311 new ones were drafted from rules (unit, period, reporting form). Checked against the 762 measures you set up by hand, the rules give the same unit for all 685 numbers and the same period for 761 of 762 periods. The one difference is an error in my own Part 5b conversion, now fixed (below).
- **Build checks confirm every set-up measure in every year it exists.** They flag 124 measures for your review. Another 6 units the rules could not decide, so the review list has 130 measures (`stage5b2/review_list.csv`). There is no list of the rest to review.
- **The faster build is in place:**
  - no change: 1 second;
  - a wording change: 1 second;
  - a one-measure change: about 1 minute;
  - the full rebuild: 34 minutes (90 minutes on the slower final run).

  Five tests confirm that each kind of change leaves the database exactly as a full rebuild would.
- **The full rebuild confirms the 92 relabelled breakdown results:**
  - all 118 results that read "no data" with nothing tested (the 92 among them) come out the same;
  - of all 2,478 breakdown results in that export, 2,477 match;
  - the one change is completions by race in 2021-22, now loaded with its two approved exceptions, as you decided.
- **The full question set, run twice on Haiku: 90.4% and 89.6% right or acceptable** (104 and 103 of 115), against 97.4% in the last Part 5.0 run. This is the decline the work order expected, with three causes (below). Two of them recur in both runs and need your decision.
- **One path defect appeared and is fixed:** a breakdown that named no school and no group stopped with an error. It now takes the default group, the national universe, like every other group figure. A test covers it.
- **Tests:** 204 run: 201 pass, and 3 are marked as known failures until Part 5d, because their measures no longer reach the shortlist.

## Part 5b decisions applied

| Decision | Done |
| --- | --- |
| Breaks approved | All 14 rows are `approved`. |
| New hires | Your wording: "IPEDS changed the hiring window for new hires; its documentation gives different first years, from 2016-17 to 2020-21." Attached from 2016-17. |
| Enrollment by major (EFCP), CIP 2020 | **No break added:** EFCP has the same 9 field codes, with the same labels, in 2018-19 and 2020-21. |
| Finance, fiscal 2020 | The scholarships row now covers F1A, F2 and F3: all three forms carry the same codebook sentence and gained the same discounts-and-allowances lines in fiscal 2020. **No pandemic-relief revenue line exists:** no column was added to any finance form in fiscal 2020, 2021 or 2022 apart from those lines, and no codebook title or description mentions CARES, HEERF, relief or coronavirus. So no revenue context note is added. |
| Pandemic note | Attached by period: new columns `period_from` and `period_to` (2020-03 to 2022-06), with no table restriction. Your wording: "Figures covering 2020 to 2022 reflect the COVID-19 pandemic period." Part 5c works out each figure's period from the table's year rule. |
| Row 13 | Approved. A context row for F1C19OT ("The 2016-17 finance changes may have shifted what is counted as other expenses.") was added with the F1C195 successor. |
| Outcome Measures total, 2015-16 and 2016-17 | New `sum_of` column in `category_codes.csv`: the default "total entering" row in those years is codes 1-4 added together. The build finds it in both years (4,105 and 3,998 schools). |
| Completions by race, 2021-22 | New file `breakdown_exceptions.csv`, listing Alhambra Beauty College and Cinta Aveda Institute. They are not parent or child campuses, so the campus rule could not cover them. The set is tested without them and is now loaded for 2021-22; Part 5c shows their totals with a note. The 4 failures were 4 rows: 2 schools at 2 award levels. |
| Successors | 39 approved, 6 rejected (new status `rejected`; their message says "It is no longer collected."). Nothing is left to review. |
| DRVOM percents | **Confirmed and approved:** the 2016-17 codebook says the 2008 cohort was measured "at 8 years (August 31, 2016)", the same 8-year status point as the 2017-18 redesign. Break row 1 applies. None rejected. |
| Unique names | Build check `name_clashes`: 474 names are shown for more than one measure, covering 1,259 measures. See open question 3. |

## The faster build

`python build/build_dictionary.py` now compares a fingerprint of each dictionary file, and of each loaded release, with the last build (`build/changes.py`), and reruns only what the change affects:

| Change | What reruns | Time on the real database |
| --- | --- | ---: |
| Nothing | nothing | 1 s |
| Wording only: messages, term wording, statements, outside-IPEDS rows, nicknames, breaks, the wording columns of measures and category rows | reload, with no data checks | 1 s |
| Synonyms | as wording; the app notices the new fingerprint and rebuilds its search index, with no restart | 1 s |
| A measure's other columns | that measure's links, breakdown-set columns, years and checks | about 1 min (61 s; 74 s to undo) |
| Category codes, breakdown exceptions, or a table's parent-and-child rule | that table, in the affected years | about 1-3 min per year |
| School groups or members | the directory and groups | about 2 min |
| A new or replaced release | that year's full checks | about 2 min, plus groups |
| `--table terms` | that one table on its own; other changes wait for the next run | |
| `--full` | everything | 34 min (90 min on a slow run) |

- **A full rebuild is still required** before each part's final report and for every yearly update. `CLAUDE.md`, `UPDATING.md` and the dictionary README say so.
- **If a build stops part way, the next run is a full rebuild,** so a half-finished state is never taken as finished.
- **The equivalence tests** (`tests/test_dictionary.py`, `FasterBuild`) run five kinds of change on a two-year made-up database: wording, category codes, a measure, a replaced release, and one table on its own. Each compares every dictionary and result table with a full rebuild, row for row. Building them caught two real differences, both fixed before the test passed:
  - a measure that stopped being a count kept its old breakdown results;
  - the loader tests relied on a full build.
- **Measuring it on the real database found one more slow step:** the first one-measure change took 10.5 minutes, 625 seconds of it rerunning all the measure checks. They now recheck only the measures, tables and years a change touched.

## Setting up every measure

`scripts/setup_draft.py` drafted the 2,311 measures, reading only the codebook's own wording:

| Unit | New measures |
| --- | ---: |
| count | 703 |
| dollars | 679 |
| average (a per-school figure that can't be added: prices, charges, averages, per-student amounts) | 411 |
| coded | 382 |
| percent | 80 |
| none (text, ID numbers, test-score percentiles, map coordinates) | 56 |

The rules for units:
- a coded variable is `coded`;
- a line on a finance form (which has a reporting form) is `dollars` unless its title says percent or ratio;
- otherwise the title is read first, then the description, against ordered rules: not a quantity, "number of", percent, ratio, recipients and cohorts, per-school figures, dollars, counts.

The other drafts:
- **Period:** a year range in the title (2021-22) that differs from the table's period becomes the measure's period, counted from the release it appeared in. A single year in a title is a cohort or a classification edition and sets no period.
- **Finance forms:** the reporting form comes from the table, or from the derived table's variable name.

**A correction to Part 5b.** Checking the period rule found 113 period cells, all in the cost and aid tables, written as "{Y-3}-22" instead of "{Y-3}-{Y-2:yy}". My Part 5b pattern step turned only the current and neighbouring years' two digits into pattern words, and the check missed it because it compared only the 2024-25 text. All 113 are fixed. For an earlier release they would have shown, for example, "2012-22".

**Finance note for individual schools:** when schools are compared, ranked or listed on a finance line, the answer now carries the "different reporting forms" statement, as group figures already did.

### The review list (`stage5b2/review_list.csv`)

| Flag | Measures | What it means |
| --- | ---: | --- |
| Codes without labels | 62 | A coded measure whose values in some year include codes the codebook does not label. 45 are branch-campus fields (IC_PCCAMPUSES), 36 rows are survey response flags (FLAGS); the others are ADM.ADMCON9, AL.LILSYN, CDEP.CIPCODE, F_F1A.F1MHOP and IC.DISTPGS. The app shows the raw code where there is no label. |
| No way to pick one row | 45 | Tables with several rows per school and no category rows: programs offered by field (CDEP, 42 measures) and custom comparison groups (CUSTOMCGIDS, 3). Until a row rule exists, an answer could take any row. |
| Never a value | 17 | No school has a value in any year: off-campus-with-family charges for earlier years in COST1 (6), branch-campus charges (8), cost flags (3). |
| Unit unclear | 6 | Instructional staff counts by rank in S_SIS ("Professors", "Lecturers" and so on): almost certainly counts, but no rule decided. |

## The question set on Haiku (two runs)

Same questions as before: 115 scored and 21 trend.

| | Part 5.0 (final run) | Part 5b2, first run | Part 5b2, second run |
| --- | ---: | ---: | ---: |
| Correct answer | 45 | 46 | 44 |
| Correct decline | 50 | 44 | 45 |
| Clarifying question | 17 | 14 | 14 |
| Wrong reading | 3 | 11 | 12 |
| **Right or acceptable** | **97.4%** | **90.4%** | **89.6%** |
| Trend: answer / decline / clarify / wrong | 3 / 11 / 6 / 1 | 3 / 12 / 6 / 0 | 4 / 13 / 4 / 0 |
| Time per turn (mean; slowest tenth) | 4.7 s; 8.1 s | 5.0 s; 9.6 s | 4.6 s; 8.3 s |
| Cost per run | $0.15 | $0.16 | $0.16 |

- **Fixed by the new measures:** "Which Massachusetts colleges offer distance education to undergraduates?" is now answered correctly (it was a wrong reading in Part 5.0).
- **Reviewed by hand:** 47 answers were carried over from the Part 5.0 review because they used the same measures, schools and groups. 4 declines were carried over because they gave the identical message. 31 answers I read and judged. All are recorded in `docs/stage4/review.csv`.

**Wrong readings, by cause:**

1. **Coded category columns read as figures (both runs; recurs).**
   - "How many full-time and part-time instructional staff did Yale have?" (two phrasings): the model picked S_OC.FTPT, the coded full-/part-time column, so the answer shows the words "Full-time, Part-time" instead of counts.
   - There are 37 such columns now set up as measures: the category columns of multi-row tables, which pick rows and are not figures.
2. **A variant with no value for that school (both runs; recurs).**
   - Smith tuition: the model picked the program-year column, which vocational schools use.
   - Wellesley 2022-23 net price: it picked the in-state net price, which is for public schools.

   The current-year net price picks the right variant by kind of school (`applies_to`), but the earlier-year and program-year variants now set up have no such rule.
3. **Shortlist crowding (expected; Part 5d):**
   - "What is the universe with the lowest net cost?" is now "not found" (both runs);
   - an ROI ranking used a finance "investment return" line (first run);
   - "List every Yale student's name and GPA" showed the admissions GPA consideration beside the right statement (second run);
   - the dual-enrollment follow-up "both" could not be read (both runs, as in Part 5.0).
4. **Model variation, as in earlier runs:**
   - the ROI conversation's later turns;
   - the earnings data-exists question (first run);
   - test requirements, given as score ranges only (second run);
   - the STEM conversation (second run, as in Part 5.0).
5. **"Yale's faculty salary by academic field"** now shows all-ranks salary with the statement that IPEDS has salaries by rank, not field. That's a partial answer, which your Part 5.0 rule allows. But the expectation still says decline, so it is counted as wrong. See open question 5.

## Tests, timing and size

- **Tests:** 204 run: 201 pass; 3 known failures are marked until Part 5d (the staff-total shortlist tests). New tests cover:
  - **faster build:** 5 equivalence tests;
  - **measure checks and the dictionary:** measure checks; years of retired variables against the data; units by rule; every clashing name flagged;
  - **retired and summed rows:** an approved and a rejected successor; the summed Outcome Measures total and the race exceptions, through the build;
  - **the path defect:** a breakdown with no school and no group.
- **Build time:** dictionary full rebuild 34 minutes (2,065 s) on the first run. The final full rebuild before this report took 90 minutes (5,395 s) with the same results, because the computer was much slower that time (each year's tests 170 to 520 s instead of about 120 s; possibly OneDrive syncing the 3 GB database). About 10 minutes of a full rebuild is the measure checks.
- **Lines:** the question path is 2,392 lines (2,376 before). The build is 1,503, including the new `build/changes.py` (157); it was 1,121.

## Where existing code does not yet follow the version 3 habits

Unchanged from Part 5b. Habit 5 (conversation identifier) is done. Habit 2: `measure_years` gives every measure's table and variable for every year, ready for results to carry. Habits 1, 3 and 4 wait for their parts.

## Open questions

1. **Category columns as measures (recurring wrong reading).** The 37 category columns of multi-row tables are set up like every other measure, and the model reads one as a figure. One general fix: a column listed in `category_codes.csv` is a row key, so the app treats it as a choice of row, not a figure; it would stay in the dictionary but not be offered as a measure. Approve?
2. **Earlier-year and program-year variants (recurring wrong reading).** Give the earlier-year net prices the same `applies_to` pairs as the current-year one (public in-state, private all students), and give tuition the academic-year and program-year pair by the school's calendar system? Both are dictionary rows (`terms.csv`), with no code change.
3. **Unique names.** 474 names are shown for more than one measure (1,259 measures), mostly the same breakdown column in different tables ("Asian total" in completions, 12-month enrollment, fall enrollment). One way to fix most of them at once: a short subject for each table (about 60 rows, for example "completions", "fall enrollment"), shown after any name that clashes. Should I draft that list for your review, instead of plain names one by one?
4. **The review list.** For "no way to pick one row" (programs by field, custom comparison groups): add category rows for CDEP (the CIP field) and CUSTOMCGIDS, or leave them listed for each school only? For codes without labels: show the raw code with a note, or leave those measures out of answers?
5. **Partial answers in the expectations.** Should "Yale's faculty salary by academic field" (and similar) expect "answer the part IPEDS has, with the outside note", in line with your Part 5.0 decision?
6. **The 90% line.** The two runs read 89.6% to 90.4%. Questions 1 and 2 would fix the recurring wrong readings without touching the search. The crowding waits for Part 5d. Do you want 1 and 2 done before Part 5c, or folded into 5d?

Nothing is pushed.
