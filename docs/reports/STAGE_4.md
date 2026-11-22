# Stage 4 report: measuring the question path

Date: 2026-11-21. Data: the IPEDS 2024-25 provisional release only. Models: Haiku (`claude-haiku-5-5`) and Sonnet (`claude-sonnet-5-5`).

This report has three parts:
1. Known answers: does the app's arithmetic reproduce published figures?
2. The question set run through the live model on both models.
3. The items still left over from the last change order.

Nothing in the path was changed during Stage 4. The defects found are listed under "Defects found", each with a proposal. They are not fixed; they wait for your decision.

## Summary

- **Known answers.** 19 NCES figures, 17 Yale figures and all 5 checks from the design's test table match through the app's own resolve and fetch steps.
  - 8 NCES figures differ. Five are within 0.06% (likely provisional versus revised data). Two are different definitions. One is the salary figure you already know about.
  - 4 NCES figures are declined by design: they are averages with no counts to combine, so there is no rates row.
  - 12 NCES figures are not set up.
- **Question set: Haiku and Sonnet do about equally well on reading.** Haiku costs a fifteenth as much ($0.09 against $1.35 for 143 turns). It is slower: 4.0 seconds per turn against 2.8.
  - Scored questions, out of 102:

    | Model | Correct answer | Correct decline | Clarifying question | Wrong reading |
    | --- | ---: | ---: | ---: | ---: |
    | Haiku | 30 | 52 | 6 | 14 |
    | Sonnet | 27 | 49 | 8 | 18 |

  - 15 of the 32 wrong readings come from three general defects in the path, not from the model. The biggest is one net-price defect, which accounts for 11 turns across both models. Right or acceptable answers (correct answer, correct decline or clarifying question) are 86% on Haiku and 82% on Sonnet now. Fixing the three path defects would bring them to about 91% and 92%.
- **Trend questions** (20 per model) are declined for years as designed: 17 on Haiku and 19 on Sonnet. The rest were a clarifying question or an answer to the single-year part. No trend question was answered with a wrong year.
- **Shortlist misses** (decision C6): 2 of the 19 turns that can be checked automatically, the same on both models.
  - The admissions applicants count was not shortlisted for "Data extract: Applicants, Admission rate".
  - The "PhD-enrolling universities" group was missing (a group, not a measure).

## 1. Known answers (no model call)

`scripts/benchmarks.py` writes each benchmark as a structured request, the same shape the model produces, and runs it through `resolve` and `fetch`. Reference values come from version 1's NCES Trend Generator exports and Yale CSVs; version 1's code is not used. Full results are in `docs/reports/stage4/benchmarks.csv`.

### NCES (2024-25 release observations)

| Result | Count | Cases |
| --- | ---: | --- |
| Match | 19 | q1, 3, 4, 5, 19, 20, 21, 25, 32, 33, 34, 35, 36, 37, 101, 102, 103, 150, 200 |
| Differs | 8 | see below |
| App declines (no rates row for an average) | 4 | q38 federal loan average, q42 distance-education percent, q220 grant average, q221 loan average |
| Split by finance form, by rule | 1 | q110 core expenses per FTE |
| Not covered | 12 | q13, 15, 17, 39, 40, 41 (total revenues and expenses: only core figures are set up); q22 (less-than-two-year rate, left out by your decision); q155; q205–208 (average tuition by control) |
| No 2024-25 value in the file | 1 | q8 |

The eight figures that differ:

| Case | NCES | App | Difference | Likely reason |
| --- | ---: | ---: | ---: | --- |
| q2 12-month headcount | 25,662,076 | 25,670,468 | +0.03% | Same 5,626 schools (q1 matches), so probably provisional data versus NCES's revised data |
| q24 awards conferred | 5,365,113 | 5,367,633 | +0.05% | Same |
| q43 12-month FTE | 16,117,442 | 16,124,697 | +0.05% | Same |
| q210 students awarded | 4,826,826 | 4,829,463 | +0.05% | Same |
| q51 full-time instructional staff | 741,767 | 740,904 | −0.12% | Same |
| q12 full-time instructional staff, degree-granting (salary table) | 624,689 | 628,128 | +0.55% | Salary-table count; NCES may exclude medical-school staff or use a different table |
| q30 people employed | 4,114,069 | 3,625,678 (degree-granting); 3,682,028 (all) | −12% | NCES likely includes graduate assistants (406,661 nationally); the app's "grand total" row excludes them |
| q50 average salary | 100,224 | 100,254 | +0.03% | Known: NCES includes administrative offices |

