# Stage 4 follow-up: the change order after Stage 4

Date: 2026-11-21. Data: the IPEDS 2024-25 provisional release. Model: Haiku (`claude-haiku-5-5`), now the default.

Every decision is recorded in `dictionary/DECISIONS.md` under "2026-11-21: after Stage 4".

## Summary

- **New Haiku scorecard** (102 scored questions):

  | Haiku run | Correct answer | Correct decline | Clarifying question | Wrong reading | Right or acceptable |
  | --- | ---: | ---: | ---: | ---: | ---: |
  | Before this change order | 30 | 52 | 6 | 14 | 86% |
  | After | 40 | 49 | 6 | 7 | 93% |

  - The three fewer correct declines are questions that are now answered: net-price comparisons and "the most recent year".
  - Cost is unchanged ($0.096 for 143 turns), and the mean time per turn fell from 4.0 to 3.6 seconds.
- **Defects A–F are fixed, each with a test**, as are two more path defects the first rerun exposed (see "Fixed in passing"). 146 tests pass, up from 133.
- **Net-price group averages work.** They are weighted by the net-price cohort count, and a group with both public and private schools is split by control, with a statement.
- **"Michigan" now asks** whether you mean the state or a school.
- **Item 4, the staff total including graduate assistants, is not built.** It does not work as specified against the data; see "Not done". I need your decision.
- **Version 1 against version 2** on the 42 scored logged questions both saw: version 2 gave 18 correct answers and 18 correct declines. Version 1's log shows 16 answers as expected and 15 clarifying questions. The log has no answer values, so version 1's figures cannot be checked; see the last section.

## What changed

### Defect A: one measure per kind of school

- `terms.csv` gains `applies_to`. The net-price readings now say which schools each measure is for:
  - public schools use NPIST2 (grant-aided) and NPIS42 (Title IV);
  - private nonprofit and for-profit schools use NPGRN2 and NPT42.
- A new group, "Private, nonprofit or for-profit" (HD.CONTROL 2 or 3), holds the private side.
- In every operation, each school takes the measure that applies to it: one-school answers, rankings, lists, comparisons and group figures.
- One general step in resolve (`pair_measures`) does this, plus three lines in fetch.
- An empty ranking now says "No school in {group} reports {measure}"; the wording is in `terms.csv`.

### Item 2: net-price group averages

- The two grant-aided rows in `rates.csv` are approved, and two Title IV rows were added. Each is weighted by its cohort count: GISTN2, GRNTN2, GIS4N2 and GRN4N2.
- Each rate row names its kind of school. A group with both kinds gets one figure per kind, with the "kind of school" statement, the same way finance is split by form.
  - Example: Ohio shows a Public row and a "Private, nonprofit or for-profit" row.
- The Ivy League average equals the cohort-weighted average computed directly from the data (tested).
- One consequence to note: net price now has counts behind it, so net-price rankings apply the ranking guard. Schools with fewer than 30 students in the cohort are left out, and the page says how many.

### Defect B: topics outside IPEDS

My Stage 4 grading was wrong here. The page did show the outside-IPEDS message; my review script printed only the heading. The three Sonnet answers are re-graded as correct declines, and a correction note is at the top of `STAGE_4.md`. The real defect was cosmetic: an empty table under the message, now removed.

### Defects C–F

- **C, the level check.** When a question names schools and no group, the graduation-rate level default looks at the named schools. Five four-year schools no longer get asked "which level?".
- **D, units of computed rates.** `rates.csv` gains `unit` (percent or dollars). The Outcome Measures eight-year award rate shows as 47.3%, not "$0", and the NCES q200 benchmark matches.
- **E, a chosen reading wins over the level default.** The precedence rule already held whenever the reply names the reading, and a test now confirms it: the overall 150% rate at four-year schools gives 61.0%, matching NCES. The instructions now tell the model to always give the reading's tag when the user names one.
- **F, "the latest year".** `year.kind` gains `latest`. "Most recent year for all colleges" is now answered; it was declined in both earlier runs.

### Shortlist categories

- Each measure on the shortlist now lists its category columns: the default row, plus the row tags shortlisted for that column. For example: "categories by STAFFCAT (default: Grand Total): R1, R2".
- The instructions say to list a measure once per category when the user asks for several, such as full-time and part-time.
- Result: "full-time and part-time instructional staff at Yale" now shows both figures (2,995 and 805) on both phrasings.
- It did not fix "Yale's undergraduates by race": Haiku still declines, saying there is no undergraduate level.

