# Stage 6, change order 1: two proposals (before the beta)

Date: 2026-11-25. Proposals only, as you asked (`dictionary/DECISIONS.md`, "Stage 5 approved"). Nothing here is built. They come from the trend gaps found after Part 5g. Two of the six new test questions check each one.

## Proposal a: the years a measure is held, and "which years do you have?"

**The problem.** A "what data exists" answer shows each measure's latest period only, for example "Percent admitted - total (Academic year Fall 2024)". So "Which years are available for Ivy League admission rates?" (log 1.1, a real user's question) is answered with one year, though the app holds ten. It fails in every run.

**What it would do.**
1. **A "Years held" column** in every "what data exists" answer: the first and last period held, and the number of releases. For example:
   - "Fall 2015 to Fall 2024 (10 releases)";
   - for graduation rates, "students who entered in fall 2009 to fall 2018 (10 releases)";
   - for a measure IPEDS added recently, "July 2022 to June 2024 (2 releases)", such as dual enrollment.
   - Gaps are named, for example "not collected in 2016-17".
2. **"Which years do you have for X?"** reads as a "what data exists" question for X. One instruction line: "Questions about which years are held are data_exists."
3. **When the question also asks for figures** ("Which years are available? Compare the latest available year"), the answer gives the years and offers the comparison as a button. The app already has these buttons (the "today's schools only" one, for example). The figures are not shown unasked.

**Where it comes from.** The build already records, for every measure, the releases that hold it (the `measure_years` table, 24,099 rows). Each release's period is the measure's own period pattern filled for that release, as the app does now for one year. Nothing new is needed in the dictionary.

**What it touches.**

| Step | Change | Size |
| --- | --- | --- |
| resolve.py (the data-exists plan) | the releases held and their periods, as one span with any gaps | about 10 lines |
| fetch.py / show.py | the "Years held" column; the offered comparison | about 8 lines |
| interpret.py | one instruction line | 1 line |
| terms.csv | one message row for the gap wording ("not collected in {years}") | dictionary |
| Tests | the column for a ten-year measure, a recent one and one with a gap; the offer; "which years do you have" reads as data_exists | about 30 lines |

**Cost:** one fast rebuild, a trial call, one question-set run. Expected to fix log 1.1 and the two new "which years" questions.

**One link to proposal b:** with b, net price and charges would also be held for a few years before 2015-16. The "Years held" column would then show them, marked as coming from a later release.

## Proposal b: trends from the ten releases, earlier-year columns only before them

**The problem.** Some tables hold a few earlier years as columns of their own:
- in release Y, net price for Y-1, Y-2 and Y-3 (NPGRN2, NPGRN1, NPGRN0);
- tuition and charges for Y down to Y-3;
- grant aid counts and amounts for three years.

When asked for a trend, the model can take these columns for one: "How has cost of attendance changed at the University of Chicago…" (log 11.1, run 2) was answered with three cost-of-attendance columns from the 2024-25 release (2021-22 to 2023-24), not the published cost across the ten releases.

**What it would do.**
1. **A trend always uses each release's own column for each year.** If the model names an earlier-year column (or several of them) in a trend, the code reads the release's own column across the releases instead, and says so. For example, NPGRN1 becomes NPGRN2 read from each release.
2. **Earlier-year columns are used only for years the ten releases do not cover:**
   - net price for 2012-13 and 2013-14, from the 2015-16 release's NPGRN0 and NPGRN1;
   - charges back to 2012-13.
   - Each such year is labelled "as reported in the 2015-16 release".
3. **A single earlier year inside the ten releases** (net price for 2021-22, say) comes from that year's own release, not from a later release's column. The answer is then the figure the release published, as NCES's trend tables and the benchmarks use.

**How the earlier-year columns compare with what the earlier releases published.** `scripts/earlier_year_columns.py` (new) compares every school-year from the 2016-17 to 2024-25 releases. The summary is in `docs/reports/stage5g/earlier_year_columns.csv`. The school-by-school detail (225,000 rows) goes to the untracked logs folder when the script runs, since it is data, not a result.

