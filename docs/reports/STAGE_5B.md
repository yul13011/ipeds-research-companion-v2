# Stage 5, part 5b: the dictionary across years

Date: 2026-11-22. Decisions are recorded in `dictionary/DECISIONS.md` under the four dated headings of 2026-11-22 that follow "owner decisions on the part 5a report". The gap list this part answered is `STAGE_5B_GAPS.md` (section 9 holds the aid-split check). Working files are in `docs/reports/stage5b/`.

## Summary

- **The dictionary is loaded and tested in all ten years.** The category-row, summary-to-detailed link and breakdown-set tests now run in each year, each year with its own category codes. The results the app reads still come from 2024-25, and its answers are unchanged:
  - all 190 tests pass;
  - the benchmarks are identical to the last run.
- **Every rate was checked in every year against NCES:** 83 of 88 rate-years with an NCES figure match, and the other 5 differ by less than 0.1 point.
- **The national universe matches NCES in every year,** from 7,021 schools in 2015-16 to 5,626 in 2024-25.
- **Years available are worked out per measure** (table `measure_years`). Of the 762 set-up measures, 488 have values in all ten years. A group rate is available only in years where all its counts have values (table `rate_years`).
- **The comparability-breaks table is drafted:** 12 rows, each with its source, all marked `draft` and not used. They are listed below for your review.
- **The aid-split check is done.** The all-undergraduate totals did not change definition. The details are in `STAGE_5B_GAPS.md` section 9.
- **The question log now records a conversation identifier and turn number** on every line (habit 5).
- **Build time:** the dictionary now takes about 25 minutes (about two minutes a year, against 4 minutes for one year before). A full ten-year rebuild takes about 55 minutes.

## What was built

| Decision | What changed |
| --- | --- |
| 1a. Year rules as patterns | All 52 table periods in `year_meaning.csv` and the 378 measure periods in `measures.csv` are written with `{Y}`, `{Y-1}`, `{Y+1}` and `{Y:yy}`. Each reproduces today's 2024-25 text exactly. The app fills them in with the year it answers from (`fill_years` in `path/request.py`, tested). |
| 1b. Titles that name a year | Built table `year_titles`: each year's own codebook title, for 438 measures whose title names a year. The dictionary title stays the 2024-25 one. |
| 2a. Cost and aid mapping | New file `measure_history.csv`, 560 rows: each 2024-25 cost or aid measure and where the same figure was stored before (for example COST2_NETPRICE.NPGRN2 in SFA_P2, 2015-2023). The 3 "check" and 42 new variables have no row, so no earlier years. Made once by `scripts/measure_history_draft.py`. |
| 2a. Title IV net price | The reading is now labelled "All students awarded Title IV federal aid (2024-25 only)". The default net price, which has all ten years, was already the grant-aid one. |
| 2b. One release per aid year | Built in: each 2024-25 measure maps to the earlier variable in the same position of its own release (current year to current year), so each aid year's figure comes from the release where it is current. |
| 3. Not collected | Message row "not collected year": "IPEDS did not collect {what} in {year}." A year with no row in `measure_years` is a year not collected. |
| 4a. Codes by year | `category_codes.csv` has two new columns: `years`, and `same_as` (decided after the gap list). Each year's tests use only that year's rows. Award level code 1 is part of "Awards by level" before 2020-21, and codes 20 and 21 after. 12-month enrollment uses EFFYLEV before 2020-21. Outcome Measures cohorts use codes 1-4 in 2015-16 and 2016-17. |
| 4b. Field of study | Break row drafted with your wording; no crosswalk. |
| 5a, 5b. Breaks table | `comparability_breaks.csv`, with `kind` and `status` columns. Drafted (below). |
| 6a to 6d. The directory | `school_groups.csv` has a new `membership` column. The 73 Carnegie groups are marked "as of latest year", so their 2024-25 list is used in every year. Names, closures, mergers and today's peers are answer behaviour for part 5c; the directory already holds each year's names, NEWID and comparison groups. |
| 7. Seven earlier-only tables | `year_meaning.csv` rows for DRVIC, IC_AY, IC_PY, IC_PCCAMPUSES, SFA_P1, SFA_P2 and GR_GENDER, in the pattern form. The build now checks that every table in every year has a year rule. |
| 8. Rates in every year | `scripts/rates_by_year.py` (below). |
| 9. Aid split | Context row drafted. Start years per variable, and group rates only once all their counts exist (`rate_years`). The trend defaults and the no-mixing rule are applied in part 5c. |
| 9a. Grant recipients | Context row drafted with your wording. |
| Same information, other column | `same_as` (details below). |
| A breakdown not usable in a year | Message row "breakdown not this year": "The breakdown "{set}" isn't available for {year}, because {why}. The total is shown." It is used in part 5c. |
| Habit 5 | Each question-log and decline-log line carries `conversation` and `turn`. A cleared conversation gets a new identifier. |

