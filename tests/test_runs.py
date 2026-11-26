"""The question-set runner (scripts/stage4_run.py, owner decision 2026-11-26): parallel conversations merged into one
run, and the wait-and-retry when the API refuses a call for rate limits. No API calls; nothing written to a shared log."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import anthropic
import httpx

import config
import stage4_run as run
from path import interpret
from test_path import M, S, reply_request, req, saved


def refused(wait="0"):
    response = httpx.Response(429, headers={"retry-after": wait}, request=httpx.Request("POST", "https://api.anthropic.com"))
    return anthropic.RateLimitError("rate limited", response=response, body=None)


class Runner(unittest.TestCase):
    def test_a_call_refused_for_rate_limits_waits_and_is_retried(self):
        answers = iter([refused(), refused(), "reply"])

        def call(*a):
            x = next(answers)
            if isinstance(x, Exception):
                raise x
            return x
        waits = []
        with mock.patch("time.sleep") as sleep:
            self.assertEqual(run.patient(call, waits)(), "reply")
        self.assertEqual(waits, [0.0, 0.0])                 # the wait the API asked for, recorded
        self.assertEqual(sleep.call_count, 2)

    def test_conversations_run_apart_and_merge_into_one_run_in_order(self):
        yale = req("schools", measures=[M("DRVEF.ENRTOT")], schools=[S("Yale", 130794)])
        harvard = req("schools", measures=[M("DRVEF.ENRTOT")], schools=[S("Harvard", 166027)])
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(config, "SUMMARY", False):
            folder, parts = Path(tmp), []
            for i, (case, r) in enumerate([("b", harvard), ("a", yale)]):
                part = folder / "parts" / f"{i:04d}"
                with mock.patch.object(interpret, "call_api", saved(reply_request(r))):
                    run.run_conversation((i, "log", case, [(1, f"enrollment {case}", False)], str(part), "m", 4))
                parts.append(part)
            run.merge(parts, folder)
            turns = [json.loads(x) for x in (folder / "turns.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([t["case"] for t in turns], ["b", "a"])          # the usual order, not finishing order
            self.assertEqual([t["workers"] for t in turns], [4, 4])
            self.assertEqual(len((folder / "questions.jsonl").read_text(encoding="utf-8").splitlines()), 2)
            self.assertFalse((folder / "parts").exists())


if __name__ == "__main__":
    unittest.main()
