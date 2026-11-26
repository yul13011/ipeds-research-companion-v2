# Stage 6, part 6.0: change order 1 (years held; trends and earlier-year columns)

Date: 2026-11-25. Your decisions are in `dictionary/DECISIONS.md`: "Stage 6 begins", "Part 6.0 draft approved", and "log 1.1 and follow-up item 31". Committed locally; not pushed.

## Done when (from the work order)

| Check | Result |
| --- | --- |
| Log 1.1 passes | **Yes, as acceptable.** It shows the years held (fall 2015 to fall 2024, 10 releases), with the comparison of the eight Ivies for the latest year offered as a button. The "right" reading, both shown together, is item 31 in Part 6a |
| Log 11.1 passes | **Yes, as acceptable.** The model asked which cost of attendance was meant. Its options would now read correctly, but the question is not answered directly |
| The four new trend-gap questions pass | **3 of 4.** "Which years of graduation rates do you have for Yale?", "What years of net price data are available?" and "How has net price at Harvard changed over the last ten years?" pass. **"How has the total cost of attendance at MIT changed since 2015?" fails:** see "Did not work as planned" |
| Yale's net price for 2022-23 is $26,044 | **Yes.** Whether asked by year or as "two years before", it now comes from the 2023-24 release's own figure (test) |
| The question set (IPEDS_STAGE=6.0) shows no new wrong readings | **None caused by Part 6.0.** Four wrong readings were right in all four runs after Part 5g; none comes from this change (below) |

## What was built

**The two new columns** (as approved: 430 measures, 135 families).
- **`own_column` and `years_back`** in `measures.csv`, with README entries and a build check that each named own column exists and names itself.
- **A new `note` column**, never shown to users. It records the GRN4G0 codebook title error, since `statement` is shown on every answer.

**Trends** (trend.py).
- **Each year comes from that release's own column.**
- **Years no loaded release's own column covers** come from the earliest release that holds the figure. Those years are marked, with "… as reported in the 2015-16 release" (or the 2021-22 release for other-campus charges).
  - For example, Harvard's net price for 2012-13 ($16,445) and 2013-14 ($15,095) now appear.
  - A figure split by kind of school (net price, public and private) uses that release's school lists.

**Earlier-year columns in a request** (resolve.py, `own_columns`).
- **One earlier-year column** (for example NPGRN1, "the year before") becomes its own column, in the year it holds, from the release that published it.
- **Several earlier-year columns of one figure named together** become one trend, with the right release for each year. This is what went wrong in log 11.1 in Part 5g.
- **A year the user gave is kept.**

**Years held** (resolve.py, fetch.py, show.py).
- **Every "what data exists" answer has a "Years held" column,** and the message names the years. For example:
  - "Academic year Fall 2015 to Academic year Fall 2024 (10 releases)";
  - "students who entered in fall 2009 to fall 2018 (10 releases)", for graduation rates (entering cohorts, as in trends);
  - "2014-15 to 2023-24 (10 releases); 2012-13, 2013-14 as reported in the 2015-16 release", for net price;
  - "2020-21 to 2022-23 (3 releases); 2018-19, 2019-20 as reported in the 2021-22 release", for other-campus charges.
- **Releases in between that lack a measure** are named ("not collected in …").
- **When the question names schools or a group,** the figures are offered as a button. Schools get a comparison; a group gets the ranking of its schools for the latest year.
- **One instruction line:** questions about which years are held are "what data exists" questions.

**Dictionary rows.** Seven message rows in terms.csv ("as reported", "years held" and its variants, the offer).

**Elsewhere.**
- The grader knows stages "6.0" and "7".
- Items 46 and 47 are re-marked stage 7.
- Log 1.1's expectation is now a scored answer.
- The run log now records offered buttons.

## Test results

