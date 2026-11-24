# Stage 5, part 5c: the decisions on the Part 5c report

Date: 2026-11-24. Your decisions are recorded in `dictionary/DECISIONS.md` under "2026-11-23: Part 5c approved; decisions on its report". The trial-call rule is in `CLAUDE.md` and the work order. Part 5c was pushed to GitHub (`d036993..a9530ec`) after a history check: no keys, logs, data, session IDs or email addresses, and the only author is your no-reply address. This work is committed locally and not pushed.

## Summary

| Item | Done | Example |
| --- | --- | --- |
| 1. Periods that start in the years asked | yes | Yale's Pell share "since 2015" shows nine years, aid years 2015-16 to 2023-24. "Interpreted as" names the first and last periods. |
| 2. Trend expectations | yes | The 17 rows and log 4.5 expect a trend. The grader counts a table by year, or a ranking or list by change, as a trend. |
| 3. A single earlier year | yes | Yale's bachelor's degrees in 2014-15: 1,327, from the 2015-16 release, in the usual one-year layout, with "Figures from the IPEDS 2015-16 release". A year not loaded, such as 1990, is declined, and the latest year is offered instead. |
| 4. The 13 messages | yes | Approved as written. |
| 5. Ranking and listing by change | yes | "Which Connecticut schools grew enrollment the most since 2015?" ranks by the change from fall 2015 to fall 2024. Ranking in one earlier year also works. |
| 6. Plain names | yes | For example "Net position (financial health section)" and "Total expenses deductions - Interest (until 2015-16)". IC TUITVRY1-3 are left unnamed and are now not set up. |
| 7. Questions wholly outside IPEDS | yes | One instruction line, worded narrowly. A question only partly outside IPEDS is still answered, as decided in Part 5.0. |

- **Tests:** 245 pass (234 before).
- **Haiku, one run:** 108 of 118 scored questions right or acceptable (91.5%); trend questions 15 of 21. Most misses come from five path defects that the run found. All five are fixed, with tests, but not re-measured, since the cadence allows one run. See below.

## How the rules are applied

**Item 3, one earlier year.** The model now gives the year it was asked for, even for a single year. For a year written as two ("2022-23"), it gives both, and the code then picks the release whose period falls inside July 2022 to June 2023. That gives fiscal year 2023, fall 2022 and aid year 2022-23. A single year such as "2023" takes the period that starts in it, so "books in 2023" gives fiscal year 2023, as your rule says.

Every operation works for one earlier year. Each reads that year's own measures, codes and schools.

**Item 5, ranking and listing by change.** The figure is the change between the first and last year chosen.
- A school counts when it is in the group in both years. With "today's schools only", it counts when it is in today's list.
- It must also have a value in both years. A missing value is never zero.
- A ranking leaves out values of zero or below, and keeps the ranking guard in both years.
- Breaks are marked on the year columns, and the answer says how many schools were left out, and why.
- In a list, a condition applies to the change. "Lost enrollment since 2015" lists the schools whose change is below zero.

Three note wordings are new, marked as drafts in `terms.csv`:
- "{ranked} of {schools} schools ranked by the change; {left} left out with no value in one of the years, or a value of zero or below."
- "{small} left out with fewer than {guard} in the denominator in one of the years."
- "{listed} of {schools} schools meet the conditions on the change."

**Item 6, plain names.** One pair is still shared: the for-profit revenue pair, F3B01 and F3D09, "Total revenues and investment return". It isn't one of the six financial-health pairs. My draft was "(sum of revenue sources)" for F3D09. The TUITVRY group is still listed as a shared name, as you decided.

## The question-set run

| | Part 5c, two runs | This run |
| --- | ---: | ---: |
| Scored (118) | 92.4%, 93.2% | **91.5%** (108) |
| Trend (21), now expected to be trends | 21 of 21, 20 of 21 under the old rule | **15 of 21** |
| Mean time per turn | 5.6 s, 5.8 s | 5.1 s (leaving out one turn that waited 9.4 hours overnight, probably while the computer slept) |
| Cost for 180 turns | $0.18 | $0.18 |

The 10 scored misses:

| Cause | Turns | Status |
| --- | --- | --- |
| Path (5) | "Yale's average net price for 2024-25" was declined, because no net price period starts in 2024 (it runs a year behind). | Fixed: a year that is the newest release's gets the usual latest-year answer, with the lag stated. |
| | "Total expenses", "endowment" and "tuition revenue" for "2022-23" showed fiscal year 2022. | Fixed: a year written as two is matched by its months, so fiscal year 2023. The tuition question also read the revenue per FTE, not the total (model). |
| | The 1990 decline offered no alternative, so "What can you show me instead?" had nothing to offer. | Fixed: the latest year is offered. |
| API (1) | Yale Pell since 2015: a connection error during the overnight wait. | It answered correctly in every other run. |
| Model (4) | 24.3 "both", 24.6 rank order kept as a list, 58.5 a bare list of names, 62.1 "hawaii". | Known from earlier runs; listed in the last report. |

Each path fix has a test. Because the run came before the fixes, the 91.5% includes the five path misses. Leaving out the fixed path misses and the connection error, the model's readings are right on 108 of 112 scored questions (96%).

Trend misses (6, all model readings):
- **1.1:** read as "what data exists", not a trend.
- **4.4:** "PhD-enrolling universities" not found.
- **11.1:** three cost-of-attendance years from one release, rather than a trend.
- **45.1 "Show a 10-year trend" and 45.2 "Show a longitudinal trend":** no measure is named, so no trend can be built. These two can only ever be a decline or a question back. I suggest they expect a clarifying question or a decline; that is your call.
- **64.1:** declined for want of a "Kansas community colleges" group. The earlier runs used the two-year reading.

Two other questions are now right because of these decisions: log 4.1 and the matching eval question (bachelor's degrees in 2014-15), and log 4.2 (Ivy League graduation rates for 2015). Their expectations said decline because the year wasn't loaded. They now expect an answer, noted in each row with decision 3.

## Line counts

The question path is 3,174 lines (3,007 before):
- `trend.py`: 541;
- resolve: 986, request: 309, fetch: 398, show: 152, interpret: 194.

## Open questions

1. **The F3B01 / F3D09 name:** use "(sum of revenue sources)" for F3D09?
2. **45.1 and 45.2:** expect a clarifying question or a decline, since no measure is named?
3. **The three new note wordings** for rankings and lists by change.
4. **Re-measuring the five path fixes:** they are tested, but there's no new run. A second run would cost $0.18. It can wait for the next change order, or run now.

Next: Part 5d, starting with the badly written test set for your review.
