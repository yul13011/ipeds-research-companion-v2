# Stage 3 change order: what changed

Nov 16, 2026

All six items of the change order are in place and recorded in `dictionary/DECISIONS.md`. All 121 tests pass, and the work is committed locally (not pushed). No live model call has been made.

## 1. A school beside its group

The school is shown with its own counts. When the count behind its rate is under the ranking-guard threshold (30), the page warns. The warning is a setting row in `terms.csv`, with blanks the code fills in:

> {school}'s figure rests on {count} students, fewer than {threshold}, so it can change a lot from year to year.

Front Range now shows: "Front Range Community College's figure rests on 1 students, fewer than 30, so it can change a lot from year to year." The "1 students" is the template's wording; if you want "1 student" for counts of one, that is a one-row change.

## 2. Term statements, before and after

| Term | Before | After |
| --- | --- | --- |
| graduation rate | State which graduation rate was used. | Graduation rates differ by school level: four-year schools use the bachelor's six-year rate, and two-year schools the overall rate within 150% of normal time. |
| net price | State that the latest net price year is 2023-24. | Net price is reported one year behind the rest of the release; the period shown is the latest available. |
| revenue, expenses | State the fiscal year. Finance is reported on three forms; a school has values on only one. | Finance figures are for the fiscal year shown. Each school reports on one of three finance forms. |
| peers | State that the school's own IPEDS comparison group was used. | Peers are the comparison group the school itself submitted to IPEDS. |
| selective | Selective is not an IPEDS category. State the admission-rate cut-off used. | Selective is not an IPEDS category; the admission-rate cut-off used is shown above. |
| ranking guard (default) | For rates, schools with fewer than 30 in the denominator are excluded; the number excluded is stated and the count is shown beside each value. | Schools with fewer than 30 students behind the rate are left out of the ranking, and the number left out is stated; the count behind each rate is shown beside it. |
| ranking guard (include all) | All schools with a value are included, however small the denominator. | All schools with a value are included, however few students are behind the rate. |
| summable units | Only counts and dollar amounts are added up across schools. A percent, average or ratio is computed from its counts in rates.csv, or declined for a group with the per-school list offered. | Only counts and dollar amounts are added up across schools; rates and averages are computed from the counts behind them. |

Unchanged, because they were already sentences for the user: faculty, faculty salary, enrollment by major, different reporting forms, no year stated, no group stated, top with no number, split by.

The net price sentence no longer names 2023-24, so it stays true when more years are added; the period itself is still shown from the measure's own `period`.

## 3. Sentences that explain a word

These moved from the group's definition to a new `word_note` column in `school_groups.csv`. They are shown in "Definitions & sources" under "Note on words". "Interpreted as" shows only the definition.

| Group | Definition now | Note on words |
| --- | --- | --- |
| Private not-for-profit | Private not-for-profit | "Private" alone and "private colleges" mean private nonprofit, all levels. |
| Public, 4-year or above | Public, 4-year or above | "State schools" and "public universities" mean public four-year. |
| Private not-for-profit, 4-year or above | Private not-for-profit, 4-year or above | "Private universities" means private nonprofit four-year. |
| R1, 2021 definition | Doctoral Universities: Very High Research Activity (Carnegie 2021 basic classification) | R1 normally means the Carnegie 2025 research designation; this 2021 group is used only when asked for. |
| R2, 2021 definition | Doctoral Universities: High Research Activity (Carnegie 2021 basic classification) | R2 normally means the Carnegie 2025 research designation; this 2021 group is used only when asked for. |
| Liberal arts colleges | Baccalaureate Colleges: Arts & Sciences Focus (Carnegie 2021 basic classification) | "Liberal arts colleges" has no exact IPEDS category; this classification is the stand-in. |
| Flagship universities | A hand-kept list of 53 state flagship universities | Flagship is not an IPEDS category. |

One to check: your decision B12 said the app should say that flagship is not an IPEDS category. That sentence now appears under "Definitions & sources", not in "Interpreted as". If you want it in "Interpreted as", it can go back into the definition.

## 4. Plain names for the 20 generic measures

