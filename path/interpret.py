"""Step 3, Interpret: the one model call.

The model is shown the shortlist for this question, the previous request, any pending
clarifying options, and the question, each shortlist item with a short tag. It returns one
structured reply in tags (request.reply_schema, built for this question), enforced by the API's
structured output; code maps the tags back to real IDs. It never writes SQL and never produces a number.

The call itself is passed in (`call`), so tests use saved replies and never reach the API.
"""
import json
import time

import config
from path.request import COMPARISONS, OPERATIONS, REPLY_SCHEMA, from_wire, to_wire

INSTRUCTIONS = """You read questions about U.S. colleges for an app that answers them from IPEDS data.
You do not answer the question. You turn it into one structured reply that code will run.

Rules:
- Every item in the SHORTLIST has a tag (M1 measure, S1 school, G1 group, R1 category row, B1 breakdown set,
  T1 term reading, O1 outside-IPEDS topic, C1 explanation, D1 glossary entry). Answer with tags only. If what the question needs has no tag,
  decline and say what is missing.
- Never write SQL and never state a number from the data.
- Leave a field empty when it does not apply: "" for a tag, a choice or text, 0 for a number, an empty list. Fill only the parts the kind you choose needs.
- Choose kind, and fill `requests` to match:
  request: one complete request for a new question (its label can be empty).
  edit: a follow-up that changes the PREVIOUS REQUEST ("add Northeastern", "now for Texas", "rank them",
        "break that down by gender"). List each changed field in `changes` with add, remove or replace, and put only
        the new values in one item of `requests`. Leave everything else to the previous request.
        "Go back", "as before", "back to all eight": one change with action back (any field). The app restores
        the whole earlier request, operation included; do not rebuild it field by field.
        A reference to schools already named ("the example set", "those schools", "the same institutions", "them")
        means the schools in the PREVIOUS REQUEST: keep them; never pick new schools for it.
  options: the question has two or three reasonable readings. Give each as a complete request with a short label.
  choose: the user is answering the PENDING OPTIONS ("the first one", "B", "both"). Give their 0-based numbers.
        If no PENDING OPTIONS are open, a reply like that still is kind choose, with chosen empty: the app asks what
        the user means.
        If PENDING OPTIONS are open and the user changes something without choosing ("show 2023-24"), return an
        edit with that change; the app applies it to every option and asks again.
  decline: the question cannot be run as asked. Put in `requests` the one request you would have made, as far as
        the question allows (its school, group, measure and year), so a follow-up can change it. Set `missing`:
        measure (no listed measure fits), group, calculation, breakdown, not a data question, other.
        Never decline, or add a note or an outside topic, because of the years asked for: write the years as the user
        named them, and the app checks which years it holds. Use "not in IPEDS" only with an outside-IPEDS topic (O tag) in the request;
        never decide on your own that IPEDS lacks something: if nothing listed fits, use measure.
        If the question as a whole is about an outside-IPEDS topic (O tag), the request names no measure.
        If only one part of the question is outside IPEDS and another part can be answered, do not decline:
        return a request for the part that can be answered, with the O tag in outside.
        reason and closest are for the app's log only; keep each to one short sentence (at most 25 words).
  about_decline: the user asks about the answer the app just declined: "why not?" (about = why),
        "where can I find that?" (where), "what can you show instead?" (instead). Fill decline.about only.
  search: nothing on the SHORTLIST fits what the question needs (a measure, a group, a school). Put in search_words
        a few plain words for the missing item only, in the words a data dictionary would use ("total fall
        enrollment", "community colleges", "University of Missouri"); leave out the rest of the question. The app
        searches and shows the shortlist again with what it found first. Use it only while SEARCHES LEFT is above 0,
        and only before deciding to decline for want of a measure, group or school. With no searches left, answer
        from the shortlist or decline. For every other kind, search_words is empty.
- Operations: {operations}
- measures: pick the measure that matches. For a multi-row measure, name a category row (R tag listed for that
  measure) only when the user asks for one, such as transfer-in students; otherwise leave `row` empty and the app
  uses the overall total. A measure lists its categories (such as full-time/part-time or level) with their R tags.
  When the user asks for several categories of one measure ("full-time and part-time", "undergraduates"), list the
  measure once per category, each with its R tag; a breakdown keeps the category the user asked for in `row`.
- breakdown: use a breakdown set (B tag) listed for the measure you chose. A set listed "through the detailed table"
  also works for that measure.
- TERMS: a term lists its readings, each with a T tag. If the user said which reading they mean, put its tag in `readings`.
  If the user named a specific reading (such as the overall 150% rate), always give its T tag.
  If the term says "always ask" and the user did not say, return options, one per reading.
  Otherwise use the reading marked default.
- schools: write each name as the user wrote it, with its S tag if the shortlist clearly has that school,
  or "" if it does not or several schools could be meant. A nickname or short name that means one school (UConn,
  UMich, Mizzou, Purdue, Northeastern) is that school: give its tag. Only for a name several schools share (such as
  "BU" or "U of M") or a name no listed school has (such as "RTI"), give "", never another school's tag; the app
  then offers the nearest names. This holds in a decline too.
- groups: G tags. A school must be in every group named.
- plus_schools: schools added to a group's list ("the Ivies plus MIT and Stanford"): the group in groups, the added
  schools' S tags in plus_schools.
- Schools named in an earlier turn ("the same institutions", "the example set") are listed under SCHOOLS NAMED
  EARLIER; use their tags.
- Figures over years that names no figure at all ("show a 10-year trend"): kind request, measures empty, with the years.
- several: when one message asks two things ("which years do you have... and compare the latest year"), give kind
  several with one complete request for each, in order.
- "its peers" or "peer institutions": set peers_of to the school's S tag.
- conditions: comparison is one of {comparisons}; value is a number or a category code, written as text.
- year: copy the year as the user stated it, or leave it empty. Set kind only if the user said (fall, fiscal year, ...).
  For "the latest" or "the most recent year", leave stated empty and set kind to latest.
  span says whether the question is about one year or a period:
    one year: a single year, however written ("2023", "2022-23", "fall 2024", "the 2016 entering cohort"), or none;
    from a year on: "since 2015", "from 2018 on" (start);
    a range of years: "2015 through 2024", "between 2016 and 2020", "2014-15 to 2023-24" (start and end);
    the last N years: "the last five years", "a 10-year trend" (last);
    the change between two years: "how did it change from 2015 to 2024" (start and end).
    A trend or change with no years named ("how has it changed", "over time"): a range of years, start 0 and end 0.
  start and end are calendar years exactly as the user named them, never shifted for a measure that is reported a
  year behind: the app handles that. Example: "2023-24" means start 2023 and end 2024, for every measure; for one year, start
  is that year, or 0 if no year was named; a year written as two ("2022-23") gives start 2022 and end 2023. Write 0 for any of start, end and last the span does not use.
  For a ranking or a list over a period, the figure is the change between the first and last year, and a condition
  ("lost enrollment", "grew by more than 1,000") applies to that change. For a group over time, membership is "each year" unless the user asks
  for today's schools only ("today").
- define and data_exists: put the matching measures in measures, or the outside-IPEDS topic (O tag) in outside.
  A question about which years are held ("which years do you have for net price?") is data_exists, with its schools
  or group if it names them.
- C (explanation) and D (glossary) tags are only for define, when the user asks what a word or idea means
  ("what is an adjusted cohort?"). Never use them, or define, for a question that asks for figures
  ("retention rate at Yale" is a data question). For define, put in explain the C and D tags that explain the word
  asked about, and the matching measures in measures if the word is a measure. Only if no C, D or M tag explains it,
  write a short general explanation (at most three sentences) in general: no numbers, and never say whether IPEDS
  collects something. Otherwise general is "".
  For a broad topic ("admissions", "finance", "faculty"), list every shortlist measure that belongs to it, up to 15.
  Only if no listed measure belongs to the topic, put the user's topic in plain words in topic.
"""


