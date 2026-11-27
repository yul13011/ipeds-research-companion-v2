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
A figure IPEDS holds for several years in one table (net price for this year and the two before: measures.csv
`own_column`) is read from each release's own column. The years no loaded release's own column covers come from the
earlier-year columns of the earliest release that holds the figure, labelled "as reported in the ... release" (owner
decision 2026-11-25).
Approved comparability breaks and context notes (comparability_breaks.csv) are shown, and the years marked, when the
trend crosses them; the pandemic note goes by the period each figure covers. Schools keep today's name, with
"(then: ...)" and "merged into ..." notes where the directory says so. Every sentence comes from a "message" row.
"""
import copy
import json
import re

from path.request import covers, fill_years

OPERATIONS = ("schools", "group", "school_vs_group", "split", "breakdown", "rank", "list")   # over several years; one
                                                        # named year works with every operation
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
    written from the release year): periods that start in the years asked (owner decision, 2026-11-23), so "since
    2015" means fall 2015, aid year 2015-16 or fiscal year 2015 on, whatever the release. One named year is a range of
    one."""
    if year.get("last"):
        return years[-int(year["last"]):]
    start = year.get("start") or 0
    end = start if year.get("span") == "one year" else (year.get("end") or 9999)
    if year.get("span") == "one year" and year.get("end") == start + 1:   # "2022-23": the periods inside July to June
        inside = [y for y in years if (lambda p: p and f"{start}-07" <= p[0] and p[1] <= f"{start + 1}-06")(
            period_months(fill_years(pattern, y)))]
        if inside:
            return inside[-1:]
    chosen = []
    for y in years:
        covered = calendar_years(fill_years(pattern, y))
        if covered and start <= min(covered) <= end:    # a period is placed by the year it starts
            chosen.append(y)
    if year.get("change") and len(chosen) >= 2:
        return [chosen[0], chosen[-1]]
    return chosen


def plan(request, plan_, d, say):
    """Choose the years and record how the trend counts schools. Returns a decline, or None."""
    from path.resolve import cohort_period, cohort_rule, decline, without
    year = request["year"]
    years = sorted(set(releases(d.db)) | extra_years(d.db, plan_["measures"]))   # and the years only earlier-year columns hold
    unnamed = not (year.get("start") or year.get("end") or year.get("last"))      # a trend with no years named:
    rule, statement = d.setting("trend with no years stated") if unnamed else (None, None)   # terms.csv (owner
    if rule == "releases held":                         # decision 2026-11-25): every release that holds the figure,
        held = set()                                    # no years from a later release's earlier-year columns
        for m in plan_["measures"]:
            for mid in [p["id"] for p in m.get("parts") or []] or [m["id"]]:
                held |= set(held_years(d.db, mid))
        years = sorted(held & set(releases(d.db))) or releases(d.db)
    m0 = plan_["measures"][0] if plan_["measures"] else None
    covered = plan_["members"] if plan_["members"] is not None else {s["id"] for s in plan_["schools"]}
    pattern = (m0 or {}).get("period_pattern") or "{Y}"
    rules = [cohort_rule(m, covered, d) for m in plan_["measures"]] if year.get("kind") == "entering cohort" else []
    rule = next((r for r in rules if r), None)          # years named as entering cohorts: matched by the cohort of
    if rule:                                            # the first measure that has one
        pattern = f"{rule[0]} {{Y{rule[1]:+d}}}"
    chosen = choose(year, pattern, years)
    if not chosen and year.get("span") == "one year" and year.get("start") == years[-1]:
        return None                                     # the newest release's own year: the usual latest-year answer
    if not chosen:
        first, last = (fill_years(m0["period_pattern"], years[0]), fill_years(m0["period_pattern"], years[-1])) if m0 else ("", "")
        latest = dict(year, span=None, start=None, end=None, last=None, change=False, kind="latest", stated=None)
        return decline(d, "years", request, wanted=year.get("stated"), what=m0["name"] if m0 else "",
                       held=f"{first} to {last}", asked=year.get("stated") or "",
                       closest=dict(text=f"{m0['name']} for {last}", request=without(request, year=latest)) if m0 else None)
    single = len(chosen) == 1 and not year.get("change")
    op = plan_["operation"]
    if not single and (op not in OPERATIONS or (op == "breakdown" and len(plan_["schools"]) > 1)):
        return decline(d, "trend operation", request, closest=dict(
            text=say("trend operation instead"), request=without(request, year=dict(year, span=None, start=None, end=None,
                                                                                    last=None, change=False))))
    if single and chosen == years[-1:] and not any(m.get("retired") for m in plan_["measures"]):
        return None                                     # the latest year: the usual one-year answer
    membership = year.get("membership") or "each year"
    if statement:
        plan_["statements"].append(statement)
    periods = {y: "; ".join(dict.fromkeys(cohort_period(m, covered, d, y) or fill_years(m.get("period_pattern") or "", y)
                                          for m in plan_["measures"])) for y in chosen}
    plan_["trend"] = dict(years=chosen, change=bool(year.get("change")), membership=membership, periods=periods, single=single,
                          groups=list(plan_.get("group_names") or []), fixed=plan_.get("peer_members"), latest=years[-1])
    if plan_["members"] is not None and plan_["operation"] != "schools":
        if plan_.get("peer_members") is not None:
            plan_["statements"].append(say("trend peers"))
        else:                                           # groups whose latest list is used for every year (school_groups.csv
            fixed = [g for g in request["groups"]       # `membership`, the Carnegie groups): said, and no "today" button
                     if d.one('SELECT 1 FROM dict_school_groups WHERE "group"=? AND membership=?', g, 'as of latest year')]
            if fixed:
                plan_["statements"].append(say("trend latest list", groups=", ".join(fixed), latest=label(years[-1])))
            if len(fixed) < len(request["groups"]) or not request["groups"]:
                plan_["statements"].append(say("trend today" if membership == "today" else "trend each year"))
                if membership != "today":               # offered as a button: the same request, today's schools only
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


