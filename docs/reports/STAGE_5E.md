# Stage 5, part 5e: written summary, status line, number tile

Date: 2026-11-24. Your decisions on the Part 5d report are in `dictionary/DECISIONS.md` under "2026-11-24: Part 5d approved; decisions on its report". Part 5d was pushed to GitHub after the full rebuild (`a9530ec..24bb550`), after a clean history check. This part, including the Part 5d decision items, is committed locally and not pushed.

## Summary

- **Written summary:** a second model call writes two or three neutral sentences from the table and its notes only. Code checks every number against the result: in the two runs, 267 of 278 summaries were kept, 4 were dropped for a number not in the table, and 7 came back empty (none of these was shown). It takes 1.3 s (median) and costs $0.018 per 139 answers.
- **Status line:** each step is shown as it runs:
  - "Finding matching data…"
  - "Reading your question…"
  - "Searching for more matching data…" (the AI's own search)
  - "Getting the numbers…"
  - "Writing the summary…"
- **Number tile:** one figure is shown large above the table, with its label, school or group, and period.
- **The scorecard, two end-of-part runs (Haiku, with the AI's search and the summary):**

  | | Run 1 | Run 2 | Range |
  | --- | ---: | ---: | --- |
  | Scored questions (118), right or acceptable | 112 (94.9%) | 114 (96.6%) | **94.9% to 96.6%** |
  | Badly written set (56) | 56 | 56 | 100% |
  | Trend questions (21) | 16 | 17 | |
  | Cost for 236 turns (questions and summaries) | $0.254 | $0.257 | |

- **Tests:** 285 pass (272 before). The question path is 3,580 lines (3,401 before); `summary.py` is 103 of those.

## Your decisions on the Part 5d report

1. **fastembed:** closed. Recorded.
2. **Word abbreviations:** a new dictionary table, `word_abbreviations.csv` (17 rows):
   - st = state or saint;
   - u, univ = university;
   - coll = college;
   - cc = community college;
   - comm, cmty = community;
   - inst = institute;
   - tech = technology or technical;
   - mt = mount;
   - ft = fort;
   - intl = international;
   - med = medical;
   - sch = school;
   - penn = pennsylvania.

   The school search adds every meaning beside the word itself, and the picker or the model chooses.
   - **"wayne st"** finds Wayne State University.
   - **"st. olaf"** finds St Olaf College first.
   - **"penn st"** finds Penn State's campuses, but the main campus is not in the picker's first eight. IPEDS names the 22 branch campuses "…Penn State …" and the main campus "Pennsylvania State University-Main Campus", without "Penn". See question 2.
3. **Finance pairing:** tuition and fees revenue, total expenses and total revenues are paired by finance form, as net worth is. In both runs, "Yale's tuition revenue" and "Yale's total expenses" came from Yale's own (FASB) form; before, they had been read from the public or for-profit form. The draft of other concepts is `docs/reports/stage5e/finance_pairing_draft.csv`: 129 concepts whose IPEDS title is the same on two or three forms, each with a proposed pairing. This method can't match lines worded differently on each form (for example "Instruction - current year total" against "Instruction - total amount"). Those need a second, closer pass if you want them.
4. **EFA "Level of student" (LSTUDY)** has its category rows (undergraduate, graduate, all students; the first-professional code has no rows in any release). It is now a row choice, never a figure.
5. **Years outside 2015-16 to 2024-25:** the outside-IPEDS row has a new `instead` column. The decline now offers "the same figure for the years this app holds", and "what can you show me instead?" runs it.
6. **The near-duplicate subgroup sets** are approved and recorded.

## Part 5e

**The written summary** (`path/summary.py`):
- **What the model sees:** "Interpreted as", the table's columns and rows, and its notes. The instructions say:
  - two or three plain sentences;
  - only numbers from the table, rounding allowed;
  - no new calculations, causes, judgements or anything the table doesn't say.
- **The number check** (`numbers_check`) is general: it checks any text against any list of result strings. It allows for rounding to the digits written, thousands separators, dollar and percent signs, and "million" or "billion". A summary with any other number is dropped and logged with the number that failed. An empty reply is also dropped (found in the runs, fixed with a test).
- **On the page:** it streams in under the table, and is then kept only if the check passes. A sidebar switch turns it off; `IPEDS_SUMMARY=0` turns it off by default. Each call is logged to `summaries.jsonl` with its text, whether it was kept, any failed numbers, time, tokens and cost.
- **Tests** use saved replies; the page tests never call the API.
- **What the runs showed:**
  - The 4 dropped summaries all counted the rows of a "what data exists" table ("The table lists 15 measures…"), which the check rightly refuses.
  - The kept ones are plain restatements, for example: "The table ranks all eight Ivy League schools by percent admitted for Fall 2024, lowest first. Columbia, Yale, and Harvard are tied at 4%, … Cornell is last at 9%."
  - A word scan of the 132 kept summaries in run 1 found 6 with "because" or "indicates". All of them restate the table's notes or a measure's name ("Title IV institution indicator"), not an interpretation.

**The status line:** `answer.ask` reports each step to the page as it starts. The page shows it in a status box, which the summary step then follows. The five lines of wording are message rows in `terms.csv`.

**The number tile:** shown when the answer is one figure. That covers one school and one measure; one group figure; and a count of schools. It shows the label (the measure's name), the school or group, and the period, and falls back to the table alone for anything else, including trends and missing values.

**Time limits:**
- **Turns with a search** (24 and 27): none went over the 20-second limit.
- **Other turns:** 10 per run went over 10 seconds, at most 15.5 s. These times include writing the summary (about 1.3 s) and the API's own waits; the table appears before the summary.

## Found on the way (each fixed, with a test)

- **The fast build failed when a new dictionary table appeared** (`word_abbreviations.csv`): it read the table's earlier rows before the table existed. That counts as a path defect in the build. The full rebuild ran afterwards, as planned for the push.
- **The loader tests' made-up dictionary** lacked the new table.
- **A summary that came back empty** counted as kept.

## Wrong readings in the final runs (all model readings)

| Turn | Run 1 | Run 2 |
| --- | :---: | :---: |
| 1.1, 11.1 (trends read as "what data exists" or one release) | x | x |
| 24.3 "both"; 24.6 (list instead of ranking); 58.5 (list of names) | x | x |
| 45.1, 45.2 (no measure named: declined, a question was expected) | x | x |
| 14.3 (combined ranking); fu_go_back.2; 55.1 (one year, not a trend) | x | |
| "2023-24" or "2022-23" read as the year before (Smith tuition, Yale expenses) | x | x |

**The last row is the year misread, which recurs** despite last part's instruction line. Haiku sometimes writes "2023-24" as 2022 to 2023, or gives only the start year of "2022-23", for measures with a one-year lag. Code can't fix it from the user's text without reading the wording, so I propose a worked example in the instruction ("2023-24": start 2023, end 2024; never the year before). That's a general line, and your call.

## Part 5g

As you asked, Part 5g will report which modules of the question path grew most during Stage 5.

## Open questions

1. **The finance pairing draft:** 129 concepts in `docs/reports/stage5e/finance_pairing_draft.csv`. Approve them as proposed, or mark the ones to leave? And do you want a second pass for lines worded differently on each form?
2. **Penn State's main campus first in the picker:** change the nickname row "penn state" from `picker` to `alias` for the main campus. That suggests it first and still shows the other campuses. Shall I?
3. **The year misread:** add the worked example to the instruction?
4. **Summaries of "what data exists" tables** add little (they list the measures again). Leave them, or switch the summary off for those answers?
5. **Push:** this part, with the Part 5d decision items, when you approve it.
