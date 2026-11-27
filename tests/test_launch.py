"""Part 6c and 6f: downloads that match the screen, the spending guard, the data download at start-up, the owner's log
zip and the hosted-log script. No test calls the API, uses the network or writes to a shared log."""
import csv
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import config
import hosted_log
import serve
from path import answer, request as rq
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


class HostedLog(unittest.TestCase):
    def test_log_zip_and_rows(self):
        with tempfile.TemporaryDirectory() as d:
            lines = [dict(conversation="aaa", question="Yale admission rate", outcome="ready"),
                     dict(conversation="aaa", question="[option] Total", outcome="ready"),
                     dict(conversation="bbb", question="hi", outcome="limit_daily"),
                     dict(conversation="ccc", question="Harvard", outcome="decline"),
                     dict(conversation="aaa", question="yale admission rate", outcome="ready")]
            (Path(d) / "questions.jsonl").write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
            (Path(d) / "spend.json").write_text("{}", encoding="utf-8")
            rows = hosted_log.rows(d)
            self.assertEqual([(r["conversation"], r["turn"], r["repeat"]) for r in rows],
                             [("h1", 1, "no"), ("h2", 1, "no"), ("h1", 2, "yes")])
            self.assertNotIn("aaa", json.dumps(rows))
            names = zipfile.ZipFile(io.BytesIO(downloads.log_zip(Path(d)))).namelist()
            self.assertEqual(sorted(names), ["questions.jsonl", "spend.json"])


if __name__ == "__main__":
    unittest.main()
