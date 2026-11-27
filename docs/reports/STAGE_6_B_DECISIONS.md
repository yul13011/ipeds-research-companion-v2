# End of Part 6b: the owner's three decisions (2026-11-26)

Proposals only. Nothing in the question path, the dictionary or the grader has changed. The dictionary was changed for decision 1, the build refused it, and it was put back (below).

## 1. The faculty term's `always_ask`: not built. The build refuses it, and the cause is elsewhere

**What happened.** I set `always_ask` to `no` on the six faculty rows and reloaded the dictionary. The build stopped with its own check:

> terms.csv: 'faculty' neither asks the user nor has a default reading

- The check (`build/build_dictionary.py`, line 205) requires every term to either ask or have a default.
- The reason: with `always_ask = no` and no default, nothing in the code asks for a bare "faculty". `resolve.apply_readings` asks only when `always_ask = yes`. The "ask when no default applies" route (`level_defaults`) covers only terms with a `default_for` group.
- So "a bare 'faculty' still asks, since the term has no default" does not hold in the code. Building it as decided would make a bare "faculty" answer with whatever row the model picked, or with no row.
- I put the CSV back and reloaded the dictionary. `terms.csv` is unchanged.

**The real cause of the instructional-staff example's question.** The live call's reply (in `logs/trial/questions.jsonl`) shows:
- the model picked the instructional-staff row itself, `EAP.EAPPT` with `EAPCAT = 21000`, which is exactly the "Instructional staff" reading's row;
- it left `readings` empty;
- the code asks whenever a term marked `always_ask` has no reading in `readings`, even when the measure's row already *is* one reading.

The 6b report said the app asks "whenever the model picks either reading". That was too loose: the app asks whenever the model doesn't *name* a reading, even when the row it picked identifies one.

**Proposed fix (general step, no convention change).** Keep `always_ask = yes`. In `resolve.apply_readings`, before asking: when a measure's row matches exactly one reading's measure and condition, count that reading as chosen.
- **Where:** step 4 (resolve), `apply_readings`; reads `dict_terms` as now. About 4 lines and one test.
- **Effect:** "instructional staff" questions are answered. A bare "How many faculty does Yale have?" still asks when the model sends no row, as the current test checks.
- **The risk:** a bare "faculty" where the model guesses a row would no longer ask. One live call on each of the two questions would show whether Haiku does that (about $0.003).
- **A second problem, separate:** in the same reply the model took full-time staff from a different table (`S_IS.HRTOTLT`, the staff survey) and part-time from `EAP`. Even with the fix, that answer mixes two tables. It's a model reading. No change is proposed; it will be judged in the next run.

**Your choice:** (a) the fix above, or (b) another convention, such as giving the faculty term a default reading, which would stop a bare "faculty" from asking.

## 2. Log 4.6: the model's reply is right. The code drops it

**What the model sent** (the same in both 6b runs): a new request, operation `group`, group Ivy League, `plus_schools` MIT and Stanford, no measure, no schools. That's exactly right.

**What the code did.** A trend that names no figure goes to `resolve.no_measure` (owner decision 2026-11-25: use the previous request's figure, schools and group). That function starts from the previous request and replaces each scope part *only when the new request fills it*:
- the new request had no `schools`, so the previous request's Yale stayed;
- groups and added schools were replaced;
- the previous operation, `schools`, was kept.

So the page showed Yale's trend. The resolved request in the run log was: operation `schools`, schools Yale, group Ivy League, added MIT and Stanford.

**So the request's shape needs no change, and no trial call was needed.** The reply already says it sets a new scope: a `request` (not an `edit`) that names schools or a group. The fix belongs in the general step.

**Proposed fix.**
- **Where:** step 4 (resolve), `no_measure`. When the new request names any part of the scope (schools, groups, added schools, peers), take all four parts from the new request, and its operation when it's a trend operation. Keep only the previous figure and its readings. A request that names no scope keeps the previous scope, as now. About 3 lines changed.
- **Test:** the 4.5 → 4.6 pair replayed with fixed replies. It expects the Ivy League plus MIT and Stanford, operation `group`, and no Yale.
- **The instruction line added in Part 6a for log 4.6** ("A question naming its own schools or group replaces the previous ones…", `interpret.py` line 76) rested on the wrong diagnosis. I propose removing it with the fix. That frees about 19 words: the prompt is now 2,496 words against the 2,500 limit. The next question-set run checks that nothing else depended on it.
- **The 6b report's cause column** for log 4.6 says "model". It should say "code". I'll correct it when the fix is built.

## 3. Expectations that name no schools or no measure

**The list:** `docs/reports/STAGE_6_EXPECTATION_GAPS.csv`, 73 expectations that expect an answer or a trend. Real users' questions come first (log 34, badly written 1), then version 1's evaluation set (16), your questions (21) and the Explore examples (1).
- **No schools or group:** 41.
- **No measure:** 7.
- **Neither:** 25.

**The proposed fill** is in `proposed_measures`, `proposed_schools` and `proposed_groups`, with school names and where each came from (`basis`):
- **21** from a turn graded correct by hand in Part 6b's runs;
- **33** from a turn that answered but was only graded automatically (these need your eye most: the automatic grade is the weak point being fixed);
- **19** marked "fill by hand": the 6b turns asked, declined or were wrong, so there is nothing to copy.

**The three kinds of rows:**
- **School or group questions** (for example log 1.1, 11.2, 11.3, the net-price follow-ups): the group or schools can be filled. This is the main gain.
- **National questions, definitions and advice** (log 24.x dual enrollment for all colleges, the o44 to o47 definitions, "what data do we have on…"): there are rightly no schools.
  - A blank today means "anything passes".
  - **Proposed:** a marker, `none` in `schools`, meaning the request must name no schools or group. Grader change: about 3 lines in `auto_reading`.
- **Measure columns written as a concept** (`*net price`): these already go to a person (the grader can't check them). They're listed only where the schools are blank.

**The grader has a second gap, and it matters more for log 4.6.**
- The grader checks the IDs in the *resolved request*, not what the page shows.
- Log 4.6's resolved request held the Ivy League group plus MIT and Stanford (and Yale), so a filled-in expectation would still have passed it. What was wrong was the operation (`schools`, so only Yale's row was shown).
- **Proposed:** an optional `operation` column in `expectations.csv`, checked by the grader when filled (about 3 lines). Fill it for the trend and group rows in the list.

**When:** you said this can go alongside Part 6c. Once you've marked up the CSV, I'll copy the approved values into `expectations.csv`, which changes those rows' fingerprints, so their carried grades go back for review once.
