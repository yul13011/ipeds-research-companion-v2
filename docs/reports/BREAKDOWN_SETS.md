# Breakdown sets: proposal and test results

Nov 15, 2026

Your change order is applied and recorded in `dictionary/DECISIONS.md`. This report covers the breakdown sets: how the dictionary names them, the twelve drafts, and how each tested. Every draft adds up to its total. Nothing here is used by the question path until you approve it. All 65 tests pass, and a first local commit has been made.

## How a set is written in the dictionary

IPEDS stores breakdowns two ways, so the dictionary names sets in two places. Both use the same two words, `breakdown_set` and `set_total`.

### Breakdowns stored as rows: `category_codes.csv`

Three new columns. Only the part rows are marked; the total is named, not marked.

| Column | What it holds |
| --- | --- |
| `breakdown_set` | The set's name, on each part row. A code can be in one set |
| `set_total` | The code of the row the parts add up to, or `sum of parts` when the data has no total row |
| `set_fixed` | In tables keyed by several category columns, the values the other columns are held at, such as `CIPCODE = 99; MAJORNUM = 1` |

### Breakdowns stored as columns: `measures.csv` (the plan's Addition B)

Race and ethnicity, and gender, are columns, not rows. The same pattern repeats in every table that has them. Two new columns:

| Column | What it holds |
| --- | --- |
| `breakdown_set` | The set's name, on each part column. All columns of one table with the same name form the set |
| `set_total` | The column the parts add up to, or `sum of parts` |

A set is identified by its table and its name. "By race and ethnicity" in the fall enrollment table and in the completions table are the same kind of breakdown applied to different counts.

The two kinds combine. "Yale's undergraduate enrollment by race" is the column set "By race and ethnicity" read on the undergraduate row of the fall enrollment table. A test confirms it returns nine categories adding up to 6,814, the figure in the plan.

### How the build tests a set

- **Row sets:** at each school, do the part rows add up to the total row? The test runs for every count column in the table, and the set is loaded only for the columns that pass at every school. This means a percentage column is never offered as a breakdown of counts, with no rule about which columns are counts.
- **Column sets:** on each row of the table, do the part columns add up to the total column?
- **Additive sets:** there is no total in the data, so there is nothing to test. The result shows a total computed by summing the parts.
- **A set that fails is not loaded,** and the build records how many schools or rows failed.

## Sets stored as rows

All nine pass at every school tested, for the main count column and for the other count columns listed.

| Set | Table and column | Parts | Total | Held fixed | Schools tested | Count columns that add up |
| --- | --- | --- | --- | --- | ---: | --- |
| Fall enrollment by level | `EFA.EFALEVEL` | Undergraduate (2), Graduate (12) | All students (1) | none | 5,842 | 34 of 34 |
| Fall enrollment by attendance status | `EFA.EFALEVEL` | Full-time (21), Part-time (41) | All students (1) | none | 5,842 | 30 of 34 |
| Fall enrollment by age | `EFB.EFBAGE` | Eleven age bands (3 to 6, 8 to 14) | All ages (1) | All students (`LSTUDY` = 1) | 2,576 | 9 of 9 |
| First-time students by state of residence | `EFC.EFCSTATE` | 62 states and other places | All first-time students (99) | none | 5,386 | 2 of 2 |
| Awards by level | `C_A.AWLEVEL` | Twelve award levels | Degrees and certificates total (15) | All fields, first major (`CIPCODE` = 99, `MAJORNUM` = 1) | 5,869 | 30 of 30 |
| Degrees by field of study | `C_A.CIPCODE` | 38 two-digit fields | All fields (99) | Degrees total, first major (`AWLEVEL` = 12, `MAJORNUM` = 1) | 3,963 | 30 of 30 |
| Outcome measures by Pell status | `OM.OMCHRT` | Pell (51), non-Pell (52) | Total entering (50) | none | 3,590 | 19 of 26 |
| Full-time instructional staff by rank | `SAL_IS.ARANK` | Six ranks | All instructional staff (7) | none | 3,782 | 36 of 54 |
| Staff by occupation | `EAP.OCCUPCAT` | Twelve occupation groups | All staff (100) | All faculty statuses (`FACSTAT` = 0) | 5,837 | 9 of 9 |

Yale's fall enrollment as a check: 6,814 undergraduate plus 8,750 graduate is 15,564; 15,121 full-time plus 443 part-time is 15,564.

The count columns that do not add up, and why that is right:

- **Attendance status, 4 columns:** the four "gender unknown or another gender" columns, which IPEDS collects for all students but not by attendance.
- **Outcome measures, 7 columns:** percentages (percent awarded, percent still enrolled). Percentages do not add.
- **Staff by rank, 18 columns:** average salaries and salary outlays equated to nine months. Averages do not add.

## Sets stored as columns

