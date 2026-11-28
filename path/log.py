"""Local logs: one line per question, and one line per decline. Never the version 1 Google Sheet.

Each line is one JSON object, so the logs open in R with jsonlite::stream_in() or in Python with pandas.
Tests pass their own folder, so they never write to the shared log. The day's API spend is kept beside the logs
(spend.json), for the spending guard.

On the host, each question is also added as one row to version 2's Google Sheet (owner decision 2026-11-27), when both
sheet values are set in config.py. Only the app's own log (no folder given) writes to the sheet, so tests and question-set
runs never do. Adapted from version 1's question_log.py (agent-redesign/prototype/question_log.py, read only): the
write runs on a background thread and a failure is only noted, so the answer always shows and the disk log keeps the
turn.
"""
import datetime
import json
import logging
import threading
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import config

_SPEND = threading.Lock()                               # several visitors share one process
COLUMNS = ("time", "conversation", "turn", "question", "outcome", "decline_reason", "operation", "measures",
           "schools_or_group", "model", "seconds", "cost_usd",
           "interpreted_as", "n_rows", "had_value", "app_version")   # added 2026-11-27, after the first twelve
_SHEET = dict(lock=threading.Lock(), worksheet=None)
_note = logging.getLogger("question_sheet")


class Log:
    def __init__(self, folder=None):
        self.folder = Path(folder or config.LOG_DIR)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.to_sheet = folder is None and bool(config.QUESTIONS_SHEET and config.SHEET_CREDENTIALS)

    def write(self, name, row):
        row = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), **row)
        with open(self.folder / name, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")

    def question(self, row):
        self.write("questions.jsonl", row)
        if self.to_sheet:
            to_sheet(sheet_row(row))

    def decline(self, row):
        self.write("declines.jsonl", row)

    def summary(self, row):
        self.write("summaries.jsonl", row)

    def spent_today(self):
        """US$ of model calls today (Eastern time)."""
        day = datetime.datetime.now(ZoneInfo(config.DAY_ZONE)).date().isoformat()
        try:
            kept = json.loads((self.folder / "spend.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            kept = {}
        return kept.get("usd", 0.0) if kept.get("day") == day else 0.0

    def add_spend(self, usd):
        if not usd:
            return
        with _SPEND:
            day = datetime.datetime.now(ZoneInfo(config.DAY_ZONE)).date().isoformat()
            total = self.spent_today() + usd
            (self.folder / "spend.json").write_text(json.dumps(dict(day=day, usd=round(total, 6))), encoding="utf-8")


def sheet_row(row):
    """One turn's log line as the sheet's columns. The request's parts come from the resolved request (or each part's,
    when several were answered together)."""
    requests = [row["request"]] if row.get("request") else [p["request"] for p in row.get("parts") or [] if p.get("request")]
    answers = [row] if row.get("request") else [p for p in row.get("parts") or [] if p.get("request")]
    counted = [a["rows"] for a in answers if a.get("rows") is not None]
    def each(get):
        return "; ".join(dict.fromkeys(x for r in requests for x in get(r)))
    scope = lambda r: list(r.get("groups") or []) + [s.get("name") or str(s.get("id")) for s in r.get("schools") or []] +         [f"+{u}" for u in r.get("plus_schools") or []] + ([f"peers of {r['peers_of']}"] if r.get("peers_of") else [])
    values = dict(time=datetime.datetime.now(ZoneInfo(config.DAY_ZONE)).strftime("%Y-%m-%d %H:%M:%S"),
                  conversation=row.get("conversation"), turn=row.get("turn"), question=row.get("question"),
                  outcome=row.get("outcome"), decline_reason=row.get("missing") or row.get("detail") or row.get("error_kind"),
                  operation=each(lambda r: [r.get("operation") or ""]), measures=each(lambda r: [m["id"] for m in r.get("measures") or []]),
                  schools_or_group=each(scope), model=row.get("model"), seconds=row.get("seconds"), cost_usd=row.get("cost_usd"),
                  interpreted_as=" | ".join(a["interpreted"] for a in answers if a.get("interpreted")),
                  n_rows=sum(counted) if counted else None,
                  had_value=any(bool(a.get("had_value")) for a in answers) if counted else None,
                  app_version=config.APP_VERSION)
    return ["" if values[c] is None else values[c] for c in COLUMNS]


def open_sheet():
    """The worksheet, opened once (network). None when it can't be opened; tried again on the next question."""
    if _SHEET["worksheet"] is None:
        import gspread
        client = gspread.service_account_from_dict(json.loads(config.SHEET_CREDENTIALS))
        ref = config.QUESTIONS_SHEET
        book = client.open_by_url(ref) if "://" in ref else client.open_by_key(ref)
        try:
            ws = book.worksheet(config.SHEET_TAB)
        except gspread.WorksheetNotFound:
            ws = book.add_worksheet(title=config.SHEET_TAB, rows=1000, cols=len(COLUMNS))
        first = ws.row_values(1)
        if first != list(COLUMNS):
            if first != list(COLUMNS[:len(first)]):         # empty, or an earlier header that these columns extend
                raise RuntimeError("the sheet's first row is not version 2's header; nothing is written over it")
            if ws.col_count < len(COLUMNS):
                ws.add_cols(len(COLUMNS) - ws.col_count)
            ws.update(range_name="A1", values=[list(COLUMNS)])
        _SHEET["worksheet"] = ws
    return _SHEET["worksheet"]


def to_sheet(values):
    """Add one row on a background thread. A failure is noted in the host's log only; the disk log already has the turn."""
    def add():
        try:
            with _SHEET["lock"]:
                open_sheet().append_row(values, value_input_option="RAW")
        except Exception:
            _note.exception("question sheet: the row was not written (it is in the disk log)")
    thread = threading.Thread(target=add, daemon=True)
    thread.start()
    return thread
