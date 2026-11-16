"""Step 3, Interpret: the one model call.

The model is shown the shortlist for this question, the previous request, any pending
clarifying options, and the question. It returns one structured reply (request.REPLY_SCHEMA),
enforced by the API's structured output. It never writes SQL and never produces a number.

The call itself is passed in (`call`), so tests use saved replies and never reach the API.
"""
import json
import time

import config
from path.request import COMPARISONS, OPERATIONS, REPLY_SCHEMA

INSTRUCTIONS = """You read questions about U.S. colleges for an app that answers them from IPEDS data.
You do not answer the question. You turn it into one structured reply that code will run.

Rules:
- Use only IDs and names that appear in the SHORTLIST below. Never invent a measure, school, group,
  category row or breakdown set. If what the question needs is not there, decline and say what is missing.
- Never write SQL and never state a number from the data.
- Choose kind:
  request: a complete request for a new question.
  edit: a follow-up that changes the PREVIOUS REQUEST ("add Northeastern", "now for Texas", "rank them",
        "break that down by gender", "go back"). List each changed field with add, remove, replace or back,
        and put only the new values in `values`. Leave everything else to the previous request.
  options: the question has two or three reasonable readings. Give each as a complete request with a short label.
  choose: the user is answering the PENDING OPTIONS ("the first one", "B", "both"). Give their 0-based numbers.
  decline: nothing in the shortlist can answer it, or it asks for something IPEDS does not hold (see OUTSIDE IPEDS),
        individual records, a measure applied to the wrong population, or it is not a question about data.
        Say plainly what is missing and name the closest thing the app can do.
- Operations: {operations}
- measures: pick the measure that matches. For a multi-row measure, name a category row only when the user asks
  for one (for example transfer-in students); otherwise leave `row` empty and the app uses the overall total.
- TERMS: a term lists its readings. If the user said which reading they mean, record it in `readings`.
  If the term says "always ask" and the user did not say, return options, one per reading.
  Otherwise use the reading marked default.
- schools: write each name as the user wrote it, with its ID if the shortlist clearly has that school,
  or null if it does not or several schools could be meant.
- groups: use group names exactly as listed. A school must be in every group named.
- "its peers" or "peer institutions": set peers_of to the school's ID.
- conditions: comparison is one of {comparisons}; value is a number or a category code, written as text.
- year: copy the year as the user stated it, or null. Set kind only if the user said (fall, fiscal year, ...).
- define and data_exists: put the matching measure IDs in measures, or the OUTSIDE IPEDS topic in topic.
  If nothing matches, put the user's topic in plain words in topic.
"""


def render(short, previous, pending, question):
    """The shortlist and conversation as plain text for the model."""
    lines = ["SHORTLIST", "Measures (id | name | period | unit):"]
    for m in short["measures"]:
        flag = "" if m["set_up"] else " | not set up in this app yet"
        lines.append(f"  {m['id']} | {m['name']} | {m['period'] or ''} | {m['unit'] or ''}{flag}")
    lines.append("Terms:")
    for t in short["terms"]:
        lines.append(f"  {t['term']}" + (" (always ask)" if t["always_ask"] == "yes" else ""))
        for r in t["readings"]:
            extra = " [default" + (f" for {r['default_for']}" if r["default_for"] else "") + "]" if r["is_default"] == "yes" else ""
            when = " [offered when a group mixes levels]" if r["when"] else ""
            lines.append(f"    - {r['reading']}: {', '.join(r['measures']) or r['condition'] or ''}{extra}{when}")
    lines.append("Schools (id | name | city, state | also called):")
    lines += [f"  {s['id']} | {s['name']} | {s['city']}, {s['state']} | {s['alias'] or ''}" for s in short["schools"]]
    lines.append("Groups (name | definition):")
    lines += [f"  {g['name']} | {(g['statement'] or '')[:120]}" + (" | not available" if g["status"] == "decline" else "")
              for g in short["groups"]]
    lines.append("Category rows (table.column = code | label):")
    lines += [f"  {r['table']}.{r['column']} = {r['code']} | {r['label']}" for r in short["rows"]]
    lines.append("Breakdown sets (set | table):")
    lines += [f"  {s['set']} | {s['table']}" for s in short["sets"]]
    lines.append("Outside IPEDS (topic):")
    lines += [f"  {o['topic']}" for o in short["outside"]]
    lines.append("")
    lines.append("PREVIOUS REQUEST: " + (json.dumps(previous) if previous else "none"))
    if pending:
        lines.append("PENDING OPTIONS:")
        lines += [f"  {i}: {o['label']}" for i, o in enumerate(pending)]
    lines.append("")
    lines.append("QUESTION: " + question)
    return "\n".join(lines)


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


def call_api(system, user, model):
    """One call to the Anthropic API with the reply held to the request shape. Returns (reply text, usage)."""
    import anthropic
    client = anthropic.Anthropic()                  # reads ANTHROPIC_API_KEY from the environment
    response = client.messages.create(
        model=model, max_tokens=8000, system=system, messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": REPLY_SCHEMA}, "effort": config.INTERPRET_EFFORT})
    if response.stop_reason in ("refusal", "max_tokens"):
        raise ValueError(f"the model stopped early ({response.stop_reason})")
    text = next(b.text for b in response.content if b.type == "text")
    return text, {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}


def interpret(question, short, previous=None, pending=None, call=None, model=None):
    """Returns (reply, meta). On two failed attempts the reply is None and meta["error"] says why."""
    model = model or config.INTERPRET_MODEL
    call = call or call_api
    system = INSTRUCTIONS.format(operations="; ".join(f"{k}: {v}" for k, v in OPERATIONS.items()),
                                 comparisons=", ".join(COMPARISONS))
    user = render(short, previous, pending, question)
    meta = {"model": model, "attempts": 0, "input_tokens": 0, "output_tokens": 0, "error": None,
            "prompt_words": len((system + user).split())}
    start = time.time()
    for _ in range(2):                              # one retry, then a plain failure
        meta["attempts"] += 1
        try:
            text, usage = call(system, user, model)
            meta["input_tokens"] += usage["input_tokens"]
            meta["output_tokens"] += usage["output_tokens"]
            reply = json.loads(text)
            problem = check(reply)
            if problem:
                raise ValueError(problem)
            meta["error"] = None
            break
        except Exception as e:                      # any failure is recorded and retried once
            reply, meta["error"] = None, f"{type(e).__name__}: {e}"
    price_in, price_out = config.PRICES.get(model, (0, 0))
    meta["cost_usd"] = round((meta["input_tokens"] * price_in + meta["output_tokens"] * price_out) / 1e6, 6)
    meta["seconds"] = round(time.time() - start, 2)
    return reply, meta
