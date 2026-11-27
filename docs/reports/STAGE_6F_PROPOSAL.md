# Part 6f proposal: hosting

Proposal only. Nothing has been built, created or changed outside this computer. Render prices are from version 1's runbook (October 2026); I'll confirm them on render.com/pricing before you act.

## What version 2 needs on the host

- **One file: `ipeds_v2.sqlite`, 3.27 GB** (ten releases plus the dictionary; 15 MB of free space, so compacting it gains nothing). The app reads nothing else at run time: no cross-year index, nothing from version 1's folder.
- **The code** from the GitHub repository `yul13011/ipeds-research-companion-v2`, Python 3.12 and the pinned `requirements.txt`.
- **One API key.** The model stays Haiku by default.
- **The search index** is built in memory from the database on a process's first question.
  - Measured locally just now: **1.3 s** with the database file already in the computer's file cache, adding about 45 MB of memory.
  - So the index alone doesn't explain the slow first answers in the 6b runs (log 1.1: 50.8 s, against 8.5 s of model time, straight after a rebuild). Most of that time is probably the first reads of a 3.27 GB file that isn't cached yet: the index's tables, then the data tables the question uses.
  - On Render's disk this can be slower than here. So start-up should warm both the index and the database (below), and the hosting test measures the first answer after start-up and after idle separately.

## 1. The version 2 dataset on Hugging Face

- **A new public dataset, proposed name `yul13011/ipeds-v2-data`,** separate from version 1's `yul13011/ipeds-data`, which stays untouched.
  - **What it holds:** `ipeds_v2.sqlite`, plus a short README saying what it is, the build date and the sources.
  - **What it leaves out:** logs, secrets, the review workbook and version 1's files.
- **Size:** 3.27 GB, one file.
- **Uploading it:** from your computer, with your own Hugging Face login (`hf auth login`; the token stays in your user folder, never in the repository).
  - **Your call needed:** this needs the `huggingface_hub` package, which isn't installed. Two options:
    - install it in `.venv` only, as an upload tool, not listed in `requirements.txt`; or
    - upload through the Hugging Face website (drag and drop works for a file this size).
  - I'll ask before creating the dataset, as the work order says.
- **Downloading it on the host, with no new package:** the host fetches the one file from the dataset's direct-file address with `requests` (already pinned), streaming to the persistent disk.
  - **Pinned:** the download names a fixed version of the dataset (`IPEDS_DATASET_REVISION`), so a later upload never changes the live app by surprise.
  - **Checked:** the file's size and SHA-256 are compared with the values published beside it.
  - **Once only:** a marker file records which version is on the disk, so a restart or redeploy skips the download. A new version downloads into a new folder and switches only once it's complete.
  - About 30 lines in a new `serve.py` (below), with tests that use a small local file, not the network.
- **How long:** Hugging Face usually delivers 50 to 100 MB a second to cloud hosts, so 3.27 GB takes about 1 to 2 minutes. That's an estimate; the hosting test measures it. It happens once per data version, not per start.

## 2. Render settings (prepared, not applied)

**Start-up: a small launcher, `serve.py`** (about 40 lines; the start command runs it instead of `streamlit run`):
1. Make sure the data file is on the disk (section 1).
2. **Warm up in the background, in the same process,** so the first visitor doesn't pay for it.
   - **Build the search index.** Streamlit runs the page in the process that started it, so the index built here is the one the page uses.
   - **Run the four Explore examples' data steps.** These use stored requests (resolve, fetch, show; no model call, no cost, no log line), so the directory and the most-used tables are read once from disk.
   - The port opens at once, so Render sees the service as healthy. A question asked before the warm-up finishes waits for the index, rather than building a second copy.
3. Start Streamlit, as version 1's `launch.py` does.

**Idle time:**
- On Render's paid instances the process never sleeps, so the index stays in memory between visitors.
- What can still make the first answer after a quiet spell slower:
  - the computer's file cache, so the first database reads come from disk;
  - Anthropic's prompt cache, which expires after 5 minutes, so the first call after a quiet spell pays the full prompt (about 1 to 2 s more, and a little more cost).
- The hosting test measures this separately, as the switch test asks.

**Settings for the version 2 service:**