- **320 tests, all passing.** 7 are new (`ChangeOrder1`):
  - the earlier-year column read from its own release ($26,044);
  - a ten-year trend matching each release's own figure, cell for cell, against the raw tables;
  - the years before 2015-16 with their label and marks;
  - several earlier columns becoming one trend;
  - the "Years held" column, with cohorts and labelled years;
  - the offered button running the comparison;
  - the instruction line.
- **One older test was updated.** It used an earlier-year column with no values (CHG10AY0) as its example of "IPEDS has no values for this measure". That column now reads its own release, which has values, so the test uses a measure with no values in any year.
- **Trial calls:** accepted.

## The scorecard (one run, `haiku_60_first`, IPEDS_STAGE=6.0)

| Row | Result | After Part 5g (two runs) |
| --- | --- | --- |
| Full set, scored and trend | 142 of 155 (91.6%) | 91.9% and 92.6% of 149 |
| Real users' questions (version 1's log) | 57 of 66 (86.4%) | 84.8% and 84.8% |
| The same questions as Part 5e (now 119, with log 1.1 moved to scored) | 113 of 119 (95.0%) | |
| The same 118 as Part 5e (log 1.1 left out) | 112 of 118 (94.9%) | 94.1% and 94.9% |
| Badly written set | 54 of 56 (96.4%) | 96.4% and 98.2% |
| Median turn | 6.3 s | 6.7 s and 6.3 s |
| Turns over the limit (10 s; 20 s with a search) | 7 of 242 (slowest 13.4 s) | 6 and 5 |
| Cost | $0.27 for 242 turns | $0.27 |
| Shortlist misses | 0 of 25 | 0 |

**The full set has 155 questions:** the six new questions count from this run, and log 1.1 moved from trend to scored. Manual review: 13 turns read by hand, the rest carried over where the reading was the same.

**Right now, wrong in both runs after Part 5g:** log 1.1 (years held), log 11.1 (now a clarifying question), and log 14.3.

**Wrong now, right in all four runs after Part 5g:**
- **log 55.1** (FRCC against Colorado community colleges, "trends over time"): answered for fall 2024 only. It was also wrong in Part 5e run 1; a reading that varies.
- **"Does Smith College offer … on-campus childcare?":** childcare left out, as in Part 5f run 1; a reading that varies.
- **"Show fall enrollment for the Big Ten plus Notre Dame":** a new question. It is expected to ask a clarifying question until Part 6a; it showed Notre Dame beside the Big Ten.
- **The MIT cost question:** a new question; below.

None involves the years or the earlier-year columns.

## Did not work as planned

**"How has the total cost of attendance at MIT changed since 2015?"**
- **What happened:** the model chose the cost of attendance in the 2024-25 net price table (Title IV students, COAT42), which the releases hold for three years only. The code now reads it correctly: 2021-22 to 2023-24, labelled "as reported in the 2024-25 release". Earlier years show as not collected.
- **What was wanted:** the published total price (DRVCOST.CINSON, total price for in-state students living on campus), which every one of the ten releases holds.
- **Why it isn't fixed:**
  - This is a choice between two IPEDS figures that both answer to "cost of attendance": the price for students awarded Title IV aid, and the published price.
  - Which one "cost of attendance" means is a convention, so it's your decision. I didn't add a rule.
  - The term "cost" already offers a cost profile, which includes the published total price. But this question names "total cost of attendance", which matches the Title IV column's own title.

## Line counts

| | End of Stage 5 | Now |
| --- | --- | --- |
| The question path | 3,676 | 3,794 (+118: resolve.py +69, trend.py +47, interpret.py +2) |
| The page (app.py) | 161 | 161 |
| The dictionary build | 1,021 | 1,029 (+8, the check) |

New scripts: `earlier_year_draft.py` (the draft, kept for the record). `stage4_run.py` now records offered buttons.

## Open questions

1. **"Cost of attendance" in a question:**
   - the published total price (DRVCOST, ten releases);
   - the Title IV cost of attendance (net price table, three years);
   - or ask which?

   A terms.csv row would settle it, and the MIT question would then pass.
