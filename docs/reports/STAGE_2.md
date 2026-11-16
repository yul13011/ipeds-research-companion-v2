# Stage 2 report: dictionary and directory

Nov 15, 2026

Stage 2 is done. The conventions now live in one folder of ten tables, the build loads them and checks every row against the data, and the school directory and groups are built. All 54 tests pass. Nothing is committed. Three things need your approval before Stage 3, and one finding about category codes affects the breakdown operation.

## What was built

| File | Lines | What it is |
| --- | ---: | --- |
| `dictionary/` | | Ten CSV tables, `README.md` (one line per file and per column) and `DECISIONS.md` (45 dated decisions) |
| `build/build_data.py` | 318 | Now reads its special-code rules from the dictionary, and keeps the reason per school |
| `build/build_dictionary.py` | 224 | Loads the folder, checks it against the data, builds the directory and groups |
| `tests/test_dictionary.py` | 286 | 29 tests |
| `tests/test_build_data.py` | 326 | 25 tests |
| `config.py` | 21 | Paths |
| `CLAUDE.md` | | Working rules only; the "one home for conventions" rules added, decisions moved out |
| `docs/test_questions.csv` | | 107 rows in 60 conversations, with turn order; 74 distinct questions; no session IDs or times |
| `docs/archive/` | | The workbook and the one-off conversion script. Nothing reads either |

Code that runs: 563 lines. None of it is the question path yet.

### The dictionary folder

| Table | Rows | Notes |
| --- | ---: | --- |
| `measures.csv` | 2,599 | 737 in the first version. Long descriptions included for search |
| `terms.csv` | 59 | 19 terms; one row per reading and measure |
| `school_groups.csv` | 160 | 158 groups; the national universe takes three rows |
| `group_members.csv` | 79 | Ivy League, Ivy Plus, Seven Sisters, flagships |
| `school_nicknames.csv` | 23 | From version 1 |
| `rates.csv` | 12 | All twelve now tested |
| `category_codes.csv` | 1,078 | See the finding below |
| `year_meaning.csv` | 52 | Every data table has a period |
| `outside_ipeds.csv` | 12 | Enrollment by major moved out |
| `special_codes.csv` | 36 | 17 label rules and 19 column rules |

The four merges you asked for did not complicate the loading code. Each is one extra condition.

### What the build checks

The build stops and lists every problem if a dictionary row does not fit the data. It checks that every measure, count column, group column and category column exists; that every group code occurs in the data; that every school in a member list or nickname is in the directory; that every term either has a default or asks; and that every data table has a year meaning. The real dictionary passes with no problems. Six tests confirm that a bad row stops the build.

### What the build produces for the question path

- **`directory`:** 6,072 schools, with name, alias, city, state and the 29 grouping columns that `school_groups.csv` names. The list of columns comes from the table, not from code.
- **`group_list`:** 4,931 groups a user can name. 151 come straight from `school_groups.csv`. The rest are single values: 59 states, 63 religious affiliations, 138 conferences, 434 systems, 776 metro areas, 1,030 counties and 2,280 cities.
- **`group_membership`:** which schools are in each group. Two groups combine by taking the schools in both. "Public two-year colleges in the Southeast" gives 287 schools.
- **`value_labels`:** every coded value with its IPEDS label, from the codebook.
- **`_missing_reasons`:** 573,269 rows, one per cell that a special code made missing, with "Not applicable", "Not reported" or "Not available". Display only.

## Checks against your decisions

| Decision | Result |
| --- | --- |
| National universe | 5,626 schools; matches NCES |
| Census regions | Northeast 1,174; Midwest 1,350; South 2,122; West 1,288. Each of the 50 states and DC is in exactly one |
| BEA regions kept separately | Southeast is 1,502, a different group from the South |
| Small, large | 4,860 and 534 schools |
| Named lists | Ivy League 8, Ivy Plus 12, Seven Sisters 6, flagships 53 |
| Conference on any of four columns | The Big East has 11 schools, none of them through football |
| All religious affiliations | 63 loaded |
| Declined groups | Four, each with "IPEDS has no flag for this group." and no members |
| R1 | 187 schools (Carnegie 2025); the 2021 group is 146 and is used only on request |

