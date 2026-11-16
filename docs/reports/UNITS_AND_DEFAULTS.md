# Units and default rows: two lists for approval

Nov 16, 2026

The dictionary additions from your change order are made and recorded in `dictionary/DECISIONS.md`. Two lists need your approval before Stage 3 uses them: the units, and the default rows. All 76 tests pass. No Stage 3 code has been written, and nothing new has been committed.

## 1. Units

`measures.csv` has a new `unit` column for the 762 first-version measures. The full list, one row per measure, is in [unit_list.csv](unit_list.csv), which opens in Excel.

### How the draft was made

From the codebook format first, then whole words in the IPEDS title, in this order:

1. Coded answers (format `Disc`) are `coded`.
2. Text, directory identifiers and locations, and SAT and ACT percentile scores are left blank, so they are never summed.
3. "Ratio" makes `ratio`.
4. "Per FTE" makes `average`.
5. "Percent", "rate" or "yield" makes `percent`.
6. "Average", or a published price ("tuition and fees", "total price", "published"), makes `average`.
7. "Dollars", "total amount", "revenue", "expense", "endowment" or "salary" makes `dollars`.
8. Anything else is `count`.

### The result

| Unit | Measures | May be summed across schools |
| --- | ---: | --- |
| count | 193 | yes |
| dollars | 26 | yes |
| percent | 356 | no |
| average | 85 | no |
| ratio | 4 | no |
| coded | 58 | no |
| blank | 40 | no |

By table:

| Table | count | dollars | percent | average | ratio | coded | blank |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ADM admissions | 27 | | 2 | | | 12 | 15 |
| DRVADM admission rates | | | 12 | | | | |
| DRVAL libraries | 5 | | 13 | 1 | | | |
| DRVC completions | 21 | | | | | | |
| DRVCOST, COST1, COST2 prices | | | | 18 | | | |
| DRVEF fall enrollment | 35 | | 51 | | | | |
| DRVEF12 12-month enrollment | 22 | | 39 | | | | |
| DRVF finance | | 6 | 69 | 41 | 3 | | |
| DRVGR graduation rates | | | 36 | | | | |
| DRVHR staff and salaries | 19 | | | 7 | | | |
| DRVOM outcome measures | | | 108 | | | | |
| EFD retention | 12 | | 3 | | 1 | | |
| F_F1A, F_F2 endowment | | 2 | | | | | |
| HD directory | | | | | | 46 | 25 |
| SFA financial aid | 32 | 18 | 23 | 18 | | | |
| Multi-row tables (see below) | 20 | | | | | | |

### Calls worth your eye

- **Published prices are `average`, not `dollars`.** Tuition, total price and out-of-state tuition (14 measures) are amounts per student. Adding them across schools means nothing, so a group figure is declined and the per-school list is offered. The title words alone would have made them `dollars`.
- **Only 26 measures are `dollars`:** total core revenues and expenses (one per finance form), total aid amounts in `SFA`, and endowment assets. These add up across schools.
- **Per-FTE figures are `average`**, such as expenses per student and endowment per student (42 measures).
- **Full-time-equivalent counts are `count`.** Staff FTE and enrollment FTE add up across schools.
- **SAT and ACT percentile scores are blank** (15 measures). They are none of the six units and must never be summed. If you want a seventh unit such as `score`, say so; blank already behaves correctly.
- **Average net price is `average`.** None of the four net price measures has a row in `rates.csv`, so a group net price is declined under your rule. NCES does publish group averages of net price, weighted by the number of aided students. If you want that later, it needs a rate row naming the weight, and you will need to decide it.

### 25 measures added to the first version

The approved terms and breakdown sets point to measures that were marked priority 2 or 3, so they were "not set up in this app yet". I marked them first-version so the approved readings work. Please confirm.

| Why | Measures |
| --- | --- |
| Named by an approved term | Faculty counts `EAP.EAPTOT`, `EAPFT`, `EAPPT`; out-of-state tuition `COST1.chg3ay3`; endowment `F_F1A.F1H02`, `F_F2.F2H02`; net price for Title IV students `COST2_NETPRICE.NPIS42`, `NPT42`; enrollment by major `EFCP.EFTOTLT` |
| Main count of an approved breakdown set | The "grand total" column of `EFA`, `EF`, `EFB`, `EFC`, `EFFY`, `EFFY_HS`, `C_A`, `C_B`, `C_C`, `GR`, `S_IS`, `S_NH`, `S_OC`, `SAL_IS`; Outcome Measures cohort and eight-year awards `OM.OMACHRT`, `OMAWDN8` |

The race and gender part columns stay unmarked. The breakdown step reads them from the set, so the model never needs to pick them.

## 2. Default rows

`category_codes.csv` has a new `default` column. A default is used when a request does not name that column.

### First, which columns need one

