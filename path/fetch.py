"""Step 5, Fetch: one query routine per operation, built by code from the resolved plan.

Every figure comes from here. Missing values stay missing: they are never counted as zero, and
each table says how many schools had no value. Group rates and averages add up the counts
across schools first and divide once (rates.csv), never averaging school figures.
"""
import sys
from collections import defaultdict


class Data:
    def __init__(self, db, year=None):                 # the latest year, unless a trend asks for another
        self.db = db
        self.year = year or db.execute("SELECT MAX(year) FROM directory").fetchone()[0]

    def q(self, sql, *args):
        return self.db.execute(sql, args).fetchall()

    def column(self, table, column, rows=None, extra=None, units=None):
        """{UNITID: value} for one column, on the row the plan names. `units` limits it to a few schools."""
        where = ["year = ?"] + [f'CAST("{c}" AS TEXT) = ?' for c in rows or {}] + [f'CAST("{c}" AS TEXT) = ?' for c in extra or {}]
        args = [self.year] + list((rows or {}).values()) + list((extra or {}).values())
        if units:
            where.append(f"UNITID IN ({','.join('?' * len(units))})")
            args += list(units)
        return dict(self.q(f'SELECT UNITID, "{column}" FROM "{table}" WHERE {" AND ".join(where)}', *args))

    def label(self, table, column, code):
        """A code's IPEDS label; where the codebook gives none, the code itself (and the answer says so)."""
        if isinstance(code, float) and code.is_integer():   # stored as 1.0, labelled as 1
            code = int(code)
        row = self.q('SELECT label FROM value_labels WHERE local_table=? AND "column"=? AND code=? ORDER BY year = ? DESC, year DESC',
                     table, column.upper(), str(code), self.year)
        if not row:
            self.unlabelled = True
        return row[0][0] if row else code

    def reason(self, table, column, unitid):
        row = self.q('SELECT reason FROM _missing_reasons WHERE local_table=? AND "column"=? AND unitid=? AND year=?',
                     table, column, unitid, self.year)
        return row[0][0] if row else "No value reported"

    def names(self, ids):
        return {u: (n, s) for u, n, s in self.q(f"SELECT UNITID, INSTNM, STABBR FROM directory WHERE year = ? AND "
                                                  f"UNITID IN ({','.join('?' * len(ids))})", self.year, *ids)} if ids else {}


class _Blank(dict):
    def __missing__(self, key):
        return ""


def say(db, key, **fields):
    """A message to the user, from the "message" rows of terms.csv."""
    row = db.execute("SELECT statement FROM dict_terms WHERE term = 'message' AND reading = ?", (key,)).fetchone()
    return ((row[0] if row else "") or "").format_map(_Blank(fields)).strip()


def cell(value, unit):
    """A figure with its unit, so show can format it. Missing stays None."""
    return None if value is None else (value, unit or "count")


def unit_of(m):
    """The unit a figure is shown in. A rate computed from counts takes the unit of its ready-made measure."""
    return {"computed from counts": "average", "dollars": "average"}.get(m["unit"], m["unit"])


def count_column(data, ref, category, code):
    table, column = ref.split(".")
    return data.column(table, column, extra={category: code} if category else None)


def school_values(m, data, units=None):
    """{UNITID: value} for a measure. A computed rate divides each school's own counts. A measure by kind of
    school takes, for each school, the part that applies to it."""
    if m.get("parts"):
        out = {}
        for p in m["parts"]:
            out.update({u: v for u, v in school_values(p, data, units).items() if u in p["members"]})
        return out
    if m["column"]:
        return data.column(m["table"], m["column"], m["rows"], units=units)
    out = {}
    for r in m["rates"]:
        num = count_column(data, r["numerator"], r["category"], r["numerator_code"])
        den = count_column(data, r["denominator"], r["category"], r["denominator_code"])
        for u in num.keys() & den.keys():
            if (r["members"] is None or u in r["members"]) and num[u] is not None and den[u]:
                out[u] = num[u] if r["method"] == "weighted average" else num[u] / den[u] * (100 if m["unit"] == "percent" else 1)
    return out


