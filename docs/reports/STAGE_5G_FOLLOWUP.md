# Stage 5, after Part 5g: the trend questions, the reply format, years held

Date: 2026-11-25. Your Part 5g decisions are in `dictionary/DECISIONS.md` ("Part 5g decisions"). The speed target in `docs/V2_PLAN.md` now reads as your limits. Committed locally; Stage 5 is pushed after your review.

## 1. The 12 trend questions version 2 did not answer right

These are the 19 logged trend questions from the version 1 comparison. Version 2 answered 7 right in each run: 4.3, 4.4, 4.5, 6.1, 11.3, 58.2 (run 1) and 64.1. Here are the other 12, using run 1 (`haiku_5g_first`), with run 2 where it differed.

| Question | What version 2 did | Why |
| --- | --- | --- |
| **1.1** "Which years are available for Ivy League admission rates? Compare the latest available year." | **Wrong reading** (both runs). It said "Yes. This app has: Percent admitted (Fall 2024)", and neither listed the years held nor compared the schools | **A gap.** A "what data exists" answer shows only the latest period, never which years the app holds, so "which years are available" can't be answered as asked. The second half (compare the latest year) was dropped |
| **4.6** "Please create a trend for Ivies plus MIT and Stanford" | **Wrong reading** (both runs). It declined, saying no measure was named | Two causes. The model didn't carry the previous turn's measure (the graduation rate) into this follow-up. And "a group plus two schools" can't be expressed: groups in a request narrow each other, they never add schools. The nearest group, Ivy Plus, also has Johns Hopkins and Chicago |
| **4.7** "MIT is massachusetts institute of technology" | **Decline**, counted right by its expectation | The user is correcting the previous turn. The app treats it as a new question with no figure. Not a trend problem in itself, but it follows from 4.6 |
| **8.2** "how many degrees did Marian University in Indiana award in the last ten years?" | **Clarifying question** (run 1: the school picker). Run 2 answered right | Acceptable: two schools are named Marian University. Not a gap |
| **8.3** "confirm 151786" | **Decline**, counted right by its expectation | The user typed the school's ID to answer version 1's question. Version 2 asks with a picker instead. Not a gap |
| **11.1** "how has cost of attendance changed at University of Chicago compared to Harvard, Princeton, Yale, and Stanford" | **Clarifying question** (run 1); **wrong reading** (run 2) | **A gap.** Run 2 read the three "cost of attendance" columns inside one release's net price table (2021-22, 2022-23, 2023-24) as the trend, instead of the published cost of attendance across the ten releases. Several tables hold a few earlier years as columns of their own, and the model can take those for a trend |
| **22.2** "Show Yale's undergraduate grant and scholarship percentages from 2014–15 through 2023–24." | **Clarifying question** (both runs): "financial aid can mean different things" | Not needed: the user named grant and scholarship aid. The model matched the broader term "financial aid", which always asks. A minor reading problem, not a trend gap |
| **45.1** "Show a 10-year trend." | **Wrong reading** (both runs). It declined with "I couldn't find data matching that" and unrelated closest matches (10-month contracts) | **A gap in the reply, not the reading.** This is the conversation's first turn, so no measure exists. The right answer is to ask which figure. The app's "not found" decline offers matches on the words "10" and "year" |
| **45.2** "Show a longitudinal trend" | **Wrong reading** (both runs), as 45.1 | The same |
| **48.1** "how did the student body (characteristics) of Syracuse University change from 2015 to 2023" | **Clarifying question** (both runs) | Acceptable: "student body characteristics" covers many measures. Version 1 also asked. A profile of the standard set (enrollment, race, gender, age, residence) would answer it directly, but that is a new feature |
| **55.1** "How does FRCC compare against other Colorado community colleges in enrollment and outcomes trends over time?" | **Clarifying question** (both runs) | Acceptable: "outcomes" has several readings (graduation rate, Outcome Measures). Version 1 also asked |
| **58.7** "compare these same institutions on their ten year trends for expenditures per student FTE" | **Wrong reading** (both runs). It answered for RIT alone | "These same institutions" means the five schools the user listed two turns earlier (the example set). The model kept only RIT. Turn 58.6 fails the same way. Carrying named schools over several turns |

**Does this point to a trend gap the question set misses?** The set holds every question above, so none is missing, but three gaps rest on one question each:
1. **"Which years do you have?"**: only 1.1 asks it. The app can't list the years held for a measure in a "what data exists" answer.
2. **A few earlier years held as columns of one release** (net price two years back, cost of attendance in the net price table): only 11.1 runs into it. The model can take those columns for a trend, which gives three years from one release where the user wanted ten.
3. **A group plus named schools** ("Ivies plus MIT and Stanford"): only 4.6. The request can't express it; the plan already puts "groups from a list the user confirms" in Stage 6.

The others are follow-ups that carry things across turns (4.6, 4.7, 58.6, 58.7), which the set covers several times and the plan leaves to Stage 6. There is also the "not found" reply to a trend that names no measure (45.1, 45.2), covered twice.

**My suggestion, for your decision:**
- Add about six questions to the set, two for each of the three thin gaps. For example: "Which years of graduation rates do you have for Yale?", "How has net price at Harvard changed over the last ten years?", and "Show enrollment for the Big Ten plus Notre Dame".
- Gap 1 could be fixed in the "what data exists" answer (show the releases a measure is held in, from `measure_years`). That would be a proposal, not part of this change.

## 2. The reply-format restructure (decision 1)

**Each of the 12 fields checked.** "" (or 0 for the one number) can never be a real value in any of them:

| Field | "None" is now | Why it can't be real |
| --- | --- | --- |
| a school's tag | "" | tags are S1 to S16 |
| peers_of | "" | the same |
| breakdown | the object is always present; set "" | set tags are B1 to B32 |
| split_by | "" | sector, level or control |
| sort | the object is always present; order "" | highest or lowest |
| sort's limit | 0 | "the top 0" means nothing |
| year's stated text | "" | when the user names a year, the text is never empty |
| year's kind | "" | a fixed list of kinds |
| topic | "" | the user's topic is never empty when given |
| outside | "" | tags are O1 to O4 |
| decline | the object is always present (read only when the reply is a decline); missing "" | a fixed list of reasons |
| decline's "about" | "" | why, where or instead |

**What changed:**
- The reply shape has no "value or null" choice left.
- The code that reads the model's reply turns "" and 0 into "not given", so the rest of the path is unchanged.
- The explanation now has its own fields: `explain` (a list of C and D tags) and `general`. The tags are out of `topic` and the general explanation is out of `label`.
- The instructions say "leave a field empty" where they said "null".
- **Accepted by the API** (trial calls, 2026-11-25): 6,469 characters, no "value or null" choices.
- **Code:** request.py and interpret.py, about the same size as before.

## 3. Years held: only the code decides (decision 2)

- **The model can't decline for years:** "years" is no longer one of its decline reasons. One instruction line says: "Never decline, or add a note or an outside topic, because of the years asked for: write the years as the user named them, and the app checks which years it holds."
- **The model can't attach the outside-IPEDS row for years:** the row "Years outside 2015-16 to 2024-25" has a new column, `checked_by_code = years` (outside_ipeds.csv, README updated, a build check), and such rows are never put on the shortlist.
- **When years really aren't held,** the code's own message says so and now adds that row's pointer: "I have Total enrollment for Fall 2015 to Fall 2024 only, so I can't show 1990. You may find this in NCES IPEDS Data Center for earlier years. Instead, I can show Total enrollment for Fall 2024."
- **Tests** (`YearsHeldByCode`), with the logged question "How many bachelor's degrees did Yale award in 2014–15?":
  - the model can't decline or add a note for years;
  - 2014–15 is answered (1,327, July 2014 to June 2015) with no note on earlier years;
  - a years decline from an older reply is checked by the code and answered;
  - years not held (2009-10) are declined by the code, with the pointer.

## 4. Speed (decision 3)

The plan now reads: at most 10 seconds a turn, 20 for a turn where the AI searches, with the median turn time reported for each run. Below, the runs report it.

## 5. The two runs

Runs `haiku_5h_first` and `haiku_5h_second` (`IPEDS_STAGE=5f`), after both builds. One trial call first, accepted. Manual review in `docs/stage4/review.csv`: earlier reviews carried over where the reading was the same, and 16 turns read by hand.

| | Run 1 | Run 2 | Range |
| --- | --- | --- | --- |
| Scored questions (128) | 121 (94.5%) | 122 (95.3%) | |
| Trend questions (21) | 16 | 16 | |
| **Scored and trend together (149), the success test** | **137 (91.9%)** | **138 (92.6%)** | **91.9% to 92.6%** (Part 5g: 91.3% to 91.9%) |
| Trend questions: measure read right | 19 of 21 | 20 of 21 | |
| Badly written set (56) | 54 (96.4%) | 55 (98.2%) | |
| The same 118 questions as Part 5e | 111 (94.1%) | 112 (94.9%) | Part 5e: 94.1% and 95.8%; Part 5g: 93.2% and 94.9% |
| False "IPEDS does not collect this" | none | none | |
| Shortlist misses | 0 of 25 | 0 of 25 | |
| **Median turn time** | **6.7 s** | **6.3 s** | |
| 90th percentile | 10.0 s | 9.8 s | |
| Turns over your limit (10 s; 20 s with a search) | 6 of 236 | 5 of 236 | slowest 13.1 s |
| Cost | $0.27 | $0.27 | for 236 turns |

**What the two builds changed:**
- **Years:** "How many bachelor's degrees did Yale award in 2014–15?" is answered right in both runs, with no note on earlier years. No answer in either run carries the "earlier years" note, and the model declined for years in no turn.
- **Reply format:** no turn failed on the format. Fields the model left empty were read as "not given" everywhere, with no new wrong readings traced to it. The explanation questions were all answered from the concepts table first, as before.
- **The score:** the same as before within the spread between two runs. The 118 questions are as in Part 5e, and the success test rises slightly (91.9% to 92.6%).

**Wrong readings in these runs:**
- **The persistent follow-ups:** log 24.3, 24.6, 58.5 and 14.3; the trends with no measure, 45.1 and 45.2; "which years are available" (1.1); cost of attendance over time (11.1).
- **Readings that vary between runs:**
  - Yale's test requirement (run 1);
  - "Which Massachusetts colleges offer distance education" (run 2: read as schools with students enrolled only online);
  - "uiuc intl students" (run 1: not found);
  - "hi can u tell me abt stanford" (run 1: declined where a question was expected);
  - "is miami dade the biggest community college" (run 2: the ranking without naming Miami Dade);
  - the WSU Tech trend (run 1: a bachelor's rate, which can't be combined for a group);
  - log 58.7 (run 2: RIT alone).
- **None involves years or the reply format.**

## 6. Tests and line counts

- Tests: 313, all passing (4 new for years held; the explanation and years-outside tests updated to the new fields).
- The question path: 3,676 lines (3,668 after Part 5g).

## 7. Questions for you

1. The six test questions for the three thin trend gaps (section 1): add them to the set?
2. Gap 1, listing the years a measure is held in a "what data exists" answer: do you want a proposal?
3. Push Stage 5 after your review?
