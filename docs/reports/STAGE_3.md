# Stage 3 report: the question path

Nov 16, 2026

The question path is built: shortlist, one model call, resolve and check, fetch, show, and a chat page. All 117 tests pass, and none of them calls the API. No live model call has been made yet. That waits for you to set the API key, and the walkthrough is in the last section. Stage 3 work is not committed; the last commit is `fec863f`, before it.

## What was built

| Module | Step | Lines | What it does |
| --- | --- | ---: | --- |
| `path/request.py` | all | 143 | The structured request, the reply shape the model must follow, and how an edit changes the previous request |
| `path/shortlist.py` | 2 | 209 | Text search over the dictionary and directory. Code only |
| `path/interpret.py` | 3 | 135 | Builds the prompt, makes the one model call with structured output, retries once |
| `path/resolve.py` | 4 | 463 | Shortlist check, names to schools, every dictionary rule; returns a plan, a question, a picker or a decline |
| `path/fetch.py` | 5 | 318 | One query routine per operation |
| `path/show.py` | 6 | 100 | "Interpreted as", tables, warnings, definitions and sources |
| `path/log.py` | all | 27 | Local question log and decline log |
| `path/answer.py` | all | 105 | Runs the steps in order |
| `app.py` | page | 90 | The Streamlit chat page |
| `scripts/smoke_test.py` | | 41 | The live test, not run |

The question path is 1,500 lines; with the page, 1,590. That is longer than I hoped. `resolve.py` is the largest, because that is where every dictionary rule is applied.

### Your design changes

| Change | How it was done |
| --- | --- |
| Fewer operations | Ten: `schools` (lookup and compare), `group` (code decides sum or rate), `rank`, `list`, `breakdown`, `split`, `count_schools`, `school_vs_group`, `define`, `data_exists` |
| Units | A group figure sums only units named in the "summable units" setting; anything else needs a `rates.csv` row or is declined, with the per-school list offered |
| Shortlist only | Resolve rejects any measure, school, group, category row, breakdown set or reading the model was not shown, and logs it as a wrong reading |
| Edits change any field | add, remove and replace on list fields, replace on the rest, and "back". Tested: add a school, now for Texas, rank them, break that down by gender |
| Pending options | Shown to the next model call; a typed "the second one" is matched |
| Shortlist logged | Every log row holds the shortlist IDs |
| Structured output | The reply is held to the request shape by the API; an invalid reply is retried once, then a plain failure is shown and logged |
| No API in tests | Model replies are saved files (`tests/replies/`) or written in the test; the page is tested with Streamlit's test runner |

### The nine questions of the design note

Run through the whole path from saved replies, written the way the model should answer. Each figure is checked against a number the test computes from the data itself.

| Question | Result | Checked against |
| --- | --- | --- |
| a. Yale's admission rate | 4%, fall 2024; counts 2,227 of 57,517 | the IPEDS figure |
| b. Six-year rates at RIT, WPI, Drexel | 71%, 90%, 78% | the IPEDS figures |
| c. Public four-year in Texas, highest retention | UT Austin first; 37 of 67 ranked, 28 with no value, 2 under the 30-student guard | the guard and the note |
| d. Yale undergraduates by race | nine categories, total 6,814 | parts add up to the total |
| e. Graduation rate, public two-year | 36.7%, from 156,621 completers of 426,480; caveat on community colleges shown | counts summed then divided |
| f. Yale bachelor's degrees by field | each field with a total | the bachelor's total, all fields |
| g. Front Range against its peers | Front Range beside its 36-school comparison group, 68.6% | the comparison group |
| h. Data on AI policies | "IPEDS has no data on AI policies." No pointer, as the table names none | the dictionary row |
| i. "add Northeastern" after (b) | four schools | the edit |

Each takes under half a second once the model reply is in hand.

### What the model is shown

| Question | Words in the prompt |
| --- | ---: |
| add Northeastern | 756 |
| What was Yale's admission rate? | 1,073 |
| Do you have data on AI policies? | 1,413 |
| The other six | 1,780 to 1,900 |

The instructions are 440 words; the rest is the shortlist. That is more than the 1,400 I estimated, mostly because a matched term or breakdown set brings in its measures. It costs about a fifth of a cent per question on Sonnet and much less on Haiku. Stage 4 will report real token counts.

