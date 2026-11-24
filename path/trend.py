"""Trends (Part 5c): a question run once for each year asked for. Resolve calls plan(); fetch calls run().

For each year:
  - each measure is read where it was stored that year (measure_years, which follows the approved rows of
    measure_history.csv), at that year's own category codes (category_codes.csv `years` and `same_as`). Where a summary
    measure has no values that year and its detailed link is loaded, the detailed measure is read instead (graduate
    12-month headcount before 2020-21). A rate computed from counts starts only once all its counts exist;
  - a group counts that year's own schools by default, or today's schools only when asked; "its peers" is today's
    comparison group; Carnegie groups hold the stated classification in every year (the build does that);
  - a year IPEDS did not collect is a gap, with "IPEDS did not collect {what} in {year}", never zero; a breakdown
    not available in a year gets its own message, and the total is still shown.
Approved comparability breaks and context notes (comparability_breaks.csv) are shown, and the years marked, when the
trend crosses them; the pandemic note goes by the period each figure covers. Schools keep today's name, with
"(then: ...)" and "merged into ..." notes where the directory says so. Every sentence comes from a "message" row.
"""
import copy
import json
import re

from path.request import covers, fill_years

OPERATIONS = ("schools", "group", "school_vs_group", "split", "breakdown")
MARK = "*"                                              # marks a year a note refers to


def label(y):
    return f"{y}-{(y + 1) % 100:02d}"


def releases(db):
    return [y for (y,) in db.execute("SELECT DISTINCT year FROM directory ORDER BY year")]


def calendar_years(text):
    """The calendar years a period's text names: 'Academic year 2015-16' -> {2015, 2016}; 'Fall 2015' -> {2015}."""
    out = set()
    for full, short in re.findall(r"((?:19|20)\d\d)(?:-(\d\d)(?!\d))?", text or ""):
        out.add(int(full))
        if short:
            out.add(int(full[:2] + short))
    return out


def choose(year, pattern, years):
    """The releases a trend shows, chosen by the period each release's figure covers (`pattern`, the measure's period
    written from the release year), so "since 2015" means figures for 2015 on, whatever the release."""
    if year.get("last"):
        return years[-int(year["last"]):]
    start, end = year.get("start") or 0, year.get("end") or 9999
    chosen = []
    for y in years:
        covered = calendar_years(fill_years(pattern, y))
        if covered and max(covered) >= start and min(covered) <= end:   # any figure whose period reaches the years asked
            chosen.append(y)
    if year.get("change") and len(chosen) >= 2:
        return [chosen[0], chosen[-1]]
    return chosen


def plan(request, plan_, d, say):
    """Choose the years and record how the trend counts schools. Returns a decline, or None."""
    from path.resolve import cohort_period, cohort_rule, decline, without
    year = request["year"]
    years = releases(d.db)
    m0 = plan_["measures"][0] if plan_["measures"] else None
    covered = plan_["members"] if plan_["members"] is not None else {s["id"] for s in plan_["schools"]}
    pattern = (m0 or {}).get("period_pattern") or "{Y}"
    rule = cohort_rule(m0, covered, d) if m0 and year.get("kind") == "entering cohort" else None
    if rule:                                            # years named as entering cohorts: matched by cohort
        pattern = f"{rule[0]} {{Y{rule[1]:+d}}}"
    chosen = choose(year, pattern, years)
    if not chosen:
        held = f"{fill_years(m0['period_pattern'], years[0])} to {fill_years(m0['period_pattern'], years[-1])}" if m0 else ""
        return decline(d, "years", request, wanted=year.get("stated"), what=m0["name"] if m0 else "", held=held,
                       asked=year.get("stated") or "")
    membership = year.get("membership") or "each year"
    periods = {y: "; ".join(dict.fromkeys(cohort_period(m, covered, d, y) or fill_years(m.get("period_pattern") or "", y)
                                          for m in plan_["measures"])) for y in chosen}
    plan_["trend"] = dict(years=chosen, change=bool(year.get("change")), membership=membership, periods=periods,
                          groups=list(plan_.get("group_names") or []), fixed=plan_.get("peer_members"), latest=years[-1])
    if plan_["members"] is not None and plan_["operation"] != "schools":
        if plan_.get("peer_members") is not None:
            plan_["statements"].append(say("trend peers"))
        else:
            plan_["statements"].append(say("trend today" if membership == "today" else "trend each year"))
            if membership != "today":                   # offered as a button: the same request, today's schools only
                plan_["offers"] = [dict(label=say("trend today offer"),
                                        request=without(request, year=dict(year, membership="today")))]
    return None


