# IPEDS Research Companion: full code assessment

Nov 14, 2026 · @Eva

The data layer and the rule that the model never produces a number are sound. The code between the question and the data has two overlapping engines, six ways to fetch data and many duplicated rules, and the switch to the new engine silently dropped several capabilities and one safety check. Update, same day: after weighing repair against rebuild, the recommendation changed to building a new app around the sound parts and keeping this one live meanwhile. The "rebuild or repair" document holds that plan. The findings below still stand.

## Scope and method

Every Python file the app uses was read line by line, at commit `43b994d` of `yul13011/IPEDS-research_companion`. Nothing was run.

- **What was read.** All 39 files in `prototype/` (about 845 KB) and the `analysis_catalog/` package, split among six readers. Each reader traced which functions call which, using a search across the whole folder to confirm every claim about callers.
- **What else informed this.** The 2024-25 database and the column listings for all ten years; the real question log (107 rows, 37 free-form data questions); the November 5 evaluation results; and the design documents, including `V1_RETIREMENT_PLAN.md`.
- **What was not done.** The app and its tests were not run: the 3 GB of data and the API key were not available to the readers. Every defect below comes from tracing the code. Each one should be reproduced with a test before it is fixed.
- **Not read.** The test files, `ingestion/`, and most of `evaluations/`, except where a finding pointed there.

Throughout, "old engine" means the v1 path centred on `intent_router.py`, and "new engine" means the v2 path centred on `resolver_v2.py`, which is the default today.

## What is sound

These parts are worth keeping as they are.

- **The model never produces a number.** Every figure comes from a read-only, time-limited query that Python builds and checks.
- **The data copies.** Ten verified yearly databases, faithful to the IPEDS source.
- **The IPEDS domain rules.** Fiscal-year naming, cohort timing, totals mixed with sub-totals, duplicate rows, and missing values never treated as zero.
- **Provenance.** Each result carries its source table, variable, period and query, and exports include an audit trail.
- **A cross-year index already exists.** `analysis_catalog` records, for every table, whether it has one row per school, its key columns, its period, and its "family" across years (for example `DRVC{YEAR}`). It also links each variable to the same variable in the next year. This is built but not used at run time. By the project's own count, 303 of 505 school-level tables are keyed by school alone.
- **The idea itself.** Four questions the app failed on in the real log were answered by one simple query each against the 2024-25 file, in under 3 milliseconds.

## How a question moves through the modules today

A typed question passes through up to nine stages, and four of them call a model.

1. **`ui.run_pending`** shows a status line and calls `intent_router.handle`, which only forwards to the new engine.
2. **`faq_v2`** checks whether the text exactly matches one of the 18 example-button questions. If so, a stored plan runs with no model call.
3. **`resolver_v2.resolve`** (model call, Haiku) picks one of five operations and rewrites the question as a standalone request.
4. **Identity** (`institution_confirmation.mentions`, a second model call) extracts school names from the user's newest message and authorises only those schools.
5. **Keyword shortcuts** in `model_policy` and `catalog_planner` try the debt, cost and aid routes.
6. **`agent._ask`** applies more keyword gates (discovery, scope guard, degrees breakdown, catalogue scope).
7. **A planner** (model calls): `agent.model_plan` for reviewed measures, or `catalog_planner.model_catalog_plan` for everything else, with up to 8 calls and 16 lookups.
8. **One of six fetch paths** runs the plan (see structural findings).
9. **`result_narrative`** (model call, Sonnet) writes the summary during page rendering, before the table and chart are drawn.

If stage 8 returns no number, stages 3 to 8 run again on the larger model. A question that ends without a number can therefore use up to 22 model calls. Nothing is streamed: the user sees status text until everything, including the summary, is finished.

## Old engine versus new engine

The new engine did not only replace the old one. It bypasses `agent.ask`, and several capabilities and one safety check lived there or in `intent_router.dispatch`. The retirement plan lists only multi-part questions as deferred.