### Tests

117 in all, 31 seconds:

- **Stages 1 and 2:** 81 tests.
- **The question path:** 33 new tests. They cover request edits; the shortlist; the retry; the nine questions; and each rule:
  - wrong reading, logged with its shortlist;
  - school picker;
  - always-ask term with buttons, and a typed choice;
  - mixed levels asking, then splitting;
  - year outside the data, declined and logged;
  - an average with no rate row, declined;
  - average Pell grant ($5,300, matching NCES);
  - finance split by form;
  - a group total;
  - a declined group;
  - "yes" and "not set up yet" answers;
  - three edits;
  - a check that tests never touch the shared log.
- **The page:** 3 tests, driven by Streamlit's test runner.

## Changes made to the dictionary during Stage 3

All are recorded in `DECISIONS.md`. None changes a decision of yours; each was needed to apply one.

1. **The three per-FTE rows now share one name,** "Core expenses per FTE student", and differ by `applies_to`. One request then covers all three forms, and a mixed group splits by form automatically. The build now requires rows that share a name to say which schools each covers.
2. **The finance form groups are now "has a core-expenses value on that form".** Before, they were "has a row in that form's table". 16 public schools have GASB figures in the derived table but no GASB row, and the old definition gave $33,118 where the counts give $32,973.
3. **"Split by" sector, level or control** maps to the directory columns through three setting rows in `terms.csv`, so the column names are not in code.
4. **Rate rows marked "Pending"** (net price) are skipped until you approve them.

## Findings

1. **Front Range shows 100% retention, and it is real data.** It reports a full-time cohort of one student, who returned. 366 schools show 100% retention, most with small cohorts. The page shows the counts beside the rate, so the reader can see it; rankings already apply the 30-student guard. A comparison of one school with a group does not apply the guard. Should it?
2. **Some term statements are written as instructions, not as text for the user.** Examples: "State which graduation rate was used." and "State that the latest net price year is 2023-24." The app shows them as written, which reads oddly. I suggest rewriting them as sentences for the user, such as "Graduation rate: bachelor's degree within six years." That is a change order to `terms.csv`, about eight rows.
3. **Group statements that explain a word are always shown.** "Public, 4-year or above" carries 'State schools and public universities mean public four-year.' The app shows it whenever that group is used, even when the user said neither phrase. The code cannot tell which words the user used without reading their wording, which the rules forbid. Options: keep it, or move those sentences into the definition only.
4. **"Grand total" is a poor name.** The 20 main count columns added for breakdowns are titled "Grand total" in IPEDS, so "Interpreted as" reads "Grand total, All students, Undergraduate total for Yale University". Plain names for those 20 rows in `measures.csv` would fix it.
5. **Graduation rates state their period as "Status of student as of August 31, 2024".** That is the IPEDS period text. The entering cohort year (2018 for the six-year rate, 2021 for the two-year rate) is not in the dictionary. Your rule asks for the real period, so I suggest adding the cohort year to the graduation measures' `period` column.
6. **Bare "colleges" and "universities" (your decision B15).** I removed those words from the group words, so the search no longer points the model at a group for them. Nothing stops the model choosing "Four or more years" for "universities" on its own, and putting the rule in the prompt would put a convention outside the dictionary. Stage 4 will show whether it happens.
7. **Counting schools in a named group** does not intersect with the national universe. "How many public four-year institutions in Texas" counts every sector-1 school in the Texas directory rows, including schools outside Title IV. NCES-style counts use the universe. Which do you want?
8. **Staff salaries and the universe.** NCES's salary figure includes administrative offices, as reported before. The same note appears on its staff-count table. Neither is changed.

## Open questions

1. Should a school-against-group comparison apply the small-denominator guard to the school (finding 1)?
2. Rewrite the term statements as user-facing sentences (finding 2)?
3. Keep the word-explaining group statements, or move them to the definition (finding 3)?
4. Plain names for the 20 "Grand total" measures (finding 4)?
5. Add the cohort year to graduation measures' periods (finding 5)?
6. Counts of schools in a named group: intersect with the national universe or not (finding 7)?

## Next: the first live call

Before any live call I'll walk you through setting the key (below). Then, with your approval, the smoke test runs the nine questions live, about $0.02 on Sonnet, and prints what the model returned beside the saved reply. After that, Stage 4.