q110 core expenses per FTE: the app gives $32,973 (public, GASB form), $52,613 (private nonprofit, FASB form) and the for-profit figure separately. NCES combines public and private nonprofit into $38,376. The rule that splits finance figures by reporting form is yours and is in the dictionary.

### Yale

17 of 17 covered figures match. They are fall 2024 enrollment (total, undergraduate, graduate), applications, admits, matriculants, the admit rate and yield (IPEDS rounds to whole percents), the SAT 25th/50th/75th percentiles for both sections, and the 2018 bachelor's cohort, its six-year graduates and its rate.

Not covered: the SAT 10th and 90th percentiles (IPEDS does not collect them), and the 2018 cohort by gender and by Pell status (subgroup measures not set up).

### V2_PLAN.md test table

The checks not already covered above all match:

| Check | Result |
| --- | --- |
| Yale undergraduates by race | 9 categories, total 6,814 |
| Bachelor's six-year rate by control | 63.8 / 68.3 / 34.1%; the plan has 63.8 / 68.2 / 34.0 (rounding) |
| University of Michigan salary by rank | 7 rows |
| RIT's IPEDS comparison group | 11 schools; the plan said 8 |
| Lowest net price at four-year schools | Top value is now positive ($672) |

**Two defects found here, not fixed:**
- A group rate built only from counts, with no ready-made measure, is shown in the wrong unit. The Outcome Measures award-within-eight-years rate, 0.473, is formatted as "$0" instead of 47.3%. Cause: such a rate gets the unit "average".
- The graduation-rate level default overrides a measure the model stated. If the model states the overall 150% rate for four-year schools without choosing that reading, resolve switches it to the bachelor's six-year rate. This conflicts with the precedence rule (what is stated wins over a default). It did not occur in the live runs, but it would mislead a question that names the overall rate.

## 2. The question set

### What was run

- **The logged questions:** every distinct question in `docs/test_questions.csv`. Conversations were run in order with their history. A conversation made only of repeats was skipped; a repeated turn inside a conversation was run for context but not scored.
- **Version 1's evaluation set:** all 54 cases in `eval_set.py`, with their follow-up turns. I included every case rather than only the single-year ones; trend turns are scored in the trend column.

Each model ran 143 turns. Expected outcomes were written before the run, in `docs/stage4/expectations.csv`. My review of each answer is in `docs/stage4/review.csv`, and the combined scorecard in `docs/reports/stage4/scorecard.csv`. Logs are in `logs/stage4/<model>/`.

Corrections to the expectations, made after the run and shown in the review file:
- **Salary questions for 2023-24:** declining is right. Salaries in the 2024-25 release are for 2024-25, so I had expected wrongly.
- **One turn added:** the third turn of "go back to all eight" was missing from the file.
- **The ACT question:** IPEDS counts ACT submitters among enrolled students, not admitted ones. A decline that says so is graded correct, and so is an answer that shows the IPEDS label.

### Scorecard

| | Haiku | Sonnet |
| --- | ---: | ---: |
| **Scored questions** | 102 | 102 |
| Correct answer | 30 | 27 |
| Correct decline | 52 | 49 |
| Clarifying question (including school pickers) | 6 | 8 |
| Wrong reading | 14 | 18 |
| of which, path defect | 5 | 10 |
| of which, model | 9 | 8 |
| **Trend questions** | 20 | 20 |
| Correct decline | 17 | 19 |
| Clarifying question | 2 | 1 |
| Answer to the single-year part | 1 | 0 |
| Wrong reading | 0 | 0 |
| Model produced a structured request | 3 | 1 |
| **Not scored** | | |
| Greetings (2) | 2 polite declines | 2 polite declines |
| Test rows (7) | 7 declines | 7 declines |
| Chart edits (6) | 6 declines | 6 declines |
| **Cost and time** | | |
| Total cost, 143 turns | $0.093 | $1.349 |
| Cost per turn | $0.0006 | $0.0094 |
| Mean / median / slowest turn | 4.0 / 3.7 / 11.1 s | 2.8 / 2.5 / 7.2 s |
| Input tokens (of which read from the cache) | 1,315,062 (890,133) | 1,325,341 (896,446) |
| Output tokens | 82,777 | 30,875 |
| API errors | 0 | 0 |

