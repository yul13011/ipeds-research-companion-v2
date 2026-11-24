# Stage 5, part 5d: understanding any phrasing

Date: 2026-11-24. Decisions are in `dictionary/DECISIONS.md` under "2026-11-24: decisions on the AI's own search report". Earlier Part 5d reports cover the test set, the meaning-search comparison and the AI's own search (`STAGE_5D_MEANING_SEARCH.md`, `STAGE_5D_AI_SEARCH.md`). Committed locally; nothing is pushed.

## Summary

- **The scorecard, two end-of-part runs on Haiku with the AI's own search:**

  | | Run 1 | Run 2 | Range |
  | --- | ---: | ---: | --- |
  | Scored questions (118), right or acceptable | 109 (92.4%) | 111 (94.1%) | **92.4% to 94.1%** |
  | Badly written set (56) | 54 (96.4%) | 53 (94.6%) | 94.6% to 96.4% |
  | Trend questions (21) | 15 | 17 | |
  | Cost for 236 turns | $0.251 | $0.255 | |

  For comparison, before the AI's own search the badly written set was 68%, and with the search alone (last report) 89%.
- **Group misses, measured again:** after the dictionary fix, the right group reaches the shortlist in **14 of 14** badly written questions, on the word search alone. That was 6 of 14 before; meaning search reached 11 of 14. That's the result for your fastembed decision.
- **School names:** RTI, "is rti a real college", BU, U of M, WSU and OSU now always go to the school picker, with the nearest names; another school is never substituted. Nicknames that mean one school (UConn, UMich, Mizzou) still resolve.
- **Near-duplicate measures** are grouped on the shortlist, judged from the dictionary's own subgroup labels.
- **The grader checks groups** as well as measures and schools.
- **Tests:** 272 pass. The question path is 3,401 lines (3,250 before).

## What was built for each decision

**1. Group misses (dictionary first, as you asked):**
- **20 system abbreviations** as `synonyms` rows in `school_groups.csv`: CUNY, SUNY, UNC, UC, Cal State/CSU, UT System, Texas A&M System, UW System, USG, PASSHE, TBR and others. The build stops if a synonyms row names a group that doesn't exist.
- **A system or one school:** nine `system or school` rows in `school_nicknames.csv`: UNC, Texas A&M, University of Texas, Minnesota, Wisconsin, Colorado, Illinois, Tennessee. When the question uses one of these names, both the system and the school go on the shortlist. If the request uses one and not the other, the app asks: '"unc" can mean the system or one school. Which did you mean?'
  - It doesn't ask when the question names the school in full: "unc chapel hill" has words beyond the system's name.
  - It doesn't ask when only the model's own search words contain the name: "tamu" searched as "Texas A&M University" asked once in run 1. That was fixed after the run, with a test.
- **Why "comunity colleges in texs" missed. Two causes, both general:**
  1. A four-letter word was corrected only when two letters were swapped, so "texs" (a missing letter) was never read as "texas". Now a missing letter is allowed too.
  2. The group the dictionary calls "community colleges" (public two-year) ranked 108th among groups. Dozens of systems whose names contain "Community College" scored higher, because a group's curated words counted no more than words in a name. The search now takes the best groups by their own dictionary words and the best by their names, and merges the two lists. So "Public, 2-year" and "State: Texas" both reach the shortlist.

**2. Time limits:** recorded in `DECISIONS.md` and the work order: up to 20 seconds when the AI searches, 10 seconds otherwise. The Part 5e status line will show the search step.
- **Run 1:** the 21 searched turns had a median of 9.1 s and a maximum of 15.1 s. Eight other turns went over 10 seconds, at most 11.7 s.
- **Run 2:** the 24 searched turns had a median of 9.0 s and one over 20 seconds (21.6 s). Six other turns went over 10 seconds, at most 14.8 s.

  These are API waits, not app time.

**3. The grader checks groups:** `expectations.csv` has a new `groups` column, filled for the badly written set. A request counts as right only when it holds every expected group.

**4. School names:**
- **An instruction line:** a nickname that means one school is that school. Only a name several schools share, or one no listed school has, gets no school.
- **Shared abbreviations:** `school_nicknames.csv` kind `ambiguous` lists the schools each one stands for (BU, U of M, WSU, OSU). The app always shows the picker for these, whatever the model chose.
- **A decline that names an unclear school** becomes the picker. The picker offers the nearest names, misspellings allowed: "RTI" offers Rochester Institute of Technology first.
- **A "direct" nickname** resolves even if the model leaves the school empty.