def render(short, previous, pending, question, declined=None, searches=None, searches_left=0, earlier=()):
    """The shortlist and conversation as plain text for the model, in tags. Returns (text, words per part)."""
    parts = {}
    def section(name, lines):
        parts[name] = lines
    rows = []
    for m in short["measures"]:
        flag = (f" | no longer collected: IPEDS collected it {m['retired']}" if m.get("retired")
                else " | not set up in this app yet" if not m["set_up"] else "")
        b = (f" | breakdowns: {', '.join(m['breakdowns'])}" if m["breakdowns"] else "") + \
            (f" | breakdowns through the detailed table, held at {m.get('detail_held') or 'this measure'}: "
             f"{', '.join(m['breakdowns_via_detail'])}" if m["breakdowns_via_detail"] else "")
        cats = "".join(f" | categories by {c['column']} (default: {c['default']}): {', '.join(c['tags']) or 'none shortlisted'}"
                       for c in m.get("categories", []))
        also = (f" | also by subgroup, not listed (search for one if asked): {', '.join(m['variants'][:12])}"
                if m.get("variants") else "")
        rows.append(f"  {m['tag']} | {m['name']} | {m['period'] or ''} | {m['unit'] or ''}{cats}{b}{also}{flag}")
    section("measures", ["Measures (tag | name | period | unit):"] + rows)
    rows = []
    for t in short["terms"]:
        rows.append(f"  {t['term']}" + (" (always ask)" if t["always_ask"] == "yes" else ""))
        for r in t["readings"]:
            extra = " | default" + (f" for {r['default_for']}" if r["default_for"] else "") if r["is_default"] == "yes" else ""
            when = " | offered when a group mixes levels" if r["when"] else ""
            uses = f" | {', '.join(r['measure_tags'])}" if r["measure_tags"] else ""
            only = " | used only when the question asks for it specifically" if r.get("only") else ""
            rows.append(f"    {r['tag']} | {r['reading']}{uses}{extra}{when}{only}")
    section("terms", ["Terms (tag | reading):"] + rows)
    section("schools", ["Schools (tag | name | city, state | also called):"] +
            [f"  {s['tag']} | {s['name']} | {s['city']}, {s['state']} | {s['alias'] or ''}" for s in short["schools"]])
    section("groups", ["Groups (tag | name | definition):"] +
            [f"  {g['tag']} | {g['name']} | {(g['statement'] or '')[:120]}" + (" | not available" if g["status"] == "decline" else "")
             for g in short["groups"]])
    section("rows", ["Category rows (tag | label | for measures):"] +
            [f"  {r['tag']} | {r['label']} | {', '.join(r['for'])}" for r in short["rows"]])
    section("sets", ["Breakdown sets (tag | set | for measures | held at):"] +
            [f"  {s['tag']} | {s['set']} | {', '.join(s['for'])} | {s.get('held') or 'the measure row chosen'}"
             for s in short["sets"]])
    section("outside", ["Outside IPEDS (tag | topic):"] + [f"  {o['tag']} | {o['topic']}" for o in short["outside"]])
    section("explain", ["Explanations, for define only (tag | concept or glossary term | start of the text):"] +
            [f"  {c['tag']} | {c['concept']} | {c['explanation'][:100]}" for c in short.get("concepts", [])] +
            [f"  {g['tag']} | {g['term']} | {g['definition'][:100]}" for g in short.get("glossary", [])])
    convo = ["PREVIOUS REQUEST" + (f" (the app declined it: {declined})" if declined else "") + ": " +
             (json.dumps(to_wire(previous, short["tags"])) if previous else "none")]
    back = {key: t for t, (kind, key) in short["tags"].items() if kind == "schools"}
    named = list(dict.fromkeys(s["id"] for r in reversed(list(earlier)) for s in r["schools"] + [
        dict(id=u) for u in r.get("plus_schools") or []] if s.get("id") in back))      # newest first
    if named:
        names = {s["id"]: s["name"] for s in short["schools"]}
        convo.append("SCHOOLS NAMED EARLIER: " + "; ".join(f"{back[u]} {names.get(u, u)}" for u in named))
    for s in searches or []:
        convo.append(f"YOUR SEARCH: {s['words']!r} found " + (", ".join(f"{len(v)} {k}" for k, v in s["added"].items())
                                                                  or "nothing new") + " (listed first above)")
    convo.append(f"SEARCHES LEFT: {searches_left}")
    if pending:
        convo += ["PENDING OPTIONS:"] + [f"  {i}: {o['label']}" for i, o in enumerate(pending)]
    section("conversation", convo)
    section("question", ["QUESTION: " + question])
    order = ["measures", "terms", "schools", "groups", "rows", "sets", "outside", "explain", "conversation", "question"]
    text = "\n".join(["SHORTLIST"] + [line for name in order for line in parts[name]])
    return text, {name: len(" ".join(parts[name]).split()) for name in order}


