# Stage 5, part 5f: explaining terms and concepts

Date: 2026-11-24. Your decisions on the Part 5f review points are in `dictionary/DECISIONS.md` ("Part 5f review approved, with fixes"); what was built is recorded under "Part 5f built"; your decisions on the first version of this report are under "Part 5f decisions" and are applied. Committed locally; not pushed.

## 1. The net price period (you asked for this before any change)

**What the codebook says.** VARTABLE titles in all ten releases: the net price variables in release Y are titled for the academic year before it.
- NPIST2 and NPGRN2 (students awarded grant or scholarship aid): release 2015 says "2014-15", and so on to release 2024, which says "2023-24".
- NPGRN1 is the year before that (2024 release: 2022-23), and NPGRN0 two years before (2021-22).
- NPIS42 and NPT42 (all students awarded federal aid, 2024 release only): 2023-24.
- The SFA titles (UPGRNTP, PGRNT_P) carry no year.

**What the four places say.**

| Place | Says | Agrees with the codebook? |
| --- | --- | --- |
| measures.csv, each net price measure's own period | NPIST2 and NPGRN2 `{Y-1}-{Y:yy}`; NPGRN1 `{Y-2}-{Y-1:yy}`; NPGRN0 `{Y-3}-{Y-2:yy}` | Yes |
| terms.csv statement | "Net price is reported one year behind the rest of the release" | Yes |
| year_meaning.csv, table COST2_NETPRICE | `Academic year {Y}-{Y+1:yy}` (the release year itself) | **No** |
| Concept "Why net price is a year behind" | the 2024-25 release reports 2023-24 | Yes |
| Concept "Release year and data year" (draft) | net price "for the year before that" (two years behind) | **No** (fixed: see below) |

**What the app shows.** Every answer shows the measure's own period, which is right: all 54 net price measures have one, so the table-level period in year_meaning.csv never reaches an answer. It does reach the shortlist the model sees, as the table's period.

**Done:** the "Release year and data year" concept now says completions, finance and net price are all for the year before (2023-24 in the 2024-25 release). **Your decision 1, done:** year_meaning.csv now gives COST2_NETPRICE the period `Academic year {Y-1}-{Y:yy}`, so all four places agree with the codebook.

## 2. The glossary

**612 entries**, edition 2025-26, in `dictionary/glossary.csv` (term, definition, edition, historical, note).

**How the fixes are made.** `scripts/parse_glossary.py` now works in two steps:
1. The first reading of the PDF gives the list of terms.
2. `docs/sources/glossary_corrections.csv` corrects the terms that reading got wrong. Then every definition is cut out of the PDF's own text, from the end of one term to the start of the next.

So no definition is typed by hand, and a corrected term automatically gives its neighbours back the text they had lost (for example, "Associate's Colleges" is no longer stuck to the end of the definition of Assets).

**Corrections: 26.**
- **Your 14,** with your wording of the Carnegie terms, "Postsecondary education institution", and the 14th, "Postsecondary education".
- **12 more,** found by searching all 612 entries for the same two faults:
  - 8 entries where the term's last word started its definition, all with "education": Adult basic, Continuing, Continuing professional, Developmental, Distance, Institution of higher, Noncredit and Noncredit workforce education.
  - 4 where the definition's first word or line ended up in the term: Race and ethnicity unknown, Trimester (calendar system), and both Operation and maintenance of plant entries.
- **A third fault the sample found:** a word broken at a line end after its hyphen was joined with a space ("for- profit", "electronic- announcements"). This is now fixed for every entry. It changed 28 definitions and some terms ("300-899 clock hours"), and only in that way: I checked that removing the spaces gives back the earlier text.
- **One change from the review draft:** "3/2 program" ends with a stray "22". The first parse took it to be a page number and removed it, but it is printed inside the definition's cell on page 1. It is now kept as printed, with a note.

**The 60-entry check against the PDF.**
- **First sample (60 random entries):**
  - 2 were wrong, both from the hyphen fault: "Private institution" ("for- profit") and "Semester (calendar system)" (a split web address).
  - After the fix, all 60 are right.
  - How they were checked: 44 against the PDF's printed two-column layout. The other 16 sit on pages where that layout text is scrambled, so I checked them on the page images in the browser (for example Basic Principles for Income Tax Accounting, Faculty Status, Hispanic/Latino and Unique Entity Identifier).
  - The term and the start and end of each definition were compared, since every fault found so far sat at those boundaries.
- **Second sample (60 different entries, after all fixes):**
  - 0 wrong.
  - 44 matched the printed layout automatically. The other 16 were read against the PDF's text, term by term, and 2 of them also on the page images.
- **How far to trust this:** the checks found every fault at a term boundary, and the pattern searches now come back empty. A fault inside a definition's middle (a dropped line) would not be caught by these checks. I saw none in the 120 entries read.

