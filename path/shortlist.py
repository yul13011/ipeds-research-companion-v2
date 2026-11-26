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

from path.request import TAG_RANGES, fill_years

SET_UP, NOT_SET_UP = 15, 5         # measures: the best set-up ones, then a few IPEDS collects but the app has not set up
RETIRED = 2                         # ... then, listed last, at most this many that IPEDS no longer collects
PER_TABLE = 5                       # at most this many of the set-up measures from one table, unless ...
SOFT_CAP = 2                        # ... a further one scores at least this many times the next measure from another table
NAME_WEIGHT = 3                     # a match in a measure's name or synonyms counts this many times one in its table title
                                    # or description
LIMITS = {"measures": 60, "terms": 5, "schools": 10, "groups": 15, "rows": 15, "sets": 8, "outside": 3,
          "concepts": 3, "glossary": 3}
ROWS_PER_TABLE = 6                  # category rows searched within each shortlisted multi-row table
CUTOFF = 0.25                       # keep entries scoring at least this share of the best entry of their kind
SWAP_ONLY_UP_TO, ONE_OFF_UP_TO = 4, 7   # misspellings: words of up to 4 letters may only swap two neighbouring letters;
                                        # up to 7 letters, one letter off; longer words, two letters off
_INDEX = {}


def words(text):
    """Lower-case words, with a light trim so 'rates' finds 'rate', 'awarded' finds 'award', 'offering' finds 'offer' and
    'enrollment' finds 'enroll'. The same trim is applied to the question and to the dictionary. (A standard English
    stemmer would need a package that is not installed; these hand rules are the owner-approved fallback.)"""
    out = []
    for w in re.findall(r"[a-z0-9]+", (text or "").lower().replace("'s", "")):
        if len(w) > 4 and w.endswith("ies"):
            w = w[:-3] + "y"
        elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        elif len(w) > 5 and w.endswith("ed"):
            w = w[:-2]
        elif len(w) > 5 and w.endswith("ing"):
            w = w[:-3]
        elif len(w) > 6 and w.endswith("ment"):
            w = w[:-4]
        out.append(w)
    return out


def distance(a, b, most):
    """Edits between two words (insert, delete, change, or swap two neighbouring letters), stopping above `most`."""
    if abs(len(a) - len(b)) > most:
        return most + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        if min(cur) > most:
            return most + 1
        prev2, prev = prev, cur
    return prev[-1]


def swapped(a, b):
    """True if b is a with two neighbouring letters swapped."""
    return len(a) == len(b) and sorted(a) == sorted(b) and \
        [i for i in range(len(a)) if a[i] != b[i]] in ([[i, i + 1] for i in range(len(a) - 1)])


def corrected(text, vocabulary):
    """The question with each word the index does not know matched to the index words it is a misspelling of
    (SWAP_ONLY_UP_TO, ONE_OFF_UP_TO). The question's own words are kept; corrections are added beside them. Applied
    to the question only, against the index's own (trimmed) words, so both sides are compared the same way."""
    extra = []
    for w in set(words(text)):
        if w in vocabulary.get(len(w), ()) or w.isdigit() or len(w) < 3:
            continue
        if len(w) <= SWAP_ONLY_UP_TO:                   # two letters swapped, or one letter left out ("texs")
            found = [v for v in vocabulary.get(len(w), ()) if swapped(w, v)] or \
                    [v for v in vocabulary.get(len(w) + 1, ()) if v[0] == w[0] and distance(w, v, 1) == 1]
        else:
            most = 1 if len(w) <= ONE_OFF_UP_TO else 2
            found = []
            for n in range(len(w) - most, len(w) + most + 1):
                found += [(distance(w, v, most), v) for v in vocabulary.get(n, ())
                          if v[0] == w[0] or v[:2] == w[1::-1]]
            best = min((d for d, _ in found), default=most + 1)
            found = [v for d, v in found if d == best and d <= most]
        extra += found
    return text + (" " + " ".join(sorted(set(extra))) if extra else "")


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

    def scores(self, text):
        query = set(words(text)) & set(self.idf)
        out = {}
        for key, doc, length in zip(self.keys, self.docs, self.lengths):
            s = sum(self.idf[w] * doc[w] * (self.k1 + 1) / (doc[w] + self.k1 * (1 - self.b + self.b * length / self.avg))
                    for w in query if w in doc)
            if s > 0:
                out[key] = s
        return out

    def search(self, text, limit):
        return best(self.scores(text), limit)


