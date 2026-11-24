"""The chat page for the first slice of version 2. Run: streamlit run app.py

The page only displays what path/answer.py returns. It holds the conversation in the session:
the requests answered so far, any options or school picker waiting for the user.
"""
import altair as alt
import pandas as pd
import streamlit as st

import config
from path import answer
from path.log import Log

st.set_page_config(page_title="IPEDS Research Companion", layout="wide")
s = st.session_state
s.setdefault("conversation", {})
s.setdefault("turns", [])
log = Log()

with st.sidebar:
    st.header("IPEDS Research Companion")
    st.caption("Version 2. Ten IPEDS releases are loaded (2015-16 to 2024-25). Answers use the latest year unless "
               "you ask about a period, such as \"since 2015\" or \"the last five years\".")
    names = list(config.MODELS)
    default = next((n for n, m in config.MODELS.items() if m == config.INTERPRET_MODEL), names[0])
    s.model = config.MODELS[st.selectbox("Model for reading questions", names, index=names.index(default))]
    s.summary_on = st.toggle("Written summary", value=config.SUMMARY,
                             help="Two or three sentences under each answer, checked against its table.")
    if st.button("Clear conversation"):
        s.conversation, s.turns = {}, []
        st.rerun()


def table(part):
    if part["rows"]:
        st.dataframe(pd.DataFrame(part["rows"], columns=part["columns"]), hide_index=True, width="stretch")


def chart(spec):
    """The automatic chart: a line over the years for a trend, bars for a comparison in one year."""
    if not spec or not any(v is not None for _, _, v in spec["points"]):
        return
    c = config.CHART
    data = pd.DataFrame(spec["points"], columns=[spec["x"], "Series", "Value"])
    pct = spec.get("unit") == "percent"
    fmt = ".1f" if pct else "$,.0f" if spec.get("unit") in ("dollars", "average") else ",.0f"
    color = alt.Color("Series:N", scale=alt.Scale(range=c["palette"]), legend=alt.Legend(title=None, orient="bottom"))
    order = list(dict.fromkeys(data[spec["x"]]))
    if spec["kind"] == "line":                          # a gap stays a gap: missing years break the line
        graph = alt.Chart(data).mark_line(point=alt.OverlayMarkDef(size=c["point_size"]), strokeWidth=c["line_width"],
                                          invalid="break-paths-show-domains").encode(
            x=alt.X(f"{spec['x']}:O", sort=order, title=None), y=alt.Y("Value:Q", title=None, axis=alt.Axis(format=fmt)),
            color=color, tooltip=[spec["x"], "Series", alt.Tooltip("Value:Q", format=fmt)])
    else:
        graph = alt.Chart(data.dropna()).mark_bar(color=c["palette"][0]).encode(
            y=alt.Y(f"{spec['x']}:N", sort=order, title=None), x=alt.X("Value:Q", title=None, axis=alt.Axis(format=fmt)),
            tooltip=[spec["x"], alt.Tooltip("Value:Q", format=fmt)])
    graph = graph.properties(width="container").configure(font=c["font"]).configure_axis(
        labelFontSize=c["font_size"], titleFontSize=c["font_size"], labelColor=c["text"], titleColor=c["text"],
        gridColor=c["grid"], domainColor=c["domain"]).configure_legend(labelFontSize=c["font_size"]).configure_view(stroke=None)
    st.altair_chart(graph, width="stretch")


def number_tile(t):
    """The single-number tile: the figure large, with its label, school or group, and period."""
    if t:
        st.metric(label=t["label"], value=t["value"])
        st.caption(" · ".join(x for x in (t["who"], t["period"]) if x))


def written_summary(page):
    """The summary under the table: streamed as it is written, then kept only if every number checks out."""
    if page.get("summary_pending"):
        page["summary_pending"] = False
        box = st.empty()
        box.caption(answer.status("writing"))
        so_far = []
        def show_piece(piece):
            so_far.append(piece)
            box.markdown("".join(so_far))
        page["summary"] = answer.summarize(page, s.conversation, log, model=s.model, on_text=show_piece)
        if page["summary"]:
            box.markdown(page["summary"])
        else:                                           # dropped: a number was not in the table (logged)
            box.empty()
    elif page.get("summary"):
        st.markdown(page["summary"])


def show_answer(page, key, latest=False):
    st.markdown(f"**Interpreted as:** {page['interpreted']}")
    for w in page["warnings"]:
        st.warning(w)
    if page.get("message"):
        st.markdown(page["message"])
    number_tile(page.get("tile"))
    table(page["table"])
    written_summary(page)
    chart(page.get("chart"))
    for n in page["notes"]:
        st.caption(n)
    if latest:
        for i, label in enumerate(page.get("offers") or []):
            if st.button(label, key=f"f{key}.{i}"):
                s.turns.append((f"[{label}]", answer.take_offer(i, s.conversation, log)))
                st.rerun()
    if page.get("data_release"):
        st.caption(page["data_release"])
    if (page["counts"]["rows"] or page["status"]) and st.checkbox("Show underlying counts and data status", key=f"c{key}"):
        table(page["counts"])
        for line in page["status"]:
            st.caption(line)
    if page["definitions"]:
        with st.expander("Definitions & sources"):
            for d in page["definitions"]:
                st.markdown(f"**{d['measure']}**  \nScope: {d['scope']}  \nPeriod: {d['period']}  \n"
                            f"Definition: {d['definition']}  \nCalculation: {d['calculation']}  \nSource tables: {d['sources']}"
                            + (f"  \nNote on words: {d['notes']}" if d["notes"] else ""))


def show(page, key, latest):
    if page["kind"] == "many":
        for i, p in enumerate(page["pages"]):
            show(p, f"{key}.{i}", latest and i == len(page["pages"]) - 1)
    elif page["kind"] == "answer":
        show_answer(page, key, latest)
    elif page["kind"] == "clarify":
        st.markdown(page["message"])
        if latest:
            for i, label in enumerate(page["options"]):
                if st.button(label, key=f"o{key}.{i}"):
                    s.turns.append((f"[{label}]", answer.choose(i, s.conversation, log)))
                    st.rerun()
    elif page["kind"] == "picker":
        st.markdown(page["message"])
        if latest and page["candidates"]:
            labels = {label: unitid for unitid, label in page["candidates"]}
            pick = st.selectbox("School", list(labels), key=f"p{key}")
            if st.button("Use this school", key=f"b{key}"):
                s.turns.append((f"[{pick}]", answer.pick_school(labels[pick], s.conversation, log)))
                st.rerun()
    else:
        st.info(page["message"])


for i, (question, page) in enumerate(s.turns):
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        show(page, i, latest=(i == len(s.turns) - 1))

question = st.chat_input("Ask a question about U.S. colleges")
if question:
    with st.status(answer.status("finding")) as box:     # the status line: each step in plain words
        page = answer.ask(question, s.conversation, log, model=s.model,
                          progress=lambda step: box.update(label=answer.status(step)))
        box.update(state="complete")
    for p in page.get("pages") or [page]:               # the summary is written under the table, once
        p["summary_pending"] = s.summary_on and p["kind"] == "answer" and bool((p.get("table") or {}).get("rows"))
    s.turns.append((question, page))
    st.rerun()