**Historical Carnegie entries:** the 27 entries with "Carnegie" in the term (the 2000 classes, the 2005 classifications, and "Carnegie Classification" itself) are marked `historical = yes`. They are never put on the shortlist, so the app can't show them as the meaning of its own Carnegie groups. A test checks this.

## 3. The concepts table

**26 concepts**, in `dictionary/concepts.csv` (concept, words, explanation, source, app_convention, own_wording). Your wording and source fixes are in. Two things went beyond them:
- **Carnegie:** the draft said the app uses the 2021 basic classification. That is wrong: R1 and R2 use the 2025 research designation (your decision B8), and the groups also include the 2025 institutional classification. The concept now says the 2024-25 release carries both editions, that R1 and R2 mean the 2025 designations, and that each group names its classification.
- **Imputation:** the app's present rule is that imputed figures are included, as IPEDS publishes them, and they are not labelled. The concept states that rule. If you want imputed figures labelled for a school, that is a new feature (the FLAGS imputation columns exist); I can write a proposal.

Six rows are marked `own_wording = yes`: retention versus persistence (the persistence part), provisional and final data, parent and child reporting, degree-granting, summer melt, and College Scorecard.

## 4. Finance check list

Your decisions applied, and 64 rows added to terms.csv. **Your later decisions (item 3), done:** F1C086 is paired for "O&M - O&M" and F1C083 for "O&M benefits"; F1C19OM joins "Total expenses - O&M"; the F2E111 + F3E111 pair is removed, and those two measures now say the cost is spread to the other functions, so the line is zero. The held items below are kept as the record of why.

- **Similarity 1.0, approved (item 8):**
  - 32 lines that complete approved pairs.
  - 9 new pairs: the financial-health total expenses; independent operations O&M; land, buildings and equipment; private gifts, grants and contracts; hospital revenue; total revenues and investment return; and local government grants to students.
- **Rejected or not paired, as you said:** Independent operations; Other revenues and additions; other expenses benefits (F1M05); O&M benefits (F1C086); private funded institutional grants with for-profit institutional grants; public operating grants with private total grants.
- **Re-paired (item 9):**
  - "Other expenses - all other" is now F1C145 + F2E127 + F3E067.
  - "Total expenses - all other" is a new pair: F1C195 + F2E137 + F3E077.
  - The amounts show each line is the sum of its form's function rows (it holds for 1,937, 1,884 and 2,825 schools respectively).
- **Below 1.0, the amount check (item 11).** In each form I tested which total the line adds up to, school by school:

| Row | Lines | Result |
| --- | --- | --- |
| Other expenses: O&M, salaries, depreciation, interest | F1C146, F1C142, F1C144, F1C147 with the private and for-profit lines | **Paired.** Each is a column of the other-expenses row; the row adds up in all three forms for every school (2015) |
| Discounts and allowances applied to tuition and fees | F2C08 joins F1E08 and F3C06 | **Paired.** In each form it is the tuition part of the total (F1E10, F2C10, F3C08), for every school bar one |
| Allowances applied to auxiliary enterprise revenues | F2C09 + F3C07 | **Paired.** The auxiliary part of the same totals |
| Total expenses - O&M (natural classification) | F1C196 + F2E134 | **Paired.** Both are the O&M column total. F1C196 exists only in 2015; from 2016 the public line is F1C19OM, which is not on the check list (you may want it added) |
| O&M total amount | F1C19OM with F2E111 and F3E111 | **Not paired. For you.** F1C19OM is the O&M column total. F2E111 and F3E111 are the O&M function row's total, which is zero for every school (the cost is spread to the other functions) |
| Public grants | F1B02, F1B03, F1B04A, F1B04B with the private totals | **Not paired** (your item 10). The public line is operating grants only; the private line is all grants. If you want them paired with a note, say so |

- **One approved 1.0 row held back, for you.** "O&M - O&M" would add F1C081 to the pair F2E114 + F3E114.
  - The amounts show F1C081 is the public O&M row's total, which is zero for every school.
  - F2E114 and F3E114 are the O&M allocated out, negative for most schools.
  - The public line that plays that part is F1C086, which is also negative for every school that reports it.
  - So the right pairing is probably F1C086 here, and F1C083 (benefits) for the O&M benefits pair you rejected. Your call; neither is paired.
- **Also for you:** the private and for-profit "O&M - total amount" pair you approved in Part 5e (F2E111, F3E111) is zero for every school, for the reason above. It does no harm, but it never shows a figure.

All of the O&M function-row lines and most of the other-expenses columns exist in the 2015-16 release only.

## 5. The dictionary's statements against the glossary

The list is in `docs/reports/stage5f/statement_check.csv`. 64 statements share words with a glossary entry; I read each pair.