**Near-duplicate measures:**
- **What counts as a near-duplicate:** two measures in one table whose names are the same once the words of the person-subgroup labels are taken out. The subgroup sets (gender, race and ethnicity, Pell status) and the total words are listed in `terms.csv`.
- **What the shortlist shows:** the best-scoring member, with the others named beside it ("also by subgroup, not listed: women, men, Asian…"). The model can search for one.
- **Example:** "graduation rate at Yale" used to fill 4 of its top 5 places with the rate for Hispanic students, women, men and Asian students. It now lists the total once, with its 12 subgroup versions named beside it. "graduation rate for women" lists the women's rate.

## Found on the way

- **The first wording of the school-name line was too strong.** In the first end-of-part run, Haiku left clear nicknames (UConn, UMich, Purdue) without a school. Some pickers then had nothing to offer, because the picker didn't use the nickname table. The grader counted those clarifying questions as acceptable, which hid it. I stopped the run, set it aside (`haiku_5d_overcautious`), fixed the line and the picker with tests, and ran both runs again.
- **Two misreadings that recurred across three runs, fixed generally before the final runs:**
  - "revenue from tuition and fees" was read as the per-student figure. The synonym "tuition revenue" was on the per-student measure, and the three totals had none; it is now on the totals.
  - "2023-24" was written as 2022-23 for net price. An instruction line now says years are copied as written, never shifted for a measure reported a year behind. In both final runs the year was right.
- **Groups made from a column's values** (states, systems) carry their names only in the group name. A first version of the group weighting dropped "State: Texas" from "public four-year colleges in Texas"; the merged lists fixed that.
- **"wsu tehc"** lost WSU Tech once the shared abbreviation "wsu" fed its five schools' names into the school search. Those names are now for the picker only.

## Wrong readings in the final runs

| Turn | Run 1 | Run 2 | Cause |
| --- | :---: | :---: | --- |
| "salary of profs at wayne st" | x | x | **Path:** the picker's nearest-name search doesn't read "st" as "state", so Wayne State isn't offered. Not fixed: see question 2. |
| 1.1, 11.1 (trend questions read as one year or "what data exists") | x | x | model, known |
| 14.3 combined ranking | x | x | model, known |
| 24.3 "both"; 45.1 and 45.2 (no measure named) | x | x | model, known |
| "total expenses" read as core expenses | x | x | model, recurring in these two runs |
| "tuition revenue" for Yale on another form's line | x | x | model: the total is found now, but on the public or for-profit form. See question 3. |
| Others, once each | | | model: 14.4, 55.1, 58.7, 60.4, fu_go_back.2, o50 degree-seeking Pell; "hi can u tell me abt stanford" (answered instead of asking); CUNY read with a coded column; the 1990 follow-up, read as the outside-IPEDS "years" topic, offered no alternative |

## Version 3 habits

No change. The new rules (system or school, shared abbreviations, near-duplicates) sit in the search and resolve steps as plain functions, driven by dictionary rows.

## Open questions

1. **fastembed:** groups now reach the shortlist 14 of 14 on the word search alone. I don't see a remaining case for it. Close it?
2. **Abbreviated words in school names** ("wayne st", "penn st", "st. olaf"): the fix is a dictionary table of word abbreviations used by the school search. "st" would mean "state" and "saint"; "u" would mean "university"; "coll" would mean "college". It's a new table, so it's your call.
3. **Finance measures by form:** "tuition revenue" and "total expenses" are each three measures, one per finance form. They are paired by kind of school only where a `terms.csv` reading pairs them, as net worth now is. Should I add the same pairing for tuition and fees revenue, total expenses and total revenues (dictionary rows, with your review)?
4. **"Level of student" in EFA** (LSTUDY) is a coded column with no category rows, so it can be picked as a figure. Should it get its category rows (it then becomes a row choice), or be marked not set up?
5. **The outside-IPEDS row "Years outside 2015-16 to 2024-25"** offers no alternative. Should that row offer the same figure for the years held?
6. **Near-duplicates:** the subgroup sets and total words are in `terms.csv`, as drafts for your review.