def family(db, mid):
    """{years_back: member measure} for the figure whose own column is `mid`; empty if it has no earlier-year columns."""
    return {int(b): f"{t}.{v}" for t, v, b in db.execute('SELECT "table", variable, years_back FROM dict_measures '
                                                          "WHERE UPPER(own_column) = UPPER(?)", (mid,))}


def held_years(db, mid):
    return [y for (y,) in db.execute("SELECT year FROM measure_years WHERE UPPER(measure) = UPPER(?) AND n_values > 0 "
                                     "ORDER BY year", (mid,))]


def borrowed(db, mid, y):
    """For a year whose release holds no own column for `mid`: (earlier-year column, the release it is read from), from
    the earliest later release that holds the figure; None if there is none."""
    later = [r for r in held_years(db, mid) if r > y]
    member = family(db, mid).get(later[0] - y) if later else None
    return (member, later[0]) if member and where(db, member, later[0]) else None


def extra_years(db, measures):
    """Years before a figure's first own column that its earlier-year columns cover (net price 2012-13 and 2013-14)."""
    out = set()
    for m in measures:
        for mid in [p["id"] for p in m.get("parts") or []] or [m["id"]]:
            fam, held = family(db, mid), held_years(db, mid)
            if fam and held:
                out |= {held[0] - k for k in fam if k > 0}
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
                p2["members"] = members_of(db, p["applies_to"], p2.get("from_release") or y)   # the release read
                parts.append(p2)
        if not parts:
            return None
        mm["parts"] = parts
        mm["from_release"] = next((p["from_release"] for p in parts if p.get("from_release")), None)
        mm.update({k: parts[0][k] for k in ("table", "column", "rows")})
        mm["rates"] = [r for p in parts for r in p["rates"]]
        return mm
    if m["column"]:
        loc = where(db, m["id"], y)
        rows = year_rows(db, loc[0], m["rows"], y) if loc and loc[2] else None
        early = borrowed(db, m["id"], y) if rows is None else None
        if early:                                       # a year no release's own column covers: an earlier-year column
            r_loc = where(db, early[0], early[1])
            mm["table"], mm["column"], mm["rows"] = r_loc[0], r_loc[1], year_rows(db, r_loc[0], m["rows"], early[1]) or {}
            mm["from_release"] = early[1]
            notes.setdefault("earlier", {}).setdefault(early[1], set()).add(y)
        elif rows is not None:
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
    base = (out if out is not None else set(plan_["members"] or ())) & present
    return base | (set(plan_.get("plus") or ()) & present)   # schools added to the group, each year they report


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
        mine = {t.strip().upper() for t in (ts or "").split(",") if t.strip()}   # tables, or single measures (TABLE.COLUMN)
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
        here = fetch.Data(db, year=y)
        members_here = group_members(plan_, db, y) if plan_["members"] is not None else None
        for m in plan_["measures"]:
            mm = at_year(m, y, db, notes)
            data, members = here, members_here
            if mm and mm.get("from_release"):           # read from the later release that holds the earlier-year column
                data = fetch.Data(db, year=mm["from_release"])
                members = group_members(plan_, db, mm["from_release"]) if plan_["members"] is not None else None
            if mm is None:
                missing.setdefault(m["name"], set()).add(y)
            else:
                tables.update(({mm["table"]} | {p["table"] for p in mm.get("parts") or []} |   # (a rate from counts has no table)
                               {r[k].partition(".")[0] for r in mm["rates"] for k in ("numerator", "denominator")}) - {None})
                tables.update(({mm["id"]} | {p["id"] for p in mm.get("parts") or []} |          # and each measure, for a break
                               {r[k] for r in mm["rates"] for k in ("numerator", "denominator")}) - {None})  # that names measures
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
                name = plan_["scope"] or "Group"
                if op == "school_vs_group" and scope != members:     # schools compared are in the group
                    name = say("group compared, trend", group=name)
                parts = [(name, scope)]
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
    earlier = [(say("as reported", years=", ".join(t["periods"].get(y) or label(y) for y in sorted(ys)), release=label(r)), ys)
               for r, ys in sorted(notes.get("earlier", {}).items())]
    for i, (note, marked) in enumerate(list(break_notes(db, years, tables, periods)) + earlier, 1):
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
    for (name, link), ys in _detail(notes).items():
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
    """The change between the first and last year, one cell per column."""
    a, b = years
    row = [title, f"{label(a)} to {label(b)}"]
    for key, _, unit in series:
        va, vb = values[key].get(a), values[key].get(b)
        row.append("no value" if va is None or vb is None else difference(va, vb, unit))
    return row


