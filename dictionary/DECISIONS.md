# Owner decisions

One dated line per decision, with its reason. Newest at the bottom. A change to any table in this folder adds a line here.

## 2026-11-15: working decisions

- **Workbook blanks.** A blank "Your decision" cell in the review workbook meant the draft was accepted. Reason: stated in the workbook's instructions.
- **National universe.** 50 states and DC, Title IV, excluding administrative offices (5,626 schools). Reason: it matches the NCES count for 2024-25. Not chosen: all 6,072 directory rows; 50 states and DC Title IV including administrative offices (5,692); Title IV primarily postsecondary only, excluding administrative offices (5,597); Title IV primarily postsecondary degree-granting (3,867).
- **Model.** A configuration setting; the key is read from `ANTHROPIC_API_KEY`. Stage 4 runs the question set once with Haiku and once with Sonnet and reports accuracy, time and cost. Reason: to choose the model on evidence.
- **Codebook tables.** The four codebook tables are loaded into the local database. Reason: definitions and value labels come from them.
- **Trend questions in Stage 4.** Scored in their own column, still recording the structured request and whether measure and schools were read correctly. Reason: the slice holds one year.
- **Question log.** Each distinct question is run once; test rows, greetings and chart edits are reported separately. The "37" in the plan is out of date.
- **Year.** `year` in every table is the release year. Every result must state the real period (fiscal year, aid year, entering cohort). Never show a bare release year for a table that reports an earlier period.
- **Raw question log.** `docs/question_log.csv` is not tracked. `docs/test_questions.csv` is tracked and holds question text with a conversation number and turn order, no session IDs or times. Reason: privacy, while keeping follow-ups replayable.
- **Local database.** Stays at `data/ipeds_v2.sqlite`.
- **Tables across years.** No table is kept for which table families exist in which releases. It can be regenerated from the cross-year index when more years are added.

## 2026-11-15: cleaning (`special_codes.csv`, build)

- **Numbers stored as text.** The codebook's `DataType` field (N = numeric) is the rule, not guesses from the values. A value that fails to convert is reported, not dropped.
- **Padded text.** Text is trimmed; a blank cell is missing.
- **Special codes.** A code becomes missing only by a row in `special_codes.csv`, either by codebook label or for one named table and column.
- **A1.** Carnegie "Not classified", "No research designation" and "Not in Carnegie universe" are kept. Reason: they are real categories; 5,530 schools have no research designation.
- **A2.** -9 "Not active" in the response-status columns is kept. Reason: it is a status.
- **A3.** -2 used as a row label in `EFFY`, `S_OC` and `S_NH` is kept. Reason: it describes the row, not a missing measurement.
- **A4, A5.** -1 and -2 in columns where the codebook lists no codes are set to missing through `table and column` rows. Reason: they are codes, and the system name matters for groups such as SUNY.
- **A6.** Small negative values in `GR200.BAAEXCL` and `GR200.L4AEXCL` are left as they are. Reason: they are adjustments, not codes.
- **A7.** The reason a value is missing is kept per school in a side table, for display only. It must never enter a calculation.
- **A8.** Code 0 "Implied no" reads as no.

## 2026-11-15: school groups (`school_groups.csv`, `group_members.csv`)

- **B1, B2.** Northeast, Midwest, South and West are the Census regions by state, and the definition is stated in "Interpreted as". The eight BEA regions are separate groups under their own names. "The South" has one definition, the Census one. Reason: Census regions are what users mean by these four words.
- **B3.** "Private" alone means private nonprofit, and the app states it.
- **B4.** "State schools" means public four-year, and the app states it.
- **B5.** Small is under 5,000 students; large is 10,000 and above; "big" is the same as large. The cut-off is always stated.
- **B6.** "Liberal arts colleges" is Carnegie 2021 Baccalaureate Colleges: Arts & Sciences Focus.
- **B7.** "Community colleges" is public two-year, with the caveat that community colleges awarding bachelor's degrees are classified as four-year.
- **B8.** R1 and R2 use the Carnegie 2025 research designation; the 2021 definition is used only when the user says so.
- **B9, B10, B11, B14.** Hispanic-serving institutions, other minority-serving institutions, women's colleges and named associations such as the AAU are declined for now, saying IPEDS has no flag for this group. No derived rule.
- **B12.** Flagships use version 1's list of 53 for now, under review. The app says flagship is not an IPEDS category.
- **B13.** "Selective" asks the user, offering admission rate under 10%, under 25% or under 50% (in `terms.csv`).
- **B15.** "Colleges" and "universities" both mean institutions and do not filter. The words "universities", "public universities" and "private colleges" were removed from the drafts for this reason.
- **B16.** A conference matches on any of the four conference columns (football, basketball, baseball, track).
- **B17.** All 63 religious affiliations are loaded.
- **Named groups.** Ivy League, Ivy Plus and Seven Sisters are carried over from version 1 as member lists. The Ivy League is the member list, not the conference code.
- **Nicknames.** The 22 nicknames from version 1 are carried over (`school_nicknames.csv`).

