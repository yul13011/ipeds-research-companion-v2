# Stage 5, part 5g: measure it

Date: 2026-11-25. Part 5f is pushed (`e72dae9..ba6a82f`), after the full rebuild and the history check. Part 5g is committed locally, not pushed.

## The scorecard against the plan's success test

| Test (V2_PLAN.md) | Result | Met? |
| --- | --- | --- |
| Benchmarks match NCES trend tables across ten years, apart from known definition differences | 231 of 251 NCES year-figures match or are within 0.1% (or 0.1 point); the other 20 are the two known definition differences and one provisional-year figure. 40 are declined by rule, as in Stage 4 | **Yes** |
| At least 90% of scored questions right or acceptable, trend questions included | 91.3% and 91.9% (136 and 137 of 149) | **Yes**, by a small margin |
| No false "IPEDS does not collect this" in any test set | none in either run | **Yes** |
| Speed: your limits of 10 seconds a turn, 20 with the AI's own search | 6 and 4 turns over (of 236); 97% and 98% within | **Mostly**: see section 4 |
| Speed in the plan: typical questions under 5 seconds | median 6.0 and 6.4 seconds; 29% of turns under 5 seconds | **No** |

## 1. Benchmarks across ten years

`scripts/benchmarks_trend.py` (new) runs each Stage 4 benchmark once as a ten-year trend ("the last 10 years") through the app's own resolve, trend and fetch steps, with no model call. It then compares every year with the published figure. Results: `docs/reports/stage5g/benchmarks_trend.csv`.

**NCES: 30 series, 292 year-figures.**

| Result | Year-figures | What they are |
| --- | --- | --- |
| Exact match | 203 | |
| Within 0.1% or 0.1 percentage point | 28 | NCES rounds percentages and dollars; the app shows the exact figure |
| The 2024-25 differences of 0.03 to 0.05% (12-month headcount, awards, FTE, students awarded) | 4 of the 28 | They occur **only** in 2024-25: the same four measures match NCES exactly in all nine final releases. That confirms the Stage 4 explanation, provisional data |
| Differs: total staff (q30) | 10 | About 12% below NCES every year: the app's total excludes graduate assistants and says so (your Stage 4 decision) |
| Differs: full-time instructional staff from the salary table (q12) | 9 | 0.5 to 0.6% above NCES every year, the Stage 4 definition difference |
| Differs: full-time instructional staff (q51), 2024-25 only | 1 | 0.12%, the provisional year; the other nine years are within 0.1% |
| App has no figure | 1 | q12 in 2015-16: IPEDS did not collect that table that year, and the app says so |
| Declined by rule | 40 | The four averages with no rates row (q38, q42, q220, q221), every year, as in Stage 4 |

The ten-year run adds no new difference: every one is a definition or rounding difference already known in Stage 4, or the provisional year.

**Yale: 12 series, 120 year-figures.**
- 108 match, and 4 are within 0.1%.
- The 8 that differ are years where Yale's own files disagree with what Yale reported to IPEDS, for example SAT ranges for fall 2017 and 2018, and graduate enrollment for fall 2022. In each case the app shows the figure in the IPEDS data (checked against the loaded tables: for example 35,301 applications for fall 2018, where Yale's file says 35,307).

## 2. The question set: two end-of-stage runs

`IPEDS_STAGE=5f`, so all owner questions due by Part 5f count. Runs `haiku_5g_first` and `haiku_5g_second`. Manual review in `docs/stage4/review.csv`: earlier reviews were carried over where the reading was the same, and 22 turns were read by hand.

| | Run 1 | Run 2 | Range |
| --- | --- | --- | --- |
| Scored questions (128) | 120 (93.8%) | 122 (95.3%) | 93.8% to 95.3% |
| Trend questions (21) | 16 | 15 | |
| **Scored and trend together (149), the success test** | **136 (91.3%)** | **137 (91.9%)** | **91.3% to 91.9%** |
| Trend questions: measure read right | 18 of 21 | 19 of 21 | |
| Badly written set (56) | 55 (98.2%) | 56 (100%) | |
| Shortlist misses (a measure was wanted but not on the shortlist) | 0 of 25 | 0 of 25 | |

### The same 118 questions as Part 5e (you asked)

All six runs are graded the same way here, with today's expectations; that is why Part 5e's figures differ slightly from its report, since the income question now expects an answer.

| | Run 1 | Run 2 |
| --- | --- | --- |
| Part 5e | 111 (94.1%) | 113 (95.8%) |
| Part 5f | 110 (93.2%) | 111 (94.1%) |
| Part 5g | 110 (93.2%) | 112 (94.9%) |