Each multi-row table has category columns that pick out a row, and sometimes others that only describe it. In the staff table `EAP`, for example, the combined code `EAPCAT` picks the row, and `OCCUPCAT` and `FACSTAT` repeat what it already says. The build now works out, from the data, the fewest columns that pick one row per school. Only those columns take a default. A default on a describing column would contradict the row the request names, so the build refuses one.

The build also checks that the defaults together pick exactly one row per school. All 19 pass.

### The list

| Table | Column | Default code | Label |
| --- | --- | --- | --- |
| C_A completions by program | AWLEVEL | 15 | Degrees/certificates total |
| | MAJORNUM | 1 | First major |
| | CIPCODE | 99 | Grand total (all fields) |
| EAP staff by position | EAPCAT | 10000 | All staff |
| EF fall enrollment, summary | EFLEVEL | 10 | All students total |
| EFA fall enrollment by level | EFALEVEL | 1 | All students total |
| EFA_DIST distance education | EFDELEV | 1 | All students total |
| EFB enrollment by age | EFBAGE | 1 | All age categories total |
| | LSTUDY | 1 | All students total |
| EFC residence of first-time students | EFCSTATE | 99 | All first-time degree/certificate-seeking undergraduates |
| EFFY 12-month enrollment | EFFYALEV | 1 | All students total |
| EFFY_DIST 12-month distance education | EFFYDLEV | 1 | All students total |
| GR_PELL_SSL graduation by Pell status | PSGRTYPE | 1 | Total 2018 cohort, four-year institutions |
| OM outcome measures | OMCHRT | 50 | Total entering, Total |
| S_IS full-time instructional staff | SISCAT | 1 | All full-time instructional staff |
| S_NH new hires | SNHCAT | 10000 | All full-time new hires |
| S_OC staff by occupation | STAFFCAT | 1100 | Grand total |
| S_SIS instructional staff, faculty status | FACSTAT | 0 | All full-time instructional staff |
| SAL_IS salaries | ARANK | 7 | All instructional staff total |

### No default, so the app asks

| Table | Column | Why |
| --- | --- | --- |
| C_C students receiving awards | AWLEVELC | There is no total row. A student can receive awards at more than one level, so the parts cannot be added up |
| EFCP enrollment by major | EFCIPLEV | The code packs a field and a student level together, and there is no all-fields row. The user must name a field |
| GR graduation rates | GRTYPE | Its rows are cohorts and completers, not one total. Questions about these counts come through `rates.csv` |

### Calls worth your eye

- **Completions default to degrees and certificates (15), not degrees only (12).** That follows your "overall total" rule. "How many degrees did X award?" already goes through the `degrees` term, which returns the six degree levels with a total, so it is not affected. The breakdown set "Degrees by field" keeps its own default of degrees only (12).
- **Residence of first-time students defaults to 99, all first-time students.** The other total, 58, is "US total", which leaves out students from other countries and outlying areas.
- **The Pell graduation table's default, code 1, is a four-year cohort.** Less-than-four-year schools report a separate 2021 cohort (code 4), so for them the default finds no row and the app asks.
- **The staff table defaults to all staff (10000).** The approved faculty readings name their own rows (21000 and 10010), so they are not affected.

## Other additions

| Addition | Where | Content |
| --- | --- | --- |
| Applies-to | `rates.csv` | The four graduation-rate rows name their group. Both 150% rows point to the same ready-made rate, so the build now requires each to say which schools it covers |
| No year stated | `terms.csv`, setting | The latest period |
| No group stated | `terms.csv`, setting | The national universe |
| "Top" with no number | `terms.csv`, setting | 10 |
| Ranking guard | `terms.csv`, setting | For rates, a denominator of at least 30, with a second reading "include all schools" |
| Summable units | `terms.csv`, setting | Count and dollars. This puts your summing rule in the dictionary, so code reads it rather than holding it |

Each setting carries the sentence that "Interpreted as" will show.

## Tests and lines

76 tests, all passing. Eleven are new:

- **On made-up data (3):** row keys and defaults are found; two defaults for one column stop the build; two rate rows sharing a measure without saying which schools stop the build.
- **On the real data (8):**
  - **Units:** the unit values are the six agreed; key examples are right (prices are `average`, percentile scores blank); no continuous measure is left without a unit by mistake.
  - **First version:** every measure a term names is in it.
  - **Default rows:** the defaults are as listed; the three columns without one are the three above; a describing column takes no default.
  - **Applies-to and settings:** rate rows name their schools, and the setting rows are present.

`build/build_dictionary.py` is now 400 lines. The dictionary reload takes about a minute and three quarters.

## Waiting on you

1. Approve or correct the units, including the 25 added measures.
2. Approve or correct the default rows.

On approval I'll build Stage 3. Before its first live model call I'll stop and walk you through setting the API key in Windows.
