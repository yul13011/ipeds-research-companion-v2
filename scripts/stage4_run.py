"""Stage 4: run the logged questions and version 1's evaluation questions through the live path, on one model.

    python scripts/stage4_run.py --yes --model haiku                 # 4 workers (owner decision 2026-11-26)
    python scripts/stage4_run.py --yes --model haiku --workers 1     # one question at a time: the timing run

Conversations are run with their history; turns within a conversation stay in order. With several workers,
conversations run side by side, each in its own process and folder, and the folders are merged at the end in the
usual order, so the grader and the review files see one run. A call the API refuses for rate limits is retried after
the wait the API gives, and each wait is recorded with the turn. A conversation made only of repeated questions is
skipped; a repeated turn inside a conversation is run for context and not scored. Each turn's request, outcome, time,
tokens and cost go to logs/stage4/<model>/turns.jsonl; the app's own question and decline logs go to the same folder.
"""
import argparse
import csv
import json
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "agent-redesign" / "evaluations"))

import config
from path import answer, interpret
from path import summary as summary_step
from path.log import Log

FILES = ("questions.jsonl", "declines.jsonl", "summaries.jsonl", "turns.jsonl")
TRIES = 6                                               # rate-limit waits per call before it is left to fail


def patient(fn, waits):
    """The API call, retried after the wait the API asks for when it refuses for rate limits (429)."""
    import anthropic

    def call(*a, **k):
        for attempt in range(TRIES):
            try:
                return fn(*a, **k)
            except anthropic.RateLimitError as e:
                header = e.response.headers.get("retry-after") if getattr(e, "response", None) is not None else None
                wait = float(header) if header else 5.0 * 2 ** attempt
                waits.append(round(wait, 1))
                time.sleep(wait)
        return fn(*a, **k)
    return call


def conversations():
    by = {}
    for r in csv.DictReader(open(ROOT / "docs" / "test_questions.csv", encoding="utf-8")):
        by.setdefault(r["conversation"], []).append((int(r["turn"]), r["question"], r["repeat"] == "yes"))
    for conv, turns in by.items():
        if all(rep for _, _, rep in turns):
            continue
        yield "log", conv, sorted(turns)
    import eval_set
    cases = eval_set.all_cases() if callable(getattr(eval_set, "all_cases", None)) else eval_set.CASES
    for c in cases:
        yield "eval", c["id"], [(i + 1, t["q"], False) for i, t in enumerate(c["turns"])]
    owner = {}                                          # the owner's questions for question types 44 to 49
    for r in csv.DictReader(open(ROOT / "docs" / "owner_questions.csv", encoding="utf-8")):
        owner.setdefault(r["case"], []).append((int(r["turn"]), r["question"], False))
    for case, turns in owner.items():
        yield "owner", case, sorted(turns)
    bad = {}                                            # Part 5d: the badly written set (docs/stage5d)
    for r in csv.DictReader(open(ROOT / "docs" / "stage5d" / "badly_written.csv", encoding="utf-8")):
        bad.setdefault(r["case"], []).append((int(r["turn"]), r["question"], False))
    for case, turns in bad.items():
        yield "bad", case, sorted(turns)


def summary(page):
    if page["kind"] == "many":
        return dict(kind="many", parts=[summary(p) for p in page["pages"]])
    out = dict(kind=page["kind"], message=page.get("message"), interpreted=page.get("interpreted"))
    if page.get("table"):
        out["table"] = dict(columns=page["table"]["columns"], rows=page["table"]["rows"][:12], n_rows=len(page["table"]["rows"]))
        out["warnings"] = page.get("warnings")
    if page.get("options"):
        out["options"] = page["options"]
    if page.get("candidates"):
        out["candidates"] = page["candidates"][:8]
    if page.get("offers"):                              # buttons offered under the answer (Part 6.0)
        out["offers"] = page["offers"]
    return out