The two models fail on different questions. Haiku wrote 2.7 times as many output tokens, mostly in longer decline reasons, which is why it is slower despite being the smaller model.

**Trend column.** The model mostly declines a trend question itself, with a reason, rather than producing a structured request: Haiku produced a request on 3 of 20 trend turns and Sonnet on 1 of 20. So "was the measure read correctly" can only be judged on those few turns. Where it could be judged, it was right. A real trend test has to wait for the multi-year slice.

### Every wrong reading

Path defects (the fix belongs in a general step):

| Model | Question | What went wrong |
| --- | --- | --- |
| both | "Compare net price for grant-aided students across the Ivy League in 2023-24", and the follow-ups "Sort them from lowest to highest" and "Go back to all eight" (5 turns on each model) | The ranking was empty. The net-price reading names two measures: the in-state net price that public schools report and the net price that private schools report. The ranking used only the first, which no Ivy has. **Defect A.** |
| Sonnet | "What is the universe with the lowest net cost?" | Same defect: the ranking left out every public school |
| Sonnet | "Is there any data helpful … institutional AI policies"; "Any variable that shows economic mobility"; "Do you have something like income after graduation" | The model correctly chose "what data exists" on a topic that the outside-IPEDS table covers. The page showed an empty table instead of the outside-IPEDS message. **Defect B.** |
| Sonnet | Naming five comparison schools for RIT (all four-year) | Asked "which level?" as if the schools were mixed. After the edit, the level check looked at a wider set than the five schools named. **Defect C.** |

Model readings:

| Model | Question | What went wrong |
| --- | --- | --- |
| both | "How many full-time and part-time instructional staff did Yale have in Fall 2024?" (logged question 7) | Showed one row only: Haiku full-time (2,995), Sonnet part-time (805). On the identical eval question, Haiku gave all three rows (total 3,800). Sonnet repeated the error there. |
| Sonnet | "Show Yale's undergrad population by race and ethnicity" | Showed all students (15,564), not undergraduates (6,814). The level was not fixed to undergraduate. |
| Haiku | Same question | Declined, saying the race set has no undergraduate level; it does. |
| both | "most recent year for all colleges" (a follow-up on dual enrollment) | Sonnet passed "most recent year" as a stated year, so the path declined for years. Haiku read it as a "what data exists" question. The next turn, "both", failed as a result. |
| both | "Michigan enrollment" | Gave the Michigan state total, 489,583. A defensible reading, but I had expected the University of Michigan or a question. |
| Sonnet | "What about part time student persistence" | Treated as a one-school question with no school, then declined. Haiku correctly gave the national figure, 46.9%. |
| Haiku | "use the institutions in the example set" | Added ten unrelated schools whose names matched words in the question. |
| Haiku | "What is the universe with the lowest net cost?" | Declined, saying there is no "net cost" measure, although net price was on the shortlist |
| Haiku | "What is Yale's average net price for 2024-25?" | Declined and offered 2023-24, instead of giving 2023-24 with the lag stated. Arguably acceptable. |
| Haiku | "What are Yale's admissions test score requirements?" | Gave score percentiles. Requirements are a different, not-set-up item. |
| Sonnet | "What city is Smith College located in?" | Read as "what data exists". The city is in the directory, but it is not a measure the path can show. |

### Decline log

Grouped by what was missing (the `missing` field the path or the model records):

| Missing | Haiku | Sonnet | Typical questions |
| --- | ---: | ---: | --- |
| Years (outside the one release, or a trend) | 30 | 37 | 2014-15 degrees, 2015 to 2024 admission rates, fall 2023 figures, 10-year trends |
| Measure (not set up, or not in IPEDS at that grain) | 16 | 12 | Student services (counseling, placement), on-campus housing, distance-education offering, library book counts, room and board, published tuition 2023-24, PhD economics enrollment, applicants (a shortlist miss) |
| Not a data question | 15 | 17 | Greetings, test rows, chart edits, "yes", "confirm 151786" |
| Not in IPEDS | 10 | 7 | Return on investment, earnings, student debt, student names, AI policies, College Scorecard |
| Other | 10 | 6 | "Another topic for Michigan", "both" with nothing pending, faculty SAT scores |
| Calculation | 5 | 4 | Combined or weighted rankings, a share of headcount (needs a formula), group averages of net price (rates row pending your review), Pell 8-year completion rate |
| Group | 1 | 3 | "PhD-enrolling universities", "the example set" |
| Breakdown | 2 | 0 | Haiku's undergraduate race decline |
| **Total** | **89** | **86** | |