## 2026-11-15: other tables

- **C1.** `SAL_IS` and `SAL_NIS` are academic year 2024-25 (`year_meaning.csv`).
- **C2.** The two "faculty" definitions come from version 1's Yale faculty check and are loaded as `pending owner approval` until approved (`terms.csv`).
- **C3.** The eight-year award rate uses the Outcome Measures total row, OMCHRT 50 "Total entering, Total" (`rates.csv`).
- **C4.** Faculty salary by academic field has no pointer. The app says IPEDS has salaries by rank and gender, not by field (`outside_ipeds.csv`).
- **C5.** Enrollment by major is collected for nine selected fields (`EFCP`). The app answers yes for those fields and, for other majors, says degrees awarded by program is the nearest measure. The row moved from `outside_ipeds.csv` to `terms.csv`. Reason: correction to the workbook.
- **C6.** The IPEDS title is the plain name where none is given, and the IPEDS long description is searchable. Stage 4 reports separately how often the shortlist failed to include the right measure.
- **C7.** Priority 2 and 3 variables are "IPEDS collects it, but it is not set up in this app yet" (`measures.csv`, `in_first_version`).

## 2026-11-15: how conventions are organised

- **One home.** This folder is the only source of conventions. The review workbook was converted once and archived in `docs/archive`; nothing reads it.
- **Change orders.** A change to a convention comes from the owner as a change order: change the row, add a line here, rebuild, run the tests, report.
- **Folder contents.** `DECISIONS.md`, `README.md` and ten tables. Terms and their readings are one file; label rules and column rules for special codes are one file; the national universe is a row in `school_groups.csv`.

## 2026-11-15: change order after Stage 2

- **Column-keyed special codes.** The 19 `table and column` rows are approved as listed.
- **Flagships.** The list of 53 is approved for now; status is `in use`.
- **Faculty.** Both definitions are approved and in use, and the app always asks. Results show the total with the full-time and part-time split. Statement: "Counts include medical school staff."
- **Breakdown sets.** `category_codes.csv` gains `breakdown_set`, `set_total` and `set_fixed`; `measures.csv` gains `breakdown_set` and `set_total` for breakdowns stored as columns. A set names its total and, where a table is keyed by several category columns, the fixed values of the others. The build tests that each set adds up at every school; a set that fails is not loaded and is reported. A set can be additive (`sum of parts`) when the data has no total. The breakdown operation uses only named, tested sets; a breakdown with no set is declined and logged. Reason: a single total-or-part flag cannot say which codes form one clean breakdown.
- **Draft sets.** Nine row sets and three column sets are drafted in the tables and tested. They are pending owner approval and must not be used by Stage 3 until approved. See `docs/reports/BREAKDOWN_SETS.md`.
- **Lists in one cell.** `words` and `codes` stay as they are.
- **Correction to B15.** Bare "colleges" and "universities" do not filter. "Public universities" means public four-year and "private universities" means private nonprofit four-year, each stated. "Private colleges" means private nonprofit, all levels.
- **Faculty salary statement.** "Salary figures cover full-time instructional staff outside the medical school, equated to nine-month contracts."
- **Degrees.** All six levels are returned, including "Doctor's degree - other", as an additive set so the result shows a total.
- **Out-of-state tuition.** A second reading of "tuition" uses `COST1.chg3ay3`, published out-of-state tuition and fees 2024-25. Checked: the same schools report it and the default reading, and it is never lower.
- **Graduation rate for a group that mixes levels.** The app asks, with three options: four-year schools only, two-year schools only, or both shown separately.
- **City groups.** Fine as built: matched by name; naming the state too narrows it.
- **Nickname kinds.** Confirmed: direct, alias, picker.
- **Peers.** Default to the school's own IPEDS comparison group when it has one, and state it. Ask only when it has none. A new group, "Has an IPEDS comparison group", records which schools have one (2,326 schools in the 2024-25 directory).
- **Two-year graduation rate.** Added to `rates.csv`: `GRTYPE` 30 over 29. From counts 0.4267; NCES 0.427.
- **Rate statuses.** All thirteen rates are marked tested as of 2026-11-15.
- **Measure periods.** The `period` column in `measures.csv` is approved.