| Setting | Value |
| --- | --- |
| Build command | `pip install -r requirements.txt` |
| Start command | `python serve.py` (it runs Streamlit on `$PORT`, address `0.0.0.0`, headless, no usage statistics) |
| Python | `PYTHON_VERSION = 3.12.10` (as locally) |
| Instance | **Starter** (512 MB, $7 a month, always on), as version 1 now; Standard (2 GB, $25) only if the hosting test shows memory above about 400 MB |
| Persistent disk | Grow the existing disk from 4 GB to **10 GB**, mounted at `/var/data`, so version 1's data (3.1 GB) and version 2's (3.27 GB) both fit, with room for one data update. Keeping version 1's data is what makes switching back quick. About $2.50 a month (Render disks are about $0.25 per GB a month); a disk can be grown, not shrunk. |
| `IPEDS_LOCAL_DB` | `/var/data/v2/<dataset version>/ipeds_v2.sqlite` (set by `serve.py` from the two values below; shown for reference) |
| `IPEDS_DATASET_REPO` | `yul13011/ipeds-v2-data` |
| `IPEDS_DATASET_REVISION` | the dataset version to use |
| `IPEDS_LOG_DIR` | `/var/data/v2/logs` |
| `IPEDS_DAILY_USD`, `IPEDS_CONVERSATION_QUESTIONS` | the spending guard (section 4) |
| Secrets | section 6 |

**Memory (measured locally):**
- Python with Streamlit, the API client, pandas and Altair loaded: 167 MB.
- With the search index built: 212 MB.
- What comes on top: Streamlit's server, each visitor's session, and the tables of a large answer (a ten-year trend for six schools). Version 1 peaked at about 260 MB on the same plan.
- So Starter's 512 MB should be enough. That's not certain: the hosting test records peak memory from Render's metrics. SQLite reads the database from disk, so its 3.27 GB doesn't count against memory.
- **Disk speed is the bigger unknown:** Render's 0.5-CPU Starter and its disk may make cold reads slower than here.

## 3. Testing on the host before the switch, without a new public link

The live service must keep serving version 1 until the switch, and Render's preview environments need the $25-a-month team workspace. Two ways to test:

**(A) Recommended: a temporary second Render service with a locked page.**
- Same instance type, disk size, start command and settings as section 2; its own small disk; deleted after the test.
- The page shows only "This is a private test" until a passphrase is typed (secret `IPEDS_TEST_PASSPHRASE`; about 10 lines in the page, active only when that secret is set, so the live app never shows it). So the address it gets leads nowhere for anyone else, and it's never shared.
- It downloads the real dataset, so the test covers the download, start-up time, memory, the provisional label and every warning, and real speed on the host (including the first answer after idle, by leaving it for an hour).
- I run the full question set against it once (6g asks for that anyway).
- **Cost:** Render bills by the second. Three days of a Starter-class instance plus a 5 GB disk is about $1 to $3 (about $5 if Standard). The question-set run is about $0.30 of API.
- **This needs your OK,** because it creates a second service with its own address, even though the page is locked.

**(B) No new service: a local copy with the host's limits.**
- Run the app on this computer inside a container with the same Python, the same memory cap and the real download.
- $0, and no address at all.
- But it needs Docker installed (a package to approve), and it can't measure Render's speed, which the switch test requires on the host. So (B) would still leave the speed check for after the switch.

## 4. The spending guard

