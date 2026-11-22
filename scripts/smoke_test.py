"""Live smoke test: the nine design questions through the real model call. Costs money; run only when approved.

    python scripts/smoke_test.py --yes                 (the model in config, Sonnet by default)
    python scripts/smoke_test.py --yes --model haiku

Prints, for each question, what the model returned (in tags and mapped to IDs) beside the saved reply, the
outcome, time, tokens and cost; then where the prompt tokens go, counted with the API's free token counter.
Logs go to logs/smoke/, not the app's question log.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import anthropic

import config
from path import answer, interpret, shortlist
from path.log import Log

parser = argparse.ArgumentParser()
parser.add_argument("--yes", action="store_true", help="confirm that live API calls may be made")
parser.add_argument("--model", choices=[m.lower() for m in config.MODELS], default=None)
args = parser.parse_args()
if not args.yes:
    sys.exit("This makes live API calls. Add --yes to run it.")
model = config.MODELS[args.model.title()] if args.model else config.INTERPRET_MODEL
log = Log(config.LOG_DIR / "smoke")
client = anthropic.Anthropic()


def count(system=None, text="x"):
    kw = dict(model=model, messages=[{"role": "user", "content": text}])
    if system:
        kw["system"] = system
    return client.messages.count_tokens(**kw).input_tokens


baseline = count()
cases = sorted(p for p in Path(__file__).resolve().parents[1].joinpath("tests", "replies").glob("*.json")
               if not p.name.startswith("real_"))
states, total, where = {}, 0.0, defaultdict(list)
for path in cases:
    case = json.loads(path.read_text(encoding="utf-8"))
    state = states.get(case.get("after"), {}) if case.get("after") else {}
    history, pending = state.get("history") or [], state.get("pending") or []
    short = shortlist.shortlist(case["question"], config.LOCAL_DB.as_posix(), history[-1:] + [o["request"] for o in pending])
    user, _ = interpret.render(short, history[-1] if history else None, pending, case["question"])
    system = interpret.INSTRUCTIONS.format(operations="; ".join(f"{k}: {v}" for k, v in interpret.OPERATIONS.items()),
                                           comparisons=", ".join(interpret.COMPARISONS))
    page = answer.ask(case["question"], state, log, model=model)
    states[path.stem] = state
    row = json.loads((log.folder / "questions.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    total += row.get("cost_usd") or 0
    # where the prompt tokens go
    sections, current = {}, None
    for line in user.splitlines():
        if line.startswith(("Measures", "Terms", "Schools", "Groups", "Category rows", "Breakdown sets", "Outside IPEDS",
                            "PREVIOUS REQUEST", "QUESTION")):
            current = line.split(" (")[0].split(":")[0]
        sections.setdefault(current or "SHORTLIST", []).append(line)
    parts = {"instructions": count(system) - baseline}
    parts.update({name: count(text="\n".join(lines)) - baseline for name, lines in sections.items()})
    total_in = (row["tokens_in"] or 0) + (row.get("cache_write") or 0) + (row.get("cache_read") or 0)
    parts["reply shape and call overhead"] = total_in - count(system, user) if total_in else 0
    for k, v in parts.items():
        where[k].append(v)
    expected = case["reply"].get("request") or case["reply"].get("edit")
    got = row.get("reply") or {}
    print(f"\n## {case['question']}\n  outcome: {page['kind']}   {row['seconds']}s   tokens in {total_in:,} "
          f"(uncached {row['tokens_in']:,}, cache written {row.get('cache_write') or 0:,}, cache read {row.get('cache_read') or 0:,}), "
          f"out {row['tokens_out']:,}   ${row.get('cost_usd', 0):.4f}")
    print("  model, in tags:", json.dumps(row.get("raw_reply")))
    print("  model, mapped:", json.dumps(got.get("request") or got.get("edit") or got.get("decline") or got.get("options")))
    print("  saved:", json.dumps(expected))
    print("  shown:", page.get("interpreted") or page.get("message"))
print(f"\nTotal cost: ${total:.4f} with {model}")
print("\nWhere the prompt tokens go (average over the nine questions):")
for k, v in sorted(where.items(), key=lambda kv: -sum(kv[1])):
    print(f"  {k:<32}{sum(v) / len(v):>8,.0f}")
