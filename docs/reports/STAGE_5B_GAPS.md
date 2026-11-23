# Stage 5, part 5b: gap list (the dictionary across years)

Date: 2026-11-22. Nothing has been loaded or changed in the dictionary. This list is drawn from the ten-year data and waits for your answers. The working files are in `docs/reports/stage5b/`, made by `scripts/gaps_5b.py`, `scripts/per_year_checks.py` and `scripts/year_rules_draft.py`.

## What the data shows (no decision needed)

| Check | Finding |
| --- | --- |
| Measures with data in each year (`measure_years.csv`) | Of 762 set-up measures, 411 have data in all ten years. 117 have data in 2024-25 only, mostly the reorganised cost and aid tables (see decision 2). The rest start or stop part-way. |
| Dictionary columns missing in some year (`columns_by_year.csv`) | 365 of the 815 columns the dictionary names are missing in at least one year. The main groups: the cost and aid tables (2024 only), Outcome Measures derived (from 2017), 12-month enrollment derived (from 2020), "another gender" columns (from 2022), and Carnegie columns. |
| Cells written with a fixed year (`fixed_years.csv`) | 113 cells: 52 periods in `year_meaning.csv`, 18 measure periods and 42 measure titles in `measures.csv`, and 1 caveat |
| Summary-to-detailed links, year by year (`per_year_checks.csv`) | All links that exist in a year pass in that year: 54 of 54 from 2020-21, and 33 of 33 before. The other 21 are 12-month enrollment links whose measures start in 2020-21. |
| Breakdown sets, year by year | From 2020-21 they pass as in 2024: 214 to 221 loaded, against 223. Before 2020-21, two sets fail: "Awards by level" and "Fall enrollment by level". Other failures are tables with no data that year (dual enrollment before 2023-24; enrollment by major in odd years). |
| Category rows, year by year | 2015-16 to 2019-20 fail on 12-month enrollment (EFFY): its level is keyed by a different column, EFFYLEV, before 2020-21. |
| Parent and child flags | Present in every year (10 to 12 survey components), so each year's own flags can be used |

The school directory over time (`directory_by_year.csv`):

| Year | Schools | National universe | With an IPEDS comparison group | Gone since the year before | New | Renamed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2015-16 | 7,647 | 7,021 | 2,420 | | | |
| 2016-17 | 7,521 | 6,606 | 2,365 | 318 | 192 | 162 |
| 2017-18 | 7,153 | 6,502 | 2,367 | 496 | 128 | 168 |
| 2018-19 | 6,857 | 6,138 | 2,326 | 468 | 172 | 184 |
| 2019-20 | 6,559 | 5,999 | 2,289 | 428 | 130 | 139 |
| 2020-21 | 6,440 | 5,916 | 2,292 | 262 | 143 | 146 |
| 2021-22 | 6,289 | 5,839 | 2,305 | 223 | 72 | 167 |
| 2022-23 | 6,256 | 5,783 | 2,304 | 162 | 129 | 116 |
| 2023-24 | 6,163 | 5,686 | 2,293 | 186 | 93 | 98 |
| 2024-25 | 6,072 | 5,626 | 2,845 | 162 | 71 | 60 |

The national universe is built from each year's own directory with the same rule, as you decided in the plan. It matches NCES for 2024-25 (5,626). Checking the earlier years against the NCES trend files is part of loading. The directory also records closures and mergers (CLOSEDAT, DEATHYR, NEWID).

## Decisions needed

### 1. Year rules as patterns counted from the release year

I propose writing every period with pattern words:
- `{Y}` is the release year;
- `{Y-1}` and `{Y+1}` count from it;
- `{Y:yy}` gives the last two digits.

| Table or measure | Today | Pattern | Filled in for 2015-16 |
| --- | --- | --- | --- |
| DRVEF and the other fall tables | Fall 2024 | Fall {Y} | Fall 2015 |
| C_A and the other July–June tables | July 1, 2023 - June 30, 2024 | July 1, {Y-1} - June 30, {Y} | July 1, 2014 - June 30, 2015 |
| COST1 and the other academic-year tables | Academic year 2024-25 | Academic year {Y}-{Y+1:yy} | Academic year 2015-16 |
| Net price (COST2_NETPRICE.NPGRN2) | 2023-24 | {Y-1}-{Y:yy} | 2014-15 |

All 70 period cells convert, and each pattern reproduces today's 2024 text exactly (`year_rules_draft.csv`). Graduation-rate entering cohorts are already counted back from the release year.

- **1a.** Approve the pattern words and the conversion of the 70 cells?
- **1b.** The 42 measure titles that contain a year (for example "Tuition and fees, 2024-25"). For an earlier year, I recommend showing that year's own codebook title, since IPEDS retitles them each year. The dictionary title stays as the 2024 one.