What the decline log points to, for later stages:
- Years, which the multi-year slice will answer.
- About a dozen not-set-up measures that come up repeatedly: student services, housing, distance-education offering, room and board, library counts, and prior-year published tuition.
- Net-price group averages, whose rates row is waiting for your review.

## Defects found (proposals only; nothing changed)

Each is a general fix with a test, not a rule for one phrasing.

| | Defect | Step and table | Proposal | Cost |
| --- | --- | --- | --- | --- |
| A | A term reading that names one measure per kind of school (net price: public in-state versus private) is ranked or listed using only the first measure | resolve (`group_method` / `rank_plan`) and fetch (`rank`, `listing`); `terms.csv` already holds the pair | Treat the pair the way finance forms are treated: each school takes the measure that applies to it, and the page says which. An empty ranking should say "no school in this group reports this measure" rather than show an empty table. | Small: about 20 lines plus tests. It needs your rule for which measure applies to which school. That rule should come from a dictionary column (for example `applies_to` on the reading), not from code. |
| B | "What data exists" on a topic outside IPEDS shows an empty table | show (`topic_message`) and fetch (`topic`); `topics_outside.csv` | When the topic is an outside-IPEDS row, show that row's statement and where the data can be found | Very small |
| C | After an edit to a school list, the level check uses the wrong set of schools | resolve (`level_defaults`) | Use the schools named in the request when there is no group | Very small |
| D | A group rate built only from counts takes the unit "average", so 47.3% shows as "$0" | fetch (`unit_of`); `rates.csv` | Add a `unit` column to `rates.csv` (percent or dollars), so the unit comes from the dictionary | Small; one column and a dated decision line |
| E | The level default replaces a measure the model stated | resolve (`level_defaults`) | Apply the default only when the measure came from the term's default, consistent with the precedence rule | Small, plus a test |
| F | "Most recent year" stated as a year | interpret instructions and resolve (`year`) | The schema already has `year.kind`; make "latest" a kind the instructions name, so "most recent" fills it rather than `stated` | Very small |

Model-side errors (one row instead of both, an undergraduate level not fixed, Michigan read as the state) would need wording in the instructions or better shortlist hints, not code rules. I have not drafted these. If you want them, the shortlist could show the full-time/part-time and level columns of a measure more plainly.

## 3. Items from the last change order

### Before and after: fixed reply shape and prompt caching (the nine design questions, Sonnet)

| Question | Before: input tokens | Before: cost | After: input tokens (cached) | After: cost |
| --- | ---: | ---: | ---: | ---: |
| a | 5,291 | $0.0123 | 7,472 (6,313 written) | $0.0198 |
| b | 8,342 | $0.0187 | 9,748 (6,313 read) | $0.0101 |
| c | 8,536 | $0.0188 | 9,853 (6,313 read) | $0.0100 |
| d | 9,478 | $0.0208 | 10,657 (6,313 read) | $0.0118 |
| e | 8,394 | $0.0183 | 9,697 (6,313 read) | $0.0096 |
| f | 8,994 | $0.0198 | 10,382 (6,313 read) | $0.0112 |
| g | 7,604 | $0.0170 | 9,228 (6,313 read) | $0.0089 |
| h | 6,751 | $0.0149 | 8,531 (6,313 read) | $0.0071 |
| i | 4,973 | $0.0116 | 7,353 (6,313 read) | $0.0050 |
| **Total** | **68,363** | **$0.1521** | **82,921** | **$0.0934** |

- **Cost:** down 39%, even though input tokens rose 21%. The fixed reply shape is larger than a per-question one, but it is read from the cache at a tenth of the price.
- **Time:** total model time fell from 37.8 to 23.1 seconds. Output tokens were 1,535 in both runs.
- **Across the 143-turn runs:** 68% of input tokens were read from the cache on both models.

