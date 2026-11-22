"""Draft of shorthand synonyms for the owner's review. Writes docs/stage4/shorthand_draft.csv; changes no table.

Each rule says which first-version measures (by ID, or by a pattern on the measure's name) and which category rows
(by a pattern on the label) a word would be added to, whether a measure already has the word, and whether the word
could mean two different things.
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "dictionary"

# word(s) | measure IDs or a name pattern (re:) | row label pattern (re:) or "" | two meanings? | note
RULES = [
    ("first-year; freshman; freshmen", "re:first-time", "re:first-time", "yes",
     "IPEDS 'first-time' means new to college; a first-year transfer student is first-year but not first-time. "
     "'first-year' also appears in 'first-year retention', which already has its own synonym."),
    ("FT", r"re:\bfull-time\b(?! equivalent)", r"re:\bfull-time\b(?! equivalent)", "yes", "Could be read as FTE."),
    ("PT", r"re:\bpart-time\b", r"re:\bpart-time\b", "no", ""),
    ("admit rate; acceptance rate", "DRVADM.DVADM01", "", "no", "Already on DVADM01; nothing to add."),
    ("selectivity", "DRVADM.DVADM01", "", "yes", "Also used for test scores or a Carnegie selectivity class."),
    ("applicants; apps; applications", "ADM.APPLCN", "", "no", "Fixes the Stage 4 shortlist miss ('Data extract: Applicants')."),
    ("admits; admitted students", "ADM.ADMSSN", "", "no", ""),
    ("matriculants; enrollees; yield count", "ADM.ENRLT", "", "no", "The Yale benchmark files call ENRLT 'matrics'."),
    ("yield", "re:yield", "", "no", "Already in the names; only DVADM04 has it as a synonym. Nothing needed."),
    ("persistence; persistence rate", "EFD.RET_PCF; EFD.RET_PCP", "", "yes",
     "In IR, persistence can also mean still enrolled anywhere (Outcome Measures 'still enrolled' / 'enrolled elsewhere')."),
    ("completions; awards conferred", "C_A.CTOTALT; re:^(Associate's|Bachelor's|Master's|Doctor's|Certificates?)", "", "yes",
     "'completion rate' means graduation rate (already a 'graduation rate' word). Only the plural 'completions' is proposed."),
    ("completers", "C_B.CSTOTLT; re:^Number of students receiving", "", "no", "Students, not awards."),
    ("FTE; FTE enrollment", "DRVEF12.FTE12MN", "", "yes", "FTE also names staff FTE (library FTE staff, instructional FTE)."),
    ("COA; cost of attendance; sticker price", "re:^Total price", "", "yes",
     "'cost' alone is a term with readings (cost profile). COA and sticker price are already on CINSON only."),
    ("net cost", "re:^Average net price", "", "no", "Would have fixed the Stage 4 'universe with the lowest net cost' reading."),
    ("Pell rate; percent Pell", "SFA.UPGRNTP", "", "no", "'Pell' itself is already in every Pell measure's name."),
    ("low-income", "SFA.UPGRNTP", "", "yes", "Pell is a proxy for low income; IPEDS has no income measure. Not recommended."),
    ("endowment per student", "re:^Endowment assets.*per FTE", "", "no", "IPEDS divides by FTE enrollment."),
    ("faculty", "re:instructional staff|faculty", "re:instructional staff|faculty", "yes",
     "'faculty' is already a term with readings (instructional staff; staff with faculty status)."),
    ("professors; full professors", "DRVHR.SalProf", "re:^Professor", "yes",
     "Colloquially 'professors' means all faculty; in IPEDS it is one rank."),
    ("student body", "DRVEF.ENRTOT", "", "yes", "Often means characteristics (race, gender, age), not just the count."),
    ("census enrollment; fall census", "DRVEF.ENRTOT", "", "no", ""),
    ("SFR; S/F ratio; student faculty ratio", "EFD.STUFACR", "", "no", ""),
    ("dual enrollment; dual credit; concurrent enrollment; early college", "EFFY_HS.EFYTOTLT", "", "no", ""),
    ("eight-year completion; 8-year award rate", "re:receiving an award.*8 years|award - 8 years", "", "no", "Outcome Measures."),
    ("spending per student", "re:^Core expenses per FTE|Instruction expenses per FTE", "", "yes",
     "Core expenses per FTE or instruction expenses per FTE."),
    ("tuition revenue", "re:Revenues from tuition and fees per FTE", "", "yes", "Per FTE in the app; a total is not set up."),
    ("URM; underrepresented minority", "", "", "yes", "No IPEDS measure; it is a grouping of race categories. Proposed for outside-IPEDS or a future set, not as a synonym."),
]


def main():
    measures = [x for x in csv.DictReader(open(D / "measures.csv", encoding="utf-8")) if x["in_first_version"] == "yes"]
    rows = list(csv.DictReader(open(D / "category_codes.csv", encoding="utf-8")))
    name = lambda x: x["plain_name"] or x["title"]
    out = []
    for words, target, row_rule, two, note in RULES:
        hits = []
        for part in (p.strip() for p in target.split(";") if p.strip()):
            if part.startswith("re:"):
                hits += [m for m in measures if re.search(part[3:], name(m), re.I)]
            else:
                hits += [m for m in measures if f"{m['table']}.{m['variable']}" == part]
        ids = list(dict.fromkeys(f"{m['table']}.{m['variable']}" for m in hits))
        first = words.split(";")[0].strip().lower()
        have = sum(1 for m in hits if first in (m["synonyms"] or "").lower())
        row_hits = [r for r in rows if row_rule and re.search(row_rule[3:], r["label"], re.I)]
        out.append(dict(words=words, two_meanings=two, measures=len(ids), already_have=have, rows=len(row_hits),
                        example_measures="; ".join(ids[:6]), note=note))
    path = ROOT / "docs" / "stage4" / "shorthand_draft.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for o in out:
        print(f"{o['words'][:45]:<46}{o['two_meanings']:<4}{o['measures']:>4}{o['already_have']:>4}{o['rows']:>5}  {o['example_measures'][:70]}")


if __name__ == "__main__":
    main()
