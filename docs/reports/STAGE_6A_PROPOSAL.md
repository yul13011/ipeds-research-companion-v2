# Stage 6, part 6a: follow-ups real users need (proposal)

Date: 2026-11-25. Proposal only, as the work order asks; nothing here is built. It covers four gaps from the real users' questions: the three in the work order, plus follow-up item 31 (your decision, "log 1.1 and follow-up item 31").

**The questions it must fix** (done when: they pass, with no new wrong readings elsewhere). These failed in every run after Part 5g, or are new questions for these gaps:

| Question | What happens now | Gap |
| --- | --- | --- |
| log 4.6 "Please create a trend for Ivies plus MIT and Stanford" | declines | 1, group plus schools |
| owner o52 "Show fall enrollment for the Big Ten plus Notre Dame" | shows Notre Dame beside the Big Ten | 1 |
| owner o52 "Graduation rate trend for the Ivy League plus MIT and Stanford" | declines or asks | 1 |
| log 45.1 "Show a 10-year trend.", log 45.2 "Show a longitudinal trend" | "I couldn't find data matching that", with unrelated matches | 2, trend with no measure |
| log 58.5 (a bare list of five schools after "compare RIT's completion rate to its peer institutions") | the app's own check rejects the model's correct edit: see gap 3 | 3, schools named earlier |
| log 58.6 "use the institutions in the example set", log 58.7 "compare these same institutions on their ten year trends…" | the five schools are lost; RIT alone, or RIT beside its peers | 3 |
| log 1.1 "Which years are available…? Compare the latest available year." | the years, with the comparison as a button (acceptable) | 4, two requests together (to reach "right") |
| log 24.3 "both" | declines: no options are pending | see the question at the end |

## The reply shape: checked first

Trial calls on 2026-11-25, one tiny call each:

| Variant | Characters | API |
| --- | --- | --- |
| Today's shape | 6,460 | accepted |
| + `plus_schools` (gap 1) | 6,653 | accepted |
| + reply kind `several` (gap 4) | 6,471 | accepted |
| Both | 6,664 | accepted |
| Both + a formula field (Stage 7, for headroom) | 7,397 | accepted |

Since the "value or null" choices were removed in Part 5g, there is room for both additions and the formula field.

## Gap 1. A group plus named schools

**The request:** one new list field, `plus_schools`, holding school tags. A group narrows as now (groups still intersect), and `plus_schools` adds schools to the result: the combined list is the group's schools plus those named. `schools` keeps its meaning: schools shown beside a group, or compared with each other.

**The code steps:**
- **request.py:** the field in the reply shape, read and written like `schools`. It can be edited ("add Notre Dame", "drop Stanford"), and its tags are checked against the shortlist.
- **resolve.py (scope):** after the groups' members are worked out, the added schools join them, if the directory holds them in that year. The national-universe limit doesn't remove a school the user named.
- **trend.py (group members by year):** the added schools join each year's list, if present that year.
- **"Interpreted as":** a message row in terms.csv, "{group} plus {schools}", for example "The eight Ivy League schools plus Massachusetts Institute of Technology and Stanford University".
- **interpret.py:** one instruction line: "A group with schools added ('the Ivies plus MIT and Stanford') puts the group in groups and the added schools in plus_schools."
- **Every operation that uses a group** (group figure, rank, list, split, count, trends) gets the combined list with no change of its own.

**Tests:**
- the Ivies plus MIT and Stanford give 10 schools, in one year and in a trend;
- a group figure sums over all 10;
- "Interpreted as" names both parts;
- an edit adds or removes one added school;
- an added-school tag not on the shortlist is rejected.

**Expectations:** the two owner questions change from "a clarifying question or a decline" to an answer, and log 4.6 stays a trend.

**Lines:** about 20 in the question path (request 6, resolve 6, trend 3, interpret 2, show 3), and about 40 in tests.

## Gap 2. A trend that names no measure

**The rule:**
- When a reply asks for figures over several years but names no measure, and the previous request has a measure, the code uses the previous request's measure, schools and group, with the new years. A follow-up is read the same way now, so this is how an edit works.
- When there is no previous measure, the app asks which figure, offering likely measures as buttons, instead of "not found".

**Where the likely measures come from:** "Show a 10-year trend" has no words to search on, so the shortlist's own top matches are unrelated (10-month contracts). I propose a settings row in terms.csv, "figures to offer when none is named". The draft is fall enrollment, admission rate, graduation rate (bachelor's six-year) and net price. That's a convention for you to approve or change.