### Item 3: default model and decline length

- Haiku is now the default (`IPEDS_MODEL` still overrides it), and Sonnet stays a choice on the page.
- The decline reason and the closest alternative are capped at one short sentence each, in the instructions.
- **The cap saved little.** Output tokens on decline turns fell from 468 to 447 on average, and total output fell 4% (82,777 to 79,290 tokens). Most of Haiku's output is evidently not the visible reason. My guess, not yet checked, is that it is the reasoning the "medium" effort setting allows.
- If you want a real cut, the next step is a proposal: run Haiku at low effort and measure accuracy and tokens again. I have not done this.

### Item 6: state or school

- When a new question's only group is a state and a school is called by that state's name, the app asks which you mean.
- The name patterns are the condition of the "state or school" setting in `terms.csv`: "University of {state}; The University of {state}". A name followed by a campus after a hyphen also counts.
- "Michigan enrollment" now offers: State: Michigan, University of Michigan-Ann Arbor, -Dearborn and -Flint.
- It is not asked when counting or listing schools ("How many colleges are in Michigan?"), or in a follow-up edit.
- My first version matched any shortlisted school with the state's name in it. It asked about "Ohio" with three unrelated schools, and a test caught it. So the patterns are in the dictionary, where you can change them.

### Item 5: small NCES differences

Recorded as known provisional-data differences, to recheck when the final release is out.

### Fixed in passing (found by the first rerun)

The first rerun showed two more path defects. Both were general, so I fixed them with tests and ran the question set again. The scorecard above is from that last run; the in-between run is kept in `logs/stage4/haiku_mid/`.
- **Two category rows of one measure.** Once the model listed full-time and part-time as two items, the one-school table merged them by heading and showed only the first. Each row now keeps its own column.
- **"IPEDS comparison group" named together with "its peers".** It produced an empty comparison, because that group is defined per school and has no member list. A per-school group is now treated as the school's peers.

## Not done: staff total including graduate assistants (item 4)

IPEDS stores graduate assistants as their own staff category (S_OC STAFFCAT 4400), separate from the grand total (STAFFCAT 1100). A total that includes them is the sum of two rows. No field in the dictionary can express that yet: a reading picks one row; it cannot add two.

It would also not match NCES:

| Figure | Count |
| --- | ---: |
| Grand total | 3,682,028 |
| Graduate assistants | 405,802 |
| Sum | 4,087,830 |
| NCES "people employed" | 4,114,069 |
| Gap | 26,239 (0.64%) |

So the premise, "the default matches NCES", does not hold.

**Proposal:**
- **(a)** A general "sum of rows" for a reading: its condition lists several codes, and fetch adds them. This is the first piece of the formula field the plan anticipates. Cost: about 15 lines plus tests. It would land 0.64% below NCES.
- **(b)** Keep the grand total as the default, and add a statement saying it excludes graduate assistants.

Which do you want?

## New Haiku scorecard

The scorecard files are `docs/reports/stage4/scorecard_haiku.csv` (after), `scorecard_haiku_before.csv` and `scorecard_sonnet.csv`. They are graded against the same expectations file, with my review in `docs/stage4/review.csv`.

| | Haiku before | Haiku after |
| --- | ---: | ---: |
| Correct answer | 30 | 40 |
| Correct decline | 52 | 49 |
| Clarifying question | 6 | 6 |
| Wrong reading | 14 | 7 |
| of which, path defect | 5 | 1 |
| Trend questions (20): correct decline / clarifying question / answer | 17 / 2 / 1 | 16 / 4 / 0 |
| Cost for 143 turns | $0.093 | $0.096 |
| Mean time per turn | 4.0 s | 3.6 s |
| Output tokens | 82,777 | 79,290 |
| API errors | 0 | 0 |

The seven wrong readings left:

| Question | What went wrong | Cause |
| --- | --- | --- |
| "Show Yale's undergrad population by race and ethnicity" | Declined, saying there is no undergraduate level for the race set | Model |
| "both" (after a dual-enrollment answer) | Nothing was pending, so there was no choice to make | Model, and an odd turn in the log |
| "use the institutions in the example set" | Added ten unrelated schools whose names matched words in the question | Model |
| "What is the universe with the lowest net cost?" | Declined "net cost" although net price was on the shortlist | Model |
| "What is Yale's average net price for 2024-25?" | Declined and offered 2023-24, instead of answering with the lag stated; arguably acceptable | Model |
| "What are Yale's admissions test score requirements?" | Gave score percentiles; requirements are not set up | Model |
| "Actually, go back to all eight" (net price, after "Just Yale and Harvard") | The edit restored the group but kept the one-school operation, so the path asked for a school | **Path** (`apply_edit` "back" restores the fields named, not the operation). Found in this run; not fixed. Proposal: "back" restores the whole earlier request. Very small. |

Shortlist misses are unchanged: 2 of the 19 checkable turns (the applicants count, and the "PhD-enrolling universities" group).

Known answers after the changes: 19 NCES, 17 Yale and 5 design-table figures match, as before. q200 now matches as a percent.

## Version 1 beside version 2

`scripts/v1_grade.py` lines up version 1's recorded outcomes in `docs/question_log.csv` with the same expectations file, matching questions by text and in order. The side-by-side rows are in `docs/reports/stage4/v1_vs_v2.csv`.

The log matches all 107 logged questions; 74 have an expectation. Version 1 was not rerun, and no session IDs or times were copied.

### Where the log is not enough to grade

- **No answer values, measures or schools.** For a version 1 answer the log records only:
  - that it answered;
  - which route served it ("reviewed example", "catalog relational planner", and so on);
  - how many rows it returned.

  So I cannot say whether a version 1 answer was right, only that it answered where an answer was expected.
- **An interpretation is written for only 16 of 107 rows.** Where one is written, I judged the reading. Six were right; one was wrong: "What about part time student persistence" was read as Odessa College, a school the user never named. Those judgments are in `docs/stage4/v1_review.csv`.
- **Year-based questions are not comparable.** Version 1 held ten years, so its answers to trend questions and to years before 2024-25 were legitimate there. This covers all 18 trend questions and 2 scored questions.
- **Clarifying questions cannot be judged.** The log does not say what version 1 asked or what was offered, only that it asked.
- **The eval-set questions are not in the log**, so only the logged questions are compared.

### On the 42 scored logged questions

| Outcome | Version 1 (from the log) | Version 2 (Haiku, after) |
| --- | ---: | ---: |
| Answered where an answer was expected | 16 (6 with the reading checked; 10 unverifiable) | 18 correct answers (figures checked) |
| Declined where a decline was expected | 2 | 18 |
| Clarifying question | 15 | 2 |
| Wrong reading (judged from the interpretation) | 1 | 4 |
| "Answered" with no rows returned | 3 | 0 |
| Answered where a decline was expected | 1 ("Where does income data come from", answered conversationally) | 0 |
| Error | 2 ("What data do we have on college tuition / graduation rates") | 0 |
| Not comparable (years) | 2 | n/a |

Plainly:
- Version 1 asked a clarifying question on 15 of the 42 where version 2 gave a definite answer or decline. Examples: return on investment, AI policies, economic mobility, "how many dual enrollment students are there?", RIT's peers.
- Version 1 failed outright on 5: two errors and three answers with no rows.
- Where version 1 did answer, the log cannot show whether the figure was right. Version 2's figures are checked against the data, and against NCES and Yale where those exist.
- The 4 wrong readings counted for version 2 are fully graded. Version 1's single wrong reading comes from the 16 rows where an interpretation exists, so its count is a floor, not a full grade.

## Tests and line counts

- 146 tests pass. New: `ChangeOrder1121` in `tests/test_path.py` (13 tests), plus two updated tests for decisions that have since changed (net price approved; the "average with no rate row" test now uses the federal loan average).
- The question path is 1,944 lines, up from 1,838: resolve 675, fetch 360, shortlist 275, request 237, interpret 165, answer 105, show 100, log 27.
- Scripts: `v1_grade.py` is new (91 lines). `stage4_grade.py` now takes run names.

## Open questions for you

1. **Staff total (item 4):** (a) sum of rows, 0.64% below NCES, or (b) keep the grand total and state that it excludes graduate assistants?
2. **"Go back" in an edit:** fix it so "back" restores the whole earlier request, as proposed above?
3. **Haiku output tokens:** try low effort for Haiku and measure accuracy and tokens again?
4. **"Yale's undergraduates by race":** the remaining model error. One option is to show the breakdown set's fixed level (undergraduate or all students) on the shortlist line for the set. That would be a shortlist change, like the category columns.

