"""Local logs: one line per question, and one line per decline. Never the version 1 Google Sheet.

Each line is one JSON object, so the logs open in R with jsonlite::stream_in() or in Python with pandas.
Tests pass their own folder, so they never write to the shared log. The day's API spend is kept beside the logs
(spend.json), for the spending guard.
"""
import datetime
import json
import threading
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import config

_SPEND = threading.Lock()                               # several visitors share one process


class Log:
    def __init__(self, folder=None):
        self.folder = Path(folder or config.LOG_DIR)
        self.folder.mkdir(parents=True, exist_ok=True)

    def write(self, name, row):
        row = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), **row)
        with open(self.folder / name, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")

    def question(self, row):
        self.write("questions.jsonl", row)

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
