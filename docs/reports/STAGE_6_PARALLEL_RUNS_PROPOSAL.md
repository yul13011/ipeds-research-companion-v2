# Proposal: running the question set in parallel

Date: 2026-11-26. Proposal only; nothing built.

## Today

- **One run** is 242 turns in 182 conversations, asked one after another.
- **The run takes about 26 minutes.** That's 1,551 s of turn time in run 1 of Part 6a's end, plus a few seconds to start.
- **Cost:** $0.27 per run.
- **Per run, from run 1's log:**
  - 263 classification calls plus about 128 summary calls;
  - about 1.3 million uncached input tokens and 2.2 million cached ones;
  - 234,000 output tokens.

## What would change

- **Conversations run side by side; turns within a conversation stay in order,** since each needs the turns before it. The longest conversation takes about 1 minute (7 turns).
- **Each worker is a separate process with its own log folder.** The script merges the folders at the end, in the usual order, so the grader and the review files are unchanged. Separate processes avoid two writers on one log file.
- **About 40 lines** in `scripts/stage4_run.py`. Nothing in the question path changes.

## Expected run time

| Workers | Run time (estimate) |
| --- | --- |
| 1 (today) | about 26 min |
| 4 | about 7 to 8 min |
| 8 | about 4 to 5 min, if the rate limits allow |

The cost per run is the same: the same calls, made sooner.

## Rate limits

- **The API limits requests and tokens per minute** for each organisation. The limits depend on the account's usage tier, which I can't see from here. The owner can see them in the Anthropic Console, under Limits.
- **Four workers would send about 50 requests and 170,000 uncached input tokens a minute** (cached reads usually count less, or not at all, toward the input limit). Eight would send about twice that.
- **Today a call gets one retry,** and a refused call becomes a plain failure. A parallel run would need to:
  - wait and retry when the API answers "rate limited" (429), using the wait time the API gives;
  - log each wait, so a slow turn caused by the limit is visible.
- **Proposal:** start with 4 workers. Drop to 2 automatically if more than a few 429s come back.

## Effect on the timing figures

- **Turn times from a parallel run aren't comparable with today's:**
  - calls made at the same time can wait in the API's queue;
  - the four processes share the computer's processor and disk when reading the database.
- **The median turn and "turns over the limit" would likely rise a little,** and no longer measure what one user sees.
- **Proposal:**
  - Use parallel runs for the scorecard: right or acceptable, the four rows, cost.
  - Take the timing figures from one sequential run per part. That can be the first run of a part's two, or the run on the host in Part 6g.
  - Every report says which run the timings come from.
- **The model's own time per call** (`model_seconds`) is still logged in a parallel run, so a big change in the model's speed would still show.

## Decisions needed

1. Build it, and with how many workers to start (proposal: 4)?
2. Timing figures from one sequential run per part: agreed?
