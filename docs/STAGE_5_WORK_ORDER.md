# Stage 5 work order

Paste everything below the line into Claude Code, opened in the `ipeds-research-companion-v2` folder.

---

This is the work order for Stage 5 of version 2. Work through it one part at a time, in order. Stop after each part, write a report, and wait for my go before starting the next.

READ FIRST
- `CLAUDE.md`: the working rules. They all still apply.
- `docs/V2_PLAN.md`, especially "How the app understands a question", "Stage 5 plan" and "Stage 6 and later". The plan is the design. Build to it; do not redesign it. If something in it does not work against the real data, stop and tell me before changing the design.
- `docs/reports/STAGE_4.md` and `STAGE_4_FOLLOWUP.md`: where the first slice stands.

HOW EACH PART ENDS
- Tests written for each piece and all tests passing. No test calls the API or writes to a shared log.
- A report in `docs/reports/STAGE_5_<part>.md`: what was built, test results, line counts for the question path and the build, anything that did not work as planned, and open questions.
- A local commit. Do not push.
- Then stop and wait.

STANDING RULES FOR THIS STAGE
- Accuracy comes first, then speed, then cost.
- The model never writes SQL and never produces a number.
- Conventions live only in the `dictionary` folder, with a dated line in `DECISIONS.md` for each decision. Where you need a decision I have not made, list it in the report and wait; do not guess.
- No patterns that read the user's wording to decide meaning, in code or in the dictionary.
- Ask me before installing any package.
- Keep the default model as Haiku at its current effort setting.
- Keep version 3 in view (see "Future direction: a research companion" in the plan). Five habits, from now on:
  1. Each operation is a clean function, with structured input and output and no chat-page code inside it.
  2. Every result carries its source: table, year, definition and statements.
  3. The number check in Part 5e is a general component that can check any AI-written text against any result, not only the summary.
  4. "What data exists" stays a self-contained step that can be called on its own.
  5. Logs record a conversation identifier with each turn.
  Do not build version 3 features; just follow these habits, and say in each report where existing code does not yet follow them.
- Names: measures are shown by their official IPEDS titles, to match the codebook. Plain names are kept only for the 20 "Grand total" measures. Where two or more measures share a title, the shown name is "subject: title", with the subject taken from IPEDS's own table title. The build checks that no two measures are shown with the same name.
- Build and test cadence (owner decision, Nov 23): use the fast build path for routine changes. Run a full rebuild only before a push to GitHub, at the end of each stage, and for yearly updates; its result must match the fast path, as tested. Run the question set once per change order, and twice only at the end of a part, when the scorecard is judged.
- Judging wrong readings (owner decision, Part 5.0): a path defect must never appear. Model readings are tracked as a rate over two runs of the full set, must stay at or above 90% right or acceptable, and are reported with the range across runs. A misreading that recurs across runs is fixed through a synonym, a dictionary row or an instruction line, never a special-case patch.
- Out of scope for Stage 5: moving the Access-to-SQLite converter and the cross-year index into version 2 (a later task), web search, the formula field, category sets, groups from a confirmed list, data extracts, the format-chart panel, downloads, the Explore page, "Need ideas?" and the About page.

PART 5.0. FIXES FROM OWNER TESTING (one year of data, as now)

Build these, as set out in parts 2, 3 and 5 of "How the app understands a question":
1. Misspelling tolerance in the search, for measure words and school names: words a letter or two off, and swapped letters, applied the same way to the question and the dictionary. This is the agreed exception to the search freeze.
2. The four answers when data is not found (yes; collected but not set up; not collected; not found). "IPEDS does not collect this" comes only from `outside_ipeds.csv`. Otherwise the answer is "not found", with the closest matches or a suggestion to rephrase, logged as a search miss. Make sure neither the instructions nor resolve let the model state on its own that IPEDS lacks a topic.
3. User-facing messages written by code from the dictionary, by kind of decline. The model's own explanation goes to the log only. No internal words such as "shortlist" or "tag" may reach the user.
4. A declined, clarified or partly answered request is kept as the previous request, so a follow-up such as "show 2023-24" edits it. Choosing an option or a school clears the pending question.
5. Questions about a decline (question types 48 and 49): store the decline reason with the request, so "why not?", "where can I find that?" and "what can you show instead?" are answered from it.
6. Answer what can be answered. When part of a request is out of range, show what exists and say what is missing, instead of declining the whole request.
7. Two smaller defects from testing: a degrees answer whose note named only "Associate's degree", and a decline that suggested an unrelated measure ("tuition and fees"). Suggestions must build on the request in hand.

