"""Publish data/ipeds_v2.sqlite to the public Hugging Face dataset the host downloads from (Part 6f).

    .venv\\Scripts\\python.exe scripts/publish_dataset.py

Needs `huggingface_hub` in .venv (not in requirements.txt: the host doesn't need it) and the owner's Hugging Face login
(`.venv\\Scripts\\hf.exe auth login`; the token stays in the user folder). Writes the file's SHA-256 beside it, uploads
both, and prints the commit id to put in Render's IPEDS_V2_DATASET_REVISION. The README is kept as it is on the dataset.
"""
import hashlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config

REPO = "yul13011/ipeds-v2-data"


def main():
    from huggingface_hub import HfApi
    db = config.LOCAL_DB
    digest = hashlib.sha256()
    with open(db, "rb") as f:
        for block in iter(lambda: f.read(16 << 20), b""):
            digest.update(block)
    api = HfApi()
    with tempfile.TemporaryDirectory() as d:
        checksum = Path(d) / "ipeds_v2.sqlite.sha256"
        checksum.write_text(f"{digest.hexdigest()}  ipeds_v2.sqlite\n", encoding="utf-8")
        api.upload_file(path_or_fileobj=str(checksum), path_in_repo=checksum.name, repo_id=REPO, repo_type="dataset",
                        commit_message="checksum")
    info = api.upload_file(path_or_fileobj=str(db), path_in_repo="ipeds_v2.sqlite", repo_id=REPO, repo_type="dataset",
                           commit_message="ipeds_v2.sqlite")
    print(f"sha256 {digest.hexdigest()}\nIPEDS_V2_DATASET_REVISION = {info.oid}")


if __name__ == "__main__":
    main()
