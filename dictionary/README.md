# The dictionary folder

This folder is the only home for conventions: what a word means, which counts sit behind a rate, which schools are in a group. No convention lives in code, in prompts or in any other file.

- Each table is a CSV you can open in Excel. One row is one fact.
- After any change, the build must be rerun. `python build/build_dictionary.py` reruns only what the change affects and stops with a list of problems if a row does not fit the data: a wording change takes seconds, a measure or a table's category rows a few minutes. `python build/build_dictionary.py --table terms` reloads one table on its own; `python build/build_dictionary.py --full` reruns everything (about 30 minutes; required before each part's final report and for every yearly update). A change to `special_codes.csv` needs the full data build, `python build/build_data.py`.
- Every owner decision gets one dated line in `DECISIONS.md`.
- Table names are the local names without the year (`HD`, not `HD2024`). A measure is written `TABLE.VARIABLE`, for example `DRVGR.GBA6RTT`.
- Two columns hold short lists in one cell: `words` (separated by semicolons) and `codes` (separated by commas).

## DECISIONS.md

One dated line per owner decision, with its reason.

## measures.csv

One row per IPEDS variable in any of the ten releases: the 2,599 of the 2024-25 release, and 474 that appear only in earlier releases (retired variables, marked not set up, with the title and description from the last release they appeared in).

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
- `period`: filled only when the variable reports a different year from its table (net price for 2023-24 in a 2024-25 table), written with the year words described under `year_meaning.csv`. Blank means the table's period in `year_meaning.csv`.
- `plain_name`: your plain-English name. Blank means the IPEDS title is used.
- `synonyms`: other words users say for this measure.
- `statement`: a sentence shown whenever an answer uses this measure, such as the note that IPEDS counts first-time students, not first-year students.
- `detailed_measure`: for a summary measure, the same figure in a detailed table, written `TABLE.COLUMN where COLUMN = code; ...`, for example `EFA.EFTOTLT where EFALEVEL = 2` for undergraduate enrollment. When a breakdown is asked for on the summary measure, the app uses the detailed one and says so. The build checks that the two agree at every school and lists the schools where they do not (schools that report together with a related campus).
- `breakdown_set`: filled when this column is one part of a breakdown stored as columns, such as "By race and ethnicity" or "By gender". All the columns of one table with the same name form the set.
- `years_available`: for a retired variable, the releases it appeared in. The build works out every measure's years from the data (table `measure_years`); this column is for reading.
- `set_total`: the column that the parts add up to, or `sum of parts` when the data has no total column. The build tests that the parts add up on every row; a set that fails is not loaded.
- `own_column`: for a column that is one year of a figure held for several years in the same table (net price for this year and the two before, tuition for four years), the release's own column for that figure, `TABLE.VARIABLE`; the own column names itself. Blank for every other measure. A trend reads each release's own column; the other columns supply only the years no loaded release's own column covers, labelled with the release they came from (owner decision 2026-11-25).
- `years_back`: how many years before the own column's period this column's period starts; 0 for the own column.
- `note`: anything about the row for the owner, never shown to users (for example a codebook title error).

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
- `statement_when`: for a term's statement, `always` (shown whenever one of its measures appears, for example the net-price lag) or `chosen` (shown only when the model chose this term's reading, for example "low-income").
- `always_ask`: `yes` if the app must ask the user to choose. `no` if it uses the default; when no default applies to the school, it asks. `mixed levels` marks the options offered only when a group mixes school levels.
- `statement`: what the app must say whenever this term is used.
- `status`: `in use`, or `pending owner approval` (loaded but not used).
- `note`: anything else.

## school_groups.csv

Every way a user can name a group of schools.

- `group`: the group's name. Rows with the same name must all hold (only the national universe uses this).
- `kind`: `column` (schools with these codes), `any value` (every value of the column is its own group, such as each state), `member list` (members are in `group_members.csv`), `per school` (depends on the school asked about, such as its comparison group), `has rows` (schools with at least one row in the named table), `has value` (schools with a value in the named column), `universe` (the national universe), `none` (no definition; see `status`), `synonyms` (more words for a group made from a column's values, such as "CUNY" for "System: City University of New York": `group` is that group's full name and `words` the words; the build stops if the group does not exist).
- `words`: what users say.
- `table`, `column`: where the codes are. Several columns mean a match in any of them.
- `codes`: the codes that define the group, or `any`.
- `statement`: the definition the app states in "Interpreted as".
- `caveat`: a warning shown with the definition.
- `word_note`: a sentence explaining which words the group stands for ("State schools" means public four-year). Shown in "Definitions & sources", not in "Interpreted as".
- `membership`: blank means each year's own list of schools. `as of latest year` means the latest year's list is used for every year (the Carnegie groups, whose classification exists only in recent releases), and the answer says so.
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
- `kind` `system or school`: a name that can mean a system or one of its schools ("unc"). `unitid` and `name` are the school, `search_phrase` the system group's full name. Both go on the shortlist and the app asks which, unless the question names the school in full (its own words beyond the system's name, such as "chapel hill").
- `kind` `ambiguous`: an abbreviation several schools share ("bu", "u of m"). `search_phrase` lists their names, separated by semicolons. A school written as this abbreviation always goes to the school picker, which offers those names; it is never replaced by one of them silently.

