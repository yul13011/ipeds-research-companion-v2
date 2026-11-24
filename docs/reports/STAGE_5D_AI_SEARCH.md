# Stage 5, part 5d: the AI's own search, and meaning search on top of it

Date: 2026-11-24. Your decisions on the comparison are in `dictionary/DECISIONS.md` under "2026-11-24: decisions on the meaning-search comparison". Committed locally; nothing is pushed.

## Summary

- **The version 2 environment is set up:**
  - `.venv` in the project, ignored by git;
  - `requirements.txt` with every version pinned exactly: 55 packages, the app's six (streamlit 1.58.0, anthropic 0.122.0, altair 6.2.2, pandas 3.0.3, numpy 2.5.0, openpyxl 3.1.5) and what they need. No fastembed.
  - The run commands in `CLAUDE.md` now use it. All tests pass in it, and your main Python environment is unchanged.
- **The AI's own search is built:**
  - When nothing on the shortlist fits, the model replies with a search instead of an answer. The app runs its own search on those words and asks again, with the results listed first. That happens at most twice.
  - Every search is logged with its words, what it added and its time.
  - The final answer can only use what was on the shortlist shown in the last call, so code still rejects anything a search didn't show the model.
- **Measured, with and without it (one run each, Haiku):**

  | | Without the AI's search | With it |
  | --- | ---: | ---: |
  | Scored questions (118), right or acceptable | 107 (90.7%) | **111 (94.1%)** |
  | Badly written set (56), right or acceptable | 38 (68%) | **50 (89%)** |
  | Trend questions (21) | 14 | 15 |
  | Cost for the 236 turns | $0.228 | $0.265 (+16%) |
  | Median time per turn | 6.1 s | 5.6 s |

  The gain comes from the turns where the model searched. Most other differences between the two runs are ordinary run-to-run variation (see below).
- **Meaning search on top of it** still adds right groups in 5 questions where the AI's search didn't help, all on the raw question. On the model's own search words it adds 1 group and no measures. Details below.
- **Tests:** 257 pass (249 before).

## How the AI's own search works

| Step | What changed |
| --- | --- |
| Request (`request.py`) | The reply format has a new kind, "search", and one plain text field for the search words. A trial call confirmed the API accepts the format. |
| Shortlist (`shortlist.py`) | `extend()`: the app's own search runs on the model's words. What it finds is put first, the shortlist the model already had follows (trimmed at the end where the tag ranges are full), and everything is tagged afresh. |
| Interpret (`interpret.py`) | One instruction line: when nothing on the shortlist fits, search for the missing item only, in plain words, before deciding to decline. The prompt shows "SEARCHES LEFT" and each earlier search with what it found. A search asked for with none left becomes a decline for want of a measure. |
| Answer and log (`answer.py`) | The final shortlist is the one checked and logged. Each question's log line records its calls, its searches (words, what each added, seconds) and the search time. `IPEDS_AI_SEARCH=0` turns the search off; that is how the "without" run was made. |

The model searched in 31 of the 236 turns (13%), and twice in 5 of them. Most of its search words are sensible, for example:
- "University of Missouri" for Mizzou;
- "New York University" for "nyu how much does it cost to go there";
- "total fall enrollment" for "harvard enrolment since 2015";
- "graduation rate total" for "michigan state grad rat";
- "University of California system" for "UC system admit rate".

## Shortlist hits and wrong readings, before and after

- **Shortlist hits** are counted on the shortlist the model last answered from, including what the conversation carried forward:

  | | Before | After |
  | --- | ---: | ---: |
  | Badly written set: the right measure | 34 of 43 | **39 of 43** |
  | Badly written set: the right group | 6 of 14 | 8 of 14 |
  | Full question set: the right measure | 25 of 25 | 25 of 25 |

- **Answers that changed on the turns where the model searched:**
  - **Wrong before, right after (10):** Mizzou tuition; "mizou vs umich vs uconn"; NYU's cost; UF and FSU; "harvard enrolment since 2015"; "michigan state grad rat"; "ivy leage enrolment"; the UC system; the PhD-enrolling comparison (a clarifying question now); and the SUNY question (now a clarifying question).
  - **Right before, wrong after (2):**
    - "What city is Smith College located in?" The model searched and found the city column, and the display crashed on a text value. That was a path defect, now fixed with a test; the answer is now "Northampton".
    - "is rti a real college": the model answered RIT's directory status without saying that RTI International is not a college.
