# Stage 6, part 6a: follow-ups real users need, and the two cost corrections

Date: 2026-11-25. Your decisions are in `dictionary/DECISIONS.md`, "2026-11-25: cost corrections; Part 6a proposal approved". Built together, as you asked, then one question-set run. Committed locally; not pushed.

## In short

- **The cost corrections work.**
  - "How much does it cost to attend Harvard College in 2024-25?" gets the cost profile.
  - "How has the total cost of attendance at MIT changed since 2015?" gets ten years of the published total price, $63,250 in 2015-16 to 2024-25.
- **The scorecard is the same as the last Part 6.0 run on the full set and real users' questions** (94.2% and 89.4%), and one question better on the same 119 (96.6%).
- **Part 6a fixed eight of the questions it was for:** logs 1.1 (now "right"), 4.6, 24.3, 58.5, 58.6, 58.7 and 60.3 (College Scorecard), and the Big Ten plus Notre Dame.
- **It did not fix logs 45.1 and 45.2, and it broke log 23.1** (below). The cause is in my own code for gap 2: one general step, to change after your go.
- **Three trend questions were answered for one year only** (logs 11.1 and 55.1, and the Ivy-plus graduation rate trend). The model read "how has it changed" and "trend" with no years named as one year. No dictionary row says what a trend with no years named covers, so this is a question for you.

## Done when (from the proposal)

| Question | Before | Now |
| --- | --- | --- |
| log 4.6 "Please create a trend for Ivies plus MIT and Stanford" | declines | **Right.** The ten schools' combined graduation rate, for each entering cohort from fall 2009 to fall 2018 |
| o52 "Show fall enrollment for the Big Ten plus Notre Dame" | Notre Dame beside the Big Ten | **Right.** 19 schools; "Interpreted as" reads "Big Ten Conference, plus University of Notre Dame" |
| o52 "Graduation rate trend for the Ivy League plus MIT and Stanford" | a clarifying question | **Wrong.** The ten schools are right, but for one year only (the model gave one year; see open question 2) |
| log 45.1 "Show a 10-year trend.", 45.2 "Show a longitudinal trend" | "not found" | **Still wrong.** See "Did not work as planned" |
| log 58.5 (five schools named, after "compare RIT's completion rate to its peer institutions") | the app rejected the model's correct edit | **Right.** The five schools' graduation rates beside RIT's comparison group |
| log 58.6 "use the institutions in the example set" | the five schools lost | **Right.** The five kept |
| log 58.7 "compare these same institutions on their ten year trends for expenditures per student FTE" | RIT beside its peers | **Right.** Core expenses per FTE for the five schools, fiscal 2015 to 2024 |
| log 1.1 "Which years are available for Ivy League admission rates? Compare the latest available year." | years held, comparison as a button (acceptable) | **Right.** Both answers shown, one under the other |
| log 24.3 "both" (nothing pending) | declines | **Right.** "I'm not sure what you mean: there are no options open to choose from. Which schools, figure or years would you like?" |
| log 60.3 "What is college scorecard" | "choose an option" with none pending | **Right.** A short explanation: a Department of Education site whose earnings and debt figures are not in IPEDS |

**About logs 58.5 to 58.7:**
- RIT's own figure isn't in the 58.5 and 58.7 tables, because the user's list replaced RIT with the five schools. The expectation names only the five, so they pass. But a user comparing RIT to these schools would want RIT in the table too.
- The comparison group's row reads "RIT's own IPEDS comparison group (11 schools)" with 6 schools reporting. That is not new: a school being compared is left out of the group's figure, and all five are in RIT's group. The label could say so. I've noted it; nothing changed.

## What was built

**The cost corrections.**
- **terms.csv:**
  - "cost" keeps its five cost-profile rows as the default.
  - A new term, "cost of attendance" (words: "cost of attendance; COA"), defaults to DRVCOST.CINSON, with its statement.
  - The two net-price-table readings (the cost used to calculate net price; the cost for Title IV students) are marked `only_when_asked`.
- **The shortlist marks those readings:** "… | used only when the question asks for it specifically".
- **When the app asks which reading is meant, the term's default is always an option** (resolve.py, `with_default`). If two readings of one term are offered without the default, the default is put first. For MIT: "Total price, in-state students living on campus", then the two others.

**Part 6a, the five approved changes.**
1. **A group plus named schools.**
   - A new request field, `plus_schools`. The added schools join the group's list in every operation and in every year of a trend, even if they are outside the group or the national universe.
   - "Interpreted as" names both parts, using a new message row, "{group}, plus {schools}".
