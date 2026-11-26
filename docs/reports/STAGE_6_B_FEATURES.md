# Stage 6, part 6b: review point — version 1's features and how each works in version 2

Date: 2026-11-26. Nothing is built yet. This is the list the work order asks for before building. Read from version 1's `prototype/ui.py`, `components.py`, `learning_content.json`, `responses.py` and `.streamlit/config.toml`; nothing in `..\agent-redesign` was changed.

## In short

- Most of version 1's page carries over as it is: copy its page code, CSS and wording, and replace its data calls with version 2's `answer.ask`, `choose`, `pick_school` and `take_offer` and the page object they return.
- **Six things don't fit version 2 as written** and need your decision (F1 to F6, at the end). The biggest:
  - **Version 1 has no sidebar.** Its model selector is on the About page, and "Clear conversation" sits beside the chat box. Point 3 of the work order ("rebuild the sidebar to look like version 1's") has nothing to copy.
  - **Version 1's AI switch turns on a keyword parser.** Version 2 can't have one (no wording rules).
  - **Version 1 hides the definitions browser** behind a "development mode" switch. Users see "Under development".
- **Streamlit:** version 1 uses 1.66.0, version 2 uses 1.58.0. Version 1's page code uses features of the newer version (horizontal containers, `key` on containers for the CSS, `height="stretch"`, `icon_position`). Following point 2 (same version as version 1) means moving version 2 up to 1.66.0. That's a package change, so I'm asking: **go to upgrade Streamlit to 1.66.0?** Nothing in version 2 needs a version newer than that.

## The features

### Whole page

| Version 1 | What it does | Version 2 |
| --- | --- | --- |
| Theme (`config.toml`) | Teal primary `#196F66`, off-white background, dark-blue text, sans serif | Copied as it is |
| Page CSS (`main()` in ui.py, about 75 lines) | Card backgrounds, border radius, nav underline, panel heights, mobile reordering | Copied as it is |
| Header | "IPEDS Research Companion" with a "Beta" label; tabs "Explore IPEDS" and "Ask & Analyze"; an "About this prototype" button | Copied |
| "Hide Menu" / "Expand Menu" | Collapses the header and the introduction on the chat page | Copied. This is version 1's "menu"; it stands in for "sidebar open and closed" in the check (F1) |
| Transcript scrolling (`transcript_scroll.js`) | Keeps the newest answer in view in the fixed-height chat box | Copied |
| "Database missing" | Red error, page stops: "Local metadata catalog missing. See ingestion/README.md." | Same style. The check is for `data\ipeds_v2.sqlite`, and the wording names version 2's build command (F5) |

### Explore IPEDS

| Version 1 | What it does | Version 2 |
| --- | --- | --- |
| Title, intro, "Ask a question →" | Opens the chat | Copied |
| "10 annual releases · 2015–16 Final through 2024–25 Provisional" | Typed into the code | **From the database's list of releases**, so it can't go out of date. Same wording |
| Six topic cards | Icon, title, subtitle, one-line summary, "Explore topic →" | Copied, with wording, from `learning_content.json` |
| The open topic | Description, a scope note (blue box), three example questions with their kind ("ONE DATA POINT"), "Ask your own question about …", × to close | Copied. **An example click sends its question to the chat as if typed**, through the question path. In version 1 an example ran a fixed plan with no model call. Version 2 has no fixed plans, so the example is only as good as the question path, which is why each must pass in the question set |
| Footer caption | "IPEDS is collected by NCES…" | Copied |

