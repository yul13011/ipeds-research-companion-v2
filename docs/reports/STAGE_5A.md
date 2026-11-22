# Stage 5, part 5a: the ten years stacked

Date: 2026-11-22. Decisions are recorded in `dictionary/DECISIONS.md` under "2026-11-22: Stage 5, part 5a".

## Summary

- **All ten releases (2015-16 to 2024-25) are in the local database:** 554 tables, 33,484,311 rows, every table matching its source row for row. Each year was cleaned with its own codebook.
- **Build time:** 28 minutes to stack the ten years, plus 4 minutes for the dictionary (32 in all). Adding or replacing one release takes about 9.5 minutes, dictionary included.
- **Database size:** 3.1 GB, up from 0.35 GB for one year.
- **Adding or replacing a release is one command,** `python build/build_data.py --release <folder>`. It is tested on made-up releases for both cases: a new year, and a provisional release replaced by its final version. It is also tested end to end on the real database: replacing 2024-25 with itself left every row count, the table registry and the missing-value records exactly as they were.
- **`UPDATING.md`** gives the yearly steps with the exact commands.
- **Each year is labelled provisional or final.** Answers now say "Figures from the IPEDS 2024-25 release (provisional)", and the provisional warning stays.
- **The app still answers from 2024 only, and its answers are unchanged:**
  - all 180 tests pass on the ten-year database;
  - the benchmarks are identical (19 NCES, 17 Yale and 5 design-table figures match);
  - the national universe is still 5,626.

  Trends come in part 5c.
- **The chat page you were testing is running again** at http://localhost:8501 on the ten-year database. I stopped it for the switch, which took a few seconds. The one-year database is kept as `data/ipeds_v2_2024only.sqlite`, untracked.

## Row counts per year

| Release | Status | Tables | Source rows | Loaded rows |
| --- | --- | ---: | ---: | ---: |
| 2015-16 | final | 52 | 3,299,056 | 3,299,056 |
| 2016-17 | final | 55 | 3,386,220 | 3,386,220 |
| 2017-18 | final | 54 | 3,333,620 | 3,333,620 |
| 2018-19 | final | 55 | 3,279,594 | 3,279,594 |
| 2019-20 | final | 55 | 3,140,338 | 3,140,338 |
| 2020-21 | final | 56 | 3,394,088 | 3,394,088 |
| 2021-22 | final | 56 | 3,314,879 | 3,314,879 |
| 2022-23 | final | 58 | 3,474,592 | 3,474,592 |
| 2023-24 | final | 57 | 3,363,672 | 3,363,672 |
| 2024-25 | provisional | 56 | 3,498,252 | 3,498,252 |
| **Total** | | **554** | **33,484,311** | **33,484,311** |

Per table and year: `docs/reports/stage5a/rows_by_table_year.csv`.

Cleaning across the ten years:
- 168 columns stored as numbers, not text, as the codebook says;
- 1,519,679 text cells trimmed;
- 176,546 blank cells set to missing;
- 5,095,692 special-code cells set to missing;
- no cell failed to convert.

## What changes between years

### Tables present only in some years (21; `tables_by_year.csv`)

**The largest change: the cost and student-aid tables were reorganised in the 2024-25 release.** The same figures sit under different table names before and after:

| Through 2023-24 | From 2024-25 |
| --- | --- |
| IC_AY, IC_PY (student charges) | COST1 |
| SFA_P1, SFA_P2 (student aid and net price) | SFA, COST2_FINANCIALAID, COST2_NETPRICE |
| DRVIC (derived charges) | DRVCOST |

The cross-year index gives them different families, so they stack as different tables. Linking them, so that a trend in net price or tuition runs across 2023 and 2024, is part 5b work. The variables need matching one by one.

Other tables in some years only:
- **Outcome Measures:** derived variables (DRVOM) from 2016-17; the Pell/subsidized-loan graduation table (GR_PELL_SSL) from 2016-17.
- **Fall enrollment by major (EFCP):** even-numbered years only, which is how IPEDS collects it.
- **Distance education, 12-month (EFFY_DIST):** from 2020-21.
- **Dual enrollment (EFFY_HS):** from 2023-24.
- **Graduation rates by gender (GR_GENDER):** 2022-23 and 2023-24 only.
- **Additional campuses (IC_PCCAMPUSES):** 2021-22 to 2023-24.
- **Codebook tables** that came and went (FILENAMES, SECTIONTABLE, NEWVARIABLES, TABLES19_RV). These hold no data.

### Columns whose stored type changes (2; `type_changes.csv`)