## Addendum: owner decisions (2026-11-21)

- **Staff total.** The grand total stays the default. Every answer that uses it now says it excludes graduate assistants, and they can be asked for as their own figure. The note lives in a new `statement` column of `category_codes.csv`.
- **"Go back".** The path's `back` already restored the whole earlier request. In the run, the model rebuilt it field by field instead. The instructions now say to use `back`. A three-turn test covers it: rank, then "Just Yale and Harvard", then back to a ranking of all eight. Not checked live.
- **Haiku effort** is unchanged.
- **Breakdown sets on the shortlist** now show where they are held, and a measure broken down through its detailed table shows the level it carries over (for example "All students, Undergraduate total").
- **Finding: why "undergrad" fails.** For "Show Yale's undergrad population by race and ethnicity", neither the undergraduate measure nor the undergraduate row reaches the shortlist: "undergrad" does not match "undergraduate". So the model has no tag for the undergraduate level. With "undergraduate" spelled out, the shortlist carries the undergraduate measure and its held level. The fix is a synonym ("undergrad", and perhaps "grad" for graduate) in `measures.csv` or `category_codes.csv`, which needs your approval as a change order. Not done.
- 149 tests pass.

## Addendum: shorthand synonyms and their effect on the shortlist (2026-11-21)

- **Added as decided** (see DECISIONS.md). New dictionary columns:
  - `measures.statement`, shown whenever the measure is used;
  - `rates.synonyms`, for core expenses per FTE.

  Also new: a "low-income" term and a URM row in `outside_ipeds.csv`. 154 tests pass.
- **Shortlist before and after, no model call** (`scripts/shortlist_compare.py`, results in `docs/reports/stage4/shortlist_compare.csv`):
  - 146 questions: 9 design, 83 distinct logged, 54 eval turns.
  - The shortlist changed for 64 of them.
  - A right measure is known for 56. Here, "right measure" means an expectation ID, a saved design reply, or a measure from a correct answer in the last Haiku run.
  - **No right measure dropped out.** Nine were missing both before and after. Eight of those are follow-up turns ("What about Harvard?", "Sort them…"), where the live path carries the earlier request's measures onto the shortlist; this check does not.
  - **Four questions now fill with near-duplicates from one table.** All four are crowded by Outcome Measures, whose many Pell / non-Pell / cohort variants now carry "persistence" or "eight-year completion":

    | Question | Largest table among the 15 set-up slots, before → after |
    | --- | --- |
    | "What about part time student persistence" | DRVEF 5 → DRVOM 12 |
    | "What is the 10-year trend in completion rates for RIT" | DRVGR 10 → DRVOM 12 |
    | "compare RIT's completion rate to its peer institutions" | DRVGR 13 → DRVOM 12 |
    | "Show a 10-year trend" | DRVGR 11 → DRVOM 12 |

    In the first, the right measure moved from 11th to 1st. In the RIT questions, the graduation rates stay on the list through the "graduation rate" term. So nothing is lost yet, but those slots no longer show alternatives.
- **Ranking problems the synonyms could not fix:**
  - "How many applicants did Yale have?" still leaves ADM.APPLCN out of the top 15 set-up measures, despite the new synonym. All admissions measures share a table title that names applicants, so ten "admission considerations" measures outrank it, and the 12-month enrollment measures take the rest.
  - "How many freshmen did Yale enroll?" fills with 12-month first-time measures, and the fall measure (DRVEF.EFUG1ST) does not reach the list.
- **How I would fix the ranking** (not done; needs your go):
  1. **Field weights.** Score a match in a measure's name or synonyms well above a match in its table's title or description (BM25F, standard practice). The table title should help choose the table, not lift every measure in it equally.
  2. **One table cannot fill the list.** At most five of the fifteen set-up slots from one table. The rest of that table stays reachable through its category rows and the measures a matched row or set brings, as now.
  3. **Group near-duplicates.** Measures in one table whose names differ only by a subgroup should take one slot: the best-scoring one, with "and N similar" for the model. "Differ only by a subgroup" means the same name apart from one category word, read from the dictionary's own category labels, not from a word list in code.

  Fixes 1 and 2 are small, about 20 lines in `shortlist.py`, and the comparison script checks them across all 146 questions. Fix 3 is larger.
