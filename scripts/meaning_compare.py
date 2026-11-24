"""Part 5d: compare meaning search with fastembed and with sentence-transformers (same model, BAAI/bge-small-en-v1.5).

    <throwaway env>\\python scripts/meaning_compare.py --lib fastembed|sentence-transformers --cache <folder> --out <file.json>

Run in a throwaway environment that has the library; the app's own environment is not touched. For each question with
an expected measure (and, in the badly written set, an expected group), it records whether the expected item reaches
the shortlist by:
  word search alone      the app's shortlist (path/shortlist.py), unchanged;
  meaning search alone   the measures (and groups) whose meaning fingerprint is closest to the question's;
  both merged            the word shortlist, plus the closest measures by meaning that it does not already hold.
Fingerprints for the dictionary are computed once (as the build would); each question is fingerprinted when asked, and
that time is recorded. Questions are read on their own, without the earlier turns of their conversation, for all three.
"""
import argparse
import csv
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config
from path import shortlist as sl

MODEL = "BAAI/bge-small-en-v1.5"
QUERY = "Represent this sentence for searching relevant passages: "   # bge's own instruction for queries
MEANING_MEASURES, MEANING_GROUPS = 20, 15     # meaning alone: as many as the word shortlist's measure and group slots
MERGE_ADD = 10                                # merged: the closest measures by meaning that word search did not find


def question_sets():
    """[(set, source, case, turn, question, measures, groups)]: the badly written set and the full question set."""
    out = []
    for r in csv.DictReader(open(ROOT / "docs" / "stage5d" / "badly_written.csv", encoding="utf-8")):
        ms = [m for m in r["measures"].split("|") if m and not m.startswith("*")]
        gs = [g for g in r["groups"].split(";") if g]
        if ms or gs:
            out.append(("badly written", "bad", r["case"], r["turn"], r["question"], ms, gs))
    exp = {(r["source"], r["case"], r["turn"]): r for r in csv.DictReader(open(ROOT / "docs" / "stage4" / "expectations.csv",
                                                                                encoding="utf-8"))}
    runs = sorted((config.LOG_DIR / "stage4").glob("haiku_5c_decisions/turns.jsonl"))
    for line in runs[0].read_text(encoding="utf-8").splitlines():
        t = json.loads(line)
        e = exp.get((t["source"], str(t["case"]), str(t["turn"])))
        if t.get("repeat") or not e:
            continue
        ms = [m for m in e["measures"].split("|") if m and not m.startswith("*")]
        if ms and e["category"] in ("scored", "trend"):
            out.append(("full set", t["source"], str(t["case"]), str(t["turn"]), t["question"], ms, []))
    return out


def embedder(lib, cache):
    if lib == "fastembed":
        from fastembed import TextEmbedding
        model = TextEmbedding(MODEL, cache_dir=cache)
        return lambda texts: __import__("numpy").array(list(model.embed(texts, batch_size=64)))
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL, cache_folder=cache, device="cpu")
    return lambda texts: model.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)


def main():
    import numpy as np
    p = argparse.ArgumentParser()
    p.add_argument("--lib", required=True, choices=["fastembed", "sentence-transformers"])
    p.add_argument("--cache", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--reuse", action="store_true", help="reuse the fingerprints saved by an earlier run")
    p.add_argument("--text", choices=["name", "name+context"], default="name+context",
                   help="what a measure's fingerprint is made from")
    p.add_argument("--probe", nargs="*", help="print the closest measures for these questions, and stop")
    a = p.parse_args()
    db_path = config.LOCAL_DB.as_posix()
    index = sl.get_index(db_path)
    measures, groups = index["measures"][1], index["groups"][1]

    start = time.time()
    embed = embedder(a.lib, a.cache)
    load_seconds = time.time() - start
    m_keys = list(measures)
    m_texts = [measures[k]["main"] if a.text == "name" else f"{measures[k]['main']}. {measures[k]['context'][:200]}"
               for k in m_keys]                 # name and synonyms; or with the table title and description too
    g_keys = list(groups)
    g_texts = [groups[k]["text"] for k in g_keys]
    start = time.time()
    saved = Path(a.cache) / f"fingerprints_{a.text.replace('+', '_')}.npz"
    if saved.exists() and a.reuse:
        got = np.load(saved)
        m_vec, g_vec = got["m"], got["g"]
    else:
        m_vec = np.asarray(embed(m_texts), dtype="float32")
        g_vec = np.asarray(embed(g_texts), dtype="float32")
        np.savez(saved, m=m_vec, g=g_vec)
    norm = lambda v: v / np.linalg.norm(v, axis=1, keepdims=True)
    m_vec, g_vec = norm(m_vec), norm(g_vec)
    fingerprint_seconds = time.time() - start

    embed([QUERY + "warm up"])
    if a.probe:
        for question in a.probe:
            qv = norm(np.asarray(embed([QUERY + question]), dtype="float32"))[0]
            print(question)
            for i in np.argsort(-(m_vec @ qv))[:8]:
                print(f"   {float(m_vec[i] @ qv):.3f} {m_keys[i]} | {m_texts[i][:110]}")
        return
    results, times = [], []
    for qset, source, case, turn, question, want_m, want_g in question_sets():
        word = sl.shortlist(question, db_path)
        word_m, word_g = set(word["measures"]) if isinstance(word["measures"], dict) else {m["id"] for m in word["measures"]}, \
            set(word["groups"]) if isinstance(word["groups"], dict) else {g["name"] for g in word["groups"]}
        t0 = time.perf_counter()
        qv = norm(np.asarray(embed([QUERY + question]), dtype="float32"))[0]
        m_rank = [m_keys[i] for i in np.argsort(-(m_vec @ qv))]
        g_rank = [g_keys[i] for i in np.argsort(-(g_vec @ qv))[:MEANING_GROUPS]]
        times.append(time.perf_counter() - t0)
        meaning_m = set(m_rank[:MEANING_MEASURES])
        merged_m = word_m | set([k for k in m_rank if k not in word_m][:MERGE_ADD])
        merged_g = word_g | set(g_rank[:5])
        row = dict(set=qset, source=source, case=case, turn=turn, question=question, measures=want_m, groups=want_g,
                   rank=min((m_rank.index(m) + 1 for m in want_m if m in m_rank), default=None),
                   word_m=any(m in word_m for m in want_m), meaning_m=any(m in meaning_m for m in want_m),
                   merged_m=any(m in merged_m for m in want_m), n_word=len(word_m), n_merged=len(merged_m))
        if want_g:
            row.update(word_g=all(g in word_g for g in want_g), meaning_g=all(g in g_rank for g in want_g),
                       merged_g=all(g in merged_g for g in want_g))
        results.append(row)
    json.dump(dict(lib=a.lib, model=MODEL, text=a.text, load_seconds=load_seconds, fingerprint_seconds=fingerprint_seconds,
                   n_measures=len(m_keys), n_groups=len(g_keys), query_ms=[t * 1000 for t in times], results=results),
              open(a.out, "w", encoding="utf-8"), indent=1)
    print(a.lib, f"{len(results)} questions; fingerprints {fingerprint_seconds:.0f}s; "
          f"median per question {sorted(times)[len(times) // 2] * 1000:.0f} ms")


if __name__ == "__main__":
    main()