Both are in the codebook tables, not in data:
- VALUESETS.PERCENT is text through 2022 and a number from 2023;
- VARTABLE.HASRV is a number through 2022 and text from 2023.

No data column changes type.

### Variables added, retired or renamed (`variables_by_year.csv`)

Between consecutive years: 568 added, 326 retired, and 1 rename found with certainty (F_F1A F1C197 → F1C19IN, "Total expenses deductions - Interest").

The cross-year index does not detect renames; it compares variables with the same name only. I matched retired and new variables by their codebook titles. That finds only renames whose title stayed the same, so the rename count is a floor.

Where many variables changed at once, most are survey redesigns:

| Table | Change | Count |
| --- | --- | ---: |
| DRVOM (Outcome Measures, derived) | added 2016→2017 | 108 |
| F_F1A, F_F2, F_F3 (finance forms) | retired 2015→2016 | 61, 58, 53 |
| F_F1A, F_F2, F_F3 (finance forms) | added 2019→2020 | 31, 30, 25 |
| DRVEF12 (12-month enrollment, derived) | added 2019→2020 | 54 |
| SAL_IS (salaries) | added 2015→2016 | 36 |
| DRVF (finance, derived) | retired and added 2015→2016 | 24 each (likely renames with new titles) |
| IC | retired 2023→2024 | 23 (moved into COST1) |

These are for the part 5b gap list.

## What did not work as planned, and what I did about it

1. **The dictionary build failed at first on ten years.** It stopped twice:
   - seven tables that exist only in earlier years have no year_meaning.csv row (DRVIC, IC_AY, IC_PY, SFA_P1, SFA_P2, IC_PCCAMPUSES, GR_GENDER);
   - in earlier years, the 12-month enrollment table (EFFY) is keyed by different category columns, so its default row does not pick one row per school.

   Both need conventions, which is part 5b. As this part changes the dictionary only as far as the build needs, I scoped these checks to the latest year (2024), the year the app answers from. The same scoping applies to the category-row, summary-to-detailed link and breakdown-set tests. The results are identical to the one-year build: 54 links loaded; 223 breakdown sets loaded, 1 additive, 29 failed (as before).
2. **A real build defect: groups narrowing across years.** A group defined by several conditions removed non-matching schools by looking at any year, not the same year. With ten years loaded, a school meeting a condition in 2015 could stay in the 2024 group. Fixed; the national universe for 2024 is 5,626, as before.
3. **Groups made from every value of a column picked up values seen only in earlier years.** For example, 67 religious affiliations instead of 63, and 5,887 groups instead of 4,936. For now these lists use the latest year (4,936 groups, as before). Groups for each year are part 5b.
4. **App lookups that named no year.** Seven app queries read the school directory, value labels or parent/child flags without naming a year. With ten years they would have mixed years, for example an older school name. All are now filtered to the year answered.
5. **Tests.** Many tests computed their own expected figures with SQL that names no year. They now use a latest-year view for those queries (`tests/latest.py`); the app's own connections are untouched. Three build tests now compare against the 2024-25 release's own records.

## Speed

The code's part of answering, without the model call, takes 0.04 to 0.23 seconds on ten years, against 0.02 to 0.11 on one year. The slowest case is a figure split by control. That is negligible beside the model call (about 4.5 seconds). The test suite takes longer, 75 seconds against about 30, because of the tests' own counting queries.

## Tests and line counts

- 180 tests pass on the ten-year database, up from 172. New:
  - add and replace a release (5 tests on made-up releases);
  - every release held once, with its status and every row;
  - the provisional/final label (2 tests).
- The question path is 2,302 lines, up from 2,268 (the year filters and the release label).
- The build is 879 lines, up from 777: `build_data` 400, `build_dictionary` 479.

## For part 5b (no decision needed now)

The gap list will start from:
- the cost and aid tables reorganised in 2024-25, to link across years;
- year_meaning rows for the seven earlier-year tables;
- the 12-month enrollment (EFFY) category keys in earlier years;
- the variables added, retired and renamed, especially the finance forms in 2016 and 2020 and Outcome Measures in 2017;
- testing breakdown sets, category rows, summary-to-detailed links and groups in every year.

## Open questions

1. **The cost and aid tables reorganised in 2024-25.** In part 5b, should I propose a one-by-one mapping of the old variables to the new ones (for example SFA_P2 net price to COST2_NETPRICE) for your review, before trends use them?
2. **Database size.** At 3.1 GB, it is near the size of version 1's data. Render hosting will need a disk of at least that, growing about 300 MB a year. No action now; noting it for the hosting step.
