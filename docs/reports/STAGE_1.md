# Stage 1 report: data tables

Nov 15, 2026

Stage 1 is done. Every table in the 2024-25 IPEDS release is now in one local database with a year column, and every row count matches the source. Nothing was committed, and nothing in version 1 or the outer repository was changed.

## What was built

| File | Lines | What it is |
| --- | --- | --- |
| `CLAUDE.md` | 68 | The working rules, the RULES section, and your seven decisions from Nov 15, so later sessions start with them |
| `.gitignore` | 26 | Keeps data, secrets, logs and Python clutter out of git |
| `config.py` | 18 | The one place paths are set: version 1's data folder, the local database, and the list of releases to load |
| `build/build_data.py` | 134 | The build script |
| `tests/test_build_data.py` | 171 | The tests |

Code that runs: 152 lines (`config.py` plus `build_data.py`). None of this is part of the question path yet; that count starts in Stage 3.

A new git repository was started in this folder with `git init`. No commit was made.

## How the local database is organised

- **One file:** `data/ipeds_v2.sqlite`, 294 MB, untracked. It rebuilds from scratch in 15 seconds with `python build/build_data.py`.
- **The source is read in place.** The script opens version 1's database read-only. A test confirms the source file is byte-for-byte unchanged afterwards and that a write to it is refused.
- **Each table is named by its family, with the year taken out of the name.** `ADM2024` becomes `ADM`, `F2324_F1A` becomes `F_F1A`, `COST2_2024_NetPrice` becomes `COST2_NETPRICE`. The family names come from the cross-year index in `analysis_catalog`, not from rules about table names. This is what lets another year land in the same table later.
- **Every table has a `year` column,** set to 2024 for this release.
- **Multi-row tables are loaded whole,** with all their category columns. Nothing is filtered or reshaped.
- **The four codebook tables are loaded too:** `VARTABLE`, `VALUESETS`, `TABLES`, `NEWVARIABLES`.
- **A small table called `_tables` records what was loaded:** the local name, the source name, the family, the release, the year, and both row counts. Stage 2 uses it to translate the workbook's names (such as `DRVGR2024.GBA6RTT`) into local names.
- **Tables keyed by school get an index** on school ID and year, so lookups are fast.

### Adding the other nine years later

Add one line per release to the list in `config.py` and run the build again. The script already handles the two things that differ between years:

- **A column that exists in one year but not another** is added to the stacked table and left missing (not zero) for the years that lack it. A test covers this with two made-up years.
- **Running a year twice** replaces that year's rows; it does not duplicate them. Also tested.

I checked the naming against all 554 tables in the cross-year index, across all ten releases: they reduce to 66 local tables with no two tables in one release landing on the same name.

## Row counts

All 56 tables match: 3,498,252 rows in the source, 3,498,252 loaded, 0 mismatches. That total also equals the figure version 1 recorded when it converted the original NCES Access file.

| Local table | Source table | Rows | Match |
| --- | --- | ---: | --- |
| ADM | ADM2024 | 1,956 | yes |
| AL | AL2024 | 3,652 | yes |
| CDEP | C2024DEP | 247,147 | yes |
| C_A | C2024_A | 1,688,471 | yes |
| C_B | C2024_B | 5,827 | yes |
| C_C | C2024_C | 16,104 | yes |
| COST1 | Cost1_2024 | 5,867 | yes |
| COST2_FINANCIALAID | Cost2_2024_FinancialAid | 5,406 | yes |
| COST2_NETPRICE | COST2_2024_NetPrice | 5,406 | yes |
| CUSTOMCGIDS | CUSTOMCGIDS2024 | 51,764 | yes |
| DRVADM | DRVADM2024 | 1,931 | yes |
| DRVAL | DRVAL2024 | 3,920 | yes |
| DRVC | DRVC2024 | 5,876 | yes |
| DRVCOST | DRVCOST2024 | 3,388 | yes |
| DRVEF | DRVEF2024 | 5,843 | yes |
| DRVEF12 | DRVEF122024 | 5,862 | yes |
| DRVF | DRVF2024 | 5,915 | yes |
| DRVGR | DRVGR2024 | 5,219 | yes |
| DRVHR | DRVHR2024 | 5,912 | yes |
| DRVOM | DRVOM2024 | 3,590 | yes |
| EAP | EAP2024 | 285,259 | yes |
| EF | EF2024 | 41,775 | yes |
| EFA | EF2024A | 113,833 | yes |
| EFA_DIST | EF2024A_DIST | 21,819 | yes |
| EFB | EF2024B | 76,359 | yes |
| EFC | EF2024C | 70,119 | yes |
| EFCP | EF2024CP | 168,639 | yes |
| EFD | EF2024D | 5,578 | yes |
| EFFY | EFFY2024 | 115,026 | yes |
| EFFY_DIST | EFFY2024_DIST | 21,997 | yes |
| EFFY_HS | EFFY2024_HS | 2,381 | yes |
| EFIA | EFIA2024 | 5,861 | yes |
| F_F1A | F2324_F1A | 1,911 | yes |
| F_F2 | F2324_F2 | 1,750 | yes |
| F_F3 | F2324_F3 | 2,046 | yes |
| FLAGS | FLAGS2024 | 6,072 | yes |
| GR | GR2024 | 51,011 | yes |
| GR200 | GR200_24 | 4,838 | yes |
| GR_L2 | GR2024_L2 | 1,535 | yes |
| GR_PELL_SSL | GR2024_PELL_SSL | 8,173 | yes |
| HD | HD2024 | 6,072 | yes |
| IC | IC2024 | 5,963 | yes |
| ICMISSION | IC2024Mission | 5,890 | yes |
| OM | OM2024 | 47,029 | yes |
| S_IS | S2024_IS | 63,389 | yes |
| S_NH | S2024_NH | 40,678 | yes |
| S_OC | S2024_OC | 178,024 | yes |
| S_SIS | S2024_SIS | 20,784 | yes |
| SAL_IS | SAL2024_IS | 15,216 | yes |
| SAL_NIS | SAL2024_NIS | 3,914 | yes |
| SFA | SFA2324 | 5,575 | yes |
| SFAV | SFAV2324 | 5,823 | yes |
| NEWVARIABLES (codebook) | newVariables24 | 63 | yes |
| TABLES (codebook) | tables24 | 52 | yes |
| VALUESETS (codebook) | valueSets24 | 12,143 | yes |
| VARTABLE (codebook) | varTable24 | 2,599 | yes |

