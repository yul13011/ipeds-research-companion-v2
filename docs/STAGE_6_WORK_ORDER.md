# Stage 6 work order

Paste everything below the line into Claude Code, opened in the `ipeds-research-companion-v2` folder.

---

This is the work order for Stage 6 of version 2. Its goal is in section 9 of the plan: version 2 replaces version 1 at the existing link, https://ipeds-research-companion.onrender.com/, once it does everything version 1 does and passes the switch test. Work through it one part at a time. The order is 6.0, 6a, 6b, then the Part 6f proposal, then Part 6c while I do the account steps for 6f, then the rest of 6f, then 6g (owner decision, Nov 26, 2026: publish as soon as possible, so hosting starts early). Stop after each part, write a report, and wait for my go before starting the next. Parts that say "propose first" stop twice: once with the proposal, once with the build.

READ FIRST
- `CLAUDE.md`: the working rules. They all still apply.
- `docs/V2_PLAN.md`, especially sections 1 (principles), 4 (how the app understands a question), 8.2 (Stage 5 results) and 9 (Stage 6). The plan is the design. Build to it; do not redesign it. If something in it does not work against the real data, stop and tell me before changing the design.
- `docs/reports/STAGE_5G.md`, `STAGE_5G_FOLLOWUP.md` and `STAGE_6_CHANGE_ORDER_1_PROPOSALS.md`: where Stage 5 ended.
- `docs/V1_ASSESSMENT.md` and the version 1 code in `..\agent-redesign`, for the features carried over. Read version 1; never change it, its data or its Google Sheet log.

