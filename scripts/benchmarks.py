"""Stage 4: known answers, through the app's own resolve and fetch steps (no model call).

Each benchmark is written as a structured request, the same shape the model produces, and run through resolve
and fetch. The app's figure is compared with the published one. Reference values are read from version 1's
benchmark files (NCES Trend Generator exports and the Yale CSVs); version 1's code is not used.

    python scripts/benchmarks.py            writes docs/reports/stage4/benchmarks.csv and prints a summary
"""
import csv
import glob
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import openpyxl

import config
from path import fetch, resolve
from path.request import empty

DB = config.LOCAL_DB.as_posix()
TESTS = config.SOURCE_DATA.parent / "Test cases"
OUT = ROOT / "docs" / "reports" / "stage4"


def req(op, measures=(), groups=(), schools=(), readings=()):
    r = empty(op)
    r["measures"] = [dict(id=m, row=[dict(column=c, code=v) for c, v in rows]) if isinstance(m, tuple) is False else
                     dict(id=m[0], row=[dict(column=c, code=v) for c, v in m[1]]) for m in measures for rows in [()]]
    r["groups"], r["schools"] = list(groups), [dict(name=str(u), id=u) for u in schools]
    r["readings"] = [dict(term=t, reading=x) for t, x in readings]
    return r


def M(mid, *rows):
    return (mid, list(rows))


# NCES: question number -> (structured request, how the published figure is scaled to the app's)
# Source year rule from the benchmark files: graduation tables show the entering cohort, aid and annual tables the
# academic year before the release.
NCES = {
    1: (req("count_schools"), 1),
    2: (req("group", [M("DRVEF12.UNDUP")]), 1),
    3: (req("group", [M("DRVEF.ENRTOT")]), 1),
    4: (req("group", [M("DRVEF.EFUGTRN")]), 1),
    5: (req("group", [M("DRVEF.EFUG1ST")]), 1),
    12: (req("group", [M("SAL_IS.SAINSTT")], groups=["Degree-granting"]), 1),
    19: (req("group", [M("DRVGR.GRRTTOT")], groups=["Four or more years"],
             readings=[("graduation rate", "Total cohort within 150% of normal time")]), 100),
    20: (req("group", [M("DRVGR.GBA6RTT")], groups=["Four or more years"]), 100),
    21: (req("group", [M("DRVGR.GRRTTOT")], groups=["At least 2 but less than 4 years"]), 100),
    24: (req("group", [M("C_A.CTOTALT")]), 1),
    25: (req("group", [M("SFA.ANYAIDN")]), 1),
    30: (req("group", [M("S_OC.HRTOTLT")], groups=["Degree-granting"]), 1),
    32: (req("group", [M("EFD.RET_PCF")]), 100),
    33: (req("group", [M("EFD.RET_PCP")]), 100),
    34: (req("group", [M("SFA.ANYAIDP")], readings=[("financial aid", "Any financial aid, full-time first-time undergraduates")]), 100),
    35: (req("group", [M("SFA.UPGRNTP")]), 100),
    36: (req("group", [M("SFA.UPGRNTA")]), 1),
    37: (req("group", [M("SFA.UFLOANP")]), 100),
    38: (req("group", [M("SFA.UFLOANA")]), 1),
    42: (req("group", [M("DRVEF.PCTDEEXC")]), 100),
    43: (req("group", [M("DRVEF12.FTE12MN")]), 1),
    50: (req("group", [M("DRVHR.SALTOTL")], groups=["Degree-granting"]), 1),
    51: (req("group", [M("S_IS.HRTOTLT")], groups=["Degree-granting"]), 1),
    101: (req("group", [M("ADM.APPLCN")]), 1),
    102: (req("group", [M("DRVADM.DVADM01")]), 100),
    103: (req("group", [M("DRVADM.DVADM04")]), 100),
    110: (req("group", [M("rate:Core expenses per FTE student")]), 1),
    150: (req("group", [M("EFC.EFRES01")]), 1),
    200: (req("group", [M("rate:Award within eight years (Outcome Measures)")]), 100),
    210: (req("group", [M("C_B.CSTOTLT")]), 1),
    220: (req("group", [M("SFA.AGRNT_A")]), 1),
    221: (req("group", [M("SFA.LOAN_A")]), 1),
}
NOT_MAPPED = {8: "age category not identified in the export", 13: "total revenues (not core) are not set up",
              15: "total revenues (not core) are not set up", 17: "total revenues (not core) are not set up",
              39: "total expenses (not core) are not set up", 40: "total expenses (not core) are not set up",
              41: "total expenses (not core) are not set up", 155: "first-time students from high school within 12 months not set up",
              205: "average tuition by control: no rates.csv row", 206: "average tuition by control: no rates.csv row",
              207: "graduate tuition not set up", 208: "graduate tuition not set up",
              22: "less-than-two-year graduation rate left out by owner decision (2026-11)"}


