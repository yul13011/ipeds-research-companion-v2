"""Part 6c and 6f: downloads that match the screen, the spending guard, the data download at start-up, the question
sheet and the hosted-log script. No test calls the API, uses the network or writes to a shared log."""
import csv
import hashlib
import io
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import config
import hosted_log
import serve
from path import answer, log, request as rq
from path.log import Log
from tools import downloads

REPLIES = Path(__file__).with_name("replies")


def saved(reply):
    return lambda system, user, model, schema=None: (json.dumps(reply), {"input_tokens": 1000, "output_tokens": 100})


def no_call(*a, **k):
    raise AssertionError("the model was called")


def unguard(text):
    return text[1:] if isinstance(text, str) and text.startswith("'") else text


@unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built")
class Downloads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.log = Log(cls.dir.name)

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def page(self, name=None, request=None, question="q"):
        if name:
            case = json.loads((REPLIES / f"{name}.json").read_text(encoding="utf-8"))
            question, reply = case["question"], case["reply"]
        else:
            reply = dict(kind="request", request=request, edit=None, options=[], chosen=[], decline=None)
        page = answer.ask(question, {}, self.log, call=saved(reply))
        self.assertEqual(page["kind"], "answer")
        return page

    def same_as_screen(self, page):
        shown = [page["table"]["columns"]] + page["table"]["rows"]
        got = list(csv.reader(io.StringIO(downloads.csv_bytes(page).decode("utf-8-sig"))))
        self.assertEqual([[unguard(c) for c in r] for r in got], [[str(c) for c in r] for r in shown])
        book = pd.read_excel(io.BytesIO(downloads.excel_bytes(page)), sheet_name=None, dtype=str, keep_default_na=False)
        data = book["Data"]
        self.assertEqual([list(data.columns)] + [[unguard(c) for c in r] for r in data.values.tolist()],
                         [[str(c) for c in r] for r in shown])
        self.assertEqual(list(book["Sources"]["Measure"]), [d["measure"] for d in page["definitions"]])
        self.assertIn(page["interpreted"], list(book["Notes"]["Text"]))
        for note in page["notes"] + page["warnings"]:
            self.assertIn(note, list(book["Notes"]["Text"]))
        if page["counts"]["rows"]:
            self.assertEqual(len(book["Underlying counts"]), len(page["counts"]["rows"]))

    def test_a_trend(self):
        r = rq.empty("schools")
        r.update(measures=[dict(id="DRVADM.DVADM01", row=[])], schools=[dict(name="Yale", id=130794)],
                 year=dict(rq.no_year(), span="a range of years", start=2020, end=2024))
        page = self.page(request=r, question="Yale admission rate 2020 to 2024")
        self.assertGreater(len(page["table"]["rows"]) * len(page["table"]["columns"]), 5)
        self.same_as_screen(page)

    def test_a_group_figure(self):
        self.same_as_screen(self.page("e_group_grad"))

    def test_a_breakdown(self):
        self.same_as_screen(self.page("d_yale_race"))

    def test_formula_guard(self):
        self.assertEqual(downloads.safe("=SUM(A1)"), "'=SUM(A1)")
        self.assertEqual(downloads.safe("@x"), "'@x")
        self.assertEqual(downloads.safe("-1.5"), "-1.5")
        self.assertEqual(downloads.safe(3), 3)