def best(scores, limit):
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [key for key, s in ranked[:limit] if s >= CUTOFF * ranked[0][1]] if ranked else []


class FieldBM25:
    """BM25 over two fields: a match in the main field (name and synonyms) counts NAME_WEIGHT times a match in the
    context field (the table's title and the description), so a table title helps choose the table without lifting
    every measure in it equally."""
    def __init__(self, docs, idf, main_b=0.75):
        self.main = BM25([(k, main) for k, main, _ in docs], idf, b=main_b)
        self.context = BM25([(k, context) for k, _, context in docs], idf)

    def scores(self, text):
        main, context = self.main.scores(text), self.context.scores(text)
        return {k: NAME_WEIGHT * main.get(k, 0) + context.get(k, 0) for k in main.keys() | context.keys()}

    def search(self, text, limit):
        return best(self.scores(text), limit)


class GroupSearch(FieldBM25):
    """Groups: the best by their own dictionary words and the best by their names, merged, so a curated group
    ("community colleges") and a group named in the question ("State: Texas") both reach the shortlist instead of
    one cutting the other off. A group's own words carry no penalty for being several (most groups have none)."""
    def __init__(self, docs, idf):
        super().__init__(docs, idf, main_b=0)

    def search(self, text, limit):
        main, context = self.main.scores(text), self.context.scores(text)
        keys = list(dict.fromkeys(best(main, limit // 2) + best(context, limit)))
        combined = {k: NAME_WEIGHT * main.get(k, 0) + context.get(k, 0) for k in keys}
        return sorted(keys, key=lambda k: -combined[k])[:limit]


def build_index(db):
    """Read every searchable entry once. Returns {kind: (BM25 index, {key: details})}."""
    q = lambda sql: db.execute(sql).fetchall()
    titles = dict(q('SELECT "table", title FROM dict_year_meaning'))
    latest = q("SELECT MAX(year) FROM directory")[0][0]
    periods = {t: fill_years(p, latest) for t, p in q('SELECT "table", period FROM dict_year_meaning')}
    index = {}

    measures = {}
    then = lambda y: f"{y}-{(y + 1) % 100:02d}"
    try:                                        # variables IPEDS no longer collects: the releases that had them
        spans = {m: (a, b) for m, a, b in q("SELECT measure, MIN(year), MAX(year) FROM measure_years "
                                           "GROUP BY measure") if b < latest}
    except sqlite3.OperationalError:            # a database built before measure_years existed
        spans = {}
    category = {(t, c.upper()) for t, c in q("SELECT DISTINCT \"table\", \"column\" FROM dict_category_codes WHERE in_latest = 'yes'")}
    for t, v, title, desc, plain, shown, syn, first, unit, period, per_school in q(
            'SELECT "table", variable, title, long_description, plain_name, shown_name, synonyms, in_first_version, unit, '
            "period, rows_per_school FROM dict_measures"):
        if (t, v.upper()) in category:          # a category column picks rows (shown with its table's measures),
            continue                            # never a figure, so it is not a measure on the shortlist
        name = shown or plain or title          # shown to the model: "subject: title" where titles are shared; the
        own = plain or title                    # search reads the measure's own name, so the subject adds no words
        measures[f"{t}.{v}"] = dict(id=f"{t}.{v}", name=name, table=t, unit=unit, period=fill_years(period, latest) or periods.get(t),
                                    set_up=first == "yes", many_rows=(per_school or "").startswith("many"),
                                    main=f"{own} {syn or ''}", context=f"{titles.get(t, '')} {(desc or '')[:300]}")
        measures[f"{t}.{v}"]["text"] = measures[f"{t}.{v}"]["main"] + " " + measures[f"{t}.{v}"]["context"]
        if f"{t}.{v}" in spans:                 # set up or not, a variable IPEDS no longer collects
            a, b = spans[f"{t}.{v}"]
            measures[f"{t}.{v}"].update(retired=f"{then(a)} to {then(b)}", period=None)
    for rate, syn in q("SELECT rate, MAX(synonyms) FROM dict_rates WHERE rate_measure IS NULL GROUP BY rate"):
        measures[f"rate:{rate}"] = dict(id=f"rate:{rate}", name=rate, table=None, unit="computed from counts",
                                        period=None, set_up=True, many_rows=False, main=f"{rate} {syn or ''}", context="",
                                        text=f"{rate} {syn or ''}")
    terms = {}
    try:                                        # readings used only when asked (owner decision 2026-11-25)
        only = {(t, r) for t, r in q("SELECT term, reading FROM dict_terms WHERE only_when_asked = 'yes'")}
    except sqlite3.OperationalError:            # a dictionary without the column
        only = set()
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
                     when=ask if ask == "mixed levels" else None, measures=[], condition=condition,
                     only=(term, reading) in only)
            t["readings"].append(r)
        if measure and measure not in r["measures"]:
            r["measures"].append(measure)
    nick = {}
    for n, unitid in q("SELECT nickname, unitid FROM dict_school_nicknames WHERE unitid IS NOT NULL"):
        nick.setdefault(int(unitid), []).append(n)
    schools = {u: dict(id=u, name=name, alias=alias, city=city, state=st, text=" ".join([name, alias or ""] + nick.get(u, [])))
               for u, name, alias, city, st in q("SELECT UNITID, INSTNM, IALIAS, CITY, STABBR FROM directory "
                                                 "WHERE year = (SELECT MAX(year) FROM directory)")}
    groups = {g: dict(name=g, statement=s, status=status, text=" ".join([g, w or "", s or ""]), main=w or "",
                      context=" ".join([g, s or ""]))
              for g, w, s, status in q("SELECT group_name, words, statement, status FROM group_list")}
    rows = {(t, c, code): dict(table=t, column=c, code=code, label=label, text=f"{label} {syn or ''}")
            for t, c, code, label, syn in q('SELECT k."table", k."column", c.code, c.label, c.synonyms FROM row_keys k JOIN (SELECT * FROM dict_category_codes WHERE in_latest = \'yes\') c '
                                       'ON c."table" = k."table" AND UPPER(c."column") = UPPER(k."column")')}
    labels = {(t, c.upper(), str(code)): label for t, c, code, label in q('SELECT "table", "column", code, label FROM dict_category_codes WHERE in_latest = \'yes\'')}
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
               for t, ex, say, p in q("SELECT topic, example_wording, what_to_say, pointer FROM dict_outside_ipeds "
                                      "WHERE COALESCE(checked_by_code, '') = ''")}   # years: the code decides, never the model
    kinds = [("measures", measures), ("terms", terms), ("schools", schools), ("groups", groups),
             ("rows", rows), ("sets", sets), ("outside", outside)]
    try:                                        # for "what does X mean" only: searched on their own word weights, so
        concepts = {c: dict(concept=c, explanation=e, source=s, convention=conv, text=f"{c} {w or ''}")   # they never
                    for c, w, e, s, conv in q("SELECT concept, words, explanation, source, app_convention "   # change how
                                              "FROM dict_concepts")}                    # a data question's measures rank
        glossary = {t: dict(term=t, definition=d, edition=ed, text=t)
                    for t, d, ed in q("SELECT term, definition, edition FROM dict_glossary WHERE historical IS NULL")}
    except sqlite3.OperationalError:            # a dictionary without the two tables
        concepts, glossary = {}, {}
    explain = [("concepts", concepts), ("glossary", glossary)]
    idf = rarity([e["text"] for _, entries in kinds for e in entries.values()])
    index["vocabulary"] = {}
    for w in idf:                               # the index's own words, by length, for misspelling tolerance
        index["vocabulary"].setdefault(len(w), set()).add(w)
    for kind, entries in kinds:
        index[kind] = (BM25([(k, e["text"]) for k, e in entries.items()], idf), entries)
    own_idf = rarity([e["text"] for _, entries in explain for e in entries.values()])
    for kind, entries in explain:
        index[kind] = (BM25([(k, e["text"]) for k, e in entries.items()], own_idf), entries)
    index["measures"] = (FieldBM25([(k, e["main"], e["context"]) for k, e in measures.items()], idf), measures)
    index["groups"] = (GroupSearch([(k, e["main"], e["context"]) for k, e in groups.items()], idf), groups)
    families(measures, q)
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
    try:                                        # word abbreviations in school names ("st": state or saint)
        index["abbreviations"] = {}
        for a, m in q("SELECT abbreviation, means FROM dict_word_abbreviations"):
            index["abbreviations"].setdefault(a.lower(), []).append(m)
    except sqlite3.OperationalError:            # a dictionary without the table
        index["abbreviations"] = {}
    index["picker_phrases"] = q("SELECT nickname, search_phrase FROM dict_school_nicknames WHERE search_phrase IS NOT NULL "
                                "AND kind = 'picker'")   # 'ambiguous' names are for the picker only
    index["either"] = q("SELECT nickname, CAST(unitid AS INTEGER), search_phrase FROM dict_school_nicknames "
                        "WHERE kind = 'system or school'")
    index["first_version"] = {}
    for m in measures.values():
        if m["table"] and m["set_up"]:
            index["first_version"].setdefault(m["table"], []).append(m["id"])
    return index


def get_index(db_path):
    """The search index, built once and rebuilt when the dictionary changes (a new synonym, say): the build records a
    fingerprint of the dictionary files, and a different fingerprint means a new index."""
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        try:
            stamp = tuple(db.execute("SELECT item, fingerprint FROM _dictionary_state ORDER BY item"))
        except sqlite3.OperationalError:                # a database built before the fingerprints were kept
            stamp = ()
        if _INDEX.get(db_path, (None,))[0] != stamp:
            _INDEX[db_path] = (stamp, build_index(db))
    finally:
        db.close()
    return _INDEX[db_path][1]


def public(entry):
    return {k: v for k, v in entry.items() if k != "text"}


def shortlist(question, db_path, carried=()):
    """The shortlist for one question. `carried` is a list of earlier requests whose items must stay available."""
    index = get_index(db_path)
    question = corrected(question, index["vocabulary"])
    found = {}
    for kind, limit in LIMITS.items():
        bm25, entries = index[kind]
        text = question
        if kind == "schools":                   # a nickname that only seeds the picker adds its search phrase
            low = " " + " ".join(words(question)) + " "
            text += " " + " ".join(p for n, p in index["picker_phrases"] if f" {' '.join(words(n))} " in low)
            text = expanded(text, index)
        found[kind] = {key: entries[key] for key in bm25.search(text, limit)}
    either = []
    asked = set(words(question))
    for nickname, unitid, group in index["either"]:
        if f" {' '.join(words(nickname))} " not in " " + " ".join(words(question)) + " ":
            continue
        school = index["schools"][1].get(unitid)
        if not school or group not in index["groups"][1]:
            continue
        own = set(words(school["name"])) - set(words(group)) - set(words(nickname)) - STOPWORDS
        if own and own <= asked:                # the school named in full ("unc chapel hill"): no question
            continue
        found["schools"] = {unitid: school, **found["schools"]}
        found["groups"] = {group: index["groups"][1][group], **found["groups"]}
        either.append(dict(name=nickname, school=unitid, group=group))

    entries = index["measures"][1]
    score = index["measures"][0].scores(question)
    ranked = sorted(found["measures"], key=lambda k: (-score.get(k, 0), entries[k].get("subgroup") is not None))
    per_table, set_up, held_back = Counter(), [], []
    kept, variants = {}, {}                     # near-duplicates (families): the best one, and the others' subgroups
    for k in list(ranked):
        family = entries[k].get("family")
        if family and family in kept:
            variants.setdefault(kept[family], []).append(entries[k].get("subgroup") or "total")
            ranked.remove(k)
        elif family:
            kept[family] = k
    for k in (k for k in ranked if entries[k]["set_up"] and not entries[k].get("retired")):   # the best set-up measures,
        table = entries[k]["table"] or "rate"               # at most PER_TABLE per table, unless a held-back one clearly
                                                            # outscores the next one
        if per_table[table] >= PER_TABLE:
            held_back.append(k)
            continue
        while held_back and len(set_up) < SET_UP and score[held_back[0]] >= SOFT_CAP * score[k]:
            set_up.append(held_back.pop(0))
        if len(set_up) < SET_UP:
            per_table[table] += 1
            set_up.append(k)
    set_up += held_back[:SET_UP - len(set_up)]
    current = [k for k in ranked if not entries[k]["set_up"] and not entries[k].get("retired")][:NOT_SET_UP]
    gone = [k for k in ranked if entries[k].get("retired")][:RETIRED]
    keep = set_up + current + gone              # retired variables rank below every current measure
    measures = {k: dict(entries[k], variants=variants[k]) if k in variants else entries[k] for k in keep}
    for t in found["terms"].values():           # a matched term brings the measures of its readings
        for r in t["readings"]:
            for mid in r["measures"]:
                if mid in entries:
                    measures.setdefault(mid, entries[mid])
    for table in {r["table"] for r in found["rows"].values()} | {s["table"] for s in found["sets"].values()}:
        for mid in index["first_version"].get(table, [])[:3]:   # a matched category row or set brings its table's measures
            measures.setdefault(mid, entries[mid])
    kept_m, kept_s, kept_g = {}, {}, {}         # what the conversation already uses: first, so the shortlist's
    for request in reversed(list(carried)):     # limits never drop it (newest request first)
        for mid in [m["id"] for m in request["measures"]] + [c["measure"] for c in request["conditions"]]:
            if mid in entries:
                kept_m.setdefault(mid, entries[mid])
        for s in request["schools"] + [{"id": u} for u in request.get("plus_schools") or []] + \
                ([{"id": request["peers_of"]}] if request["peers_of"] else []):
            if s.get("id") in index["schools"][1]:
                kept_s.setdefault(s["id"], index["schools"][1][s["id"]])
        for g in request["groups"]:
            if g in index["groups"][1]:
                kept_g.setdefault(g, index["groups"][1][g])
    measures = {**kept_m, **{k: v for k, v in measures.items() if k not in kept_m}}
    found["schools"] = {**kept_s, **{k: v for k, v in found["schools"].items() if k not in kept_s}}
    found["groups"] = {**kept_g, **{k: v for k, v in found["groups"].items() if k not in kept_g}}
    for request in carried:
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
    found["measures"] = dict(sorted(measures.items(), key=lambda kv: bool(kv[1].get("retired"))))  # retired last
    short = tag({kind: [public(e) for e in found[kind].values()] for kind in LIMITS}, index)
    short["either"] = either
    return short


STOPWORDS = {"the", "of", "at", "in", "and", "a", "an", "for", "university", "college"}


def families(measures, q):
    """Near-duplicate measures: in one table, names that are the same once the part labels of the person-subgroup
    breakdown sets (terms.csv "near-duplicate subgroups") and the total words ("subgroup total words") are taken out.
    Sets each measure's `family` (table, the rest of its name) and `subgroup` (the label it carries, or None)."""
    try:
        sets = [s.strip() for s in (q("SELECT condition FROM dict_terms WHERE term = 'near-duplicate subgroups'")[0][0] or "").split(";")]
        totals = [w.strip().lower() for w in (q("SELECT condition FROM dict_terms WHERE term = 'subgroup total words'")[0][0] or "").split(";")]
    except (IndexError, sqlite3.OperationalError):     # a dictionary without these settings: no grouping
        return
    tokens = lambda text: re.findall(r"[a-z0-9.]+", (text or "").lower())
    quoted = ",".join("'" + s.replace("'", "''") + "'" for s in sets)
    total_words = {w for t in totals for w in tokens(t)}
    label_words = {"non"}                               # "non-Hispanic", "Non-Pell": the label words, and their negation
    for (label,) in q(f"SELECT DISTINCT label FROM breakdown_parts WHERE set_name IN ({quoted})"):
        label_words |= set(tokens(label)) - total_words
    for m in measures.values():
        if not m.get("table"):
            continue
        name = tokens(m["name"])
        subgroup = [w for w in name if w in label_words]
        is_total = any(" " + t + " " in " " + " ".join(name) + " " for t in totals)
        if subgroup or is_total:                        # the family: the rest of the name, within the table
            m["family"] = (m["table"], " ".join(w for w in name if w not in label_words and w not in total_words))
            m["subgroup"] = " ".join(w for w in name if w in label_words) or None


PREFIX = {"measures": "M", "schools": "S", "groups": "G", "rows": "R", "sets": "B", "outside": "O", "concepts": "C",
          "glossary": "D"}


def tag(short, index):
    """Give every shortlist item a short tag (M1, S1, G1, R1, B1, T1, O1, C1, D1). The model answers in tags only;
    short["tags"] maps each tag back to what it stands for."""
    for kind, (_, most) in TAG_RANGES.items():          # the reply shape has a fixed number of tags of each kind
        if kind in short:
            short[kind] = short[kind][:most]
    tables = {m["table"] for m in short["measures"]}
    short["rows"] = [r for r in short["rows"] if r["table"] in tables]   # a row is only useful with its measure
    tags = {}
    for kind, prefix in PREFIX.items():
        for i, item in enumerate(short.setdefault(kind, []), 1):
            item["tag"] = f"{prefix}{i}"
            key = {"measures": item.get("id"), "schools": item.get("id"), "groups": item.get("name"),
                   "rows": (item.get("table"), item.get("column"), item.get("code")),
                   "sets": (item.get("set"), item.get("table")), "outside": item.get("topic"),
                   "concepts": item.get("concept"), "glossary": item.get("term")}[kind]
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


def extend(short, words, db_path):
    """The shortlist after the model's own search: what the app's search finds for the model's words comes first, then
    the shortlist it already had (trimmed at the end where the tag ranges are full), all tagged afresh. Returns the new
    shortlist and what the search added, by kind."""
    index = get_index(db_path)
    found = shortlist(words, db_path)
    keys = {"measures": lambda e: e["id"], "schools": lambda e: e["id"], "groups": lambda e: e["name"],
            "rows": lambda e: (e["table"], e["column"], e["code"]), "sets": lambda e: (e["set"], e["table"]),
            "outside": lambda e: e["topic"], "terms": lambda e: e["term"], "concepts": lambda e: e["concept"],
            "glossary": lambda e: e["term"]}
    merged, added = {}, {}
    for kind, key in keys.items():
        before = {key(e) for e in short[kind]}
        new = [e for e in found[kind] if key(e) not in before]
        added[kind] = [key(e) for e in new]
        merged[kind] = [{k: v for k, v in e.items() if k != "tag"} for e in new + short[kind]]
    for t in merged["terms"]:
        t["readings"] = [{k: v for k, v in r.items() if k != "tag"} for r in t["readings"]]
    merged = tag(merged, index)
    merged["either"] = short.get("either", [])        # only the user's own words ask "the system or one school"
    return merged, {k: v for k, v in added.items() if v}


def expanded(text, index):
    """School names with their abbreviated words written out (word_abbreviations.csv), every meaning added beside
    the word itself: "wayne st" also searches "wayne state saint"; the picker or the model chooses."""
    extra = [m for w in re.findall(r"[a-z]+", (text or "").lower()) for m in index["abbreviations"].get(w, [])]
    return text + (" " + " ".join(extra) if extra else "")


def search_schools(name, db_path, limit=8):
    """Candidates for the school picker: the schools whose names best match what the user wrote, abbreviated words
    written out."""
    index = get_index(db_path)
    bm25, entries = index["schools"]
    return [public(entries[k]) for k in bm25.search(expanded(name, index), limit)]


def ids(short):
    """Everything on a shortlist, by kind, in the form request.used_ids() returns."""
    return {"measure": {m["id"] for m in short["measures"]},  # by real ID; tags are mapped back before this check
            "school": {s["id"] for s in short["schools"]},
            "group": {g["name"] for g in short["groups"]},
            "row": {(r["table"], r["column"].upper(), r["code"]) for r in short["rows"]},
            "set": {s["set"] for s in short["sets"]},
            "reading": {(t["term"], r["reading"]) for t in short["terms"] for r in t["readings"]},
            "explanation": {("concepts", c["concept"]) for c in short.get("concepts", [])} |
                           {("glossary", g["term"]) for g in short.get("glossary", [])}}
