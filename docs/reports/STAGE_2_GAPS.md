# Stage 2, before loading the workbook: cleaning results and gap list

Nov 15, 2026

The three build fixes you asked for are done and tested. The workbook has not been loaded. This report has two parts: what the cleaning found, and the decisions I need before Stage 2 can go on. Nothing is committed.

## Part 1. What was done

### Numbers stored as text

- **Rule:** the codebook's `DataType` field. A column the codebook marks `N` that the source stored as text is now stored as a number.
- **Found:** 42 columns, in six tables: staff full-time equivalents (19 in `DRVHR`), library full-time equivalents (5 in `DRVAL`), eight-year outcome percentages (5 in `OM`), nine non-credit flags and the disability percentage (10 in `IC`), latitude and longitude (2 in `HD`), and one finance flag (`FLAGS`).
- **Result:** every value converted. Zero failures.
- **After the fix,** every one of the 2,557 codebook-numeric columns is stored as a number.
- **Text columns the codebook marks `A` stay text,** including codes that look numeric, such as CIP codes, OPE IDs and EINs.

### Padded text

- **Rule:** every text value is trimmed. A cell that is empty or only spaces becomes missing.
- **Found:** 176,771 cells had padding removed, and 20,017 blank cells became missing. Examples: school names in the comparison-group table were padded to 255 characters; blank web addresses and alias fields in the directory held a single space.

### Special codes

- **Rule:** a value becomes missing only when both things are true. The codebook's value labels list that code for that column, and the label is on a short approved list, `build/special_code_labels.csv`. The list has 17 labels, which is every negative code label in the 2024-25 codebook.
- **A negative number in a column with no listed code is left alone.** Negative net prices and negative finance amounts are real values and are unchanged; a test checks this.
- **Set to missing:** 481,813 cells in 273 columns across ten tables.

| Code | Codebook label | Columns | Cells |
| --- | --- | ---: | ---: |
| -2 | Not applicable | 250 | 480,404 |
| -1 | Not reported | 182 | 1,072 |
| -3 | {Not available} | 8 | 160 |
| -2 | not applicable | 1 | 107 |
| -2 | Not reported | 1 | 70 |

- **Left as they are, awaiting your decision:** 326,154 cells in 35 columns. These are the unclear cases, listed in Part 2, section A.

### What the build now records

Three small tables in the local database keep an audit trail, so nothing changes silently:

- `_columns`: for each of the 2,710 columns, how it was stored before and after, and how many cells were trimmed, blanked, set to missing, or failed to convert.
- `_special_codes`: every special code the codebook lists for a column, its label, whether it was set to missing or kept, and how many cells held it.
- `_conversion_failures`: any value that should be a number and is not. Such a value is kept as text in place and listed here. It is empty for 2024-25.

### Question file

- `docs/question_log.csv` is now in `.gitignore`.
- `docs/test_questions.csv` is the cleaned copy to track: one column, 74 distinct questions from the 107 log rows, in first-seen order, with no session IDs, timestamps or other fields.

### Tests

23 tests, all passing, in 28 seconds.

| Your requirement | Test |
| --- | --- |
| Every converted column keeps the same non-missing count and total as the source | `test_converted_columns_hold_only_numbers`, on all 42 columns |
| A value that fails to convert is reported, not dropped | `test_value_that_will_not_convert_is_reported_not_dropped`, on made-up data with a bad value |
| Nothing else is lost | `test_nothing_is_lost_without_a_recorded_reason`: for every column, source values = loaded values + blanks + special codes |
| Every column still matches the source | `test_every_column_matches_the_cleaned_source`: count and total for all 2,710 columns, recomputed from the source |
| Padding is gone | `test_no_padded_or_blank_text_remains` |
| Approved codes are gone; real negatives remain | `test_approved_special_codes_are_gone_and_real_negatives_remain` |

Line counts: `build/build_data.py` 279, `config.py` 18, `tests/test_build_data.py` 304. The build now takes about 100 seconds, up from 15, because it counts every column before and after.

