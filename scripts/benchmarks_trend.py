"""Part 5g: the NCES and Yale benchmarks across all ten releases, through the app's own trend path (no model call).

Each benchmark from scripts/benchmarks.py is run once as a ten-year trend ("the last 10 years") through resolve,
trend and fetch, and each year's figure is compared with the published value for that release. Reference values
are read from version 1's benchmark files, as in Stage 4; version 1's code is not used.

    python scripts/benchmarks_trend.py      writes docs/reports/stage5g/benchmarks_trend.csv and prints a summary
"""
import csv
import glob
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import openpyxl

import benchmarks as b                                  # the Stage 4 requests, year rules and reference files
import config
from path import fetch, resolve
from path.request import no_year

OUT = ROOT / "docs" / "reports" / "stage5g"
TEN = dict(no_year(), span="the last N years", last=10)


def references(q):
    """{release year: value} for every observation in one NCES Trend Generator file."""
    path = glob.glob(str(b.TESTS / "NCES" / f"TrendGenerator-q{q}-*.xlsx"))[0]
    rows = list(openpyxl.load_workbook(path, read_only=True, data_only=True).active.iter_rows(values_only=True))
    out = {}
    for cells in rows:
        first = str(cells[0] or "").strip()
        if re.fullmatch(r"\d{4}(?:-\d{2,4})?", first) and len(cells) > 1 and isinstance(cells[1], (int, float)):
            out[b.source_year(q, first)] = (first, float(cells[1]))
    return str(rows[2][0]).strip(), out


def by_release(request, db, column=2):
    """{release year: value} from the app's ten-year trend for one request; the first figure column unless named."""
    request = dict(request, year=TEN)
    out = resolve.resolve_request(request, resolve.Dictionary(db, b.DB), None)
    if out["kind"] != "ready":
        return out["kind"], out.get("message"), {}
    result = fetch.fetch(out["plan"], db)
    values = {}
    for row in result["rows"]:
        m = re.match(r"(\d{4})-\d{2}", str(row[0]))
        if not m:
            continue
        cell = row[column] if len(row) > column else None
        values[int(m.group(1))] = cell[0] if isinstance(cell, tuple) else (None if cell == "not collected" else cell)
    return "answer", "; ".join(result["notes"]), values