# ---- one year's measure and schools

def where(db, measure, y):
    return db.execute('SELECT "table", variable, n_values FROM measure_years WHERE UPPER(measure) = UPPER(?) AND year = ?',
                      (measure, y)).fetchone()


def year_rows(db, table, rows, y):
    """The category rows a request names, in the codes of year y (same_as); None if that year has no such row."""
    out = {}
    if not rows:
        return out
    every = db.execute('SELECT "column", code, years, same_as FROM dict_category_codes WHERE "table" = ?', (table,)).fetchall()
    listed = {c.upper() for c, _, _, _ in every}        # columns the dictionary lists codes for, in any year
    codes = [r for r in every if covers(r[2], y)]
    for column, code in rows.items():
        if any(c.upper() == column.upper() and str(k) == str(code) for c, k, _, _ in codes):
            out[column] = code
            continue
        target = f"{column}={code}".replace(" ", "").upper()
        match = [(c, k) for c, k, _, s in codes if s and target in s.replace(" ", "").upper().split(";")]
        if not match:
            if column.upper() not in listed:
                out[column] = code                      # a column the dictionary lists no codes for: unchanged
                continue
            return None
        out[match[0][0]] = match[0][1]
    return out


def members_of(db, group, y):
    return {u for (u,) in db.execute("SELECT unitid FROM group_membership WHERE group_name = ? AND year = ?", (group, y))}


def at_year(m, y, db, notes):
    """The measure as stored in year y, or None if IPEDS did not collect it that year."""
    mm = copy.copy(m)
    if m.get("parts"):                                  # one measure per kind of school: each part in year y
        parts = []
        for p in m["parts"]:
            p2 = at_year(p, y, db, notes)
            if p2:
                p2["members"] = members_of(db, p["applies_to"], y)
                parts.append(p2)
        if not parts:
            return None
        mm["parts"] = parts
        mm.update({k: parts[0][k] for k in ("table", "column", "rows")})
        mm["rates"] = [r for p in parts for r in p["rates"]]
        return mm
    if m["column"]:
        loc = where(db, m["id"], y)
        rows = year_rows(db, loc[0], m["rows"], y) if loc and loc[2] else None
        if rows is not None:
            mm["table"], mm["column"], mm["rows"] = loc[0], loc[1], rows
        else:                                           # missing that year: its detailed equivalent, where loaded
            link = db.execute("SELECT detailed, rows FROM detail_links WHERE measure = ? AND status = 'loaded'",
                              (m["id"],)).fetchone()
            d_loc = where(db, link[0], y) if link else None
            d_rows = year_rows(db, d_loc[0], json.loads(link[1] or "{}"), y) if d_loc and d_loc[2] else None
            if d_rows is None:
                return None
            mm["table"], mm["column"], mm["rows"] = d_loc[0], d_loc[1], d_rows
            notes.setdefault("detail", set()).add((m["name"], link[0], y))
    rates = []
    for r in m["rates"]:
        num, den = where(db, r["numerator"], y), where(db, r["denominator"], y)
        if not (num and num[2] and den and den[2]):
            continue                                    # a rate starts only once all its counts exist
        r2 = dict(r, numerator=f"{num[0]}.{num[1]}", denominator=f"{den[0]}.{den[1]}")
        if r.get("applies_to"):
            r2["members"] = members_of(db, r["applies_to"], y)
        rates.append(r2)
    mm["rates"] = rates
    if not m["column"] and not rates:
        return None
    return mm