2. **Push Part 6.0 after your review?** Then Part 6a's proposal. It now has four gaps: a group plus named schools, a trend that names no measure, follow-ups that refer to schools named several turns earlier, and item 31, two requests answered together.

## After your approval: cost of attendance (2026-11-25)

**The convention, as built** (terms.csv, term `cost`; DECISIONS.md "Part 6.0 approved; cost of attendance"):

| Reading | Measure | Default |
| --- | --- | --- |
| Published total price (on campus, in-state), new | DRVCOST.CINSON | yes |
| Cost profile (total price, tuition, net price) | 5 rows, unchanged | no (was yes) |
| Cost of attendance used to calculate net price, new | COAISGS2 (public), COAGS2 (private) | no; used only when asked |
| Cost of attendance for students awarded Title IV aid, new | COAIST42 (public), COAT42 (private) | no; used only when asked |

"COA" is added to the term's words. The default reading's statement is shown in "Interpreted as": "Cost of attendance is read as the published total price for full-time, first-time undergraduates living on campus, in-state for public schools."

**What the default alone did not do.**
- The model picks the net-price-table column directly, because its own title is "Total cost of attendance", and a term's default applies only when the model goes through the term.
- A blanket rule ("a measure in a non-default reading becomes the default") would break other terms; "undergraduate enrollment", for example, is a deliberate reading of "enrollment".
- **So terms.csv has a new column, `only_when_asked`,** set on the two net-price-table readings only. If the model names one of their measures without choosing that reading, the code uses the term's default instead, and shows the default's statement.
- Choosing the reading is how the model says the question asked for it.
- A build check makes sure such a term has a default.
- A slip found on the way is also fixed: a chosen reading now shows its own statement, not the first reading's.

**Tests:** 322, all passing. 2 are new: the default is the published total price, with MIT's ten years; and the net-price-table cost gives the default unless its reading is chosen, in which case it keeps it, with its own statement.

**The run** (`haiku_60_cost`, IPEDS_STAGE=6.0):

| Row | This run | First Part 6.0 run |
| --- | --- | --- |
| Full set, scored and trend | 146 of 155 (94.2%) | 91.6% |
| Real users' questions | 59 of 66 (89.4%) | 86.4% |
| The same as Part 5e (119; without log 1.1: 113 of 118, 95.8%) | 114 of 119 (95.8%) | 95.0% |
| Badly written set | 55 of 56 (98.2%) | 96.4% |
| Median turn | 6.7 s | 6.3 s |

**The MIT question:** a wrong reading before, a clarifying question now, which its expectation accepts. But the two options it offered are the two net-price-table costs. The model took "total cost of attendance" as asking for that cost specifically, so it chose those readings, and the published total price wasn't among the options.

So the convention is applied when the model names the measure alone, and not when it picks the reading itself. One way to close this, not built: the shortlist marks a reading used only when asked ("used only when the question asks for it specifically"), so the model sees the convention. That's one line in interpret.py.

**The other cost questions that changed:**
- "How much does it cost to attend Harvard College in 2024-25?" (log 13.1, and the same question in the eval set) and "nyu how much does it cost to go there" now give the published total price, $89,315 and $92,062, with the statement, where they gave the cost profile before. Right by the convention.
- Of the other questions on cost, tuition, net price or price, none changed between right and wrong. "cal state tuition" went from a correct decline to a clarifying question; both are acceptable.

**Changes not about cost:**
- **Two went from right to wrong:**
  - "What is college scorecard" (the model replied "choose an option" with none pending: a reply the app can't read);
  - "How many of Yale's admitted students submitted ACT scores" (the model declined, reading "admitted" strictly against IPEDS's first-time students).
- **Six went from wrong to right:** log 55.1, 58.7 and 62.3, "just Yale and Harvard", Smith's childcare, and "hi can u tell me abt stanford".

All of these have gone both ways in earlier runs; none touches the cost rows.
