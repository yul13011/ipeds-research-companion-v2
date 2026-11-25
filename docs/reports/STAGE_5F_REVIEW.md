# Stage 5, part 5f: review points (glossary parse, draft concepts)

Date: 2026-11-24. This stops at the two review points the work order sets for Part 5f. Nothing here is used by the app yet. Your decisions on the Part 5e report are in `dictionary/DECISIONS.md`, and Part 5e is pushed (`24bb550..e72dae9`); the drafts below are committed locally only.

## Your Part 5e decisions, done

1. **Finance pairings:** the 129 approved concepts are paired by form. Total assets on the for-profit form uses the balance-sheet line (F3A01). The rows are pairing-only, with no search words, so they never crowd the shortlist.

   The second pass is in `docs/reports/stage5e/finance_pairing_check.csv`: 61 matches marked "check", none paired.
   - **42 would complete an approved pair.** For example, public "Instruction - Current year total" joins "Instruction-Total amount"; public "Total expenses and deductions - Current year total" joins "Total expenses-Total amount"; private nonprofit "Federal appropriations - Total" and "State appropriations - Total" join their pairs.
   - **19 are new pairs.** For example, the three forms' financial-health "Total expenses" lines, which are matched only with each other.
   - **Some are weaker (similarity 0.75)** and worth a close look, such as public "Total expenses and deductions - Operations and maintenance of plant" against "Operation and maintenance of plant-Total amount".
2. **"penn state"** now suggests the main campus first in the picker; the other campuses still show.
3. **The worked year example** is in the instruction. Whether the misreading recurs will show in the next question-set run, and I'll tell you rather than add more lines.
4. **No written summary** for "what data exists" answers or definitions. Declines and clarifying questions never had one.
5. **Pushed** after the full rebuild (everything passes: 287 tests) and the history check, with your note on the outcome of Part 5d in the work order.

## Review point 1: the glossary parse

**How it was read:** `scripts/parse_glossary.py` uses `pdftotext`, which comes with Git for Windows, so nothing was installed. The PDF is a browser printout: the file stores each term before its definition, while the side-by-side layout puts definitions in a right-hand column. The parser uses both, together:
- a line found in the right-hand column is definition text, and anything else is a term (long terms wrap over two or three lines);
- lines holding both, in either order, are split where the definition's own line starts;
- page headers and page numbers are taken out.

The definitions are otherwise exactly NCES's text: lines are joined, nothing reworded.

**Result: 612 entries.** The checks flag entries whose term holds a sentence, starts in lower case, or appears more than once.
- **12 entries were not separated cleanly**, all listed with a proposed fix in `docs/reports/stage5f/glossary_parse_issues.csv`:
  - 5 where the definition's first line was read as part of the term: both "Adjustments to beginning net…" entries, both "Full-time equivalent (FTE)…" entries, and "Less-than-annual contract…";
  - 4 "(Carnegie)" class names whose first line went to the previous entry;
  - "Local appropriations, education district taxes, and similar support", split in two;
  - "Payments made on principal", which took the next entry's definition (Peer Analysis System);
  - "Yellow Ribbon Program".
- **1 more found by reading, not by the checks:** "Postsecondary institution", whose definition begins with the last word of the neighbouring term "Postsecondary education". So the checks don't catch every misalignment.
- **I propose** you, or I with your go, read a sample of entries against the PDF before the table is used. Three of the Carnegie fixes say "to confirm".
- **15 long terms** are kept as they are, because they really are long. For example: "Postsecondary award, certificate, or diploma (900-1,800 clock hours, …)" and "Community, Social Service, Legal, Arts, Design, Entertainment, Sports, and Media Occupations".

The parsed table is in `docs/reports/stage5f/glossary_parsed.csv` (term, definition, edition "2025-26", note). It moves into `dictionary/` once you approve the fixes; the build then loads it. I'll apply the fixes as a small corrections file the parser reads, so no definition text is typed in by hand.

## Review point 2: the draft concepts table

`docs/reports/stage5f/concepts_draft.csv`: 26 concepts. Each has:
- the words people use;
- a plain-English explanation (my draft, for your review);
- its source (the glossary entry, the overview page, or the app's own table);
- the evidence for choosing it;
- the app convention that goes with it;
- status "draft".

| Evidence | Concepts |
| --- | --- |
| Your Part 5f questions | FTE; adjusted cohort; retention versus persistence; published price versus net price; why net price is a year behind; graduation rate and transfer students; provisional versus final data; Title IV institution; the IPEDS comparison group; summer melt |
| Your Part 6 questions (choosing a measure) | fall versus 12-month enrollment; instructional staff versus faculty status; Pell as an income measure; graduation rate versus Outcome Measures; admission rate and selectivity |
| Words the app shows (Interpreted as, notes, definitions) | the national universe in this app; parent and child reporting; first-time full-time students; degree-granting; Carnegie classification; GASB and FASB finance forms; release year and data year; not reported versus not applicable; "private" in this app |
| How IPEDS works (the 2019 overview) | Title IV (page 1), the universe (page 8), branch campuses and parent reporting (page 2), imputation (page 11), provisional and final data (pages 10-11) |
| The question log | College Scorecard |

**Concepts not in the glossary**, where the explanation is mine and marked as such: persistence, provisional and final data, parent and child reporting, degree-granting, summer melt, College Scorecard. Your review of those wordings matters most.

## What comes after your review (not built yet)

- Load the glossary (with the fixes) and the reviewed concepts table into the dictionary.
- Check the dictionary's statements against the glossary and list any that contradict it.
- Explanation questions:
  - a small glossary section on the shortlist, at most three entries;
  - the order of sources (concepts table, glossary, dictionary, then general knowledge, labelled and logged);
  - the edition label;
  - the convention shown after the official definition.
- Tests: data questions whose words match glossary terms must still return data.

## Questions for you

1. Approve the 13 glossary fixes, and read a sample against the PDF?
2. Edit or approve the 26 concepts, especially the six not in the glossary.
3. The 61 finance matches marked "check".