def school_counts(m, data):
    """{UNITID: (numerator, denominator, rate row)} for the counts behind a rate, one rate row per school."""
    out = {}
    for r in m["rates"]:
        num = count_column(data, r["numerator"], r["category"], r["numerator_code"])
        den = count_column(data, r["denominator"], r["category"], r["denominator_code"])
        for u in num.keys() | den.keys():
            if r["members"] is None or u in r["members"]:
                out.setdefault(u, (num.get(u), den.get(u), r))
    return out


def group_figure(m, members, data):
    """One figure for a set of schools. Returns a list of rows: label, value, reporting, missing, numerator, denominator."""
    if m.get("method") == "sum":
        values = data.column(m["table"], m["column"], m["rows"])
        got = [values[u] for u in members if values.get(u) is not None]
        return [dict(label=m["name"], value=sum(got) if got else None, reporting=len(got), missing=len(members) - len(got),
                     numerator=None, denominator=None, form=m["form"])]
    out = []
    for r in m["rates"]:
        scope = members if r["members"] is None else members & r["members"]
        if not scope:
            continue
        num = count_column(data, r["numerator"], r["category"], r["numerator_code"])
        den = count_column(data, r["denominator"], r["category"], r["denominator_code"])
        both = [u for u in scope if num.get(u) is not None and den.get(u)]
        top = sum(num[u] * den[u] if r["method"] == "weighted average" else num[u] for u in both)
        bottom = sum(den[u] for u in both)
        scale = 100 if unit_of(m) == "percent" else 1    # school figures are stored as percents; counts give a share
        out.append(dict(label=m["name"] + (f" ({r['applies_to']})" if len(m["rates"]) > 1 and r["applies_to"] else ""),
                        value=scale * top / bottom if bottom else None, reporting=len(both), missing=len(scope) - len(both),
                        numerator=top, denominator=bottom, form=r["form"]))
    return out


def shown(m, value, data):
    """A value as the user sees it: a coded answer becomes its label."""
    if value is not None and m["unit"] == "coded":
        return data.label(m["table"], m["column"], value)
    return cell(value, unit_of(m))


def additive_total(measures, data):
    """If the measures are the parts of a set marked 'sum of parts', the name of that set."""
    if len(measures) < 2 or not all(m["column"] for m in measures):   # one measure is its own total
        return None
    tables = {m["table"] for m in measures}
    row = data.q("SELECT set_name FROM breakdown_sets WHERE status='additive' AND \"table\"=?", next(iter(tables)))
    if len(tables) == 1 and row:
        parts = {p for (p,) in data.q("SELECT part FROM breakdown_parts WHERE set_name=? AND \"table\"=?", row[0][0], next(iter(tables)))}
        if {m["column"] for m in measures} <= parts:
            return row[0][0]
    return None


def campus_notes(plan, data, result, shown):
    """For each school shown, the note that IPEDS reports its data together with a related campus, where it does."""
    templates = plan.get("campus_notes") or {}
    for flag_column, parent_column in {tuple(m["parent_child"]) for m in plan["measures"] if m.get("parent_child")}:
        for u in shown:
            row = data.q(f'SELECT "{flag_column}", "{parent_column}" FROM FLAGS WHERE UNITID=? AND year=?', u, data.year)
            if not row or row[0][0] not in (1, 2):
                continue
            flag, parent = row[0]
            if flag == 2:
                campuses = data.names([parent]).get(parent, (str(parent),))[0]
            else:
                children = [c for (c,) in data.q(f'SELECT UNITID FROM FLAGS WHERE "{parent_column}"=? AND "{flag_column}"=2 '
                                                 'AND year=?', u, data.year)]
                campuses = ", ".join(sorted(n for n, _ in data.names(children).values()))
            note = templates.get(str(flag), "").format(school=data.names([u]).get(u, (str(u),))[0], campuses=campuses)
            if note and note not in result["warnings"]:
                result["warnings"].append(note)


