"""The chat page, driven by Streamlit's own test runner. The model call is replaced by saved replies,
and the page's log is pointed at a temporary folder, so nothing reaches the API or the shared log."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from path import interpret, log, summary

ROOT = Path(__file__).resolve().parents[1]
REPLIES = Path(__file__).with_name("replies")


@unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built")
class App(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest
        self.dir = tempfile.TemporaryDirectory()
        self.saved_log_dir, config.LOG_DIR = config.LOG_DIR, Path(self.dir.name)
        self.saved_call = interpret.call_api
        self.replies = []
        interpret.call_api = lambda system, user, model, schema=None: (json.dumps(self.replies.pop(0)), {"input_tokens": 1, "output_tokens": 1})
        self.saved_summary = summary.call_api           # the written summary: a saved reply, never the API
        self.summary_text = "The table shows the figure asked for."
        summary.call_api = lambda system, user, model, on_text=None: (self.summary_text, {"input_tokens": 1, "output_tokens": 1})
        self.at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)

    def tearDown(self):
        interpret.call_api = self.saved_call
        summary.call_api = self.saved_summary
        config.LOG_DIR = self.saved_log_dir
        self.dir.cleanup()

    def ask(self, name):
        case = json.loads((REPLIES / f"{name}.json").read_text(encoding="utf-8"))
        self.replies.append(case["reply"])
        self.at.chat_input[0].set_value(case["question"]).run()

    def test_answer_shows_interpreted_as_table_and_sources(self):
        self.at.run()
        self.ask("a_yale_admission")
        self.assertFalse(self.at.exception)
        text = " ".join(m.value for m in self.at.markdown)
        self.assertIn("Interpreted as:", text)
        self.assertEqual(len(self.at.dataframe), 1)
        self.assertEqual(self.at.dataframe[0].value.iloc[0, 0], "Yale University")
        self.assertTrue(any("provisional" in w.value for w in self.at.warning))
        self.assertEqual(self.at.expander[0].label, "Definitions & sources")
        self.at.checkbox[0].check().run()                     # underlying counts
        self.assertEqual(len(self.at.dataframe), 2)
        self.assertTrue((Path(self.dir.name) / "questions.jsonl").exists())

    def test_follow_up_and_clear(self):
        self.at.run()
        self.ask("b_compare_grad")
        self.ask("i_add_northeastern")
        self.assertEqual(len(self.at.dataframe[-1].value), 4)
        self.at.button[0].click().run()                       # Clear conversation
        self.assertEqual(len(self.at.dataframe), 0)

    def test_option_buttons_run_the_option(self):
        self.at.run()
        self.replies.append(dict(kind="request", edit=None, options=[], chosen=[], decline=None,
                                 request=dict(json.loads((REPLIES / "a_yale_admission.json").read_text())["reply"]["request"],
                                              measures=[dict(id="EAP.EAPTOT", row=[])])))
        self.at.chat_input[0].set_value("How many faculty does Yale have?").run()
        labels = [b.label for b in self.at.button]
        self.assertIn("Instructional staff", labels)
        self.at.button[labels.index("Instructional staff")].click().run()
        self.assertFalse(self.at.exception)
        self.assertEqual(self.at.dataframe[-1].value.iloc[0, 1], "3,800")

    def test_a_trend_draws_a_line_chart(self):
        """Part 5c: a question over several years shows the table by year and a chart beneath it."""
        self.at.run()
        reply = json.loads((REPLIES / "a_yale_admission.json").read_text())["reply"]
        reply["request"]["year"] = dict(stated="since 2015", kind=None, start=2015, end=None, last=None, change=False,
                                        membership=None)
        self.replies.append(reply)
        self.at.chat_input[0].set_value("Yale's admission rate since 2015").run()
        self.assertFalse(self.at.exception)
        self.assertEqual(list(self.at.dataframe[-1].value.columns[:2]), ["Year", "Period"])
        self.assertEqual(len(self.at.get("vega_lite_chart")), 1)

    def test_one_figure_shows_a_tile_and_a_summary(self):
        """Part 5e: one figure is shown large above the table, and the summary is written under it."""
        self.at.run()
        self.ask("a_yale_admission")
        self.assertFalse(self.at.exception)
        self.assertEqual(len(self.at.metric), 1)
        self.assertIn("The table shows the figure asked for.", " ".join(m.value for m in self.at.markdown))

    def test_a_summary_with_a_wrong_number_is_not_shown(self):
        self.summary_text = "The admission rate was 99.9%."
        self.at.run()
        self.ask("a_yale_admission")
        self.assertNotIn("99.9%", " ".join(m.value for m in self.at.markdown))


if __name__ == "__main__":
    unittest.main()
