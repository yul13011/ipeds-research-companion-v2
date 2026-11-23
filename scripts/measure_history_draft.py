"""Part 5b: write dictionary/measure_history.csv from the approved cost and aid mapping (owner decision 2a).

    python scripts/measure_history_draft.py

The 2024-25 release reorganised the cost and aid tables. For each 2024-25 variable this finds the earlier
variable that reports the same figure for the same position in its own release (the same name, with the same
title once the years are taken out: COST1.CHG1AY3 "tuition and fees 2024-25" <- IC_AY.CHG1AY3 "tuition and fees
2023-24" in the 2023-24 release). That keeps each aid year's figure from the release where it is current
(decision 2b). The one approved title match with a different name is kept. Variables marked "check" or "no match"
in docs/reports/stage5b/cost_aid_map.csv get no row: they have no earlier years.
Run once; after that the CSV is the owner's table and is changed by change order only.
"""
import csv
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config

YEAR = re.compile(r"(?:19|20)\d\d(?:-\d\d)?")


def main():
    db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
    latest = db.execute("SELECT MAX(year) FROM _tables").fetchone()[0]
    src = {(t, y): s.upper() for t, s, y in db.execute("SELECT local_table, source_table, year FROM _tables")}
    title, title_any = {}, {}
    for tn, v, ti, y in db.execute("SELECT UPPER(TableName), UPPER(VarName), varTitle, year FROM VARTABLE"):
        title[(tn, v, y)] = ti or ""
        title_any.setdefault((v, y), ti or "")
    look = lambda t, v, y: title.get((src.get((t, y), ""), v, y)) or title_any.get((v, y), "")
    strip = lambda s: re.sub(r"\s+", " ", YEAR.sub("{YEAR}", s or "").lower()).strip()
    years_of = {}
    for t, c, y in db.execute("SELECT t.local_table, UPPER(c.column), t.year FROM _columns c JOIN _tables t "
                              "ON t.source_table = c.source_table AND t.release = c.release"):
        years_of.setdefault((t, c), set()).add(y)
    out, skipped = [], 0
    for r in csv.DictReader(open(ROOT / "docs/reports/stage5b/cost_aid_map.csv", encoding="utf-8")):
        if r["match"] in ("no match", "same name, different title: check"):
            skipped += 1
            continue
        nt, nv = r["new"].split(".")
        new_title = strip(look(nt, nv, latest))
        old = None
        if r["match"] == "same title, different name":
            old = tuple(r["old"].split("."))
        else:                                       # the same name, same title once years are taken out
            for (ot, oc), ys in years_of.items():
                earlier = max((y for y in ys if y < latest), default=None)
                if oc == nv and earlier and ot != nt and strip(look(ot, oc, earlier)) == new_title:
                    old = (ot, oc)
                    break
        if not old:
            skipped += 1
            print("  no same-position match:", r["new"], r["new_title"])
            continue
        ys = sorted(y for y in years_of.get(old, ()) if y < latest)
        out.append(dict(measure=r["new"], earlier_table=old[0], earlier_variable=old[1], years=f"{ys[0]}-{ys[-1]}" if ys[0] != ys[-1] else str(ys[0]),
                        how="same name and title, years aside" if r["match"] != "same title, different name"
                        else "same title, different name"))
    with open(ROOT / "dictionary/measure_history.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["measure", "earlier_table", "earlier_variable", "years", "how"], lineterminator="\r\n")
        w.writeheader()
        w.writerows(out)
    print(len(out), "rows written;", skipped, "variables with no earlier years")


if __name__ == "__main__":
    main()
