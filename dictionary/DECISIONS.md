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

## 2026-11-22: owner decisions on the part 5a report

- **Part 5a approved.**
- **Cost and aid tables reorganised in 2024-25.** In part 5b, a variable-by-variable mapping of the old tables (IC_AY, IC_PY, SFA_P1, SFA_P2, DRVIC) to the new ones (COST1, COST2_FINANCIALAID, COST2_NETPRICE, SFA, DRVCOST) is proposed for review. Where an old and a new table report the same aid year, the same school must give the same value in both; any mismatches are reported.
- **The local database stays where it is,** in OneDrive (`data/ipeds_v2.sqlite`, untracked).

## 2026-11-22: owner decisions on the part 5b gap list

- **1a. Year rules as patterns.** Periods are written with pattern words counted from the release year: `{Y}` is the release year, `{Y-1}` and `{Y+1}` count from it, and `{Y:yy}` gives the last two digits. The 70 period cells are converted.
- **1b. Measure titles that contain a year.** For an earlier year, that year's own codebook title is shown. The dictionary title stays the 2024-25 one.
- **2a. The cost and aid mapping is approved.** Trends run 2015-16 to 2023-24 on the old tables (IC_AY, IC_PY, SFA_P1, SFA_P2, DRVIC, IC) and 2024-25 on the new ones. The 3 "check" variables and the 42 new ones are listed as they are, with no earlier years. For trends, the default net price is the measure with all ten years (average net price for students awarded grant or scholarship aid). The Title IV students reading is offered and labelled "2024-25 only".
- **2b. One release per aid year.** Each aid year's figure is the one first published, from the release in which it is the current year, not a later revision.
- **3. A year IPEDS did not collect.** It shows as a gap, never zero, with the message "IPEDS did not collect {what} in {year}." This is distinct from the per-school missing reasons: a school that did not report keeps its own "not reported" or "not applicable" wording.
- **4a. Category codes by year.** `category_codes.csv` gains a `years` column. A breakdown set or default row uses each year's own codes.
- **4b. Field of study across the CIP 2020 change.** The trend is shown with a break note, with no crosswalk for now. The note says the 2020 changes were mostly at the detailed six-digit level, and the broad two-digit fields used in the field-of-study breakdown changed much less.
- **5a. A comparability-breaks table** (`comparability_breaks.csv`), with a `kind` column: `definition change` or `context`. The rows are drafted with their sources and shown to the owner before they are used.
- **5b. The pandemic years.** One context row for 2020-21 and 2021-22, shown on enrollment, finance and retention trends crossing those years: "Figures for 2020-21 and 2021-22 cover the COVID-19 pandemic period." It is not a definition change.
- **6a. School names in a trend.** Today's name, with "(then: …)" for earlier years where the name differed. Stated in the answer.
- **6b. Closures and mergers.** The gap after a school left is shown, and the app says "merged into … in …" where the directory's NEWID says so.
- **6c. "Its peers" in a trend.** Today's comparison group for every year, stated in the answer.
- **6d. Carnegie groups in a trend.** The classification named in the group row, as of 2024-25, for every year, stated in the answer. This is an exception to the default of each year's own membership.
- **7. Year rules for the seven earlier-only tables** (DRVIC, IC_AY, IC_PY, SFA_P1, SFA_P2, IC_PCCAMPUSES, GR_GENDER), drafted in the pattern form, following the 2024-25 tables they correspond to.
- **8. Rates tested in every year** against the NCES trend files where they have figures. Also, where IPEDS provides a ready-made rate, it is checked each year against the rate computed from counts, and differences are reported.
- **The degree-seeking split in the student aid tables** (before the 2024-25 reorganisation): checked whether the all-undergraduate totals changed definition; a comparability-breaks row says when the split begins (2022-23 release for grant aid and the Pell and loan percents; 2023-24 release for Pell and loan counts and amounts). Years are worked out per variable, so each measure starts in its own first year; a group rate computed from counts does not start before its counts exist; one trend never mixes measures with different first years. For trends, the default Pell, grant and loan measures are the all-undergraduate ones (ten years); the degree-seeking split is offered from the year it starts.
- **Version 3 habit 5 now:** the question log records a conversation identifier with each turn. The other habits wait for the parts where those files are next changed.
- **9. The plan for the aid-table split is approved:** the context row with its first years; start years worked out per variable; group rates starting only once all their counts exist; no trend mixing measures with different first years; all-undergraduate measures as the trend default.
- **9a. Grant recipients 2021-22 and 2022-23.** A context note for grant-recipient trends crossing those years describes the rise and fall without naming a cause: "The number of students receiving grant aid rose in 2021-22 and fell in 2022-23 at many schools; IPEDS does not give a reason."