def source_year(q, period):
    start = int(period[:4])
    if q in {19, 20}:
        return start + 6
    if q in {21, 22}:
        return start + 3
    if q == 200:
        return start + 8
    if q in {2, 24, 25, 34, 35, 36, 37, 38, 43, 210, 220, 221}:
        return start + 1
    return start


def nces_reference(q):
    """(title, period, value) for the observation that belongs to the 2024-25 release."""
    path = glob.glob(str(TESTS / "NCES" / f"TrendGenerator-q{q}-*.xlsx"))[0]
    rows = list(openpyxl.load_workbook(path, read_only=True, data_only=True).active.iter_rows(values_only=True))
    for cells in rows:
        first = str(cells[0] or "").strip()
        if re.fullmatch(r"\d{4}(?:-\d{2,4})?", first) and len(cells) > 1 and cells[1] is not None and source_year(q, first) == 2024:
            return str(rows[2][0]).strip(), first, float(cells[1])
    return str(rows[2][0]).strip(), None, None


def run(request, db):
    out = resolve.resolve_request(request, resolve.Dictionary(db, DB), None)
    if out["kind"] != "ready":
        return out["kind"], out.get("message"), None
    result = fetch.fetch(out["plan"], db)
    return "answer", None, result


def first_value(result, column="Value"):
    cols = result["columns"]
    i = cols.index(column) if column in cols else 1
    cell = result["rows"][0][i] if result["rows"] else None
    return cell[0] if isinstance(cell, tuple) else cell


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = []
    for path in sorted(glob.glob(str(TESTS / "NCES" / "*.xlsx")), key=lambda p: int(re.search(r"-q(\d+)", p)[1])):
        q = int(re.search(r"-q(\d+)", path)[1])
        title, period, expected = nces_reference(q)
        row = dict(source="NCES", case=f"q{q}", title=title, period=period, expected=expected)
        if expected is None:
            row.update(status="no 2024-25 observation in the file")
        elif q in NOT_MAPPED:
            row.update(status="not covered", note=NOT_MAPPED[q])
        else:
            request, scale = NCES[q]
            kind, message, result = run(request, db)
            if kind != "answer":
                row.update(status=f"app {kind}", note=message)
            else:
                values = [(r[0], r[1][0] if isinstance(r[1], tuple) else r[1]) for r in result["rows"]]
                actual = (values[0][1] if values else None) if q != 1 else first_value(result, "Schools")
                if not values:
                    row.update(status="app answer, no rows", note="; ".join(result["notes"] + result["warnings"]))
                elif q == 110:                            # NCES publishes public and private nonprofit together
                    note = "; ".join(f"{label}: {v:,.0f}" for label, v in values)
                    row.update(status="split by form (by rule)", actual=None, note=note)
                else:
                    tolerance = 0.05 if scale == 100 else (0.5 if expected < 1e5 and not float(expected).is_integer() or q in (36, 50, 220, 221, 110) else 0)
                    diff = actual - expected * scale if actual is not None else None
                    row.update(actual=actual, expected_scaled=expected * scale, difference=diff,
                               status="match" if diff is not None and abs(diff) <= tolerance else "differs",
                               note="; ".join(result["notes"]))
        rows.append(row)

    # Yale: the 2024 rows of each file, as questions about one school
    yale = []
    enr = next(r for r in csv.DictReader(open(TESTS / "Yale" / "w005-enr-historical-by-level(in).csv", encoding="utf-8-sig")) if r["Fall"] == "2024")
    yale += [("fall enrollment, total", M("DRVEF.ENRTOT"), float(enr["Total"]), 0),
             ("fall enrollment, undergraduate", M("DRVEF.EFUG"), float(enr["Undergraduate"]), 0),
             ("fall enrollment, graduate", M("DRVEF.EFGRAD"), float(enr["Graduate/Professional"]), 0)]
    adm = next(r for r in csv.DictReader(open(TESTS / "Yale" / "w033-yale-college-admissions-summary(in).csv", encoding="utf-8-sig")) if r["Year Entered"] == "2024")
    yale += [("applications", M("ADM.APPLCN"), float(adm["Total Applications"]), 0),
             ("admits", M("ADM.ADMSSN"), float(adm["Total Admits"]), 0),
             ("matriculants", M("ADM.ENRLT"), float(adm["Total Matrics"]), 0),
             ("admit rate (IPEDS reports a whole percent)", M("DRVADM.DVADM01"), 100 * float(adm["Admit Rate"]), 0.5),
             ("yield (IPEDS reports a whole percent)", M("DRVADM.DVADM04"), 100 * float(adm["Yield Rate"]), 0.5)]
    for r in csv.DictReader(open(TESTS / "Yale" / "w032-first-year-sat-scores(in).csv", encoding="utf-8-sig")):
        if r["Entered"] == "2024":
            section = {"Verbal": "SATVR", "Math": "SATMT"}[r["Test"]]
            for p in (25, 50, 75):
                yale.append((f"SAT {r['Test']} {p}th percentile", M(f"ADM.{section}{p}"), float(r[f"{p}th"]), 0))
            for p in (10, 90):
                yale.append((f"SAT {r['Test']} {p}th percentile", None, float(r[f"{p}th"]), 0))
    gr = next(r for r in csv.DictReader(open(TESTS / "Yale" / "w041-yale-college-graduation-rates(in).csv", encoding="utf-8-sig")) if r["Entering Year"].startswith("2018"))
    yale += [("2018 bachelor's cohort", M("GR.GRTOTLT", ("GRTYPE", "8")), float(gr["Number of First Year Entering Students"]), 0),
             ("2018 cohort graduates in six years", M("GR.GRTOTLT", ("GRTYPE", "12")), float(gr["Number of Graduates"]), 0),
             ("six-year graduation rate (IPEDS reports a whole percent)", M("DRVGR.GBA6RTT"), 100 * float(gr["6-yr Graduation Rate"]), 0.5)]
    for r in csv.DictReader(open(TESTS / "Yale" / "yale-college-grad-rates-subgroups(in).csv", encoding="utf-8-sig")):
        if r["Year of Entry"] == "2018":
            yale.append((f"2018 cohort by {r['Category']}: {r['Group']}", None, float(r["Cohort"]), 0))
    for label, measure, expected, tolerance in yale:
        row = dict(source="Yale", case=label, title="Yale University", period="2024-25 release", expected=expected)
        if measure is None:
            row.update(status="not covered", note="not collected by IPEDS, or a subgroup measure not set up")
        else:
            kind, message, result = run(req("schools", [measure], schools=[130794]), db)
            actual = first_value(result, result["columns"][1]) if kind == "answer" else None
            diff = actual - expected if actual is not None else None
            row.update(actual=actual, difference=diff, note=message or "",
                       status=f"app {kind}" if kind != "answer" else ("match" if diff is not None and abs(diff) <= tolerance else "differs"))
        rows.append(row)

    # The test table in the plan (docs/archive/V2_PLAN_2026-11-25.md): the checks not already covered by the NCES files above
    def plan(case, request, expected, read):
        kind, message, result = run(request, db)
        actual = read(result) if kind == "answer" else None
        rows.append(dict(source="Plan", case=case, title="V2_PLAN.md test table", period="2024-25 release", expected=expected,
                         actual=actual, status=("match" if str(actual) == str(expected) else "differs") if kind == "answer" else f"app {kind}",
                         note=message or ""))
    val = lambda c: round(c[0], 1) if isinstance(c, tuple) else c
    r = req("breakdown", [M("EFA.EFTOTLT", ("EFALEVEL", "2"))], schools=[130794])
    r["breakdown"] = dict(set="By race and ethnicity", fixed=[dict(column="EFALEVEL", code="2")])
    plan("Yale undergraduates by race: categories, total", r, "9 categories, total 6814",
         lambda res: f"{len(res['rows']) - 1} categories, total {val(res['rows'][-1][1])}")
    r = req("split", [M("DRVGR.GBA6RTT")], groups=["Four or more years"])
    r["split_by"] = "control"
    plan("Bachelor's six-year rate by control (percent)", r, "63.8 / 68.3 / 34.1",
         lambda res: " / ".join(f"{val(x[2])}" for x in res["rows"]))
    r = req("breakdown", [M("SAL_IS.SAINSTT")], schools=[170976])
    r["breakdown"] = dict(set="Full-time instructional staff by rank", fixed=[])
    plan("University of Michigan salary by rank: rows incl. all ranks (plan: seven)", r, 7, lambda res: len(res["rows"]))
    r = req("list", [M("DRVEF.ENRTOT")])
    r["peers_of"] = 195003
    plan("RIT's IPEDS comparison group: schools", r, "11 (plan said 8)", lambda res: f"{len(res['rows'])} (plan said 8)")
    r = req("rank", [M("COST2_NETPRICE.NPGRN2")], groups=["Four or more years"])
    r["sort"] = dict(order="lowest", limit=3)
    plan("Lowest net price, four-year: top value is positive", r, True, lambda res: val(res["rows"][0][3]) > 0)

    with open(OUT / "benchmarks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source", "case", "title", "period", "expected", "expected_scaled", "actual",
                                          "difference", "status", "note"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    for source in ("NCES", "Yale", "Plan"):
        print(source, dict(Counter(r["status"] for r in rows if r["source"] == source)))
    for r in rows:
        if r["status"] not in ("match", "not covered"):
            print(f"  {r['source']} {r['case']}: {r['status']} expected {r.get('expected_scaled', r['expected'])} actual {r.get('actual')} {r.get('note') or ''}"[:260])


if __name__ == "__main__":
    main()
