"""Step 7, Summary (Part 5e): two or three neutral sentences about a result, written by a second model call.

The model is given only the result: what the table shows ("Interpreted as"), its columns and rows, and its notes. It
never sees the question path, the database or the dictionary. Code then checks every number in its sentences against
the result (numbers_check, a general check of any written text against any result). If a number is not there, the
summary is dropped and logged, and the table stands alone.

The call itself is passed in (`call`), so tests use saved replies and never reach the API.
"""
import re
import time

import config

INSTRUCTIONS = """You write a short, neutral summary of a table of U.S. college data (IPEDS) for the person who asked.
Write two or three plain sentences. Use only numbers that appear in the table or its notes, written as they appear
(rounding is allowed). Do not calculate new numbers, such as differences, totals or averages that the table does not
show. Do not interpret, explain causes, judge, or add anything the table and its notes do not say. No headings or lists."""

NUMBER = re.compile(r"(?<![\w.])-?\$?\d[\d,]*(?:\.\d+)?%?(?:\s*(?:million|billion))?", re.IGNORECASE)


def result_text(page):
    """The result as plain text for the model: what it shows, the table, and its notes."""
    t = page.get("table") or {}
    lines = [f"WHAT THE TABLE SHOWS: {page.get('interpreted') or ''}", "TABLE:", " | ".join(map(str, t.get("columns") or []))]
    lines += [" | ".join(map(str, row)) for row in t.get("rows") or []]
    if page.get("notes"):
        lines += ["NOTES:"] + [str(n) for n in page["notes"]]
    return "\n".join(lines)


def value_of(token):
    """A number as written ("$22,408", "12.5%", "1.2 million") -> (value, decimals written)."""
    text = token.lower().replace("$", "").replace(",", "").replace("%", "").strip()
    scale = 1
    for word, factor in (("million", 1e6), ("billion", 1e9)):
        if text.endswith(word):
            text, scale = text[:-len(word)].strip(), factor
    decimals = len(text.partition(".")[2])
    return float(text) * scale, decimals, scale


def numbers_check(text, sources):
    """The numbers in `text` that appear in none of `sources` (strings: table cells, notes), allowing for rounding,
    thousands separators, dollar and percent signs, and "million" or "billion". An empty list means every number is
    there. General: it checks any written text against any result."""
    known = []
    for s in sources:
        for token in NUMBER.findall(str(s)):
            known.append(value_of(token)[0])
    missing = []
    for token in NUMBER.findall(text or ""):
        value, decimals, scale = value_of(token)
        tolerance = 0.5 * 10 ** -decimals * scale + 1e-9      # what rounding to the digits written allows
        if not any(abs(value - k) <= tolerance for k in known):
            missing.append(token.strip())
    return missing


def sources_of(page):
    """Everything the summary may draw numbers from: the table's cells and headings, the notes, "Interpreted as"."""
    t = page.get("table") or {}
    return [page.get("interpreted") or ""] + list(map(str, t.get("columns") or [])) + \
        [str(c) for row in t.get("rows") or [] for c in row] + list(map(str, page.get("notes") or []))


def call_api(system, user, model, on_text=None):
    """One plain-text call, streamed when `on_text` is given. Returns (text, usage)."""
    import anthropic
    client = anthropic.Anthropic(timeout=config.CALL_SECONDS, max_retries=0)
    kwargs = dict(model=model, max_tokens=400, system=system, messages=[{"role": "user", "content": user}])
    if on_text:
        with client.messages.stream(**kwargs) as stream:
            for piece in stream.text_stream:
                on_text(piece)
            message = stream.get_final_message()
    else:
        message = client.messages.create(**kwargs)
    text = "".join(b.text for b in message.content if b.type == "text")
    u = message.usage
    return text, {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens}


def summarize(page, call=None, model=None, on_text=None):
    """(summary or None, meta). None when the page has no table to summarise, the call failed, or a number in the
    summary is not in the result (meta["missing"] lists them)."""
    model = model or config.SUMMARY_MODEL
    meta = dict(model=model, seconds=0.0, input_tokens=0, output_tokens=0, cost_usd=0.0, missing=[], error=None, kept=False)
    if page.get("kind") != "answer" or not (page.get("table") or {}).get("rows") or             page.get("operation") in ("define", "data_exists"):   # no summary for "what data exists" or a definition
        return None, meta                               # (owner, 2026-11-24); declines and questions have no table
    start = time.time()
    try:
        text, usage = (call or call_api)(INSTRUCTIONS, result_text(page), model, on_text)
    except Exception as e:                              # a failed summary never stops the answer
        meta.update(error=f"{type(e).__name__}: {e}", seconds=round(time.time() - start, 2))
        return None, meta
    meta.update(seconds=round(time.time() - start, 2), text=text, **usage)
    price_in, price_out = config.PRICES.get(model, (0, 0))
    meta["cost_usd"] = round((usage["input_tokens"] * price_in + usage["output_tokens"] * price_out) / 1e6, 6)
    meta["missing"] = numbers_check(text, sources_of(page))
    meta["kept"] = not meta["missing"] and bool(text.strip())   # an empty reply is no summary
    return (text.strip() if meta["kept"] else None), meta
