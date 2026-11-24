"""Runs the steps in order for one question. The only thing the page calls.

    ask()          a typed question: shortlist, interpret (the model call), resolve, fetch, show
    summarize()    the written summary of an answer (a second model call), checked against its table
    status()       the status line's words for a step (terms.csv message rows "status ...")
    choose()       an option button: runs that option's request directly, with no model call
    take_offer()   a button offered under an answer ("Today's schools only"): runs its request, with no model call
    pick_school()  the school picker: fills in the school and runs the request, with no model call

`state` is the conversation, kept by the page: "history" (requests answered, oldest first),
"pending" (options on screen) and "picker" (a request waiting for a school). Every log line carries the
conversation's identifier and the turn number, so one conversation's turns can be read together.
"""
import sqlite3
import time
import uuid

import config
from path import fetch, interpret, resolve, show, shortlist, summary


def connect(db_path):
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def release(db, year=None):
    """The release a year's figures come from, and whether it is provisional or final: {year, release, status}."""
    try:
        row = db.execute("SELECT year, release, status FROM _releases WHERE year = COALESCE(?, (SELECT MAX(year) FROM _releases))",
                         (year,)).fetchone()
    except sqlite3.OperationalError:                    # a database built before releases were recorded
        row = None
    if row is None:
        name = db.execute("SELECT release FROM _tables ORDER BY year DESC LIMIT 1").fetchone()[0]
        row = (None, name, "provisional" if "Provisional" in name else "final")
    return dict(zip(("year", "release", "status"), row))


def turn(state):
    """The conversation's identifier (made on its first turn; a cleared conversation gets a new one) and this turn's number."""
    state.setdefault("conversation_id", uuid.uuid4().hex[:12])
    state["turns"] = state.get("turns", 0) + 1
    return dict(conversation=state["conversation_id"], turn=state["turns"])


def finish(out, state, db, log, row):
    """Turn a resolve outcome into what the page shows, update the conversation, and write the logs."""
    if out["kind"] == "many":
        pages = [finish(o, state, db, log, dict(row, part=i)) for i, o in enumerate(out["outcomes"])]
        return dict(kind="many", pages=pages)
    row["outcome"] = out["kind"]
    if out.get("log"):                                  # the model's own explanation: log only, never shown
        row["model_explanation"] = out["log"]
    if out.get("search_miss") or (out.get("plan") or {}).get("search_miss"):
        row["search_miss"] = True
    if out["kind"] == "about":                          # a question about the last decline, answered from it
        return dict(kind="decline", message=out["message"])
    if out["kind"] == "ready":
        plan = out["plan"]
        result = fetch.fetch(plan, db)
        page = show.render(plan, result, release(db))
        state.setdefault("history", []).append(out["request"])
        state["pending"], state["picker"], state["last_decline"] = None, None, None
        state["offers"] = plan.get("offers") or None    # a button under the answer, such as "Today's schools only"
        if out.get("instead"):
            page["message"] = out["instead"]
        row.update(request=out["request"], rows=len(result["rows"]))
    elif out["kind"] == "clarify":
        state["pending"] = out["options"]
        if out.get("request"):                          # kept as the previous request while the question is open
            state.setdefault("history", []).append(out["request"])
        page = dict(kind="clarify", message=out["question"], options=[o["label"] for o in out["options"]])
        row["options"] = [o["request"] for o in out["options"]]
    elif out["kind"] == "picker":
        state["picker"] = out
        state.setdefault("history", []).append(out["request"])  # kept, so "show 2023-24" edits it before a school is picked
        page = dict(kind="picker", message=f'Which school do you mean by "{out["name"]}"?',
                    candidates=[(c["id"], f"{c['name']} ({c['city']}, {c['state']})") for c in out["candidates"]])
    else:
        page = dict(kind=out["kind"], message=out["message"])
        row.update(detail=out.get("detail"), missing=out.get("missing"))
        if out["kind"] == "decline":
            if out.get("request"):                      # kept, so "show 2023-24" or "why not?" can follow
                state.setdefault("history", []).append(out["request"])
            state["last_decline"] = dict(message=out["message"], missing=out["missing"], pointer=out.get("pointer"),
                                         closest=out.get("closest"), request=out.get("request"))
            state["pending"] = None
            log.decline(dict(conversation=row.get("conversation"), turn=row.get("turn"), question=row.get("question"),
                             wanted=out.get("wanted") or out.get("request"),
                             missing=out["missing"], closest=out.get("closest"), message=out["message"]))
    return page


