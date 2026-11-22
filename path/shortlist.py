"""Step 2, Shortlist: a text search over the dictionary and the school directory. Code only.

It decides nothing about meaning. It ranks dictionary entries by how many of the question's
words they share, weighting rare words more (BM25, the standard search-engine score), and
returns the best few of each kind for the model to choose from. Anything the previous request
or a pending clarifying question used is carried along, so a follow-up can refer back to it.
"""
import json
import math
import re
import sqlite3
from collections import Counter

from path.request import TAG_RANGES

SET_UP, NOT_SET_UP = 15, 5         # measures: the best set-up ones, then a few IPEDS collects but the app has not set up
LIMITS = {"measures": 60, "terms": 5, "schools": 10, "groups": 15, "rows": 15, "sets": 8, "outside": 3}
ROWS_PER_TABLE = 6                  # category rows searched within each shortlisted multi-row table
CUTOFF = 0.25                       # keep entries scoring at least this share of the best entry of their kind
_INDEX = {}


def words(text):
    """Lower-case words, with a light trim so 'rates' finds 'rate' and 'awarded' finds 'award'."""
    out = []
    for w in re.findall(r"[a-z0-9]+", (text or "").lower().replace("'s", "")):
        if len(w) > 4 and w.endswith("ies"):
            w = w[:-3] + "y"
        elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        elif len(w) > 5 and w.endswith("ed"):
            w = w[:-2]
        out.append(w)
    return out


def rarity(all_texts):
    """How rare each word is across every entry of every kind, so 'the' and 'in' count for little everywhere."""
    df = Counter(w for text in all_texts for w in set(words(text)))
    n = len(all_texts)
    return {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}


class BM25:
    def __init__(self, docs, idf, k1=1.2, b=0.75):
        self.docs = [Counter(words(text)) for _, text in docs]
        self.keys = [key for key, _ in docs]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lengths) / max(len(self.docs), 1)
        self.idf = idf
        self.k1, self.b = k1, b

    def search(self, text, limit):
        query = set(words(text)) & set(self.idf)
        if not query:
            return []
        scores = []
        for key, doc, length in zip(self.keys, self.docs, self.lengths):
            s = sum(self.idf[w] * doc[w] * (self.k1 + 1) / (doc[w] + self.k1 * (1 - self.b + self.b * length / self.avg))
                    for w in query if w in doc)
            if s > 0:
                scores.append((s, key))
        scores.sort(key=lambda x: -x[0])
        if not scores:
            return []
        return [key for s, key in scores[:limit] if s >= CUTOFF * scores[0][0]]