- **One contradiction (your decision 2, done: the statement now reads as you worded it).** The terms.csv statement for "low-income" said "IPEDS does not measure income". The glossary defines family income (used for the Student Aid Index), and IPEDS reports net price by family income for students awarded federal aid.
  - Proposed: "IPEDS reports family income only for students awarded federal aid (net price by income); for all students, the Pell share is the usual proxy."
  - Not changed: it is a convention, for you.
- **The net price period** in year_meaning.csv (section 1).
- **Not contradictions, worth knowing:**
  - "Other expenses" means a finance line in the app, but a cost-of-attendance item in the glossary.
  - The finance-forms statement didn't say that the for-profit form also follows FASB standards; it now does (your decision 3).
  - The glossary's "Comparison group" entry is about the retired Peer Analysis System. The concept comes first, so it is not the answer to "what is the comparison group".

## 6. Explanation questions

**How a "what does X mean" question is answered:**

1. **The shortlist has two small new sections:** up to three concepts (tag C) and up to three glossary entries (tag D, never the historical ones).
   - They are searched on their own word weights, so they can't change which measures a data question gets, or their order. A test checks this on "retention rate at Yale".
   - The model is told to use them only when the user asks what a word means.
2. **The reply shape is unchanged.** The first trial call showed the API refusing any new field: three trial calls and a set of small probes found that even one extra text field, of any shape, makes its grammar too large, and that shortening the tag lists does not help. So:
   - the C and D tags go in `topic`, which already takes "an ID from the shortlist" (for define only; code reads the tags out and checks each was on the shortlist);
   - the model's own short explanation goes in the request's `label`, which is otherwise used only to name options (read for define only).
   - Worth knowing: the reply shape is now at the API's limit. Any future field (the planned `formula`, for example) will need room made first.
3. **The answer follows the order of sources:**
   - the concept, with its source and the app's convention;
   - then the glossary entry, labelled "IPEDS glossary, 2025-26 edition", followed by "In this app: …" when terms.csv has a convention for the same word (for "net price": the one-year lag);
   - then any measure's own definition, now with its period, its year caveat and any approved comparability-break note ("fuller explanations" in the work order).
4. **A general explanation:**
   - It is shown only when none of those sources explains the word.
   - It is labelled "General explanation, not from IPEDS documentation".
   - The question log marks it (`general_explanation`), so it can be reviewed.
   - It is never shown if it contains a number.
5. **What an explanation never does** is say on its own whether IPEDS collects something. "IPEDS does not collect this" still comes only from outside_ipeds.csv. No summary is written for a definition.

**The four message wordings** are rows in terms.csv, so you can edit them.

## 7. Tests and runs

- **Tests:** 297, all passing.
  - New: 10 explanation tests:
    - the three data questions from the work order still get their measures;
    - the new sections don't change a data question's measures;
    - the concept comes first, and the glossary carries its edition;
    - the convention follows the glossary entry;
    - historical Carnegie entries are never offered;
    - a general explanation is labelled and logged, and is not shown if it holds a number;
    - an unlisted tag is rejected;
    - tags in `topic` and an explanation in `label` are read only for define;
    - a measure's explanation includes its year rule and comparability note.
  - The dictionary checks cover the two new tables. The fixture and the inventory know them.