# ---- one earlier year, and rankings or lists by the change between two years

def answer(plan_, db, result, fetch):
    """The trend answer for the plan: one named earlier year, a ranking or list by change, or the table by year."""
    t, op = plan_["trend"], plan_["operation"]
    if t["single"] and op != "breakdown":
        single(plan_, db, result, fetch)
    elif op in ("rank", "list"):
        by_change(plan_, db, result, fetch)
    else:
        run(plan_, db, result, fetch)


def single(plan_, db, result, fetch):
    """One named earlier year, answered as the latest year would be: the same operation, on that year's release, with
    that year's measures, codes and schools."""
    y = plan_["trend"]["years"][0]
    say = lambda key, **f: fetch.say(db, key, **f)
    notes, gone = {}, []
    year_plan = dict(plan_, measures=[], conditions=[])
    for m in plan_["measures"]:
        mm = at_year(m, y, db, notes)
        if mm is None:
            gone.append(m["name"])
        else:
            year_plan["measures"].append(mm)
    for c in plan_["conditions"]:
        mm = at_year(c["measure"], y, db, notes)
        if mm is None:
            gone.append(c["measure"]["name"])
        else:
            year_plan["conditions"].append(dict(c, measure=mm))
    if plan_["members"] is not None:
        year_plan["members"] = group_members(plan_, db, y)
    for name in dict.fromkeys(gone):
        result["notes"].append(say("not collected year", what=name, year=label(y)))
    if (plan_["measures"] and not year_plan["measures"]) or len(year_plan["conditions"]) < len(plan_["conditions"]):
        return                                          # nothing to show for that year: the note says why
    data = fetch.Data(db, year=y)
    fetch.OPS[plan_["operation"]](year_plan, data, result)
    fetch.campus_notes(year_plan, data, result, fetch.shown_schools(year_plan, result))
    for (name, link), ys in _detail(notes).items():
        result["notes"].append(say("trend detail", what=name, detail=link, year=spans(ys)))
    if plan_["schools"] and plan_["operation"] not in ("rank", "list"):
        names_then(plan_, db, [y], result, say)


def _detail(notes):
    out = {}
    for name, link, y in notes.get("detail", ()):
        out.setdefault((name, link), []).append(y)
    return out