2. **A trend that names no figure.**
   - It uses the previous request's figure, with the new years (and new schools or group, if named).
   - With no previous figure, it asks "Which figure would you like to see over time?", with buttons for the four approved figures (terms.csv `figures to offer`). Each button uses its term's default reading.
3. **Schools named several turns earlier.**
   - The shortlist carries the last five requests. What they used is placed first, so the 64-measure limit can't drop it: this was the log 58.5 defect.
   - The prompt lists "SCHOOLS NAMED EARLIER", newest first.
   - An edit may keep an ID from an earlier request without it being rejected.
4. **Two requests in one message.**
   - A new reply kind, `several`. Each request is checked and answered, and the answers are shown one under the other (the page already does this).
   - The log records each part's outcome and request.
5. **No "choose an option" with nothing pending.** A reply of kind "choose" with no options open now gets the question above, instead of a failed reply.

**Elsewhere.**
- Two expectations changed, as approved: the Big Ten plus Notre Dame now expects an answer, and the Ivy-plus question a trend.
- The grader reads a several-part answer's requests, and counts added schools as schools named.
- The run script records each part's request.

## Test results

- **333 tests, all passing.** 11 are new (`Part6a`):
  - the Ivies plus MIT and Stanford: 10 schools, "Interpreted as", and a trend whose totals exceed the Ivies' alone in every year;
  - an added school edited, and one off the shortlist rejected;
  - a no-figure trend after Yale's enrollment gives ten years of it;
  - a no-figure trend with nothing before asks, with the four buttons; a button gives ten rows;
  - the log 58.5 shortlist keeps the carried measure, and the prompt lists the schools named earlier;
  - an edit keeping an earlier ID is accepted;
  - two requests answered together, with both logged;
  - "both" with nothing pending asks what is meant;
  - the term's default is always among the options, and isn't added twice;
  - only-when-asked readings are marked on the shortlist;
  - "cost" keeps the profile.
- **The older cost tests** use the new term name.
- **Trial call:** accepted. The MIT question gave ten years of total price.

## The scorecard (one run, `haiku_6a_first`, IPEDS_STAGE=6.0)

| Row | This run | Last Part 6.0 run (`haiku_60_cost`) |
| --- | --- | --- |
| Full set, scored and trend | 146 of 155 (94.2%) | 146 of 155 (94.2%) |
| Real users' questions (version 1's log) | 59 of 66 (89.4%) | 59 of 66 (89.4%) |
| The same as Part 5e (119, with log 1.1) | 115 of 119 (96.6%) | 114 of 119 (95.8%) |
| Badly written set | 54 of 56 (96.4%) | 55 of 56 (98.2%) |
| Median turn | 6.6 s | 6.7 s |
| Turns over the limit (10 s; 20 s with a search) | 16 of 242 (slowest 16.9 s) | 15 (slowest 19.0 s) |
| Cost | $0.27 for 242 turns | $0.28 |
| Shortlist misses | 0 of 25 | 0 |

**Manual review:** 24 turns read by hand. The rest were carried over where the reading was the same as in a reviewed run.

**Clarifying questions went from 13 to 19 in the scored rows, and declines from 23 to 19.**
- **Four short replies with nothing pending** ("yes", "yes please", "Another topic for Michigan", "MIT is massachusetts institute of technology") now get the new "what do you mean" question, instead of a decline. Their expectations accept both.
- **The others vary between runs:**
  - the faculty question offered two readings;
  - "part time student persistence" and "hbcus graduation rate" offered two measures;
  - "purdue" got the school picker.

## Wrong readings in this run (11)

| Question | Cause | New? |
| --- | --- | --- |
| log 23.1 "do you know the phd economics enrollment for past 5 years" | **path, Part 6a:** a decline for a figure IPEDS doesn't have went to the "which figure" question | **New.** Right in every earlier run |
| log 45.1, 45.2 (a trend with no figure) | **path, Part 6a:** the new step didn't catch these declines | wrong before too |
| log 11.1 (cost of attendance, five schools, "how has … changed") | model: one year for no years named | was a clarifying question |
| log 55.1 (FRCC, "trends over time") | model: one year (two answers, enrollment and outcomes) | was a clarifying question; has gone both ways |
| o52 Ivy League plus MIT and Stanford, graduation rate trend | model: one year | was a clarifying question |
| log 14.3 (rank by three measures, one outside IPEDS) | model: answered the part it could | wrong in Part 5g too |
| bw08 "RTI graduation rate" | model: read as RIT without asking | was a clarifying question; varies |
| log 24.6, probe_adm_act_yale, bw30 | as in the last run | wrong before too |