## word_abbreviations.csv

Abbreviated words people use in school names. The school search adds every meaning beside the word itself, so "wayne st" also searches "wayne state" and "wayne saint"; the school picker or the model chooses.

- `abbreviation`: the short word, as typed (without a full stop).
- `means`: one meaning; an abbreviation with several meanings has one row for each.

## rates.csv

The counts behind each rate, so a group rate is computed by summing counts, never by averaging school rates.

- `rate`: plain name of the rate.
- `rate_measure`: the ready-made rate column for one school.
- `numerator`, `denominator`: the count columns.
- `category_column`: for multi-row tables, the column that picks the rows.
- `numerator_code`, `denominator_code`: the row codes to use.
- `method`: how schools are combined. `sum of counts`: add the numerators, add the denominators, then divide (rates, and averages such as dollars per student). `weighted average`: the numerator is each school's own average and the denominator its count of students; the group figure is the sum of average times count, divided by the sum of counts (net price, where IPEDS gives no total).
- `applies_to`: the school group the counts apply to, when the rate is defined only for some schools. Rows that share a ready-made rate must each name one.
- `synonyms`: for a rate with no ready-made measure, other words users say for it (used to find it for the shortlist).
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
- `years`: the release years the row applies to, such as `2015-2019` or `2020-2024`. Blank means every year. A code that IPEDS changed has one row for each span (award levels before and after 2020-21; 12-month enrollment levels, keyed by `EFFYLEV` before 2020-21). Each year's tests use only the rows for that year, and the app answers from the rows for the latest year.
- `same_as`: for a row of an earlier year that holds the same information under another column or code, the latest year's row it stands for, written `COLUMN = code` (12-month enrollment `EFFYLEV 4`, Graduate, is `EFFYALEV = 12`). A summary-to-detailed link or a request that names the latest year's row is read through it in that year. Where both columns are filled in the same year, the build checks that they pick the same rows. A year with no such row does not hold the information, and its breakdown is not offered for that year.
- `sum_of`: for a row standing for a total that IPEDS did not report as a row in those years, the codes it adds up, such as `1, 2, 3, 4` (the Outcome Measures total entering cohort in 2015-16 and 2016-17, the sum of the four cohorts). Those codes must have rows for the same years.

The build tests each set: at every school, do the parts add up to the total? A set is loaded only for the count columns where it does. The breakdown operation uses only loaded sets.

## year_meaning.csv

What the year means for each table. Every result must state this period.

- `table`, `years`: the table and the release years the row applies to (`2015-2024`). One row per table.
- `kind`: fall, fiscal year, academic year, cohort, or 12 months July to June.
- `period`: the period text shown to the user, written with year words counted from the release year: `{Y}` is the release year (2024 for the 2024-25 release), `{Y-1}` and `{Y+1}` count from it, and `{Y:yy}` gives the last two digits. `July 1, {Y-1} - June 30, {Y}` reads "July 1, 2023 - June 30, 2024" for the 2024-25 release.
- `entering_cohort`: for graduation and outcome tables, the entering cohort as offsets from the release year, by school level where they differ: `fall -6 for Four or more years; fall -3 for At least 2 but less than 4 years`. Each level name is a school group. A measure's own `entering_cohort` wins.
- `title`: the IPEDS table title.
- `parent_child_flag`: the two `FLAGS` columns that say whether a school reports this survey together with a related campus, written `FLAGS.PRCH_EF; FLAGS.IDX_EF`. The first holds 1 (parent record, includes data from child campuses) or 2 (child record, data reported with the parent); the second holds the parent's ID. A summary-to-detailed link may differ only at such schools, and any answer that shows such a school says which campus it reports with (the "related campus" setting).
- `caveat`: a warning shown whenever figures from this table are given for a group of schools, such as optional-year reporting.
- `subject`: a short name for the table, drafted from IPEDS's own table title ("Fall enrollment", "12-month headcount"). Wherever two or more measures share a name, the name shown becomes "subject: title". Approved and applied (2026-11-23). The build writes the name an answer shows into `shown_name`: the official IPEDS title (or one of the plain names kept for the "Grand total" measures), with the subject added only where the name is shared. Names still shared after that are listed by the build (`name_clashes`).

