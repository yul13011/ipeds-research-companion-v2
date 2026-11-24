"""Part 5d, item 3: does meaning search still add right measures or groups on top of the AI's own search?

    <throwaway env>\\python scripts/meaning_on_top.py --run haiku_5d_search --before haiku_5d_before --cache <folder> --out <file.json>

Reads the logged turns of a question-set run made with the AI's own search. For each question with an expected measure
or group, it checks the final shortlist the model answered from, then whether meaning search (fastembed, bge-small,
fingerprints from each measure's own name and synonyms) would have found the expected item that shortlist lacks:
  on the raw question       the 10 closest measures and 5 closest groups to the question as asked;
  on the model's search words   the same, for each search the model made (only where it searched).
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config
from path import shortlist as sl

MODEL = "BAAI/bge-small-en-v1.5"
QUERY = "Represent this sentence for searching relevant passages: "
ADD_MEASURES, ADD_GROUPS = 10, 5              # as merged in the first comparison


def turns(run):
    path = config.LOG_DIR / "stage4" / run / "turns.jsonl"
    return {(t["source"], str(t["case"]), str(t["turn"])): t for t in map(json.loads, path.read_text(encoding="utf-8").splitlines())}


def main():
    import numpy as np
    from fastembed import TextEmbedding
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True)
    p.add_argument("--before", required=True)
    p.add_argument("--cache", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    exp = {(r["source"], r["case"], r["turn"]): r for r in csv.DictReader(open(ROOT / "docs" / "stage4" / "expectations.csv",
                                                                                encoding="utf-8"))}
    groups_wanted = {(("bad", r["case"], r["turn"])): [g for g in r["groups"].split(";") if g]
                     for r in csv.DictReader(open(ROOT / "docs" / "stage5d" / "badly_written.csv", encoding="utf-8"))}
    after, before = turns(a.run), turns(a.before)
    index = sl.get_index(config.LOCAL_DB.as_posix())
    measures, groups = index["measures"][1], index["groups"][1]
    m_keys, g_keys = list(measures), list(groups)
    model = TextEmbedding(MODEL, cache_dir=a.cache)
    embed = lambda texts: np.asarray(list(model.embed(texts, batch_size=64)), dtype="float32")
    norm = lambda v: v / np.linalg.norm(v, axis=1, keepdims=True)
    saved = Path(a.cache) / "fingerprints_name.npz"
    got = np.load(saved) if saved.exists() else None
    if got is None or len(got["m"]) != len(m_keys) or len(got["g"]) != len(g_keys):
        m_vec, g_vec = embed([measures[k]["main"] for k in m_keys]), embed([groups[k]["text"] for k in g_keys])
        np.savez(saved, m=m_vec, g=g_vec)
    else:
        m_vec, g_vec = got["m"], got["g"]
    m_vec, g_vec = norm(m_vec), norm(g_vec)

    def closest(text):
        qv = norm(embed([QUERY + text]))[0]
        return ([m_keys[i] for i in np.argsort(-(m_vec @ qv))[:ADD_MEASURES]],
                [g_keys[i] for i in np.argsort(-(g_vec @ qv))[:ADD_GROUPS]])

    rows = []
    for key, t in after.items():
        e = exp.get(key)
        if t.get("repeat") or not e or e["category"] not in ("scored", "trend", "badly written"):
            continue
        want_m = [m for m in e["measures"].split("|") if m and not m.startswith("*")]
        want_g = groups_wanted.get(key, [])
        if not want_m and not want_g:
            continue
        final = set(map(str, (t.get("shortlist") or {}).values()))
        first = set(map(str, ((before.get(key) or {}).get("shortlist") or {}).values()))
        raw_m, raw_g = closest(t["question"])
        words = [s["words"] for s in t.get("searches") or []]
        by_words = [closest(w) for w in words]
        word_m = {m for ms, _ in by_words for m in ms}
        word_g = {g for _, gs in by_words for g in gs}
        row = dict(set=e["category"], source=key[0], case=key[1], turn=key[2], question=t["question"], measures=want_m,
                   groups=want_g, searches=words)
        if want_m:
            row.update(before_m=any(m in first for m in want_m), after_m=any(m in final for m in want_m),
                       raw_adds_m=any(m in raw_m for m in want_m) and not any(m in final for m in want_m),
                       words_adds_m=any(m in word_m for m in want_m) and not any(m in final for m in want_m))
        if want_g:
            row.update(before_g=all(g in first for g in want_g), after_g=all(g in final for g in want_g),
                       raw_adds_g=all(g in final or g in raw_g for g in want_g) and not all(g in final for g in want_g),
                       words_adds_g=all(g in final or g in word_g for g in want_g) and not all(g in final for g in want_g))
        rows.append(row)
    json.dump(dict(run=a.run, before=a.before, rows=rows), open(a.out, "w", encoding="utf-8"), indent=1)
    print(f"{len(rows)} questions written to {a.out}")


if __name__ == "__main__":
    main()