## For your approval

### 1. The column-keyed special-code list (A4, A5)

These 19 rows are in `special_codes.csv` with `applies_by` = "table and column". All are set to missing.

| Table | Column | Code | Shown as | Cells | What the column is |
| --- | --- | --- | --- | ---: | --- |
| HD | F1SYSNAM | -2 | Not applicable | 3,744 | System name: school is not in a system |
| HD | F1SYSNAM | -1 | Not reported | 36 | System name |
| HD | CLOSEDAT | -2 | Not applicable | 6,004 | Date closed: school has not closed |
| HD | OPEID | -2 | Not applicable | 37 | OPE ID |
| HD | EIN | -1 | Not reported | 78 | Employer ID number |
| HD | NEWID | -2 | Not applicable | 6,045 | ID of the school it merged into |
| COST1 | PRGMOFR | -2 | Not applicable | 3,780 | Number of programs offered |
| FLAGS | IDX_C, IDX_E12, IDX_COS, IDX_SFA, IDX_GR, IDX_GR2, IDX_OM, IDX_ADM, IDX_HR, IDX_EF, IDX_F, IDX_AL | -2 | Not applicable | 5,418 to 6,072 each | ID of the parent institution for each survey component |

The "Shown as" wording is mine, following the usual IPEDS reading of -1 and -2, because the codebook has no label for these columns. Please correct any that are wrong.

### 2. The flagship list (B12)

53 schools, from version 1. The app states that flagship is not an IPEDS category.

| State | School | State | School |
| --- | --- | --- | --- |
| AK | University of Alaska Fairbanks | MT | The University of Montana |
| AL | The University of Alabama | NC | University of North Carolina at Chapel Hill |
| AR | University of Arkansas | ND | University of North Dakota |
| AZ | University of Arizona | NE | University of Nebraska-Lincoln |
| CA | University of California-Berkeley | NH | University of New Hampshire-Main Campus |
| CO | University of Colorado Boulder | NJ | Rutgers University-New Brunswick |
| CT | University of Connecticut | NM | University of New Mexico-Main Campus |
| DE | University of Delaware | NV | University of Nevada-Reno |
| FL | University of Florida | NY | Stony Brook University |
| GA | University of Georgia | NY | University at Buffalo |
| HI | University of Hawaii at Manoa | OH | Ohio State University-Main Campus |
| IA | University of Iowa | OK | University of Oklahoma-Norman Campus |
| ID | University of Idaho | OR | University of Oregon |
| IL | University of Illinois Urbana-Champaign | PA | Pennsylvania State University-Main Campus |
| IN | Indiana University-Bloomington | RI | University of Rhode Island |
| IN | Purdue University-Main Campus | SC | University of South Carolina-Columbia |
| KS | University of Kansas | SD | University of South Dakota |
| KY | University of Kentucky | TN | The University of Tennessee-Knoxville |
| LA | Louisiana State University and A&M College | TX | Texas A&M University-College Station |
| MA | University of Massachusetts-Amherst | TX | The University of Texas at Austin |
| MD | University of Maryland-College Park | UT | University of Utah |
| ME | University of Maine | VA | University of Virginia-Main Campus |
| MI | University of Michigan-Ann Arbor | VT | University of Vermont |
| MN | University of Minnesota-Twin Cities | WA | University of Washington-Seattle Campus |
| MO | University of Missouri-Columbia | WI | University of Wisconsin-Madison |
| MS | University of Mississippi | WV | West Virginia University |
|  |  | WY | University of Wyoming |

There is no school for DC. Indiana, New York and Texas have two each.

