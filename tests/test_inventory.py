"""The database inventory (docs/DATABASE.md). Writes only to a temporary file."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import config
import database_inventory as inv


@unittest.skipUnless(config.LOCAL_DB.exists(), "local database not built")
class Inventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.path, cls.tables = inv.write(out_path=Path(cls.dir.name) / "DATABASE.md")
        cls.text = cls.path.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def test_every_table_has_a_layer_and_a_description(self):
        for t in self.tables:
            self.assertIn(t["layer"], inv.LAYERS, t["name"])
            self.assertNotIn("not yet described", t["held"].lower(), t["name"])

    def test_survey_and_codebook_tables_have_rows_by_release(self):
        for t in self.tables:
            if t["layer"] in ("survey data", "IPEDS codebook") and t["rows"]:
                self.assertEqual(sum(n for _, n in t["by_release"]), t["rows"], t["name"])

    def test_totals_at_the_top(self):
        self.assertIn(f"| Tables | {len(self.tables):,} |", self.text)
        self.assertIn(f"| Rows | {sum(t['rows'] for t in self.tables):,} |", self.text)
        self.assertIn("| File size |", self.text)


if __name__ == "__main__":
    unittest.main()