def run_conversation(job):
    """One conversation, in order, into its own folder."""
    index, source, case, turns, folder, model, workers = job
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    log, state = Log(folder), {}
    with open(folder / "turns.jsonl", "a", encoding="utf-8") as out:
        for turn, question, repeat in turns:
            n = sum(1 for _ in open(folder / "questions.jsonl", encoding="utf-8")) if (folder / "questions.jsonl").exists() else 0
            waits, start = [], time.time()
            try:
                page = answer.ask(question, state, log, model=model, call=patient(interpret.call_api, waits))
                error = None
                written = []                            # Part 5e: the written summary of each answer, checked
                for part in page.get("pages") or [page]:
                    if config.SUMMARY and part.get("kind") == "answer":
                        before = (folder / "summaries.jsonl").read_text(encoding="utf-8").splitlines() \
                            if (folder / "summaries.jsonl").exists() else []
                        answer.summarize(part, state, log, model=model, call=patient(summary_step.call_api, waits))
                        after = (folder / "summaries.jsonl").read_text(encoding="utf-8").splitlines() \
                            if (folder / "summaries.jsonl").exists() else []   # no summary written yet in this run
                        written += [json.loads(x) for x in after[len(before):]]
            except Exception as e:                       # recorded, and the run goes on
                page, error, written = dict(kind="error", message=repr(e)), repr(e), []
            lines = (folder / "questions.jsonl").read_text(encoding="utf-8").splitlines()[n:] if (folder / "questions.jsonl").exists() else []
            rows = [json.loads(x) for x in lines]
            first = rows[0] if rows else {}
            rec = dict(source=source, case=case, turn=turn, question=question, repeat=repeat, error=error,
                       seconds=round(time.time() - start, 2), page=summary(page), workers=workers, rate_waits=waits,
                       reply=first.get("reply"), requests=[q for r in rows for q in ([r.get("request")] + [p.get("request") for p in r.get("parts") or []]) if q],
                       options=first.get("options"), missing=first.get("missing"), detail=first.get("detail"),
                       shortlist=first.get("shortlist"), tokens_in=first.get("tokens_in"), tokens_out=first.get("tokens_out"),
                       cache_write=first.get("cache_write"), cache_read=first.get("cache_read"), cost_usd=first.get("cost_usd"),
                       model_seconds=first.get("model_seconds"), model_error=first.get("model_error"),
                       calls=first.get("calls"), searches=first.get("searches"), search_seconds=first.get("search_seconds"),
                       summaries=[dict(kept=w["kept"], missing=w["missing"], text=w.get("text"), seconds=w["seconds"],
                                       cost_usd=w["cost_usd"], error=w.get("error")) for w in written])
            out.write(json.dumps(rec, default=str) + "\n")
            out.flush()
            print(f"{source} {case}.{turn} {page['kind']:<13} {rec['seconds']:>5}s  {question[:70]}", flush=True)
    return index


def merge(parts, folder):
    """The conversations' folders, joined in the usual order into one run."""
    for name in FILES:
        with open(folder / name, "w", encoding="utf-8") as out:
            for part in parts:
                if (part / name).exists():
                    out.write((part / name).read_text(encoding="utf-8"))
    shutil.rmtree(folder / "parts", ignore_errors=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--model", choices=[m.lower() for m in config.MODELS], required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not args.yes:
        sys.exit("This makes live API calls. Add --yes to run it.")
    model = config.MODELS[args.model.title()]
    folder = config.LOG_DIR / "stage4" / args.model
    folder.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        (folder / name).unlink(missing_ok=True)
    shutil.rmtree(folder / "parts", ignore_errors=True)
    jobs = [(i, source, case, turns, str(folder / "parts" / f"{i:04d}"), model, args.workers)
            for i, (source, case, turns) in enumerate(conversations())]
    if args.workers <= 1:
        for job in jobs:
            run_conversation(job)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(run_conversation, jobs))
    merge([Path(j[4]) for j in jobs], folder)


if __name__ == "__main__":                              # the workers import this file: only the main process runs
    main()
