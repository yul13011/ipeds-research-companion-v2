# Stage 5, part 5b2: fixes before Part 5c

Date: 2026-11-23. Decisions are recorded in `dictionary/DECISIONS.md` under "2026-11-23: Part 5b2 approved; decisions on the Part 5b2 report". Parts 5b and 5b2 are pushed to GitHub (d036993). This work is committed locally and not pushed.

## Summary

- **Item 1, category columns are row choices:** done, as a general rule with a test from the instructional-staff question.
  - A category column is no longer listed as a measure on the shortlist.
  - If a request still names one as the figure, the app asks which of the table's figures the user wants, keeping the rows asked for. It never shows codes as the answer.
  - Asked through that route, "full-time and part-time instructional staff at Yale" now gives counts: 805 part-time and 2,995 full-time.
  - Taking these columns off the shortlist also freed room, and the 3 shortlist tests marked as known failures until Part 5d now pass.
- **Item 2, kind-of-school pairing:** done, in dictionary rows only (`terms.csv`, `school_groups.csv`). The earlier-year net prices pair the public and private measures as the current one does. Tuition in each year pairs the academic-year and program-year columns, using two new groups from the calendar system (IC.CALSYS 1-5 report by academic year, 6-7 by program; the data agree exactly). Wellesley's 2022-23 net price ($21,501) and Smith's 2023-24 tuition ($61,568) now show. Test added.
- **Item 5, partial answers count as expected:** expectation updated ("Yale's faculty salary by academic field").
- **New test question** "How many schools have negative net worth and which are they?":
  - added, due at stage 5b2, with its expectation;
  - your counts match the data: 147 public, 28 private nonprofit and 50 for-profit (123, 26 and 50 inside the national universe);
  - the pension note is a statement on F_F1A.F1A18 in `measures.csv`.
- **Tests:** 206 pass, none failing.
- **Haiku, two runs: 94.0% and 94.0% right or acceptable** (109 of 116 each), up from 90.4–91.3% for Part 5b2 under the same expectations. Part 5.0 was 97.4%. Cost $0.16 per run; mean 4.9–5.1 s per turn.

## The question set on Haiku

| | Part 5b2 (two runs) | After items 1 and 2 (two runs) |
| --- | --- | --- |
| Right or acceptable | 91.3%, 90.4% | **94.0%, 94.0%** |
| Wrong readings | 10, 11 | 7, 7 |

The Part 5b2 runs are re-graded here with the partial-answer expectation, which raises them from 90.4%/89.6%.

**Fixed:**
- the full/part-time staff question (now a clarifying question about "faculty", in both runs, instead of the words "Full-time, Part-time");
- Wellesley's earlier net price;
- Smith's tuition.

**Wrong readings left (7 in each run):**
- **The net-worth question (both runs):** the app lists schools by net position only, the public form. The private nonprofit and for-profit measures are not used, so the answer is not grouped by form. The pension note and the fiscal year do appear. This needs a path change: a condition ("below zero") that uses one measure per reporting form. Today the pairing works for figures, not for conditions. See open question 2.
- **Room and board at Mount Holyoke (both runs):**
  - one run picked the program-year food-and-housing column (no value);
  - the other picked an earlier release's room-and-board variable, now retired.

  Food and housing, books and other charges have the same academic-year/program-year split that tuition has, and your decision covered tuition only. See open question 1.
- **Model variation, as in earlier runs:**
  - the dual-enrollment follow-up "both";
  - "the universe with the lowest net cost" (not found);
  - the income data-exists question;
  - the ACT question, which the model declined as "admitted students who submitted ACT scores" in both runs;
  - "use the institutions in the example set" (one run picked 15 unrelated schools);
  - an earnings question in the second run.

## Item 3: table subjects, for your review

Drafted from IPEDS's own table titles. Not applied yet: once you approve the list, every name shared by two or more measures is shown as "subject: title". Applied to today's measures, the subjects resolve 288 of the 474 shared names. The other 186 (373 measures) are pairs inside one table with the same title: mostly the academic-year and program-year versions of each charge, and the in-state and all-students net prices. Those pairs are what the kind-of-school pairing joins in answers. The list is in `docs/reports/stage5b2/names_still_shared.csv`.

