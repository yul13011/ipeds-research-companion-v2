# Stage 5, part 5c: trend questions

Date: 2026-11-23. Your decisions on the second change-order report are recorded in `dictionary/DECISIONS.md` under "2026-11-23: decisions on the second change-order report; Part 5c begins". What this part drafted for your review is under "2026-11-23: Part 5c built (trends); drafts for the owner's review". Committed locally. Nothing is pushed.

## Summary

- **Trend questions work.** They cover one school, several schools, a group, a school beside its peers or a group, a group split by sector, level or control, and a breakdown for one school or one group. "Since 2015", "the last five years", a range of years and the change between two years all work. A follow-up such as "just the last three years" changes the period.
- **Your two test questions are right in both runs.** Yale's Pell share since 2015 shows all ten releases. Front Range's degree-seeking Pell share starts in the 2022-23 release. The seven years before are marked "not collected", with the message, and the measure is never mixed with the all-undergraduate one.
- **Group membership:** a group counts each year's own schools by default, and the answer says so. A "Today's schools only" button runs the same question with today's list. The difference can be large. Connecticut's fall 2015 enrollment is 210,273 counting that year's schools, but 155,794 counting only today's. The gap includes the community colleges that merged into one school in 2023.
- **Chart:** a line for trends and bars for comparisons, with version 1's palette, font and axis colours. There is no formatting panel.
- **Haiku, two runs (end of part):**
  - scored questions: 109 of 118 (92.4%) and 110 of 118 (93.2%), so the range is **92.4% to 93.2%**;
  - trend questions: 21 of 21 and 20 of 21. The one miss was a path defect, now fixed.
- **Tests:** 234 pass. **Full rebuild:** done at the end of the part; the dictionary has not changed since.

## What was built

Each step of the flow keeps its own module. Trends add one new module, `path/trend.py`.

| Step | What changed |
| --- | --- |
| Request (`request.py`) | The year now says what kind of span it is: one year, from a year on, a range of years, the last N years, or the change between two years. It also holds the first and last calendar years, N, and whose schools a group counts. Code keeps only the years that span uses. |
| Interpret (`interpret.py`) | One instruction block on spans, with examples of each kind. It also covers references to schools already named ("the example set", "those schools") from your decision. |
| Resolve (`resolve.py`) | For a trend, the single-year "years held" check is skipped. A measure IPEDS no longer collects is read in the years it was collected, with the "IPEDS collected…" message. The groups named, and today's peers, are kept so each year can count its own schools. Ranking, lists and counts over several years are declined, and the latest year is offered instead. |
| Trend (`trend.py`, new) | Chooses the years and reads each year as it was stored (details below). Builds the table: Year, Period, then one column per school, group or category. Adds the change row and all the notes. |
| Fetch (`fetch.py`) | The data reader takes a year. A trend is handed to `trend.py`. |
| Show (`show.py`) | "Interpreted as" names the first and last period. The release line says each year's figure comes from the release in which it is the current year. Adds the chart description: a line for trends, bars for a one-year comparison of schools, a ranking, a split or a breakdown. |
| Answer and page (`answer.py`, `app.py`) | The offer button ("Today's schools only") runs its request with no model call. The chart is drawn with Altair, which comes with Streamlit; nothing new was installed. The sidebar now says that answers use the latest year unless a period is asked for. |
| Dictionary | 13 message rows in `terms.csv`, all marked as drafts for your review (listed below). |

How each trend rule from Part 5b is met:

| Rule | How |
| --- | --- |
| Default trend measures cover all ten years | Already the defaults: the all-undergraduate Pell, grant and loan measures, and the grant-aid net price. The degree-seeking measures and the Title IV net price start in their own first years and are never spliced onto the defaults. |
| Years worked out per variable; a group rate only once all its counts exist; no mixing of first years | Each measure is read from `measure_years` for each year. A rate computed from counts is used in a year only when both its counts exist that year. Two measures in one question keep two separate columns. |
| Each aid year as first published | Each release supplies only its own current-year figure. |
| Today's name, "(then: …)", "merged into … in …" | Columns use today's name, or a closed school's last name. Notes give earlier names, for example Arizona State University-Tempe, and mergers recorded in the directory, for example Lyme Academy merged into the University of New Haven in 2016-17. |
| Peers are today's comparison group; Carnegie groups use the stated classification | Peers use today's list in every year, and the answer says so. The Carnegie groups were already built that way in Part 5b. |
| "IPEDS did not collect {what} in {year}"; a breakdown missing in a year gets its own message, and the total is still shown | Both are done. The breakdown message has its three reasons as dictionary rows. No breakdown loaded today is missing in an earlier year while its measure exists, so the real data never shows this message. It is tested with a stand-in for one year. |
| Breaks and context notes on any trend crossing them; the pandemic note by the period a figure covers | Notes are numbered, and the years they apply to are marked (for example `2020-21 *1`). A change of definition is noted only when the trend runs across it. The pandemic note goes by the months a figure covers: fall 2020 and fall 2021 are marked, fall 2022 is not. |
| Graduate 12-month headcount before 2020-21 from the detailed table | Read from EFFY through the earlier codes (EFFYLEV 4), with one note naming the years. |
| Retired variables use the "IPEDS collected…" message, continuing through a successor | The measure is shown in its own years, and the message names any approved successor. |