## Did not work as planned

**Gap 2, a trend that names no figure: logs 45.1, 45.2 and 23.1.**
- **What I built:** the step runs when the model declines because a measure is missing, and the request has a span of years. That's how the model answered "Show a 10-year trend" in the Part 6.0 runs.
- **What happened:**
  - **45.1:** the model declined with a different reason ("other"), so the step didn't run.
  - **45.2:** the model gave no years, so the step didn't run.
  - **23.1:** the model declined because PhD economics enrollment isn't in IPEDS, with a five-year span. The step did run, and offered four unrelated figures. That's worse than the right decline it gave before.
- **The cause:** the step leans on how the model happens to phrase a decline. It can't tell "no figure named" from "a figure named that IPEDS doesn't have".
- **The fix I'd propose** (general, about 6 lines; not built):
  1. One instruction line: "A request for figures over years that names no figure at all ('show a 10-year trend'): kind request, measures empty, with the years. The app uses the previous figure or asks which."
  2. Drop the decline route, so a decline for a figure IPEDS doesn't have stays a decline.

  The request route (a request with no measures and a span of years) is already built and tested. Checking it would need a run.

## Line counts

| | At the last commit | Now |
| --- | --- | --- |
| The question path | 3,814 (3,794 at Part 6.0's report, +20 for the cost convention) | 3,926 (+112: resolve +74, interpret +16, shortlist +11, request +7, answer +3, trend +1) |
| The page (app.py) | 161 | 161 |
| Tests (test_path.py) | | +142 |

The proposal estimated about +67 lines for 6a. The rest went to the cost corrections (the default always offered, the shortlist marker) and the change for "choose" with nothing pending.

## Open questions

1. **Gap 2's fix:** go on the instruction line and dropping the decline route (above)? It needs a run to check. The two runs at the end of Part 6a would do.
2. **What does a trend with no years named cover?** ("How has the cost of attendance changed at …", "Graduation rate trend for …", "trends over time".)
   - Today the instructions give examples only for named spans ("since 2015", "a 10-year trend"). The model sometimes reads these as one year, and sometimes asks.
   - A convention row would settle it. For example: "a trend with no years named covers all the years held (ten releases)", with one instruction example ("how has it changed", with no years: a range of all years).
   - Your decision; nothing built.
3. **Log 58.5:** when the user lists schools to compare with RIT, should RIT stay in the table? Today the list replaces RIT, which passes the expectation.
4. **The comparison group's label:** say "(11 schools; the 5 compared are left out)" when the compared schools are in the group?

## After your decisions: the end-of-part runs (2026-11-26)

Your five decisions are built, and the two work-order changes are recorded. They are in DECISIONS.md, "2026-11-25: Part 6a decisions after the first run; Stage 6 work order changes". Then the two end-of-part runs, `haiku_6a_second` and `haiku_6a_third`. Committed locally with your updated work order and plan; not pushed.

### What changed

1. **A trend with no figure.**
   - One instruction line: a request that names no figure is sent as a request with no measures and the years.
   - The route that read the model's decline is gone. The code decides: the previous figure if there is one, otherwise the four buttons.
2. **A trend with no years named** covers every release that holds the figure, starting at the first such release. Years from a later release's earlier-year columns come in only when the user asks for those years.
   - A terms.csv setting, `trend with no years stated`, holds the rule. Its statement is shown: "No years were given, so the trend covers every release that holds the figure."
   - One instruction line: "A trend or change with no years named ("how has it changed", "over time"): a range of years, start 0 and end 0."
   - For example: Harvard's net price with no years gives 2014-15 to 2023-24, ten rows. "Since 2012" gives twelve, with the two earlier years labelled.
3. **The school being compared stays** when the comparison schools are replaced (request.py, the edit step). Only removing it takes it out.
4. **The group label shows both counts** when the schools compared are in the group:
   - "Rochester Institute of Technology's own IPEDS comparison group: 11 schools in the group; 6 reported this figure (the schools compared are not counted in the group figure)";
   - in a trend, "… (the schools compared are not counted in the group figure)".
   - Two message rows.
5. **The run script** no longer fails when no summary has been written yet in a run. That failure is the `FileNotFoundError` on log 1.1, the first question of each run. It happened after the app had answered, and the app's answer is in its own log.

**Two instruction lines were shortened.** The test that keeps the prompt under 2,500 words failed by 5 words.

### Tests

- **339, all passing.** 6 are new (`Part6aDecisions`):
  - log 23.1's decline stays a decline;
  - the two instruction lines;
  - a no-years trend of net price (ten releases, no earlier-column years, the statement), and "since 2012" (twelve);
  - a no-years trend starts at the first release holding the figure: the Pell graduation rate, nine releases from 2016-17;
  - replacing the comparison schools keeps RIT, and removing RIT takes it out;
  - the label with both counts, one year and trend.
- **One older Part 6a test** now sends a trend with no figure as a request with no measures, instead of a decline.
- **Trial call:** accepted. "Graduation rate trend for the Ivy League plus MIT and Stanford" gave ten years.

### The scorecard (two runs, IPEDS_STAGE=6.0)

| Row | Run 1 (`haiku_6a_second`) | Run 2 (`haiku_6a_third`) | First 6a run |
| --- | --- | --- | --- |
| Full set, scored and trend | 148 of 155 (95.5%) | 146 of 155 (94.2%) | 94.2% |
| Real users' questions | 59 of 66 (89.4%) | 60 of 66 (90.9%) | 89.4% |
| The same as Part 5e (119) | 114 of 119 (95.8%) | 112 of 119 (94.1%) | 96.6% |
| Badly written set | 55 of 56 (98.2%) | 54 of 56 (96.4%) | 96.4% |
| Median turn | 6.3 s | 6.5 s | 6.6 s |
| Turns over the limit (whole turn, with the summary) | 9 of 242 | 11 of 241 | 16 |
| Cost | $0.27 | $0.27 | $0.27 |
| Shortlist misses | 0 of 25 | 0 of 25 | 0 |

**One turn of run 2 is left out of its timing.** "What is an adjusted cohort?" waited 10 hours for the API: the run went overnight, and the computer most likely slept. Its answer was right.

**Manual review:**
- 14 turns in run 1 and 11 in run 2 were read by hand. The rest were carried over where the reading was the same.
- I also checked each trend question's carried review against the years its answer covers. The carry-over compares figures and schools, not years, and this change is about years.
  - **One was wrong:** log 55.1 in run 2 carried "one year only", but the answer now covers every release. Corrected.
  - **Log 4.6 in run 1** was scored right by the grader, because its expectation names no schools, but it showed Yale only. Corrected to wrong.

### The questions these decisions were for

| Question | Run 1 | Run 2 |
| --- | --- | --- |
| log 23.1 (PhD economics enrollment, past five years) | **right**: declined again | **right** |
| log 45.1 "Show a 10-year trend." | **right**: asks which figure, with the four buttons | **right** |
| log 45.2 "Show a longitudinal trend" | **right**: the four buttons | **right** |
| log 11.1 (cost of attendance, five schools, "how has … changed") | **right**: total price, 2015-16 to 2024-25 | **right** |
| log 55.1 (FRCC, "trends over time") | **right**: enrollment over ten years; the outcome measures part asked which category | **right**: both over every release held |
| o52 Ivy League plus MIT and Stanford, graduation rate trend | **right**: ten schools, entering cohorts fall 2009 to fall 2018 | **right** |
| log 58.5 to 58.7 (the five schools) | **right**: RIT kept with the five | **right**, with the new label |

### Wrong readings in the two runs

**Wrong in one or both runs, but right in the first 6a run (or every earlier run):**

- **log 4.6, "Please create a trend for Ivies plus MIT and Stanford", both runs (model).**
  - The model kept Yale and "Yale's peers" from the earlier turns of that conversation and chose a "schools" answer, so only Yale's trend was shown. "Interpreted as" says Yale only.
  - It was right in the first 6a run. The same question asked on its own (the o52 owner question) is right in both runs.
- **log 1.1, run 1 (model):** the years held, then the Ivy League's combined admission rate, not the eight schools compared. Run 2 had both parts right.
- **log 8.2, run 1 (model):** bachelor's degrees only, for "how many degrees".
- **Big Ten plus Notre Dame, run 2 (model).**
  - The model chose a "schools" answer with Notre Dame only as an added school, so the app asked "Which school do you mean?". Right in run 1.
  - The app's question there is unhelpful; see open question 1.
- **log 60.5, "Where does income data come from in ipeds", run 2 (model):** declined as not a data question. Right in every earlier run.
- **bw23, "uw madison room and board", run 2 (model):** the combined food and housing charge, which UW-Madison leaves blank, instead of the on-campus figure. Right in every earlier run.

**Wrong before too, varying from run to run (model):** logs 14.3, 24.6, 60.4, 62.1 and 62.3, "just Yale and Harvard", the Yale ACT question, and "is miami dade the biggest community college".

None of these comes from the code built in this part.

### Speed: why the first 6a run had 16 turns over the limit

**The comparison with Part 5g ("16 against 6") mixed two ways of counting.**
- Part 5g's figures (6 and 5) and the first Part 6.0 run's (7) left out the written summary's time.
- The last Part 6.0 run (15) and the first 6a run (16) included it.

Counted the same way:

| Run | Over the limit, whole turn | Without the summary | Median turn | Model's median time | Median prompt |
| --- | --- | --- | --- | --- | --- |
| Part 5g run 1 | 10 | 6 | 6.0 s | 5.0 s | 13,524 tokens |
| Part 5g run 2 | 10 | 4 | 6.4 s | 5.1 s | 13,471 |
| Part 6.0, last run | 15 | 9 | 6.7 s | 5.4 s | 13,410 |
| Part 6a, first run | 16 | 8 | 6.6 s | 5.2 s | 13,672 |
| Part 6a, run 1 | 9 | 3 | 6.3 s | 5.2 s | 13,788 |
| Part 6a, run 2 | 11 | 6 | 6.5 s | 5.3 s | 13,722 |

**What changed, and what didn't:**
- The model's own time hasn't changed.
- The prompt grew by about 250 tokens (2%), from the new instruction lines and the "schools named earlier" line.
- **The extra slow turns in the first 6a run came mostly from the summary:**
  - more answers get one (128, against 117 in Part 5g), as more questions are now answered rather than asked about;
  - a two-part answer writes a summary for each part (log 1.1, 2.4 s; the negative net worth question, 4.8 s);
  - trend tables take longer to summarize.
- The table appears before the summary, so the user sees the answer within the time without the summary.
- **The two new runs, at 9 and 11, are in line with Part 5g's 10.**

The 16 turns over the limit in the first 6a run (whole turn; model and summary time):

| Turn | Time | Model | Summary |
| --- | --- | --- | --- |
| log 58.7 (expenses per FTE, five schools, ten years) | 16.9 s | 8.1 s | 3.0 s |
| owner: schools with negative net worth (two answers) | 15.1 s | 9.6 s | 4.8 s |
| log 14.3 (rank by three measures) | 13.6 s | 10.8 s | 2.2 s |
| log 55.1 (FRCC, two answers) | 13.2 s | 10.1 s | 2.8 s |
| log 11.1 (cost of attendance, five schools) | 13.0 s | 9.6 s | 3.1 s |
| log 64.1 (WSU Tech) | 11.9 s | 8.6 s | 2.5 s |
| bw11 "cuny schools grad rates" | 11.9 s | 9.7 s | 1.8 s |
| eval: Yale's admissions test score requirements | 11.9 s | 9.3 s | 2.2 s |
| log 1.1 (two answers) | 11.3 s | 7.5 s | 2.4 s |
| log 4.6 (Ivies plus MIT and Stanford trend) | 11.1 s | 8.1 s | 1.4 s |
| log 8.2 (Marian degrees, ten years) | 11.0 s | 7.0 s | 2.7 s |
| eval: does Smith provide on-campus housing | 10.9 s | 10.6 s | none |
| log 13.1 (Harvard cost) | 10.6 s | 7.7 s | 2.4 s |
| eval: Yale's net price, grant-aided students only | 10.5 s | 8.3 s | 1.9 s |
| bw47 "SUNY graduation rates" | 10.4 s | 10.3 s | none |
| bw41 "hi can u tell me abt stanford" | 10.1 s | 9.9 s | none |

None had a search, so all have the 10-second limit. Three are over on the model's time alone.

### Line counts

| | At the last commit | Now |
| --- | --- | --- |
| The question path | 3,926 | 3,950 (+24: trend +13, fetch +9, request +2, interpret and resolve together 0) |
| Tests (test_path.py) | | +71 |

### Open questions

1. **A "schools" request with no schools but added ones** (the Big Ten question in run 2) is declined with "Which school do you mean?", which reads oddly when the user named a group. Two options, neither built:
   - the decline says what was missing;
   - a general rule reads a request whose only schools are added ones as a group request.

   Your call.
2. **Log 4.6:** the model carries Yale and its peers into "a trend for Ivies plus MIT and Stanford", in a conversation about Yale. I didn't add a rule. If it stays wrong after Part 6b, the instruction on what a new question keeps from the previous one may need a look.
3. **The first column heading in log 7.1** (instructional staff) reads "Staff headcount, from the occupation table", without "Full-time, Instructional staff".
   - It happens when the same measure appears twice with different rows. It was there before Part 6a.
   - A general fix in show.py (each column names its row) is about 3 lines, on your go.
4. **Part 6a is ready for your review.** Then Part 6b's review point (the version 1 feature list), as the updated work order says.