## 2026-11-16: breakdown sets approved

- **All twelve sets approved.** Nine stored as rows and three stored as columns; Stage 3 may use them.
- **Rows with no detail.** Rows where IPEDS collects no detail at all are not failures. A breakdown asked for on such a row shows the total and says the detail is not collected. Reason: graduation rate by race is needed, and the 100%-of-normal-time rows have no detail by design.
- **Gender.** The set is men and women. "Gender unknown" and "another gender" stay as their own measures. Reason: in the data, men plus women already equal the total.
- **One code, one set: limit lifted.** `set_fixed` names a default that the request may change. The build tests each set at every value of the other category columns and loads only the values that pass. Reason: "bachelor's degrees by field" and "undergraduates by age" must work.
- **Age caveat.** Enrollment by age is optional in even-numbered years; 2,576 of 5,842 schools reported it for fall 2024. `year_meaning.csv` gains a `caveat` column, shown whenever figures from that table are given for a group.
- **Less-than-two-year graduation rate.** Left out for now.

## 2026-11-16: Stage 3 design approved, with changes

- **Operations.** Lookup and compare are one operation (one or more schools). Group total and group rate are one group operation: code decides from the dictionary whether the measure is summed or computed from counts. The model never chooses between a total and a rate.
- **Units.** `measures.csv` gains `unit` for first-version measures: count, dollars, percent, average, ratio or coded. Only count and dollars may be summed across schools (the "summable units" setting in `terms.csv`). A percent, average or ratio with no row in `rates.csv` gets a decline for a group figure, with the per-school list offered. Blank is not summable. Pending owner approval of the list.
- **Shortlist only.** Resolve rejects any measure, school, group, category code or breakdown set that was not on the shortlist shown to the model for that question, and logs it as a wrong reading.
- **Edits.** A follow-up can change any field (schools, measures, groups, breakdown, condition, sort, year, operation), with add, remove and replace for list fields. "Now for Texas", "break that down by gender" and "rank them" must work as edits.
- **Pending options.** After a clarifying question, the next model call is shown the pending options, so "the first one" or "both" can be matched.
- **Logging the shortlist.** Each question's log row records the shortlist (IDs only).
- **Structured output.** The model reply uses the API's structured output. An invalid reply is retried once, then a plain failure message is shown and logged.
- **Tests and the API.** Tests never call the API; they use saved model replies. Live calls happen only in a smoke test the owner approves, and in Stage 4.
- **Default rows.** `category_codes.csv` gains `default`: the overall total where one exists, first major for completions. Pending owner approval of the list.
- **Applies-to.** `rates.csv` gains `applies_to`, the school group a rate row applies to.
- **Unstated things.** No year: the latest period. No group: the national universe. "Top" with no number: 10. Each is stated in "Interpreted as". Recorded as `setting` rows in `terms.csv`.
- **Ranking guard.** For rates, schools with fewer than 30 in the denominator are excluded; the number excluded is stated and the count is shown beside each value. The user can ask to include all. The threshold is a `setting` row in `terms.csv`.
- **Staff by race and gender.** No optional-year caveat for now.

## 2026-11-16: units and default rows approved

- **Units.** The `unit` column in `measures.csv` is approved as drafted, including published prices as `average` and SAT and ACT percentile scores left blank.
- **25 added measures.** The measures named by approved terms and the main count column of each approved breakdown set are in the first version.
- **Default rows.** The 19 defaults in `category_codes.csv` are approved. Three key columns have no default and the app asks: students receiving awards by level, enrollment by major, graduation-rate cohort rows.

## 2026-11-16: group averages and finance reporting forms