| Set | Parts | Tables | Result |
| --- | --- | --- | --- |
| By race and ethnicity | Nine categories, American Indian or Alaska Native through U.S. Nonresident | 11: fall enrollment, enrollment by major, 12-month enrollment, dual enrollment, completions (three tables), graduation rates, three staff tables | Adds up on every row with detail, in all 11 |
| By gender | Men, Women | 13: the same 11, plus two more fall enrollment tables | Adds up on every row with detail, in all 13 |
| Degrees by level | Associate's, Bachelor's, Master's, and three kinds of Doctor's degree | `DRVC` | Additive: no total column in the data, so the result shows a computed total |

The largest table tested is completions by program, where both sets add up on all 1,688,471 rows.

## Three things to decide

### 1. Rows where IPEDS collects no detail

In the graduation-rate table, 3,623 of 51,011 rows have a total but no race or gender detail at all. They are the three "completers within 100% of normal time" rows (`GRTYPE` 35, 36, 37); the codebook labels them "not available by race or gender". On the other 47,388 rows both sets add up exactly.

I built the test to count such rows separately and not as failures. A breakdown asked for on one of those rows would show the total and say the detail is not collected. Under a strict reading of your rule, the graduation-rate race and gender sets would not be loaded at all, and graduation rate by race is one of the breakdowns the Yale benchmark needs. Please confirm the looser reading, or tell me to make it strict.

### 2. Gender: unknown and another gender

Fall enrollment, 12-month enrollment and one completions table also report "gender unknown" and "another gender". My first draft put them in the gender set, and the set failed: in the data, men plus women already equal the total, and the unknown and another-gender counts are reported beside it, not inside it. I removed them from the set, and it now passes.

The effect is that a gender breakdown shows men and women only. The other counts remain available as measures in their own right. If you want them shown alongside the breakdown, that is a display choice for Stage 3 and needs no change to the set.

### 3. One code, one set

A code can be in only one set, because the set name sits on the code's row. That has two consequences in the drafts:

- **Enrollment by age is for all students.** Undergraduates by age and graduates by age use the same age codes with a different fixed value, so they would need the same codes in three sets.
- **Degrees by field is for all degrees.** Bachelor's degrees by field uses the same field codes held at a different award level.

Two ways to lift this, if you want either: let `set_fixed` name a default that the request may change, with the build testing the set at every value of the other columns; or keep one set per code and accept the limit for this slice. I have built the second and recommend deciding on the first only after the decline log shows the demand.

## What else changed in this change order

| Change | Result |
| --- | --- |
| Faculty: in use, always ask, with split | Six rows; Yale 3,800 (2,995 full-time, 805 part-time) and 5,735 (4,688 and 1,047) |
| Peers default | Uses the school's own comparison group when it has one |
| Graduation rate for mixed groups | Three options added, offered only when a group mixes levels |
| Tuition, out-of-state reading | `COST1.chg3ay3` added |
| Degrees | Sixth level added |
| B15 correction | "Public universities", "private universities", "private colleges" added with their statements |
| Two-year graduation rate | Added: 233,174 of 546,398, or 0.4267; NCES 0.427 |
| Rate statuses | All thirteen marked tested |

Three findings from doing these:

- **Comparison groups: 2,326 schools, not 2,845.** The comparison-group table lists 2,845 schools, but 519 of them are not in the 2024-25 directory. The plan's figure of 2,845 counted those. The new group "Has an IPEDS comparison group" has 2,326 members.
- **Out-of-state tuition is consistent with the default.** The default reading is the in-district figure at every school. Out-of-state tuition is reported by exactly the same 3,388 schools and is never lower. At private schools the two are almost always equal.
- **NCES also publishes a less-than-two-year graduation rate** (0.712). I have not added a row for it. The codebook does not give that level its own cohort codes in the way it does for two-year and four-year schools, so I would want to look before proposing one.

## Tests and line counts

65 tests, all passing, in 34 seconds. Eleven are new:

- On made-up data: a row set that adds up is loaded using only its fixed rows; one that does not add up is not loaded; an additive set is loaded untested; a column set is tested on every row with detail; a set whose rows disagree about the total stops the build; a group of schools that have rows in a table.
- On the real data: each of the nine row sets adds up for its main count column; a percentage column is not offered as a breakdown of counts; the column sets load and Yale's undergraduates by race add up to 6,814; every item of this change order is in the tables; out-of-state tuition sits consistently beside the default.

Code that runs: 660 lines (`build_data.py` 318, `build_dictionary.py` 321, `config.py` 21). Tests: 735 lines.

## Commit

A first local commit has been made as a restore point. Nothing was pushed. The raw question log, the local database and the logs folder are not in it.

## Waiting on you

1. Approve, change or drop each of the twelve sets.
2. The three decisions above: rows with no detail, gender unknown, and one code per set.

Stage 3 has not been started.
