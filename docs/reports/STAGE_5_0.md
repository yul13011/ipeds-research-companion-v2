# Stage 5, part 5.0: fixes from owner testing

Date: 2026-11-22. Data: the 2024-25 release only, as before. Model: Haiku. Decisions are recorded in `dictionary/DECISIONS.md` under "2026-11-22: Stage 5, part 5.0".

## The "done" tests, one by one

| Test | Result |
| --- | --- |
| **ROI two-turn conversation** ("What's the ROI for Yale?", then "Where can I find that?") | **Pass.** Turn 1: "IPEDS does not collect earnings…", from the outside-IPEDS row. Turn 2: "You may find it in: College Scorecard (U.S. Department of Education)." |
| **HSI two-turn conversation** ("Graduation rate for Hispanic-serving institutions", then "Why not?") | **Pass.** Both turns: "IPEDS has no flag for this group. Instead, I can show the same figure for all U.S. schools." |
| **Yale 1990 two-turn conversation** ("Enrollment at Yale in 1990", then "What can you show me instead?") | **Pass.** Turn 1 is declined for years. Turn 2 runs the alternative: Yale's fall 2024 enrollment, 15,564. |
| **Marian two-turn conversation** ("How many degrees did Marian University award over the last ten years?", then "show 2023-24") | **Not a pass as written.** There are two Marian Universities (Indianapolis and Fond du Lac), so turn 1 asks which. In the final full run, "show 2023-24" was then declined, because a school picker did not keep its request as the previous request. I fixed this after the run, with a test. In a live check, run twice on Haiku, turn 2 now asks again which Marian, with 2023-24 applied to both choices; choosing one gives the 2023-24 degrees (tested with saved replies). If you want this conversation to reach an answer in two turns, the question needs "in Indiana" (as the logged question had). |
| **"what data do you have on admisisons"** lists the admissions measures | **Pass**, checked live twice. The misspelling is corrected, and the answer lists 14 admissions measures, from "Admission test scores" to "Percent admitted - total". It needed one more instruction line ("list every shortlist measure of a broad topic"). Before that, the model gave only the topic word, and the app correctly said "not found". |
| **"what was the fall enrollment for wsu tehc"** asks which WSU or finds WSU Tech, never Texas Tech | **Pass.** The full run and two live checks all found WSU Tech (fall headcount 6,106). Texas Tech is not even on the shortlist. |
| **No false "IPEDS does not collect this"** in the full rerun | **Pass.** All 10 statements that IPEDS lacks something come from a row in `outside_ipeds.csv` (earnings/ROI, AI policies) or from a group's own entry ("IPEDS has no flag for this group"). |
| **No internal words shown** (shortlist, tag, dictionary, item codes) | **Pass in the final run.** The run before it had one leak: an option label written by the model said "Smith College (S4)". Codes are now removed from labels in code, with a test. |
| **No new wrong readings** in the full rerun compared with the last Haiku scorecard | **Not met.** 6 earlier wrong readings are fixed; 5 new ones appeared, all model readings, one caused by a search miss. Details below. |

## Scorecard: Haiku, final 5.0 run beside the Stage 4 run

Same questions in both runs: 102 scored and 20 trend questions.

| | Stage 4 (Haiku) | Part 5.0 (Haiku) |
| --- | ---: | ---: |
| Correct answer | 40 | 40 |
| Correct decline | 49 | 47 |
| Clarifying question | 6 | 11 |
| Wrong reading | 7 | 4 |
| **Right or acceptable** | **93%** | **96%** |
| Trend questions: correct answer / correct decline / clarifying question / wrong reading | 0 / 16 / 4 / 0 | 4 / 8 / 6 / 2 |

Trend questions can now get "the year held, with the missing years named" (part 5.0, item 6), which counts as acceptable until trends exist. A trend answered for one year with no such note counts as a wrong reading.

**Fixed since Stage 4** (6):
- "Show Yale's undergrad population by race and ethnicity" now gives undergraduates (6,814). The cause was the "undergrad" synonym plus the breakdown's level on the shortlist.
- "What is the universe with the lowest net cost?" is answered.
- "Actually, go back to all eight" is answered.
- "What is Yale's average net price for 2024-25?" gives 2023-24, with the lag stated.
- "What are Yale's admissions test score requirements?" gives the test policy (test optional).
- "use the institutions in the example set" now gets a clarifying question.