### 2. The cost and aid tables reorganised in 2024-25 (`cost_aid_map.csv`, `cost_aid_values.csv`)

The 605 variables of the new tables (COST1, COST2_FINANCIALAID, COST2_NETPRICE, SFA and DRVCOST) were matched to the old ones (IC_AY, IC_PY, SFA_P1, SFA_P2, DRVIC and IC). Matching is by title and year first, then by name and title.

| Match | Variables |
| --- | ---: |
| Same title and same aid year | 239 |
| Same name and title (the year digit in the name moves with the release, for example 2023-24 tuition is CHG1AY3 in 2023-24 and CHG1AY2 in 2024-25) | 320 |
| Same title, different name | 1 |
| Same name, different title: check (application fees and "provides housing", whose wording changed) | 3 |
| New in 2024-25, no earlier match | 42 |

The 42 new ones include:
- the Title IV net price for all incomes (NPIS40–42, NPT40–42). Before 2024-25, IPEDS published this net price only by income band, so **the app's "Title IV students" net-price reading has no earlier years**;
- total cost of attendance by aid group;
- the off-campus-with-family food and housing charge;
- part-time fees;
- application-fee waivers;
- FAFSA questions.

**Same aid year in both releases.** For the 239 variables where the 2023-24 release and the 2024-25 release report the same aid year, 2.9% of school values differ:

| Table | Values compared | Differ | Share |
| --- | ---: | ---: | ---: |
| COST1 (published charges) | 171,433 | 5,359 | 3.1% |
| COST2_FINANCIALAID | 325,665 | 6,185 | 1.9% |
| COST2_NETPRICE | 50,213 | 4,672 | 9.3% |
| DRVCOST | 10,057 | 123 | 1.2% |

Where net price differs, the median gap is 7.5%; 40% of gaps are within 5%, and the 90th percentile is 41%. Schools revise earlier years' figures in the next release. Examples are in `cost_aid_values.csv`.

- **2a.** Approve the mapping, so that trends run 2015-16 to 2023-24 on the old tables and 2024-25 on the new? The 3 "check" variables and the 42 new ones would be listed as they are.
- **2b.** When two releases report the same aid year, which value counts? I recommend each release's own current year only: the figure as first published for that year, not the later revision. Each year then comes from one release, as in NCES's trend tables. The alternative is the latest revision, which is newer but mixes releases.

### 3. A year in which IPEDS did not collect a measure

In a trend, that year shows as a gap, never zero (as agreed). Approve a message row: "IPEDS did not collect {what} in {year}." The years each measure is available are worked out from the data, so they need no dictionary row.

### 4. Category codes that change across years (`code_changes.csv`)

| Column | Change | Effect |
| --- | --- | --- |
| C_A CIPCODE (field of study) | CIP 2020 codes from 2020-21 | Field-of-study trends crossing 2019-20 to 2020-21 |
| C_A AWLEVEL, C_C AWLEVELC (award level) | Certificate levels 20 and 21 (under 12 weeks; 12 weeks to under 1 year) from 2020-21 | "Awards by level" fails before 2020-21 |
| EFA EFALEVEL (student level) | Codes differ before 2022-23 | "Fall enrollment by level" fails before 2022-23 |
| EFFY level | A different column (EFFYLEV) before 2020-21; four codes missing in 2020-21 and 2021-22 | 12-month enrollment by level before 2022-23 |
| OM OMCHRT (Outcome Measures cohorts) | Cohort codes 1–4 in 2015-16 and 2016-17; 10–52 from 2017-18 | Outcome Measures trends across 2017-18 |
| S_OC, EAP, S_IS, S_NH (staff categories) | Faculty-status codes 44/45 and graduate-assistant categories changed after 2015-16 | Staff trends across 2016-17 |
| GR GRTYPE | Code 1 absent through 2022-23 | Minor; to check |
| "Another gender" columns (ADM, enrollment, completions) | Added from 2022-23 | Measures start in 2022-23; totals unaffected |
| Carnegie (HD) | 2025 classification (R1, R2…) in 2024-25 only; 2021 basic in 2021-22 to 2024-25; older editions before | See decision 6 |

- **4a.** I propose that category rows in `category_codes.csv` gain a "years" column (for example "2015-2019"). A breakdown set or default row then uses each year's own codes, and the 12-month enrollment keys work before 2020-21. Approve?
- **4b.** Field of study across the CIP 2020 change: show the trend with a break note and no crosswalk for now? A CIP 2010→2020 crosswalk could come later.

### 5. A comparability-breaks table