Done when:
- The owner questions due at stage 5.0 pass.
- "what data do you have on admisisons" lists the admissions measures, and "what was the fall enrollment for wsu tehc" either asks which WSU or finds WSU Tech, never Texas Tech.
- The full question set rerun on Haiku shows no new wrong readings and no false "IPEDS does not collect this".
Report the new scorecard beside the last one.

PART 5a. STACK THE TEN YEARS

- Add the nine earlier releases in `..\agent-redesign\data\annual` to the local database, read in place, using the cross-year index. Apply the same cleaning rules to each year, with special codes taken from each year's own codebook.
- Report: row counts per table and year against the source; columns whose type changes between years; tables present only in some years; variables renamed or retired between years; build time and database size.
- Make adding or replacing a release one repeatable, tested step: each year IPEDS adds a provisional release for the newest year and replaces last year's provisional release with its final version. Test both cases, including that a replaced release leaves no rows behind. All years are kept; there is no rolling window.
- Write `UPDATING.md` at the top of the project: the yearly update steps in "Keeping the app up to date" in the plan, with the exact commands for each step this project can run.
- The app labels each year's data as provisional or final.
- Do not change the dictionary in this part beyond what the build needs to run.

PART 5b. THE DICTIONARY ACROSS YEARS

Start with a gap list and wait for my answers before loading anything, as in Stage 2. Then:
- The years each measure is available, worked out from the data.
- Year rules written as offsets from the release year, replacing fixed years: net price one year behind, graduation-rate entering cohorts, finance fiscal years, the period text shown with each result.
- Category codes that change across years: field-of-study codes (revised in 2020), gender categories, Carnegie classifications, and any others you find. Breakdown sets and summary-to-detailed links tested in every year.
- Comparability breaks: a dictionary table of years where a definition changed, with the note to show. Draft it from the codebooks, using `docs/sources/ipeds_overview_2019.pdf` (NCES's description of IPEDS and the history of each survey component) as a starting source. The overview ends in 2019, so later breaks must come from each year's codebook. List each break, with its source, for my review.
- The school directory over time: names, closures and mergers, the national universe for each year, comparison groups for each year, and parent and child flags for each year.
- Rates tested in every year against the NCES trend benchmark files where they have figures.

PART 5b2. SET UP EVERY MEASURE

The released app must answer everything IPEDS has. Today 762 measures are set up; set up all the rest.
- Every measure in measures.csv, including: detailed cost and aid (net price by income band, charges by student type and others); yes/no and coded institutional facts (programs offered, services, policies); staff, enrollment and completions detail; Outcome Measures subgroups; the detailed lines of the three finance forms; and the survey response flags.
- Draft what each needs in bulk, from rules, not by hand: the unit from the codebook's data type and format; the period from the table's year rule; years available from the data; value labels for coded measures from the codebook; and, for multi-row tables, the default row and tested breakdowns as now.
- Finance lines follow the existing rule: a group figure for a group that mixes reporting forms is split by form, with the statement. A comparison of individual schools on different forms carries the same note.
- Averages and percentages with no counts to combine stay "reported for each school only" for group figures, as now.
- Build checks confirm every newly set-up measure in every year it exists.
- Give me a review list only for measures the checks flag or the drafting could not decide (for example a unit that is unclear, or a coded measure without labels). Do not ask me to review the rest.
- Retired variables (owner decision, Nov 22): the measures table covers every variable from all ten releases, not only 2024-25.
  - Add the variables that exist only in earlier releases (about 326) to measures.csv, with the title and description from the last year each appeared and their years available, and set them up like the rest.
  - Where a retired variable has a successor (same meaning under a new name or table, as in the finance and Outcome Measures redesigns), link it in measure_history.csv so a trend can continue, with a comparability break where the definition changed. Match by name, title and the NEWVARIABLES lists; mark uncertain matches for my review rather than guessing.
  - A message for retired data: "IPEDS collected {what} from {first} to {last}", followed by "It was replaced by {successor}." or "It is no longer collected." The app never says "not found" for a variable that existed.
  - Retired variables must not crowd current measures off the shortlist: they rank below current measures and are used mainly when nothing current fits or for "what data exists" questions.
  - Show me the successor list in the report.
- Then rerun the full question set on Haiku and report the change. Some decline in shortlist quality is expected now that many more measures compete; Part 5d is where the search is improved for the full list, so do not tune the search in this part.

PART 5c. TREND QUESTIONS

- A school, several schools or a group over time; "since 2015", "the last five years", a range of years, and the change between two years.
- Group membership: each year's own list of schools by default, stated in the answer; "today's schools only" offered as an option.
- Missing years shown as gaps, never as zero. A note, and the year marked, when a comparability break falls inside the period.
- Follow-ups that change the period ("now since 2015", "just the last three years").
- A basic automatic chart: a line for trends, bars for comparisons. Take the palette and fonts from version 1's chart settings (read only). No formatting panel.

Trend rules decided in Part 5b (recorded in DECISIONS.md):
- Default measures for trends are those covering all ten years: the all-undergraduate aid measures, and the average net price for students awarded grant or scholarship aid. The degree-seeking aid split and the Title IV net price are offered from their own first years.
- Years available are worked out per variable. A group rate starts only once all its counts exist, and one trend never mixes measures with different first years.
- Each aid year's figure is taken as first published, from the release where it is the current year.
- Schools are shown by today's name, with "(then: …)" for earlier years, and "merged into … in …" where the directory records it. "Its peers" uses today's comparison group for every year. Carnegie groups use the stated classification for every year.
- A year IPEDS did not collect a measure gets "IPEDS did not collect {what} in {year}"; a breakdown not available in a year gets its own message, and the total is still shown.
- Comparability-break and context notes are shown on any trend crossing them. The pandemic note goes by the period a figure covers (March 2020 to June 2022), not by release.
- Graduate 12-month headcount before 2020-21 comes from the detailed table, since the summary lacks it.
- Retired variables use the "IPEDS collected {what} from {first} to {last}" message, continuing through an approved successor where there is one.

PART 5d. UNDERSTANDING ANY PHRASING

- Write a test set of 30 to 50 badly written questions: misspellings, abbreviations (UConn, UMich, CUNY, Mizzou, WSU Tech), informal phrasing ("how many kids go there"), and "RTI" (RIT, or RTI International, which is not a college). Include expected outcomes. Show me the set before using it.
- Meaning search: compare fastembed and sentence-transformers, each with a comparable small English model, on that set and the full question set. Report how often the right measure reaches the shortlist, time added per question, and install size. Ask before installing either, and propose one before building it in. Meaning fingerprints for the dictionary are computed once in the build. Meaning search runs on every question, and its results are merged with the word search into one shortlist.
- The AI's own search: when nothing on the shortlist fits, the model calls the app's search with its own words, at most twice. Log every search call. Code still rejects any item that did not come from a search shown to the model for that question.
- Group near-duplicate measures (those differing only by a subgroup such as Pell status or gender) so they do not crowd the shortlist, judged from the dictionary's own category labels.
- Measure the shortlist-miss rate and the number of wrong readings before and after each layer. Speed limits: typical questions under 5 seconds, hard ones under 10.
- The search now has to work for every measure set up in Part 5b2 (about 3,000, including retired ones). Fix the three shortlist tests marked for this part, and keep retired variables ranked below current measures (at most two on the shortlist).

PART 5e. WRITTEN SUMMARY

- A second model call writes two or three neutral sentences about the result, given only the table and its notes. No interpretation beyond the numbers.
- Code checks that every number in the summary appears in the table (allowing for rounding and percent formatting). If the check fails, the summary is dropped and logged; the table stands alone.
- It streams in under the table and can be switched off. Log its time and cost. Tests use saved replies.
- A staged status line while the app works, showing each step in plain words (for example "Finding matching data…", "Reading your question…", "Getting the numbers…", "Writing the summary…"), including the AI's own search from Part 5d.
- A single-number tile: when the answer is one figure, show it large, with its label, school or group and period, above the table.

PART 5f. EXPLAINING TERMS AND CONCEPTS (question types 44 and 45)

- Fuller explanations of IPEDS terms built from the dictionary: definition, period, year rules and caveats.
- Load the official IPEDS glossary, `docs/sources/ipeds_glossary_2025-26.pdf`, into the dictionary as a table: term, definition, and edition. The PDF is a browser printout in two columns, so long terms wrap across lines: parse it carefully, report the number of terms, and list any entries you could not separate cleanly. Do not edit the definitions; this table is NCES's wording.
- Draft a reviewed concepts table in the dictionary for what the glossary does not cover, plus plain-English versions of key terms where the official wording is heavy. Choose the terms from evidence, and show the reason for each: terms users asked about (question log, decline log, owner questions); words the app itself shows in "Interpreted as", notes and definitions; IR concepts that change how a number should be read (for example retention versus persistence, provisional versus final data, Pell as an income proxy); and how IPEDS works, using `docs/sources/ipeds_overview_2019.pdf` (the universe, Title IV, parent and child reporting, imputation). Show me the draft for review before the app uses it.
- Check the dictionary's statements against the glossary and list any that contradict it.
- Keep the glossary and the dictionary from conflicting:
  - An answer that shows data uses the measure's own description and period. The glossary is used only when the user asks what a word means.
  - Glossary text is always labelled with its edition (2025-26). For a given year's data, that year's codebook wins; the comparability-break table flags years where a definition changed.
  - When the word being explained also has an app convention in terms.csv (for example "private"), show the official definition and then the convention ("In this app, 'private' alone is read as private nonprofit; say 'for-profit' to include them").
  - Glossary entries get their own small section of the shortlist, at most three, so they never crowd out measures, and they are used only for explanation questions. A data question always uses measures.
  - Tests include data questions whose words match glossary terms ("retention rate at Yale", "net price for Harvard", "graduation rate for public universities in Texas"); they must still return data, not a definition.
- When a user asks what something means, the app uses these sources in order and says which one it used: (1) the reviewed concepts table; (2) the IPEDS glossary, cited as such; (3) the dictionary, when the term is an IPEDS measure; (4) the model's general knowledge, labelled "general explanation, not from IPEDS documentation", with the question logged for review. An explanation never states on its own whether IPEDS collects something; that part follows the four answers.

PART 5g. MEASURE IT

- NCES trend benchmarks and Yale benchmarks across all ten years.
- The full question set with trend questions now scored, plus the owner questions due by stage 5f (set IPEDS_STAGE accordingly) and the badly written set.
- Version 1 against version 2 on the trend questions, from version 1's log, as far as the log allows.
- Time and cost per question.
- Judge model readings as set out in the standing rules: two runs of the full set, the range across runs, and the 90% threshold.
- A scorecard against the success test in the plan: benchmarks match apart from known definition differences; at least 90% of scored questions right or acceptable, trend questions included; no false "IPEDS does not collect this"; the speed limits.

START by reading the documents above and telling me in a few sentences how you understand Part 5.0, with anything unclear. Then wait for my go.
