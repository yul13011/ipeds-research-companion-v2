"""Part 5b addition: variables that exist only in earlier releases (owner decision of 2026-11-22, "retired variables").

    python scripts/retired_variables.py

1. Adds each retired variable to dictionary/measures.csv, not set up, with the codebook title and description from
   the last year it appeared and the releases it appeared in (`years_available`). A variable already mapped as the
   earlier name of a 2024-25 measure (measure_history.csv) is that measure, not a retired one.
2. Proposes successors and adds them to dictionary/measure_history.csv. A successor is a 2024-25 measure that first
   appears in the release right after the retired variable last appeared, and
     - has the same name and the same title once years are taken out          -> status "in use"
     - has the same title under another name in the same table                -> status "in use"
     - has the same name with another title, or the same title in another
       table, or a similar title (most words shared) in the same table       -> status "to review"
   A successor claimed by more than one retired variable is "to review". The codebook lists of new variables
   (NEWVARIABLES, 2023-24 and 2024-25 only) are noted where they list the successor.
3. Writes the full list to docs/reports/stage5b/successors.csv.
Run once; after that the CSVs are the owner's tables, changed by change order only.
"""
import collections
import csv
import io
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config

YEAR = re.compile(r"(?:19|20)\d\d(?:-\d\d)?")
FORMS = {"F1": "GASB", "F2": "FASB", "F3": "for-profit"}     # DRVF variables carry their form in the name
SHARE = 0.6                                                  # "similar title": at least this share of words in common


def label(y):
    return f"{y}-{(y + 1) % 100:02d}"