| Measure | Column in release Y | Against | School-years | Identical | Within 1% | More than 10% apart |
| --- | --- | --- | --- | --- | --- | --- |
| Net price, grant-aided, private (NPGRN) | NPGRN1 (Y-2) | NPGRN2 of release Y-1 | 31,915 | 86.7% | 88.5% | 5.8% |
| | NPGRN0 (Y-3) | NPGRN2 of release Y-2 | 27,194 | 79.1% | 81.8% | 9.7% |
| Net price, grant-aided, public (NPIST) | NPIST1 | NPIST2 of release Y-1 | 16,595 | 92.5% | 93.5% | 3.7% |
| | NPIST0 | NPIST2 of release Y-2 | 14,601 | 88.7% | 90.1% | 5.9% |
| Students awarded grant aid (GISTN) | GISTN1 | GISTN2 of release Y-1 | 16,613 | 98.1% | 98.2% | 1.2% |
| Published in-district tuition and fees | CHG1AY2 (Y-1) | CHG1AY3 of release Y-1 | 31,599 | 94.3% | 95.9% | 1.3% |
| | CHG1AY1 (Y-2) | CHG1AY3 of release Y-2 | 27,505 | 93.1% | 95.1% | 1.6% |
| Tuition and fees, derived (TUFEYR) | TUFEYR2, TUFEYR1 | TUFEYR3 of the earlier release | as tuition | 94.3%, 93.1% | 95.9%, 95.1% | 1.3%, 1.6% |

**Mostly the same figure, but not always.**
- **Big schools match exactly.** Yale's net price for 2022-23 is $26,044 in both the 2024-25 release's NPGRN1 and the 2023-24 release's own NPGRN2. Harvard, Ohio State and Front Range match too, and so does tuition at all four.
- **Where they differ,** a school has revised its figure in a later survey. Net price differs in 10 to 15% of school-years in every release, mostly at small schools, for example:
  - a cosmetology school: $5,739 later against $7,216 first published;
  - a rabbinical college: $18,161 against $13,791;
  - an adult school: $7,680 against $9,755.
- **So the choice matters for small schools.** A trend built from one release's columns can disagree with the same years read from each release, and with NCES's tables.

**Which measures are affected.** 411 measures in the 2024-25 release, all set up:

| Table (2024-25; earlier releases) | Measures with earlier-year columns | What |
| --- | --- | --- |
| COST2_FINANCIALAID (SFA_P2) | 210 | grant and loan aid counts and amounts, three years |
| COST1 (IC_AY) | 102 | tuition, fees and other charges, four years |
| IC_PCCAMPUSES | 66 | charges at other campuses, three years |
| COST2_NETPRICE (SFA_P2) | 54 | net price overall and by income, cost of attendance, three years |
| DRVCOST (DRVIC) | 13 | derived tuition and total price |

**What it touches.**

| Step | Change | Size |
| --- | --- | --- |
| measures.csv | two new columns for the 411 measures: the release's own column for the same measure (for example NPGRN1 → NPGRN2) and how many years back. A draft, made by a one-off script from the variable names and period patterns, for your review | dictionary |
| build_dictionary.py | check that each named column exists and has the stated period | about 8 lines |
| trend.py | in a trend, read the release's own column for each year; before 2015-16, the earliest release's earlier-year columns, labelled | about 20 lines |
| resolve.py | a single year inside the ten releases from its own release; several earlier-year columns of one measure named together become one trend | about 10 lines |
| terms.csv | one message row ("{years}: as reported in the {release} release") | dictionary |
| Tests | net price for Harvard over ten years; NPGRN1 named in a trend; 2013-14 net price from the 2015-16 release; a single year within the releases | about 40 lines |

**Cost:** your review of the 411-row draft, one fast rebuild, a trial call, one question-set run. Expected to fix log 11.1 and the two new questions on earlier-year columns.

**A decision for you inside b:** where the two figures differ, which one should the app show for a year inside the ten releases? My recommendation is the figure the year's own release published (as above). The other choice is the later, revised figure. That would fit "the latest data" but disagree with NCES's trend tables.