## measure_history.csv

Where a 2024-25 measure was stored before the 2024-25 reorganisation of the cost and aid tables, so a trend reads the same figure from the earlier tables. Each year's figure comes from the release in which it is the current year.

- `measure`: the 2024-25 measure, as in `measures.csv`.
- `earlier_table`, `earlier_variable`: where the same figure is stored in earlier releases (same name and title once the years are taken out).
- `years`: the releases that hold it there.
- `how`: how the match was made.
- `status`: `in use`, `to review` (a possible successor waiting for the owner's decision; not used), or `rejected` (the owner decided it is not a successor; the retired variable's message says it is no longer collected).

The same file links a retired variable to its successor: a 2024-25 measure that first appears in the release after the retired variable last appeared, with the same meaning under a new name or table. The full list, with uncertain matches, is `docs/reports/stage5b/successors.csv`.

Measures with no row have no earlier years. The years each measure has values are worked out from the data by the build (table `measure_years`), not written here.

## comparability_breaks.csv

Years in which IPEDS changed a definition, or that need a note in a trend. Shown when a trend's period crosses `first_release` (or falls within `first_release` to `last_release`). The data is never hidden.

- `kind`: `definition change` or `context` (a note where no definition changed).
- `tables`: the tables the row applies to. Blank means every table (used with a period).
- `applies_to`: what the note is about, in plain words.
- `first_release`, `last_release`: the release years, such as `2020-21`. `last_release` is blank for a lasting change.
- `period_from`, `period_to`: instead of releases, the months a figure's period must overlap for the note to show (`2020-03` to `2022-06` for the pandemic note). A row needs releases or a period.
- `what_changed`: the change, for review.
- `note_shown`: the sentence shown with the trend.
- `source`: where the change is documented.
- `status`: `draft` (not shown) or `approved`.

## breakdown_exceptions.csv

Schools whose parts do not add up to their total in one year, which the owner has approved as exceptions so the breakdown can still be offered. The set is tested without them; for these schools only the total is shown, with a note.

- `breakdown_set`, `table`: the breakdown.
- `year`: the release year.
- `unitid`, `name`: the school.
- `note`: why, and the owner's decision.

## outside_ipeds.csv

Topics users ask about that IPEDS does not hold.

- `topic`, `example_wording`: the topic and how users phrase it.
- `in_ipeds`: `No`, `Partly`, or `Not in this app`.
- `what_to_say`: the app's reply.
- `pointer`: where to send the user. Blank means no pointer is given.

- `instead`: an alternative the decline offers, such as "the same figure for the years this app holds" for years outside the ten releases; blank for none.
- `checked_by_code`: `years` for the row about years outside the ten releases. The app's code alone decides whether the years asked for are held (owner decision, 2026-11-25), so this row is never shown to the model; the code's own "years" message adds its pointer. Blank for every other row.

## glossary.csv

The official IPEDS glossary, edition 2025-26, one row per entry, read from `docs/sources/ipeds_glossary_2025-26.pdf` by `scripts/parse_glossary.py`. The definitions are NCES's wording and are never edited; a term the reading got wrong is corrected in `docs/sources/glossary_corrections.csv` and the script is run again. Used only when a user asks what a word means, and always cited with its edition; for a given year's data, that year's codebook (the measure's own description) comes first.

- `term`, `definition`: as printed.
- `edition`: the glossary edition, `2025-26`.
- `historical`: `yes` for entries that describe an older classification (the Carnegie 2000 and 2005 entries). They are never shown as the definition of the app's own groups.
- `note`: anything about the reading, such as a stray character printed in the definition.

## concepts.csv

Reviewed plain-English explanations of the ideas users ask about ("what is an adjusted cohort?"). The first source for a "what does X mean" question.

- `concept`: the idea's name.
- `words`: the words people use for it, separated by semicolons.
- `explanation`: the plain-English explanation shown to the user.
- `source`: where the explanation comes from (glossary entries, the IPEDS overview, the app's own tables).
- `app_convention`: the app's own rule that goes with it, shown after the explanation; blank for none.
- `own_wording`: `yes` where the explanation is the app's own wording rather than IPEDS documentation (approved by the owner).

## special_codes.csv

Which special codes become missing values.

- `applies_by`: `codebook label` (the rule applies wherever the codebook uses this code with this label) or `table and column` (the rule applies to one named column, for codes the codebook does not list).
- `table`, `column`: filled only for `table and column` rules.
- `code`: the code, such as -1 or -2.
- `label`: the codebook label, for `codebook label` rules.
- `decision`: `missing` or `keep`.
- `shown_as`: the reason shown to a user for a specific school. Display only; it never enters a calculation.
- `note`: anything else.
