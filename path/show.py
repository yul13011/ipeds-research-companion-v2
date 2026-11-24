"""Step 6, Show: turn a plan and its rows into what the page displays. Code only.

"Interpreted as" is built from the dictionary's own wording (measure names, group definitions,
term and setting statements, periods), never written by the model, so nothing in it is invented.
"""
PHRASES = {"schools": "{measures} for {who}", "rank": "Rank {who} by {measures}, {order} first",
           "list": "List {who} that meet the conditions", "breakdown": "{measures} for {who}, broken down {set}",
           "group": "{measures} for {who}", "split": "{measures} for {who}, shown separately by {split}",
           "count_schools": "Count of {who}", "school_vs_group": "{measures}: {school} beside {who}",
           "define": "Definition", "data_exists": "What data exists on {topic}"}


def fmt(cell):
    """A figure as text. Percents stored by IPEDS are whole numbers; group rates carry decimals."""
    if cell is None:
        return "no value"
    if not isinstance(cell, tuple):
        return str(cell)
    value, unit = cell
    if unit == "percent":
        return f"{value:.1f}%" if value != int(value) else f"{int(value)}%"
    if unit in ("dollars", "average"):
        return f"${value:,.0f}"
    if unit == "ratio":
        return f"{value:g}"
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"


def interpreted(plan):
    who = ", ".join(s["name"] for s in plan["schools"]) if plan["operation"] in ("schools", "breakdown") and plan["schools"] \
        else (plan["scope"] or "the schools named")
    names = list(dict.fromkeys((m.get("shown_as") or m["name"]) + "".join(f", {x}" for x in m.get("row_labels", []))
                               for m in plan["measures"]))
    trend = plan.get("trend")
    if trend and not trend["single"] and plan["operation"] in ("rank", "list"):   # ranked or listed by the change
        names = [f"the change in {n}" for n in names]
    text = PHRASES[plan["operation"]].format(
        measures=", ".join(names) or "schools", who=who, order=(plan["sort"] or {}).get("order", ""),
        set=" ".join([(plan["breakdown"] or {}).get("set", "").lower()] +
                     [f"({x})" for x in (plan["breakdown"] or {}).get("fixed_labels", [])]), split=plan["split"] or "",
        school=", ".join(s["name"] for s in plan["schools"]), topic=(plan["topic"] or {}).get("asked") or "the topic")
    periods = list(dict.fromkeys(m["period"] for m in plan["measures"] + [c["measure"] for c in plan["conditions"]]
                                 if m.get("period")))                   # a measure used only in a condition too
    if plan.get("trend"):                               # over several years: the first and last figure's periods
        years, by_year = plan["trend"]["years"], plan["trend"]["periods"]
        ends = [by_year.get(years[0]), by_year.get(years[-1])]
        if all(ends):
            periods = [(" and " if plan["trend"]["change"] else " to ").join(dict.fromkeys(ends))]
    if periods:
        text += f" ({'; '.join(periods)})"
    for c in plan["conditions"]:
        text += f"; where {c['measure']['name']} {c['comparison']} {c['value']}"
    return ". ".join([text] + [s.rstrip(".") for s in plan["statements"] if s]) + "."


def calculation(m):
    method = m.get("method")
    if method == "sum":
        return "Added up across the schools that reported a value; schools with no value are left out, not counted as zero."
    if method == "rate" or (m["rates"] and not m["column"]):
        r = m["rates"][0]
        if r["method"] == "weighted average":
            return f"Each school's {r['numerator']} weighted by its {r['denominator']}, summed, then divided by the summed weights."
        return f"{r['numerator']} summed across schools, divided by {r['denominator']} summed across the same schools."
    return "As reported by each school."


def definitions(plan):
    out = []
    for m in plan["measures"] + [c["measure"] for c in plan["conditions"]]:
        sources = [m["source"]] if m["source"] else []
        sources += sorted({r[k].partition(".")[0] for r in m["rates"] for k in ("numerator", "denominator")}) if m.get("method") == "rate" or not m["column"] else []
        out.append(dict(measure=m["name"], scope=plan["scope"] or ", ".join(s["name"] for s in plan["schools"]),
                        period=f"{m['period']} ({m['period_kind']})", definition=(m["definition"] or "")[:600],
                        calculation=calculation(m), sources=", ".join(sources), notes=" ".join(plan["word_notes"])))
    return out