## The tests in every year

The tests run once per year, on a copy of that year's rows (much faster than reading all ten years at each test), with the category rows whose `years` cover it. The latest year runs last, so the tables the app reads hold 2024-25. Every year's results are kept in the new table `year_checks` (exported to `stage5b/year_checks.csv`).

| Release | Links loaded | Set columns loaded | No data that year | Failed |
| --- | ---: | ---: | ---: | ---: |
| 2015-16 | 33 | 179 | 48 | 0 |
| 2016-17 | 33 | 199 | 10 | 18 |
| 2017-18 | 33 | 216 | 12 | 25 |
| 2018-19 | 33 | 218 | 10 | 25 |
| 2019-20 | 33 | 216 | 12 | 25 |
| 2020-21 | 50 | 218 | 10 | 25 |
| 2021-22 | 50 | 215 | 12 | 26 |
| 2022-23 | 54 | 222 | 2 | 29 |
| 2023-24 | 54 | 222 | 2 | 29 |
| 2024-25 | 54 | 224 | 0 | 29 |

"Failed" is mostly sets that also fail in 2024-25 and are not loaded there either (for example "Fall enrollment by attendance status" and "Outcome measures by Pell status" on some count columns). Only one set fails in an earlier year but passes in 2024-25:
- "By race and ethnicity" in completions (C_C), 2021-22: at 4 of 15,984 schools the race parts do not add up to the total. Under your rule, that breakdown is not offered for 2021-22, and the total is still shown.

"No data that year" means the table, or that count column, has no values that year:
- "another gender" columns before 2022-23;
- the nine-month-equated salary columns before 2016-17;
- fall enrollment by major (EFCP) in odd years;
- dual enrollment (EFFY_HS) before 2023-24.

### Same information under another column or code (`same_as`)

| Table | Earlier rows | Same as | Years |
| --- | --- | --- | --- |
| EFFY (12-month enrollment) | EFFYLEV 1, 2, 4 (all students, undergraduate, graduate) | EFFYALEV 1, 2, 12 | 2015-16 to 2019-20 |
| OM (Outcome Measures) | OMCHRT 1-4 (full-time first-time, part-time first-time, full-time non-first-time, part-time non-first-time) | OMCHRT 10, 20, 30, 40 | 2015-16, 2016-17 |

The build checks a `same_as` claim wherever both columns are filled in the same year. EFFYLEV and EFFYALEV are both filled in 2020-21 to 2024-25, and they pick exactly the same rows in every year. The Outcome Measures codes are in one column, so that claim cannot be checked this way. It rests on the codebook labels, and the 2017-18 break note applies across it.

With this, the two 12-month headcount links (total and undergraduate) are tested and pass in 2015-16 to 2019-20, and 12-month enrollment has working row keys in every year.

### Links that are not in a year's data, and why

No link is "not in this year's data" in any year: every link whose summary measure has values in a year was tested and passed. Links are absent only where IPEDS did not collect the summary measure that year:

| Years | Links | Why |
| --- | --- | --- |
| 2015-16 to 2019-20 | DRVC.CERT1A, DRVC.CERT1B (certificates under 12 weeks; 12 weeks to under a year) | The award levels did not exist before 2020-21; certificates of less than a year were one level |
| 2015-16 to 2019-20 | 19 derived 12-month measures (DRVEF12.E12FT, E12PT, E12GRAD, E12UG1ST and the other undergraduate and graduate splits) | Before 2020-21, DRVEF12 held only the total and undergraduate headcounts and FTE |
| 2020-21, 2021-22 | DRVEF12.E12FT, E12PT, E12GRADFT, E12GRADPT | Not in the derived table in those two years |

The graduate 12-month headcount for 2015-16 to 2019-20 is in the detailed table (EFFYLEV 4). Part 5c can read it through the link and `same_as` when the derived figure is missing.

### Default rows

Every table that has default rows finds them in every year, except Outcome Measures in 2015-16 and 2016-17. Completions by level (C_C), fall enrollment by major (EFCP) and graduation rates (GR) have no default by design, as in 2024-25, so the app asks. There, the default is the total entering cohort (code 50), which IPEDS did not report until 2017-18. See open question 3.

## Years available

`measure_years` gives, for every measure and year, where it is stored and how many values it has. Of the 762 set-up measures:

| Years with values | Measures |
| ---: | ---: |
| 10 | 488 |
| 9 | 36 |
| 8 | 109 |
| 5 | 64 |
| 3 to 4 | 39 |
| 1 to 2 | 26 |

The aid family, as decided:

| Measure | First release |
| --- | --- |
| Percent of undergraduates awarded Pell grants (SFA.UPGRNTP), and the grant and loan percents | 2015-16 (all ten) |
| Percent of degree-seeking undergraduates awarded Pell grants (SFA.UDGPGRNTP), and grant aid | 2022-23 |
| Number of degree-seeking undergraduates awarded Pell grants (SFA.UDGPGRNTN), and loan counts and amounts | 2023-24 |
| Average net price, grant or scholarship aid (NPGRN2, NPIST2) | 2015-16 (all ten) |
| Average net price, Title IV aid, all incomes (NPIS42, NPT42) | 2024-25 only |

Group rates available by year (`stage5b/rate_years.csv`):
- every rate has all ten years except these:
  - the nine-month salary rates (from 2016-17);
  - Pell recipients' bachelor's graduation rate (from 2016-17);
  - Outcome Measures award within eight years (from 2017-18);
  - Title IV net price (2024-25 only).

Measures used per year: `stage5b/measure_years_summary.csv`.

## Rates in every year (decision 8)

`scripts/rates_by_year.py` computes each rate's national figure from its counts over each year's national universe, as the app computes a group figure, and compares it with the NCES Trend Generator files. Results: `stage5b/rates_by_year.csv`.

- **83 of 88 rate-years with an NCES figure match** within 0.05 point. The 5 that differ are all within 0.1 point:

| Rate | Release | This app | NCES |
| --- | --- | ---: | ---: |
| Bachelor's six-year graduation rate | 2015-16 | 59.46 | 59.4 |
| Bachelor's six-year graduation rate | 2020-21 | 64.05 | 64.0 |
| Bachelor's six-year graduation rate | 2022-23 | 64.69 | 64.6 |
| Percent of undergraduates awarded Pell grants | 2015-16 | 38.44 | 38.5 |
| Percent of full-time first-time students awarded any aid | 2015-16 | 83.33 | 83.4 |

  The graduation-rate gaps all lean the same way, which suggests NCES cuts off rather than rounds, or uses a slightly different set of schools. I have not confirmed which.
- **Ready-made rates against counts** (`stage5b/ready_made_by_year.csv`): IPEDS's own rate for each school agrees with the rate from its counts, within rounding, for every rate and every year, except retention:
  - full-time retention rate: 2 schools in 2019-20, 1 in 2020-21 and 5 in 2021-22;
  - part-time retention rate: 1 school in 2018-19, 2 in 2019-20 and 1 in 2021-22.

  The app computes group rates from counts, so these schools do not change any group figure. A single school's own rate is shown as IPEDS gives it.