def build_index(db):
    """Read every searchable entry once. Returns {kind: (BM25 index, {key: details})}."""
    q = lambda sql: db.execute(sql).fetchall()
    titles = dict(q('SELECT "table", title FROM dict_year_meaning'))
    periods = dict(q('SELECT "table", period FROM dict_year_meaning'))
    index = {}

    measures = {}
    for t, v, title, desc, plain, syn, first, unit, period, per_school in q(
            'SELECT "table", variable, title, long_description, plain_name, synonyms, in_first_version, unit, period, '
            "rows_per_school FROM dict_measures"):
        name = plain or title
        measures[f"{t}.{v}"] = dict(id=f"{t}.{v}", name=name, table=t, unit=unit, period=period or periods.get(t),
                                    set_up=first == "yes", many_rows=(per_school or "").startswith("many"),
                                    text=" ".join([name, name, syn or "", syn or "", titles.get(t, ""), (desc or "")[:300]]))
    for (rate,) in q("SELECT DISTINCT rate FROM dict_rates WHERE rate_measure IS NULL"):
        measures[f"rate:{rate}"] = dict(id=f"rate:{rate}", name=rate, table=None, unit="computed from counts",
                                        period=None, set_up=True, many_rows=False, text=rate + " " + rate)
    terms = {}
    for term, words_, kind, reading, measure, condition, default, default_for, ask, statement in q(
            "SELECT term, words, kind, reading, measure, condition, is_default, default_for, always_ask, statement "
            "FROM dict_terms WHERE status = 'in use' AND (kind <> 'setting' OR words IS NOT NULL) ORDER BY rowid"):
        t = terms.setdefault(term, dict(term=term, always_ask="no", statement=statement, readings=[], text=term))
        if words_ and words_ not in t["text"]:
            t["text"] += " " + words_
        t["always_ask"] = "yes" if ask == "yes" else t["always_ask"]
        r = next((r for r in t["readings"] if r["reading"] == reading), None)
        if r is None:
            r = dict(reading=reading, kind=kind, is_default=default, default_for=default_for,
                     when=ask if ask == "mixed levels" else None, measures=[], condition=condition)
            t["readings"].append(r)
        if measure and measure not in r["measures"]:
            r["measures"].append(measure)
    nick = {}
    for n, unitid in q("SELECT nickname, unitid FROM dict_school_nicknames WHERE unitid IS NOT NULL"):
        nick.setdefault(int(unitid), []).append(n)
    schools = {u: dict(id=u, name=name, alias=alias, city=city, state=st, text=" ".join([name, alias or ""] + nick.get(u, [])))
               for u, name, alias, city, st in q("SELECT UNITID, INSTNM, IALIAS, CITY, STABBR FROM directory")}
    groups = {g: dict(name=g, statement=s, status=status, text=" ".join([g, w or "", s or ""]))
              for g, w, s, status in q("SELECT group_name, words, statement, status FROM group_list")}
    rows = {(t, c, code): dict(table=t, column=c, code=code, label=label, text=label)
            for t, c, code, label in q('SELECT k."table", k."column", c.code, c.label FROM row_keys k JOIN dict_category_codes c '
                                       'ON c."table" = k."table" AND UPPER(c."column") = UPPER(k."column")')}
    labels = {(t, c.upper(), str(code)): label for t, c, code, label in q('SELECT "table", "column", code, label FROM dict_category_codes')}
    def held(table, pairs):                     # {column: code} -> "label; label", in the words IPEDS uses
        return "; ".join(labels.get((table, c.upper(), str(v)), f"{c} {v}") for c, v in pairs.items())
    def parse(fixed):
        return {k.strip(): v.strip() for k, _, v in (x.partition("=") for x in (fixed or "").split(";")) if k.strip()}
    sets = {}
    defaults = {}
    for t, column, label in q('SELECT "table", "column", default_label FROM row_keys'):
        defaults.setdefault(t, []).append(f"{column} {label or 'overall total'}")
    for s, t, how, fixed in q("SELECT set_name, \"table\", stored_as, MAX(fixed) FROM breakdown_sets WHERE status <> 'failed' "
                              "GROUP BY set_name, \"table\", stored_as"):
        level = held(t, parse(fixed)) or (f"the measure's row ({'; '.join(defaults[t])} unless `row` names another)"
                                          if t in defaults else "")
        sets[(s, t)] = dict(set=s, table=t, stored_as=how, held=level, text=f"{s} {titles.get(t, '')}")
    outside = {t: dict(topic=t, what_to_say=say, pointer=p, text=f"{t} {ex or ''}")
               for t, ex, say, p in q("SELECT topic, example_wording, what_to_say, pointer FROM dict_outside_ipeds")}
    kinds = [("measures", measures), ("terms", terms), ("schools", schools), ("groups", groups),
             ("rows", rows), ("sets", sets), ("outside", outside)]
    idf = rarity([e["text"] for _, entries in kinds for e in entries.values()])
    for kind, entries in kinds:
        index[kind] = (BM25([(k, e["text"]) for k, e in entries.items()], idf), entries)
    support = {}
    for s, t, how, measure, total in q("SELECT set_name, \"table\", stored_as, measure, total FROM breakdown_sets "
                                       "WHERE status IN ('loaded', 'additive')"):
        mid = f"{t}.{measure if how == 'rows' else total}"
        if (s, t) not in support.setdefault(mid, []):
            support[mid].append((s, t))
    index["support"] = support
    index["detailed"] = {m: d for m, d in q("SELECT measure, detailed FROM detail_links")}
    index["detail_held"] = {m: held(d.partition(".")[0], json.loads(r)) for m, d, r in
                            q("SELECT measure, detailed, rows FROM detail_links WHERE status = 'loaded'")}
    index["row_keys"] = {}                       # each multi-row table's category columns and their default rows
    for t, column, label in q('SELECT "table", "column", default_label FROM row_keys'):
        index["row_keys"].setdefault(t, []).append((column, label))
    index["picker_phrases"] = q("SELECT nickname, search_phrase FROM dict_school_nicknames WHERE search_phrase IS NOT NULL")
    index["first_version"] = {}
    for m in measures.values():
        if m["table"] and m["set_up"]:
            index["first_version"].setdefault(m["table"], []).append(m["id"])
    return index


