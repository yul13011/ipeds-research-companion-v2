"""Live smoke test: the nine design questions through the real model call. Costs money; run only when approved.

    python scripts/smoke_test.py --yes                 (the model in config, Sonnet by default)
    python scripts/smoke_test.py --yes --model haiku

Prints, for each question, what the model returned, the outcome, the time and the cost. Logs go to
logs/smoke/, not the app's question log.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from path import answer
from path.log import Log

parser = argparse.ArgumentParser()
parser.add_argument("--yes", action="store_true", help="confirm that live API calls may be made")
parser.add_argument("--model", choices=[m.lower() for m in config.MODELS], default=None)
args = parser.parse_args()
if not args.yes:
    sys.exit("This makes live API calls. Add --yes to run it.")
model = config.MODELS[args.model.title()] if args.model else config.INTERPRET_MODEL
log = Log(config.LOG_DIR / "smoke")
cases = sorted(Path(__file__).resolve().parents[1].joinpath("tests", "replies").glob("*.json"))
states, total = {}, 0.0
for path in cases:
    case = json.loads(path.read_text(encoding="utf-8"))
    state = states.get(case.get("after"), {}) if case.get("after") else {}
    page = answer.ask(case["question"], state, log, model=model)
    states[path.stem] = state
    row = json.loads((log.folder / "questions.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    total += row.get("cost_usd") or 0
    expected = case["reply"].get("request") or case["reply"].get("edit")
    print(f"\n## {case['question']}\n  outcome: {page['kind']}   {row['seconds']}s   ${row.get('cost_usd', 0):.4f}")
    print("  model:", json.dumps(row.get("reply")))
    print("  saved:", json.dumps(expected))
    print("  shown:", page.get("interpreted") or page.get("message"))
print(f"\nTotal cost: ${total:.4f} with {model}")