- **Group averages.** Averages are treated like rates: a row in `rates.csv` names the total and the count, both summed across schools before dividing. `rates.csv` gains `method`: `sum of counts`, or `weighted average` where IPEDS gives no total. An average with no row still gets a decline for a group figure.
- **Core expenses per FTE student.** One row per finance form: core expenses over 12-month FTE enrollment (`DRVEF12.FTE12MN`, the FTE IPEDS uses for its own per-FTE figures). Public and private nonprofit together give 38,376, matching NCES.
- **Average Pell grant.** Total Pell dollars over Pell recipients: 5,300, matching NCES.
- **Average salary.** Salary outlays equated to nine months over staff on 9-to-12-month contracts (`SAL_IS`), all ranks and each of six ranks. 100,254 with the app's national universe; NCES's 100,224 includes administrative offices, and the counts give exactly 100,224 when they are included. The universe is not changed.
- **Average net price.** Each school's average weighted by its cohort count (`GISTN2` for public in-state, `GRNTN2` for private). No NCES figure. Pending owner review; not used until approved.
- **Finance reporting forms.** `measures.csv` gains `reporting_form` (GASB, FASB, for-profit) for finance measures, and `school_groups.csv` three groups of schools by the form they report on. A group figure never combines forms; it is shown separately for each form, with the statement in the "different reporting forms" setting in `terms.csv`. The split is by form, not by control, because 18 public institutions report on the FASB form.
- **One name for the three per-FTE rows.** The three core-expenses-per-FTE rows share the name "Core expenses per FTE student" and differ by `applies_to`, so one request covers all three forms and a group mixing forms is split automatically. The build now requires rows sharing a name to say which schools each covers.
- **Split by.** "sector", "level" and "control" in a request map to `HD.SECTOR`, `HD.ICLEVEL` and `HD.CONTROL` through `setting` rows in `terms.csv`; sector is the default.
- **Finance form groups.** The three "Reports on the ... finance form" groups are schools with a core-expenses value on that form (`has value`, `DRVF.F1COREXP` and so on), not schools with a row in the form's table. Reason: 16 public schools have GASB-derived figures in `DRVF` but no row in `F_F1A`; the narrower definition gave $33,118 for GASB core expenses per FTE where the counts give $32,973.
- **Rates pending review are not used.** A `rates.csv` row whose status begins "Pending" is skipped by the question path until the owner approves it (the two net price rows).

## 2026-11-16: Stage 3 approved; change order

- **School beside its group.** The school is never hidden. Its counts are shown, and when the count behind its rate is under the ranking-guard threshold, a small-cohort warning is shown. The warning text is the "small cohort" setting in `terms.csv`.
- **Term statements.** Every term statement is a sentence for the user, not an instruction to the app. Nine were rewritten; the before-and-after list is in `docs/reports/STAGE_3_CHANGES.md`.
- **Word notes.** Sentences that explain which words a group stands for moved to a new `word_note` column in `school_groups.csv`, shown in "Definitions & sources". "Interpreted as" shows only the group's definition. Seven groups.
- **Plain names.** The 20 generic count columns ("Grand total" and similar) have plain names in `measures.csv`.
- **Graduation periods.** Results state the entering cohort and the status date: "students who entered in fall 2018, status as of August 31, 2024". Cohort years are offsets from the release year, in a new `entering_cohort` column in `measures.csv` (one cohort) and `year_meaning.csv` (by school level where a column covers more than one cohort). The sentence is the "cohort period" setting. The codebook's table titles give cohort years one year earlier than its variable descriptions; the variable descriptions are used, as they match the status date.
- **National universe on every group figure.** Counts, totals, rates, averages, rankings, lists, splits, group breakdowns and peers stay inside the national universe and say so. "All institutions" is a reading of the "national universe" setting that the user can ask for. Questions about named schools are not affected. Question (e) changes from 156,621 / 426,480 to 156,443 / 426,082 (both 36.72%); the national two-year rate stays 0.4267 against NCES 0.427.

## 2026-11-16: the handoff from the model to code (after the first live smoke test)

- **Tags instead of typed IDs.** Every shortlist item has a short tag: M measures, S schools, G groups, R category rows, B breakdown sets, T term readings, O outside-IPEDS topics. The model answers in tags only, and code maps them back to real IDs. The structured-output schema is built for each question: each field accepts only the tags on that question's shortlist, and unused fields are null or empty lists, never the word "none". Reason: in the first smoke test four of nine replies failed on typed text ("none", a reading with its ID attached, a column with its table name).
- **Breakdowns on the shortlist.** Each measure on the shortlist lists the breakdown sets it supports, its own and those through its detailed table.
- **Summary to detailed measures.** `measures.csv` gains `detailed_measure`, linking a summary measure to the same figure in a detailed table (for example `DRVEF.EFUG` to `EFA.EFTOTLT where EFALEVEL = 2`). 54 links for fall enrollment, 12-month enrollment and degrees. When a breakdown is asked for on a summary measure that has none of its own, resolve uses the detailed measure and "Interpreted as" says so (the "detailed measure" setting). The build tests every link at every school: a summary of 0 with no detailed row agrees. 11 schools that report together with a related campus differ; the page warns when one of them is shown (the "detail differs" setting).
- **The school picker for an ambiguous name** ("add Northeastern", three Northeastern campuses on the shortlist) is acceptable. No change.
- **Real replies as tests.** The nine replies from the first live smoke test are saved test cases (`tests/replies/real_*.json`), each with what the model wrote and, where tags now rule out what it typed, the tag equivalent.
- **Tokens logged.** Each question's log row holds input and output tokens, the raw reply in tags, and the size of each part of the prompt.

