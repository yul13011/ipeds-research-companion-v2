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

# Releases loaded into the local database, one per year: (release folder, database file name, year).
# `year` is the release year: 2024 for the 2024-25 release. The folder name says whether a release is
# provisional or final. To add a new year or replace a provisional release with its final version, change
# its line here and run: python build/build_data.py --release <folder>   (see UPDATING.md)
RELEASES = [
    ("IPEDS_2015-16_Final", "IPEDS201516.sqlite", 2015),
    ("IPEDS_2016-17_Final", "IPEDS201617.sqlite", 2016),
    ("IPEDS_2017-18_Final", "IPEDS201718.sqlite", 2017),
    ("IPEDS_2018-19_Final", "IPEDS201819.sqlite", 2018),
    ("IPEDS_2019-20_Final", "IPEDS201920.sqlite", 2019),
    ("IPEDS_2020-21_Final", "IPEDS202021.sqlite", 2020),
    ("IPEDS_2021-22_Final", "IPEDS202122.sqlite", 2021),
    ("IPEDS_2022-23_Final", "IPEDS202223.sqlite", 2022),
    ("IPEDS_2023-24_Final", "IPEDS202324.sqlite", 2023),
    ("IPEDS_2024-25_Provisional", "IPEDS202425.sqlite", 2024),
]

# The interpret step's model call. The key is read from the ANTHROPIC_API_KEY environment variable.
INTERPRET_MODEL = os.environ.get("IPEDS_MODEL", "claude-haiku-5-5")
INTERPRET_EFFORT = os.environ.get("IPEDS_EFFORT", "medium")
MODELS = {"Haiku": "claude-haiku-5-5", "Sonnet": "claude-sonnet-5-5"}
SUMMARY = os.environ.get("IPEDS_SUMMARY", "1") != "0"        # the written summary (Part 5e); 0 turns it off
SUMMARY_MODEL = os.environ.get("IPEDS_SUMMARY_MODEL", INTERPRET_MODEL)
AI_SEARCH = os.environ.get("IPEDS_AI_SEARCH", "1") != "0"   # the model's own search (Part 5d); 0 turns it off
CALL_SECONDS = float(os.environ.get("IPEDS_CALL_SECONDS", "30"))   # the limit on one model call (owner decision, 2026-11-26)
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00)}   # US$ per million tokens, in and out

# Local logs. Tests pass their own folder, so they never write here.
LOG_DIR = Path(os.environ.get("IPEDS_LOG_DIR", ROOT / "logs"))

# The spending guard (Part 6f, owner decision 2026-11-26: $2 a day, 40 questions per conversation on the host).
# 0 means no limit, the local default; the host sets both. The day runs midnight to midnight, Eastern time.
DAILY_USD = float(os.environ.get("IPEDS_DAILY_USD", "0"))
CONVERSATION_QUESTIONS = int(os.environ.get("IPEDS_CONVERSATION_QUESTIONS", "0"))
DAY_ZONE = "America/New_York"
# The owner-only log download in About (Part 6f): shown only when this secret is set on the host.
OWNER_PASSPHRASE = os.environ.get("IPEDS_OWNER_PASSPHRASE", "")

# The automatic chart (Part 5c): palette, font and axis colours taken from version 1's chart settings
# (agent-redesign/prototype/charts.py, read only). No formatting panel in this stage.
CHART = dict(palette=["#24658A", "#C47A28", "#78649B", "#398278", "#A24B4B", "#5E8C3A", "#C96E9C", "#4E9DB5", "#9C7A3C", "#6B6FA8"],
             font="Arial", font_size=13, text="#263746", grid="#E7EBED", domain="#AAB4B9", line_width=2.5, point_size=32)

# The latest benchmark run, read by the About page for its match rates (Part 6b): the ten-year run of Part 5g.
# Point this at a newer run's file when the benchmarks are run again.
BENCHMARKS = ROOT / "docs" / "reports" / "stage5g" / "benchmarks_trend.csv"
