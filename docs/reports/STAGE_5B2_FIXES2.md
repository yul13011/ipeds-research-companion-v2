# Stage 5, part 5b2: second change order before Part 5c

Date: 2026-11-23. Decisions are recorded in `dictionary/DECISIONS.md` under "2026-11-23: decisions on the Part 5b2 fixes report". The working cadence is recorded there and in `CLAUDE.md`. Your work-order edit is committed. Nothing is pushed.

## Summary

- **Item 1, charges by calendar:** done. Books and supplies, on-campus and off-campus food and housing, and on-campus and off-campus other expenses each pair their academic-year and program-year columns, for every year, through the calendar groups.
  - Test: Mount Holyoke's 2023-24 on-campus food and housing now shows $18,838 (it showed "no value").
  - Only "food and housing, on campus" can be found by the search, with the words "room and board", "food and housing" and "housing and meals". The other pairing rows are pairing only, so they don't crowd the shortlist (see "Found on the way").
- **Item 2, one measure per reporting form:** done, as a general rule.
  - A condition now uses each school's own form's measure, as figures already did. A list made with such a measure is grouped by form, and names each form's measure.
  - The answer carries the statement that the forms use different accounting standards, the pension note from the dictionary, and the fiscal year.
  - Test: the net-worth question lists 199 schools: 123 public (net position), 26 private nonprofit (total net assets) and 50 for-profit (total equity), inside the national universe. That matches the data.
  - Repeated identical conditions (the model sent one per form) now collapse into one.
- **Item 3, table subjects:** applied, with your two changes. The build writes each measure's shown name: the official title, or "subject: title" where titles are shared. Answers now say, for example, "Fall enrollment: Asian total" and "Award recipients: Asian total". 186 names are still shared (373 measures); the proposal is below.
- **Item 4:** the 6 rank headcounts are counts.
- **Also built:**
  - **Programs by field (CDEP):** the 39 field rows from completions, with Grand total as the default and a tested "Programs by field of study" breakdown. It picks a row in every year, and its 42 "no way to pick one row" flags are gone.
  - **Custom comparison groups:** kept as per school only; their 3 measures stay on the review list.
  - **"IPEDS gives no label for this code":** a coded answer whose code has no label shows the code, with this note.
  - **"IPEDS has no values for this measure: {what}.":** the answer for a measure no school has a value for in any year.
- **Tests:** 211 pass.
- **Haiku, one run (per the new cadence):** 108 of 116, 93.1% right or acceptable. The last two runs were 94.0% each.

## Found on the way (each fixed, with a test where it is code)

- **Coded values stored as decimals.** Some coded columns hold 1.0 where the codebook labels "1". Both the label check and the app compared them as text, so the app would have shown "1.0" instead of the label. Both now read 1.0 as code 1. Rechecked: 60 coded measures have codes without labels (62 before), none of them in 2024-25. So "IPEDS gives no label for this code" will first matter in trends.
- **The faster build had two flaws, both found on the real database:**
  - A change to one table's category rows stopped with an error when it reached other tables' breakdown sets.
  - A run that stopped part way had already loaded the new rows but had not marked itself "in progress". The next run compared the new rows with themselves and skipped the retest.

  The build now marks itself in progress before it changes anything, so a stopped run makes the next run a full rebuild. Two new equivalence tests cover these. The retest the database missed (programs by field) was then run.
- **The search must not read the subjects.** Once the shown names carried subjects, an enrollment question's shortlist filled with "Fall enrollment: Race/ethnicity unknown total" and its namesakes, and lost the right measure. The search was frozen, so it now matches on each measure's own name, and the subject is added only to the name shown to the model.
- **The new charge terms took shortlist places** by matching common words such as "and". They are now pairing-only rows, which the search doesn't read. The pairing works from the measure, so nothing is lost.

## The question set on Haiku (one run)

| | After decisions 1 and 2 (two runs) | This change order (one run) |
| --- | ---: | ---: |
| Right or acceptable | 94.0%, 94.0% | **93.1%** (108 of 116) |
| Wrong readings | 7, 7 | 8 |
| Time per turn (mean; slowest tenth) | 4.9-5.1 s; 8.8-9.9 s | 4.7 s; 8.0 s |
| Cost | $0.16 per run | $0.17 |