def group_members(plan_, db, y):
    """The schools a group counts in year y: that year's own list, today's schools only, or a fixed set (peers)."""
    t = plan_["trend"]
    present = {u for (u,) in db.execute("SELECT UNITID FROM directory WHERE year = ?", (y,))}
    if t["fixed"] is not None:
        return set(t["fixed"]) & present
    out = None
    for g in t["groups"]:
        mine = members_of(db, g, t["latest"] if t["membership"] == "today" else y)
        out = mine if out is None else out & mine
    return (out if out is not None else set(plan_["members"] or ())) & present


# ---- notes

def spans(years):
    """[2015, 2016, 2017, 2020] -> '2015-16 to 2017-18, 2020-21'."""
    out = []
    for y in sorted(years):
        if out and y == out[-1][1] + 1:
            out[-1][1] = y
        else:
            out.append([y, y])
    return ", ".join(label(a) if a == b else f"{label(a)} to {label(b)}" for a, b in out)


def period_months(text):
    """The months a figure covers, (first, last) as yyyy-mm, from the dictionary's own period wording."""
    t = text or ""
    for pattern, first, last in ((r"July 1, (\d{4}) - June 30, (\d{4})", "{0}-07", "{1}-06"),
                                 (r"[Ff]all (\d{4})", "{0}-09", "{0}-11"),
                                 (r"[Ff]iscal year (\d{4})", "{p}-07", "{0}-06"),
                                 (r"as of (?:\w+ \d+, )?(\d{4})", "{0}-08", "{0}-08"),
                                 (r"((?:19|20)\d\d)-(\d\d)(?!\d)", "{0}-07", "{c}{1}-06")):
        found = re.search(pattern, t)
        if found:
            g = found.groups()
            return first.format(*g, p=int(g[0]) - 1, c=g[0][:2]), last.format(*g, p=int(g[0]) - 1, c=g[0][:2])
    return None


def break_notes(db, years, tables, periods):
    """The approved breaks and context notes a trend crosses: [(note, marked years)]."""
    out = []
    for ts, first, last, start, end, note in db.execute(
            "SELECT tables, first_release, last_release, period_from, period_to, note_shown FROM "
            "dict_comparability_breaks WHERE status = 'approved' ORDER BY rowid").fetchall():
        mine = {t.strip().upper() for t in (ts or "").split(",") if t.strip()}
        if mine and not mine & {t.upper() for t in tables}:
            continue
        if start:                                       # by the period each figure covers
            marked = [y for y in years if periods.get(y) and periods[y][0] <= end and periods[y][1] >= start]
        elif last:                                      # a span of releases: the years inside it
            marked = [y for y in years if int(first[:4]) <= y <= int(last[:4])]
        else:                                           # a change: marked when the trend runs across it
            marked = [int(first[:4])] if min(years) < int(first[:4]) <= max(years) else []
        if marked:
            out.append((note, marked))
    return out


def names_then(plan_, db, years, result, say):
    """Each school keeps today's name; earlier names and mergers are noted."""
    for s in plan_["schools"]:
        then = {}
        for y, n in db.execute(f"SELECT year, INSTNM FROM directory WHERE UNITID = ? AND year IN ({','.join('?' * len(years))})",
                               (s["id"], *years)):
            if n and n.strip().lower() != (s["name"] or "").strip().lower():
                then.setdefault(n.strip(), []).append(y)
        for n, ys in then.items():
            result["notes"].append(say("then named", school=s["name"], then=n, year=spans(ys)))
        last = db.execute("SELECT MAX(year) FROM directory WHERE UNITID = ?", (s["id"],)).fetchone()[0]
        if last is not None and last < plan_["trend"]["latest"]:
            into = db.execute("SELECT NEWID FROM HD WHERE UNITID = ? AND year = ?", (s["id"], last)).fetchone()
            if into and into[0] and int(into[0]) > 0 and int(into[0]) != s["id"]:
                name = db.execute("SELECT INSTNM FROM directory WHERE UNITID = ? ORDER BY year DESC", (int(into[0]),)).fetchone()
                if name:
                    result["notes"].append(say("merged", school=s["name"], into=name[0], year=label(last + 1)))


