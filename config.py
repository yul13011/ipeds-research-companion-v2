"""Where things are. Every path the project uses is set here and nowhere else."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Version 1's data folder. Read in place, never written to.
SOURCE_DATA = Path(os.environ.get("IPEDS_SOURCE_DATA", ROOT.parent / "agent-redesign" / "data"))
CATALOG = SOURCE_DATA / "analysis_catalog.sqlite"  # the cross-year index

# The one home for conventions: CSV tables the owner reviews. See dictionary/README.md.
DICTIONARY = ROOT / "dictionary"

# The local database for this slice. Untracked; rebuilt by build/build_data.py.
LOCAL_DB = Path(os.environ.get("IPEDS_LOCAL_DB", ROOT / "data" / "ipeds_v2.sqlite"))

# Releases loaded into the local database. To stack another year, add a line here
# and run the build again: (release folder, database file name, year).
RELEASES = [
    ("IPEDS_2024-25_Provisional", "IPEDS202425.sqlite", 2024),
]

# The interpret step's model call. The key is read from the ANTHROPIC_API_KEY environment variable.
INTERPRET_MODEL = os.environ.get("IPEDS_MODEL", "claude-sonnet-5-5")
INTERPRET_EFFORT = os.environ.get("IPEDS_EFFORT", "medium")
MODELS = {"Haiku": "claude-haiku-5-5", "Sonnet": "claude-sonnet-5-5"}
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00)}   # US$ per million tokens, in and out

# Local logs. Tests pass their own folder, so they never write here.
LOG_DIR = Path(os.environ.get("IPEDS_LOG_DIR", ROOT / "logs"))