Where the prompt tokens go, after the change (average per question, from the API's free token counter):

| Part | Tokens |
| --- | ---: |
| Reply shape and call overhead | 5,081 |
| Instructions | 1,230 |
| Measures | 1,209 |
| Category rows | 724 |
| Groups | 470 |
| Breakdown sets | 223 |
| Schools | 199 |
| Terms | 171 |
| Outside IPEDS | 59 |

### Summary-to-detailed links: all 54 load

The build checks each link school by school. A link loads only if the summary value equals the detailed value at every school, except schools that IPEDS flags as reporting together with a related campus for that survey. Those flags are in FLAGS.PRCH_<component> and FLAGS.IDX_<component>, named in the `parent_child_flag` column of `year_meaning.csv`.

All 54 links load, and no difference is unexplained. The links cover:
- 12 completions links (DRVC to C_A at the award level, with CIPCODE 99 and MAJORNUM 1);
- 21 fall enrollment links (DRVEF to EFA at EFALEVEL);
- 21 12-month enrollment links (DRVEF12 to EFFY at EFFYALEV).

The full list is in `docs/reports/stage4/detail_links.csv`. Every differing value is in `docs/reports/stage4/detail_link_exceptions.csv`.

### The 11 flagged schools and the size of the difference

At every flagged school, the parent's detailed value equals its own summary value plus its child campuses' summary values. The detailed table carries the whole amount at the parent, while the summary tables give each campus its own share. This is a reporting arrangement, not an error.

| School | IPEDS flag | Links that differ | Example (summary versus detailed) |
| --- | --- | ---: | --- |
| University of Connecticut (129020) | parent | 5 | Bachelor's degrees 5,511 vs 5,739 (= 5,511 + 4 × 57) |
| UConn Waterbury (436818) | child | 5 | Bachelor's 57 vs none (counted at the parent) |
| UConn Avery Point (436827) | child | 5 | Bachelor's 57 vs none |
| UConn Stamford (436836) | child | 5 | Bachelor's 57 vs none |
| UConn Hartford (463056) | child | 5 | Bachelor's 57 vs none |
| Oregon State University (209542) | parent | 6 | Bachelor's 5,904 vs 6,215 (= 5,904 + 311) |
| Oregon State University-Cascades (440828) | child | 6 | Bachelor's 311 vs none |
| Southern University and A & M College (160621) | parent | 46 | Fall enrollment 7,452 vs 8,279 (= 7,452 + 827); bachelor's 612 vs 756 |
| Southern University Law Center (440916) | child | 46 | Fall enrollment 827 vs none |
| Central Texas Beauty College-Temple (383464) | parent | 2 | Certificates (1–2 years) 20 vs 40 |
| Central Texas Beauty College-Round Rock (246460) | child | 2 | Certificates 20 vs none |

When any of these schools appears in an answer, the page adds the note from the "related campus" setting in `terms.csv`. For example: "IPEDS reports Southern University Law Center's data for this survey with its parent campus, Southern University and A & M College." The rule is recorded in `DECISIONS.md` (2026-11-21) and in the `year_meaning.csv` notes, and is covered by a test.

## Tests and line counts

- 133 tests pass (`python -m unittest discover -s tests`). No test calls the API or writes to a shared log.
- The question path (`path/`) is 1,838 lines: resolve 593, fetch 350, shortlist 268, request 237, interpret 158, answer 105, show 100, log 27. It is unchanged in Stage 4.
- The build is 777 lines (`build_data` 318, `build_dictionary` 459). `app.py` is 91 lines and `config.py` 30.
- Stage 4 scripts: `benchmarks.py` 239, `stage4_run.py` 90, `stage4_grade.py` 168. They are outside the path and are not loaded by the app.

## Open questions for you

1. **Defects A–F.** Which to fix, and in what order? A, the net-price pair, needs a rule from you: which measure applies to which kind of school. It should go in a dictionary column.
2. **Net-price group averages.** The weighted-average rates row is still "Pending". With it approved, "Yale's net price compared to other Ivies" would answer instead of declining.
3. **Choice of model.** Haiku reads about as well as Sonnet in this set, at a fifteenth of the cost but 1.2 seconds slower per turn. Should the default become Haiku, with Sonnet as the setting?
4. **q30 people employed.** Should the staff total include graduate assistants, as NCES appears to? That would need a new reading or a row in `measures.csv`.
5. **The small sum differences (+0.03 to +0.05%) against NCES.** I believe these come from the provisional release. Do you want me to check one school-level difference against the NCES final file once it is available?
6. **The "Michigan enrollment" reading.** The state total is one of two sensible readings. Should a state name with no school word be a reading that always asks? That would be a row in `terms.csv`.
