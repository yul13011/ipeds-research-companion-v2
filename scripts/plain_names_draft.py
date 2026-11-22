"""Draft short plain names for first-version measures whose IPEDS titles are long. Writes a review file only:
docs/stage4/plain_names_draft.csv (table, variable, IPEDS title, draft, length). Changes no dictionary table.

The drafts apply the same shortenings everywhere, so similar measures read alike. Each shortening is listed in
SHORTER, in the order applied. A draft still longer than LONG characters is marked for a hand-written name.
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LONG, MIN_TITLE = 70, 46

SHORTER = [
    (r"Average salary equated to 9 months of full-time instructional staff - all ranks", "Average faculty salary, all ranks"),
    (r"Average salary equated to 9 months of full-time instructional staff - ", "Average faculty salary, "),
    (r"first-time degree/certificate-seeking undergraduate students", "first-time undergraduates"),
    (r"first-time degree/certificate-seeking undergraduates", "first-time undergraduates"),
    (r"first-time degree/certificate-seeking students", "first-time students"),
    (r"degree/certificate-seeking", "degree-seeking"),
    (r"undergraduate students", "undergraduates"),
    (r"12-month unduplicated headcount", "12-month headcount"),
    (r"Percent of full-time first-time undergraduates awarded ", "Share of full-time first-time undergraduates with "),
    (r"Percent of undergraduates awarded ", "Share of undergraduates with "),
    (r"Percent of ", "Share of "),
    (r"federal, state, local, institutional or other sources of grant aid", "grant aid"),
    (r"federal, state, local or institutional grant aid", "grant aid"),
    (r"Average amount of ", "Average "),
    (r" awarded to ", " for "),
    (r"Average net price-students awarded grant or scholarship aid", "Average net price, grant-aided students"),
    (r"Average net price - all students awarded Title IV federal financial aid", "Average net price, Title IV aid recipients"),
    (r"Average net price -all students awarded Title IV federal financial aid", "Average net price, Title IV aid recipients"),
    (r"Percent full-time first-time receiving an award - (\d) years", r"Full-time first-time: award within \1 years"),
    (r"Percent part-time first-time receiving an award - (\d) years", r"Part-time first-time: award within \1 years"),
    (r"Percent full-time non-first-time receiving an award - (\d) years", r"Full-time transfer-in: award within \1 years"),
    (r"Percent part-time non-first-time receiving an award - (\d) years", r"Part-time transfer-in: award within \1 years"),
    (r"Percent (full|part)-time (first-time|non-first-time), Pell grant recipients", r"\1-time \2 Pell recipients"),
    (r"Percent (full|part)-time (first-time|non-first-time), non-Pell recipients", r"\1-time \2 non-Pell recipients"),
    (r"still enrolled at same institution", "still enrolled here"),
    (r"subsequently enrolled at another institution", "enrolled elsewhere"),
    (r"enrollment status unknown", "status unknown"),
    (r"receiving an award", "with an award"),
    (r"non-first-time", "transfer-in"),
    (r" as a percent of ", " as % of "),
    (r"total core expenses", "core expenses"),
    (r"total core revenues", "core revenues"),
    (r"Graduation rate - Bachelor degree within (\d) years", r"Bachelor's graduation rate, \1 years"),
    (r"Graduation rate, ", "Graduation rate, "),
    (r"Percent of total enrollment that are ", "Share of enrollment: "),
    (r"Percent of undergraduate enrollment that are ", "Share of undergraduates: "),
    (r"Percent of graduate enrollment that are ", "Share of graduate students: "),
    (r"enrolled exclusively in distance education courses", "fully online"),
    (r"enrolled in some but not all distance education courses", "partly online"),
    (r"not enrolled in any distance education courses", "not online"),
    (r"Percent (full|part)-time (first-time|non-first-time) receiving an? (associate's|bachelor's|certificate|award)( degree)? - (\d) years",
     r"\1-time \2: \3 within \5 years"),
    (r"\(for-profit institutions?\)", "(for-profit)"),
    (r"the total library collection", "the library collection"),
    (r"Total amount of ", "Total "),
    (r"Number of full-time first-time undergraduates awarded ", "Full-time first-time undergraduates with "),
    (r"full-time first-time undergraduates", "full-time first-time students"),
    (r"Total entering students at the undergraduate level, fall (\d{4})", r"Entering undergraduates, fall \1"),
    (r"Salaries and wages for (\w+) as a percent of total expenses for \1", r"Salaries and wages, share of \1 expenses"),
    (r"Salaries and wages for (\w+) as % of total expenses for \1", r"Salaries and wages, share of \1 expenses"),
    (r" that are ", ": "),
    (r"\s+", " "),
]


def draft(title):
    out = title
    for pattern, replacement in SHORTER:
        out = re.sub(pattern, replacement, out)
    out = out.strip(" -,")
    return out[0].upper() + out[1:] if out else out


def main():
    rows = [x for x in csv.DictReader(open(ROOT / "dictionary" / "measures.csv", encoding="utf-8"))
            if x["in_first_version"] == "yes" and not x["plain_name"] and len(x["title"]) >= MIN_TITLE]
    out = []
    for x in rows:
        d = draft(x["title"])
        out.append(dict(table=x["table"], variable=x["variable"], ipeds_title=x["title"], draft=d, length=len(d),
                        note="still long: needs a hand-written name" if len(d) > LONG else
                        ("unchanged" if d == x["title"] else "")))
    path = ROOT / "docs" / "stage4" / "plain_names_draft.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(len(out), "drafts;", sum(1 for o in out if o["note"].startswith("still long")), "still long;",
          sum(1 for o in out if o["note"] == "unchanged"), "unchanged")


if __name__ == "__main__":
    main()
