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
