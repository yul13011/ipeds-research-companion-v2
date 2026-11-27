"""Downloads (Part 6c): CSV and Excel with a sources sheet, made from the answer's own page object, so a download
carries exactly the figures, periods, notes and definitions on screen. Adapted from version 1's exports.py
(agent-redesign/prototype/exports.py, read only): its formula guard and sheet layout; rewritten for version 2's page.
"""
import io

import pandas as pd


def safe(value):
    """Text a spreadsheet would read as a formula gets a leading apostrophe (version 1's guard). A negative figure
    such as "-1.5" stays as it is."""
    if isinstance(value, str) and value[:1] in "=+@" or isinstance(value, str) and value[:1] == "-" and not value[1:2].isdigit():
        return "'" + value
    return value


def parts(page):
    """The answers in a turn: one, or each part of several answered together."""
    return [p for p in (page.get("pages") or [page]) if p.get("kind") == "answer" and (p.get("table") or {}).get("rows")]


def table(part, name="table"):
    t = part[name]
    return pd.DataFrame([[safe(v) for v in row] for row in t["rows"]], columns=t["columns"])


def csv_bytes(part):
    """The table as shown, cell for cell. UTF-8 with a byte-order mark, so Excel opens accents correctly."""
    return table(part).to_csv(index=False).encode("utf-8-sig")


def notes(part):
    """Everything said around the table, in the order the page shows it."""
    rows = [("Interpreted as", part.get("interpreted"))]
    rows += [("Summary", part["summary"])] if part.get("summary") else []
    rows += [("Warning", w) for w in part.get("warnings") or []]
    rows += [("Note", n) for n in part.get("notes") or []]
    rows += [("Data status", s) for s in part.get("status") or []]
    rows += [("Data release", part["data_release"])] if part.get("data_release") else []
    return pd.DataFrame([(k, safe(v)) for k, v in rows if v], columns=["Item", "Text"])


def sources(part):
    keys = [("measure", "Measure"), ("scope", "Scope"), ("period", "Reporting period"), ("definition", "Definition"),
            ("calculation", "Calculation"), ("sources", "Source tables"), ("notes", "Note on words")]
    return pd.DataFrame([[safe(d.get(k) or "") for k, _ in keys] for d in part.get("definitions") or []],
                        columns=[label for _, label in keys])


def excel_bytes(part):
    """Sheets: Data (the table), Underlying counts (when shown), Notes, Sources (definitions and source tables)."""
    sheets = [("Data", table(part))]
    if (part.get("counts") or {}).get("rows"):
        sheets.append(("Underlying counts", table(part, "counts")))
    sheets += [("Notes", notes(part)), ("Sources", sources(part))]
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for name, df in sheets:
            df.to_excel(writer, sheet_name=name, index=False)
            ws = writer.sheets[name]
            ws.freeze_panes = "A2"
            for col in ws.columns:
                width = max(len(str(c.value or "")) for c in col) + 2
                ws.column_dimensions[col[0].column_letter].width = min(80, max(14, width))
    return out.getvalue()