## 2026-11-21: precedence, link check, cost

- **One precedence rule.** Wherever a value can come from more than one place, the first that has it wins: what the user stated, then a reading the user chose, then values already decided (carried over when a summary measure switches to its detailed equivalent), then a dictionary default, which only fills what is still empty. It is applied in one function in resolve (`first_present`): for chosen readings, for the switch to a detailed measure, for a measure's category rows, and for a breakdown's fixed values. Questions (d) and (f) of the second smoke test are fixed through this rule, with tests from both live replies.
- **Summary-to-detailed links approved, with a build check.** A link loads only if the summary equals the detailed value at every school, except schools IPEDS flags as reporting together with a related campus for that survey (parent or child record). Any other difference fails the link: it is not loaded, and the build reports it. All 54 links load; their differences are at 11 flagged schools.
- **Where the parent/child rule lives.** `year_meaning.csv` gains `parent_child_flag`: for each table, the `FLAGS` columns that mark parent (1) and child (2) records for its survey, and the parent's ID. The note shown is the "related campus" setting in `terms.csv`.
- **Related-campus note in every answer.** When an answer shows a school IPEDS flags as a parent or child record for the measure's survey, it says which campus it reports with: a parent names its related campuses, a child names its parent.
- **Fixed reply shape and prompt caching.** The reply schema has the same tag ranges for every question (M1–M64, S1–S16, G1–G20, R1–R64, B1–B32, T1–T24, O1–O4). A shortlist longer than a range is cut to it. A tag not on the question's shortlist is rejected as a wrong reading. The instructions are marked for caching. Reason: cost; the per-question schema could not be cached.

## 2026-11-21: after Stage 4

- **A measure per kind of school (defect A).** `terms.csv` gains `applies_to`: for a reading that names one measure per kind of school, the school group each measure applies to. Net price: public schools use the in-state measures (NPIST2, NPIS42); private nonprofit and for-profit schools use NPGRN2 and NPT42. A new group, "Private, nonprofit or for-profit" (HD.CONTROL 2 or 3), holds the private side. Each school takes the measure that applies to it in every operation. A group with more than one kind is shown separately for each, with the "kind of school" statement. An empty ranking says that no school in the group reports the measure (the "empty ranking" setting).
- **Net-price group averages approved.** Each school's average is weighted by its net-price cohort count: GISTN2 and GRNTN2 for grant-aided students, GIS4N2 and GRN4N2 for Title IV students. Rows for the Title IV readings were added. A group that mixes public and private schools is split by control automatically, as finance is by form. Rankings of net price now apply the ranking guard to the cohort count.
- **Statements out of code.** The "shown separately for each kind of school" wording moves from resolve to the "kind of school" setting in `terms.csv`.
- **Topics outside IPEDS (defect B).** The page already showed the outside-IPEDS message; Stage 4 graded three such answers as wrong by mistake (corrected in the Stage 4 report). The empty table drawn under the message is removed.
- **Level check (defect C).** When the question names schools and no group, the graduation-rate level default looks at the named schools, not the national universe.
- **Units of computed rates (defect D).** `rates.csv` gains `unit` (`percent` or `dollars`). A rate with no ready-made measure, such as the Outcome Measures award within eight years, is shown in that unit: 47.3%, not "$0".
- **Chosen reading over the level default (defect E).** The precedence rule already holds when the reply names the reading, which a test now confirms. The instructions now tell the model to always give the T tag when the user names a specific reading.
- **"Latest" year (defect F).** `year.kind` gains `latest`. "The most recent year" sets it and leaves `stated` empty, so it is not declined as an unknown year.
- **Category columns on the shortlist.** Each measure on the shortlist lists its category columns (such as staff category or student level), with the default row and the shortlisted row tags. The instructions say to list a measure once per category when the user asks for several (full-time and part-time), and to keep the asked-for category in `row` for a breakdown.
- **Default model: Haiku.** `IPEDS_MODEL` still overrides it, and Sonnet stays a choice on the page. Decline reasons and "closest" are capped at one short sentence each (at most 25 words), in the instructions.
- **Staff total including graduate assistants: not built; returned to the owner.** IPEDS stores graduate assistants as a separate staff category (S_OC STAFFCAT 4400). A total including them is the sum of two rows, which no field in the dictionary can express yet. The sum is 4,087,830 nationally against NCES's 4,114,069 (0.64% short), so it would not match NCES either. See the Stage 4 follow-up report.
- **Small differences from NCES.** The +0.03 to +0.05% differences in 12-month headcount, awards, FTE and students awarded (and −0.12% in full-time instructional staff) are recorded as known provisional-data differences. Recheck when the final 2024-25 release is out.
- **State or school.** When a new question's only group is a state and a school is called by the state's name, the app asks which. The name patterns are the condition of the "state or school" setting in `terms.csv` ("University of {state}; The University of {state}", with or without a campus after a hyphen). At most three schools are offered. Not asked when counting or listing schools, or for an edit.

