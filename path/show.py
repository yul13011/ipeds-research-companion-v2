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
    text = PHRASES[plan["operation"]].format(
        measures=", ".join(names) or "schools", who=who, order=(plan["sort"] or {}).get("order", ""),
        set=" ".join([(plan["breakdown"] or {}).get("set", "").lower()] +
                     [f"({x})" for x in (plan["breakdown"] or {}).get("fixed_labels", [])]), split=plan["split"] or "",
        school=plan["schools"][0]["name"] if plan["schools"] else "", topic=(plan["topic"] or {}).get("asked") or "the topic")
    periods = list(dict.fromkeys(m["period"] for m in plan["measures"] if m.get("period")))
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
    if t["outside"]:
        o = t["outside"]
        return o["say"] + (f" See: {o['pointer']}." if o["pointer"] else "")
    if not t["measures"]:
        return f"IPEDS does not collect data on {t['asked'] or 'that topic'}."
    if plan["operation"] == "define":
        return "\n\n".join(f"**{m['name']}** ({m['period']}): {m['definition']}" for m in t["measures"])
    ready = [m for m in t["measures"] if m["set_up"] == "yes"]
    if ready:
        return ("Yes. This app has: " + "; ".join(f"{m['name']} ({m['period']})" for m in ready)
                + ". This first version holds the 2024-25 IPEDS release only.")
    return "IPEDS collects this, but it is not set up in this app yet: " + "; ".join(m["name"] for m in t["measures"]) + "."


def render(plan, result, release):
    """Everything the page shows for one answer."""
    warnings = []
    if "Provisional" in release:
        warnings.append(f"These figures come from the {release.replace('_', ' ')} release, which is provisional and may change.")
    if result["missing"]:
        warnings.append("Some values are missing. See the data status; missing values are never counted as zero.")
    warnings += result["warnings"] + plan["caveats"]
    page = dict(kind="answer", interpreted=interpreted(plan), warnings=warnings, notes=result["notes"],
                table=dict(columns=result["columns"], rows=[[fmt(c) for c in row] for row in result["rows"]]),
                counts=dict(columns=result["counts_columns"], rows=[[fmt(c) for c in row] for row in result["counts"]]),
                status=result["missing"], definitions=definitions(plan), message=None)
    if plan["operation"] in ("define", "data_exists"):
        page["message"] = topic_message(plan)
    return page
