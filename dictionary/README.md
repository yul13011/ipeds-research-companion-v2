# The dictionary folder

This folder is the only home for conventions: what a word means, which counts sit behind a rate, which schools are in a group. No convention lives in code, in prompts or in any other file.

- Each table is a CSV you can open in Excel. One row is one fact.
- After any change, the build must be rerun. `python build/build_dictionary.py` reloads the tables (about a minute and a half) and stops with a list of problems if a row does not fit the data. A change to `special_codes.csv` needs the full build, `python build/build_data.py`.
- Every owner decision gets one dated line in `DECISIONS.md`.
- Table names are the local names without the year (`HD`, not `HD2024`). A measure is written `TABLE.VARIABLE`, for example `DRVGR.GBA6RTT`.
- Two columns hold short lists in one cell: `words` (separated by semicolons) and `codes` (separated by commas).

## DECISIONS.md

One dated line per owner decision, with its reason.

## measures.csv

One row per IPEDS variable in the release (2,599).

- `table`: the data table the variable is in.
- `variable`: the IPEDS variable name.
- `title`: the IPEDS title.
- `long_description`: the IPEDS long description. Searched when shortlisting.
- `format`: IPEDS format. `Cont` is a quantity, `Disc` is a coded answer, `Alpha` is text.
- `data_type`: `N` numeric or `A` text, from the codebook.
- `rows_per_school`: one row per school, or many.
- `reporting_form`: for finance measures, the form the school reported on: `GASB`, `FASB` or `for-profit`. A group figure never combines measures or rate rows with different forms; the "different reporting forms" setting in `terms.csv` holds the rule and its statement. A rate row takes the form of its numerator.
- `unit`: for first-version measures, one of `count`, `dollars`, `percent`, `average`, `ratio` or `coded`. Only the units named in the "summable units" setting in `terms.csv` (count and dollars) are added up across schools. A percent, average or ratio is computed for a group from its counts in `rates.csv`, or the group figure is declined. Blank means not summable (text, identifiers, test-score percentiles).
- `priority`: 1 for ready-made and most-asked measures, then 2 and 3.
- `in_first_version`: `yes` or `no`. A `no` means "IPEDS collects it, but it is not set up in this app yet".
- `entering_cohort`: for graduation measures that cover one entering cohort, the cohort as a kind and an offset from the release year, such as `fall -6` (the 2024 release: students who entered in fall 2018). Blank means the table's rule in `year_meaning.csv`.
- `period`: filled only when the variable reports a different year from its table (net price for 2023-24 in a 2024-25 table). Blank means the table's period in `year_meaning.csv`.
- `plain_name`: your plain-English name. Blank means the IPEDS title is used.
- `synonyms`: other words users say for this measure.
- `detailed_measure`: for a summary measure, the same figure in a detailed table, written `TABLE.COLUMN where COLUMN = code; ...`, for example `EFA.EFTOTLT where EFALEVEL = 2` for undergraduate enrollment. When a breakdown is asked for on the summary measure, the app uses the detailed one and says so. The build checks that the two agree at every school and lists the schools where they do not (schools that report together with a related campus).
- `breakdown_set`: filled when this column is one part of a breakdown stored as columns, such as "By race and ethnicity" or "By gender". All the columns of one table with the same name form the set.
- `set_total`: the column that the parts add up to, or `sum of parts` when the data has no total column. The build tests that the parts add up on every row; a set that fails is not loaded.

## terms.csv

Words with more than one possible reading. One row per reading and measure. A reading that shows several measures together (the cost profile) has one row per measure.

- `term`: the name of the term. All rows of one term share it.
- `words`: what users say.
- `kind`: `measure` if the reading is something to look up; `group` if the reading defines a set of schools; `setting` for a rule the app applies when the user does not say (no year, no group, no number for "top"), the ranking guard, and which units may be summed.
- `reading`: the name of this reading. It is the text on the option button when the app asks.
- `shown_as`: the column heading in the result. Rows of one reading with the same heading are the same measure reported on different forms; a school has a value in only one.
- `measure`: the measure this row points to.
- `condition`: a filter on the measure. `EAPCAT = 21000` picks one category row. `< 25` keeps schools below a cut-off. For peers: `comparison group`, `same state and sector` or `user named`. For a group that mixes levels: `only this group` (keep the schools in `default_for`) or `split by level`.
- `is_default`: `yes` if this reading is used when the user does not say which.
- `default_for`: a school group. The default applies only to schools in that group. Blank means all schools.
- `applies_to`: for a reading that names one measure per kind of school, the school group each measure applies to (for example net price: `Public` uses the in-state measure, `Private, nonprofit or for-profit` the all-students one). Each school takes the measure that applies to it; a group with more than one kind is shown separately for each, with the "kind of school" statement.
- `always_ask`: `yes` if the app must ask the user to choose. `no` if it uses the default; when no default applies to the school, it asks. `mixed levels` marks the options offered only when a group mixes school levels.
- `statement`: what the app must say whenever this term is used.
- `status`: `in use`, or `pending owner approval` (loaded but not used).
- `note`: anything else.

## school_groups.csv

Every way a user can name a group of schools.