## 2026-11-21: owner decisions on the Stage 4 follow-up

- **Staff total.** Keep the IPEDS grand total (S_OC STAFFCAT 1100, EAP EAPCAT 10000) as the default. Whenever it is shown, the page says it excludes graduate assistants, who can be asked for as their own figure (S_OC STAFFCAT 4400, EAP EAPCAT 40000). The note is a new `statement` column in `category_codes.csv`, shown whenever an answer uses that row. No sum-of-rows feature now; the planned formula field will cover it.
- **"Go back" restores the whole earlier request, operation included.** The path already did this for the `back` action. In the Stage 4 run the model rebuilt the request field by field instead. The instructions now name `back` for "go back", "as before" and "back to all eight", and say not to rebuild field by field. A test covers the three-turn case.
- **Haiku effort stays at its current setting.** Low effort is not tried; accuracy comes first at this stage.
- **Breakdown sets show where they are held.** Each set on the shortlist shows the values it is held at (for example "Grand total; First major"), or, for a set stored as columns, that it keeps the measure's own category row unless `row` names another. A measure broken down through its detailed table shows the level it carries over (for example "All students, Undergraduate total").

## 2026-11-21: shorthand synonyms, first set

- **"undergrad" and "grad".** "undergrad" is added to the synonyms of every measure whose name contains "undergraduate" (208 measures), and to every category row so labelled (220 rows). "grad" is added to every measure whose name contains "graduate" (not "undergraduate") or "graduation rate" (110 measures), and to every row labelled graduate (49 rows). "grad" is deliberately on both meanings ("grad students", "grad rate"); the model picks from context.
- **Synonyms for category rows.** `category_codes.csv` gains `synonyms`, used only to find a row for the shortlist, the same way measure synonyms are used.
- **Further shorthand** (first-year, FT/PT, admit rate, and others) is drafted for the owner's review and not yet added.

## 2026-11-21: shorthand synonyms, second set

- **Approved unmarked rows added:**
  - PT
  - applicants / apps / applications → ADM.APPLCN
  - admits / admitted students → ADM.ADMSSN
  - matriculants / enrollees / yield count → ADM.ENRLT
  - completers
  - net cost
  - Pell rate / percent Pell
  - endowment per student
  - census enrollment / fall census
  - SFR / S/F ratio / student faculty ratio
  - dual enrollment / dual credit / concurrent enrollment / early college
  - eight-year completion / 8-year award rate
- **first-year, freshman, freshmen.** Added to every first-version measure and category row labelled first-time (170 measures, 43 rows). Each carries the statement: "IPEDS counts first-time students (new to college); first-year transfer students are not included."
- **FT.** Added to full-time measures and rows only, not full-time equivalent.
- **selectivity.** Added to the admission rate and the SAT and ACT score measures.
- **persistence, persistence rate.** Added to both retention rates, with the statement "IPEDS calls this the retention rate; it is what is often called persistence." Also added to the Outcome Measures still-enrolled measures, with the statement "IPEDS reports this as students still enrolled (Outcome Measures); it is one meaning of persistence."
- **completions, awards conferred.** Added to the awards total and the degree-by-level counts.
- **FTE, FTE enrollment.** Added to 12-month FTE enrollment and to every staff FTE measure (not to "per FTE" ratios).
- **COA, cost of attendance, sticker price.** Added to all nine total-price measures.
- **low-income.** A term with one reading, the percent of undergraduates awarded Pell grants, and the statement "IPEDS does not measure income; the Pell share is a common proxy."
- **faculty.** No change; the existing term covers it.
- **professors, full professors.** Added to the instructional staff measures, salary by rank, and the Professor rank rows.
- **student body.** Added to total fall enrollment.
- **spending per student.** Added to instruction expenses per FTE, and to core expenses per FTE (a rate, so `rates.csv` gains `synonyms`).
- **tuition revenue.** Added to the tuition revenue per FTE measures.
- **URM, underrepresented minority.** A row in `outside_ipeds.csv`: IPEDS reports race categories, and combining them into a group is planned for a later stage.
- **Statements on measures.** `measures.csv` gains `statement`, shown whenever an answer uses the measure, the same way a category row's statement is. The first-time and persistence statements use it, so they show whenever those measures are used, not only when the user wrote the shorthand. The path does not read the user's wording.