**Not clearly below:** about one question apart, which is less than the spread between two runs of the same code (Part 5e's two runs differed by two).

Two questions have failed more often since Part 5f, so I checked whether Part 5f caused them. I ran each with and without the new explanation section of the shortlist:
- "What are Yale's admissions test score requirements?" (the requirement itself, not only the score ranges): chosen in 3 of 6 tries with the section and 2 of 6 without it.
- "Please create a trend for Ivies plus MIT and Stanford" (replaying its whole conversation): decline, clarify, answer with the section; decline, answer, answer without it.

Both vary from run to run, with or without Part 5f's changes. Neither is caused by Part 5f.

**Failing in every run since Part 5e:**
- log 24.3 and log 58.5 (follow-ups that name schools from an earlier turn);
- three trend follow-ups that name no measure (log 1.1, 45.1 and 45.2: "show a 10-year trend").

These are the follow-up questions the plan leaves to Stage 6.

### The year, once more

In run 1, "2014-15" (now with an ordinary hyphen) was answered with the right figure (1,327). But the model also attached the "years outside the ten releases" topic, so the answer carries a note about earlier years. This is the same cause as Part 5f's decline: the model judges which years the app holds. The general fix proposed in Part 5f (only the code decides whether years are held) would cover both. It is not built.

## 3. Version 1 against version 2 on trend questions

`scripts/v1_grade.py <run> --trends` now includes trend questions, since both versions hold ten years. Output: `docs/reports/stage5g/v1_vs_v2_5g_first.csv` and `_5g_second.csv`.

**What can be compared:** version 1's log records the outcome, the route and the number of rows, but no figures, years or measures. So version 1 can be graded only by the kind of answer, not by whether the figures were right.

| Trend questions (19 from the log) | Version 1 | Version 2, run 1 | Version 2, run 2 |
| --- | --- | --- | --- |
| Answered over several years (version 1: figures not checkable) | 9 | 7 checked right | 7 checked right |
| Clarifying question | 7 | 5 | 4 |
| Correct decline | | 2 | 2 |
| Answered where a clarifying question was expected ("show a 10-year trend") | 2 | | |
| Answered with no rows | 1 | | |
| Wrong reading | | 5 | 6 |

**My reading:**
- **Both versions answer most trend questions.** Version 2's answers can be checked, and 7 of them were checked right in each run.
- **Version 1's 9 answers can't be graded.** It answered with 10 to 125 rows, so they were very likely trends, but whether the figures and years were right is unknown.
- **Where version 2 is wrong,** it is mostly on the follow-ups listed above. Version 1 asked a clarifying question for several of those.

## 4. Time and cost

| | Run 1 | Run 2 |
| --- | --- | --- |
| Mean per turn | 6.4 s | 6.6 s |
| Median per turn | 6.0 s | 6.4 s |
| 90th percentile | 9.3 s | 9.8 s |
| Turns over your limit (10 s; 20 s with a search) | 6 | 4 |
| Slowest | 12.8 s | 19.2 s |
| Model cost per question | $0.0011 | $0.0011 |
| Whole run (236 turns) | $0.26 | $0.26 |

- **The slowest turn,** 19.2 seconds, was "connect enrollment and graduation in STEM or med-related majors, by demographics". The model took 8.6 seconds; the rest was the data work for a national breakdown by race across fields.
- **The other turns over the limit** were 10.2 to 13.6 seconds, mostly clarifying questions and long first questions.
- **The plan's "typical questions under 5 seconds" is not met.** That figure came from Stage 3's one-year slice. Since then, each turn reads a larger shortlist, and some turns search.

## 5. The reply format: what takes up its size, and one restructure (your request)

`scripts/reply_format_size.py` (new) measures the shape. With `--probe`, it asks the API which variants it accepts, with one tiny call each.

**What the shape is made of** (today: 6,635 characters, 438 allowed tag values in fixed lists, 12 "value or null" choices, 10 lists, 10 objects):

| Part | Characters | Allowed values | "Value or null" choices |
| --- | --- | --- | --- |
| measures | 1,109 | 128 | 0 |
| breakdown | 884 | 96 | 1 |
| conditions | 727 | 70 | 0 |
| year | 678 | 15 | 2 |
| decline | 495 | 11 | 2 |
| changes | 375 | 16 | 0 |
| schools | 327 | 16 | 1 |
| sort | 249 | 2 | 2 |
| the other 12 parts | 1,791 | 84 | 4 |

**The 12 "value or null" choices:** a school's tag, peers_of, breakdown, split_by, sort, sort's limit, year's stated text, year's kind, topic, outside, decline, and decline's "about".

**What the API accepts** (probes, 2026-11-25):

| Variant | Characters | Allowed values | Choices | API |
| --- | --- | --- | --- | --- |
| Today's shape | 6,635 | 438 | 12 | accepted |
| Today + two explanation fields | 6,747 | 438 | 12 | **refused** |
| Every tag as checked text (368 fewer allowed values) + explanation fields | 4,156 | 70 | 12 | **refused** |
| Measure and row tags as text + explanation fields | 4,951 | 182 | 12 | **refused** |
| **No "value or null" choices + explanation fields** | 6,375 | 438 | 0 | **accepted** |
| **No "value or null" choices + explanation fields + a formula field** | 6,686 | 442 | 1 | **accepted** |

**So the size that matters is the "value or null" choices, not the length or the lists of allowed tags.** Shortening the tag lists by 84% freed nothing; removing the 12 choices freed enough for both explanation fields and a formula field (which itself has one such choice).

**The proposal: write every "value or null" field as a value that means "none" when empty.**
- **What changes:** a tag field takes "" for none; text takes ""; a number takes 0, as the year numbers already do since Part 5d. The breakdown, sort and decline objects are always present, with an empty tag or "none" for their parts.
- **Where:** request.py, about 20 lines. The schema writes the fields that way, and the code that reads the model's reply turns "", 0 and "none" back into "not given". The rest of the path never sees the difference.
- **What it frees:** room for `explain` and `general` as their own fields, moved out of `topic` and `label` (about 10 lines back out of request.py and interpret.py), and for the formula field in Stage 6.
- **Cost and risk:** no rebuild is needed, since this is code only. It needs a trial call, the saved-reply tests updated, and one question-set run. The risk is the model writing "" where it means something; the badly written set and the trial call would show that.
- **Not changed:** proposal only, as you said.

## 6. Which modules grew most during Stage 5 (from Part 5d)

Lines in each step of the question path, before Part 5.0 (commit `ccb95f8`) and now:

| Module | Before Stage 5 | Now | Change | Mainly |
| --- | --- | --- | --- | --- |
| trend.py | 0 | 549 | +549 | new in Part 5c: trends, earlier single years, ranking by change |
| resolve.py | 686 | 1,092 | +406 | the four answers (5.0), finance pairing and school names (5d, 5e), the order of sources for explanations (5f) |
| shortlist.py | 336 | 544 | +208 | misspellings (5.0), the AI's own search, near-duplicates and abbreviations (5d), explanation sections (5f) |
| summary.py | 0 | 103 | +103 | new in Part 5e: the written summary and its number check |
| request.py | 237 | 326 | +89 | spans of years, the search reply, reading explanations |
| answer.py | 105 | 192 | +87 | the AI's own search loop, status line, summary |
| interpret.py | 169 | 252 | +83 | the instruction lines added part by part |
| show.py | 100 | 182 | +82 | tile, chart, definitions |
| fetch.py | 360 | 398 | +38 | |
| log.py | 27 | 30 | +3 | |
| **Total** | **2,020** | **3,668** | **+1,648** | |

resolve.py is now the largest step by far (30% of the path). If you want the path easier to read, resolve.py is where to split, for example school names into a module of their own. That is a proposal for later, not a change.

## 7. Done since your Part 5f approval

These are in the Part 5f report, section 11, and pushed:
- the income expectation is now an answer;
- every convention sentence has a test, which exposed and fixed a false statement in Carnegie-group trends;
- dashes become hyphens before the model sees the question.

## 8. Tests and line counts

- **Tests:** 309, all passing. No new tests in Part 5g: it adds measuring scripts, not app code.
- **New scripts:** `benchmarks_trend.py`, `reply_format_size.py`, and the `--trends` option of `v1_grade.py`.
- **The question path:** 3,668 lines, unchanged in Part 5g except trend.py (+5 for the Carnegie statement, in the Part 5f follow-up) and answer.py (+1, dashes).

## 9. Questions for you

1. The reply-format restructure (section 5): approve it, for Stage 5 or Stage 6?
2. The year: let only the code decide whether years are held, as proposed in Part 5f (this part shows it recurring as an extra note)?
3. The plan's "typical questions under 5 seconds": keep it as a target, or replace it with your 10 and 20 second limits?
4. Push Part 5g after your review?
