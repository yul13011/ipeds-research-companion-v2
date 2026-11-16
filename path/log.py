"""Local logs: one line per question, and one line per decline. Never the version 1 Google Sheet.

Each line is one JSON object, so the logs open in R with jsonlite::stream_in() or in Python with pandas.
Tests pass their own folder, so they never write to the shared log.
"""
import json
import time
from pathlib import Path

import config


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