def compare(rows, source, case, title, expected, kind, note, values, scale=1, tolerance=0):
    for y in sorted(expected):
        period, ref = expected[y]
        row = dict(source=source, case=case, title=title, release=f"{y}-{(y + 1) % 100:02d}", period=period,
                   expected=ref * scale)
        if y not in range(2015, 2025):
            continue                                    # outside the ten releases this app holds
        if kind != "answer":
            row.update(status=f"app {kind}", note=note)
        elif values.get(y) is None:
            row.update(status="app has no figure", note=note)
        else:
            diff = values[y] - ref * scale
            close = abs(diff) <= 0.1 if scale == 100 or "rate" in case else abs(diff) <= 0.001 * abs(ref * scale)
            row.update(actual=values[y], difference=diff, status="match" if abs(diff) <= tolerance else
                       "within 0.1 point" if close and (scale == 100 or "rate" in case) else
                       "within 0.1%" if close else "differs")
        rows.append(row)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f"file:{b.DB}?mode=ro", uri=True)
    rows = []
    for path in sorted(glob.glob(str(b.TESTS / "NCES" / "*.xlsx")), key=lambda p: int(re.search(r"-q(\d+)", p)[1])):
        q = int(re.search(r"-q(\d+)", path)[1])
        if q not in b.NCES or q in (1, 110):            # 1: a count; 110: split by form (both checked separately below)
            continue
        title, expected = references(q)
        request, scale = b.NCES[q]
        kind, note, values = by_release(request, db)
        tolerance = 0.05 if scale == 100 else (0.5 if q in (36, 50, 220, 221) or any(not float(v).is_integer() for _, v in expected.values()) else 0)
        compare(rows, "NCES", f"q{q}", title, expected, kind, note, values, scale, tolerance)

    # Yale: every year in the files, as questions about one school
    yale = csv.DictReader(open(b.TESTS / "Yale" / "w005-enr-historical-by-level(in).csv", encoding="utf-8-sig"))
    enr = {int(r["Fall"]): r for r in yale if r["Fall"].isdigit()}
    adm = {int(r["Year Entered"]): r for r in csv.DictReader(open(b.TESTS / "Yale" / "w033-yale-college-admissions-summary(in).csv",
                                                                  encoding="utf-8-sig")) if r["Year Entered"].isdigit()}
    sat = {}
    for r in csv.DictReader(open(b.TESTS / "Yale" / "w032-first-year-sat-scores(in).csv", encoding="utf-8-sig")):
        if r["Entered"].isdigit():
            sat.setdefault(r["Test"], {})[int(r["Entered"])] = r
    gr = {int(r["Entering Year"][:4]): r for r in csv.DictReader(open(b.TESTS / "Yale" / "w041-yale-college-graduation-rates(in).csv",
                                                                        encoding="utf-8-sig")) if r["Entering Year"][:4].isdigit()}
    cases = [("fall enrollment, total", b.M("DRVEF.ENRTOT"), {y: (f"Fall {y}", float(r["Total"])) for y, r in enr.items()}, 1, 0),
             ("fall enrollment, undergraduate", b.M("DRVEF.EFUG"), {y: (f"Fall {y}", float(r["Undergraduate"])) for y, r in enr.items()}, 1, 0),
             ("fall enrollment, graduate", b.M("DRVEF.EFGRAD"), {y: (f"Fall {y}", float(r["Graduate/Professional"])) for y, r in enr.items()}, 1, 0),
             ("applications", b.M("ADM.APPLCN"), {y: (f"Fall {y}", float(r["Total Applications"])) for y, r in adm.items()}, 1, 0),
             ("admits", b.M("ADM.ADMSSN"), {y: (f"Fall {y}", float(r["Total Admits"])) for y, r in adm.items()}, 1, 0),
             ("matriculants", b.M("ADM.ENRLT"), {y: (f"Fall {y}", float(r["Total Matrics"])) for y, r in adm.items()}, 1, 0),
             ("admit rate (a whole percent)", b.M("DRVADM.DVADM01"), {y: (f"Fall {y}", float(r["Admit Rate"])) for y, r in adm.items()}, 100, 0.5),
             ("six-year graduation rate (a whole percent)", b.M("DRVGR.GBA6RTT"),
              {y + 6: (f"cohort {y}", float(r["6-yr Graduation Rate"])) for y, r in gr.items()}, 100, 0.5)]
    for test, section in (("Verbal", "SATVR"), ("Math", "SATMT")):
        for p in (25, 75):
            cases.append((f"SAT {test} {p}th percentile", b.M(f"ADM.{section}{p}"),
                          {y: (f"Fall {y}", float(r[f"{p}th"])) for y, r in sat.get(test, {}).items() if r.get(f"{p}th")}, 1, 0))
    for label, measure, expected, scale, tolerance in cases:
        kind, note, values = by_release(b.req("schools", [measure], schools=[130794]), db)
        compare(rows, "Yale", label, "Yale University", expected, kind, note, values, scale, tolerance)

    with open(OUT / "benchmarks_trend.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source", "case", "title", "release", "period", "expected", "actual", "difference",
                                          "status", "note"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    for source in ("NCES", "Yale"):
        print(source, dict(Counter(r["status"] for r in rows if r["source"] == source)))
    by_case = {}
    for r in rows:
        if r["status"] != "match":
            by_case.setdefault((r["source"], r["case"], r["title"][:60]), []).append(f"{r['release']}: {r['status']} "
                                                                                   f"{r.get('expected')} vs {r.get('actual')}")
    for k, v in by_case.items():
        print(" ", k, "|", "; ".join(v)[:400])


if __name__ == "__main__":
    main()
