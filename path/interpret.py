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
  T1 term reading, O1 outside-IPEDS topic). Answer with tags only. If what the question needs has no tag,
  decline and say what is missing.
- Never write SQL and never state a number from the data.
- Leave a field null, or an empty list, when it does not apply. Fill only the parts the kind you choose needs.
- Choose kind, and fill `requests` to match:
  request: one complete request for a new question (its label can be empty).
  edit: a follow-up that changes the PREVIOUS REQUEST ("add Northeastern", "now for Texas", "rank them",
        "break that down by gender", "go back"). List each changed field in `changes` with add, remove, replace
        or back, and put only the new values in one item of `requests`. Leave everything else to the previous request.
  options: the question has two or three reasonable readings. Give each as a complete request with a short label.
  choose: the user is answering the PENDING OPTIONS ("the first one", "B", "both"). Give their 0-based numbers.
  decline: nothing in the shortlist can answer it, or it asks for something IPEDS does not hold (see OUTSIDE IPEDS),
        individual records, a measure applied to the wrong population, or it is not a question about data.
        Say plainly what is missing and name the closest thing the app can do.
- Operations: {operations}
- measures: pick the measure that matches. For a multi-row measure, name a category row (R tag listed for that
  measure) only when the user asks for one, such as transfer-in students; otherwise leave `row` empty and the app
  uses the overall total.
- breakdown: use a breakdown set (B tag) listed for the measure you chose. A set listed "through the detailed table"
  also works for that measure.
- TERMS: a term lists its readings, each with a T tag. If the user said which reading they mean, put its tag in `readings`.
  If the term says "always ask" and the user did not say, return options, one per reading.
  Otherwise use the reading marked default.
- schools: write each name as the user wrote it, with its S tag if the shortlist clearly has that school,
  or null if it does not or several schools could be meant.
- groups: G tags. A school must be in every group named.
- "its peers" or "peer institutions": set peers_of to the school's S tag.
- conditions: comparison is one of {comparisons}; value is a number or a category code, written as text.
- year: copy the year as the user stated it, or leave it empty. Set kind only if the user said (fall, fiscal year, ...).
- define and data_exists: put the matching measures in measures, or the outside-IPEDS topic (O tag) in outside.
  If nothing matches, put the user's topic in plain words in topic.
"""


def render(short, previous, pending, question):
    """The shortlist and conversation as plain text for the model, in tags. Returns (text, words per part)."""
    parts = {}
    def section(name, lines):
        parts[name] = lines
    rows = []
    for m in short["measures"]:
        flag = " | not set up in this app yet" if not m["set_up"] else ""
        b = (f" | breakdowns: {', '.join(m['breakdowns'])}" if m["breakdowns"] else "") + \
            (f" | breakdowns through the detailed table: {', '.join(m['breakdowns_via_detail'])}" if m["breakdowns_via_detail"] else "")
        rows.append(f"  {m['tag']} | {m['name']} | {m['period'] or ''} | {m['unit'] or ''}{b}{flag}")
    section("measures", ["Measures (tag | name | period | unit):"] + rows)
    rows = []
    for t in short["terms"]:
        rows.append(f"  {t['term']}" + (" (always ask)" if t["always_ask"] == "yes" else ""))
        for r in t["readings"]:
            extra = " | default" + (f" for {r['default_for']}" if r["default_for"] else "") if r["is_default"] == "yes" else ""
            when = " | offered when a group mixes levels" if r["when"] else ""
            uses = f" | {', '.join(r['measure_tags'])}" if r["measure_tags"] else ""
            rows.append(f"    {r['tag']} | {r['reading']}{uses}{extra}{when}")
    section("terms", ["Terms (tag | reading):"] + rows)
    section("schools", ["Schools (tag | name | city, state | also called):"] +
            [f"  {s['tag']} | {s['name']} | {s['city']}, {s['state']} | {s['alias'] or ''}" for s in short["schools"]])
    section("groups", ["Groups (tag | name | definition):"] +
            [f"  {g['tag']} | {g['name']} | {(g['statement'] or '')[:120]}" + (" | not available" if g["status"] == "decline" else "")
             for g in short["groups"]])
    section("rows", ["Category rows (tag | label | for measures):"] +
            [f"  {r['tag']} | {r['label']} | {', '.join(r['for'])}" for r in short["rows"]])
    section("sets", ["Breakdown sets (tag | set | for measures):"] +
            [f"  {s['tag']} | {s['set']} | {', '.join(s['for'])}" for s in short["sets"]])
    section("outside", ["Outside IPEDS (tag | topic):"] + [f"  {o['tag']} | {o['topic']}" for o in short["outside"]])
    convo = ["PREVIOUS REQUEST: " + (json.dumps(to_wire(previous, short["tags"])) if previous else "none")]
    if pending:
        convo += ["PENDING OPTIONS:"] + [f"  {i}: {o['label']}" for i, o in enumerate(pending)]
    section("conversation", convo)
    section("question", ["QUESTION: " + question])
    order = ["measures", "terms", "schools", "groups", "rows", "sets", "outside", "conversation", "question"]
    text = "\n".join(["SHORTLIST"] + [line for name in order for line in parts[name]])
    return text, {name: len(" ".join(parts[name]).split()) for name in order}


def check(reply):
    """The parts a reply of each kind must carry. Returns a problem, or None."""
    needs = {"request": "request", "edit": "edit", "decline": "decline"}
    if reply["kind"] in needs and not reply.get(needs[reply["kind"]]):
        return f"a reply of kind {reply['kind']} came without its {needs[reply['kind']]}"
    if reply["kind"] == "options" and len(reply.get("options") or []) < 2:
        return "a reply of kind options came with fewer than two options"
    if reply["kind"] == "choose" and not reply.get("chosen"):
        return "a reply of kind choose named no option"
    return None


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


def interpret(question, short, previous=None, pending=None, call=None, model=None):
    """Returns (reply, meta). On two failed attempts the reply is None and meta["error"] says why."""
    model = model or config.INTERPRET_MODEL
    call = call or call_api
    system = INSTRUCTIONS.format(operations="; ".join(f"{k}: {v}" for k, v in OPERATIONS.items()),
                                 comparisons=", ".join(COMPARISONS))
    user, parts = render(short, previous, pending, question)
    schema = REPLY_SCHEMA
    meta = {"model": model, "attempts": 0, "input_tokens": 0, "output_tokens": 0, "cache_write_tokens": 0,
            "cache_read_tokens": 0, "error": None,
            "prompt_words": len((system + user).split()),
            "prompt_parts": dict(instructions=len(system.split()), **parts, schema_characters=len(json.dumps(schema))),
            "system": system, "user": user}
    start = time.time()
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
            break
        except Exception as e:                      # any failure is recorded and retried once
            reply, meta["error"] = None, f"{type(e).__name__}: {e}"
    price_in, price_out = config.PRICES.get(model, (0, 0))
    meta["cost_usd"] = round((meta["input_tokens"] * price_in + meta["cache_write_tokens"] * price_in * 1.25 +
                              meta["cache_read_tokens"] * price_in * 0.1 + meta["output_tokens"] * price_out) / 1e6, 6)
    meta["seconds"] = round(time.time() - start, 2)
    return reply, meta