| Capability | Old engine | New engine today |
| --- | --- | --- |
| Definition questions | Dedicated route into `definitions` | No route. The model answers in its own words, or the question goes to the slow planner |
| "What years do you have for X" | `coverage.answer` | Unreachable. The user gets a list of data areas instead. The data guide still tells users to ask this question |
| "How many institutions" | `populations.institution_count` | Unreachable. Its only caller is `agent.ask` |
| Picking option A, B or C | Runs the saved, validated plan | Re-planned from the message text. The planner's prompt still promises the saved plan will run |
| Multi-part questions | Task plan with dependencies | One operation per message |
| Analysis plus chart formatting in one message | Both applied | Formatting dropped |
| Request-versus-plan check (right schools, years, scope) | `intent_checks.contract` and `check_plan` | Off. The switch that enables it is set only inside `agent.ask`. Three readers confirmed this independently |
| Unknown school name | Opens a picker | Dropped silently |
| Forcing the larger model for source planning | Yes, under "automatic" | No. Planning runs on Haiku first; the model selector is ignored |
| Conversation context passed to planners | Yes | Planners receive none; only the resolver's rewrite carries context |

What the new engine added: the exact-match FAQ layer, a refuse operation, the retry loop, and routing on the user's original wording.

Removing the request-versus-plan check was a deliberate choice, noted in the `resolver_v2` docstring, because it caused false refusals. The `README` still describes two validation gates.

## Structural findings

The same job is done in several places with different rules, which is why fixes in one place do not hold in another.

| Job | How many versions | Detail |
| --- | --- | --- |
| Fetching data | 6 | `analytics.execute`, `catalog_execution.execute_catalog`, `query_engine.execute`, `observations.execute`, `populations.execute_annual`, `populations.institution_count`. Each takes a different plan shape and returns a differently shaped result, so display code branches on which one ran |
| Turning text into a school | At least 5 rule sets | `institution_confirmation.resolve` and `candidates`, `catalog.institutions`, `catalog_planner._names` and `_cost_institution_names`, `workflows.institution_matches`, plus the model call. "Columbia" resolves in one and asks for confirmation in another |
| Reading years from the question | About 12 sites | "2023-24" means 2024 in `canonical_time` and 2023 in `_source_years`. The maximum range is 30 years in one place and 9 in another |
| Deciding follow-up versus new question | 8 places | Four are live under the new engine, including a keyword test applied to text the resolver has already rewritten |
| Searching the documentation | 6 | Five stop-word lists. "Faculty" is expanded to "instructional staff" when browsing but not when planning. "Yale", "university" and "students" are stop words in one search |
| Finding the same variable in another year | 5 | Including the unused `field_history` table that already does this properly |
| Checking an "undergraduate" request | 4 | Mentioning "full-time" exempts a question from one copy and triggers another |
| Editing a chart from text | 3 | Only `intent_router.apply_chart_edits` is live; the two keyword versions run only with AI off |
| Classifying a field's unit | 3 | Two derive it from English titles by keyword at run time |
| Validating one plan | 3 to 5 passes | The same plan is re-validated at preflight, on save, and at execution |

**Other structural points**

- **Rules are keyword patterns over English.** Eighteen validators accept or reject a plan by matching words in the user's question, and field meaning (unit, population, whether values can be added) is derived by matching words in variable titles. Examples of misfires: "us" read as "US"; "public health" read as public institutions; "average graduation rate" rejected unless the user says "unweighted"; a pattern for euros that also matches "European".
- **Shortcut routes are closed word lists.** Cost, aid, debt, degrees, enrollment by race and enrollment by gender each have one. Three are tied to the 2024-25 release only.
- **Each year's variable has its own numeric ID,** assigned by row order when the catalog is built. One added row in the 2015 codebook shifts every later ID, which would break the reviewed measures and six example buttons. The evidence fingerprints also include a file path from the author's computer.
- **Many files are older files pasted together.** `discovery.py` is four, `definitions.py` three, `coverage.py` three, `semantics.py` three, `populations.py` three. The planner's instructions are 13 patches appended in sequence, with later ones overriding earlier ones.
- **Hidden coupling.** Seven shared-state variables pass information between modules out of sight; three are never set under the new engine. Modules import each other in cycles that only work because imports sit inside functions. The planner depends on the interface library through `observations`.
- **Tests and evaluation.** No test imports `resolver_v2` or `faq_v2`. Seven of the 54 evaluation cases match example-button wording exactly and never reach the model. The evaluation skips the summary step. A run without the `--engine` flag is labelled "v1" although it runs the new engine.

