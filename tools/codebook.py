"""The definitions browser's search (Part 6b): finds tables and variables in the IPEDS codebooks held in the local
database (VARTABLE, TABLES and, when asked, VALUESETS) and shows the codebook's own words.

A text search, like the school search: it finds records that contain every word typed. It never decides what a
question means and makes no model call. Records are ranked: an exact table or variable name first, then the words
as a phrase in a title, then all the words in a title, then in a description.
"""
import re
import sqlite3

import config

KINDS = {"variable": "variable_definition", "table": "table_definition", "code": "coded_category"}   # version 1's record types


def label(year):
    return f"{year}-{(year + 1) % 100:02d}"


def connect(db_path=None):
    return sqlite3.connect(f"file:{(db_path or config.LOCAL_DB.as_posix())}?mode=ro", uri=True)


def score(words, phrase, name, title, text):
    """Whole words only: "graduate" ranks "graduate enrollment" above "undergraduate enrollment"."""
    name, title, text = (name or "").lower(), (title or "").lower(), (text or "").lower()
    has = lambda s, part: re.search(r"(?<![a-z0-9])" + re.escape(part) + r"(?![a-z0-9])", s) is not None
    if phrase == name:
        return 100
    if has(title, phrase):
        return 50
    if all(has(title, w) for w in words):
        return 30
    if has(text, phrase):
        return 10
    return 5


def search(query, years=None, limit=40, codes=False, db_path=None):
    """Records for `query` in the chosen release years (all ten when empty), best first, at most `limit`."""
    words = [w for w in query.lower().split() if w]
    if not words:
        return []
    phrase = " ".join(words)
    years = list(years or [])
    where_years = f" AND year IN ({','.join('?' * len(years))})" if years else ""
    out = []
    db = connect(db_path)
    try:
        sources = [("variable", "SELECT year, TableName, varName, varTitle, longDescription FROM VARTABLE",
                    "(varName || ' ' || varTitle || ' ' || coalesce(longDescription, ''))"),
                   ("table", "SELECT year, TableName, TableName, TableTitle, Description FROM TABLES",
                    "(TableName || ' ' || TableTitle || ' ' || coalesce(Description, ''))")]
        if codes:
            sources.append(("code", "SELECT year, TableName, varName, varTitle || ': ' || valueLabel, "
                                    "'Code ' || Codevalue || ' means ' || valueLabel FROM VALUESETS",
                            "(varName || ' ' || varTitle || ' ' || valueLabel)"))
        for kind, select, field in sources:
            sql = select + " WHERE " + " AND ".join(f"lower{field} LIKE ?" for _ in words) + where_years
            for year, table, name, title, text in db.execute(sql, [f"%{w}%" for w in words] + years):
                out.append(dict(kind=kind, year=year, release=label(year), table=table,
                                variable=name if kind != "table" else None, title=title, text=text or "",
                                score=score(words, phrase, name, title, text)))
    finally:
        db.close()
    out.sort(key=lambda r: (-r["score"], -r["year"], r["table"], r["variable"] or ""))
    return out[:limit]


def detail(record, db_path=None):
    """A variable's coded categories in its release year ([(code, meaning)]); empty for a table or uncoded variable."""
    if record["kind"] != "variable":
        return []
    db = connect(db_path)
    try:
        return db.execute("SELECT Codevalue, valueLabel FROM VALUESETS WHERE year = ? AND TableName = ? AND varName = ? "
                          "ORDER BY valueOrder", (record["year"], record["table"], record["variable"])).fetchall()
    finally:
        db.close()