def check(reply):
    """The parts a reply of each kind must carry. Returns a problem, or None."""
    if reply["kind"] == "search" and not reply.get("search_words"):
        return "a reply of kind search came without search words"
    needs = {"request": "request", "edit": "edit", "decline": "decline"}
    if reply["kind"] in needs and not reply.get(needs[reply["kind"]]):
        return f"a reply of kind {reply['kind']} came without its {needs[reply['kind']]}"
    if reply["kind"] == "options" and len(reply.get("options") or []) < 2:
        return "a reply of kind options came with fewer than two options"
    if reply["kind"] == "several" and len(reply.get("several") or []) < 2:
        return "a reply of kind several came with fewer than two requests"
    return None


MAX_SEARCHES = 2                    # the model's own searches per question (owner decision, 2026-11-24)


def one_call(system, user, model, schema, short, call, meta):
    """One model call with one retry. Returns the reply in code form, or None (meta["error"] says why)."""
    meta["calls"] += 1
    reply = None
    for _ in range(2):                              # one retry, then a plain failure
        meta["attempts"] += 1
        try:
            text, usage = call(system, user, model, schema)
            for key in ("input_tokens", "output_tokens", "cache_write_tokens", "cache_read_tokens"):
                meta[key] += usage.get(key, 0)
            meta["raw_reply"] = json.loads(text)
            reply = from_wire(meta["raw_reply"], short["tags"])
            problem = check(reply)
            if problem:
                raise ValueError(problem)
            meta["error"] = None
            return reply
        except Exception as e:                      # any failure is recorded and retried once
            reply, meta["error"] = None, f"{type(e).__name__}: {e}"
    return reply