**New wrong readings** (5, all model readings):

| Question | What happened |
| --- | --- |
| "how has cost of attendance changed at university of chicago compared to …" (trend) | Answered for 2024-25 only, with no note that other years are missing: the model left the period empty |
| "Show Yale's undergraduate grant and scholarship percentages from 2014–15 through 2023–24" (trend) | Answered 2023-24 with the missing years named, but with institutional grant aid for first-time students. The undergraduate grant measure (SFA.UAGRNTP) was **not on the shortlist**: a search miss, see open question 1 |
| "can you list them in rank order from largest to smallest" (dual enrollment) | Listed the schools by name instead of ranking them |
| "Which Massachusetts colleges offer distance education to undergraduates?" | Listed schools by undergraduate offering; the distance-education measures were 1st and 2nd on the shortlist |
| "How many nonbinary faculty does Smith College employ?" | Showed the men/women breakdown instead of declining |

**Variation between runs.** I ran the full set three times while fixing (logs kept in `logs/stage4/haiku_5_0_*`). The new wrong readings differed from run to run:
- the nonbinary question was wrong in runs 1 and 3, right in run 2;
- the dual-enrollment ranking was wrong only in run 3;
- distance education was wrong in runs 2 and 3.

On a single run, "no new wrong readings" mixes real changes with Haiku's own variation. See open question 2.

**New questions** (not in the Stage 4 run):
- Conversations 62–64 from the log: 1 wrong reading. The STEM question was declined with the outside-IPEDS row on graduation rates by major, instead of answering the parts IPEDS has.
- WSU Tech (two turns): both correct.
- The owner questions due at 5.0: as in the table above.

Owner questions due at 5f and 6 are reported but not counted, as agreed.

**Time and cost.** The final run took 4.7 seconds per turn on average (Stage 4: 3.6) and cost $0.145 for 177 turns ($0.096 for 143). Output tokens rose from 79,290 to 136,296. The main cause: a decline now carries the request the model would have made, so a follow-up can edit it. Typical questions are still under the 5-second limit on average, but closer to it.

## What was built

1. **Misspelling tolerance** (`path/shortlist.py`). A question word the search does not know is matched to the index words it misspells. Words of up to four letters may only swap two neighbouring letters; five to seven letters may be one letter off; eight or more, two. The question's own word is kept beside the correction. Examples: "admisisons" finds admission, "tehc" finds tech, "Yael" finds Yale, "graduaton … Harvrd" finds graduation and Harvard.
2. **The four answers.**
   - "IPEDS does not collect this" comes only from `outside_ipeds.csv`.
   - A model decline saying "not in IPEDS" without such a row, a "measure" decline, and a "what data exists" answer with nothing matched all become "not found". That answer names the closest matches and is logged as a search miss (`search_miss` in the question log).
   - The instructions no longer let the model decide what IPEDS lacks.
3. **Messages written by code.** Every message shown when the app cannot answer comes from a "message" row in `terms.csv`, filled in by code. The model's own explanation goes only to the question log (`model_explanation`). A test checks that no message row contains internal words.
4. **Declined, clarified and partly answered requests are kept as the previous request**, including a school picker's. The model's decline now carries the request it would have made. Choosing an option or a school clears the pending question. An edit made while options are open is applied to every option, and the app asks again.
5. **Questions about a decline.** The decline's message, its outside source if any, and an alternative built from the request are stored with it. A new reply kind, `about_decline`, answers "why not?", "where can I find that?" (or "I don't have another source to point you to for this.") and "what can you show instead?" (the alternative, run).
6. **Answer what can be answered.**
   - When some of the years asked for are held, the held year is shown and the missing years are named.
   - When one of several measures is not set up, the rest are answered and the missing one named.
   - A comparison of several schools with a group shows every school, not only the first.