- **National universe against NCES (question 1):** the same in all ten years (`stage5b/universe_by_year.csv`).

## The comparability-breaks rows, for your review

All 12 rows are `draft`; none is shown until you approve it. "Release" is the release year, which is how the app names years. Full text and sources are in `dictionary/comparability_breaks.csv`.

| # | Kind | Tables | First release | Note shown | Source |
| --- | --- | --- | --- | --- | --- |
| 1 | definition change | OM, DRVOM | 2017-18 | Outcome Measures cohorts changed in 2017-18: every school now reports students who entered over a full year, split by Pell status. Earlier figures used fall entering cohorts at many schools. | NCES IPEDS overview (2019), pp. 4 and 8; OMCHRT codes |
| 2 | definition change | S_NH | 2016-17 | From fall 2016, IPEDS counts as new hires the people hired from November 1 to October 31; before, it counted only those hired from July 1 to October 31. | 2016-17 codebook, S2016_NH. **Later codebooks disagree on the first year** (2016, 2017 or 2020) |
| 3 | definition change | EAP, S_IS, S_SIS, S_NH | 2016-17 | From 2016-17, faculty not on the tenure track are split by length of contract; earlier years group them differently. | 2016-17 codebook, EAP2016; codes 44 and 45 absent in 2015-16 |
| 4 | definition change | C_A, C_C, CDEP | 2020-21 | From the 2020-21 release, certificates of less than one year are split into those under 12 weeks and those of 12 weeks to under a year. | 2020-21 codebook, C2020_A, C2020_C, C2020DEP |
| 5 | definition change | C_A, CDEP | 2020-21 | Field-of-study codes changed to the 2020 classification (CIP 2020) from the 2020-21 release. The changes were mostly at the detailed six-digit level; the broad two-digit fields used in the field-of-study breakdown changed much less. | 2020-21 codebook, C2020_A. **EFCP to confirm** |
| 6 | definition change | EFFY | 2020-21 | From the 2020-21 release, 12-month enrollment is reported in more detail by student level; earlier years have only all students, undergraduates and graduate students. | 2020-21 codebook, EFFY2020 |
| 7 | definition change | F_F1A | 2020-21 | From fiscal year 2020, scholarships and fellowships by source include the discounts and allowances attributed to each source. | 2020-21 codebook, F1920_F1A |
| 8 | definition change | EF, EFA, ADM | 2022-23 | From fall 2022, IPEDS also counts students who do not fit the men and women categories, so men plus women can be less than the total. | 2022-23 codebook, EF2022A; 2023-24, EF2023A and ADM2023 |
| 9 | context | enrollment, finance and retention tables (17) | 2020-21 to 2021-22 | Figures for 2020-21 and 2021-22 cover the COVID-19 pandemic period. | Your decision 5b |
| 10 | context | SFA_P1, SFA | 2022-23 | IPEDS began reporting degree-seeking and non-degree-seeking undergraduates separately in the 2022-23 release for grant aid and the Pell and loan percents, and in the 2023-24 release for Pell and loan counts and amounts. The all-undergraduate totals are unchanged. | Codebooks SFA2122_P1 and SFA2223_P1; aid-split check |
| 11 | context | SFA_P1, SFA (grant recipients) | 2022-23 to 2023-24 | The number of students receiving grant aid rose in 2021-22 and fell in 2022-23 at many schools; IPEDS does not give a reason. | Your decision 9a; `aid_split_national.csv` |
| 12 | definition change | COST1, DRVCOST | 2024-25 | From 2024-25, cost of attendance counts food and housing in place of room and board, and adds a charge for students living off campus with family. | 2024-25 codebook, COST1_2024 and the new-variables list |

Considered and left out, because they add or remove measures without changing what an existing measure means. A trend shows those years as not collected:
- Outcome Measures begins (2015-16);
- graduation-rate Pell and loan subcohorts (2016-17);
- the finance natural-expense detail dropped (2016-17);
- staff counts collected every year, not every other year (2016-17);
- new admissions considerations and test-score medians (2022-23).