## Part 2. Decisions needed

My recommendation is given for each, but I have not acted on any of them.

### A. Special codes that are unclear

| # | What | Where | Cells | Recommendation |
| --- | --- | --- | ---: | --- |
| A1 | -2 "Not classified", "No research designation", "Not in Carnegie universe" | 9 Carnegie columns in the directory | 26,933 | Keep as a real category. "Schools with no research designation" is a valid group, and 5,530 schools are in it |
| A2 | -9 "Not active" | 23 survey response-status columns in `FLAGS` | 1,716 | Keep. It is a status value, and the 78 inactive schools should be identifiable |
| A3 | -2 used as a row label: "Not applicable, undergraduate detail" and "does not map to occupations prior to 2012" | Category columns in `EFFY`, `S_OC`, `S_NH` | 297,505 | Keep. These describe which kind of row it is; they are not a missing measurement. Your "Category codes" tab already lists two of them as "missing or not applicable" |
| A4 | -1 and -2 in text columns where the codebook lists no codes | `HD`: system name (-2 in 3,744 schools, -1 in 36), date closed (-2 in 6,004), OPE ID (-2 in 37), EIN (-1 in 78) | 9,899 | Set to missing. The system name matters for "SUNY schools": -2 there means "not in a system". This needs a second small approved list keyed by column, because the codebook has no label to use as the rule |
| A5 | -2 in numeric columns where the codebook lists no codes | `COST1.PRGMOFR` number of programs (3,780 schools); `HD.NEWID`; 12 parent-institution ID columns in `FLAGS` | about 80,000 | Set to missing, on the same column-keyed list as A4 |
| A6 | Small negative values in two cohort-exclusion columns | `GR200.BAAEXCL` (-1, -2, -3, -6, -758), `GR200.L4AEXCL` (-1) | 14 | Leave. They look like real downward adjustments, not codes. Please confirm |

Two further points about how missing values behave:

- **A7. The reason is not kept per school.** Once -1 or -2 becomes missing, the database knows how many cells in a column were "not reported" versus "not applicable", but not which school had which. If you want the app to say "not applicable" for a specific school (for example, an open-admission school asked about test-score policy), I would need to keep that per cell. Do you want that?
- **A8. Code 0 "Implied no"** appears in 89 yes/no columns. I have left it as 0, meaning "no". Please confirm it should read as "no" and not as missing.

### B. School groups with no draft to accept

| # | Words | What the workbook says | What I need |
| --- | --- | --- | --- |
| B1 | The Northeast, the Midwest, the South, the West | "PROPOSED" combinations of BEA regions, "please decide" | Accept the BEA combinations, or give Census regions by state |
| B2 | "The South" | Listed twice: with the Southeast alone (1,502 schools), and with Southeast plus Southwest (2,158) | Which one |
| B3 | "Private" alone | Listed under private nonprofit; note says "please decide the default" | Nonprofit only, nonprofit plus for-profit, or ask |
| B4 | "State schools" | Listed under public, and also on its own row as ambiguous | All public, public four-year only, or ask |
| B5 | "Small" and "large" | Drafted as 1,000 to 4,999 and 10,000 to 19,999; note says "please decide" | Accept, or your cut-offs. "Big universities" is drafted as 20,000 and above |
| B6 | Liberal arts colleges | Carnegie 2021 "Baccalaureate Colleges: Arts & Sciences Focus" (219 schools), "please decide" | Accept or give another rule |
| B7 | Community colleges | Public two-year (838). The note warns this misses community colleges that now award bachelor's degrees | Accept sector 4, or another rule |
| B8 | R1 and R2 | Two definitions: Carnegie 2025 research designation (187 R1) and Carnegie 2021 basic (146 R1) | I assume 2025 is the default and 2021 is used only when the user says so. Confirm |
| B9 | Hispanic-serving institutions | No flag. Could be derived (at least 25% Hispanic undergraduate FTE) or taken from a federal list | A rule, a list, or decline for now |
| B10 | Other minority-serving institutions | Not in the directory | A list, or decline for now |
| B11 | Women's colleges | Not flagged; needs a hand-kept list | A list, or decline for now |
| B12 | Flagship universities | Not flagged. Version 1 has a list of 53 (see below) | Approve, edit or drop the list |
| B13 | Selective, highly selective, elite | Not a category; could be an admission-rate cut-off | Cut-offs, or have the app ask |
| B14 | AAU, other named associations | Not in IPEDS | Lists for the ones you want, or decline for now |
| B15 | Colleges versus universities | Not an IPEDS distinction | Ask the user, or a rule |
| B16 | Athletic conference | Football conference only. Conferences without football (the Big East, for example) are in three other columns | Match on football only, or on any of the four conference columns |
| B17 | Religious affiliation | Six of 63 affiliations are shown | I plan to load all 63 from the codebook labels. Say if you want only the six |