def main():
    db = sqlite3.connect(f"file:{config.LOCAL_DB.as_posix()}?mode=ro", uri=True)
    latest = db.execute("SELECT MAX(year) FROM _tables").fetchone()[0]
    src = {(t, y): s.upper() for t, s, y in db.execute("SELECT local_table, source_table, year FROM _tables")}
    book = {}
    for tn, v, y, ti, desc, fmt, dt in db.execute(
            "SELECT UPPER(TableName), UPPER(varName), year, varTitle, longDescription, format, DataType FROM VARTABLE"):
        book[(tn, v, y)] = (ti or "", desc or "", fmt or "", dt or "")
        book.setdefault((None, v, y), (ti or "", desc or "", fmt or "", dt or ""))
    look = lambda t, v, y: book.get((src.get((t, y)), v, y)) or book.get((None, v, y)) or ("", "", "", "")
    strip = lambda s: re.sub(r"\s+", " ", YEAR.sub("", s or "").lower()).strip(" ,:-")
    words = lambda s: set(re.findall(r"[a-z]+", strip(s))) - {"the", "of", "and", "or", "a", "for", "to", "in", "year"}
    new_listed = {(tn.upper(), v.upper()) for tn, v in db.execute("SELECT TableName, VarName FROM NEWVARIABLES")}

    years_of = collections.defaultdict(set)
    for t, c, y in db.execute("SELECT t.local_table, UPPER(c.column), t.year FROM _columns c JOIN _tables t "
                              "ON t.source_table = c.source_table AND t.release = c.release WHERE t.kind = 'data'"):
        years_of[(t, c)].add(y)

    path = ROOT / "dictionary" / "measures.csv"
    raw = open(path, encoding="utf-8", newline="").read()
    rows = list(csv.reader(io.StringIO(raw)))
    head, body = rows[0], rows[1:]
    if "years_available" not in head:
        head.append("years_available")
        body = [r + [""] for r in body]
    I = {k: i for i, k in enumerate(head)}
    current = {(r[I["table"]], r[I["variable"]].upper()): r for r in body}
    by_table = collections.defaultdict(list)
    for r in body:
        by_table[r[I["table"]]].append(r)
    history = list(csv.DictReader(open(ROOT / "dictionary" / "measure_history.csv", encoding="utf-8")))
    earlier = {(h["earlier_table"], h["earlier_variable"].upper()) for h in history}

    retired = sorted(k for k, ys in years_of.items() if latest not in ys and k[1] not in ("UNITID", "YEAR")
                     and k not in earlier and k not in current)
    added = []
    for t, v in retired:
        ys = sorted(years_of[(t, v)])
        title, desc, fmt, dt = look(t, v, ys[-1])
        same = by_table.get(t, [])
        per_school = collections.Counter(r[I["rows_per_school"]] for r in same).most_common(1)
        forms = {r[I["reporting_form"]] for r in same}
        form = FORMS.get(v[:2], "") if t == "DRVF" else (forms.pop() if len(forms) == 1 else "")
        row = [""] * len(head)
        row[I["table"]], row[I["variable"]], row[I["title"]], row[I["long_description"]] = t, v, title.strip(), desc.strip()
        row[I["format"]], row[I["data_type"]] = fmt, dt
        row[I["rows_per_school"]] = per_school[0][0] if per_school else "one row per school"
        row[I["reporting_form"]], row[I["priority"]], row[I["in_first_version"]] = form, "3", "no"
        row[I["years_available"]] = ", ".join(f"{a}-{b}" if a != b else str(a) for a, b in spans(ys))
        added.append(row)

    # successors: 2024-25 measures whose own column first appears right after the retired variable's last year
    first_seen = {}
    for (t, c), ys in years_of.items():
        if latest in ys and (t, c) in current:
            first_seen[(t, c)] = min(ys)
    mapped = {h["measure"].upper() for h in history}           # already continued through the cost and aid mapping
    found = []
    for t, v in retired:
        last = max(years_of[(t, v)])
        title = look(t, v, last)[0]
        cands = [k for k, f in first_seen.items() if f == last + 1 and f"{k[0]}.{k[1]}" not in mapped]
        ctitle = {k: current[k][I["title"]] for k in cands}
        pick, how, status = None, "", ""
        same_name = [k for k in cands if k[1] == v]
        same_title = [k for k in cands if strip(ctitle[k]) and strip(ctitle[k]) == strip(title)]
        if same_name and strip(ctitle[same_name[0]]) == strip(title):
            pick, how, status = same_name[0], "same name and title, years aside", "in use"
        elif len([k for k in same_title if k[0] == t]) == 1:
            pick, how, status = [k for k in same_title if k[0] == t][0], "same title, other name", "in use"
        elif same_name:
            pick, how, status = same_name[0], "same name, other title", "to review"
        elif len(same_title) == 1:
            pick, how, status = same_title[0], "same title, other table", "to review"
        else:
            w = words(title)
            scored = sorted(((len(w & words(ctitle[k])) / max(1, len(w | words(ctitle[k]))), k) for k in cands if k[0] == t),
                            reverse=True)
            if scored and scored[0][0] >= SHARE and (len(scored) == 1 or scored[1][0] < scored[0][0]):
                pick, how, status = scored[0][1], f"similar title ({scored[0][0]:.0%} of words shared)", "to review"
        found.append(dict(retired=f"{t}.{v}", retired_title=title, first=label(min(years_of[(t, v)])), last=label(last),
                          successor=f"{pick[0]}.{current[pick][I['variable']]}" if pick else "",
                          successor_title=ctitle[pick] if pick else "", how=how or "no successor found", status=status,
                          codebook_lists_successor_as_new="yes" if pick and (src.get((pick[0], last + 1)), pick[1]) in new_listed else ""))
    claimed = collections.Counter(f["successor"] for f in found if f["successor"])
    for f in found:
        if f["successor"] and claimed[f["successor"]] > 1:
            f["status"], f["how"] = "to review", f["how"] + "; claimed by more than one retired variable"

    with open(path, "w", encoding="utf-8", newline="") as out:
        w = csv.writer(out, lineterminator="\r\n" if "\r\n" in raw else "\n")
        w.writerow(head)
        w.writerows(body + added)
    hpath = ROOT / "dictionary" / "measure_history.csv"
    fields = ["measure", "earlier_table", "earlier_variable", "years", "how", "status"]
    for h in history:
        h.setdefault("status", "in use")
        h["status"] = h["status"] or "in use"
    for f in found:
        if f["successor"]:
            t, v = f["retired"].split(".")
            ys = sorted(years_of[(t, v)])
            history.append(dict(measure=f["successor"], earlier_table=t, earlier_variable=v,
                                years=", ".join(f"{a}-{b}" if a != b else str(a) for a, b in spans(ys)),
                                how=f["how"], status=f["status"]))
    with open(hpath, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=fields, lineterminator="\r\n")
        w.writeheader()
        w.writerows(history)
    with open(ROOT / "docs" / "reports" / "stage5b" / "successors.csv", "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=list(found[0]))
        w.writeheader()
        w.writerows(found)
    print(len(added), "retired variables added to measures.csv")
    print(collections.Counter(f["status"] or "no successor" for f in found))
    print(collections.Counter(f["how"].split(";")[0].split(" (")[0] for f in found))


def spans(ys):
    """[2015, 2016, 2017, 2020] -> [(2015, 2017), (2020, 2020)]."""
    out = []
    for y in ys:
        if out and y == out[-1][1] + 1:
            out[-1] = (out[-1][0], y)
        else:
            out.append((y, y))
    return out


if __name__ == "__main__":
    main()