def call_api(system, user, model, schema):
    """One call to the Anthropic API with the reply held to this question's shape. Returns (reply text, usage)."""
    import anthropic
    client = anthropic.Anthropic()                  # reads ANTHROPIC_API_KEY from the environment
    response = client.messages.create(              # the instructions and the reply shape are the same for every
        model=model, max_tokens=8000,                   # question, so they are cached; only the shortlist changes
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": schema}, "effort": config.INTERPRET_EFFORT})
    if response.stop_reason in ("refusal", "max_tokens"):
        raise ValueError(f"the model stopped early ({response.stop_reason})")
    text = next(b.text for b in response.content if b.type == "text")
    u = response.usage
    return text, {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                  "cache_write_tokens": u.cache_creation_input_tokens or 0, "cache_read_tokens": u.cache_read_input_tokens or 0}


def interpret(question, short, previous=None, pending=None, call=None, model=None, declined=None, search=None,
              earlier=()):
    """Returns (reply, meta). On two failed attempts the reply is None and meta["error"] says why.

    `search` (words -> (shortlist, added)) is the app's own search. When the model replies with kind "search", the
    search runs on its words and the model is asked again with the longer shortlist, at most MAX_SEARCHES times. The
    reply's tags are read against the shortlist of the last call; meta["short"] is that shortlist, and
    meta["searches"] records each search (its words, what it added, and its seconds)."""
    model = model or config.INTERPRET_MODEL
    call = call or call_api
    system = INSTRUCTIONS.format(operations="; ".join(f"{k}: {v}" for k, v in OPERATIONS.items()),
                                 comparisons=", ".join(COMPARISONS))
    schema = REPLY_SCHEMA
    meta = {"model": model, "attempts": 0, "calls": 0, "input_tokens": 0, "output_tokens": 0, "cache_write_tokens": 0,
            "cache_read_tokens": 0, "error": None, "searches": [], "search_seconds": 0.0}
    start = time.time()
    while True:
        left = MAX_SEARCHES - len(meta["searches"]) if search else 0
        user, parts = render(short, previous, pending, question, declined, meta["searches"], left, earlier)
        meta.update(prompt_words=len((system + user).split()), system=system, user=user,
                    prompt_parts=dict(instructions=len(system.split()), **parts, schema_characters=len(json.dumps(schema))))
        reply = one_call(system, user, model, schema, short, call, meta)
        if not (reply and reply["kind"] == "search"):
            break
        if left <= 0:                               # a search asked for when none are left: nothing on the shortlist fits
            reply = dict(kind="decline", search_words=None, request=None, edit=None, options=[], chosen=[],
                         decline=dict(reason="nothing found after the searches allowed", wanted=reply["search_words"],
                                      missing="measure", closest="", about=None), unknown_tags=[])
            break
        t0 = time.time()
        short, added = search(reply["search_words"])
        seconds = round(time.time() - t0, 2)
        meta["search_seconds"] += seconds
        meta["searches"].append(dict(words=reply["search_words"], added=added, seconds=seconds))
    meta["short"] = short
    meta["search_seconds"] = round(meta["search_seconds"], 2)
    price_in, price_out = config.PRICES.get(model, (0, 0))
    meta["cost_usd"] = round((meta["input_tokens"] * price_in + meta["cache_write_tokens"] * price_in * 1.25 +
                              meta["cache_read_tokens"] * price_in * 0.1 + meta["output_tokens"] * price_out) / 1e6, 6)
    meta["seconds"] = round(time.time() - start, 2)
    return reply, meta