def by_change(plan_, db, result, fetch):
    """A ranking or list by the change between the first and last year chosen. A school counts when it belongs to the
    group in both years (each year's own schools), or today (today's schools only), and has a value in both years;
    missing values are never zero. A change keeps values of zero; only a percent change needs a starting value above
    zero. A rate keeps the ranking guard in both years."""
    t, op = plan_["trend"], plan_["operation"]
    say = lambda key, **f: fetch.say(db, key, **f)
    a, b = t["years"][0], t["years"][-1]
    notes = {}
    data = {a: fetch.Data(db, year=a), b: fetch.Data(db, year=b)}
    who = group_members(plan_, db, a) & group_members(plan_, db, b)
    shown = list({m["id"]: m for m in [c["measure"] for c in plan_["conditions"]] + plan_["measures"]}.values())
    at = {(m["id"], y): at_year(m, y, db, notes) for m in shown for y in (a, b)}
    gone = [(m["name"], y) for m in shown for y in (a, b) if at[(m["id"], y)] is None]
    for name, y in gone:
        result["notes"].append(say("not collected year", what=name, year=label(y)))
    if gone:
        return                                          # a change needs both years: the note says which is missing
    values = {(m["id"], y): fetch.school_values(at[(m["id"], y)], data[y]) for m in shown for y in (a, b)}

    def change(m, u):
        va, vb = values[(m["id"], a)].get(u), values[(m["id"], b)].get(u)
        return None if va is None or vb is None else (va, vb, vb - va)

    tables = ({mm["table"] for mm in at.values()} | {mm["id"] for mm in at.values()}) - {None}
    marks = {}
    for i, (note, marked) in enumerate(break_notes(db, [a, b], tables, {}), 1):
        for y in marked:
            marks.setdefault(y, []).append(f"{MARK}{i}")
        result["notes"].append(f"{MARK}{i} {note}")
    heading = lambda y: label(y) + "".join(" " + k for k in marks.get(y, []))
    if op == "rank":
        m = plan_["measures"][0]
        unit = fetch.unit_of(m)
        counts = {y: fetch.school_counts(at[(m["id"], y)], data[y]) if m["rates"] else {} for y in (a, b)}
        kept, no_value, small = [], 0, 0
        for u in who:
            got = change(m, u)
            if got is None:                             # a change keeps values of zero (owner, 2026-11-24)
                no_value += 1
                continue
            if plan_["guard"] and any((counts[y].get(u, (None, None))[1] or 0) < plan_["guard"] for y in (a, b)):
                small += 1
                continue
            kept.append((got, u))
        kept.sort(key=lambda x: -x[0][2] if plan_["sort"]["order"] == "highest" else x[0][2])
        top = kept[:plan_["sort"]["limit"]]
        names = data[b].names([u for _, u in top])
        result["listed"] = [u for _, u in top]
        result["columns"] = ["Rank", "School", "State", heading(a), heading(b), say("trend change")]
        for i, ((va, vb, _), u) in enumerate(top, 1):
            result["rows"].append([i, names[u][0], names[u][1], fetch.cell(va, unit), fetch.cell(vb, unit),
                                   difference(va, vb, unit)])
        said = say("change ranked", ranked=f"{len(kept):,}", schools=f"{len(who):,}")
        if no_value:
            said += " " + say("change ranked missing", left=f"{no_value:,}")
        if plan_["guard"]:
            said += " " + say("change ranked guard", small=f"{small:,}", guard=plan_["guard"])
        result["notes"].append(said)
        return
    kept = set(who)                                     # a list: each condition on the change of its measure
    for c in plan_["conditions"]:
        kept = {u for u in kept if change(c["measure"], u) and
                fetch.passes(change(c["measure"], u)[2], c["comparison"], c["value"])}
    names = data[b].names(sorted(kept))
    result["listed"] = sorted(kept)
    result["columns"] = ["School", "State"] + [f"{m['name']}, {h}" for m in shown
                                               for h in (heading(a), heading(b), say("trend change"))]
    for u in sorted(kept, key=lambda u: names[u][0]):
        row = [names[u][0], names[u][1]]
        for m in shown:
            got, unit = change(m, u), fetch.unit_of(m)
            row += ([fetch.cell(got[0], unit), fetch.cell(got[1], unit), difference(got[0], got[1], unit)] if got
                    else ["no value"] * 3)
        result["rows"].append(row)
    result["notes"].append(say("change listed", listed=f"{len(kept):,}", schools=f"{len(who):,}"))


def difference(va, vb, unit):
    """The change from va to vb: points for percents, otherwise the difference and the percent change."""
    if unit == "percent":
        return f"{vb - va:+.1f} points"
    money = "$" if unit in ("dollars", "average") else ""
    pct = f" ({100 * (vb / va - 1):+.1f}%)" if va > 0 else ""    # no percent change from zero or below
    return f"{'-' if vb < va else '+'}{money}{abs(vb - va):,.0f}{pct}"
