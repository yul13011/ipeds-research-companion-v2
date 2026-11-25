# Stage 6, part 6.0: review point (the earlier-year columns draft)

Date: 2026-11-25. This stops at the review point you set for Part 6.0, before anything uses the draft. Nothing is loaded and the app is unchanged. Done before the draft:
- Your decisions are recorded in `dictionary/DECISIONS.md` ("Stage 6 begins").
- The grader knows the stages "6.0" and "7".
- The owner questions for items 46 and 47 are re-marked stage 7, in `docs/owner_questions.csv` and the expectations.

## What the draft is

The draft holds two new columns for `measures.csv`, made by `scripts/earlier_year_draft.py` (new). The file is `docs/reports/stage6/earlier_year_draft.csv`, one row per measure: table, variable, title, period, the two new columns, and whether the script was sure.

- **`own_column`:** the release's own column for the same figure, written as TABLE.VARIABLE. For the own column itself, it names itself.
- **`years_back`:** how many years before the own column's period this column's period starts. The own column is 0.

**How the script decides.**
- **Families:** columns in one table whose names differ only in their last digit form a family, for example NPGRN2, NPGRN1, NPGRN0.
- **The own column:** in each family it is the one with the latest period. In the tuition and total-price tables (COST1, DRVCOST) that is the next academic year (CHG1AY3: 2024-25 in the 2024-25 release). In the aid, net price and other-campus tables it is the year before (NPGRN2: 2023-24).
- **A row would be marked unsure** if two columns of a family had the same period, if the last digit didn't run in the same order as the periods, or if the titles differed by more than the year.
- **Single-year figures are left out:** a figure with no other year in its table isn't an earlier-year column. There are 20: the guaranteed tuition and fee increases, the derived total prices (CINSON and the others), and the reported FTE figures in EFIA.

## Summary by table

**430 measures in 135 families:** 135 own columns and 295 earlier-year columns.

| Table (2024-25; in earlier releases) | Families | Own column | 1 year back | 2 back | 3 back | What |
| --- | --- | --- | --- | --- | --- | --- |
| COST2_FINANCIALAID (SFA_P2) | 70 | 70 | 70 | 70 | | grant and loan aid, counts and amounts, by income |
| COST1 (IC_AY) | 24 | 24 | 24 | 24 | 24 | tuition, fees, books, food and housing, other expenses |
| IC_PCCAMPUSES | 22 | 22 | 22 | 22 | | the same charges at other campuses (releases 2021-22 to 2023-24 only) |
| COST2_NETPRICE (SFA_P2) | 18 | 18 | 18 | 18 | | net price overall and by income, cost of attendance |
| DRVCOST (DRVIC) | 1 | 1 | 1 | 1 | 1 | derived tuition and fees (TUFEYR) |
| **Total** | **135** | **135** | **135** | **135** | **25** | |

**On the 411 in the proposal:** that count was every measure whose period starts before the release year. It included the six single-year guaranteed-increase figures, and it missed the 25 own columns whose period is the next academic year (COST1 and TUFEYR3). The family count, 430, replaces it.

## Rows where the script was unsure

**None.** Every family passed all three checks.

**One more check, beyond the script.** I compared each column's period with the year in its IPEDS codebook title, in every release that has it: 3,602 title-years. All agree except one column in four releases:
- GRN4G0 (number awarded grant aid, all income levels, three years back). Its titles in the 2018-19 to 2021-22 releases give the same year as its neighbour GRN4G1, for example "2016-17" in the 2018-19 release.
- **The figures settle it.** In each of those releases, GRN4G0 equals the own figure published three years earlier in 95-96% of schools, and the GRN4G1 figure beside it in only 4-5%.
- So those four titles are a codebook error, and the draft's period (three years back) is right. I'll add a note on this row of `measures.csv` when the columns are loaded.

## What the columns will give, once loaded

- **Trends** read each release's own column for each year.
- **Years before any release's own column,** from the earliest release's earlier-year columns, labelled "as reported in the 2015-16 release":
  - tuition and charges: 2012-13 to 2014-15;
  - net price and grant aid: 2012-13 and 2013-14;
  - other-campus charges: 2018-19 and 2019-20, labelled with the 2021-22 release, since that table starts there.
- **A single year inside the ten releases:** the figure its own release published.

## For you

1. Approve the draft as it is, or mark any rows to change, so the build can load the two columns.
2. **Other-campus charges** (IC_PCCAMPUSES) start only in the 2021-22 release. Under the rule, its earlier-year columns would supply 2018-19 and 2019-20 even though the releases for those years are loaded, because those releases have no such table. Is that what you want? Or should earlier-year columns be used only before 2015-16?
