"""Part 5f: the official IPEDS glossary (docs/sources/ipeds_glossary_2025-26.pdf) as a dictionary table.

    python scripts/parse_glossary.py

Writes dictionary/glossary.csv (term, definition, edition) and prints the entries it could not separate cleanly.
The definitions are NCES's wording: nothing in them is changed, apart from joining the lines a definition wraps over
and taking out page headers and page numbers.

The PDF is a browser printout of a two-column table. Two text extractions are used together (pdftotext, which comes
with Git for Windows):
  - the file's own order (-raw), where each term comes before its definition;
  - the side-by-side layout (-layout), where a definition's lines are in the right-hand column.
A line of the first that appears in the right-hand column of the second is definition text; anything else is a term
(a long term wraps over two lines). A line holding both ("25th percentile The score at or below...") is split where
the definition's own line begins.
"""
import csv
import re
from collections import Counter
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "docs" / "sources" / "ipeds_glossary_2025-26.pdf"
OUT = ROOT / "docs" / "reports" / "stage5f" / "glossary_parsed.csv"   # dictionary/glossary.csv once the owner approves the parse
EDITION = "2025-26"
HEADERS = {"2025-26", "Data Collection System", "IPEDS HELP DESK", "(877) 225-2568 | ipedshelp@rti.org",
           "OMB NO. 1850-0582 v.33 : Approval Expires 8/31/2027", "View Glossary", "Term Definition", "Term", "Definition"}
RIGHT_COLUMN = 25          # in the side-by-side layout, the definitions start at about character 28 to 33


def text(mode):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "g.txt"
        subprocess.run(["pdftotext", mode, "-enc", "UTF-8", str(PDF), str(out)], check=True)
        return out.read_text(encoding="utf-8")


def squeeze(line):
    """Spaces squeezed, and none before punctuation or after an opening bracket, so both extractions compare."""
    line = " ".join(line.split())
    return re.sub(r"\(\s+", "(", re.sub(r"\s+([.,;:)])", r"\1", line))


def definition_lines(layout):
    """Every line of the right-hand column of the side-by-side layout, spaces squeezed. The column's position is
    found on each page (where its lines start), and a line holding a term fragment is split there, even when only
    one space separates the two."""
    found = set()
    for page in layout.split("\f"):
        lines = [l for l in page.splitlines() if l.strip()]
        starts = Counter(len(l) - len(l.lstrip()) for l in lines if len(l) - len(l.lstrip()) >= RIGHT_COLUMN)
        if not starts:
            continue
        column = starts.most_common(1)[0][0]
        for line in lines:
            if len(line) - len(line.lstrip()) >= RIGHT_COLUMN:     # a line of the right-hand column only
                found.add(squeeze(line))
                continue
            cut = next((i for i in range(column - 4, column + 3) if 0 < i < len(line) and line[i - 1] == " "
                        and line[i] != " "), None)
            if cut is not None and len(line) > column:          # a term fragment, then the right-hand column
                found.add(squeeze(line[cut:]))
    return found


def parse():
    raw, layout = text("-raw"), text("-layout")
    right = definition_lines(layout)
    entries, problems, long_terms = [], [], []
    term, definition, last = [], [], None
    def close():
        if term:
            entries.append(dict(term=" ".join(term), definition=" ".join(definition), edition=EDITION))
    for line in raw.replace("\f", "\n").splitlines():
        line = squeeze(line)
        if not line or line in HEADERS or line in {squeeze(h) for h in HEADERS}:
            continue
        kind, head, tail = None, line, ""
        if line in right:
            kind = "definition"
        else:
            words = line.split(" ")
            for i in range(1, len(words)):           # a term, then the start of its definition, on one line
                if " ".join(words[i:]) in right:
                    kind, head, tail = "both", " ".join(words[:i]), " ".join(words[i:])
                    break
            if kind is None:
                for i in range(len(words) - 1, 0, -1):   # the end of a definition, then the next term
                    if " ".join(words[:i]) in right and term:
                        definition.append(" ".join(words[:i]))
                        close()
                        term, definition, last = [], [], "definition"
                        line, head = " ".join(words[i:]), " ".join(words[i:])
                        words = line.split(" ")
                        for j in range(1, len(words)):   # ... and perhaps the start of that term's definition
                            if " ".join(words[j:]) in right:
                                kind, head, tail = "both", " ".join(words[:j]), " ".join(words[j:])
                                break
                        break
            kind = kind or "term"
        continues = term and (term[-1].endswith((",", " and", " or", " of", " the", "-", "(")) or head[:1].islower())
        if kind in ("term", "both"):
            if (last == "definition" or (last == "both" and kind != "definition")) and not continues:
                close()
                term, definition = [], []
            term.append(head)
            if kind == "both":
                definition.append(tail)
        else:
            if not term:
                problems.append(f"definition text with no term before it: {line[:80]}")
                continue
            definition.append(line)
        last = kind
    close()
    for e in entries:
        page = re.search(r"\.\s(\d{1,2})$", e["definition"])
        if page:                                       # a page number printed at the end of a page's last line
            e["definition"] = e["definition"][:page.start() + 1]
            e["note"] = f"page number {page.group(1)} taken off the end"
        if not e["definition"]:
            problems.append(f"no definition: {e['term']}")
        elif len(e["term"]) > 70 and re.search(r"[.!?] [A-Z]", e["term"]):
            problems.append(f"term holds a sentence (definition text read as a term?): {e['term'][:100]}")
        elif len(e["term"]) > 70:
            long_terms.append(e["term"])
        elif e["term"][:1].islower():
            problems.append(f"term starts in lower case (a definition line read as a term?): {e['term']}")
    seen = {}
    for e in entries:
        seen[e["term"].lower()] = seen.get(e["term"].lower(), 0) + 1
    problems += [f"term appears {n} times: {t}" for t, n in seen.items() if n > 1]
    return entries, problems, long_terms


if __name__ == "__main__":
    entries, problems, long_terms = parse()
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["term", "definition", "edition", "note"], lineterminator="\n", restval="")
        w.writeheader()
        w.writerows(entries)
    print(f"{len(entries)} terms written to {OUT}")
    print(f"{len(problems)} entries not separated cleanly:" if problems else "every entry separated cleanly")
    for p in problems:
        print("  " + p)
    print(f"{len(long_terms)} long terms, kept as they are (check):")
    for t in long_terms:
        print("  " + t)
    sys.exit(0)