**Fixed this run:**
- the net-worth question (all three forms, grouped by form);
- Mount Holyoke's food and housing;
- the full/part-time staff question, now answered with counts (2,995 and 805) instead of a clarifying question.

**Wrong readings (8):**
- **Recurring across runs, which under your rule need a dictionary or instruction fix:**
  - "use the institutions in the example set" picks unrelated schools;
  - the dual-enrollment follow-up "both" can't be read;
  - "What is the universe with the lowest net cost?" is not found.

  See open question 2.
- **Once in this run:**
  - the dual-enrollment ranking listed schools alphabetically instead of by size;
  - one turn of the RIT conversation got the app's could-not-read reply;
  - the Hawaii opening turn was declined;
  - the ROI conversation's ranking turn;
  - "List every Yale student's name and GPA" showed the admissions GPA consideration beside the right statement.

## The 186 shared names: examples, for your review

The description rule (`scripts/name_suffix_draft.py`, not applied) takes, for each measure, the shortest run of words in its own IPEDS long description that its namesakes' descriptions lack, and adds it in brackets. It separates 182 of the 186 groups, but the words it finds vary a lot in quality:

| Measures that share a name | Description rule | Quality |
| --- | --- | --- |
| Financial aid, full-time first-time students: Average amount of grant and scholarship aid awarded, 2021-22 (GISTA0 / GRNTA0) | "(paying)" / "(private)" | Partly right: the real difference is public in-state against private |
| Net price: Average net price (income 0-30,000), Title IV, 2021-22 (NPIS410 / NPT410) | "(paying)" / "(private)" | As above |
| Published charges: Books and supplies 2021-22 (chg4ay0 / chg4py0) | "(full-time)" / "(entering)" | Misleading: the difference is academic year against program |
| Branch campuses: Books and supplies 2020-21 (PCCHG4AY0 / PCCHG4PY0) | "(full-time)" / "(entering)" | As above |
| Finance, for-profit: Total assets (F3A01 / F3G04) | "(assets is the sum)" / "(these)" | Poor: one is the balance sheet, the other a summary line |
| Finance, public (GASB): Net position (F1A18 / F1N04) | "(excess)" / "(these)" | Poor |
| Fall enrollment: Level of student (EFALEVEL / LSTUDY) | "(full-)" / none | Poor |
| GR200 BASTEND / L4STEND; IC TUITVRY1-3 | none found | Not resolved |

The groups by table: 105 in the aid tables (COST2_FINANCIALAID), 28 published charges (COST1), 24 branch campuses (retired), 18 net price, 8 finance lines, and 3 others.

**My recommendation instead: take the words from your approved pairings, not from the descriptions.**
- Nearly all these groups are the same figure for two kinds of school (academic year or program; public in-state or private). The pairing rows already name the two kinds: "Charges by academic year" and "Charges by program", "Public" and "Private, nonprofit or for-profit". So "Published charges: Books and supplies 2021-22 (by academic year)" and "(by program)".
- Today those rows cover 27 groups (the charges and net price). Pairing the aid-by-income measures the same way (public in-state with private, as for net price) would cover about 130 more. That's dictionary rows, and it would also let an aid question take each school's own measure, as net price now does.
- The branch-campus groups (24, retired variables) could be paired by calendar in the same way.
- About 10 would remain (finance lines that appear twice on a form, GR200, IC.TUITVRY). For those, I'd write plain names from the codebook for your review.

## Size

- **Question path:** 2,469 lines (2,418 before).
- **Build:** 1,535 lines (1,503 before).
- **Dictionary:** 48 charge pairing rows, 3 net-worth rows, 2 messages, 39 programs-by-field rows, the 6 units, and the two subject changes.

## Open questions

1. **The 186 shared names:** take the distinguishing words from the pairings (recommended above, with the aid and branch-campus pairing rows added), or apply the description rule as it is?
2. **The three recurring wrong readings:** may I fix them with instruction or dictionary lines before Part 5c? They are "the example set" (a follow-up that should keep the schools already named), the dual-enrollment follow-up "both", and "the universe with the lowest net cost" (a synonym on net price).
3. **The review list now has 80 measures:**
   - 60 coded measures with codes the codebook does not label (none in 2024-25);
   - 17 that never have a value;
   - 3 custom comparison group measures (per school only).

   Anything further on these, or are they settled by the two messages and your decision?

Part 5c waits for your go.
