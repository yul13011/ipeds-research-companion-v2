"""Part 5b2: draft what every measure needs to be set up, from rules (owner's work order). Run once.

    python scripts/setup_draft.py --check     measure the unit rules against the 762 measures set up by hand
    python scripts/setup_draft.py             write the drafts into dictionary/measures.csv and the review list

The rules read the codebook's own wording (IPEDS titles and descriptions), never a user's question:
  - unit: from the codebook format and data type. A coded variable (Disc) is `coded`; text (Alpha) has no unit; a
    number (Cont) takes the first rule its title matches, in this order: percent, ratio, a per-school figure that
    cannot be added up (`average`: averages, prices, charges, per-student amounts), `dollars` (amounts that add up),
    `count`. A number whose title matches none, or a test-score percentile, is left blank and listed for review
    only when no rule decides it.
  - period: the table's year rule, unless the title names a different year; then that year, written as an offset
    from the release the variable appeared in (for a retired variable, the last release it appeared in).
  - reporting form (finance): the table's form; for the derived finance table, the form in the variable's name.
  - in_first_version becomes `yes` for every measure.
Value labels for coded measures come from the codebook (table value_labels); years available from the data
(table measure_years); multi-row tables use their row keys and tested breakdowns as now.
"""
import csv
import io
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config

RULES = [  # (unit, pattern) -- the title is tried against every rule first, then the description; first match wins
    ("", r"\b(\d\dth percentile|percentile|latitude|longitude|unitid|identification number|identifcation number|id number|"
         r"institution id|ipedsid|fips|zip)\b"),
    ("count", r"^(number|total number|count)\b"),
    ("percent", r"^(percent|percentage)\b"),
    ("percent", r"\b(percent|percentage|rate|yield|share)\b"),
    ("ratio", r"\bratio\b"),
    ("count", r"\b(recipients|cohort|exclusions|completers)\b"),
    ("average", r"\b(average|median|mean|per fte|per student|per full-time|per (week|credit|hour|term|year|semester)|price|"
                r"tuition|fees?|charges?|cost of attendance|room|board|food and housing|books and supplies|"
                r"other expenses for|on campus|off campus|with family|length|factor)\b"),
    ("dollars", r"\b(amount|dollars|expenses|expenditures|revenues?|assets|liabilities|endowment|outlays|appropriations|"
                r"salar(y|ies)|wages|benefits|grants|contracts|gifts|investment|net position|deductions|depreciation|"
                r"interest|tax|loans?|aid awarded|scholarships|fellowships|discounts|allowances|income)\b"),
    ("count", r"\b(number|total|count|enrollment|headcount|students|staff|employees|faculty|awards?|degrees?|"
              r"certificates?|completers|applicants|admissions|admitted|enrolled|cohort|fte|full-time equivalent|"
              r"programs?|hires|men|women|volumes|titles|circulation|transactions|libraries|branches|campuses|"
              r"units|items|databases|recipients|persons|graduates|exclusions)\b"),
]
FORMS = {"F1": "GASB", "F2": "FASB", "F3": "for-profit"}
YEAR = re.compile(r"(?<!\d)((?:19|20)\d\d)(?:-(\d\d))?(?!\d)")


def unit_of(fmt, dtype, title, desc, table="", form=""):
    if fmt == "Disc":
        return "coded", "codebook format"
    if fmt == "Alpha" or dtype == "A" or fmt != "Cont":
        return "", "text"
    if form and table.startswith("F_"):             # a line of a finance form is an amount, unless a percent or ratio
        found = re.search(r"\b(percent|percentage|ratio)\b", (title or "").lower())
        return ("ratio" if found.group(0) == "ratio" else "percent", f"title: {found.group(0)}") if found else \
            ("dollars", "finance form line")
    for where, text in (("title", title), ("description", (desc or "")[:400])):
        for unit, pattern in RULES:
            found = re.search(pattern, (text or "").lower().strip())
            if found:
                return unit, f"{where}: {found.group(0)}"
    return None, "no rule matched"