| Measure | IPEDS title | Plain name |
| --- | --- | --- |
| `C_A.CTOTALT` | Grand total | Awards and degrees conferred |
| `C_B.CSTOTLT` | Grand total | Students receiving awards or degrees |
| `C_C.CSTOTLT` | Grand total | Students receiving awards or degrees, by award level |
| `EAP.EAPTOT` | Total employees | Staff headcount, all employees |
| `EAP.EAPFT` | Full-time employees | Staff headcount, full-time employees |
| `EAP.EAPPT` | Part-time employees | Staff headcount, part-time employees |
| `EF.EFTOTAL` | Grand total | Fall enrollment, summary by level |
| `EFA.EFTOTLT` | Grand total | Fall enrollment |
| `EFB.EFAGE09` | Grand total | Fall enrollment, from the age table |
| `EFC.EFRES01` | First-time degree/certificate-seeking undergraduate students | First-time undergraduates, from the residence table |
| `EFCP.EFTOTLT` | Grand total | Fall enrollment in selected major fields |
| `EFFY.EFYTOTLT` | Grand total | 12-month unduplicated headcount |
| `EFFY_HS.EFYTOTLT` | Grand total | Dual-enrolled high school students, 12-month headcount |
| `GR.GRTOTLT` | Grand total | Graduation-rate cohort count |
| `OM.OMACHRT` | Adjusted 2016-17 cohort | Outcome Measures adjusted entering cohort |
| `OM.OMAWDN8` | Number of adjusted cohort receiving an award at 8 years (August 31, 2024) | Outcome Measures students receiving an award within eight years |
| `S_IS.HRTOTLT` | Grand total | Full-time instructional staff |
| `S_NH.HRTOTLT` | Grand total | Full-time new hires |
| `S_OC.HRTOTLT` | Grand total | Staff headcount, from the occupation table |
| `SAL_IS.SAINSTT` | Instructional staff - total | Full-time instructional staff, from the salary table |

"Interpreted as" for Yale by race now reads "Fall enrollment, All students, Undergraduate total for Yale University, broken down by race and ethnicity (Fall 2024)".

## 5. Graduation periods

Cohort years are stored as offsets from the release year:

- **Measures with one cohort:** a new `entering_cohort` column in `measures.csv`. The 19 bachelor's-cohort measures in `DRVGR` are `fall -6`.
- **Tables:** a new `entering_cohort` column in `year_meaning.csv`, by school level where the same column covers more than one cohort.

| Table | Rule | 2024 release reads |
| --- | --- | --- |
| DRVGR, GR, GR_PELL_SSL | fall -6 for four-year; fall -3 for two-year and less-than-two-year | fall 2018; fall 2021 |
| GR_L2 | fall -3 | fall 2021 |
| GR200 | fall -8 for four-year; fall -4 for the others | fall 2016; fall 2020 |
| OM, DRVOM | academic year -8 | 2016-17 |

The sentence is a setting row: "students who entered in {cohort}, {status}". Examples:

- **Six-year rate at RIT, WPI and Drexel:** "students who entered in fall 2018, status as of August 31, 2024".
- **Public two-year graduation rate:** "students who entered in fall 2021, status as of August 31, 2024".
- **The overall rate for Yale beside a two-year school:** "students who entered in fall 2018 (four or more years schools) or fall 2021 (at least 2 but less than 4 years schools), ...". The level names come from the directory groups, so they read awkwardly. Plainer level names would be a change to three group names.

**A codebook discrepancy.** The 2024-25 codebook's table titles say the cohorts are 2017 (four-year) and 2020 (two-year), and the Outcome Measures title says 2015-16. The variable descriptions say 2018, 2021 and 2016-17. With status at August 31, 2024, the variable descriptions are right: six years for a four-year cohort, three for a two-year cohort, eight for Outcome Measures. The table titles look carried over from the previous release. I used the variable descriptions.

## 6. The national universe on every group figure

Every group figure now stays inside the national universe and says so: counts, totals, rates, averages, rankings, lists, splits, breakdowns of a group, and a school's peers. "All institutions" is a setting reading the user can ask for. Questions about named schools are not affected.

### Figures that changed

| Figure | Before | After |
| --- | --- | --- |
| (e) Graduation rate, public two-year colleges | 36.72%: 156,621 completers of 426,480, 825 schools reporting, 13 with no value | 36.72%: 156,443 of 426,082, 819 reporting, 7 with no value |
| Count of public two-year colleges | 838 | 826 |

The 12 public two-year schools now left out are five in Puerto Rico and one in Palau, plus six in California, Illinois, Ohio and Pennsylvania that are outside Title IV. Six of them reported graduation rates.

**Question (e) and NCES are still consistent.** NCES's 0.427 is for all two-year institutions, not public only. From counts over the national universe the app gives 0.4267, unchanged. The test for that figure passes.

### Figures that did not change

- (c) Texas public four-year retention: all 67 schools were already in the universe; the same 37 are ranked.
- (g) Front Range against its peers: all 36 comparison schools were already in the universe; 68.6%.
- The national figures (rates, Pell, per-FTE expenses, salaries): they already used the universe.

## Tests

121 tests, all passing:

- **Changed:** the test for question (e) now expects the figures inside the national universe.
- **New:**
  - cohort periods from offsets, for one cohort and for mixed levels;
  - the universe on a count, and "All institutions" when asked;
  - word notes appear in definitions and not in "Interpreted as";
  - the plain names are used, and no term statement is left as an instruction to the app;
  - the small-cohort warning appears.

## Next

You set the API key and restart. Then, with your approval, the live smoke test runs the nine questions (`python scripts/smoke_test.py --yes`), and after it, Stage 4.