- **Differences on turns with no search** are run-to-run variation, about as many better as worse. For example, the net-price question read "2023-24" as 2022-23 in one run and correctly in the other.
- **Wrong readings left in the badly written set (6), all model readings:**
  - "RTI graduation rate": it searched, then declined without offering RIT.
  - "is rti a real college": as above.
  - "is miami dade the biggest community college": declined after searching.
  - "uiuc intl students": it found U.S. Nonresident enrollment but declined.
  - "U of M graduation rate": it chose Michigan; the picker was expected.
  - "comunity colleges in texs retention": declined; its search didn't bring up the public two-year group.

## Time and cost

- **The search step itself** takes 0.07 s (median). The cost is the extra model call.
  - A turn with a search has a median of 9.6 s, against 5.3 s without; 13 of the 31 searched turns took over 10 seconds (at most 20.1 s).
  - That is above your limit for hard questions (under 10 seconds).
- **Cost:** a searched turn costs about $0.0021, twice a turn without one ($0.0010). Over the whole set, the search adds 16% ($0.228 to $0.265 for 236 turns).
- **The median over all turns fell slightly** (6.1 s to 5.6 s). That's run-to-run variation in the API's speed, not the search.

## Meaning search on top of the AI's own search

This was run in the throwaway fastembed environment, from the logs of the run with the search. The question: does meaning search find a right measure or group that the final shortlist lacked? The closest 10 measures and 5 groups were checked in two variants.

| | On the raw question | On the model's own search words |
| --- | ---: | ---: |
| Right measures it adds (badly written set, 4 still missing) | 1 (Penn State undergraduates) | 0 |
| Right groups it adds (badly written set, 6 still missing) | **5** | 1 |
| Right measures it adds (full set, none missing) | 0 | 0 |

The five groups are the CUNY system (twice), the Cal State system, the UNC system and the public two-year group for the Texas community colleges question. In those questions the model didn't search: it saw schools named CUNY or UNC on the shortlist and took them to fit, or asked a question. So meaning search on the raw question finds groups the AI's search doesn't reach. On the model's search words it adds almost nothing, because the model's words already find what they name.

Per-question results are in `docs/reports/stage5d/meaning_on_top.csv`.

## Found on the way (each fixed, with a test)

- **A text value crashed the display** ("Northampton"). The search makes text columns, such as a school's city, reachable.
- **A future year** ("graduation rate in 2030") was answered with the latest year. The newest-year fallback from the last change order caught any year past the latest release. It now catches only the latest release's own year, and 2030 is declined.
- **An entering cohort beside another measure** ("the 2016 entering cohort", with bachelor's degrees asked for instead). The cohort rule was taken from the first measure, which had none. It is now taken from the first measure that has one.

The last two fixes came after the run with the search had started, so those two turns still show the old behaviour in it.

## Version 3 habits

- No change. The search is a clean function (`shortlist.extend`), called through a parameter passed to the interpret step, with no page code inside it.
- The question path is now 3,250 lines (3,174 before).

## Open questions

1. **fastembed:** it would add groups on the raw question (5 of the 6 group misses left), and almost nothing for measures. Merging the closest groups into the word shortlist would cost about 18 ms per question and 169 MB of packages. Your call.
2. **Time on searched turns:** 13 of 31 went over 10 seconds. Two options:
   - accept it for searched turns only, as the price of finding the item;
   - turn the effort down for the second call. That's a proposal, not built: it touches the interpret step only.
3. **The badly written set's group expectations:** the grader checks measures and schools, not groups. I checked the group questions by hand (two answers listed campuses instead of the system and were corrected to wrong). Should the grader check groups too? It would be a small change to `stage4_grade.py`.
4. **"RTI" and "U of M"** still go wrong. Both are about what the app says when no school or a wrong school fits. A line in the instructions (offer the nearest school by name, never answer for a school the user did not name) would be the general fix. Shall I propose the wording?