### 3. The two "faculty" definitions (C2)

Both come from the staff table `EAP` (employees by assigned position, fall 2024). Each is one row per school, picked by the category column `EAPCAT`, and read from the column `EAPTOT` (total employees). They are loaded with status "pending owner approval" and are not used.

| Option shown to the user | Row | Column | Yale, total | Yale, full-time | Yale, part-time |
| --- | --- | --- | ---: | ---: | ---: |
| Instructional staff | `EAPCAT` = 21000, "Instructional staff, total" | `EAPTOT` | 3,800 | 2,995 | 805 |
| All staff with faculty status | `EAPCAT` = 10010, "All staff, With faculty status" | `EAPTOT` | 5,735 | 4,688 | 1,047 |

These match version 1's Yale faculty check exactly. Two things to know:

- **Medical school staff are included in both.** `EAPTOT` counts all employees. The table has separate columns that exclude the medical school (`EAPTYP`) and that count only the medical school (`EAPMED`).
- **Full-time and part-time** are separate columns (`EAPFT`, `EAPPT`) on the same rows, if you want the answer to show the split.

## Findings

### Rates: all twelve match NCES

Each rate was computed by summing the counts over the national universe and dividing.

| Rate | From counts | NCES | Schools |
| --- | ---: | ---: | ---: |
| Full-time retention | 0.7786 | 0.779 | 5,119 |
| Part-time retention | 0.4695 | 0.469 | 3,523 |
| Admission rate | 0.5904 | 0.59 | 1,863 |
| Admissions yield | 0.1939 | 0.194 | 1,860 |
| Graduation within 150%, four-year schools | 0.6097 | 0.61 | 2,155 |
| Bachelor's six-year graduation | 0.6479 | 0.648 | 1,842 |
| Pell recipients' bachelor's six-year graduation | 0.5289 | none in the tab | 1,910 |
| Undergraduates awarded Pell grants | 0.3236 | 0.324 | 5,372 |
| Undergraduates awarded federal loans | 0.2778 | 0.278 | 5,372 |
| Undergraduates awarded grant aid | 0.6134 | none in the tab | 5,372 |
| Full-time first-time students awarded any aid | 0.8514 | 0.851 | 5,138 |
| Award within eight years, OMCHRT 50 | 0.4732 | 0.473 | 3,473 |

Two graduation figures differ in the fourth decimal from the plan's test table (0.6096 and 0.6477 there) because the plan used the 5,692-school universe. Both still round to the NCES figure. A test now checks all ten rates that have an NCES figure.

One gap: the 150% graduation rate has counts only for four-year schools. A group rate for two-year colleges, which the question log asks for ("All public 2-year colleges. Graduation rate."), needs a row with the two-year cohort codes. The codebook gives them as `GRTYPE` 30 (completers) over 29 (adjusted cohort). I have not added the row.

### Category codes: "total or part" is not enough for several tables

I tested whether the rows marked "part" add up to a row marked "total", school by school. This could be tested for the 12 category columns that are the only key in their table. The other 23 sit in tables keyed by two to five category columns at once, where the test does not apply.

| Result | Columns |
| --- | --- |
| Parts add up to the total at every school | `EFC.EFCSTATE` (state of residence), `EFFY_DIST.EFFYDLEV`, `GR_PELL_SSL.PSGRTYPE`, `OM.OMCHRT`, `SAL_IS.ARANK` |
| Parts overlap: their sum exceeds every total | `EFA.EFALEVEL` (fall enrollment by level and attendance), `EFFY.EFFYALEV`, `GR.GRTYPE`, `S_SIS.FACSTAT` |
| Parts do not cover the total | `EFA_DIST.EFDELEV` (adds up at 269 of 3,372 schools) |
| Nothing to compare | `C_C.AWLEVELC` (no row marked total), `EF.EFLEVEL` (all nine rows marked total) |