def shown_schools(plan, result):
    """The schools an answer names: the schools asked about, or the schools listed in its table."""
    if plan["operation"] in ("rank", "list"):
        return result.get("listed", [])
    return [s["id"] for s in plan["schools"]]


def fetch(plan, db):
    result = dict(columns=[], rows=[], counts_columns=[], counts=[], notes=[], missing=[], warnings=[])
    if plan.get("trend"):                               # chosen years, or one earlier year: path/trend.py
        from path import trend
        trend.answer(plan, db, result, sys.modules[__name__])
        return result
    data = Data(db)
    OPS[plan["operation"]](plan, data, result)
    campus_notes(plan, data, result, shown_schools(plan, result))
    if getattr(data, "unlabelled", False):              # a coded answer the codebook gives no label for
        result["notes"].append(say(db, "no label"))
    return result


def schools(plan, data, result):
    ids = [s["id"] for s in plan["schools"]]
    columns, merged = [], {}                            # measures with the same heading share one column
    for m in plan["measures"]:                          # a measure asked for at several category rows keeps one column each
        key = m.get("shown_as") or m["name"]
        if key in merged and merged[key][0]["rows"] != m["rows"]:
            key += "".join(f", {x}" for x in m.get("row_labels", []))
        if key not in merged:
            merged[key] = []
            columns.append(key)
        merged[key].append(m)
    total = additive_total(plan["measures"], data)
    result["columns"] = ["School"] + columns + (["Total"] if total else [])
    values = {id(m): school_values(m, data, ids) for m in plan["measures"]}
    counts = {id(m): school_counts(m, data) for m in plan["measures"] if m["rates"]}
    for s in plan["schools"]:
        row = [s["name"]]
        for key in columns:
            got = next((values[id(m)].get(s["id"]) for m in merged[key] if values[id(m)].get(s["id"]) is not None), None)
            row.append(shown(merged[key][0], got, data))
            if got is None:
                m = merged[key][0]
                result["missing"].append(f"{s['name']}, {key}: {data.reason(m['table'], m['column'], s['id']) if m['column'] else 'No value'}")
        if total:
            parts = [v[0] for v in row[1:] if v is not None]
            row.append(cell(sum(parts) if parts else None, "count"))
        result["rows"].append(row)
    result["counts_columns"] = ["School", "Measure", "Numerator", "Denominator", "How combined"]
    for m in plan["measures"]:
        for s in plan["schools"]:
            if id(m) in counts and s["id"] in counts[id(m)]:
                num, den, r = counts[id(m)][s["id"]]
                result["counts"].append([s["name"], m["name"], cell(num, "count"), cell(den, "count"),
                                         f"{r['numerator']} / {r['denominator']}"])


def rank(plan, data, result):
    m = plan["measures"][0]
    members = plan["members"]
    values = school_values(m, data)
    counts = school_counts(m, data) if m["rates"] else {}
    kept, no_value, small = [], 0, 0
    for u in members:
        v = values.get(u)
        if v is None or v <= 0:
            no_value += 1
            continue
        if plan["guard"] and (counts.get(u, (None, None))[1] or 0) < plan["guard"]:
            small += 1
            continue
        kept.append((v, u))
    kept.sort(key=lambda x: -x[0] if plan["sort"]["order"] == "highest" else x[0])
    top = kept[:plan["sort"]["limit"]]
    names = data.names([u for _, u in top])
    result["listed"] = [u for _, u in top]
    result["columns"] = ["Rank", "School", "State", m["name"]] + (["Denominator"] if plan["guard"] else [])
    for i, (v, u) in enumerate(top, 1):
        result["rows"].append([i, names[u][0], names[u][1], cell(v, unit_of(m))] + ([cell(counts[u][1], "count")] if plan["guard"] else []))
    if not kept and plan.get("empty_ranking"):
        result["notes"].append(plan["empty_ranking"].format(scope=plan["scope"], measure=m["name"]))
    result["notes"].append(f"{len(kept):,} of {len(members):,} schools ranked; {no_value:,} left out with no value or a value of "
                           "zero or below" + (f"; {small:,} left out with fewer than {plan['guard']} in the denominator" if plan["guard"] else "") + ".")