# ---- the table

def run(plan_, db, result, fetch):
    """Fill `result` for a trend: one row per year, one column per school, group or category."""
    t, op = plan_["trend"], plan_["operation"]
    say = lambda key, **f: fetch.say(db, key, **f)
    years, notes, missing, tables, periods = t["years"], {}, {}, set(), {}
    series, values = [], {}                             # series: [(key, column heading, unit)]
    several = len(plan_["measures"]) > 1

    def put(key, heading, unit, y, value, collected=True):
        if key not in values:
            series.append((key, heading, unit))
            values[key] = {}
        if collected:
            values[key][y] = value

    for y in years:
        data = fetch.Data(db, year=y)
        members = group_members(plan_, db, y) if plan_["members"] is not None else None
        for m in plan_["measures"]:
            mm = at_year(m, y, db, notes)
            if mm is None:
                missing.setdefault(m["name"], set()).add(y)
            else:
                tables.update(({mm["table"]} | {p["table"] for p in mm.get("parts") or []} |   # (a rate from counts has no table)
                               {r[k].partition(".")[0] for r in mm["rates"] for k in ("numerator", "denominator")}) - {None})
            if m.get("period_pattern") and y not in periods:
                periods[y] = period_months(fill_years(m["period_pattern"], y))
            suffix, unit = (f": {m.get('shown_as') or m['name']}" if several else ""), fetch.unit_of(m)
            if op == "breakdown":
                breakdown_year(plan_, m, mm, y, data, members, put, result, say, db)
                continue
            if op in ("schools", "school_vs_group"):
                for s in plan_["schools"]:
                    v = fetch.school_values(mm, data, [s["id"]]).get(s["id"]) if mm else None
                    put(("school", s["id"], m["id"]), s["name"] + suffix, unit, y, v, mm is not None)
            if op in ("group", "school_vs_group", "split"):
                scope = members - {s["id"] for s in plan_["schools"]} if op == "school_vs_group" else members
                parts = [(plan_["scope"] or "Group", scope)]
                if op == "split":
                    by = {}
                    for u, code in data.q(f'SELECT UNITID, "{plan_["split"]}" FROM directory WHERE year = ?', y):
                        if u in scope:
                            by.setdefault(code, set()).add(u)
                    parts = [(data.label("HD", plan_["split"], c), by[c]) for c in sorted(by, key=lambda c: (c is None, c))]
                for name, who in parts:
                    rows = fetch.group_figure(mm, who, data) if mm else [dict(label=m["name"], value=None)]
                    for g in rows:
                        extra = g["label"][len(m["name"]):] if g["label"].startswith(m["name"]) else ""
                        put(("group", name, m["id"], extra), name + extra + suffix, unit, y, g["value"], mm is not None)
    marks = {}
    for i, (note, marked) in enumerate(break_notes(db, years, tables, periods), 1):
        for y in marked:
            marks.setdefault(y, []).append(f"{MARK}{i}")
        result["notes"].append(f"{MARK}{i} {note}")
    result["columns"] = ["Year", "Period"] + [heading for _, heading, _ in series]
    for y in years:                                     # measures with different periods: each period, in order
        row = [label(y) + ("".join(" " + k for k in marks.get(y, []))), t["periods"].get(y, "")]
        for key, _, unit in series:
            row.append(fetch.cell(values[key][y], unit) if y in values[key] else "not collected")
        result["rows"].append(row)
    if t["change"] and len(years) == 2:
        result["rows"].append(change_row(say("trend change"), series, values, years))
    for name, ys in missing.items():
        result["notes"].append(say("not collected year", what=name, year=spans(ys)))
    detail = {}
    for name, link, y in notes.get("detail", ()):
        detail.setdefault((name, link), []).append(y)
    for (name, link), ys in detail.items():
        result["notes"].append(say("trend detail", what=name, detail=link, year=spans(ys)))
    if plan_["schools"]:
        names_then(plan_, db, years, result, say)
    result["chart"] = dict(kind="line", x="Year", series=[heading for _, heading, _ in series],
                           unit=series[0][2] if series else None,
                           points=[(label(y), heading, values[key].get(y)) for y in years for key, heading, _ in series])