What this means: in tables such as fall enrollment, the codes form a hierarchy with several levels of subtotal, cut more than one way (by level, by attendance, by degree-seeking status). A single "total or part" flag cannot say which codes together make one clean breakdown. The roles were guessed from label wording, as the workbook said.

This matters for one operation in Stage 3, "breakdown by category". If it summed every "part" it would double count. The other operations are not affected, because rates and group totals name their exact codes in `rates.csv`.

I have not changed anything. One way to fix it, for you to consider as a change order: add a column to `category_codes.csv` naming the breakdown a code belongs to (for example "by level" or "by attendance status"), filled for the breakdowns users ask about and left blank otherwise. A breakdown would then use only the codes of one named set, and the build could test that each set adds up to its total.

### Measures that carry their own year

378 measures name a year in their title that differs from, or is more specific than, their table's period. Net price is the main case: the 2024-25 net price table holds figures for 2023-24, 2022-23 and 2021-22. I added a `period` column to `measures.csv` and filled it from the year at the end of the IPEDS title, so that results state the right period. 15 of these are first-version measures. This was done by script from the titles and is worth a look.

For later: when more years are stacked, this column will need to become a rule ("one year before the release") and not a fixed year.

## Open questions

1. **Lists in one cell.** You said no semicolon lists for term readings, and there are none. Two columns do hold short lists: `words` (what users say, separated by semicolons, as in the workbook) and `codes` (separated by commas, as you wrote the Census states). If you want those as one row per item too, say so; it would add about 450 rows across three tables.

2. **Words removed under B15.** I removed "universities" from four-year, "public universities" from public four-year, and "private colleges" from private nonprofit four-year. I kept phrases where another word carries the meaning: "community colleges", "liberal arts colleges", "tribal colleges", "land-grant universities", "doctoral universities". Please confirm that is the line you want.

3. **Faculty salary caveat.** The draft said to "always add the caveat" about medical-school staff, but did not give the wording. The salary table's title says "nonmedical instructional staff". I need the sentence you want shown.

4. **"Degrees awarded" total.** The draft says to return degrees by level "with a total". The derived table has no total column, and adding the levels is a calculation across measures, which is not in this slice. For now the reading returns the five levels without a total. A sixth level, "Doctor's degree - other", was not in the draft list and is left out.

5. **Out-of-state tuition.** The draft says out-of-state tuition "is in COST1" but does not name the variable, so "tuition" has only its default reading.

6. **Graduation rate default by level.** The default depends on the school: six-year bachelor's rate for four-year schools, the 150% rate for two-year and less-than-two-year schools. For a group that mixes levels, such as "all colleges in Ohio", the table does not say which to use. I would have the app ask in that case. Please confirm.

7. **City groups.** A city is matched by name only, so "Springfield" covers every Springfield. A user who names the state too gets the right one, because the two groups combine.

8. **Nickname kinds.** Version 1 has three kinds, and I kept them: "direct" resolves without asking; "alias" (Brown, Columbia, Penn, Cornell) suggests the school but still shows the picker when other schools match; "picker" only supplies a search phrase. Please confirm that reading of "alias".

## Test results

54 tests, all passing, in 26 seconds.

- **Build and cleaning (25):** as before, plus tests for column-keyed rules and for the per-school missing reasons. The count of reasons equals the count of cells set to missing.
- **Dictionary loader on made-up data (14):** groups by one code, several codes, any of several columns, several rows that must all hold, single values with codebook labels, member lists, declined groups, combining two groups, and six kinds of bad row that must stop the build.
- **Real dictionary (15):** the folder holds exactly the agreed files; the database copy matches the CSV files; the dictionary fits the data; the directory covers every school; and each of the decisions in the table above.

## Next: Stage 3

Stage 3 is the question path. Before it starts I need your answers on the three approvals, and a decision on the category-code finding, since it decides how "breakdown by category" is built.
