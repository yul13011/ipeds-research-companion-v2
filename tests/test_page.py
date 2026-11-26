"""Part 6b: the pieces behind the page that are not the page itself: the codebook search, the figures the page states
about itself, the error kinds, the 30-second limit, the picker's Cancel and the page content files."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config
from path import answer, interpret
from tools import about, codebook


@unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built")
class Codebook(unittest.TestCase):
    def test_whole_words_rank_first(self):
        top = codebook.search("graduate enrollment", [2024])[:3]
        self.assertTrue(all("undergraduate" not in r["title"].lower() for r in top))
        self.assertIn("EFGRAD", [r["variable"] for r in top])

    def test_an_exact_variable_name_comes_first_and_years_filter(self):
        r = codebook.search("EFGRAD", [2023])
        self.assertEqual((r[0]["variable"], r[0]["year"], r[0]["release"]), ("EFGRAD", 2023, "2023-24"))
        self.assertTrue(all(x["year"] == 2023 for x in r))

    def test_tables_and_coded_categories(self):
        self.assertIn("table", {r["kind"] for r in codebook.search("directory information", [2024])})
        self.assertNotIn("code", {r["kind"] for r in codebook.search("private not-for-profit", [2024])})
        self.assertIn("code", {r["kind"] for r in codebook.search("private not-for-profit", [2024], codes=True)})

    def test_a_coded_variable_shows_its_codes(self):
        control = next(r for r in codebook.search("control of institution", [2024]) if r["variable"] == "CONTROL")
        self.assertIn(("1", "Public"), codebook.detail(control))

    def test_nothing_typed_finds_nothing(self):
        self.assertEqual(codebook.search("   "), [])


@unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built")
class About(unittest.TestCase):
    def test_the_releases_line_comes_from_the_database(self):
        self.assertEqual(about.releases_line(), "10 annual releases · 2015–16 Final through 2024–25 Provisional")

    def test_match_rates_count_tolerances_and_leave_out_declines(self):
        import csv
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "b.csv"
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["source", "status"])
                w.writerows([["Yale", "match"], ["Yale", "within 0.1%"], ["Yale", "differs"], ["Yale", "app decline"],
                             ["NCES", "not covered"]])
            self.assertEqual(about.match_rates(path), [("Yale", "Yale University figures", 2, 3)])
            self.assertEqual(about.match_rates(Path(d) / "none.csv"), [])


class Errors(unittest.TestCase):
    def test_error_kinds_come_from_the_api_error_type(self):
        self.assertEqual(answer.error_kind("APITimeoutError: Request timed out."), "timeout")
        self.assertEqual(answer.error_kind("BadRequestError: You have reached your specified API usage limits."), "limit")
        self.assertEqual(answer.error_kind("AuthenticationError: invalid x-api-key"), "access")
        self.assertEqual(answer.error_kind("APIConnectionError: Connection error."), "down")
        self.assertIsNone(answer.error_kind("ValueError: the reply was not valid"))   # "could not read"
        self.assertIsNone(answer.error_kind(None))

    def test_a_timeout_is_not_retried_but_other_failures_are(self):
        class APITimeoutError(Exception):
            pass
        calls = []
        def timing_out(*a):
            calls.append(1)
            raise APITimeoutError("Request timed out.")
        meta = dict(calls=0, attempts=0, input_tokens=0, output_tokens=0, cache_write_tokens=0, cache_read_tokens=0)
        self.assertIsNone(interpret.one_call("s", "u", "m", {}, {"tags": {}}, timing_out, meta))
        self.assertEqual(len(calls), 1)
        def failing(*a):
            calls.append(1)
            raise ValueError("bad")
        interpret.one_call("s", "u", "m", {}, {"tags": {}}, failing, meta)
        self.assertEqual(len(calls), 3)

    def test_the_time_limit_is_thirty_seconds(self):
        self.assertEqual(config.CALL_SECONDS, 30)


class Picker(unittest.TestCase):
    def test_cancel_drops_the_waiting_request(self):
        before, waiting = {"operation": "schools"}, {"operation": "schools", "schools": []}
        state = {"history": [before, waiting], "picker": {"request": waiting}}
        answer.cancel(state)
        self.assertEqual((state["history"], state["picker"]), ([before], None))


class Content(unittest.TestCase):
    def test_six_topics_with_three_examples_and_unique_ids(self):
        topics = json.loads((ROOT / "page" / "explore.json").read_text(encoding="utf-8"))["topics"]
        self.assertEqual(len(topics), 6)
        ids = [e["id"] for t in topics for e in t["examples"]]
        self.assertEqual((len(ids), len(set(ids))), (18, 18))
        for t in topics:
            self.assertTrue(all(t[k] for k in ("title", "subtitle", "icon", "summary", "description", "scope")))

    def test_every_example_is_in_the_question_set(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        sys.path.insert(0, str(ROOT.parent / "agent-redesign" / "evaluations"))
        import stage4_run
        norm = lambda q: q.replace("’", "'").replace("–", "-").replace("—", "-").strip().lower()
        held = {norm(q) for _, _, turns in stage4_run.conversations() for _, q, _ in turns}
        topics = json.loads((ROOT / "page" / "explore.json").read_text(encoding="utf-8"))["topics"]
        self.assertEqual([e["question"] for t in topics for e in t["examples"] if norm(e["question"]) not in held], [])

    def test_the_wording_drafts_fill_in(self):
        wording = json.loads((ROOT / "page" / "wording.json").read_text(encoding="utf-8"))
        for key, text in wording.items():
            if not key.startswith("_"):
                text.format(model="Haiku", seconds=30, release="2024-25")

    def test_hosting_requirements_leave_out_playwright(self):
        self.assertNotIn("playwright", (ROOT / "requirements.txt").read_text().lower())
        self.assertIn("streamlit==1.66.0", (ROOT / "requirements.txt").read_text())


if __name__ == "__main__":
    unittest.main()
