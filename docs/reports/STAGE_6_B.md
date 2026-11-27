# Stage 6, part 6b: the page, version 1's layout and features

Date: 2026-11-26. Built to the owner's decisions on the review point (`dictionary/DECISIONS.md`, "2026-11-26: Part 6b review point approved"). The review list itself is `STAGE_6_B_FEATURES.md`. **This stops at the screenshot comparison and the wording drafts, as asked.** Nothing is committed or pushed.

## In short

- **The page is now version 1's.** Explore IPEDS, Ask & Analyze with its two side panels and menu, the definitions browser, About. Version 1's CSS, theme and labels are copied as they are; only the data calls are version 2's.
- **The two Explore screens match version 1 pixel for pixel (0.00% different).** The other screens differ only where you approved a difference, where the wording is a draft below, or where version 2's answer is different, with one exception: **the chart's style** (open question 1).
- **Version 1 couldn't answer typed questions here.** Every typed question got its own error, "The request could not finish…". So its school picker, clarifying question and decline screens were compared with its code, not a screenshot. Its Explore examples work, because they run fixed plans with no model call.
- **368 tests, all passing** (24 new). Streamlit 1.66.0 in .venv, pinned. Playwright in .venv only, in `requirements-dev.txt`.
- **The question set was not run.** Four Explore examples were added to it, not six (below). They are first checked at the end-of-part runs.

## What was built

**The page** (`app.py`, `page/`, `.streamlit/config.toml`):