## 2026-11-21: shortlist ranking and term statements

- **Field weights in the search.** A match in a measure's name or synonyms counts three times a match in its table's title or description. The constant is `NAME_WEIGHT` in `shortlist.py`; it is search tuning, not an IPEDS convention.
- **At most five of the fifteen main slots from one table** (`PER_TABLE`). The rest of a table stays reachable through its category rows and sets.
- **Grouping near-duplicates: not now.** It goes into the next stage, with meaning search.
- **A term's statement only when its reading was chosen, where the dictionary says so.** `terms.csv` gains `statement_when`: `chosen` shows the statement only when the model chose that term's reading; `always` shows it whenever one of the term's measures appears. "low-income" is `chosen`. The other terms stay `always`, because their statements carry caveats that apply to every use of the measure, such as the net-price lag and the graduation-rate levels. A row can be switched in the table. Measure statements (first-time, persistence) are unchanged.

## 2026-11-21: last changes to the text search for this slice

- **Word endings.** No English stemmer is installed, and the owner asked to be told before any package is installed. So the owner-approved fallback is used: hand rules that also trim "-ing" (more than five letters) and "-ment" (more than six), applied the same way to the question and the dictionary. "offering" now finds "offer", and "enrollment" finds "enroll".
- **Soft per-table cap.** At most five of the fifteen main slots from one table, unless a further measure from that table scores at least twice the next measure from another table (`SOFT_CAP` in `shortlist.py`).
- **The text search is frozen for this slice.** No further ranking changes. The remaining shortlist misses are listed in the Stage 4 follow-up report, as input for the next stage's meaning search.

## 2026-11-22: topics outside IPEDS, from the new logged questions

- **Three rows added to `outside_ipeds.csv`:** graduation rates by major, high school of graduation, and linking individual student records. Each says what IPEDS does report instead (degrees by field, first-time students by state of residence, school-level figures) and where the data can be found.
- **No more school nicknames.** The drafted "WSU Tech" nickname is not added. The directory already carries "WSU Tech" as that school's alias.

## 2026-11-22: Stage 5, part 5.0 (fixes from owner testing)

- **Misspelling tolerance in the search.** A question word the search does not know is matched to the index words it misspells. Words of four letters or fewer may only swap two neighbouring letters (Yael → Yale, tehc → tech). Five to seven letters may be one letter off; eight or more, two. The question's own word is kept beside the correction. The limits are search constants in `shortlist.py`. This is the agreed exception to the search freeze.
- **The four answers.**
  - "IPEDS does not collect this" comes only from a row in `outside_ipeds.csv`.
  - A model decline saying "not in IPEDS" without such a row, a "measure" decline, and a "what data exists" question with nothing matched all become "not found". That answer names the closest matches from the search and is logged as a search miss.
  - The instructions no longer let the model decide that IPEDS lacks something.
- **Messages written by code from the dictionary.** Every message shown when the app cannot answer, or answers in part, is a "message" row in `terms.csv`, by kind of decline. The rows are drafts, used while building and listed in the 5.0 report for owner review. The model's own explanation goes to the question log (`model_explanation`) only. No message contains internal words (shortlist, tag, dictionary, measure codes); a test checks this.
- **Declined, clarified and partly answered requests are kept as the previous request.** A follow-up such as "show 2023-24" edits it. The model's decline reply now carries the request it would have made. Choosing an option or a school clears the pending question.
- **Questions about a decline** (types 48 and 49). The decline's message, its outside-IPEDS source if any, and an alternative built from the request are stored with it. A new reply kind, `about_decline`, answers "why not?" (the message), "where can I find that?" (the source, or "I don't have another source to point you to for this.") and "what can you show instead?" (the alternative, run).
- **Answer what can be answered.**
  - When some of the years asked for are held, the held year is shown and the missing years are named.
  - When one of several measures is not set up, the others are answered and the missing one named.
  - When none of the years is held, the decline names all the measures asked for (or the reading chosen, such as "degrees by level"), not only the first.
