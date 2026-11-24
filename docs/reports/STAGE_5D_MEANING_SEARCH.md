# Stage 5, part 5d: the meaning-search comparison

Date: 2026-11-24. Done in two throwaway Python environments in my scratch folder, as you approved. Nothing was installed in your main environment: its huggingface-hub is still 2.3.0, and the app is unchanged. The script is `scripts/meaning_compare.py`; each question's result is in `docs/reports/stage5d/meaning_compare.csv`.

## What was compared

- **The libraries:** fastembed (runs the model with ONNX Runtime) and sentence-transformers (runs it with PyTorch), with the same small English model, BAAI's bge-small-en-v1.5. With the same model, any difference is the library's.
- **Fingerprints:** made once for all 3,100 measures and 4,938 school groups, as the build would make them. Each question gets its own fingerprint when it is asked.
- **The three searches:**
  - **word search alone:** the app's shortlist, unchanged;
  - **meaning search alone:** the 20 measures and 15 groups closest in meaning, the same number of places the word shortlist gives them;
  - **both merged:** the word shortlist, plus the 10 measures and 5 groups closest in meaning that it doesn't already hold. That makes the shortlist about 10 measures longer (from 33 to 43 on average).
- **The questions:** every question with an expected measure ID or group, read on its own without the earlier turns of its conversation.
  - From the badly written set: 43 with a measure and 14 with a group.
  - From the full question set: 25 with an expected measure ID. Most of the full set's expectations name a concept rather than an ID, so they can't be counted automatically.

## Results

The two libraries found exactly the same items for every question. They differ only in speed and size.

| | Word search alone | Meaning search alone | Both merged |
| --- | ---: | ---: | ---: |
| Badly written set: the right measure | 34 of 43 | 15 of 43 | 34 of 43 |
| Badly written set: the right group | 6 of 14 | **11 of 14** | **11 of 14** |
| Full question set: the right measure | 20 of 25 | 11 of 25 | 20 of 25 |

| | fastembed | sentence-transformers |
| --- | ---: | ---: |
| Time added per question (median; 90th percentile) | **18 ms** (22 ms) | 36 ms (42 ms) |
| Loading the model when the app starts | **7.5 s** | 36 s |
| Fingerprinting the dictionary once (in the build) | 165 s | 129 s |
| Installed packages, over an empty environment | **169 MB** (onnxruntime, NumPy, helpers) | 1,095 MB (mostly PyTorch) |
| Model files | **about 67 MB** | about 127 MB |

My earlier estimate of about 15 MB for fastembed's packages was too low: it left out NumPy and onnxruntime's own dependencies. The figure above is measured.

## What the results mean

- **Groups:** meaning search helps a lot. It finds the systems from the names people use, which word search misses:
  - CUNY for "how many students at CUNY" and "CUNY enrollment";
  - California State University for "cal state tuition";
  - University of California for "UC system admit rate";
  - University of North Carolina for "UNC enrollment".

  Merged, the right group reaches the shortlist in 11 of 14 questions, against 6 of 14 for word search alone.
- **Measures:** meaning search on the question as asked adds almost nothing. It finds the right measure when the question is only about the measure: "admission rate" alone puts the admission rate first. In a real question, the other words pull it off course.
  - School names, years and words like "kids" pull towards the hundreds of measures whose titles carry years and cohorts.
  - So "What was Yale's admission rate in fall 2024?" ranks the admission rate about 1,000th.
- **Making fingerprints from each measure's own name and synonyms only** (no table title or description) was faster: 85 s to fingerprint and 14 ms per question. It found one more measure (Penn State undergraduates) and changed nothing else.
- **The word search's misses on measures** are questions that don't use the measure's words, and meaning search doesn't rescue them either:
  - "how many kids go to umich", "ASU how big is it", "frcc how many students";
  - "harvard enrolment since 2015";
  - "michigan state grad rat".

  These need the next layer in the work order: the AI's own search, where the model searches with its own words. A search made in its own words leaves out the school names and years.
- **The five misses in the full set** are follow-ups or open questions: "What about Harvard?", "Add Princeton.", "how has this changed since 10 years ago?", "What can you show me instead?", and the PhD-enrolling comparison. In the app, these are covered by carrying the previous request forward, which this test left out on purpose.

## Recommendation

**fastembed.** It finds exactly the same items as sentence-transformers. It takes half the time per question, loads five times faster when the app starts, and needs about a seventh of the disk space (no PyTorch). Both are well inside the speed limits: under 5 seconds for typical questions.

How to use it, as the work order describes, with what this test shows:
1. Make meaning fingerprints for measures, groups and term readings in the build, from each entry's own name and synonyms.
2. On every question, merge the closest groups by meaning into the word shortlist. That is where it pays off.
3. Merge the closest measures as well. That costs little (about 10 more measures on the shortlist) and helps a little.
4. Then the AI's own search, which this test suggests is where the remaining measure misses will be fixed.

## Open questions

1. **Which library:** I recommend fastembed.
2. **The dedicated environment for version 2.** As you asked, I won't set it up until you say so. The plan:
   - a virtual environment in the project folder (`.venv`, ignored by git);
   - exact versions pinned in `requirements.txt`: fastembed 0.9.1 and onnxruntime 1.32.0, plus what the app already uses (streamlit, anthropic, altair, pandas), at the versions now in use;
   - the model files cached in the project's ignored data folder;
   - the run commands in `CLAUDE.md` changed to use that environment.
3. **Meaning search for school names** wasn't tested. The badly written set's school abbreviations (Mizzou, CUNY, WSU) are matched by the nickname table, IPEDS's alias field and the word search. Fingerprinting 6,000 school names is possible, but meaning search is weak with names and abbreviations, so I don't propose it.