7. **The two defects from testing.**
   - The years message named only "Associate's degree". It now names the reading chosen ("degrees by level") or all the measures.
   - Alternatives are now built by code from the request in hand (the same request for the year held, without the unavailable group or breakdown, each school's figure ranked, or the nearest set-up measure of the same table). They are never the model's own suggestion; "tuition and fees" was the model's.

## Decline messages for your review (drafts in `terms.csv`, term "message")

Words in braces are filled in by code.

| Kind | Message |
| --- | --- |
| years | I have {what} for {held} only, so I can't show {asked}. |
| years partly | I have {what} for {held} only; {missing} {verb} not available, so only {held} is shown. |
| not set up | IPEDS collects {what}, but it isn't set up in this app yet. |
| not set up partly | IPEDS collects {what}, but it isn't set up in this app yet, so it is left out. |
| not collected | {say} (the outside-IPEDS row's own wording) |
| not collected source | You may find it in: {pointer}. |
| not found | I couldn't find data matching that. Try rephrasing it, or ask what data there is on a topic. |
| not found topic | I couldn't find data on {topic}. Try other words, or ask about a school, a group of schools or a measure. |
| closest matches | The closest matches I found: {matches}. |
| no measure | I couldn't tell which figure you want. Name one, such as enrollment, admission rate or graduation rate. |
| no school | Which school do you mean? Name the school and ask again. |
| needs a comparison group | To compare, I need one school and a group to compare it with, such as its peers or a state. |
| no breakdown | I couldn't tell how to break this down. Name a breakdown, such as by race and ethnicity or by gender. |
| unknown group | I don't have a group called {what}. |
| group not available | {statement} (the group's own entry) |
| group | I don't have a list of schools for that group. |
| calculation | That needs a kind of calculation the app can't do yet. |
| calculation average | {what} is reported as {unit} for each school, so I can't combine it into one figure for a group. |
| breakdown | That breakdown isn't available for this figure. |
| breakdown not tested | I don't have a tested breakdown "{set}" for {what}. |
| breakdown does not add up | The breakdown "{set}" doesn't add up at {where}, so it isn't shown. |
| not a data question | I answer questions about U.S. colleges from IPEDS data. Ask about a school, a group of schools or a figure such as enrollment or graduation rate. |
| other | I couldn't turn that into a question about the data. Could you rephrase it? |
| could not read | Sorry, I couldn't read that question reliably. Could you ask it another way? |
| which option | Sorry, I couldn't tell which option you meant. |
| which did you mean | Which did you mean? |
| nothing to change | There's no earlier question to change. Please ask the full question. |
| instead | Instead, I can show {closest}. |
| instead none | I don't have a close alternative to suggest. Try asking about a school, a group of schools or a figure such as enrollment. |
| where none | I don't have another source to point you to for this. |
| why none | There's nothing I declined to answer just now. |

One wording issue shows in practice. Measure names are IPEDS's own, so "years" can read stiffly: "I have Average salary equated to 9 months of full-time instructional staff - professors for Fall 2024 only…". A shorter plain name for these measures (`plain_name` in `measures.csv`) would read better.

## Tests and line counts

- 171 tests pass, up from 156. New: `Stage50` in `tests/test_path.py`. Three older tests were updated to the new wording.
- The question path is 2,268 lines, up from 1,944: resolve 847, shortlist 387, fetch 361, request 244, interpret 177, answer 124, show 99, log 27.
- The build is 777 lines (unchanged).

## Open questions

1. **Search miss: "undergraduate grant and scholarship percentages".** The undergraduate grant measure (SFA.UAGRNTP, "Percent of undergraduates awarded grant aid") does not reach the shortlist. A synonym such as "grant and scholarship percentage" on that measure would fix it. Approve?
2. **What "no new wrong readings" should mean, given Haiku's run-to-run variation.**
   - **(a)** Compare the sets of wrong readings across two runs of each version.
   - **(b)** Judge by cause: a path defect must not appear, while model readings are tracked as a rate.
   - **(c)** Keep single-run comparisons as now.

   I recommend (b), with the rate measured over two runs.
3. **Marian.** Should the owner question say "in Indiana", so it can reach an answer in two turns? Or should the expected outcome for turn 2 be "asks again which Marian, for 2023-24"?
4. **The decline messages above.** Any wording changes?
5. **Time.** The average is now 4.7 seconds per turn. Carrying a request with every decline is what made follow-ups to declines work; I'd keep it and watch the speed limit in later parts.