def passes(value, comparison, target):
    if value is None:
        return False
    try:
        value, target = float(value), float(target)
    except (TypeError, ValueError):
        value, target = str(value), str(target)
    return {">": value > target, ">=": value >= target, "<": value < target, "<=": value <= target,
            "=": value == target, "!=": value != target}[comparison]


def filtered(plan, data):
    members = set(plan["members"])
    for c in plan["conditions"]:
        values = school_values(c["measure"], data)
        members = {u for u in members if passes(values.get(u), c["comparison"], c["value"])}
    return members


def listing(plan, data, result):
    members = filtered(plan, data)
    shown_measures = list({m["id"]: m for m in [c["measure"] for c in plan["conditions"]] + plan["measures"]}.values())
    values = [school_values(m, data) for m in shown_measures]
    names = data.names(sorted(members))
    result["listed"] = sorted(members)
    by_kind = next((m for m in shown_measures if m.get("parts")), None)   # one measure per kind of school: group by it
    part_of = {}
    if by_kind:
        for i, p in enumerate(by_kind["parts"]):
            part_of.update({u: (i, p) for u in members if u in p["members"] and u not in part_of})
    result["columns"] = (["Kind of school", "Measure"] if by_kind else []) + ["School", "State"] + [m["name"] for m in shown_measures]
    order = lambda u: (part_of.get(u, (len(part_of) + 1, None))[0], names[u][0])
    for u in sorted(members, key=order):
        kind = [part_of[u][1]["applies_to"], part_of[u][1]["name"]] if u in part_of else ["", ""] if by_kind else []
        result["rows"].append(kind + [names[u][0], names[u][1]] + [shown(m, v.get(u), data) for m, v in zip(shown_measures, values)])
    result["notes"].append(f"{len(members):,} of {len(plan['members']):,} schools meet the conditions.")
    if by_kind:
        for i, p in enumerate(by_kind["parts"]):
            n = sum(1 for u in members if part_of.get(u, (None,))[0] == i)
            result["notes"].append(f"{p['applies_to']}: {n:,} ({p['name']}).")


def count_schools(plan, data, result):
    members = filtered(plan, data) if plan["conditions"] else plan["members"]
    result["columns"] = ["Group", "Schools"]
    result["rows"].append([plan["scope"], cell(len(members), "count")])


def group_rows(plan, members, data, result, prefix=()):
    for m in plan["measures"]:
        for g in group_figure(m, members, data):
            result["rows"].append(list(prefix) + [g["label"], cell(g["value"], unit_of(m)), cell(g["reporting"], "count"),
                                                  cell(g["missing"], "count")])
            if g["numerator"] is not None:
                result["counts"].append(list(prefix) + [g["label"], cell(g["numerator"], "count"), cell(g["denominator"], "count")])
            if g["missing"]:
                result["missing"].append(f"{' '.join(map(str, prefix))} {g['label']}: {g['missing']:,} schools had no value and are "
                                         "left out (not counted as zero).".strip())


def group(plan, data, result):
    result["columns"] = ["Measure", "Value", "Schools reporting", "Schools with no value"]
    result["counts_columns"] = ["Measure", "Numerator (sum)", "Denominator (sum)"]
    group_rows(plan, plan["members"], data, result)


def split(plan, data, result):
    column = plan["split"]
    by = defaultdict(set)
    for u, code in data.q(f'SELECT UNITID, "{column}" FROM directory WHERE year=?', data.year):
        if u in plan["members"]:
            by[code].add(u)
    result["columns"] = [column.title(), "Measure", "Value", "Schools reporting", "Schools with no value"]
    result["counts_columns"] = [column.title(), "Measure", "Numerator (sum)", "Denominator (sum)"]
    for code in sorted(by, key=lambda c: (c is None, c)):
        group_rows(plan, by[code], data, result, prefix=(data.label("HD", column, code),))


