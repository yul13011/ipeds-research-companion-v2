# The dictionary folder

This folder is the only home for conventions: what a word means, which counts sit behind a rate, which schools are in a group. No convention lives in code, in prompts or in any other file.

- Each table is a CSV you can open in Excel. One row is one fact.
- After any change, the build must be rerun. `python build/build_dictionary.py` reloads the tables (a few seconds) and stops with a list of problems if a row does not fit the data. A change to `special_codes.csv` needs the full build, `python build/build_data.py`.
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
- `priority`: 1 for ready-made and most-asked measures, then 2 and 3.
- `in_first_version`: `yes` or `no`. A `no` means "IPEDS collects it, but it is not set up in this app yet".
- `period`: filled only when the variable reports a different year from its table (net price for 2023-24 in a 2024-25 table). Blank means the table's period in `year_meaning.csv`.
- `plain_name`: your plain-English name. Blank means the IPEDS title is used.
- `synonyms`: other words users say for this measure.
- `breakdown_set`: filled when this column is one part of a breakdown stored as columns, such as "By race and ethnicity" or "By gender". All the columns of one table with the same name form the set.
- `set_total`: the column that the parts add up to, or `sum of parts` when the data has no total column. The build tests that the parts add up on every row; a set that fails is not loaded.

## terms.csv

Words with more than one possible reading. One row per reading and measure. A reading that shows several measures together (the cost profile) has one row per measure.

- `term`: the name of the term. All rows of one term share it.
- `words`: what users say.
- `kind`: `measure` if the reading is something to look up; `group` if the reading defines a set of schools.
- `reading`: the name of this reading. It is the text on the option button when the app asks.
- `shown_as`: the column heading in the result. Rows of one reading with the same heading are the same measure reported on different forms; a school has a value in only one.
- `measure`: the measure this row points to.
- `condition`: a filter on the measure. `EAPCAT = 21000` picks one category row. `< 25` keeps schools below a cut-off. For peers: `comparison group`, `same state and sector` or `user named`. For a group that mixes levels: `only this group` (keep the schools in `default_for`) or `split by level`.
- `is_default`: `yes` if this reading is used when the user does not say which.
- `default_for`: a school group. The default applies only to schools in that group. Blank means all schools.
- `always_ask`: `yes` if the app must ask the user to choose. `no` if it uses the default; when no default applies to the school, it asks. `mixed levels` marks the options offered only when a group mixes school levels.
- `statement`: what the app must say whenever this term is used.
- `status`: `in use`, or `pending owner approval` (loaded but not used).
- `note`: anything else.

## school_groups.csv

Every way a user can name a group of schools.

- `group`: the group's name. Rows with the same name must all hold (only the national universe uses this).
- `kind`: `column` (schools with these codes), `any value` (every value of the column is its own group, such as each state), `member list` (members are in `group_members.csv`), `per school` (depends on the school asked about, such as its comparison group), `has rows` (schools with at least one row in the named table), `universe` (the national universe), `none` (no definition; see `status`).
- `words`: what users say.
- `table`, `column`: where the codes are. Several columns mean a match in any of them.
- `codes`: the codes that define the group, or `any`.
- `statement`: the definition the app states in "Interpreted as".
- `caveat`: a warning shown with the definition.
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
- `nces_figure`: the published national figure for 2024-25, used as a test.
- `status`: whether it has been tested.

## category_codes.csv

Every code in the category columns of the multi-row tables.

- `table`, `column`, `code`, `label`: the code and its IPEDS label.
- `role`: `total` or `part`, guessed from the label wording. It is a reading aid only; breakdowns use the three columns below.
- `breakdown_set`: filled when this code is one part of a named breakdown, such as "Fall enrollment by level". A code can be in one set.
- `set_total`: the code of the row the parts add up to, or `sum of parts` when the data has no total row. The same on every row of the set.
- `set_fixed`: in tables keyed by several category columns, the values the other columns are held at, such as `CIPCODE = 99; MAJORNUM = 1`. The same on every row of the set.

The build tests each set: at every school, do the parts add up to the total? A set is loaded only for the count columns where it does. The breakdown operation uses only loaded sets.

## year_meaning.csv

What the year means for each table. Every result must state this period.

- `table`, `year`: the table and the release year.
- `kind`: fall, fiscal year, academic year, cohort, or 12 months July to June.
- `period`: the period text shown to the user.
- `title`: the IPEDS table title.

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
