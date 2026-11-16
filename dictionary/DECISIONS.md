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