## Defects traced in the code

These were traced by reading, not reproduced by running. Line numbers are at commit `43b994d`.

### Likely causes of failures seen in the question log

| # | Defect | Where | Effect |
| --- | --- | --- | --- |
| 1 | "Add X" and peer comparisons are blocked | `resolver_v2.py:259`, `catalog.py:257` | The identity step authorises only schools named in the newest message. A plan that includes earlier schools is rejected, and the retry repeats the same step. Matches the RIT-and-peers session |
| 2 | A no-number outcome triggers a full rerun that is then discarded | `resolver_v2.py:386-396` | Coverage gaps and clarifications cost a second pass on the larger model. Its usage is not added to the logged cost. Explains the 84 to 95 second "coverage limitation" rows |
| 3 | Lettered and short replies are re-planned from scratch | `agent.py:430` (old path only) | "A", "yes" and "both" lose the saved options. Matches the clarification dead-ends |
| 4 | The retry answers the app's own clarifying question | `resolver_v2.py` prompt, line 79 | The model is told to pick the most standard option on the user's behalf |
| 5 | A text reply from the planner is discarded | `catalog_planner.py:882-887`, `:990` | The user sees "planning search limit" even when the model answered or declined. The claim that scope was retained is untrue on the new engine |
| 6 | Discovery loses both AI steps on default settings | `resolver_v2.py:362`, `discovery.py:515`, `:652` | The interface passes "automatic"; discovery rejects that name and the error is swallowed. Users always get the template text |

### Wrong-answer risks

| # | Defect | Where | Effect |
| --- | --- | --- | --- |
| 7 | The word "to" triggers a year range | `agent.py:44`, `:87`, `catalog_planner.py:114` | "Compare Yale to Harvard in 2015 and 2024" becomes ten years |
| 8 | "The 2012 cohort" is read as observation year 2012 | `agent.py:53-54` | The model's correct cohort reading is discarded |
| 9 | "Award" as a verb triggers the degrees shortcut | `agent.py:305-309` | "How many Pell grants did Yale award in 2019?" returns a degrees breakdown |
| 10 | "sat" is matched inside other words | `agent.py:64`, `:98` | "compensation" near "90th percentile" returns the SAT refusal |
| 11 | Year checks are disabled for multi-year templates | `populations.py:190` | Years are stripped from the question before validation, and nothing compares years fetched with years asked for |
| 12 | A trend can split into one line per year | `populations.py:167`, `:181`, `query_engine.py:783-784` | Each year's value gets a different label; only the prompt asks the model to avoid it |
| 13 | "Count" has two meanings in one engine | `query_engine.py:576`, `:655` | All rows in one place, non-missing values in another |
| 14 | Request-versus-plan checks are off | `intent_checks.py:114`, set only at `agent.py:471` | See the engine comparison above |

### Interface, logging and cost

| # | Defect | Where | Effect |
| --- | --- | --- | --- |
| 15 | The summary is written before the table is shown | `ui.py:245`, `:306` | The finished table waits behind a model call |
| 16 | Summary cost and time are not logged | `result_narrative.py:139-146` | `latency_s` in the log excludes the summary and rendering |
| 17 | The summary ignores the "Use conversational AI" switch | `result_narrative.py:50` | Rows are still sent to the model with AI off |
| 18 | Tests wrote to the real-user log | `tests/test_chat_loading.py:25`, `:93`, `tests/test_transcript_scroll.py:19` | The tests patch the question handler but not the logger. Source of "A test question" and similar rows |
| 19 | A typed chart edit wipes Format-panel changes | `resolver_v2.py:141-152`, `ui.py:118` | Panel settings are overwritten |
| 20 | A bad chart setting gives the generic failure message | `resolver_v2.py:44`, `:302` | The wrong error type is caught |
| 21 | The model selector is ignored | `ui.py:12`, `:582` | The label "Sonnet for source planning" is untrue |
| 22 | Ranking fetches one school at a time in a 20-second window | `catalog_execution.py:240`, `:255-257` | One school with inconsistent counts aborts the whole ranking |
| 23 | Failures are swallowed silently | `resolver_v2.py:172`, `:186`, `:400`; `discovery.py:537`, `:681` | A real bug looks like "unavailable" and leaves no trace |