HOW EACH PART ENDS
- Tests written for each piece and all tests passing. No test calls the API or writes to a shared log.
- A report in `docs/reports/STAGE_6_<part>.md`: what was built, test results, line counts for the question path, the page and the build, anything that did not work as planned, and open questions.
- A scorecard with four rows (the full set, real users' questions, the same 118 questions as Part 5e, the badly written set), the median turn time and the turns over the limits, whenever the question set is run.
- A local commit. Do not push until I approve the report.
- Then stop and wait.

STANDING RULES FOR THIS STAGE
- Accuracy comes first, then speed, then cost.
- The model never writes SQL and never produces a number. Only the code decides facts about the data: which years are held, whether IPEDS collects something, which schools are in a group.
- Conventions live only in the `dictionary` folder, with a dated line in `DECISIONS.md` for each decision. Where you need a decision I have not made, list it in the report and wait; do not guess.
- No patterns that read the user's wording to decide meaning, in code or in the dictionary.
- Ask me before installing any package, and before creating any account, service or dataset outside this computer.
- Keep the default model as Haiku at its current effort setting.
- Keep the five version 3 habits from Stage 5 (plan section 12.1). Page code stays out of the operations: the features in Parts 6b and 6c call the same operations and result objects the chat uses, so a chart, a download and an on-screen answer always agree.
- Carrying over version 1 code: copy what is useful into version 2 and adapt it to version 2's result objects. Do not import from `..\agent-redesign`. Say in each report what was copied and how much was rewritten.
- Names: official IPEDS titles, as in Stage 5.
- Build and test cadence, judging wrong readings, and the trial call before every full question-set run: as in Stage 5. Speed limits: 10 seconds a turn, 20 with a search.
- Secrets: the API key and any hosting tokens are never written into the repository, the logs or a report.
- Out of scope for Stage 6 (Stage 7): web search, groups from a list the user confirms, the formula field, category sets, comparing and suggesting measures (items 46 and 47).

PART 6.0. CHANGE ORDER 1: FIXES FOUND IN STAGE 5

Build proposals (a) and (b) in `docs/reports/STAGE_6_CHANGE_ORDER_1_PROPOSALS.md`, with these decisions:
1. (a) Years held: as proposed. When a question also asks for figures, offer them as a button, as proposed. This also covers the two-part example for follow-up item 31; report whether log 1.1 now passes.
2. (b) Trends and earlier-year columns: as proposed. For a year inside the ten releases, show the figure that year's own release published. No note about later revisions.
3. Review point: show me the draft of the two new measures.csv columns for the 411 measures (a summary by table, and every row where the script was unsure) before the build uses them.

Done when: log 1.1, log 11.1 and the four new trend-gap questions pass; Yale's net price for 2022-23 is $26,044; the question set (IPEDS_STAGE=6.0) shows no new wrong readings.

PART 6a. FOLLOW-UPS REAL USERS NEED (propose first)

Three gaps from the real users' questions (plan sections 4.7 and 9.3):
1. A group plus named schools: "the Ivies plus MIT and Stanford", "the Big Ten plus Notre Dame". The request must be able to hold a group and named schools together, with code building the combined list and "Interpreted as" naming both parts.
2. A trend that names no measure ("show a 10-year trend"): when the previous request has a measure, use it; when it does not, ask which figure, offering the likely measures, instead of "not found".
3. Follow-ups that refer to schools named several turns earlier.

Propose first: the change to the request shape for each (checked against the reply format's size with a trial call), the code steps, the tests, and the line counts. Then wait. After my go, build, and update the test expectations for the group-plus-schools questions that now expect a clarifying question.

Done when: the follow-ups that failed in every run of Part 5g pass, with no new wrong readings elsewhere.

PART 6b. THE PAGE: VERSION 1'S LAYOUT AND FEATURES

The page must look exactly like version 1 (owner decision, Nov 25, 2026).

What is carried over (plan section 9.4):
- Explore IPEDS: the six topic cards with description, scope note and three example questions, and "Ask your own question about…". Every example question must pass in the question set; add them to it.
- Ask & Analyze: version 1's panels and menu; the "Need ideas?" panel with a topic dropdown and example questions.
- Results: the "Display table" switch.
- Tools: the definitions browser. Version 1's extract builder is not carried over (Stage 7); its absence is an approved difference from version 1.
- About: privacy note, AI switch, and benchmark match rates taken from the latest benchmark run, not typed in.
- Friendly error messages for every failure the page can meet (API down, time limit, database missing).

How it is carried over:
1. Version 1 is the reference. Copy its page code, theme settings (.streamlit/config.toml), CSS, fonts, palette, spacing, labels and wording as they are; rewire only the data calls to version 2. Do not recreate the layout.
2. Use the same Streamlit version as version 1. If version 2 needs a newer one for something it already does, tell me what and why before changing anything.
3. Rebuild version 2's current sidebar (model selector, Clear conversation) to look like version 1's.
4. Remove the summary switch from the sidebar; the summary is always on, as in version 1. Keep an internal setting to turn it off for testing only, not shown to users. Record this in DECISIONS.md.
5. Elements version 2 has and version 1 doesn't (Years held, statements, provisional notes): use version 1's existing styles only, no new ones. List each one with a screenshot for my approval.

Review point before building: a short list of each version 1 feature, what it does in version 1, and how it will work in version 2. Flag any feature that does not fit version 2's design, rather than forcing it.

The check: list every screen and state (Explore, empty chat, answer with table, chart, school picker, clarifying question, decline, About, sidebar open and closed). Run version 1 and version 2 side by side at the same window size, take a screenshot of each state in both, compare them pixel by pixel, and report every difference. Ask me before installing a screenshot tool such as Playwright.

Done when: the only differences left are the version 2 elements I've approved, and the two approved absences (the extract builder and the chart formatting panel, both Stage 7).

PART 6c. TABLE DOWNLOADS

- Downloads: Excel with a sources sheet, CSV, and the technical audit file, as in version 1. Every download carries the same figures, periods, notes and definitions as the answer on screen, from the same result object.
- Chart formatting (the "Format chart" panel, chart edits typed in chat, PNG and SVG downloads) has moved to Stage 7 (owner decision, Nov 26, 2026). The automatic chart already built stays. Until Stage 7, "make it a bar chart" keeps its current decline, and the missing panel is an approved difference from version 1 in the Part 6b check.

Tests: a download for a trend, a group figure and a breakdown matches the on-screen table cell for cell.

PART 6d. DATA EXTRACTS: MOVED TO STAGE 7

Owner decision, Nov 25, 2026: data extracts are built after version 2 is published, in Stage 7 (plan section 10.1). Version 1's extract builder is not carried over. Go from Part 6c to Part 6f.

PART 6e. A SELF-CONTAINED DATA PIPELINE: MOVED TO STAGE 7

Owner decision, Nov 26, 2026: bringing the converter and the cross-year index into version 2 moves to Stage 7 (plan section 10.3). It must be done before the next IPEDS release is added and before version 1's folder is removed. Go from Part 6c to Part 6f.

PART 6f. HOSTING (propose first)

Plan section 9.2. Propose first, then wait. The proposal covers:
1. The version 2 dataset on Hugging Face: separate from version 1's, holding only IPEDS data and the dictionary; its size; how the host downloads it at start-up and how long that takes.
2. The Render settings for version 2 (start command, environment, memory and disk needs against the current plan), prepared but not applied.
3. How hosting will be tested before the switch. Do not create a new public link; propose a way to test with the host's real settings and say what it costs.
4. The spending guard: a daily limit on API spend and a per-conversation limit on questions, with numbers based on the measured cost per turn, and the wording of the usage-limit message.
5. The question log on the host: where it is kept, separate from version 1's Google Sheet; what each turn records (including the conversation identifier); and how I get it back to add real users' questions to the scorecard.
6. The secrets: which values are secrets and where each is set.
7. The switch and how to reverse it, as numbered steps I can follow in the Render dashboard.

After my go, build what is needed, publish the dataset (ask me before creating it), and run the hosting test. Report: start-up time, the median turn time on the host against local, and the provisional label and every warning checked on the host.

PART 6g. MEASURE IT AND THE SWITCH TEST

- The question set (IPEDS_STAGE=6, with the four-row scorecard, the Explore and "Need ideas?" examples, and the owner questions due by Stage 6). Don't rerun it twice by default. If the question path (shortlist, interpret, request, resolve, fetch, trend, summary, dictionary) hasn't changed since the last two-run scorecard, reuse it and say which runs. If it has changed, run twice and say what changed. In either case, run the full set once on the host, to check that hosting changes no answer and to measure speed there.
- The benchmarks across ten years, reusing earlier results where nothing they depend on has changed, and saying which.
- Time and cost per question, locally and on the host.
- Line counts: which modules grew most during Stage 6.
- A scorecard against the switch test in plan section 9.7: the version 1 features in place, except the extract builder and chart formatting; the success test met in two runs; real users' questions at least 90% right or acceptable in two runs; version 2 running on the host without unresolved errors; the speed limits met on the host (10 seconds a turn, 20 with a search, the median reported, and the first answer after the app has been idle measured separately).

If any part of the switch test is not met, say what is missing and stop. If all of it is met, stop and wait. Then:
1. I test the hosted app myself with 10 to 15 questions of my choosing. Give me a short checklist of what to try (a lookup, a trend, a group, a follow-up, a definition, a decline, a download).
2. I switch the Render link myself, following the steps from Part 6f.
3. A few days after the switch: read version 2's hosted log, list errors, slow turns and wrong readings among real users' questions, and propose any fixes as one change order. Remind me of the steps to switch back if anything serious appears.

START by reading the documents above and telling me in a few sentences how you understand Stage 6 and Part 6.0, with anything unclear. Then wait for my go.