- **Full rebuild:** done, no check problems; the fast rebuild after your decisions also passed.
- **Trial call:** refused twice (reply format too large, see section 6), accepted on the third with the unchanged reply shape; it answered "What is an adjusted cohort?" from the concepts table.
- **Tests after the runs:** 298, all passing (one more: no explanation names an internal file; see below).
- **Two Haiku runs** (`IPEDS_STAGE=5f`, so the 10 owner questions for types 44 and 45 now count). Runs `haiku_5f_first` and `haiku_5f_second`; manual review in `docs/stage4/review.csv` (in each run, 51 turns carried over from Part 5e's reviews where the reading was the same, and 16 read by hand).

| | Run 1 | Run 2 | Range |
| --- | --- | --- | --- |
| Scored questions (128), right or acceptable | 119 (93.0%) | 120 (93.8%) | **93.0% to 93.8%** |
| The 10 explanation questions | 10 | 10 | all answered from the concepts table first; none fell back to a general explanation |
| The same 118 questions as Part 5e | 109 (92.4%) | 110 (93.2%) | Part 5e: 94.9% to 96.6% |
| Trend questions: measure read right | 19 of 21 | 18 of 21 | |
| Badly written set (56), right or acceptable | 55 (98.2%) | 54 (96.4%) | Part 5e: 100% in both |
| Mean time per turn | 6.4 s | 6.2 s | |
| Turns over their limit (10 s; 20 s with a search) | 3 | 6 | slowest 13.4 s, no search turn over 14.4 s |
| Cost | $0.26 | $0.26 | for 236 turns |

**Below the 90% threshold? No, but lower than Part 5e on the same questions** (3 and 4 more wrong readings). What changed:
- **Caused by the explanation path (2 questions):**
  - log 60.4, "What is the universe with the lowest net cost?", run 1: read as a definition of the universe (it showed the concept and the glossary entry). A ranking by net price, or a clarifying question, was expected; run 2 asked a clarifying question. The instruction already says definitions are only for "what does this word mean". I have not added lines for one phrasing.
  - log 60.5, "Where does income data come from in IPEDS?", both runs: now answered with the "Pell grants as an income measure" concept (IPEDS reports family income only for students awarded federal aid; the Pell share is the usual proxy). The expectation, written before your new low-income wording, says decline ("income data is not in IPEDS"). The answer looks right to me, and Part 5e's decline was a generic "I answer questions about U.S. colleges". **For you:** change this expectation to answer or decline?
- **The year misread, again (run 1):** log 4.1, "bachelor's degrees in 2014–15" (written with a long dash), declined as before the ten releases. Run 2 read it right. You said to tell you rather than add more lines: it recurs about once a run.
- **Readings that vary between runs, not caused by this part:** 12-month instead of fall enrollment by race (log 3.2, run 1); core expenses for RIT alone instead of RIT and its peers (log 58.7, run 1); childcare left out of Smith's services (run 1); Yale's test requirement left out, scores only (run 2); "just Yale and Harvard" kept all eight (run 2; also wrong in Part 5e run 1); a "yes please" follow-up re-ran a ranking where Part 5e declined (log 14.4, both runs).

**Found in the review and fixed after the runs:** the concepts' `app_convention` and `source` columns still held my draft's references, so the explanation answers printed, for example, "In this app: terms.csv 'national universe' and its statement". Both columns are now plain wording: 11 conventions written as sentences ("When you ask for enrollment, this app shows the fall total headcount, unless you ask for 12-month enrollment"), the rest left blank where the explanation already says it, and the sources rewritten without file names. A test now checks no explanation names an internal file. This changes only what is shown, never what the model reads, so the runs were not repeated.

## 8. Line counts

The question path is 3,662 lines (3,581 at the end of Part 5e): +81.
- resolve +32 (the order of sources);
- shortlist +18 (two sections);
- request +16 (reading the explanation from topic and label);
- interpret +9 (instruction lines and the section);
- show +4;
- answer +2.

`scripts/parse_glossary.py` is 233 lines.

## 9. The imputation proposal

Written, and decided: imputed figures are not labelled. The proposal stays in `docs/reports/STAGE_5F_PROPOSAL_IMPUTATION.md` as a record, and DECISIONS.md says imputed figures are shown as IPEDS publishes them, explained by the imputation concept, to be revisited if the question log shows users confused by it.

The reply-format workaround is accepted for now. Part 5g will report what takes up the reply format's size and propose one restructure, for your approval.

## 10. Questions for you

1. Log 60.5 ("Where does income data come from in IPEDS?"): change the expectation from decline to answer or decline, given your new low-income wording?
2. The concepts' convention sentences (section 7): approve the wording, or edit it in `dictionary/concepts.csv`?
3. Push Part 5f after your review?

## 11. After your approval (2026-11-25)

- **Income question:** its expectation is now "answer".
- **Convention sentences:** each is now tied to a test (`ConventionSentences` in tests/test_path.py), and a test fails if a sentence is added without a check. All held except one, which exposed a real bug:
  - **Carnegie groups in a trend.** The figures were right: R1 has the same 187 schools in every year, its 2024-25 list. But the answer said "In each year, the group counts the schools that belonged to it that year", the opposite of your decision 6d, which says the rule is to be stated in the answer. It also offered a "Today's schools only" button that changed nothing.
  - **Fixed:** a group whose `membership` is "as of latest year" now gets a new message row ("…every year counts the schools in the group in 2024-25, by its classification as of that year") and no button. Groups with each year's own list are unchanged.
  - The Carnegie sentence has its full stop.
- **Dashes:** en and em dashes become hyphens before the shortlist and the model see the question (answer.py, with a test).
- **The "2014–15" question** (log 4.1: "How many bachelor's degrees did Yale award in 2014–15?"):
  - **The right answer:** 1,327. It comes from the 2015-16 release, whose completions cover July 1, 2014 to June 30, 2015. Run 2 gave exactly that.
  - **What run 1 did:** it read the year the same way (2014 to 2015). The model then declined on its own ("missing: years"), judging those years not held, before the code could check.
  - **What this means:** this is the same pattern as the earlier year misreadings, but the cause is not the reading. The model is allowed to decline for years, and it guesses which years are held.
  - **A general fix to consider (not built):** the code alone decides whether years are held. The model would never decline for years, and the instruction would lose its "years" decline reason. This changes one instruction line and the decline choices.