Every earlier category code is translated through `same_as` in `category_codes.csv`, for example graduate students: EFFYALEV 12 from 2020-21, EFFYLEV 4 before.

## Your decisions from the last report

- **Shared names:** done in the last change order; 11 groups (23 measures) are still shared. The drafts below are **not applied**; tell me which to use.

  | Measures | Shared name | Draft plain names |
  | --- | --- | --- |
  | F1A18 / F1N04 | Finance, public (GASB): Net position | Net position / Net position (for the Composite Financial Index) |
  | F2A06 / F2I04 | Finance, private nonprofit (FASB): Total net assets | Total net assets / Total net assets (for the Composite Financial Index) |
  | F2B02 / F2I07 | Finance, private nonprofit (FASB): Total expenses | Total expenses / Total expenses (for the Composite Financial Index) |
  | F3A01 / F3G04 | Finance, for-profit: Total assets | Total assets / Total assets (for the Composite Financial Index) |
  | F3A03 / F3G03 | Finance, for-profit: Total equity | Total equity / Total equity (for the Composite Financial Index) |
  | F3B02 / F3G07 | Finance, for-profit: Total expenses | Total expenses / Total expenses (for the Composite Financial Index) |
  | F3B01 / F3D09 | Finance, for-profit: Total revenues and investment return | Total revenues and investment return / Total revenues and investment return (sum of revenue sources) |
  | F1C19IN / F1C197 | Finance, public (GASB): Total expenses deductions - Interest | Interest (natural classification) / Interest (total, all functions). To confirm: the codebook's descriptions are thin. |
  | GR200 BASTEND / L4STEND | Graduation rates (200%): Still enrolled | Still enrolled, bachelor's degree cohort (four-year schools) / Still enrolled, schools below four years |
  | EFA EFALEVEL / LSTUDY | Fall enrollment: Level of student | Level of student (detailed) / Level of student (summary). Both pick rows only, so they are never shown as figures. |
  | IC TUITVRY1-3 | Institutional characteristics: None | No codebook entry in any year. I propose leaving them unnamed and not set up until a codebook entry is found. |

- **"The example set" and similar references:** the instruction line is in place.
- **"Both" after options (conversation 24):** in version 2, the app never offered options before the user's "both", so there was nothing to choose from. In version 1 it had offered them. The general rule works: the instruction covers "both", and the code runs every option chosen. A test covers it. The turn stays a wrong reading in both runs, for that reason.
- **"The universe with the lowest net cost" (60.4):** the expectation already accepts a clarifying question. The miss is a "not found" from the search, so it is a Part 5d search matter.

## Found on the way (each fixed, with a test)

- **The reply format grew too large for the API.** Adding five optional trend fields made the API refuse every call ("the compiled grammar is too large"). The tests could not catch it, because they never call the API. The trend years are now plain whole numbers, with 0 meaning "not given", and a test checks that no trend field is optional. The first run, which held only failures, was deleted.
- **Single years were read as trends** (found in the first real run, kept as `haiku_5c_before_span`). Haiku filled in years for plain single-year questions. "Headcount for 2022-23" became 2021-22 to 2023-24, and "books in 2023" became fiscal 2023 to 2024: about 10 questions in all. With only numbers to fill in, the reply couldn't tell a single year from a period. The fix is the fixed list of span kinds above, a general instruction rather than a rule for any phrasing. In the runs after it, no single-year question was read as a trend.
- **Entering cohorts were matched by the status date** (log 4.3, "cohorts 2009 through 2018"). Only the 2015-18 releases were shown, that is, cohorts 2009 to 2012. Years named as entering cohorts are now matched by cohort, using the rule in `year_meaning.csv` (fall -6 for four-year schools). Each row names its cohort: "students who entered in fall 2009, status as of August 31, 2015". The saved reply was replayed: all ten releases are now shown.
- **A rate computed from counts crashed a trend** (log 58.7, run 2: "ten year trends for expenditures per student FTE"). Such a rate has no table of its own, and the break notes tried to read one. Fixed. Conversation 58 was replayed: turn 7 now answers (core expenses per FTE student, fiscal 2015 to 2024).
- **A column with codes only in later years** passed an earlier year's code through unchanged, instead of saying "no such row". Fixed.
- **A school no longer in IPEDS was named by its ID.** It is now named by its last name. This is general, not specific to trends.
- **The naming check crashed** on a measure with no title, one of the build's own error tests. Fixed and simplified.
- **The second run stalled** at question 64 for over four hours: a stuck call, or the computer sleeping. It was stopped and run again in full on the final code.

