"""Stage 4: grade the two runs against docs/stage4/expectations.csv and the manual review in docs/stage4/review.csv.

    python scripts/stage4_grade.py dump      prints each scored turn for manual review
    python scripts/stage4_grade.py           writes docs/reports/stage4/scorecard.csv and prints the tables used in STAGE_4.md

Outcome classes: answer, decline, clarify (a clarifying question or a school picker), wrong (the app's own
wrong-reading reply), error. A turn is a correct answer when an answer was expected and the measure and schools
are right; a correct decline when a decline was expected; a clarifying question when the app asked; anything else is
a wrong reading. Where the expected measure is written as a concept (starting with *), the review file says
whether the measure and schools were right.
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config

MODELS = ("haiku", "sonnet")
EXP = {(r["source"], r["case"], r["turn"]): r for r in csv.DictReader(open(ROOT / "docs" / "stage4" / "expectations.csv", encoding="utf-8"))}
REVIEW_FILE = ROOT / "docs" / "stage4" / "review.csv"
REVIEW = {(r["model"], r["source"], r["case"], r["turn"]): r for r in csv.DictReader(open(REVIEW_FILE, encoding="utf-8"))} if REVIEW_FILE.exists() else {}


def turns(model):
    path = config.LOG_DIR / "stage4" / model / "turns.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def kind_of(page):
    k = page["kind"]
    if k == "many":
        kinds = {kind_of(p) for p in page["parts"]}
        return "answer" if "answer" in kinds else sorted(kinds)[0]
    return {"picker": "clarify", "wrong_reading": "wrong"}.get(k, k)


def ids(t):
    ms, ss, gs = set(), set(), set()
    reqs = t["requests"] or ([t["reply"]["request"]] if t.get("reply") and t["reply"].get("request") else [])
    reqs += [o for o in (t.get("options") or [])]
    for r in reqs:
        ms |= {m["id"] for m in r.get("measures") or []}
        ss |= {s["id"] for s in r.get("schools") or [] if s.get("id")}
        gs |= set(r.get("groups") or [])
    return ms, ss, gs


def auto_reading(t, e):
    """Measure and schools right? True/False where the expectation names IDs; None where a person must judge."""
    ms, ss, _ = ids(t)
    m_ok = None
    if e["measures"] and not e["measures"].startswith("*"):
        m_ok = any(x in ms for x in e["measures"].split("|"))
    elif not e["measures"]:
        m_ok = True
    s_ok = {int(x) for x in e["schools"].split(";")} <= ss if e["schools"] else True
    return m_ok, s_ok


def auto_miss(t, e):
    """Where the expectation names measure IDs: 'yes' if none of them was on the shortlist."""
    if not e or not e["measures"] or e["measures"].startswith("*") or e["category"] not in ("scored", "trend"):
        return ""
    keys = json.dumps(t.get("shortlist") or {})
    return "no" if any(f'"{x}"' in keys for x in e["measures"].split("|")) else "yes"


def grade(model):
    out = []
    for t in turns(model):
        key = (t["source"], str(t["case"]), str(t["turn"]))
        e = EXP.get(key)
        if t["repeat"]:
            continue
        cat = e["category"] if e else "unlisted"
        got = kind_of(t["page"])
        m_ok, s_ok = auto_reading(t, e) if e else (None, None)
        rv = REVIEW.get((model,) + key)
        if rv:
            m_ok = {"yes": True, "no": False}.get(rv["measure_right"], m_ok)
            s_ok = {"yes": True, "no": False}.get(rv["schools_right"], s_ok)
        expect = set((e["expect"] if e else "").split("|")) - {""}
        if cat in ("greeting", "test", "chart"):
            score = got
        elif got == "clarify":
            score = "clarifying question"
        elif got == "answer" and "answer" in expect and m_ok is not False and s_ok:
            score = "correct answer" if m_ok else "needs review"
        elif got == "decline" and "decline" in expect:
            score = "correct decline"
        else:
            score = "wrong reading"
        if rv and rv.get("score"):
            score = rv["score"]
        out.append(dict(model=model, source=t["source"], case=t["case"], turn=t["turn"], category=cat, question=t["question"],
                        expect="|".join(sorted(expect)), got=got, measure_right=m_ok, schools_right=s_ok, score=score,
                        why=(rv or {}).get("why", ""), seconds=t["seconds"], cost=t.get("cost_usd") or 0,
                        tokens_in=(t.get("tokens_in") or 0) + (t.get("cache_write") or 0) + (t.get("cache_read") or 0),
                        tokens_out=t.get("tokens_out") or 0, missing=t.get("missing"),
                        cause=(rv or {}).get("cause", ""),
                        shortlist_miss=(rv or {}).get("shortlist_miss") or auto_miss(t, e)))
    return out


def dump():
    for model in MODELS:
        for t, g in zip([t for t in turns(model) if not t["repeat"]], grade(model)):
            if g["category"] in ("greeting", "test", "chart"):
                continue
            p = t["page"]
            print(f"\n### {model} {g['source']} {g['case']}.{g['turn']} [{g['category']}] expect {g['expect']} got {g['got']} -> {g['score']}")
            print("  Q:", t["question"])
            ms, ss, gs = ids(t)
            print("  measures:", sorted(ms), "schools:", sorted(ss), "groups:", sorted(gs))
            if t.get("reply"):
                r = t["reply"]
                print("  reply kind:", r.get("kind"), "| decline:", json.dumps(r.get("decline"))[:200] if r.get("decline") else "")
            parts = p.get("parts") or [p]
            for q in parts:
                print("  shown:", (q.get("interpreted") or q.get("message") or "")[:400].replace("\n", " "))
                if q.get("table"):
                    print("  table:", q["table"]["columns"], q["table"]["rows"][:3])
                if q.get("options"):
                    print("  options:", q["options"])
                if q.get("candidates"):
                    print("  candidates:", q["candidates"][:4])
            if t.get("missing"):
                print("  missing:", t["missing"], t.get("detail") or "")
            if t.get("error"):
                print("  ERROR:", t["error"])


def report():
    rows = []
    for model in MODELS:
        rows += grade(model)
    path = ROOT / "docs" / "reports" / "stage4"
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "scorecard.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for model in MODELS:
        g = [r for r in rows if r["model"] == model]
        print(f"\n## {model}")
        for cat in ("scored", "trend"):
            c = Counter(r["score"] for r in g if r["category"] == cat)
            print(f"  {cat}: n={sum(c.values())}", dict(c))
            if cat == "trend":
                rd = [r for r in g if r["category"] == "trend"]
                print("    trend measure read right:", sum(r["measure_right"] is True for r in rd), "of", len(rd),
                      "; schools right:", sum(bool(r["schools_right"]) for r in rd))
        for cat in ("greeting", "test", "chart"):
            print(f"  {cat}:", dict(Counter(r["score"] for r in g if r["category"] == cat)))
        print("  unlisted:", [(r["case"], r["turn"]) for r in g if r["category"] == "unlisted"])
        all_t = turns(model)
        print(f"  time: total {sum(t['seconds'] for t in all_t):.0f}s, mean {sum(t['seconds'] for t in all_t) / len(all_t):.2f}s per turn;"
              f" cost ${sum(t.get('cost_usd') or 0 for t in all_t):.4f} for {len(all_t)} turns")
        sm = [r for r in g if r["shortlist_miss"] in ("yes", "no")]
        print("  shortlist misses:", sum(r["shortlist_miss"] == "yes" for r in sm), "of", len(sm), "turns where a measure was wanted")


if __name__ == "__main__":
    dump() if sys.argv[1:] == ["dump"] else report()