### Suspected, needs checking against the data

- A real value may become "missing" when a school has fewer rows than expected, because IPEDS often omits zero rows (`query_engine.py:575`).
- "West Virginia" may trip the check for "Virginia" (`populations.py:124`).
- The summary check rejects honest rounding and does not confirm a number belongs to the right school.
- Categorical and list answers may trigger the wasted retry in defect 2 every time, because the test looks only for a numeric value (`resolver_v2.py:290`).

## Review of the plan to retire `intent_router.py`

`V1_RETIREMENT_PLAN.md` is largely accurate about what to move, split and delete. Its gap is that it treats retirement as removing redundant code, when the new engine has not yet replaced everything the old one did.

**Accurate**

- Sections 2a, 2b and 2e: the pure old-engine code, the mixed files that must be split (`request_tasks.py`, `model_policy.py`), and the engine switch.
- The one live dependency of the new engine on the old file is `apply_chart_edits`.
- The `executor` argument the interface passes is never used by the new engine.

**Stale or wrong**

- Line numbers have moved: `resolver_v2.py:165` is now `:167`; `resolver_v2.py:199` is now `:295`; `agent.py:454` is now `:458-461`.
- Section 7 says `agent.ask` keeps `validate_transition` alive. Its only caller is `request_tasks.py:272`, which is old-engine code.
- `PURPOSE_AND_OFFLINE_PLAN.md` lists `conversation.select` as live under the new engine. It is not.

**Missing**

- The capabilities in the engine comparison above. Only multi-part questions are listed as deferred.
- After retirement, `coverage.answer`, `discovery.topic_index`, `definitions.answer` and `populations.institution_count` have no caller at all.
- The model selector and the "automatic" setting, including defect 6.
- Inert leftovers that stay behind: the `ACTIVE` and `PLANNING_CONTEXT` shared-state variables and `source_model`.
- Interface branches that only the old engine feeds: `ui.py:273-281`, `:283-302`, `:343`, and `queue_analysis_choice`.
- Three more test files that depend on old-engine code: `test_institution_confirmation.py`, `test_latency_improvements.py`, `verify_catalog_execution.py`.
- The new engine has no unit tests. The plan's goal of "v2 suite green" has nothing to measure until some exist.

## Recommended order of work

This section is superseded by the "rebuild or repair" document. Only the cheap fixes are still recommended for the current app: defects 1, 2, 6 and 18. The order below is kept for reference in case the rebuild is not pursued.

1. **Protect what exists.**
   - Add tests for the new engine, starting with one per defect in the first two tables.
   - Stop tests writing to the real-user log (defect 18).
   - Add the 37 real questions from the log to the evaluation set.
2. **Fix the defects behind the logged failures.** Defects 1 to 6, then 7 to 10. These are small, local changes and should move the most real questions from "no answer" to "answer".
3. **Decide on the dropped capabilities.** For each row in the engine comparison, choose restore or drop: definitions, years available, institution counts, option selection, and the request-versus-plan check. This is an owner decision, not a coding one.
4. **Then retire the old engine,** using the existing plan with the corrections above. Doing this before step 3 would delete the only working versions of those capabilities.
5. **Add one fast path for common questions.** Build a single cross-year table of the one-row-per-school measures from the index `analysis_catalog` already holds, with school attributes such as sector and state. Route lookups, comparisons, trends, rankings and group figures to it. Keep the catalog planner for multi-row tables and rare questions.
6. **Consolidate the duplicates.** One school-name resolver, one year reader, one documentation search, one result shape. Move IPEDS rules out of keyword patterns into tables the owner can review.
7. **Improve the wait.** Show the table before the summary, stream the summary, and log its time and cost.

**Open question for the owner.** Step 5 can stay within the October 26 decision (typed plans, no model-written SQL) if the fast path accepts a small typed request: measures, schools or a group, years, and an operation. That keeps the existing guarantee while removing the per-year ID lookups for common questions.