def get_index(db_path):
    if db_path not in _INDEX:
        db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        _INDEX[db_path] = build_index(db)
        db.close()
    return _INDEX[db_path]


def public(entry):
    return {k: v for k, v in entry.items() if k != "text"}


def shortlist(question, db_path, carried=()):
    """The shortlist for one question. `carried` is a list of earlier requests whose items must stay available."""
    index = get_index(db_path)
    found = {}
    for kind, limit in LIMITS.items():
        bm25, entries = index[kind]
        text = question
        if kind == "schools":                   # a nickname that only seeds the picker adds its search phrase
            low = " " + " ".join(words(question)) + " "
            text += " " + " ".join(p for n, p in index["picker_phrases"] if f" {' '.join(words(n))} " in low)
        found[kind] = {key: entries[key] for key in bm25.search(text, limit)}

    entries = index["measures"][1]
    ranked = list(found["measures"])
    keep = [k for k in ranked if entries[k]["set_up"]][:SET_UP] + [k for k in ranked if not entries[k]["set_up"]][:NOT_SET_UP]
    measures = {k: entries[k] for k in keep}
    for t in found["terms"].values():           # a matched term brings the measures of its readings
        for r in t["readings"]:
            for mid in r["measures"]:
                if mid in entries:
                    measures.setdefault(mid, entries[mid])
    for table in {r["table"] for r in found["rows"].values()} | {s["table"] for s in found["sets"].values()}:
        for mid in index["first_version"].get(table, [])[:3]:   # a matched category row or set brings its table's measures
            measures.setdefault(mid, entries[mid])
    for request in carried:                     # keep what the conversation already uses
        for mid in [m["id"] for m in request["measures"]] + [c["measure"] for c in request["conditions"]]:
            if mid in entries:
                measures.setdefault(mid, entries[mid])
        for s in request["schools"] + ([{"id": request["peers_of"]}] if request["peers_of"] else []):
            if s.get("id") in index["schools"][1]:
                found["schools"].setdefault(s["id"], index["schools"][1][s["id"]])
        for g in request["groups"]:
            if g in index["groups"][1]:
                found["groups"].setdefault(g, index["groups"][1][g])
        for m in request["measures"]:
            for pair in m["row"]:
                key = (m["id"].partition(".")[0], pair["column"].upper(), pair["code"])
                if key in index["rows"][1]:
                    found["rows"].setdefault(key, index["rows"][1][key])
        for r in request["readings"]:
            if r["term"] in index["terms"][1]:
                found["terms"].setdefault(r["term"], index["terms"][1][r["term"]])
        if request["breakdown"]:
            for key, s in index["sets"][1].items():
                if s["set"] == request["breakdown"]["set"]:
                    found["sets"].setdefault(key, s)
    for mid in list(measures):                  # a summary measure brings its detailed equivalent's table
        detailed = index["detailed"].get(mid)
        if detailed and detailed in entries:
            measures.setdefault(detailed, entries[detailed])
    tables = {m["table"] for m in measures.values()}
    bm25, rows = index["rows"]
    for table in tables & {r["table"] for r in rows.values()}:     # the best rows of each shortlisted multi-row table
        for key in [k for k in bm25.search(question, 400) if k[0] == table][:ROWS_PER_TABLE]:
            found["rows"].setdefault(key, rows[key])
    for key, s in index["sets"][1].items():     # every loaded set for a shortlisted table
        if s["table"] in tables:
            found["sets"].setdefault(key, s)
    found["measures"] = measures
    return tag({kind: [public(e) for e in found[kind].values()] for kind in LIMITS}, index)