class Guard(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.log = Log(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def last_line(self):
        return json.loads((Path(self.dir.name) / "questions.jsonl").read_text(encoding="utf-8").splitlines()[-1])

    def test_the_daily_limit_stops_before_the_model(self):
        self.log.add_spend(1.5)
        self.log.add_spend(0.6)
        self.assertAlmostEqual(self.log.spent_today(), 2.1)
        with mock.patch.object(config, "DAILY_USD", 2.0):
            page = answer.ask("Yale admission rate", {}, self.log, call=no_call)
        self.assertEqual(page["error"], "daily")
        self.assertEqual(self.last_line()["outcome"], "limit_daily")

    def test_the_conversation_limit(self):
        state = dict(questions=40)
        with mock.patch.object(config, "CONVERSATION_QUESTIONS", 40):
            page = answer.ask("Yale admission rate", state, self.log, call=no_call)
        self.assertEqual(page["error"], "conversation")
        self.assertEqual(self.last_line()["outcome"], "limit_conversation")

    def test_no_limits_by_default_and_a_new_day_starts_at_zero(self):
        self.assertIsNone(answer.over_limit(dict(questions=1000), self.log))
        (Path(self.dir.name) / "spend.json").write_text(json.dumps(dict(day="2000-01-01", usd=99)), encoding="utf-8")
        self.assertEqual(self.log.spent_today(), 0.0)

    def test_the_messages_exist(self):
        wording = json.loads((ROOT / "page" / "wording.json").read_text(encoding="utf-8"))
        self.assertIn("come back tomorrow", wording["error_daily"])
        self.assertIn("40 questions", wording["error_conversation"])


class FakeResponse:
    def __init__(self, data):
        self.data, self.text = data, data.decode() if len(data) < 200 else ""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        for i in range(0, len(self.data), chunk_size):
            yield self.data[i:i + chunk_size]


class Serve(unittest.TestCase):
    def fake(self, data, checksum):
        calls = []

        def get(url, **k):
            calls.append(url)
            return FakeResponse(checksum.encode() if url.endswith(".sha256") else data)
        return get, calls

    def test_download_once_checked_and_marked(self):
        data = b"sqlite" * 1000
        get, calls = self.fake(data, hashlib.sha256(data).hexdigest() + "  ipeds_v2.sqlite\n")
        with tempfile.TemporaryDirectory() as d:
            path = serve.ensure_data(d, "owner/set", "abc123", get=get)
            self.assertEqual(path.read_bytes(), data)
            self.assertIn("huggingface.co/datasets/owner/set/resolve/abc123/ipeds_v2.sqlite", calls[-1])
            serve.ensure_data(d, "owner/set", "abc123", get=get)
            self.assertEqual(len(calls), 2)                 # the second start downloads nothing

    def test_a_wrong_checksum_keeps_nothing(self):
        get, _ = self.fake(b"broken", "0" * 64)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):
                serve.ensure_data(d, "owner/set", "abc123", get=get)
            self.assertEqual(list((Path(d) / "abc123").iterdir()), [])


class Sheet(unittest.TestCase):
    """The hosted question sheet, with a stand-in worksheet: no network, no Google account."""
    ROW = dict(conversation="abc", turn=2, question="Ivies plus MIT", outcome="ready", model="claude-haiku-5-5",
               seconds=4.2, cost_usd=0.0012, request=dict(operation="group", measures=[dict(id="DRVEF.ENRTOT", row=[])],
               schools=[dict(name="Yale", id=130794)], groups=["Ivy League"], plus_schools=[166683], peers_of=None))

    def test_one_row_per_turn_in_the_agreed_columns(self):
        row = dict(zip(log.COLUMNS, log.sheet_row(self.ROW)))
        self.assertEqual((row["conversation"], row["turn"], row["outcome"], row["operation"], row["measures"]),
                         ("abc", 2, "ready", "group", "DRVEF.ENRTOT"))
        self.assertEqual(row["schools_or_group"], "Ivy League; Yale; +166683")
        self.assertEqual((row["model"], row["seconds"], row["cost_usd"], row["decline_reason"]), ("claude-haiku-5-5", 4.2, 0.0012, ""))
        declined = dict(zip(log.COLUMNS, log.sheet_row(dict(outcome="decline", missing="not collected", question="x"))))
        self.assertEqual((declined["decline_reason"], declined["operation"]), ("not collected", ""))

    def test_only_the_apps_own_log_with_both_values_writes(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(config, "QUESTIONS_SHEET", "sheet-id"), mock.patch.object(config, "SHEET_CREDENTIALS", "{}"):
                self.assertFalse(Log(d).to_sheet)               # tests and question-set runs pass their own folder
                with mock.patch.object(config, "LOG_DIR", Path(d)):
                    self.assertTrue(Log().to_sheet)
            with mock.patch.object(config, "LOG_DIR", Path(d)):
                self.assertFalse(Log().to_sheet)                # no sheet values: the local default

    def test_a_failed_write_keeps_the_disk_log(self):
        class Broken:
            def append_row(self, *a, **k):
                raise ConnectionError("offline")
        with tempfile.TemporaryDirectory() as d, mock.patch.object(config, "LOG_DIR", Path(d)),                 mock.patch.object(config, "QUESTIONS_SHEET", "sheet-id"), mock.patch.object(config, "SHEET_CREDENTIALS", "{}"),                 mock.patch.object(log, "open_sheet", lambda: Broken()), self.assertLogs("question_sheet", "ERROR"):
            Log().question(dict(self.ROW))
            time.sleep(0.5)                                     # the write runs on its own thread
            self.assertEqual(json.loads((Path(d) / "questions.jsonl").read_text(encoding="utf-8"))["question"], "Ivies plus MIT")
        written = []

        class Good:
            def append_row(self, values, **k):
                written.append(values)
        with mock.patch.object(log, "open_sheet", lambda: Good()):
            log.to_sheet(log.sheet_row(self.ROW)).join(5)
        self.assertEqual(written[0][3], "Ivies plus MIT")


class SheetColumns(unittest.TestCase):
    """The four columns added on 2026-11-27, after the first twelve."""
    def test_the_added_columns_follow_the_first_twelve(self):
        self.assertEqual(log.COLUMNS[:12], ("time", "conversation", "turn", "question", "outcome", "decline_reason",
                                            "operation", "measures", "schools_or_group", "model", "seconds", "cost_usd"))
        self.assertEqual(log.COLUMNS[12:], ("interpreted_as", "n_rows", "had_value", "app_version"))

    @unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built")
    def test_an_answer_fills_them_from_what_was_shown(self):
        case = json.loads((REPLIES / "a_yale_admission.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            page = answer.ask(case["question"], {}, Log(d), call=saved(case["reply"]))
            line = json.loads((Path(d) / "questions.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        with mock.patch.object(config, "APP_VERSION", "737dafd"):
            row = dict(zip(log.COLUMNS, log.sheet_row(line)))
        self.assertEqual(row["interpreted_as"], page["interpreted"])
        self.assertEqual((row["n_rows"], row["had_value"], row["app_version"]), (len(page["table"]["rows"]), True, "737dafd"))

    def test_several_answers_and_a_decline(self):
        many = dict(outcome="many", parts=[dict(request=dict(operation="schools"), rows=2, interpreted="A", had_value=False),
                                           dict(request=dict(operation="rank"), rows=3, interpreted="B", had_value=True)])
        row = dict(zip(log.COLUMNS, log.sheet_row(many)))
        self.assertEqual((row["interpreted_as"], row["n_rows"], row["had_value"]), ("A | B", 5, True))
        row = dict(zip(log.COLUMNS, log.sheet_row(dict(outcome="decline", missing="not collected"))))
        self.assertEqual((row["interpreted_as"], row["n_rows"], row["had_value"]), ("", "", ""))

    def test_an_existing_twelve_column_header_is_extended_in_place(self):
        class Sheet:
            col_count = 12
            def __init__(self, first): self.first, self.updated, self.added = first, None, 0
            def row_values(self, n): return list(self.first)
            def add_cols(self, n): self.added += n
            def update(self, range_name, values): self.updated = values[0]
        class Book:
            def __init__(self, ws): self.ws = ws
            def worksheet(self, name): return self.ws
        for first, ok in [(log.COLUMNS[:12], True), ((), True), (("something", "else"), False)]:
            ws = Sheet(first)
            client = mock.Mock(open_by_key=lambda ref: Book(ws))
            gspread = mock.Mock(service_account_from_dict=lambda creds: client, WorksheetNotFound=KeyError)
            with mock.patch.dict(sys.modules, gspread=gspread), mock.patch.dict(log._SHEET, worksheet=None),                     mock.patch.object(config, "SHEET_CREDENTIALS", "{}"), mock.patch.object(config, "QUESTIONS_SHEET", "id"):
                if ok:
                    log.open_sheet()
                    self.assertEqual((ws.updated, ws.added), (list(log.COLUMNS), 4))
                else:
                    with self.assertRaises(RuntimeError):
                        log.open_sheet()
                    self.assertIsNone(ws.updated)


class HostedLog(unittest.TestCase):
    def test_rows_from_the_sheet_export(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sheet.csv"
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(log.COLUMNS)
                for conv, q, outcome in [("aaa", "Yale admission rate", "ready"), ("aaa", "[option] Total", "ready"),
                                         ("bbb", "hi", "limit_daily"), ("ccc", "Harvard", "decline"),
                                         ("aaa", "yale admission rate", "ready")]:
                    w.writerow(["2026-11-27 10:00:00", conv, 1, q, outcome, "", "", "", "", "", 1.0, 0.001, "", "", "", ""])
            rows = hosted_log.rows(path)
            self.assertEqual([(r["conversation"], r["turn"], r["repeat"]) for r in rows],
                             [("h1", 1, "no"), ("h2", 1, "no"), ("h1", 2, "yes")])
            self.assertNotIn("aaa", json.dumps(rows))


if __name__ == "__main__":
    unittest.main()