def school_vs_group(plan, data, result):
    """Each school named, beside the group (the group figure leaves the named schools out)."""
    result["columns"] = ["", "Measure", "Value", "Schools reporting", "Schools with no value"]
    result["counts_columns"] = ["", "Measure", "Numerator (sum)", "Denominator (sum)"]
    for school in plan["schools"]:
        for m in plan["measures"]:
            v = school_values(m, data, [school["id"]]).get(school["id"])
            result["rows"].append([school["name"], m["name"], cell(v, unit_of(m)), cell(int(v is not None), "count"),
                                   cell(int(v is None), "count")])
            num, den, _ = school_counts(m, data).get(school["id"], (None, None, None)) if m["rates"] else (None, None, None)
            if num is not None or den is not None:
                result["counts"].append([school["name"], m["name"], cell(num, "count"), cell(den, "count")])
            small = plan.get("small_cohort")
            if small and den is not None and den < small["threshold"]:
                result["warnings"].append(small["text"].format(school=school["name"], count=f"{den:,}", threshold=small["threshold"]))
    group_rows(plan, plan["members"] - {s["id"] for s in plan["schools"]}, data, result, prefix=(plan["scope"],))


def breakdown(plan, data, result):
    m, b = plan["measures"][0], plan["breakdown"]
    units = [s["id"] for s in plan["schools"]] or None
    if b["stored_as"] == "rows":
        def part_values(code):
            return data.column(m["table"], m["column"], m["rows"], extra=dict(b["fixed"], **{b["column"]: code}), units=units)
        parts = [(label, part_values(code)) for code, label in b["parts"]]
        total = part_values(b["total"]) if b["total"] != "sum of parts" else None
    else:
        parts = [(label, data.column(m["table"], code, m["rows"], units=units)) for code, label in b["parts"]]
        total = data.column(m["table"], b["total"], m["rows"], units=units) if b["total"] != "sum of parts" else None
    targets = [(s["name"], {s["id"]}) for s in plan["schools"]] if units else [(plan["scope"], plan["members"])]
    result["columns"] = ["Category"] + [name for name, _ in targets]
    hidden = 0
    for label, values in parts:
        row = [label]
        for _, ids in targets:
            got = [values[u] for u in ids if values.get(u) is not None]
            row.append(cell(sum(got) if got else None, "count"))
        if all(c is None for c in row[1:]) and b["stored_as"] == "rows":
            hidden += 1                                 # IPEDS reports no row for a category with nothing in it
            continue
        result["rows"].append(row)
    if hidden:
        result["notes"].append(f"{hidden} categories have no row reported and are not shown.")
    total_row = ["Total"]
    for name, ids in targets:
        if total is not None:
            got = [total[u] for u in ids if total.get(u) is not None]
        else:
            got = [r[len(total_row)][0] for r in result["rows"] if r[len(total_row)] is not None]
        total_row.append(cell(sum(got) if got else None, "count"))
        if all(r[len(total_row) - 1] is None for r in result["rows"]) and total_row[-1] is not None:
            result["notes"].append(f"{name}: IPEDS does not collect this detail for this row, so only the total is shown.")
    result["rows"].append(total_row)
    if b["total"] == "sum of parts":
        result["notes"].append("The total is the sum of the categories shown.")


def topic(plan, data, result):
    t = plan["topic"]
    result["columns"] = ["Measure", "Period", "Set up in this app"] if t["measures"] else []
    for m in t["measures"]:
        result["rows"].append([m["name"], m["period"], "yes" if m["set_up"] == "yes" else "not yet"])


OPS = {"schools": schools, "rank": rank, "list": listing, "count_schools": count_schools, "group": group, "split": split,
       "school_vs_group": school_vs_group, "breakdown": breakdown, "define": topic, "data_exists": topic}