def status(step, db_path=None):
    """The status line's words for a step: finding, reading, searching, getting, writing."""
    db = connect(db_path or config.LOCAL_DB.as_posix())
    try:
        return fetch.say(db, f"status {step}") or step
    finally:
        db.close()


def ask(question, state, log, db_path=None, call=None, model=None, progress=None):
    """`progress(step)`, if given, is told each step as it starts, for the status line."""
    db_path = db_path or config.LOCAL_DB.as_posix()
    progress = progress or (lambda step: None)
    start = time.time()
    progress("finding")
    history = state.get("history") or []
    pending = state.get("pending") or []
    carried = history[-1:] + [o["request"] for o in pending]
    short = shortlist.shortlist(question, db_path, carried)
    declined = (state.get("last_decline") or {}).get("missing")
    short_now = {"short": short}

    def searched(words):                            # the model's own search, on the latest shortlist
        progress("searching")
        short_now["short"], added = shortlist.extend(short_now["short"], words, db_path)
        return short_now["short"], added
    progress("reading")
    reply, meta = interpret.interpret(question, short, history[-1] if history else None, pending, call=call, model=model,
                                      declined=declined, search=searched if config.AI_SEARCH else None)
    short = meta.get("short") or short
    progress("getting")
    db = connect(db_path)
    try:
        out = resolve.resolve(reply, short, state, db, db_path)
        row = dict(**turn(state), question=question, reply=reply, shortlist={t: key for t, (_, key) in short["tags"].items()},
                   raw_reply=meta.get("raw_reply"), prompt_parts=meta.get("prompt_parts"),
                   model=meta["model"], tokens_in=meta["input_tokens"], tokens_out=meta["output_tokens"],
                   cache_write=meta.get("cache_write_tokens"), cache_read=meta.get("cache_read_tokens"),
                   cost_usd=meta["cost_usd"], model_seconds=meta["seconds"], model_error=meta["error"],
                   calls=meta.get("calls"), searches=meta.get("searches"), search_seconds=meta.get("search_seconds"))
        page = finish(out, state, db, log, row)
    finally:
        db.close()
    row["seconds"] = round(time.time() - start, 2)
    log.question(row)
    page["seconds"] = row["seconds"]
    return page


def summarize(page, state, log, call=None, model=None, on_text=None):
    """The written summary of an answer, or None (no table, the call failed, or a number was not in the table: then
    it is dropped and logged). Every call is logged with its time and cost."""
    text, meta = summary.summarize(page, call=call, model=model, on_text=on_text)
    if meta.get("text") is not None or meta.get("error"):
        log.summary(dict(conversation=state.get("conversation_id"), turn=state.get("turns"), kept=meta["kept"],
                         text=meta.get("text"), missing=meta["missing"], error=meta["error"], model=meta["model"],
                         seconds=meta["seconds"], tokens_in=meta["input_tokens"], tokens_out=meta["output_tokens"],
                         cost_usd=meta["cost_usd"]))
    return text


def run_direct(request, state, log, db_path, question):
    db_path = db_path or config.LOCAL_DB.as_posix()
    start = time.time()
    db = connect(db_path)
    try:
        out = resolve.resolve_request(request, resolve.Dictionary(db, db_path), None)
        row = dict(**turn(state), question=question, reply=None, model=None)
        page = finish(out, state, db, log, row)
    finally:
        db.close()
    row["seconds"] = round(time.time() - start, 2)
    log.question(row)
    page["seconds"] = row["seconds"]
    return page


def choose(index, state, log, db_path=None):
    option = state["pending"][index]
    state["pending"] = None                             # choosing an option answers the open question
    return run_direct(option["request"], state, log, db_path, question=f"[option] {option['label']}")


def take_offer(index, state, log, db_path=None):
    """A button offered under an answer: runs its request directly, with no model call."""
    offer = state["offers"][index]
    state["offers"] = None
    return run_direct(offer["request"], state, log, db_path, question=f"[offer] {offer['label']}")


def pick_school(unitid, state, log, db_path=None):
    waiting = state["picker"]
    state["picker"] = None                              # picking a school answers the open question
    request = waiting["request"]
    request["schools"][waiting["index"]]["id"] = unitid
    return run_direct(request, state, log, db_path, question=f"[picked school] {unitid}")