**Measured cost per turn** (Part 6b's two runs, 246 turns each, Haiku):
- the interpret call averages $0.0011 (95th percentile $0.0021, highest $0.0034);
- with the written summary, about $0.0012 a turn.
- **Sonnet**, which the sidebar still offers, costs about 20 times as much: about $0.025 a turn.

**Proposed limits:**
- **Daily limit: $2.00 of API spend a day** (`IPEDS_DAILY_USD`).
  - That's about 1,600 Haiku questions or 80 Sonnet questions a day.
  - The worst month is $60.
  - The running total is kept in a small file on the disk beside the log, reset at midnight Eastern, and counts the summary call too.
  - When it's reached, new questions get the message below; Explore IPEDS and the definitions browser keep working.
- **Per conversation: 40 questions** (`IPEDS_CONVERSATION_QUESTIONS`).
  - Version 1's real conversations run 1 to 9 turns, so 40 only stops scripts and runaway loops.
  - It's counted in the browser session, so "Clear conversation" or reloading starts a new count. That's acceptable for a guard against accidents; the daily limit is the real cap.
- **Backstop (you, in the Anthropic console):** a monthly spend limit on the key, for example $75. That's above the daily limit's worst case, so it only trips if the app's own guard fails.

**Wording (for page/wording.json, for your approval):**
- **Daily limit:** "The app has answered as many questions as it can today. Please come back tomorrow. Explore IPEDS and the definitions browser still work."
- **Per conversation:** "This conversation has reached its limit of 40 questions. Click "Clear conversation" to start a new one."

Both are logged as the question's outcome (`limit_daily`, `limit_conversation`) and never call the model. About 25 lines in `answer.py` and the page, with tests.

## 5. The question log on the host

- **Where:** `/var/data/v2/logs` on the persistent disk, the same three files as locally:
  - `questions.jsonl`
  - `declines.jsonl`
  - `summaries.jsonl`
- **Separate:** separate from version 1's Google Sheet, which version 2 never touches. Tests pass their own folder, so they never write to it.
- **What each turn records** (as now):
  - when, and the **conversation identifier** (a random 12-character code per browser session; no name, address or IP);
  - the turn number and the question;
  - the model's reply, the shortlist and the resolved request;
  - the outcome and any decline reason;
  - the model, tokens, cost, and model and total seconds;
  - errors.
- **Size:** about 6 KB a turn, so 10,000 turns is about 60 MB.
- **Getting it back:** an owner-only download in About.
  - Type the owner passphrase (secret `IPEDS_OWNER_PASSPHRASE`); the page offers the three log files as one zip.
  - Nothing appears without the passphrase, and it's never in a link.
  - About 20 lines.
  - On your computer, a short script (`scripts/hosted_log.py`) lists the new real users' conversations in the form of `docs/test_questions.csv`, dropping session codes and times, so you choose which to add to the scorecard.
- **Privacy note:** About should say that questions are kept to improve the app. Version 1's privacy note will be checked against this; any change to its wording comes to you.

## 6. Secrets

| Value | Secret? | Where it's set |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Yes | Render → the service → Environment, as a secret. Locally: your environment variable, as now. |
| `IPEDS_OWNER_PASSPHRASE` (log download) | Yes | Render → Environment, secret. You choose it. |
| `IPEDS_TEST_PASSPHRASE` (test service only) | Yes | The test service's Environment only; removed with it. |
| Hugging Face write token (upload) | Yes | Only on your computer (`hf auth login`). Never on Render: the dataset is public, so the host needs no token to download. |
| Dataset name and version, folders, limits, Python version | No | Render → Environment, plain values. |

None of these is ever written into the repository, the logs or a report. The history check before each push already looks for keys.

## 7. The switch, and how to reverse it (Render dashboard)

**Before:** the hosting test passed (section 3), the switch test met (6g), and your own test done.

**Switching to version 2:**
1. Open the dashboard and the service behind ipeds-research-companion.onrender.com.
2. **Settings → Disk:** confirm it's 10 GB (grown in advance; growing it doesn't restart the app's data).
3. **Environment:** add the version 2 values from section 2 and the two secrets. Leave version 1's values in place; version 2 ignores them.
4. **Settings → Build & Deploy → Repository:** change it to `yul13011/ipeds-research-companion-v2`, branch `main`.
5. Set the build command to `pip install -r requirements.txt` and the start command to `python serve.py`.
6. **Save, then Manual Deploy → Deploy latest commit.**
7. **Watch Logs:** the data download (first time, 1 to 2 minutes), then "index ready", then Live.
8. Open the link and ask the checklist's first three questions.

**Switching back to version 1:**
1. **Settings → Build & Deploy:** set the repository back to version 1's (`IPEDS-research_companion`) and its branch.
2. Set the build command back to `pip install -r prototype/requirements.txt` and the start command back to version 1's `streamlit run prototype/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false`.
3. **Save, then Manual Deploy.**
   - Version 1's data and variables were never removed, so it starts as before, with no download.
   - Version 2's log stays on the disk.

I'll write both lists into `UPDATING.md` as the record, with the exact values copied from the dashboard before the switch, in case version 1's settings differ from its runbook.

## What I'd build after your go

| Piece | About |
| --- | --- |
| `serve.py` (download, index in the background, start Streamlit) | 70 lines |
| Spending guard (`answer.py`, page) | 25 lines |
| Owner log download, test passphrase (page) | 30 lines |
| `scripts/hosted_log.py` | 40 lines |
| Tests for each, with no network and no shared log | |

The question path itself doesn't change, except the guard's check before the model call.

## Your decisions

1. The dataset's name, and how to upload it (install `huggingface_hub` in `.venv` only, or the website).
2. The instance type (memory, above).
3. The hosting test: (A) a temporary locked second service, or (B) a local container.
4. The daily limit ($2) and the per-conversation limit (40), and the two messages.
5. The owner-only log download in About.
6. Growing the disk to 10 GB.
