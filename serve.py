"""Starts the app on the host (Part 6f). Locally, `streamlit run app.py` is still the way to run the page.

    python serve.py

1. The data. When IPEDS_V2_DATASET_REPO is set, the database is downloaded once from that public Hugging Face dataset, at
   the fixed version IPEDS_V2_DATASET_REVISION, into IPEDS_V2_DATA_DIR/<version>/ on the persistent disk. Its SHA-256 is
   checked against the checksum file published beside it. A restart finds it there and skips the download.
2. The warm-up. The search index is built, and the Explore examples are shortlisted, in the background, in this
   process, so the first visitor does not wait for them. Streamlit runs the page in this same process, so the page uses
   the index built here. A question asked before the warm-up ends waits for the index rather than building another.
3. Streamlit, on the host's port.
"""
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "ipeds_v2.sqlite"
URL = "https://huggingface.co/datasets/{repo}/resolve/{revision}/{name}"


def say(text):
    print(f"[serve] {time.strftime('%H:%M:%S')} {text}", flush=True)


def ensure_data(data_dir, repo, revision, get=None):
    """The database's path, downloaded first if this version is not on the disk yet. `get` is requests.get (tests pass
    their own)."""
    folder = Path(data_dir) / revision
    target, marker = folder / NAME, folder / "complete.json"
    if marker.exists() and target.exists():
        return target
    if get is None:
        import requests
        get = requests.get
    folder.mkdir(parents=True, exist_ok=True)
    expected = get(URL.format(repo=repo, revision=revision, name=NAME + ".sha256"), timeout=60).text.split()[0].strip()
    start, part, digest, size = time.time(), folder / (NAME + ".part"), hashlib.sha256(), 0
    say(f"downloading {repo} at {revision}")
    with get(URL.format(repo=repo, revision=revision, name=NAME), stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(part, "wb") as f:
            for chunk in r.iter_content(chunk_size=8 << 20):
                f.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    if digest.hexdigest() != expected:
        part.unlink()
        raise RuntimeError(f"The downloaded database does not match its published checksum ({size:,} bytes).")
    part.replace(target)
    marker.write_text(json.dumps(dict(repo=repo, revision=revision, sha256=expected, bytes=size,
                                      seconds=round(time.time() - start, 1))), encoding="utf-8")
    say(f"downloaded {size / 2**30:.2f} GB in {time.time() - start:.0f} s")
    return target


def warm_up(db_path):
    start = time.time()
    from path import shortlist
    shortlist.get_index(db_path)
    say(f"index ready in {time.time() - start:.1f} s")
    topics = json.loads((ROOT / "page" / "explore.json").read_text(encoding="utf-8"))["topics"]
    for example in (e for t in topics for e in t["examples"]):
        shortlist.shortlist(example["question"], db_path)
    say(f"warm-up done in {time.time() - start:.1f} s")


def main():
    if os.environ.get("IPEDS_V2_DATASET_REPO"):
        db = ensure_data(os.environ["IPEDS_V2_DATA_DIR"], os.environ["IPEDS_V2_DATASET_REPO"], os.environ["IPEDS_V2_DATASET_REVISION"])
        os.environ["IPEDS_LOCAL_DB"] = str(db)          # read by config.py, imported after this line
    sys.path.insert(0, str(ROOT))
    import config
    threading.Thread(target=warm_up, args=(config.LOCAL_DB.as_posix(),), daemon=True).start()
    from streamlit.web import cli
    sys.argv = ["streamlit", "run", str(ROOT / "app.py"), "--server.port", os.environ.get("PORT", "8501"),
                "--server.address", "0.0.0.0", "--server.headless", "true", "--browser.gatherUsageStats", "false"]
    cli.main()


if __name__ == "__main__":
    main()
