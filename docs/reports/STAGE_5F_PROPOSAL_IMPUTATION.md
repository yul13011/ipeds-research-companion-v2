# Proposal: label imputed figures in school-level answers

Date: 2026-11-24. Proposal only (owner decision 4, Part 5f): nothing here is built.

## What it would do

When an answer shows a figure for a named school, and IPEDS imputed that school's data for the survey component the figure comes from, the answer carries a note. For example:

> IPEDS estimated Barry University's fall enrollment figures for Fall 2024 because the school did not report them (carried forward from its previous report).

Group figures, rankings and lists would not carry the note. The group figures add up IPEDS's published values, imputed ones included, as now. Two things would mark this in those answers: the imputation concept already says imputed figures are included, and the group note could say how many schools in the group were imputed (an option, below).

## Where the flag comes from

- **The FLAGS table** has one imputation column per survey component, for each school and year:
  - IMP_IC (institutional characteristics), IMP_ADM (admissions), IMP_EF (fall enrollment), IMP_E12 (12-month enrollment), IMP_C (completions);
  - IMP_GR, IMP_GR2 and IMP_OM (graduation rates and Outcome Measures);
  - IMP_SFA (student aid), IMP_COS1 and IMP_COS2 (cost), IMP_HR (staff), IMP_F (finance), IMP_AL (libraries).
- **Its codes** are in the codebook (VALUESETS):
  - 1 = carry forward (the school's previous report);
  - 2 = nearest neighbor (a similar school's report);
  - 3 = group median;
  - 4 = carry forward and nearest neighbor mixed;
  - 5 = ratio adjustment.
  - -2 (not applicable) is already a missing value.
- **These flags cover whole-school nonresponse**: the school did not submit that component.
- **A more detailed flag, per figure, is not loaded.** It is the X-prefixed column beside each variable (for example XAPPLCNM beside APPLCNM, 1,498 of them in 2024-25). The data build dropped these columns in Stage 1. Labelling figure by figure would mean reloading them: a change to the data build, about 1,500 more columns per release, and a full rebuild. I don't recommend it for now.

**How a table finds its flag:** a new column in year_meaning.csv, `imputation_flag`, naming the FLAGS column for each table. For example EFA, EFB, EFC, EFD and DRVEF use FLAGS.IMP_EF; F_F1A, F_F2, F_F3 and DRVF use FLAGS.IMP_F. This works the way `parent_child_flag` already does for related-campus notes (50 of the 59 tables have one). I would draft the 59 rows for your review; a few tables, such as HD and the Carnegie columns, have no imputation flag.

## How many answers it would affect

Few. Schools in the national universe with any imputed component:

| Release | Schools |
| --- | --- |
| 2015-16 to 2023-24 | 45 to 70 each year (all schools, not only the national universe) |
| 2024-25 | 61 of the national universe, among them 24 for fall enrollment, 18 for staff, 15 for finance, 9 for graduation rates, 7 for student aid and 6 for completions |

So a school-level answer gets the note only when the school is one of these few dozen and the figure is from the imputed component. The 2024-25 examples for fall enrollment include San Bernardino Valley College, Barry University, Edward Waters University and Southeastern University. In a trend, each year's own flag decides, so a school imputed in one year gets the note for that year only.

## The wording

Two message rows in terms.csv, so you can change them:
- **"imputed"**: "IPEDS estimated {school}'s {subject} figures for {period} because the school did not report them ({method})."
- **The {method} wording**, one row per code:
  - 1: "carried forward from its previous report";
  - 2: "taken from a similar school";
  - 3: "the median of similar schools";
  - 4: "carried forward and taken from a similar school";
  - 5: "adjusted from earlier figures".
- **{subject}** comes from year_meaning.csv's existing `subject` column (for example "Fall enrollment", "Finance").

**Option:** for group answers, one line such as "IPEDS estimated the figures of 3 of these 120 schools because they did not report." This needs one count per answer. I'd leave it out unless you want it.

## What it would add

| Piece | Change | Size |
| --- | --- | --- |
| year_meaning.csv | new column `imputation_flag`, 59 rows filled (draft for your review) | dictionary |
| terms.csv | the "imputed" message and five method rows | dictionary |
| build_dictionary.py | check that each named flag column exists in FLAGS | about 3 lines |
| resolve.py | read the column into the plan, as `parent_child` is read | about 3 lines |
| fetch.py | for each school shown, read its flag for the year shown and add the note (beside the related-campus note) | about 12 lines |
| Tests | a school imputed in 2024-25 gets the note; a reported school and a group answer do not; a trend notes only the imputed year | about 30 lines |

About 18 lines in the question path, no new step, and no model change. It would cost one fast dictionary rebuild and one question-set run.

## Decision for you

Build it in Stage 5 or in Stage 6, with or without the group-answer option.