## Test results

12 tests, all passing, in 15 seconds. Run with `python -m unittest discover -s tests -v`.

**On small made-up databases (7 tests):**

- Family names turn into the expected local names.
- The year column is added and row counts match; a multi-row table keeps all its rows.
- A missing value stays missing and a zero stays zero.
- A second year stacks into the same table, and a column new in that year is missing, not zero, for the other year.
- Running the same year twice does not duplicate rows.
- A source table that is not in the cross-year index stops the build with an error, so nothing is skipped silently.
- The source is opened read-only and is unchanged afterwards.

**On the real database (5 tests):**

- All 56 source tables are present: 52 data tables and 4 codebook tables.
- Row counts match the source, recounted at test time.
- Row counts match the counts version 1 recorded from the original NCES Access file (`table_checks.csv`).
- For every column of every table, the number of non-missing values matches the source, and for every numeric column the total matches. This is stronger than a row count: it would catch a shifted, dropped or zero-filled column.
- Three figures from the plan come out of the stacked tables: 6,072 schools in the directory; 5,626 in the national universe you chose; 2,845 schools with a comparison group.

The tests use Python's built-in test tool because `pytest` is not installed on this machine. No install was needed.

## Open questions

1. **What `year` holds for tables that report the previous year.** `year` is the release year, 2024, for every table. That includes `SFA2324` and the three finance tables, whose data cover 2023-24. This matches the cross-year index and your workbook's "Year meaning" tab, which is where the real meaning (fall, fiscal year, cohort) is recorded. Stage 2 will load that tab. Please confirm this is how you want it.

2. **Dollar amounts stored as text.** Version 1's converter stored Access "money" and exact-decimal fields as text to avoid rounding. 116 of the 2,710 source columns are text. I have not yet separated the true text columns (names, addresses) from the numeric ones stored as text. Stage 2 will do that when it builds the measure table, so that sums and rankings treat them as numbers. This is not a problem yet, but I am flagging it before any figure is computed.

3. **Tables that are not in all ten years.** Of the 56 tables in this release, 45 exist in all ten releases and 11 do not. Ten further families exist only in earlier years (for example `IC_AY`, `SFA_P1`, `GR_GENDER`). This matches the "Tables across years" tab and matters only when the other years are stacked.

4. **A column whose type changes between years.** When years are stacked, the stacked column keeps the type from the first year loaded. With one year this cannot arise. It should be checked when the second year is added.

5. **What goes in git from `docs/`.** `docs/question_log.csv` holds real user questions with session IDs and timestamps. Before the first commit, please decide whether it should be tracked. It is currently not ignored.

6. **The local database sits inside OneDrive,** so its 294 MB will sync. If you would prefer it elsewhere, setting the `IPEDS_LOCAL_DB` environment variable moves it with no code change.

## Next: Stage 2

Stage 2 starts with the gap list you asked for, before anything is loaded: every workbook row that has no draft to accept, plus version 1's flagships list for your approval. I will send that list and wait for your answers.
