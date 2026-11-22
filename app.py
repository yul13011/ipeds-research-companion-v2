"""The chat page for the first slice of version 2. Run: streamlit run app.py

The page only displays what path/answer.py returns. It holds the conversation in the session:
the requests answered so far, any options or school picker waiting for the user.
"""
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
    st.caption("Version 2. Ten IPEDS releases are loaded (2015-16 to 2024-25); answers use the latest year until "
               "trend questions are added.")
    names = list(config.MODELS)
    default = next((n for n, m in config.MODELS.items() if m == config.INTERPRET_MODEL), names[0])
    s.model = config.MODELS[st.selectbox("Model for reading questions", names, index=names.index(default))]
    if st.button("Clear conversation"):
        s.conversation, s.turns = {}, []
        st.rerun()


def table(part):
    if part["rows"]:
        st.dataframe(pd.DataFrame(part["rows"], columns=part["columns"]), hide_index=True, width="stretch")


def show_answer(page, key):
    st.markdown(f"**Interpreted as:** {page['interpreted']}")
    for w in page["warnings"]:
        st.warning(w)
    if page.get("message"):
        st.markdown(page["message"])
    table(page["table"])
    for n in page["notes"]:
        st.caption(n)
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
            show(p, f"{key}.{i}", False)
    elif page["kind"] == "answer":
        show_answer(page, key)
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
    with st.spinner("Reading the question"):
        s.turns.append((question, answer.ask(question, s.conversation, log, model=s.model)))
    st.rerun()