**Version 1's flagship list (B12).** 53 schools: one per state, with these exceptions noted in the version 1 code. New York has both the University at Buffalo and Stony Brook. Indiana has both IU Bloomington and Purdue. Texas has both UT Austin and Texas A&M. Second land-grant flagships such as Colorado State and Montana State are left out as debatable. I can print the 53 names from the directory for you to mark up if that helps.

### C. Other tabs

| # | Tab | Gap | What I need |
| --- | --- | --- | --- |
| C1 | Year meaning | `SAL2024_IS` and `SAL2024_NIS` are marked "needs review". Their period text is "Academic year 2024-25" | Confirm "academic year" |
| C2 | Terms and defaults | "Faculty" is set to ask, between instructional staff headcount and all staff with faculty status. The tab names the tables but not the exact rows and columns for each count | The exact definition of each option, or permission to take them from version 1's Yale faculty check and show you the result |
| C3 | Rates and counts | "Award within eight years" names the counts but not which Outcome Measures cohort row is the total | Which cohort row |
| C4 | Outside IPEDS | "Faculty salary by academic field" says "No federal source; please advise" | A source, or no pointer |
| C5 | Outside IPEDS | "Enrollment by major" says "use degrees awarded by program as the nearest measure; please confirm" | Confirm |
| C6 | Measures | 737 measures are priority 1; only 19 have draft synonyms | I plan to use the IPEDS title as the plain name for the rest. Confirm |
| C7 | Measures | Blank in "Include in first version?" means yes for priority 1 | I read this as: the 1,862 priority 2 and 3 variables are "IPEDS collects it, but it is not set up in this app yet". Confirm |

### D. Things I will check myself and report, not guess

These need no decision now. I list them so you know they are coming.

- **Category codes.** The 1,078 total-or-part roles were guessed from label wording. I will test each against the data (do the parts add up to the total?) and report every mismatch.
- **Rates and counts.** Six of the twelve rates are marked "not re-tested". I will compute each from its counts and compare with the NCES figure in the tab.
- **Columns the codebook does not list.** Four columns in the comparison-group table (`CGCITY`, `SECTOR`, `CYACTIVE`, `MATCH`) have no codebook entry, so they keep the type the source gave them.

### E. One question about the test file

`docs/test_questions.csv` holds only question text, as you asked. That removes the link between a follow-up and the question it followed: "yes please", "both" and "confirm 151786" are now standalone rows. For Stage 4 I can either score those as follow-ups with no context, or add a plain conversation number and turn order (1, 2, 3; no session IDs or times) so they can be replayed in order. Which do you prefer?

## Carried over from version 1 without needing a decision

- **Named groups:** Ivy League (8 schools), Ivy Plus (the eight plus MIT, Stanford, Johns Hopkins and Chicago), Seven Sisters (6 schools). Member lists only; version 1's wording patterns are not carried over.
- **Nicknames:** 22 entries. Seven resolve directly (Yale, Harvard, Princeton, Dartmouth, UPenn, MIT, UCLA); five are aliases (Brown, Columbia, Penn, University of Pennsylvania, Cornell); ten only seed the school picker (UMich, UConn, Cal, Georgia Tech and others).