## The question set on Haiku (two runs, end of part)

| | Part 5b2 fixes (two runs) | Part 5c (two runs) |
| --- | ---: | ---: |
| Right or acceptable (scored, 118) | 94.0%, 94.0% (116 then) | **92.4%, 93.2%** |
| Trend questions (21) | scored separately (single year accepted) | **21 of 21, 20 of 21** |
| Your trend questions (o50, 2) | declined (not yet due) | both right, both runs |
| Mean time per turn | | 5.6 s, 5.8 s |
| Cost for 180 turns | | $0.18 each |

Notes on the figures:
- **The cohort fix:** the first run was made before it. I scored log 4.3 from its reading, and the replay shows the fixed result.
- **The trend expectations** were written before trends existed. 17 of them carry the note "acceptable until trends exist" (see question 2 below).

Wrong readings (scored questions):

| Turn | Run 1 | Run 2 | What happens | Known before? |
| --- | :---: | :---: | --- | --- |
| 14.1 "best return on investment" | x | x | The model declines ROI as outside IPEDS but includes a request for "investment return", and the app answers that part | new as a repeat (wrong once before) |
| 24.3 "both" | x | x | No options were offered before (see above) | yes |
| 24.6 dual enrollment in rank order | x | x | Kept as a list with a condition, not a ranking | yes |
| 58.5 a bare list of school names | x | x | The model's reply named schools not on the shortlist | yes |
| 60.4 universe with the lowest net cost | x | x | "Not found" (search; Part 5d) | yes |
| 14.3 / 14.4, 60.5, 62.1 / 62.2, refuse_student_names, fu_go_back | one run each | | Single-run misses | mostly yes |
| 58.7 (trend) | | x | Path defect, fixed (above) | new |

14.1 and refuse_student_names have the same cause. The model declines as "not in IPEDS" but still names a measure, and the "answer what can be answered" rule from Part 5.0 then answers it. I propose one instruction line: when the whole question is outside IPEDS, the request names no measure. I haven't applied it: it changes how a decision of yours works, so it needs your go.

## Tests and line counts

- 234 tests pass (211 at the last report). New tests:
  - Part 5c: 21 on the question path, including the NCES retention-rate check year by year, the owner's two questions, the cohort and computed-rate cases, the today's-schools button, breaks and gaps, names and mergers, the change row, and follow-ups;
  - one on the page (a trend draws a chart);
  - checks on the reply format.
- Question path: **3,007 lines** (2,469 before). `trend.py` is 391; resolve 990, request 298, fetch 398, show 145, answer 153, interpret 191. Page `app.py`: 126.
- Build: `build_dictionary.py` 991, `changes.py` 154, `build_data.py` 400.

## Version 3 habits: where the code still falls short

1. Clean functions: `trend.run` takes the plan and fills a result, with no page code. `fetch` hands over its own module to `trend` (to avoid a circular import); a small shared module for the readers would be cleaner.
2. Sources: each trend row gives its period. The "Definitions & sources" panel still names the latest year's source table, not each year's.
3. The number check (5e): no change.
4. "What data exists": no change; it still describes the latest year. It does not yet say which years a measure covers.
5. Conversation identifier: kept, including for the new offer button.

## Open questions

1. **"Since 2015":** a trend takes every release whose figure's period reaches the years asked. That gives your expected ten years for Yale's Pell share, but it includes aid year 2014-15 from the 2015-16 release. Should "since 2015" start at aid year 2015-16 instead (nine years)?
2. **Trend expectations:** 17 are marked "acceptable until trends exist", and log 4.5 ("a trend line for Yale's peers") expects clarify or decline. Now that trends exist, should these expect a trend? I counted the trend answer to 4.5 as correct, to be confirmed.
3. **A single earlier year** ("Yale's enrollment in 2018") is still answered from the latest year, with "I have … for 2024-25 only". The trend path could answer it as a one-year table. A proposal: it would touch the request (no change), resolve and trend, at about 15 lines. Shall I?
4. **Message wording:** the 13 rows drafted in `terms.csv` (note "Part 5c (trends), drafted 2026-11-23"):
   - how a group counts schools (each year's own, today's only, peers);
   - the "Today's schools only" button;
   - "(then: …)" and "merged into … in …";
   - the detailed-table note;
   - the decline for trend questions not yet supported (with its offer);
   - the three reasons a breakdown is missing in one year;
   - "Change".
5. **Ranking, lists and counts over several years** are declined for now. Should one of them be built next, or left to a later part?
6. **The plain-name drafts** in the table above.
7. **The proposed instruction line** for questions wholly outside IPEDS (14.1, refuse_student_names).