## 2026-11-22: two additions to Stage 5, to build in part 5e

- **A staged status line while the app works.** Each step is shown in plain words as it runs, for example "Finding matching data…", "Reading your question…", "Getting the numbers…", "Writing the summary…". It includes the AI's own search once part 5d adds it. The wording will be message rows in `terms.csv`, like the other messages.
- **A single-number tile.** When the answer is one figure, it is shown large above the table, with its label, the school or group, and the period.

## 2026-11-22: owner decisions on earlier years stored differently

- **Same information, other column or code.** Where an earlier year stores the same information under a different column or different codes, the earlier row is mapped to the latest year's row through `category_codes.csv` (`years` and a new `same_as` column), so links and breakdowns are tested and usable in that year. Example: 12-month enrollment levels before 2020-21 are in `EFFYLEV` (1 all students, 2 undergraduate, 4 graduate = `EFFYALEV` 1, 2 and 12). Where both columns are filled (2020-21 to 2024-25), the build checks that they pick the same rows.
- **"Not in this year's data"** is kept only for years where the information truly does not exist. The report lists those links and years, and why.
- **A breakdown not usable in a year:** the total is still shown; only the breakdown is unavailable, and the message says why (message row "breakdown not this year").

## 2026-11-22: retired variables (addition to part 5b)

- **The measures table covers every variable from all ten releases,** not only 2024-25. Variables that exist only in earlier releases are added to `measures.csv`, marked not set up, with the title and description from the last year each appeared, and their years available.
- **Successors.** Where a retired variable has a successor (the same meaning under a new name or table, as in the finance and Outcome Measures redesigns), it is linked in `measure_history.csv` so a trend can continue, with a comparability break where the definition changed. Matches are made by name, title and the codebooks' lists of new variables; uncertain matches are marked for the owner's review, not guessed.
- **A message for retired data:** "IPEDS collected {what} from {first} to {last}." followed by "It was replaced by {successor}." or "It is no longer collected." The app never says "not found" for a variable that existed.
- **Retired variables do not crowd current measures off the shortlist:** they rank below current measures, and are used mainly when nothing current fits, or for "what data exists" questions.

## 2026-11-22: Part 5b approved; decisions on the Part 5b report

- **Part 5b is approved.**
- **Comparability breaks:** the drafted rows are approved, with these changes.
  - New hires: attached from 2016-17, with the note "IPEDS changed the hiring window for new hires; its documentation gives different first years, from 2016-17 to 2020-21."
  - Enrollment by major (EFCP): its field codes are compared in the releases before and after 2020-21; the CIP 2020 break is added to EFCP only if the codes changed.
  - Finance, fiscal 2020: the F1A scholarships row is approved. Check whether F2 and F3 changed the same year, and whether pandemic relief revenue appears as a new revenue line in fiscal 2020 or 2021; if so, add a context note for revenue trends.
  - Pandemic note: attached by the period a figure covers, not by release: any figure whose period overlaps March 2020 to June 2022 (fall 2020 and fall 2021; academic and fiscal years 2019-20, 2020-21 and 2021-22). Wording: "Figures covering 2020 to 2022 reflect the COVID-19 pandemic period."
  - Row 13 (finance salaries without benefits): approved, since its successors are approved.
- **Outcome Measures:** for 2015-16 and 2016-17, the total cohort is the sum of the four cohorts. The early cohorts stay mapped to the later ones, with the 2017-18 break note.
- **Completions by race, 2021-22:** the breakdown is offered, with the 4 schools whose parts don't add up treated as exceptions (their total shown, with a note), as with the parent and child campuses.
- **Successors approved:** the 24 DRVF salary percentages (...PS → ...SW..., with break row 13); F_F1A.F1C194 → F1C19DP, F1C196 → F1C19OM, F1C197 → F1C19IN; F_F1A.F1C195 → F1C19OT, with a note that the 2016-17 finance changes may have shifted what is counted as other expenses; IC.APPLFEEG → COST1.APPLFEEG, IC.APPLFEEU → COST1.APPLFEEU, IC.ROOM → COST1.ROOM.
- **Successors approved only if confirmed:** the eight DRVOM percents for 2015-16 and 2016-17, if the old codebook descriptions show the measures were taken at 8 years (then with break row 1); otherwise rejected and named in the report.
- **Successors rejected:** F_F1A.F1C144, F1C146, F1C147 (the "Other expenses" lines); DRVC.SCERT1 → SCERT1A (the old category was split in two); HD.CARNEGIE → CARNEGIEIC and HD.C21SZSET → CARNEGIESIZE (different classification schemes). Rejected retired variables have no successor, so their message says "It is no longer collected."
- **Build speed:** the dictionary build reruns only what a change affects. Wording-only tables (messages and term wording, statements, outside-IPEDS rows, nicknames) reload in seconds with no data checks; a synonym change also rebuilds the search index; a change to a measure rechecks only that measure; a change to category codes or breakdowns retests only that table, in the affected years; new or replaced data runs that year's full checks. There is an option to reload a single dictionary table. A full rebuild is still required before each part's final report and for every yearly update, and it must give the same results as the faster path, with a test. The next full rebuild must confirm that the 92 relabelled breakdown results come out the same.
- **Status line and number tile:** confirmed for part 5e (recorded above, 2026-11-22).
- **Unique names:** a build check that no two measures are shown with the same name; a clash is flagged for a plain name, as with the 20 "Grand total" measures.
- **Work order:** the owner's Part 5b2 (set up every measure) is committed. Do Part 5b2 and stop with its report, including the review list of measures the checks flag.