**The code steps:**
- **resolve.py:** in the decline path (missing a measure) and in the request path (a request with no measure), check the year span and the previous request.
- **answer.py:** passes the previous request to that step. It already holds it.
- A message row: "Which figure would you like over {years}?"

**Tests:**
- "Show a 10-year trend" after a question about Yale's enrollment gives Yale's enrollment over ten years;
- the same as a first question gives a clarifying question with the four buttons;
- a button runs the trend.

**Expectations:** log 45.1 and 45.2 are their conversations' first turns and expect a clarifying question, so they would pass.

**Lines:** about 20 in the question path, 30 in tests.

## Gap 3. Follow-ups that refer to schools named several turns earlier

**What actually goes wrong, found while preparing this (logs, all runs).** In log 58.5 the user answers "compare RIT's completion rate to its peer institutions" with a bare list of five schools. The model reads it right: an edit, "replace the schools". But the app's own check then rejects it, because the measure kept from the previous request (the graduation rate) isn't on this question's shortlist.

The shortlist carries only the last request. In this conversation that request is the repeated turn 58.4, which the run doesn't count. So this is a path defect, not a model reading. 58.6 and 58.7 then fail because the five schools were never kept.

**The code steps:**
1. **The shortlist carries the measures, schools and groups of the last five requests,** not just the last one, so an edit or a reference back can use them. answer.py: `history[-5:]` instead of `history[-1:]`, still capped by the shortlist's tag ranges.
2. **The prompt adds "SCHOOLS NAMED EARLIER":** one line listing the schools of those requests with their tags, newest first, so "these same institutions" or "the example set" can be read as the schools of an earlier turn. interpret.py: about 6 lines.
3. **One instruction line:** "A reference to schools named in an earlier turn ('the same institutions', 'the example set') uses their tags from SCHOOLS NAMED EARLIER."
4. **The check that a request's IDs were on the shortlist** treats an ID kept from an earlier request by an edit as shown. It was, in an earlier turn; the edit didn't name it again. resolve.py: about 4 lines.

**Tests:**
- the 58.4 to 58.7 sequence as saved replies: the bare list replaces the schools, "the same institutions" keeps the five, and the trend runs for RIT and the five;
- a school from three turns back is on the shortlist and in the prompt;
- an edit that keeps an earlier measure is not rejected.

**Lines:** about 15 in the question path, 40 in tests.

## Gap 4. Two requests in one message, answered together (item 31)

**The request:**
- A new reply kind, `several`, with two (at most three) complete requests in `requests`, as options already use.
- The code runs each and shows the answers one under the other. The app already does this for "both" after options; the page and the log handle a list of answers.

**For log 1.1:** a "what data exists" request with the years held, then a ranking of the Ivies by admission rate for the latest year. That's your "right" reading. The button stays for a "what data exists" answer on its own.

**The code steps:**
- **request.py:** the kind in the reply shape.
- **resolve.py:** each request is checked against the shortlist and resolved, then the answers are returned together, as for "both".
- **interpret.py:** one instruction line, "When one message asks two things ('which years… and compare…'), give kind several with one request for each."
- **The written summary** covers the first answer only (one table per summary, as now).

**Tests:**
- a saved reply of kind `several` gives two answers in order, each with its own "Interpreted as";
- a request off the shortlist in either part is rejected;
- the log records both.

**Expectations:** log 1.1 then passes as "right".

**Lines:** about 12 in the question path, 25 in tests.

## In total

- **The question path:** about +67 lines, from 3,794 to about 3,860, in request, resolve, trend, interpret and answer. No new module.
- **Dictionary:** three message rows and one settings row (gap 2's offered figures, for your approval).
- **Tests:** about 135 lines.
- **Cost:** one fast rebuild, a trial call, one question-set run (IPEDS_STAGE=6.0), and two runs at the end of the part as usual.

## Questions for you

1. **Gap 2's offered figures:** fall enrollment, admission rate, the bachelor's six-year graduation rate and net price, or another list?
2. **Log 24.3 ("both"):**
   - The user was answering version 1's clarifying question. Version 2 never offered options at that point, so "both" refers to nothing, and version 2 declines ("I couldn't turn that into a question about the data").
   - The expectation is "an answer or a clarifying question".
   - Should a decline count as right here, or should the app ask what "both" means? Asking is a fifth change: a choice with no pending options becomes a clarifying question, about 5 lines.
3. **Gap 1's meaning:** the added schools join the group even if they are outside it, or outside the national universe. Is that right, or should a school outside the universe be left out and named?