def period_of(title, table_period, base):
    """A period written from the release year, when the title names a range of years (2021-22) that differs from the
    table's period. A single year in a title is a cohort or a classification edition, not a period, and a cohort's
    years are the table's entering-cohort rule, so neither sets a period."""
    m = YEAR.search(title or "")
    if not m or not m.group(2) or "cohort" in (title or "").lower():
        return ""
    first, short = int(m.group(1)), m.group(2)
    off = first - base
    y = "{Y}" if off == 0 else f"{{Y{off:+d}}}"
    text = y + (("-{Y" + (f"{off + 1:+d}" if off + 1 else "") + ":yy}") if short else "")
    filled = re.sub(r"\{Y([+-]\d+)?(:yy)?\}", lambda k: (lambda v: f"{v % 100:02d}" if k.group(2) else str(v))(
        base + int(k.group(1) or 0)), text)
    return "" if filled in (table_period or "") else text


def main():
    check_only = "--check" in sys.argv
    db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
    latest = db.execute("SELECT MAX(year) FROM _tables").fetchone()[0]
    path = ROOT / "dictionary" / "measures.csv"
    raw = open(path, encoding="utf-8", newline="").read()
    rows = list(csv.reader(io.StringIO(raw)))
    head, body = rows[0], rows[1:]
    I = {k: i for i, k in enumerate(head)}
    if check_only:
        agree, seen = Counter(), []
        for r in body:
            if r[I["in_first_version"]] != "yes" or r[I["format"]] != "Cont":
                continue
            got, why = unit_of(r[I["format"]], r[I["data_type"]], r[I["title"]], r[I["long_description"]], r[I["table"]], r[I["reporting_form"]] or FORMS.get(r[I["variable"]][:2].upper(), "") if r[I["table"]].startswith("F_") else r[I["reporting_form"]])
            agree[got == r[I["unit"]]] += 1
            if got != r[I["unit"]]:
                seen.append((r[I["table"]], r[I["variable"]], r[I["title"]][:60], r[I["unit"]], got, why))
        print(f"unit rules agree with the hand-set unit on {agree[True]} of {sum(agree.values())} set-up numbers")
        for s in seen:
            print("  ", s)
        return

    periods = {t: p for t, p in db.execute('SELECT "table", period FROM dict_year_meaning')}
    last_year = {m: y for m, y in db.execute("SELECT measure, MAX(year) FROM measure_years GROUP BY measure")}
    review, changed = [], Counter()
    for r in body:
        if r[I["in_first_version"]] == "yes":
            continue
        mid = f"{r[I['table']]}.{r[I['variable']]}"
        got, why = unit_of(r[I["format"]], r[I["data_type"]], r[I["title"]], r[I["long_description"]], r[I["table"]], r[I["reporting_form"]] or (FORMS.get(r[I["variable"]][:2].upper(), "") if r[I["table"]].startswith("F_") else ""))
        if got is None:
            review.append(dict(measure=mid, title=r[I["title"]], flag="unit unclear", detail=why))
            got = ""
        r[I["unit"]] = got
        base = last_year.get(mid, latest)
        if not r[I["period"]]:
            r[I["period"]] = period_of(r[I["title"]], fill(periods.get(r[I["table"]], ""), base), base)
        if r[I["table"]] in ("F_F1A", "F_F2", "F_F3", "DRVF") and not r[I["reporting_form"]]:
            r[I["reporting_form"]] = FORMS.get(r[I["variable"]][:2].upper(), "")
        r[I["in_first_version"]] = "yes"
        changed[got or "(no unit)"] += 1
    with open(path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator="\r\n" if "\r\n" in raw else "\n").writerows([head] + body)
    out = ROOT / "docs" / "reports" / "stage5b2"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "unit_review.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["measure", "title", "flag", "detail"])
        w.writeheader()
        w.writerows(review)
    print("set up:", sum(changed.values()), dict(changed))
    print("units unclear:", len(review))


def fill(text, year):
    return re.sub(r"\{Y([+-]\d+)?(:yy)?\}", lambda k: (lambda v: f"{v % 100:02d}" if k.group(2) else str(v))(
        year + int(k.group(1) or 0)), text or "")


if __name__ == "__main__":
    main()