| Table | Subject (draft) | IPEDS table title | Measures with a shared name |
| --- | --- | --- | ---: |
| ADM | Admissions | Admission considerations, applicants, admissions, and test scores | 0 |
| AL | Academic libraries | Academic Libraries, Fiscal year 2024 | 5 |
| CDEP | Programs offered | Number of programs offered and number of programs offered via distance education, by award | 0 |
| C_A | Awards by program | Awards/degrees conferred by program (6-digit CIP code), award level, race/ethnicity, and g | 30 |
| C_B | Award recipients | Number of students receiving awards/degrees, by race/ethnicity and gender: July 1, 2023 to | 31 |
| C_C | Award recipients by level | Number of students receiving awards/degrees, by award level and by gender, race/ethnicity  | 12 |
| COST1 | Published charges | Application fees, tuition and required fees, food and housing for undergraduate and gradua | 99 |
| COST2_FINANCIALAID | Financial aid, first-time students | Financial aid for full-time, first-time degree/certificate-seeking undergraduate students, | 211 |
| COST2_NETPRICE | Net price | Average net price for full-time, first-time degree/certificate-seeking undergraduate stude | 36 |
| CUSTOMCGIDS | Custom comparison groups | Custom comparison groups | 0 |
| DRVADM | Admissions (derived) | Frequently used derived variables for admissions. Selectivity and admissions yield | 0 |
| DRVAL | Library indicators | Frequently used/derived variables Academic library indicators: Fiscal year 2024 | 5 |
| DRVC | Completions (derived) | Frequently used derived variables (C): Completions, July 1, 2023 to June 30, 2024 | 8 |
| DRVCOST | Cost of attendance (derived) | Frequently used derived variables (Cost): Total cost of attendance | 0 |
| DRVEF12 | 12-month enrollment (derived) | Frequently used derived variables (E12): 12-month enrollment, 2023-24 | 0 |
| DRVEF | Fall enrollment (derived) | Frequently used derived variables (EF): Fall enrollment 2024 | 0 |
| DRVF | Finance (derived) | Frequently used/derived variables Finance (F): Fiscal year 2024 | 0 |
| DRVGR | Graduation rates (derived) | Frequently used derived variables (GR) 150% of normal time to complete - cohort year 2017  | 0 |
| DRVHR | Human resources (derived) | Frequently used/derived variables Human resources (HR): Fall 2024 | 0 |
| DRVOM | Outcome Measures (derived) | Frequently used derived variables (OM) Award and enrollment rates of degree/certificate-se | 0 |
| EAP | Staff by occupation and tenure | Number of staff by occupational category, faculty and tenure status:  Fall 2024 | 2 |
| EF | Fall enrollment by gender and level | Gender, attendance status, and level of student: Fall 2024 | 9 |
| EFA | Fall enrollment | Race/ethnicity, gender, attendance status, and level of student: Fall 2024 | 37 |
| EFA_DIST | Fall enrollment by distance education | Distance education status and level of student: Fall 2024 | 4 |
| EFB | Fall enrollment by age | Age category, gender, attendance status, and level of student: Fall 2024 | 9 |
| EFC | Residence of first-time students | Residence and migration of first-time freshman: Fall 2024 (optional) | 0 |
| EFCP | Fall enrollment by major | Major field of study, race/ethnicity, gender, attendance status, and level of student: Fal | 32 |
| EFD | Entering class and retention | Total entering class, retention rates, and student-to-faculty ratio: Fall 2024 | 0 |
| EFFY | 12-month headcount | 12-month unduplicated headcount: 2023-24 | 33 |
| EFFY_DIST | 12-month headcount by distance education | 12-month unduplicated headcount by distance education status and level of student: 2023-24 | 4 |
| EFFY_HS | 12-month headcount, dual enrollment | 12-month unduplicated headcount of dual enrolled students by race/ethnicity and gender: 20 | 29 |
| EFIA | Instructional activity | 12-month instructional activity: 2023-24 | 0 |
| F_F1A | Finance, public (GASB) | Public institutions - GASB 34/35: Fiscal year 2024 | 42 |
| F_F2 | Finance, private nonprofit (FASB) | Private not-for-profit institutions or Public institutions using FASB: Fiscal year 2024 | 125 |
| F_F3 | Finance, for-profit | Private for-profit institutions: Fiscal year 2024 | 122 |
| FLAGS | Response status | Response status for all survey components | 3 |
| GR200 | Graduation rates (200%) | Graduation rate data, 200% of normal time to complete - cohort year 2015  (4-year) and coh | 2 |
| GR | Graduation rates (150%) | Graduation rate data, 150% of normal time to complete - cohort year 2017 (4-year) and coho | 29 |
| GR_L2 | Graduation rates, less-than-2-year schools | Graduation rate data, 150% of normal time to complete - cohort year 2020 (less-than-2-year | 9 |
| GR_PELL_SSL | Graduation rates, Pell and Stafford recipients | Graduation rate data for Pell Grant and Subsidized Stafford loan recipients, 150% of norma | 9 |
| HD | Directory | Directory information | 48 |
| IC | Institutional characteristics | Educational offerings, organization, admissions, services and athletic associations | 21 |
| ICMISSION | Mission statement | Mission statement | 0 |
| OM | Outcome Measures | Award and enrollment data at four, six and eight years for  entering undergraduate cohorts | 0 |
| S_IS | Full-time instructional staff | Full-time instructional staff, by faculty and tenure status, academic rank, race/ethnicity | 31 |
| S_NH | New hires | New hires by occupational category, race/ethnicity, and gender (Degree-granting institutio | 31 |
| S_OC | Staff by occupation | Full- and part-time staff by occupational category, race/ethnicity, and gender:  Fall 2024 | 29 |
| S_SIS | Instructional staff by rank | Full-time instructional staff, by academic rank, faculty and tenure status  (Degree-granti | 1 |
| SAL_IS | Salaries, instructional staff | Number and salary outlays for full-time nonmedical instructional staff, by  gender, and ac | 1 |
| SAL_NIS | Salaries, non-instructional staff | Number and salary outlays for full-time nonmedical  noninstructional staff by occupation:  | 0 |
| SFA | Student financial aid | Student financial aid: 2023-24 | 1 |
| SFAV | Veterans' benefits | Military Servicemembers and Veteran's Benefits, 2023-24 | 0 |
| DRVIC | Cost of attendance (earlier releases) | Frequently used derived variables (IC): Total cost of attendance | 0 |
| IC_AY | Charges, academic year (earlier releases) | Student charges for academic year programs | 0 |
| IC_PY | Charges by program (earlier releases) | Student charges by program (vocational programs) | 0 |
| IC_PCCAMPUSES | Branch campuses | Branch campus locations listed on College Navigator | 154 |
| SFA_P1 | Student financial aid (earlier releases) | Student financial aid: {Y-1}-{Y:yy} | 0 |
| SFA_P2 | Net price (earlier releases) | Student financial aid and net price: {Y-1}-{Y:yy} | 0 |
| GR_GENDER | Graduation cohorts, gender unknown | Gender unknown reported in revised cohorts | 5 |

## The 6 undecided units, for your review

| Measure | Title | Suggestion |
| --- | --- | --- |
| S_SIS.SISPROF | Professors | count (full-time instructional staff at this rank) |
| S_SIS.SISASCP | Associate professors | count |
| S_SIS.SISASTP | Assistant professors | count |
| S_SIS.SISINST | Intructors (IPEDS's spelling) | count |
| S_SIS.SISLECT | Lecturers | count |
| S_SIS.SISNORK | No academic rank | count |

All six are headcounts by rank in the table of full-time instructional staff by rank (S_SIS). As counts, they add up across schools.

## Not done in this step

You asked for items 1 and 2 before Part 5c. These decisions are recorded and waiting:
- item 3, applying the subjects (after your review of the list above);
- item 4: category rows for programs by field (CDEP), "IPEDS gives no label for this code", "IPEDS has no values for this measure".

## Size

- **Question path:** 2,418 lines (2,392 before).
- **Dictionary:** 16 term rows and 2 school groups added, 1 statement, and a draft `subject` column in `year_meaning.csv`.

## Open questions

1. Extend the calendar pairing (academic year or program) from tuition to the other charges that come in both versions: books and supplies, food and housing, other expenses. It's the same kind of dictionary rows, and it would fix the Mount Holyoke question.
2. The net-worth question needs conditions that use one measure per reporting form, grouped by form in the answer. The plan: a term reading with one measure per form (net position, total net assets, total equity) for the three reporting-form groups, applied to conditions the way it is applied to figures. Build it now, or in Part 5c?
3. The table subjects above: approve, or change any?
4. The 6 units: approve as counts?
