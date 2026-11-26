"""The page, driven by Streamlit's own test runner. The model call is replaced by saved replies, and the page's log
is pointed at a temporary folder, so nothing reaches the API or the shared log.

Part 6b: the page is version 1's (Explore IPEDS, Ask & Analyze with its two side panels, the definitions browser,
About), rewired to version 2."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from path import interpret, summary

ROOT = Path(__file__).resolve().parents[1]
REPLIES = Path(__file__).with_name("replies")


class APITimeoutError(Exception):
    """Stands in for the API's own timeout error: only its name is read."""


class RateLimitError(Exception):
    pass


@unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built")
class App(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest
        self.dir = tempfile.TemporaryDirectory()
        self.saved_log_dir, config.LOG_DIR = config.LOG_DIR, Path(self.dir.name)
        self.saved_call = interpret.call_api
        self.replies = []

        def fake(system, user, model, schema=None):
            reply = self.replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return json.dumps(reply), {"input_tokens": 1, "output_tokens": 1}
        interpret.call_api = fake
        self.saved_summary = summary.call_api           # the written summary: a saved reply, never the API
        self.summary_text = "The table shows the figure asked for."
        summary.call_api = lambda system, user, model, on_text=None: (self.summary_text, {"input_tokens": 1, "output_tokens": 1})
        self.at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)

    def tearDown(self):
        interpret.call_api = self.saved_call
        summary.call_api = self.saved_summary
        config.LOG_DIR = self.saved_log_dir
        self.dir.cleanup()

    def chat(self):
        self.at.run()
        self.button("Ask & Analyze").click().run()

    def button(self, label):
        return next(b for b in self.at.button if b.label == label)

    def text(self):
        return " ".join([m.value for m in self.at.markdown] + [c.value for c in self.at.caption])

    def ask(self, name):
        case = json.loads((REPLIES / f"{name}.json").read_text(encoding="utf-8"))
        self.replies.append(case["reply"])
        self.at.chat_input[0].set_value(case["question"]).run()

    # Explore IPEDS
    def test_explore_shows_six_topics_and_the_releases_held(self):
        self.at.run()
        self.assertFalse(self.at.exception)
        self.assertEqual(sum(b.label == "Explore topic →" for b in self.at.button), 6)
        self.assertIn("10 annual releases · 2015–16 Final through 2024–25 Provisional", self.text())
        self.assertEqual(len(self.at.sidebar), 0)              # no sidebar, as in version 1

    def test_an_example_question_is_sent_to_the_chat(self):
        self.at.run()
        self.at.button(key="topic_admissions").click().run()
        self.assertIn("Ask your own question about admissions", [b.label for b in self.at.button])
        self.replies.append(json.loads((REPLIES / "a_yale_admission.json").read_text())["reply"])
        self.at.button(key="home_d_admissions-point").click().run()
        self.assertFalse(self.at.exception)
        self.assertIn("What was Yale’s admission rate in fall 2024?", self.text())
        self.assertEqual(self.at.dataframe[0].value.iloc[0, 0], "Yale University")

    # Ask & Analyze
    def test_answer_shows_interpreted_as_table_and_sources(self):
        self.chat()
        self.ask("a_yale_admission")
        self.assertFalse(self.at.exception)
        self.assertIn("Interpreted as:", self.text())
        self.assertEqual(len(self.at.dataframe), 1)            # one figure, no chart: the table is shown
        self.assertEqual(self.at.dataframe[0].value.iloc[0, 0], "Yale University")
        self.assertTrue(any("provisional" in w.value for w in self.at.warning))
        self.assertIn("Definitions & sources", str(self.at.get("popover")[0].proto))
        self.at.checkbox(key=next(c.key for c in self.at.checkbox if c.key.endswith("_counts"))).check().run()
        self.assertEqual(len(self.at.dataframe), 2)
        self.assertTrue((Path(self.dir.name) / "questions.jsonl").exists())

    def test_the_side_panels_and_the_menu(self):
        self.chat()
        self.assertIn("Need ideas?", self.text())
        self.assertIn("Browse definitions", self.text())
        self.at.button(key="collapse_ideas").click().run()
        self.assertIn("› Ideas", [b.label for b in self.at.button])
        self.button("Hide Menu").click().run()
        self.assertIn("Expand Menu", [b.label for b in self.at.button])

    def test_an_ideas_example_runs(self):
        self.chat()
        self.replies.append(json.loads((REPLIES / "a_yale_admission.json").read_text())["reply"])
        self.at.button(key="ideas_admissions-point").click().run()
        self.assertFalse(self.at.exception)
        self.assertEqual(len(self.at.dataframe), 1)

    def test_follow_up_and_clear(self):
        self.chat()
        self.ask("b_compare_grad")
        self.ask("i_add_northeastern")
        self.at.toggle[-1].set_value(True).run()
        self.assertEqual(len(self.at.dataframe[-1].value), 4)
        self.button("Clear conversation").click().run()
        self.assertEqual(len(self.at.dataframe), 0)

    def test_option_buttons_run_the_option(self):
        self.chat()
        self.replies.append(dict(kind="request", edit=None, options=[], chosen=[], decline=None,
                                 request=dict(json.loads((REPLIES / "a_yale_admission.json").read_text())["reply"]["request"],
                                              measures=[dict(id="EAP.EAPTOT", row=[])])))
        self.at.chat_input[0].set_value("How many faculty does Yale have?").run()
        self.assertIn("Choose an option, or type a change to refine it.", self.text())
        self.button("Instructional staff").click().run()
        self.assertFalse(self.at.exception)
        self.assertEqual(self.at.dataframe[-1].value.iloc[0, 1], "3,800")

    def test_a_trend_draws_a_chart_and_hides_the_table(self):
        """A chart is shown: "Display table" is off until the user turns it on (owner decision, 2026-11-26)."""
        self.chat()
        reply = json.loads((REPLIES / "a_yale_admission.json").read_text())["reply"]
        reply["request"]["year"] = dict(stated="since 2015", kind=None, start=2015, end=None, last=None, change=False,
                                        membership=None)
        self.replies.append(reply)
        self.at.chat_input[0].set_value("Yale's admission rate since 2015").run()
        self.assertFalse(self.at.exception)
        self.assertEqual(len(self.at.get("vega_lite_chart")), 1)
        self.assertEqual(len(self.at.dataframe), 0)
        self.at.toggle[0].set_value(True).run()
        self.assertEqual(list(self.at.dataframe[-1].value.columns[:2]), ["Year", "Period"])

    def test_one_figure_shows_a_tile_and_a_summary(self):
        self.chat()
        self.ask("a_yale_admission")
        self.assertEqual(len(self.at.metric), 1)
        self.assertIn("The table shows the figure asked for.", self.text())

    def test_a_summary_with_a_wrong_number_is_not_shown(self):
        self.summary_text = "The admission rate was 99.9%."
        self.chat()
        self.ask("a_yale_admission")
        self.assertNotIn("99.9%", self.text())

    def test_a_timeout_gets_a_friendly_message_and_no_turn(self):
        self.chat()
        self.replies.append(APITimeoutError("Request timed out."))
        self.at.chat_input[0].set_value("Yale's admission rate").run()
        self.assertFalse(self.at.exception)
        self.assertIn("longer than 30 seconds", self.at.error[0].value)
        self.assertEqual(len(self.at.chat_message), 0)         # no partial result
        self.assertEqual(len(self.replies), 0)                 # one call only: a timeout is not retried

    def test_an_api_failure_gets_a_friendly_message(self):
        self.chat()
        self.replies += [RateLimitError("busy"), RateLimitError("busy")]
        self.at.chat_input[0].set_value("Yale's admission rate").run()
        self.assertIn("couldn't be reached", self.at.error[0].value)

    def test_the_database_missing_gets_a_friendly_message(self):
        saved, config.LOCAL_DB = config.LOCAL_DB, Path(self.dir.name) / "missing.sqlite"
        try:
            self.at.run()
        finally:
            config.LOCAL_DB = saved
        self.assertIn("database isn't available", self.at.error[0].value)

    # Tools and About
    def test_the_definitions_browser_finds_a_variable(self):
        self.chat()
        self.button("Search definitions →").click().run()
        self.at.text_input[0].set_value("graduate enrollment")
        self.at.button(key=next(b.key for b in self.at.button if b.label == "Search codebooks") or None).click().run()
        self.assertFalse(self.at.exception)
        self.assertIn("EFGRAD", list(self.at.dataframe[0].value["Variable"]))

    def test_about_has_the_model_selector_and_benchmark_rates(self):
        self.at.run()
        self.button("About this prototype").click().run()
        self.assertFalse(self.at.exception)
        self.assertEqual(self.at.selectbox[0].label, "Model strategy")
        self.assertEqual([m.label for m in self.at.metric], ["Yale match rate", "NCES match rate"])
        self.assertEqual(len(self.at.toggle), 0)                # no AI switch, no development mode


if __name__ == "__main__":
    unittest.main()