def topic_message(plan):
    t = plan["topic"]
    if t["outside"]:                                    # "IPEDS does not collect this": only from the outside-IPEDS table
        return t.get("say") or t["outside"]["say"]
    if not t["measures"]:                               # nothing matched: "not found", with the closest matches
        return t.get("not_found") or ""
    if plan["operation"] == "define":
        return "\n\n".join(f"**{m['name']}** ({m['period']}): {m['definition']}" for m in t["measures"])
    ready = [m for m in t["measures"] if m["set_up"] == "yes" and not m.get("retired")]
    if ready:
        return ("Yes. This app has: " + "; ".join(f"{m['name']} ({m['period']})" for m in ready)
                + ".")
    gone = [m["retired"] for m in t["measures"] if m.get("retired")]   # collected once, no longer: the "retired" message
    if gone and len(gone) == len(t["measures"]):
        return " ".join(gone)
    still = "; ".join(m["name"] for m in t["measures"] if not m.get("retired"))
    return " ".join(["IPEDS collects this, but it is not set up in this app yet: " + still + "."] + gone)


def bars(plan, result):
    """A bar chart for a comparison in one year: one bar per row, for the first column of figures."""
    trend = plan.get("trend")
    if (trend and not trend["single"]) or plan["operation"] not in ("schools", "rank", "split", "school_vs_group", "breakdown"):
        return None
    if plan["operation"] == "schools" and len(result["rows"]) < 2:
        return None
    rows = result["rows"]
    if plan["operation"] == "breakdown":                # the categories, without the total
        rows = [r for r in rows if r[0] != "Total"]
    figure = next((i for i in range(1, len(result["columns"])) if any(isinstance(r[i], tuple) for r in rows)), None)
    if figure is None or len(rows) < 2:
        return None
    name = 1 if plan["operation"] == "rank" else 0
    cells = [(str(r[name]) + (f", {r[1]}" if plan["operation"] in ("split", "school_vs_group") and len(plan["measures"]) > 1 else ""),
              r[figure]) for r in rows if isinstance(r[figure], tuple)]
    if len(cells) < 2:
        return None
    return dict(kind="bar", x=result["columns"][name] or "Name", series=[result["columns"][figure]],
                unit=cells[0][1][1], points=[(n, result["columns"][figure], c[0]) for n, c in cells])


def release_label(release):
    """'IPEDS 2024-25 release (provisional)' from {release, status}."""
    name = release["release"].rsplit("_", 1)[0].replace("_", " ")
    return f"{name} release ({release['status']})"


def render(plan, result, release):
    """Everything the page shows for one answer. `release` is {year, release, status} for the year shown."""
    warnings = []
    if isinstance(release, str):                        # older callers pass the release name only
        release = dict(year=None, release=release, status="provisional" if "Provisional" in release else "final")
    if release["status"] == "provisional":
        warnings.append(f"These figures come from the {release_label(release)}, which is provisional and may change.")
    if result["missing"]:
        warnings.append("Some values are missing. See the data status; missing values are never counted as zero.")
    warnings += result["warnings"] + plan["caveats"]
    page = dict(kind="answer", interpreted=interpreted(plan), warnings=warnings, notes=result["notes"],
                table=dict(columns=result["columns"], rows=[[fmt(c) for c in row] for row in result["rows"]]),
                counts=dict(columns=result["counts_columns"], rows=[[fmt(c) for c in row] for row in result["counts"]]),
                status=result["missing"], definitions=definitions(plan), message=None,
                data_release=f"Figures from the {release_label(release)}.", chart=result.get("chart") or bars(plan, result),
                offers=[o["label"] for o in plan.get("offers") or []])
    if plan.get("trend") and plan["trend"]["single"]:   # one earlier year: its own release
        y = plan["trend"]["years"][0]
        page["data_release"] = f"Figures from the IPEDS {y}-{(y + 1) % 100:02d} release."
    elif plan.get("trend"):                             # each year's figure comes from its own release
        years = plan["trend"]["years"]
        page["data_release"] = (f"Figures from the IPEDS releases {years[0]}-{(years[0] + 1) % 100:02d} to "
                                f"{years[-1]}-{(years[-1] + 1) % 100:02d}; each year's figure comes from the release in "
                                "which it is the current year.")
    if plan["operation"] in ("define", "data_exists"):
        page["message"] = topic_message(plan)
    return page