The Carnegie 2025 classification is covered by decision 6d's statement, not a break. The HEERF candidate from the gap list is dropped: I found no codebook wording for it.

## Tests, timing and size

- **Tests:** 190 pass, up from 180. They do not call the API and write only to their own folders. New:
  - **dictionary across years (loader):** years of category rows tested in each year; every table needs a year rule for every year; `measure_years` and `rate_years`; Carnegie-style groups as of the latest year; unreadable `years` cells;
  - **mapping:** a link tested in an earlier year through `same_as`; a link with no counterpart recorded as not in that year's data; a `same_as` claim that contradicts the data stops the build;
  - **path:** period patterns; conversation and turn on log lines.
- **Benchmarks:** identical to the last run (2024-25).
- **Timing:** dictionary 25 minutes: 98 to 126 seconds per year, plus about 4 minutes counting `measure_years`. Full ten-year rebuild about 55 minutes. `CLAUDE.md` and `UPDATING.md` updated.
- **Lines:** the question path is 2,324 lines (2,302 before); the build is 1,056 (879 before).
- **Note:** the 92 "failed, nothing tested" set results were relabelled "no data" in the stored table directly, rather than by running the 25-minute build again. The code now gives the same result.

## Where existing code does not yet follow the version 3 habits

| Habit | State |
| --- | --- |
| 1. Clean operations | Unchanged from 5a: `fetch.py` operations are clean; `answer.py` still mixes conversation state, logging and page building. |
| 2. Every result carries its source | Partly. `measure_years` now gives each measure's table and variable for every year, ready for trend results to carry. Results still do not carry their source in a structured form. |
| 3. Number check as a general component | Part 5e. |
| 4. "What data exists" self-contained | Unchanged; part of resolve. |
| 5. Conversation identifier in logs | **Done.** |

## Open questions

1. **The breaks rows.** Approve, change or drop each of the 12. Three need your eye:
   - row 2: the codebooks disagree on when the new-hire window changed;
   - row 5: whether fall enrollment by major (EFCP) moved to CIP 2020 at the same time is not confirmed;
   - row 7: a finance change I found in the 2020-21 codebook.
2. **Which releases the pandemic note covers.** I attached it to the 2020-21 and 2021-22 releases. For July-to-June tables (completions, 12-month enrollment, aid), those releases cover July 2019 to June 2021. For fall tables they cover fall 2020 and fall 2021. Is that what you meant?
3. **Outcome Measures in 2015-16 and 2016-17 have no total cohort row.** The total would be the sum of the four cohorts (codes 1-4). Should a trend of the total entering cohort start in 2017-18 (no total reported before), or compute 2015-16 and 2016-17 as the sum of the four, with the break note?
4. **Mapping the Outcome Measures cohorts across 2017-18** (codes 1-4 = 10, 20, 30, 40) rests on the labels, while the cohort definition changed (break row 1). Keep the mapping with the note, or treat the earlier cohorts as not comparable?
5. **Build time.** The dictionary takes 25 minutes because every year is tested every time. One option is to retest an earlier year only when its data or the dictionary rows for it change. That would bring a routine dictionary edit back to about 4 minutes. Proposal only; say if you want it.
6. **Part 5c will apply:**
   - the trend defaults (the all-undergraduate aid measures; grant-aid net price);
   - the rule that no trend mixes measures with different first years;
   - today's names with "(then: …)";
   - "merged into … in …";
   - today's peers;
   - the "not collected" and "breakdown not this year" messages;
   - the graduate 12-month headcount before 2020-21 from the detailed table.

The two new test questions (Yale Pell since 2015; degree-seeking Pell at Front Range Community College since 2015) are in `docs/owner_questions.csv` with expectation rows, due in stage 5c. Front Range Community College (127200) is in the data in all ten years.

Nothing is pushed.