## 2026-11-23: Part 5b2 approved; decisions on the Part 5b2 report

- **Part 5b2 is approved.**
- **1. Category columns are row choices, never figures.** A coded category column (such as full-time or part-time status) selects rows and is never shown as the answer. A general rule, with a test from the instructional-staff question. Before Part 5c.
- **2. Kind-of-school pairing (`applies_to`)** for the earlier-year net prices and for program-year tuition, as for the current net price. Dictionary rows only. Before Part 5c.
- **3. Shared names.** A short subject for each table, drafted from IPEDS's own table titles (for example "Fall enrollment", "12-month headcount"), applied automatically wherever two or more measures share a name, so the shown name becomes "subject: title". The list of table subjects goes to the owner for review, not the individual names.
- **4. Review list:**
  - programs by field (CDEP): category rows, using the field-of-study codes as completions does;
  - custom comparison groups: per school only;
  - codes the codebook doesn't label: the raw code is shown with the note "IPEDS gives no label for this code";
  - measures that never have a value: the answer is "IPEDS has no values for this measure", never "not found" or zero;
  - the 6 undecided units: listed with a suggestion for each, for the owner's review.
- **5. Partial answers** (for example faculty salary by field) count as expected, in line with the Part 5.0 decision. The expectations are updated.
- **New test question, due at stage 5b2:** "How many schools have negative net worth and which are they?" Expected: an answer listing the schools that meet the condition, using each form's own measure: net position for public schools (F1A18), total net assets for private nonprofit schools (F2A06), total equity for for-profit schools (F3A03). The answer groups the schools by reporting form and names each form's measure, with the statement that the three are not strictly comparable; leaves out system offices by default (outside the national universe) and says so; notes on the public rows that net position often includes the school's share of state pension and retiree-health liabilities, so a negative figure does not by itself mean financial distress; and states the fiscal year. The pension note lives in the dictionary, not in code.
- **Push Parts 5b and 5b2 to GitHub.** Part 5c starts only on the owner's go.

## 2026-11-23: decisions on the Part 5b2 fixes report

- **1. Academic-year/program pairing extended** from tuition to the other charges that come in both versions: books and supplies, food and housing, and other expenses. Tested with the Mount Holyoke room-and-board question.
- **2. One measure per reporting form, as a general rule.** A term reading can name one measure per reporting form (net worth: net position F1A18, total net assets F2A06, total equity F3A03). Lists and conditions use each school's own form's measure, and the answer groups schools by form with the statement that the measures are not strictly comparable. Tested with the net-worth question.
- **3. Table subjects approved,** with two changes: GR_PELL_SSL = "Graduation rates, Pell and Subsidized Stafford loan recipients"; COST2_FINANCIALAID = "Financial aid, full-time first-time students". Applied. For the shared names the subjects do not resolve, a rule taking the distinguishing words from IPEDS's own long descriptions (for example academic year versus program) is proposed, with examples, before it is applied.
- **4. The 6 S_SIS rank headcounts:** unit `count`.
- **Built now:** category rows for programs by field (CDEP); the message "IPEDS gives no label for this code"; the message "IPEDS has no values for this measure".
- **Working cadence.** The fast build path is used for routine changes. A full rebuild runs only before a push to GitHub, at the end of each stage, and for yearly updates; its result must match the fast path, as tested. The question set runs once per change order, and twice only at the end of a part, when the scorecard is judged.

## 2026-11-23: decisions on the second change-order report; Part 5c begins