def breakdown_year(plan_, m, mm, y, data, members, put, result, say, db):
    """One year of a breakdown over time: each category, then the total. Where the set is not available that year,
    the total alone, with the message."""
    b = plan_["breakdown"]
    ids = {plan_["schools"][0]["id"]} if plan_["schools"] else members
    if mm is None:
        for _, lab in b["parts"]:
            put(("part", lab), lab, "count", y, None, False)
        put(("total",), "Total", "count", y, None, False)
        return
    status = db.execute("SELECT status FROM year_checks WHERE kind = 'set' AND name = ? AND \"table\" = ? AND year = ? "
                        "ORDER BY measure = ? DESC", (b["set"], m["table"], y, m["column"])).fetchone()
    usable = bool(status) and status[0] in ("loaded", "additive")
    few = list(ids) if plan_["schools"] else None       # one school: read its rows only

    def total_of(values):
        got = [values[u] for u in ids if values.get(u) is not None]
        return sum(got) if got else None

    shown = []
    for code, lab in b["parts"]:
        values = None
        if usable and b["stored_as"] == "rows":
            rows = year_rows(db, mm["table"], dict(mm["rows"], **b["fixed"], **{b["column"]: code}), y)
            values = data.column(mm["table"], mm["column"], rows, units=few) if rows is not None else None
        elif usable:
            loc = where(db, f"{m['table']}.{code}", y)
            values = data.column(loc[0], loc[1], mm["rows"], units=few) if loc and loc[2] else None
        put(("part", lab), lab, "count", y, total_of(values) if values is not None else None, values is not None)
        if values is not None:
            shown.append(total_of(values))
    if b["total"] == "sum of parts":
        got = [v for v in shown if v is not None]
        total = sum(got) if got else None
    elif b["stored_as"] == "rows":
        rows = year_rows(db, mm["table"], dict(mm["rows"], **b["fixed"], **{b["column"]: b["total"]}), y)
        total = total_of(data.column(mm["table"], mm["column"], rows, units=few)) if rows is not None else None
    else:
        loc = where(db, f"{m['table']}.{b['total']}", y)
        total = total_of(data.column(loc[0], loc[1], mm["rows"], units=few)) if loc and loc[2] else None
    if total is None and not usable:                    # the measure itself, as stored that year
        total = total_of(data.column(mm["table"], mm["column"], mm["rows"], units=few))
    put(("total",), "Total", "count", y, total)
    if not usable:
        why = say("breakdown why " + (status[0] if status else "not collected"))
        result["notes"].append(say("breakdown not this year", set=b["set"], year=label(y), why=why))


def change_row(title, series, values, years):
    """The change between the first and last year: points for percents, otherwise the difference and percent change."""
    a, b = years
    row = [title, f"{label(a)} to {label(b)}"]
    for key, _, unit in series:
        va, vb = values[key].get(a), values[key].get(b)
        if va is None or vb is None:
            row.append("no value")
        elif unit == "percent":
            row.append(f"{vb - va:+.1f} points")
        else:
            money = "$" if unit in ("dollars", "average") else ""
            pct = f" ({100 * (vb / va - 1):+.1f}%)" if va else ""
            row.append(f"{'-' if vb < va else '+'}{money}{abs(vb - va):,.0f}{pct}")
    return row