- `group`: the group's name. Rows with the same name must all hold (only the national universe uses this).
- `kind`: `column` (schools with these codes), `any value` (every value of the column is its own group, such as each state), `member list` (members are in `group_members.csv`), `per school` (depends on the school asked about, such as its comparison group), `has rows` (schools with at least one row in the named table), `has value` (schools with a value in the named column), `universe` (the national universe), `none` (no definition; see `status`).
- `words`: what users say.
- `table`, `column`: where the codes are. Several columns mean a match in any of them.
- `codes`: the codes that define the group, or `any`.
- `statement`: the definition the app states in "Interpreted as".
- `caveat`: a warning shown with the definition.
- `word_note`: a sentence explaining which words the group stands for ("State schools" means public four-year). Shown in "Definitions & sources", not in "Interpreted as".
- `status`: `in use` or `decline`.
- `priority`: 1 for the groups most likely to be asked.
- `note`: anything else.

## group_members.csv

Hand-kept member lists.

- `group`: the group name, as in `school_groups.csv`.
- `unitid`: the school's IPEDS ID.
- `name`: the school's name, for reading. The ID is what counts.

## school_nicknames.csv

Short names users type for a school.

- `nickname`: what the user types.
- `kind`: `direct` resolves to the school without asking. `alias` suggests the school first but still shows the picker when other schools match. `picker` only supplies a search phrase.
- `unitid`, `name`: the school, for `direct` and `alias`.
- `search_phrase`: the phrase searched for, for `picker`.

## rates.csv

The counts behind each rate, so a group rate is computed by summing counts, never by averaging school rates.

- `rate`: plain name of the rate.
- `rate_measure`: the ready-made rate column for one school.
- `numerator`, `denominator`: the count columns.
- `category_column`: for multi-row tables, the column that picks the rows.
- `numerator_code`, `denominator_code`: the row codes to use.
- `method`: how schools are combined. `sum of counts`: add the numerators, add the denominators, then divide (rates, and averages such as dollars per student). `weighted average`: the numerator is each school's own average and the denominator its count of students; the group figure is the sum of average times count, divided by the sum of counts (net price, where IPEDS gives no total).
- `applies_to`: the school group the counts apply to, when the rate is defined only for some schools. Rows that share a ready-made rate must each name one.
- `unit`: how the group figure is shown: `percent` (a share of counts, shown as a percent) or `dollars` (an amount per person or per FTE).
- `nces_figure`: the published national figure for 2024-25, used as a test.
- `status`: whether it has been tested.

## category_codes.csv

Every code in the category columns of the multi-row tables.

- `table`, `column`, `code`, `label`: the code and its IPEDS label.
- `synonyms`: other words users say for this row, separated by semicolons (for example `undergrad` on rows labelled undergraduate). Used only to find the row for the shortlist.
- `default`: `yes` on the one code used when a request does not name this column. Only columns that pick out the row take a default; columns that just describe the row (the occupation column in a table keyed by a combined staff category) take none. The build checks that the defaults pick exactly one row per school. A column with no default makes the app ask.
- `role`: `total` or `part`, guessed from the label wording. It is a reading aid only; breakdowns use the three columns below.
- `breakdown_set`: filled when this code is one part of a named breakdown, such as "Fall enrollment by level".
- `set_total`: the code of the row the parts add up to, or `sum of parts` when the data has no total row. The same on every row of the set.
- `statement`: a sentence shown whenever an answer uses this row, such as the staff grand total's note that it excludes graduate assistants.
- `set_fixed`: in tables keyed by several category columns, the default values the other columns are held at, such as `CIPCODE = 99; MAJORNUM = 1`. The same on every row of the set. A request may ask for another value (bachelor's degrees only, undergraduates only); the build tests the set at every value and allows only those that add up.

The build tests each set: at every school, do the parts add up to the total? A set is loaded only for the count columns where it does. The breakdown operation uses only loaded sets.

## year_meaning.csv

What the year means for each table. Every result must state this period.

- `table`, `year`: the table and the release year.
- `kind`: fall, fiscal year, academic year, cohort, or 12 months July to June.
- `period`: the period text shown to the user.
- `entering_cohort`: for graduation and outcome tables, the entering cohort as offsets from the release year, by school level where they differ: `fall -6 for Four or more years; fall -3 for At least 2 but less than 4 years`. Each level name is a school group. A measure's own `entering_cohort` wins.
- `title`: the IPEDS table title.
- `parent_child_flag`: the two `FLAGS` columns that say whether a school reports this survey together with a related campus, written `FLAGS.PRCH_EF; FLAGS.IDX_EF`. The first holds 1 (parent record, includes data from child campuses) or 2 (child record, data reported with the parent); the second holds the parent's ID. A summary-to-detailed link may differ only at such schools, and any answer that shows such a school says which campus it reports with (the "related campus" setting).
- `caveat`: a warning shown whenever figures from this table are given for a group of schools, such as optional-year reporting.

## outside_ipeds.csv

Topics users ask about that IPEDS does not hold.

- `topic`, `example_wording`: the topic and how users phrase it.
- `in_ipeds`: `No`, `Partly`, or `Not in this app`.
- `what_to_say`: the app's reply.
- `pointer`: where to send the user. Blank means no pointer is given.

## special_codes.csv

Which special codes become missing values.

- `applies_by`: `codebook label` (the rule applies wherever the codebook uses this code with this label) or `table and column` (the rule applies to one named column, for codes the codebook does not list).
- `table`, `column`: filled only for `table and column` rules.
- `code`: the code, such as -1 or -2.
- `label`: the codebook label, for `codebook label` rules.
- `decision`: `missing` or `keep`.
- `shown_as`: the reason shown to a user for a specific school. Display only; it never enters a calculation.
- `note`: anything else.