**The 18 example questions in the question set.** 12 are already in it (from real users' questions or the tests). Six are not and will be added with expectations:
- "Compare Ivy League undergraduate enrollment in fall 2024."
- "Give me Yale undergraduate and graduate enrollment from 2015 through 2024."
- "What percentage of undergraduates received grants or scholarships in 2023-24? Compare eight Ivy League institutions."
- "Compare nine-month-equivalent average salaries of full-time professors, associate professors, and assistant professors at Yale, Harvard, and Princeton in 2023–24, excluding medical-school staff."
- "Show Yale's instructional staff count from Fall 2015 through Fall 2024, split by full-time and part-time."
- "Which Massachusetts colleges offer distance education to undergraduates?"

Two of these may not pass today: "excluding medical-school staff" needs a measure or breakdown row that separates medical-school staff, and the distance-education list needs that column as a condition. If either is missing from the dictionary, I'll report it and ask, not add a rule.

**The cards' scope notes are copied as written.** Two describe version 1's data in ways I'll check against version 2's dictionary before copying, and list any that aren't true of version 2:
- admissions: "SAT section medians are available from Fall 2022";
- outcomes: the 2015–2024 outcome years against 2009–2018 entering cohorts.

**Where the topic content lives (F6).** The cards are page wording, not IPEDS conventions. I'd keep them in one content file next to the page (`page/explore.json`), copied from version 1 without its version 1-only fields (`families`, `discovery_query`, `kind`, `cost_route`).

### Ask & Analyze

| Version 1 | What it does | Version 2 |
| --- | --- | --- |
| Three columns | "Need ideas?" on the left, the chat in the middle, "Analysis tools" on the right; ‹ and › collapse each side, "› Ideas" and "Tools ‹" bring them back | Copied |
| "Need ideas?" | A topic dropdown and the topic's three examples as buttons | Copied; examples are sent as typed questions (above) |
| "Analysis tools" | Without development mode: an "Under development" box. With it: "Build a data extract" and "Browse definitions" cards | See F3 |
| Chat title and introduction | "What would you like to learn?" and "Ask about one or many institutions, for one year, selected years, or a range." | Copied |
| Chat box | "Ask a question about IPEDS data…", then "Ask a follow-up question…"; locked while working | Copied |
| "Clear conversation" | A small button beside the chat box, once there is a conversation | **Moved there from version 2's sidebar.** Clears the conversation, the turns and any open picker |
| Caption under an empty chat | "Request a table, CSV extract or chart. {model} · AI interprets each typed request, including chart edits." | Wording to change (F4): chart edits are declined until Stage 7, and downloads arrive in Part 6c |
| Status line while working | A grey caption with a spinner, inside the answer's bubble | **Version 1's caption style replaces version 2's `st.status` box.** The messages stay version 2's (`answer.status`) |
| Error box | A red box at the top of the chat | Same style; wording in F5 |

### Answers

| Version 1 | What it does | Version 2 |
| --- | --- | --- |
| "Interpreted as" | Grey caption, "Interpreted as: …" | Version 1's caption, version 2's text. **This drops version 2's bold label.** |
| Written summary | Streamed under "Interpreted as", above the table; a "Verified summary" popover shows the checked message it was built from | Version 2's summary, streamed in the same place. Version 2 checks the summary against the table instead of writing it from a fixed message, so there's nothing for the popover to show. I'd leave the popover out (F2, a small difference) |
| Several answers in one turn | Numbered bold heading for each part, with a status caption | Version 2's "several" answers use this style |
| Clarifying question | Message, then one button per option in a row ("Use A"), with "Choose an option, or type a change to refine it." | Version 2's options, in version 1's row of buttons with its caption. Button text is version 2's own labels |
| School picker | "Institution: {name}", a dropdown, a "None of these? Refine by name, city/state or UNITID" box, "Continue" and "Cancel" | Copied. The refine box uses version 2's school search (`search_schools`). Cancel answers "Cancelled. No analysis ran." |
| Decline | Plain text | Plain text, replacing version 2's blue box |

### Results

| Version 1 | What it does | Version 2 |
| --- | --- | --- |
| Warnings | Yellow boxes above the table | Same |
| Single-number tile | Large figure with its measure | Same; version 2 adds the school and period as a caption, already in version 1's caption style |
| **"Display table" switch** | On each answer in the chat. **Off by default when a chart is shown**, on when there's no chart. Version 1 also turned it on when the question said "table", by reading the wording | Copied with the first rule only. Version 2 can't read the wording, so a user who wants the table turns the switch on. The default (off with a chart) is your decision (F2) |
| "Show underlying counts and data status" | A checkbox under the table | Same (already there) |
| Chart | Bold title, grey subtitle, the chart, a grey note under it | Version 2's automatic chart, already in version 1's palette and font, with version 1's title, subtitle and note around it. Without "Format chart", "Preview & download chart" and the hint about formatting (Stage 7, approved) |
| "Definitions & sources" | A popover button beside "Download Data" | **Version 1's popover replaces version 2's expander.** Version 2's definition fields inside |
| "Download Data" | Popover with Excel, CSV and JSON | Part 6c. Until then the button isn't shown |
| Extract layout, "Edit institutions…" | Only in the extract builder's result | Not carried over (Stage 7) |
| Model usage and cost | Only in the extract builder's result | Not carried over |

**Version 2's own elements, in version 1's styles only** (each will get a screenshot for your approval):
- **Years held:** a table plus a caption.
- **Statements** (for example, "No years were given, so the trend covers every release that holds the figure"): grey captions.
- **Provisional notes and the data-release line:** grey captions.
- **Offer buttons** (for example, figures after years held): version 1's option buttons.
- **The "which group" and "which figure" questions:** version 1's clarifying-question style.

### Tools: definitions browser

| Version 1 | What it does | Version 2 |
| --- | --- | --- |
| "Browse definitions" | Search box, release-year picker, a "coded categories and release documentation" checkbox; results as a table, one row opening the full definition, code labels and source reference | Copied layout, searching version 2's copy of the codebooks: `VARTABLE` (variable titles and long descriptions), `TABLES` (table descriptions) and, with the checkbox, `VALUESETS` (code labels). **Version 2's database has no release documentation**, so the checkbox label becomes "Also search coded categories" (F3) |

This is a search over the codebook, like the school search: it finds text and shows the codebook's own words. It doesn't decide what a question means, so it doesn't break the rule against wording patterns. It is a new module (about 40 lines) with its own tests, and makes no model call.

### About

| Version 1 | What it does | Version 2 |
| --- | --- | --- |
| Intro and blue info box | Releases held, provisional, aggregates under review | Copied; the release range comes from the database |
| Model selector | "Model strategy", with "Automatic (Haiku, then Sonnet)" and a caption on how it works | **Moved here from version 2's sidebar.** Version 2's model list, default Haiku. Version 1's caption describes its own two-model setup and would be wrong, so it needs new wording (F4) |
| AI switch | "Use conversational AI". Off: a keyword parser answers | See F1 |
| AI caption | What is sent to Anthropic | Copied, rewritten to what version 2 sends: the question, the shortlist and the last five requests (F4) |
| Privacy | The question log note | Copied as it is. Part 6f will check it is true on the host |
| Developer settings | The development mode switch | See F3 |
| Benchmark match rates | Two tiles, Yale and NCES, read from version 1's summary files | Same tiles, read from **version 2's latest benchmark files** (`docs/reports/stage4/benchmarks.csv`, and the trend file). The benchmark scripts will also write a small summary, which the page reads |

### Behind the scenes

- **Summary switch:** removed from the page; the summary is always on. `config.SUMMARY` (an environment variable) stays, for testing only. One line in DECISIONS.md.
- **Question log:** unchanged (local). Part 6f moves it to the host.

## Decisions needed

**F1. The sidebar and the AI switch.**
- **The sidebar:** version 1 has none. I'd do what version 1 does: no sidebar, the model selector on About, "Clear conversation" beside the chat box. "Sidebar open and closed" in the check becomes "menu expanded and hidden" and "side panels open and collapsed".
- **The AI switch:** version 2 can't answer without the model. Two options:
  - (a) Leave the switch out, and list its absence as an approved difference.
  - (b) Keep it. Off, the chat box says the AI is off, and Explore, the ideas panel and the definitions browser still work.

  I recommend (a). With the switch off, nothing typed can be answered, and the examples go through the model too.

**F2. Small differences in answers.**
- "Display table" is off by default when a chart is shown (version 1's rule)?
- The "Verified summary" popover is left out?

**F3. The tools panel.** Version 1's users see "Under development". Two options:
- (a) Show the "Browse definitions" card to everyone, drop the extract card (Stage 7), and drop "Developer settings" from About.
- (b) Copy version 1 exactly: "Under development" unless development mode is on.

I recommend (a), since the work order carries the browser over for users.

**F4. Wording that would be wrong if copied.** I'll draft new wording in version 1's voice for your approval:
- the empty-chat caption (CSV extract, chart edits);
- the model caption ("Automatic …");
- the AI caption (what is sent);
- the codebook checkbox label.

**F5. Error messages.** Version 1's three mention the extract builder and offline examples. Version 2 needs one for each of these:
- the API's usage limit is reached;
- the model isn't available to the key;
- the API is down or the network fails;
- the time limit is passed;
- the database is missing;
- any other failure.

Version 2 has no time limit on a model call today. I'd add one (for example 30 seconds, from `config`) so a hung call gets a message. I'll draft the wording for your approval. Is 30 seconds right?

**F6. Where the topic cards and example questions live.** A page content file (`page/explore.json`), not the dictionary, as they're wording, not conventions. Agree?

## What happens after your go

1. Upgrade Streamlit to 1.66.0, if you agree, and run the tests.
2. Copy version 1's page code into a `page/` folder, rewired to version 2. `app.py` becomes the entry point. I'll report how much was copied and how much rewritten.
3. Write the definitions search, the benchmark summary, the error messages and the time limit, each with tests.
4. Add the six example questions to the question set, with expectations.
5. Take screenshots of version 1 and version 2 side by side, at the same window size, for each screen and state. **This needs a screenshot tool:** may I install Playwright, or should I use the browser pane in this app (no install, but by hand, one state at a time)?
6. Report each difference, and stop at the screenshots of version 2's own elements for your approval.

The question path doesn't change in this part. The page grows from 161 lines to about 600 (version 1's ui.py and components.py, without the extract builder and chart editor).