- **Shared names:** the distinguishing words come from the approved pairings ("by academic year", "by program", and the public/private pairing). The public/private pairing is added to the aid-by-income measures. Plain names for the roughly 10 left over are drafted for the owner's review in the next report.
- **Recurring wrong readings,** each fixed by a general instruction or dictionary line, never a special case:
  - "the example set" and similar references mean the schools in the previous request;
  - "both" after the app has offered options resolves against those options (the cause in the dual-enrollment follow-up is found and the general rule fixed);
  - "the universe with the lowest net cost": no reading is forced; the expectation accepts a clarifying question, since "universe" is also a dictionary term.
- **The review list is settled:** unlabelled codes shown raw with the note, empty measures with their message, comparison groups per school.
- **Go: Part 5c,** as the work order describes, including the trend rules recorded there. Stop after it with the report.

## 2026-11-23: Part 5c built (trends); drafts for the owner's review

- **Messages drafted** in `terms.csv` (kind `message`, note "Part 5c (trends), drafted 2026-11-23"): how a group counts schools in a trend (each year's own, today's only, peers), the "Today's schools only" button, earlier names "(then: …)", mergers, the detailed-table note for graduate 12-month headcount, the decline for trend questions not yet supported (ranking, lists and counts over several years), and the three reasons a breakdown is missing in one year. Wording to review.
- **Which years "since 2015" covers (draft, from the owner's expectation for the Yale Pell question):** a trend takes every release whose figure's period reaches the years asked. So "since 2015" for Pell includes the 2015-16 release (aid year 2014-15), giving all ten releases, as the expectation says. To confirm.
- **Trend operations:** a school, several schools, a group, a school beside a group, a group split by sector, level or control, and a breakdown for one school or one group. Ranking, lists and counts over several years are declined with the latest year offered.
- **The chart's palette, font and axis colours** are taken from version 1 (read only) and kept in `config.py`, since they are presentation, not an IPEDS convention.

## 2026-11-23: Part 5c approved; decisions on its report

- **1. Which periods a trend covers.** "Since 2015" means periods that start in 2015 or later (fall 2015, aid year 2015-16, fiscal year 2015). The answer states the first and last periods shown. The Yale Pell expectation is nine years (aid years 2015-16 to 2023-24).
- **2. Trend expectations.** The 17 trend expectations marked "acceptable until trends exist", and log 4.5, now expect a trend.
- **3. A single earlier year** ("Yale's enrollment in 2018") is answered as a one-year table.
- **4. The 13 Part 5c messages** are approved as written.
- **5. Ranking and listing by the change between two years** ("which schools grew enrollment the most since 2015?"), built from the trend pieces, with the same rules: each year's own schools by default, gaps never zero, notes on breaks, and the ranking guard. Ranking by a single earlier year comes with it. Counts over several years wait.
- **6. Plain names.**
  - The six finance pairs: the second of each pair is named "(financial health section)", the codebook's own section name.
  - F1C19IN and F1C197 are one series (F1C197 is the approved predecessor): they keep the same name, and the retired one shows its years, "(until 2015-16)".
  - The GR200 still-enrolled pair and the EFA level pair are approved as drafted.
  - IC TUITVRY1-3 stay unnamed and not set up.
- **7. Questions wholly outside IPEDS.** When the question as a whole is about a topic in `outside_ipeds.csv`, the request names no measure. When only part of a question is outside IPEDS, the rest is still answered, as decided in Part 5.0.
- **Standing rule:** before every full question-set run, one cheap trial call confirms the API accepts the reply format.
- **Push:** Part 5c is pushed to GitHub (the full rebuild has run).

## 2026-11-24: decisions on the Part 5c decisions report; Part 5d begins

- **1. F3B01 / F3D09:** named by the codebook's section names, as with the financial-health pairs: F3B01 "(summary of changes in equity)", F3D09 "(revenues section)".
- **2. 45.1 and 45.2** ("Show a 10-year trend", "Show a longitudinal trend"): expect a clarifying question (which measure, and which school or group), not a decline.
- **3. Note wordings for rankings and lists by change:** the guard note and the list note are approved as written. The first note is split: "{left} left out because a value is missing in one of the years." and, only for a percent change, "{left} left out because the starting value is zero or below, so a percent change can't be computed." A change in counts keeps schools whose values are zero.
- **4. No re-run now;** Part 5d will measure the fixes.
- **Database inventory:** `docs/DATABASE.md`, written by `scripts/database_inventory.py` after each full rebuild (committed 2026-11-24).
- **Go: Part 5d,** starting with the badly written test set for the owner's review before it is used.
