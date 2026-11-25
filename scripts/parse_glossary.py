"""Part 5f: the official IPEDS glossary (docs/sources/ipeds_glossary_2025-26.pdf) as a dictionary table.

    python scripts/parse_glossary.py

Writes dictionary/glossary.csv (term, definition, edition) and prints the entries it could not separate cleanly.
The definitions are NCES's wording: nothing in them is changed, apart from joining the lines a definition wraps over
and taking out page headers and page numbers (printed outside the table).

The PDF is a browser printout of a two-column table. Two text extractions are used together (pdftotext, which comes
with Git for Windows):
  - the file's own order (-raw), where each term comes before its definition;
  - the side-by-side layout (-layout), where a definition's lines are in the right-hand column.
A line of the first that appears in the right-hand column of the second is definition text; anything else is a term
(a long term wraps over two lines). A line holding both ("25th percentile The score at or below...") is split where
the definition's own line begins.

That first pass gives the list of terms. The owner-approved corrections (docs/sources/glossary_corrections.csv) fix
the terms it got wrong. Then every definition is cut out of the file's own text, from the end of one term to the start
of the next, so no definition is ever typed in by hand.

Carnegie entries describe the 2000 and 2005 classifications: they are marked historical (owner decision, 2026-11-24),
and the app never shows them as the definition of its 2021 Carnegie groups.
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
OUT = ROOT / "dictionary" / "glossary.csv"
CORRECTIONS = ROOT / "docs" / "sources" / "glossary_corrections.csv"
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


def first_pass(raw, layout):
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
    return entries, problems


def corrected_terms(entries):
    """The first pass's terms, with the owner-approved corrections: a parsed term is replaced by the terms the PDF
    really has there (none, one or two). Rows with the same parsed term apply to its occurrences in order."""
    with open(CORRECTIONS, encoding="utf-8") as f:
        fixes = list(csv.DictReader(f))
    left = Counter(r["parsed term"] for r in fixes)
    terms, used = [], Counter()
    for e in entries:                  # each term with the first words of its definition, where the first pass has them
        rows = [r for r in fixes if r["parsed term"] == e["term"]]
        if rows:
            row = rows[used[e["term"]]] if used[e["term"]] < len(rows) else None
            used[e["term"]] += 1
            if row is not None:
                terms += [(t.strip(), None) for t in row["terms in the PDF"].split("|") if t.strip()]
                continue
        terms.append((e["term"], " ".join(e["definition"].split()[:3]) or None))
    unused = [t for t, n in left.items() if used[t] < n]
    return terms, unused


def segment(raw, terms):
    """Every definition cut out of the file's own text, between its term and the next one. A term is looked for at
    the start of a line first (where the file puts terms), then anywhere; where the first pass found the start of its
    definition, the term must be followed by it, so a term's words inside an earlier definition are not taken."""
    lines = [squeeze(l) for l in raw.replace("\f", "\n").splitlines()]
    heads = {squeeze(h) for h in HEADERS}
    stream = "\n".join(l for l in lines if l and l not in heads)
    found, problems, at = [], [], 0
    for term, anchor in terms:
        words = [re.escape(w) for w in term.split()]
        follow = r"(?=\s*" + r"\s*".join(re.escape(w) for w in anchor.split()) + ")" if anchor else ""
        start = None
        joined = "".join(w + ("" if i == len(words) - 1 else r"\s*" if len(w) > 2 and w.endswith(r"\-") else r"\s+")
                         for i, w in enumerate(words))     # "for-" at a line end, then "profit"
        for line_start, pattern in ((True, r"(?:^|(?<=\n))" + joined + follow),
                                    (False, r"\s*".join(words) + follow)):
            m = re.compile(pattern).search(stream, at)
            if m:
                start, end = m.start(), m.end()
                if not line_start:
                    problems.append(f"term found mid-line (check): {term}")
                break
        if start is None:
            problems.append(f"term not found in the text after the previous one: {term}")
            continue
        term = " ".join(re.sub(r"(?<=\S)-\n(?=\S)", "-", stream[start:end]).split())   # the term as the file has it
        found.append([term, start, end])
        at = end
    entries = []
    for i, (term, start, end) in enumerate(found):
        stop = found[i + 1][1] if i + 1 < len(found) else len(stream)
        text_ = re.sub(r"(?<=\S)-\n(?=\S)", "-", stream[end:stop])   # a hyphen at a line end joins, with no space
        entries.append(dict(term=term, definition=" ".join(text_.split()), edition=EDITION))
    return entries, problems


def parse():
    raw, layout = text("-raw"), text("-layout")
    first, problems = first_pass(raw, layout)
    terms, unused = corrected_terms(first)
    problems = [f"correction not used: {t}" for t in unused]
    entries, more = segment(raw, terms)
    problems += more
    long_terms = []
    for e in entries:
        if "carnegie" in e["term"].lower():
            e["historical"] = "yes"
            e["note"] = "Carnegie 2000 or 2005 classification; not the 2021 classification the app's groups use"
        stray = re.search(r"\.\s(\d{1,2})$", e["definition"])
        if stray:                       # kept as printed: it is inside the definition's cell on the page, not a page number
            e["note"] = "; ".join(x for x in (e.get("note"), f"ends with a stray \"{stray.group(1)}\" as printed") if x)
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
    return entries, problems, long_terms, first


if __name__ == "__main__":
    entries, problems, long_terms, first = parse()
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["term", "definition", "edition", "historical", "note"], lineterminator="\n", restval="")
        w.writeheader()
        w.writerows(entries)
    print(f"{len(entries)} terms written to {OUT}")
    print(f"{len(problems)} entries not separated cleanly:" if problems else "every entry separated cleanly")
    for p in problems:
        print("  " + p)
    print(f"{len(long_terms)} long terms, kept as they are (check):")
    for t in long_terms:
        print("  " + t)
    before = {e["term"]: e["definition"] for e in first}
    changed = [e["term"] for e in entries if e["term"] in before and before[e["term"]] != e["definition"]]
    print(f"{len(changed)} definitions differ from the first pass (the corrected entries' neighbours are expected):")
    for t in changed:
        print("  " + t)
    sys.exit(0)