- **Alternatives build on the request.** The alternative offered with a decline is made by code from the request in hand: the same request for the year held, without the unavailable group or breakdown, as a ranking of each school's figure, or the nearest set-up measure of the same table. It is never the model's own suggestion.
- **Fixes found in the 5.0 rerun.**
  - "ROI" is added to the example wording of the outside-IPEDS row on earnings and return on investment, so "What's the ROI for Yale?" reaches it.
  - An edit made while options are open ("show 2023-24" after "which Marian University?") is applied to every option, and the app asks again (message row "which did you mean").
  - When the model declines a group it named, the app's own check runs, so the group's own statement ("IPEDS has no flag for this group") is shown.
- **Further fixes found in the later 5.0 reruns.**
  - A school-against-group comparison shows every school named, not only the first.
  - Option labels written by the model have tag codes (S4, M7) removed before they are shown.
  - A school picker keeps its request as the previous request, so "show 2023-24" asks again with the change.
  - The instructions say to list every measure of a broad topic in "what data exists" answers (up to 15), and to copy a period or trend ("since 2015", "the last ten years") into the year as written.

## 2026-11-22: owner decisions on the part 5.0 report

- **Judging wrong readings.** A path defect must never appear. Model readings are tracked as a rate over two runs of the full set, must stay at or above 90% right or acceptable, and are reported with the range across the runs. A model misreading that recurs across runs is addressed through a synonym, a dictionary row or an instruction line, never a special-case patch.
- **Synonym approved:** "grant and scholarship percentage" and close variants (grant and scholarship percentages; percent receiving grants or scholarships; percent awarded grants or scholarships) on SFA.UAGRNTP.
- **Marian:** the question is kept as written. The expected outcome for turn 2 is that the app asks again which Marian, with 2023-24 applied.
- **Decline messages approved,** with three changes:
  - "not collected source": "You may find this in {pointer}."
  - "calculation average": "{what} is reported separately for each school, so I can't combine it into one figure for a group."
  - "breakdown does not add up": "The breakdown "{set}" isn't shown for {where}, because its parts don't add up to the total in the IPEDS data."
- **Short plain names** for first-version measures with long IPEDS titles are drafted for review in `docs/stage4/plain_names_draft.csv` (`scripts/plain_names_draft.py`). Not loaded until approved.
- **An outside-IPEDS row covers only the part of a question it matches.** When other parts can be answered, they are answered, and the part IPEDS lacks is named beside the answer (message row "not collected partly"). The instructions say to return a request for the part that can be answered, with the outside-IPEDS topic beside it.
- **Timing.** Reports give the slowest tenth of questions as well as the average time.

## 2026-11-22: plain names

- **No plain names for the 514 measures with long titles.** The official IPEDS titles stay as the names shown in answers and messages, because they match the codebook. The 20 plain names already approved (for the "Grand total" measures) are kept. The draft list, `docs/stage4/plain_names_draft.csv`, is set aside and not loaded. User vocabulary is handled by synonyms, and "what does this mean?" by the glossary in Part 5f.

## 2026-11-22: Stage 5, part 5a (ten releases stacked)

- **Ten releases loaded,** 2015-16 to 2024-25, read in place and cleaned with each year's own codebook. Each year is labelled provisional or final from its release folder name (table `_releases`). Answers show "Figures from the IPEDS 2024-25 release (provisional)", with the provisional warning as before.
- **The app still answers from the latest year only** until trend questions (part 5c). Every lookup the app makes is filtered by year.
- **Dictionary checks scoped to the latest year for now.** These run on the 2024 data only; part 5b extends them to every year:
  - the year_meaning coverage check;
  - the category-row, summary-to-detailed link and breakdown-set tests;
  - the groups made from every value of a column;
  - the group school counts.

  No dictionary row was changed in this part.
- **Build fix: a group defined by several conditions now narrows year by year.** Before, a school meeting a condition in any year could stay in another year's group. With ten years loaded, this would have changed the national universe for 2024; it is 5,626, as before.
- **One step to add or replace a release:** `python build/build_data.py --release <folder>`. It removes every row of that year first, so a replaced release leaves nothing behind. The runbook is `UPDATING.md`.