| File | Lines | Copied from version 1 | Rewritten |
| --- | ---: | --- | --- |
| `page/styles.css` | 75 | all (ui.py's CSS, as it is) | none |
| `page/transcript_scroll.js` | 66 | all | none |
| `.streamlit/config.toml` | 10 | all | none |
| `page/ui.py` | 322 | about 75%: header, menu, Explore cards and topics, "Need ideas?", the three-column chat, composer, tools card, definitions page, About | running a question or button (calls `path/answer.py`), error messages, the tools panel without development mode, About's model list and benchmark tiles |
| `page/components.py` | 190 | about 30%: the "Display table" switch, the counts checkbox, "Definitions & sources" as a popover, the picker's layout, the codebook results table, transcript scrolling | showing version 2's page object; the chart is version 2's own (moved from the old app.py) |
| `page/explore.json` | | version 1's `learning_content.json`, without `families`, `discovery_query`, `kind`, `plan` and the plan keys | |
| `page/wording.json` | | | the drafts below |
| `app.py` | 8 | | the entry point only |

**Behind the page** (`tools/`, new, no model calls):
- `tools/codebook.py` (79 lines) is the definitions browser's search over version 2's codebook tables: `VARTABLE`, `TABLES`, and `VALUESETS` with the checkbox. Whole words rank first, so "graduate" finds "Graduate enrollment" before "undergraduate". About 0.5 s for one year, 1.2 s for all ten with codes. The results table matches version 1's columns, except the "Column at documented location" check, which version 2 doesn't have.
- `tools/about.py` (44 lines) reads two things instead of having them typed in:
  - the releases line, "10 annual releases · 2015–16 Final through 2024–25 Provisional", from the database;
  - the benchmark rates, from the latest benchmark file (`config.BENCHMARKS`, now the Part 5g ten-year run).
- **Benchmark rates:** Yale 93% (112 of 120 matched), NCES 92% (231 of 251). A match is "match", "within 0.1%" or "within 0.1 point". Declines and questions not covered are left out of the count, and the caption says so (draft).

**The question path** (+27 lines, 3,992 now):
- **The 30-second limit.** Both model calls (interpret and summary) now stop after `config.CALL_SECONDS` (30). The API library's own automatic retries are turned off (`max_retries=0`), so one call can't run past 30 seconds. A timed-out call isn't retried; any other failure still gets the path's one retry.
  - **One effect to watch:** before, the library retried a busy or overloaded API twice by itself, with waits. Now there is one immediate retry. Rate limits in question-set runs are still handled by `stage4_run.py`'s own waits.
- **Error kinds.** `answer.error_kind` reads the API's error type, never the user's words: usage limit, access, timeout, or down. The page shows the friendly message for it and keeps no partial turn. The kind is also logged with the question.
- **The picker.** The school picker's page now carries the name typed. A new `answer.cancel` backs version 1's Cancel button: it drops the request waiting for a school.

**The question set:** a new source, `explore`, in `scripts/stage4_run.py`. It runs any example on the page that isn't asked elsewhere in the set, so the set always covers every example. There are four expectation rows (stage 6):
- enrollment-compare (DRVEF.EFUG);
- enrollment-trend (EFUG and EFGRAD, a trend);
- faculty-salaries (`*salary`, answer or clarify);
- faculty-changes (`*instructional staff`, a trend).

**Correction to the review list:** it named six examples missing from the set. Matched exactly, only four are. The grants-percentage and Massachusetts distance-education examples are already in the set, from version 1's evaluation set. A test now checks that every example is in the set.

**Removed from the page, as decided:** the sidebar, the summary switch (`IPEDS_SUMMARY=0` still turns the summary off for testing), the AI switch, development mode, the extract builder, and the "Verified summary" popover.

**One change found by the screenshots:** the summary sits above the result, as in version 1, but is now written after the table is drawn. The first build wrote it first, so the table waited for the summary. That would have broken the speed rule (the table appears before the summary).

## Tests

- **368, all passing.** 24 are new.
- `tests/test_app.py` was rewritten for the new page (15 tests), driving it as a user would:
  - Explore's six topics and the releases line; no sidebar;
  - an Explore example and a "Need ideas?" example sent to the chat;
  - the answer: "Interpreted as", the table, the provisional warning, the "Definitions & sources" popover, underlying counts, and the log written;
  - the side panels and the menu collapsing;
  - follow-up and Clear conversation;
  - the option buttons;
  - a trend: the chart shown, the table off until "Display table" is turned on;
  - the tile and the summary; a summary with a wrong number dropped;
  - a timeout: its message, no turn kept, and no second call;
  - an API failure, and the database missing;
  - the definitions browser finding EFGRAD;
  - About: "Model strategy", the two benchmark tiles, and no switches.
- `tests/test_page.py` (13 tests):
  - the codebook search: ranking, years, tables, codes, a coded variable's labels;
  - the releases line, and the match-rate counting;
  - the error kinds;
  - a timeout not retried while other failures are;
  - the 30-second setting;
  - Cancel;
  - the content file (6 topics, 18 unique examples, every example in the question set);
  - the wording drafts filling in;
  - requirements.txt has Streamlit 1.66.0 and no Playwright.
- **Instruction prompt: 2,496 words** against the 2,500 limit (`meta["prompt_words"]`, unchanged in this part).

## The check: version 1 and version 2 side by side

**How it was run:**
- `scripts/compare_pages.py` (Playwright, 1440 × 900 window) takes each state in both apps from a fresh page and compares them pixel by pixel. A pixel counts as different past a small colour tolerance.
- Version 1 ran from a copy in the scratchpad, with no secrets file, so nothing was written to its folder or its Google Sheet.
- Screenshots: `docs/reports/stage6b/` (`<state>_v1.png`, `<state>_v2.png`); the first run's pixel figures are in `pixel_summary_first_run.csv`.
- **Cost:** about 12 model calls in version 2 (Haiku, under $0.01).

| State | Pixels different | Differences, and whether each is approved |
| --- | ---: | --- |
| Explore | 0.00% | none |
| Explore, topic open | 0.00% | none |
| Empty chat | 1.08% | Tools panel: the definitions card instead of "Under development" (**approved**). Caption under the chat box (**draft W1**) |
| Menu hidden | 1.11% | the same two |
| Side panels collapsed | 0.30% | the caption (**draft W1**) |
| Answer with table (Yale's admission rate) | 2.2% | Tools panel (**approved**). No "Verified summary" popover and no "Download Data" button (**approved**; downloads in Part 6c). Version 2's own: the tile with school and period, the provisional warning's wording, the data-release line (**for your approval**, below). Version 1's table renders empty in its own screenshot |
| Answer with chart (three schools' admission rates, ten years) | 2.5% | **The chart's style differs** (open question 1). No "Format chart" or "Preview & download chart" (**approved**, Stage 7). Version 2's notes under the chart (**for your approval**) |
| School picker | 2.1% | **Version 1 failed** ("The request could not finish…"), so it was compared with version 1's code. Version 2 copies its layout ("Institution: …", dropdown, refine box, Continue, Cancel) and adds version 2's own question line above it |
| Clarifying question | 2.0% | Version 1 failed. Version 2 uses version 1's row of buttons and its caption, "Choose an option, or type a change to refine it." |
| Decline | 1.9% | Version 1 failed. Version 2 shows plain text, as version 1 does |
| Definitions browser | 4.8% | No "Return to extract builder" (**approved**). Wording (**drafts W6 to W8**). No "Column at documented location" column (version 2 has no such check). Different ranking, so different rows |
| About | 3.7% | Intro, model caption and AI caption (**drafts W2 to W4**). The model list is version 2's (Haiku, Sonnet). No AI switch and no developer settings (**approved**). Benchmark tiles from version 2's run, with the caption (**draft W5**) |

**Version 2's own elements, for your approval** (each uses version 1's styles only):
- **Provisional warning:** version 1's yellow box. `06_answer_with_table_v2.png`.
- **Data-release line and notes:** grey captions. `07_answer_with_chart_v2.png`.
- **Years held:** a numbered part with its table, in version 1's numbered-task style. `v2_only_years_held_top.png`.
- **Statements:** inside the grey "Interpreted as" caption. For example: "No years were given, so the trend covers every release that holds the figure." `v2_only_statement_top.png`.
- **Offer buttons:** version 1's button. Not captured: no question in the check offered one. Reported, not shown.

## Wording drafts, for your approval

These are in `page/wording.json`. Every other label is version 1's own.

| # | Where | Version 1 | Draft |
| --- | --- | --- | --- |
| W1 | Under the empty chat | Request a table, CSV extract or chart. {model} · AI interprets each typed request, including chart edits. | Request a table or chart. {model} · AI reads each typed request; every figure comes from a query of the IPEDS data, never from the AI. |
| W2 | About, intro | Local IPEDS codebook discovery and source-reviewed analytical extracts across ten annual releases. | Plain-English answers about U.S. colleges from ten annual IPEDS releases, with the codebooks' own definitions. |
| W3 | About, model caption | Automatic uses Haiku for interpretation and reviewed numerical planning, Sonnet for catalog planning… | Haiku reads each question and writes the short summary under each answer. Sonnet reads questions more slowly and costs more. Either way, the AI only reads the question: every figure comes from a query the app builds, and every summary is checked against its table. |
| W4 | About, AI caption | AI sends your question, up to 12 recent conversation turns with analytical plans and bounded definitions, and relevant codebook excerpts… | The AI sends your question, the IPEDS measures, schools and terms that may fit it, and your last five requests in this conversation to Anthropic. For the written summary, the answer's table is sent too. Memory lasts for this session; Clear conversation clears it. Queries and calculations stay local. |
| W5 | About, under the benchmark tiles | NCES excludes aggregates whose method is still under review. Remaining differences are… | Each published figure is compared year by year across the ten releases. Questions the app declines or does not cover are not counted. Remaining differences are documented source, universe or definition differences, not arbitrary errors; benchmarks test data retrieval, not open-ended conversation accuracy. |
| W6 | Tools panel | Build an extract or look up a definition. | Look up a definition. |
| W7 | Definitions page, intro | Search documentation to learn what a field means… Use the conversation or extract builder for institution statistics. | Search the IPEDS codebooks to learn what a field means and which table contains it. Use the conversation for institution statistics. |
| W8 | Definitions results | Ranked source excerpts, not an exhaustive inventory. A documented field may have a physical-location issue… | Ranked codebook records, not an exhaustive inventory. Under "Original source reference": "From the IPEDS {release} codebook." |
| W9 | Checkbox | Also search coded categories and release documentation | Also search coded categories (decided) |
| E1 | Usage limit reached | The Anthropic account has reached its configured API usage limit… offline examples and the extract builder remain available. | The app has reached its usage limit for now, so it can't read new questions. Explore IPEDS and the definitions browser still work. Please try again later. |
| E2 | Model not available to the key | The selected model is not available to this API credential… | The selected model isn't available right now. Choose the other model under About this prototype, or try again later. |
| E3 | Past 30 seconds | (none) | Reading this question took longer than 30 seconds, so it was stopped. No partial result was published. Please try again, or ask it in a shorter way. |
| E4 | API down or network | (part of the general message) | The AI service couldn't be reached. No partial result was published. Please try again in a minute. |
| E5 | Any other failure | The request could not finish. No partial result was published. Check model/network access or use the extract builder. | The request could not finish. No partial result was published. Please try again, or ask it another way. |
| E6 | Database missing | Local metadata catalog missing. See ingestion/README.md. | The IPEDS database isn't available, so the app can't answer questions. If you run the app yourself, build the database first: python build/build_data.py |

**Copied as they are, and true of version 2:** About's blue box (the release range is read from the database), the privacy note (Part 6f checks it on the host), the benchmark intro, and the six topic cards' descriptions and scope notes. I haven't yet checked the two scope notes flagged in the review list (SAT medians from fall 2022; outcome years against entering cohorts) against the dictionary.

## Line counts

| | Before | Now |
| --- | ---: | ---: |
| The question path | 3,965 | 3,992 (+27: answer.py for the error kinds, the picker's name and Cancel; interpret.py and summary.py for the time limit) |
| The page | 161 (app.py) | 669 (ui.py 322, components.py 190, styles.css 75, transcript_scroll.js 66, plus `__init__.py` and app.py 8) |
| Tools behind the page | 0 | 123 (codebook 79, about 44) |
| Version 1's page, for comparison | | ui.py and components.py, 1,051 |

## Open questions

1. **The chart's style is the one difference left that you haven't approved.**
   - **Version 1's automatic chart:**
     - a scale focused on the data, not from zero;
     - axis titles ("Percent (%)", "Reporting period");
     - a dash pattern per school;
     - year labels at 45°;
     - the caption "Gaps indicate unavailable observations. Percentage trend uses a focused, labeled scale."
   - **Version 2's (Part 5c):**
     - starts at zero;
     - no axis titles;
     - solid lines;
     - vertical year labels;
     - long bar labels cut short (`v2_only_years_held.png`).
   - **The fix:** copy version 1's default chart style, not its formatting panel (Stage 7), into `page/components.py`. About 60 to 80 lines, from version 1's `charts.py` `styled()`. Go?
2. **Version 1's typed questions fail in this environment**, so three states were compared with its code, not a screenshot. To see them live, version 1 would need working model access (its own model names or key). Your call whether that's needed.
3. **Seen in passing, in the question path, not the page:**
   - "What is the average starting salary of Yale graduates?" gets "I couldn't find data matching that…" with salary-outlay measures as the closest matches. A pointer to the College Scorecard would be better.
   - Notes under trends: the men-and-women note appears under an admission-rate trend. Is that the right comparability break for admissions?
   - Not changed; for the end-of-part runs.
4. **Commit:** the work order commits at the end of a part. Commit now, as a checkpoint before the remaining steps? Or after the wording and chart decisions?

## What's left in Part 6b after your decisions

- the wording you approve, put in place;
- the chart style, if you agree;
- the comparison re-run;
- the two end-of-part question-set runs (one sequential, one parallel) with the four-row scorecard and the four new examples;
- the full rebuild;
- the report's end-of-part sections.

## After your decisions: end of Part 6b (2026-11-26)

Your decisions are in DECISIONS.md under "2026-11-26: Part 6b decisions after the screenshot comparison" and "end of Part 6b". Checkpoint commit `eb99e14` was made before them. Then the full rebuild (passed its checks) and the two end-of-part runs. Committed locally with your updated work order and plan; not pushed.

### What changed

1. **The chart takes version 1's default style** (`page/components.py`, copied from version 1's `charts.py`; the formatting panel stays in Stage 7):
   - **Trends:** a scale focused on the data, axis titles ("Percent (%)", "Reporting period"), a dash pattern per school, year labels slanted when there are more than six, and version 1's caption: "Gaps indicate unavailable observations. Percentage trend uses a focused, labeled scale."
   - **Bars:** they start at zero; version 1's do too (percent bars run 0 to 100), so there is no exception to report. Ticks at 0, 25, 50, 75 and 100 for percents, with each value labelled at the end of its bar, a zero line, and the caption "Values are labeled; missing observations are not zero."
   - **School names in bar charts** wrap onto as many lines as they need and are never cut off (for example, "Columbia University in / the City of New York").
   - White chart background, as in version 1.
   - **Checked against version 1:** the line chart of the three schools' admission rates now differs by 3.1% of pixels, and only in the data and the year labels:
     - version 2 shows each year's published whole-number rate and labels years "2015-16";
     - version 1 worked out rates with decimals from the counts and labelled years "2015".
   - Screenshots: `docs/reports/stage6b/07_answer_with_chart_v1.png`, `07_answer_with_chart_v2.png`, `v2_bar_chart.png`.
2. **The wording is approved and in place**, with your three edits to W3, W4 and W5 (`page/wording.json`).
3. **"Average starting salary of Yale graduates"** now gets: "IPEDS does not collect earnings… You may find this in College Scorecard (U.S. Department of Education)."
   - **The fix:** five phrasings added to the earnings row's wording in `outside_ipeds.csv`, such as "starting salary of graduates" and "salary after graduation". No new rule.
4. **The note about counting men and women.**
   - **Where it came from:** the gender row of `comparability_breaks.csv`, which matched whole tables (EF, EFA, ADM). Admission rates in some years are worked out from the admissions counts (ADM.ADMSSN over ADM.APPLCN), so every admission-rate trend carried the note, though a total is not affected.
   - **The fix:** a row's `tables` can now name single measures as `TABLE.COLUMN`. The gender row lists the men's and women's measures only: 37 in EF, EFA and ADM, plus, at your decision, the 11 derived ones in DRVADM and DRVEF.
   - Three general lines in `path/trend.py`, one build check in `build/build_dictionary.py`, and the README updated.
   - **Checked live:** the admission-rate trend no longer shows the note; a women's figure does.
5. **The scope notes.**
   - **Graduation rates:** true as written. The 2015–2024 releases cover entering cohorts 2009–2018 (the dictionary's "fall -6").
   - **Test scores:** the 25th and 75th percentiles are held for every release from fall 2015, for SAT and ACT alike; the medians only from fall 2022.
     - The card's sentence was true but incomplete, and my last message was wrong to say only the 25th was held before 2022.
     - The card now reads: "SAT and ACT 25th and 75th percentile scores are available for Fall 2015–2024, and the medians (50th percentile) from Fall 2022, where institutions report them."
6. **Retries:** after a busy or failed API call, the single retry now waits 2 seconds. A timed-out call is still not retried. This adds 4 lines to `path/interpret.py`.
7. **One fix to the question set:** I wrote the expectation for the enrollment-trend example with ";" between its two measures; the grader reads "|". The app's answer was right in both runs. Corrected, and regraded.

### Tests

- **375, all passing** (7 new since the checkpoint):
  - the chart: bars from zero, a focused trend, names wrapped, axis titles and dashes;
  - the retry waiting 2 seconds;
  - the gender note on a women's figure (also a derived one), not on a total;
  - the salary question finding the earnings row;
  - the exact test-score wording.
- **Instruction prompt: 2,496 words** against the 2,500 limit (unchanged in this part).
- **Trial call:** accepted.

### The scorecard (two runs, IPEDS_STAGE=6)

Run 1 is sequential (`--workers 1`, the timing figures); run 2 parallel (4 workers).

| Row | Run 1 (`haiku_6b_first`) | Run 2 (`haiku_6b_second`) | Part 6a end-of-part runs (IPEDS_STAGE=6.0) |
| --- | --- | --- | --- |
| Full set, scored and trend | 156 of 159 (98.1%) | 153 of 159 (96.2%) | 95.5% and 94.2% (of 155) |
| Real users' questions | 63 of 66 (95.5%) | 60 of 66 (90.9%) | 89.4% and 90.9% |
| The same as Part 5e (119) | 117 of 119 (98.3%) | 114 of 119 (95.8%) | 95.8% and 94.1% |
| Badly written set | 54 of 56 (96.4%) | 55 of 56 (98.2%) | 98.2% and 96.4% |
| Median turn | 5.8 s | 5.9 s | 6.3 s and 6.5 s |
| Turns over the limit (whole turn, with the summary) | 8 of 246 | 16 of 246 | 9 and 11 |
| Over the limit without the summary | 3 | 10 | 3 and 6 |
| Cost | $0.28 | $0.27 | $0.27 |
| Shortlist misses | 0 of 27 | 0 of 27 | 0 of 25 |

**The full set is now 159:** the four Explore examples added to the set. IPEDS_STAGE=6 counts the questions due by Stage 6; Part 6a's runs used 6.0.

**The four Explore examples:**
- **Right in both runs:** Ivy League undergraduate enrollment; Yale's undergraduate and graduate enrollment trend; the three-rank faculty salaries (shown with the other ranks, medical school excluded, stated).
- **"Show Yale's instructional staff count from Fall 2015 through Fall 2024, split by full-time and part-time"** asked "Which did you mean?" (instructional staff or all staff with faculty status) in both runs.
  - That counts as right or acceptable, but an example on the page that answers with a question is weak.
  - Its wording says "instructional staff", yet the shortlist offers the faculty term's two readings. Something to look at; nothing changed.

**Manual review.**
- **Run 1:** 43 turns read by hand, 33 carried over from Part 6a's last run.
- **Run 2:** 41 turns read by hand, 36 carried over from run 1.
- **Plus 3 turns in each run** the carry-over script missed (below), and the four stage 7 owner questions, graded for the record.

**Better than Part 6a:**
- **log 8.2** ("how many degrees… last ten years") counts all degrees, not only bachelor's.
- **"Just Yale and Harvard"** keeps the two schools.
- **The Big Ten plus Notre Dame** answers with 19 schools in both runs.
- **The Yale master's question** shows master's degrees only.
- **bw23 "uw madison room and board"** gives on-campus food and housing, $14,124.

**Log 4.6** ("a trend for Ivies plus MIT and Stanford") is still wrong in both runs: Yale's trend only, as in Part 6a. An earlier draft of this report said it was right. The automatic grade passed it, because its expectation names no schools; the fixed carry-over script found it (see "Checks before the push").

**Wrong readings:**

| Turn | Run 1 | Run 2 | Cause |
| --- | --- | --- | --- |
| log 4.6 "a trend for Ivies plus MIT and Stanford" | wrong | wrong | model: kept Yale from earlier turns; as in Part 6a |
| log 24.6 "list them in rank order from largest to smallest" | wrong | wrong | model: listed alphabetically; wrong in earlier parts too |
| log 14.3 (rank by three measures, one outside IPEDS) | right | wrong | model; varies, as before |
| log 60.4 "the universe with the lowest net cost" | right | wrong | model: declined; varies, as before |
| log 60.5 "Where does income data come from in ipeds" | wrong | wrong | model. Run 1 gave general IPEDS glossary entries, not the income source; run 2 declined it as not a data question, as in Part 6a's run 2 |
| log 62.1 "hawaii" | right | wrong | model: declined; varies, as before |
| bw30 "is miami dade the biggest community college" | wrong | right | model; varies, as before |
| bw41 "hi can u tell me abt stanford" | wrong | wrong | model: declined; expected a question back |

None of these comes from the code changed in this part.

**Two readings changed without being wrong.**
- **Log 58.5 and 58.6:** run 1 showed RIT and the five schools beside the national figure, not RIT's comparison group. The six schools are right.
- **Log 3.2 in run 2:** Yale's undergraduates by race came from the 12-month headcount, not fall enrollment.

### Speed

- **The median turn is faster than Part 6a's:** 5.8 s, against 6.3 s.
- **The slowest turns are each worker's first question.** In run 1, log 1.1 took 50.8 s against 8.5 s of model time. In run 2, the first conversation of each of the four workers took 15 to 21 s (logs 1.1 to 4.1).
  - The time goes to loading the search index on a process's first question, made slower by the rebuild just before.
  - This matters for the new switch-test item, "the first answer after the app has been idle". The Part 6f proposal will cover loading the index when the app starts, before the first question.
- **Log 58.7** (expenses per FTE for six schools over ten years) took 17 s and 27 s, against 6 to 7 s of model time. The rest is working out the rate from the counts for each school and year.

### Checks before the push (owner's three questions, 2026-11-26)

**1. Every turn graded differently between run 1 and run 2: 18 turns, all model variation.**
- **Nothing from the runner:**
  - No turn in either run had a model error or waited for a rate limit, and none came near the 30-second limit (slowest of the 19: 18.3 s).
  - The parallel run has the same 246 turns as the sequential one, in the same order, with every conversation's turns kept together and in order.
  - So no worker or merge problem was found, and nothing needed fixing in the parallel runner.
- **Right in one run, wrong in the other (4 turns):**
  - Wrong in run 2 only: logs 14.3, 60.4 and 62.1. Each is a different reading of the same request.
  - bw30: wrong in run 1 only (run 1's request left out Miami Dade).
  - Log 60.5 is wrong in both runs, in different ways; bw41 is wrong in both.
- **Right or acceptable in both, but graded differently** (an answer in one run and a clarifying question or decline in the other; 13 turns): logs 4.7, 7.1, 8.2, 33.1, 36.4, 48.1, 50.1; probe_sal_cmp and probe_cat_housing_smith; bw06, bw24, bw38, bw48 and bw54.
- **Why real users' questions differ (95.5% against 90.9%):** run 2 lost 14.3, 60.4 and 62.1 to model variation, the kind seen in every part.

**2. The carry-over.**
- **All 69 carried grades were checked again independently** (33 in run 1, 36 in run 2). Each carried turn's page is identical, figure for figure, to the reviewed run's, and its expectation is unchanged. All 69 are "correct answer". None was carried wrongly.
- **The gap is fixed** (`scripts/carry_review.py`, 5 lines). A turn whose earlier hand grade overrode the automatic grade now goes back to a person when its answer changes, not to the grader.
- **What the fix caught:** run on run 1, it listed 5 more turns.
  - bw04 and bw10 were graded already.
  - **log 4.6 was wrong in both runs, and log 60.5 was wrong in run 1.** The automatic grade had passed both, because their expectations name no measure or no schools.
  - Both are now graded by hand, which lowers run 1 from 99.4% to 98.1% and run 2 from 96.9% to 96.2%.
- **bw23's expectation** named last year's column (`chg5ay2`); it now also accepts this year's (`chg5ay3`).
- **A limit that remains:** an expectation with no schools or no measure still lets the grader pass a wrong answer whenever no earlier hand grade exists. Log 4.6 is that case.

**3. The instructional-staff example now reads:** "Show Yale's full-time and part-time instructional staff counts from Fall 2015 through Fall 2024."
- **One live call:** it still asks "faculty can mean different things".
- **The cause is the dictionary, not the wording.** The faculty term's two readings are "Instructional staff" and "All staff with faculty status", and the term has `always_ask = yes`. So the app asks whenever the model picks either reading, even when the question names it.
- **The fix (a convention change; your decision):** set the faculty term's `always_ask` to `no`.
  - A bare "faculty" still gets the question, because the term has no default.
  - A question that names "instructional staff" gets the answer.
  - Not built.

### Line counts

| | At the checkpoint | Now |
| --- | --- | --- |
| The question path | 3,992 | 4,001 (+9: trend +4 for breaks that name measures, interpret +5 for the retry wait) |
| The page and the tools behind it | 792 | 834 (components +50 for the chart) |

### Open questions

1. **The faculty term's `always_ask`:** set it to `no`, so that a question naming "instructional staff" is answered? This affects the instructional-staff Explore example and log 7.1.

### Next

As the new order says: the Part 6f proposal (hosting), then Part 6c while you do the account steps.