PREFIX = {"measures": "M", "schools": "S", "groups": "G", "rows": "R", "sets": "B", "outside": "O"}


def tag(short, index):
    """Give every shortlist item a short tag (M1, S1, G1, R1, B1, T1, O1). The model answers in tags only;
    short["tags"] maps each tag back to what it stands for."""
    for kind, (_, most) in TAG_RANGES.items():          # the reply shape has a fixed number of tags of each kind
        if kind in short:
            short[kind] = short[kind][:most]
    tables = {m["table"] for m in short["measures"]}
    short["rows"] = [r for r in short["rows"] if r["table"] in tables]   # a row is only useful with its measure
    tags = {}
    for kind, prefix in PREFIX.items():
        for i, item in enumerate(short[kind], 1):
            item["tag"] = f"{prefix}{i}"
            key = {"measures": item.get("id"), "schools": item.get("id"), "groups": item.get("name"),
                   "rows": (item.get("table"), item.get("column"), item.get("code")),
                   "sets": (item.get("set"), item.get("table")), "outside": item.get("topic")}[kind]
            tags[item["tag"]] = (kind, key)
    n = 0
    for t in short["terms"]:
        t["readings"] = t["readings"][:max(0, TAG_RANGES["readings"][1] - n)]
        for r in t["readings"]:
            n += 1
            r["tag"] = f"T{n}"
            tags[r["tag"]] = ("readings", (t["term"], r["reading"]))
    short["terms"] = [t for t in short["terms"] if t["readings"]]
    by_measure = {m["id"]: m["tag"] for m in short["measures"]}
    by_set = {(s["set"], s["table"]): s["tag"] for s in short["sets"]}
    for m in short["measures"]:                 # which breakdowns each measure supports, own or through its detailed table
        own = [by_set[k] for k in index["support"].get(m["id"], []) if k in by_set]
        detailed = index["detailed"].get(m["id"])
        via = [by_set[k] for k in index["support"].get(detailed, []) if k in by_set] if detailed else []
        m["breakdowns"], m["breakdowns_via_detail"] = own, [b for b in via if b not in own]
        m["detail_held"] = index.get("detail_held", {}).get(m["id"]) if m["breakdowns_via_detail"] else None
    for r in short["rows"]:
        r["for"] = [m["tag"] for m in short["measures"] if m["table"] == r["table"]]
    for m in short["measures"]:                 # a measure's category columns, with the rows shortlisted for each
        m["categories"] = [dict(column=c, default=label or "overall total",
                                tags=[r["tag"] for r in short["rows"] if r["table"] == m["table"] and r["column"].upper() == c.upper()])
                           for c, label in index.get("row_keys", {}).get(m["table"], [])]
    for s in short["sets"]:
        s["for"] = [m["tag"] for m in short["measures"] if s["tag"] in m["breakdowns"] + m["breakdowns_via_detail"]]
    for t in short["terms"]:
        for r in t["readings"]:
            r["measure_tags"] = [by_measure[x] for x in r["measures"] if x in by_measure]
    short["tags"] = tags
    return short


def search_schools(name, db_path, limit=8):
    """Candidates for the school picker: the schools whose names best match what the user wrote."""
    bm25, entries = get_index(db_path)["schools"]
    return [public(entries[k]) for k in bm25.search(name, limit)]


def ids(short):
    """Everything on a shortlist, by kind, in the form request.used_ids() returns."""
    return {"measure": {m["id"] for m in short["measures"]},  # by real ID; tags are mapped back before this check
            "school": {s["id"] for s in short["schools"]},
            "group": {g["name"] for g in short["groups"]},
            "row": {(r["table"], r["column"].upper(), r["code"]) for r in short["rows"]},
            "set": {s["set"] for s in short["sets"]},
            "reading": {(t["term"], r["reading"]) for t in short["terms"] for r in t["readings"]}}