I propose a new dictionary file, `comparability_breaks.csv`, with these columns:
- scope: a table, a measure or a breakdown set;
- first_year: the first year under the new definition;
- what_changed;
- note_shown;
- source.

When a trend's period crosses first_year, the note is shown and the year is marked. Data is never hidden, as you decided. Approve the file?

Candidate breaks to draft, with where each comes from. I'll confirm the codebook wording when drafting, and you review the list before it's used.

| First year | What changed | Source |
| --- | --- | --- |
| 2015-16 | Outcome Measures begins (cohorts by full- and part-time attendance only) | NCES IPEDS overview (2019), p. "Outcome Measures" |
| 2016-17 | Finance: detailed natural-expense categories dropped, except salaries and wages | Overview, Finance section |
| 2016-17 | Staff categories revised (faculty-status codes, graduate-assistant categories) | 2015-16 and 2016-17 codebooks (S_OC, EAP) |
| 2017-18 | Outcome Measures: all schools report a full-year cohort; Pell and non-Pell subcohorts; new cohort codes | Overview; codebook OMCHRT codes |
| 2020-21 | Completions: CIP 2020 field-of-study codes; new certificate award levels | 2020-21 codebook (CIPCODE, AWLEVEL) |
| 2020-21 | 12-month enrollment: new level codes and derived measures, distance education added | 2020-21 codebook (EFFY, DRVEF12) |
| 2020-21 | Finance forms: new lines (about 25 to 31 per form), to check for pandemic-relief revenue (HEERF) | 2020-21 codebook (F_F1A, F_F2, F_F3) |
| 2022-23 | "Another gender" category added | 2022-23 codebook (ADM, EF, C) |
| 2024-25 | Cost of attendance: "food and housing" replaces "room and board"; a new off-campus-with-family housing charge; cost and aid tables reorganised | 2024-25 codebook (NEWVARIABLES, COST1) |
| 2024-25 | Carnegie 2025 classification, a new scheme | 2024-25 codebook (HD) |

- **5a.** Approve the new file?
- **5b.** Should the pandemic years (2020-21) get a caution note even where no definition changed? I'd leave them out of the breaks table, because a break means a definition change.

### 6. The school directory over time

- **6a. School names.** When a school's name changed during a trend (60 to 180 renames a year), show today's name with "(then: …)" for earlier years? Or each year's own name? I recommend today's name with the note.
- **6b. Closures and mergers.** For a school that closed or merged, show the gap after it left. Should the app say "merged into … in …" when the directory's NEWID says so? I recommend yes.
- **6c. "Its peers" in a trend.** Use the school's comparison group as submitted for each year, or today's group for every year? Only 2,293 to 2,420 schools had one before 2024-25, against 2,845 now. I recommend today's group for every year, stated, because peers are the school's current choice.
- **6d. Carnegie groups in a trend.** "Each year's own list" can't work for R1 and R2 before 2024-25, because the 2025 classification exists only then. I recommend that Carnegie groups use the classification named in the group row, as of 2024-25, for every year, stated in the answer. This would be an exception to the default rule of each year's own membership.

### 7. Year rules for the seven tables that exist only in earlier years

DRVIC, IC_AY, IC_PY, SFA_P1, SFA_P2, IC_PCCAMPUSES and GR_GENDER. Approve that I draft their `year_meaning.csv` rows in the pattern form, following the 2024 tables they correspond to? For example, SFA_P2 net price one year behind, and GR_GENDER cohorts as GR.

### 8. Rates tested in every year

The NCES trend files have figures for most rate measures across the ten years (graduation rates q19–21, retention q32–33, aid q34–37, admissions q101–103 and others). I'll test every rate in every year where NCES has a figure, after loading. Nothing to decide, unless you want years without an NCES figure checked another way.

## Where existing code does not yet follow the version 3 habits

| Habit | State |
| --- | --- |
| 1. Each operation a clean function, structured input and output, no chat-page code | Mostly. The operations in `fetch.py` take a plan and return a result, with no chat-page code. `answer.py` mixes conversation state, logging and page building, which would need separating. |
| 2. Every result carries its source (table, year, definition, statements) | Partly. The plan carries each measure's table, period and statements, and the page has definitions. But a result's rows do not carry their source in a structured form. |
| 3. The number check as a general component | Not built yet (part 5e) |
| 4. "What data exists" as a self-contained step | Partly. It runs inside the question path (`resolve.topic_plan` and `fetch.topic`) and cannot yet be called on its own. |
| 5. Logs record a conversation identifier | Not yet: the question log has no conversation ID. It is a small change, in the log step. |

None of these are being fixed in this part unless you say so.
