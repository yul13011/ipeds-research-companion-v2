"""Explore IPEDS, the conversation, the definitions browser and About (Part 6b).

Copied from version 1 (agent-redesign/prototype/ui.py, 2026-11-26): its layout, CSS, labels and wording as they are.
Only the data calls are version 2's: path/answer.py for questions and buttons, tools/ for the codebook search, the
releases held and the benchmark rates. Left out, as approved: the extract builder (Stage 7), the AI switch, the
developer settings, and the model-usage panel of the extract builder.
"""
import json
import uuid
from contextlib import contextmanager
from pathlib import Path

import streamlit as st

import config
from page.components import render_answer, render_evidence
from path import answer
from path.log import Log
from tools import about, codebook

HERE = Path(__file__).parent
WORDING = json.loads((HERE / "wording.json").read_text(encoding="utf-8"))
MODEL_OPTIONS = {model: name for name, model in config.MODELS.items()}


def say(key, **fill):
    return WORDING[key].format(**fill)


def topics():
    return json.loads((HERE / "explore.json").read_text(encoding="utf-8"))["topics"]


def example_by_id(example_id):
    for topic in topics():
        for example in topic["examples"]:
            if example["id"] == example_id:
                return example
    raise ValueError("Unknown example.")


def navigate(page='Ask & Analyze', tool=None):
    st.session_state.main_page = page; st.session_state.active_tool = tool


def copy_widget(widget, target): st.session_state[target] = st.session_state[widget]
def open_topic(topic):
    st.session_state.topic_id = topic; st.session_state.topic_open = True
def close_topic(): st.session_state.topic_open = False
def toggle_panel(panel): st.session_state[panel] = not st.session_state[panel]
def queue_example(example_id):
    """An example question is sent to the chat as if typed (owner decision, 2026-11-26)."""
    st.session_state.pending_action = {'type': 'question', 'question': example_by_id(example_id)['question']}; navigate()


def queue_button(kind, index, label):
    """An option, an offer or a picked school: run by the question path with no model call."""
    st.session_state.pending_action = {'type': kind, 'index': index, 'question': f'[{label}]'}


def clear_conversation():
    s = st.session_state; s.conversation = {}; s.turns = []; s.pending_action = None; s.transcript_revision += 1
    s.pop('request_error', None)


def show_work_status(slot, message):
    slot.caption(message)


@contextmanager
def working_status():
    slot = st.empty()
    try:
        with st.spinner(''):
            yield lambda step: show_work_status(slot, answer.status(step))
    finally: slot.empty()


def run_pending():
    """Runs the waiting question or button, and keeps the turn. A failure leaves no partial result: the turn is not
    kept and a friendly message is shown at the top of the chat, as in version 1."""
    s = st.session_state; pending = s.get('pending_action')
    if not pending: return
    s.pop('request_error', None)
    log = Log()
    try:
        with working_status() as progress:
            progress('finding')
            if pending['type'] == 'question':
                page = answer.ask(pending['question'], s.conversation, log, model=s.model_choice, progress=progress)
            elif pending['type'] == 'option':
                page = answer.choose(pending['index'], s.conversation, log)
            elif pending['type'] == 'offer':
                page = answer.take_offer(pending['index'], s.conversation, log)
            else:
                page = answer.pick_school(pending['index'], s.conversation, log)
        if page.get('error'):
            s.request_error = say('error_' + page['error'], seconds=int(config.CALL_SECONDS))
        else:
            for p in page.get('pages') or [page]:       # the summary is written under the table, once
                p['summary_pending'] = (config.SUMMARY and p['kind'] == 'answer' and bool((p.get('table') or {}).get('rows'))
                                        and p.get('operation') not in ('define', 'data_exists'))
            s.turns = (s.turns + [(pending['question'], page)])[-30:]
            s.transcript_revision += 1
    except Exception as exc:                            # an app fault: logged, never shown in detail
        s.request_error = say('error_app')
        log.question(dict(question=pending.get('question'), outcome='error_app', error=f'{type(exc).__name__}: {exc}'))
    s.pending_action = None


def example_buttons(topic, prefix, compact=False):
    for ex in topic['examples']:
        with st.container(key='example_row_' + prefix + '_' + ex['id']):
            if compact:
                st.caption(ex['purpose'].upper())
                st.button(ex['question'], key=prefix + '_' + ex['id'], on_click=queue_example, args=(ex['id'],), width='stretch')
            else:
                category, question = st.columns([1, 4], vertical_alignment='center')
                category.caption(ex['purpose'].upper())
                question.button(ex['question'], key=prefix + '_' + ex['id'], on_click=queue_example, args=(ex['id'],), width='stretch')


def render_ideas():
    s = st.session_state; content = topics(); mapping = {t['id']: t for t in content}
    with st.container(border=True, key='ideas_panel', height='stretch'):
        title, collapse = st.columns([5, 1], vertical_alignment='center')
        title.subheader('Need ideas?')
        collapse.button('‹', key='collapse_ideas', on_click=toggle_panel, args=('ideas_open',), help='Collapse ideas panel')
        st.caption('Choose a topic, then try a sample question.')
        selected = st.selectbox('Choose a topic', list(mapping), index=list(mapping).index(s.topic_id), format_func=lambda t: mapping[t]['subtitle'], key='ideas_topic_widget', on_change=copy_widget, args=('ideas_topic_widget', 'topic_id'))
        example_buttons(mapping[selected], 'ideas', compact=True)


def render_topic_detail(topic, prefix):
    with st.container(border=True, key='topic_details_' + prefix):
        heading, close = st.columns([20, 1], vertical_alignment='center')
        heading.subheader(topic['title'] if topic['title'].casefold() == topic['subtitle'].casefold() else topic['title'] + ' · ' + topic['subtitle'])
        close.button('×', key='close_topic_' + prefix, on_click=close_topic, help='Close topic')
        st.write(topic['description']); st.info(topic['scope'])
        example_buttons(topic, 'home_' + prefix)
        st.button('Ask your own question about ' + topic['subtitle'].lower(), key='home_own_' + prefix, on_click=navigate)


def render_home():
    s = st.session_state
    st.title('Discover what college data can tell you')
    st.write('Explore admissions, enrollment, costs, outcomes, and more using federal IPEDS data.')
    st.button('Ask a question →', type='primary', key='home_ask', on_click=navigate)
    st.caption(about.releases_line())
    st.subheader('Start with a topic'); st.write('Choose a topic to learn what is available and find questions to try.')
    content = topics()
    # The detail panel renders in two positions: inside the open card's column (shown on mobile) and full-width
    # after the row (shown on laptop). CSS shows only the copy that fits the screen width.
    st.html('<style>@media(max-width:750px){.st-key-topic_details_d{display:none!important}}@media(min-width:751px){.st-key-topic_details_m{display:none!important}}</style>')
    for start in [0, 3]:
        for col, topic in zip(st.columns(3), content[start:start + 3]):
            with col:
                with st.container(border=True, key='home_card_' + topic['id'], height='stretch' if start == 0 else 'content'):
                    st.subheader(topic['icon'] + ' ' + topic['title']); st.caption(topic['subtitle']); st.write(topic['summary'])
                    st.button('Explore topic →', key='topic_' + topic['id'], on_click=open_topic, args=(topic['id'],))
                if s.topic_open and s.topic_id == topic['id']: render_topic_detail(topic, 'm')
        if s.topic_open and s.topic_id in [t['id'] for t in content[start:start + 3]]:
            render_topic_detail(next(t for t in content if t['id'] == s.topic_id), 'd')
    st.caption('IPEDS is collected by the National Center for Education Statistics. Explore all supplied topics; Ask & Analyze can answer additional questions when their source definitions and calculations can be verified.')


def render_chat():
    s = st.session_state
    pending = s.get('pending_action')
    if pending and 'scroll_request' not in pending:
        s.scroll_request_serial = s.get('scroll_request_serial', 0) + 1
        pending['scroll_request'] = s.scroll_request_serial
    pending_slot = None
    heading, control = st.columns([8.5, 1.5], vertical_alignment='top')
    with heading.container(key='chat_heading'):
        st.title('What would you like to learn?')
    control.button('Hide Menu' if s.app_banner_open else 'Expand Menu', icon=':material/keyboard_arrow_up:' if s.app_banner_open else ':material/keyboard_arrow_down:', icon_position='right', key='hide_app_banner' if s.app_banner_open else 'show_app_banner', on_click=toggle_panel, args=('app_banner_open',), help='Collapse header and introduction' if s.app_banner_open else 'Expand header and introduction')
    with st.container(key='chat_introduction'):
        st.write('Ask about one or many institutions, for one year, selected years, or a range.')
    st.markdown('<div class="intro-rule"></div>', unsafe_allow_html=True)
    with st.container(key='panel_restore_controls'):
        controls_left, controls_right = st.columns(2)
        if not s.ideas_open: controls_left.button('› Ideas', key='show_ideas', on_click=toggle_panel, args=('ideas_open',))
        if config.TOOLS_PANEL and not s.tools_open:
            with controls_right.container(horizontal=True, horizontal_alignment='right'):
                st.button('Tools ‹', key='show_tools', on_click=toggle_panel, args=('tools_open',))
    # Keep column identities/positions fixed across reruns.
    with st.container(key='panel_visibility'):
        hidden = []
        if not s.ideas_open: hidden.append('[data-testid="stColumn"]:has(.st-key-ideas_panel)')
        if not s.tools_open: hidden.append('[data-testid="stColumn"]:has(.st-key-tools_panel)')
        st.html('<style>' + (','.join(hidden) + '{display:none!important}' if hidden else '') + '</style>')
    panels = st.columns([1, 4.5, 1] if config.TOOLS_PANEL else [1, 5.5], gap='medium')   # tools hidden until Stage 7
    with panels[0]: render_ideas()
    with panels[1], st.container(key='chat_workspace', height='stretch'):
        if s.get('request_error'): st.error(s.request_error)
        from page.components import render as scroll_transcript
        scroll_transcript(s.get('scroll_request_serial', 0))
        with st.container(height=500, border=False, key='conversation_messages', autoscroll=False):
            for i, (question, page) in enumerate(s.turns):
                with st.chat_message('user'): st.write(question)
                with st.chat_message('assistant'):
                    render_answer(page, f'answer_{s.transcript_revision}_{i}', latest=(i == len(s.turns) - 1 and not pending),
                                  on_button=queue_button, model=s.model_choice)
            if pending:
                with st.chat_message('user'): st.write(pending['question'])
                pending_slot = st.empty()
        with st.container(horizontal=True, vertical_alignment='center', gap='small', key='chat_composer'):
            question = st.chat_input('Ask a follow-up question…' if s.turns else 'Ask a question about IPEDS data…', max_chars=4000, key='followup_question' if s.turns else 'initial_question', disabled=bool(pending))
            if s.turns or s.get('request_error'):
                st.button('Clear conversation', key='clear_chat', type='tertiary', icon=':material/delete_sweep:', on_click=clear_conversation, disabled=bool(pending), help='Clear messages, errors and remembered conversation choices.')
        if question and question.strip(): s.pending_action = {'type': 'question', 'question': question}; st.rerun()
        if not s.turns:
            st.caption(say('empty_chat_caption', model=MODEL_OPTIONS.get(s.model_choice, s.model_choice)))
    if config.TOOLS_PANEL:
        with panels[-1], st.container(border=True, key='tools_panel'):
            title, collapse = st.columns([5, 1], vertical_alignment='center')
            title.subheader('Analysis tools')
            collapse.button('›', key='collapse_tools', on_click=toggle_panel, args=('tools_open',), help='Collapse analysis tools panel')
            render_tools()
    if pending_slot is not None:
        # Redraw the whole workspace before a slow call; the spinner stays in the assistant's bubble.
        with pending_slot.container(), st.chat_message('assistant'):
            run_pending()
        st.rerun()


def render_tools():
    """The definitions browser, shown to everyone (owner decision, 2026-11-26). No extract builder until Stage 7."""
    s = st.session_state
    with st.container():
        st.caption(say('tools_caption'))
        with st.container(border=True, key='definitions_tool', gap='small'):
            st.markdown('<div class="tool-card-copy"><h3>Browse definitions</h3><p>Find source tables, variables, and definitions in the IPEDS codebooks.</p></div>', unsafe_allow_html=True)
            st.button('Search definitions →', key='open_definitions', on_click=navigate, args=('Ask & Analyze', 'definitions'), width='stretch')
        st.caption('Your conversation is preserved when you open a tool.')
        if s.turns: st.button('New conversation', key='new_conversation', on_click=clear_conversation)


def render_definitions():
    s = st.session_state
    st.button('← Back to conversation', key='definitions_back', on_click=navigate)
    st.title('Browse definitions'); st.write(say('definitions_intro'))
    years = [y for y, _, _ in about.releases()]
    with st.form('codebook_search_form'):
        query = st.text_input('Topic, table, or variable name', value='graduate enrollment', key='codebook_search_query', max_chars=4000)
        chosen = st.multiselect('Release years (empty = all ten)', years, default=[years[-1]], key='codebook_search_years')
        include = st.checkbox(say('codes_checkbox'), key='codebook_search_other')
        submitted = st.form_submit_button('Search codebooks')
    if submitted:
        s.pop('codebook_search_result', None)
        if not query.strip(): st.info('Enter a topic, table, or variable name.')
        else:
            try: s.codebook_search_result = {'query': query, 'records': codebook.search(query, chosen, 40, codes=include)}
            except Exception: st.error('The local catalog search could not finish. Try a narrower query.')
    if 'codebook_search_result' in s:
        r = s.codebook_search_result; st.write('**Results for ' + r['query'] + '**')
        render_evidence(r['records'], 'codebook_browse', say)


def render_about():
    s = st.session_state
    st.button('← Back to conversation', key='about_back', on_click=navigate)
    held = about.releases()
    st.title('About this prototype'); st.write(say('about_intro'))
    first, last = held[0][0], held[-1][0]
    st.info(f'Local source releases: {first}–{(first + 1) % 100:02d} through {last}–{(last + 1) % 100:02d}; latest release {held[-1][2]}. Observation periods and entering cohorts vary by survey. Verified national and sector aggregates are available; unresolved methods remain under review.')
    st.subheader('Model settings')
    st.selectbox('Model strategy', list(MODEL_OPTIONS), index=list(MODEL_OPTIONS).index(s.model_choice), format_func=lambda x: MODEL_OPTIONS[x], key='settings_model', on_change=copy_widget, args=('settings_model', 'model_choice'))
    st.caption(say('model_caption'))
    st.caption(say('ai_caption'))
    st.subheader('Privacy')
    st.caption('To help improve the prototype, each question and whether it could be answered is saved to a private analytics log. A random session id groups the questions from one visit but identifies no one. Please don’t enter personal information.')
    st.subheader('Evaluation and coverage')
    st.write('We benchmark the app against two independent published sources — Yale University’s official figures and NCES national and sector aggregates — comparing retrieved values cell by cell.')
    suites = about.match_rates()
    if suites:
        cols = st.columns(len(suites))
        for col, (label, desc, m, total) in zip(cols, suites):
            col.metric(f'{label} match rate', f'{round(100 * m / total)}%' if total else '—')
            col.caption(f'{m:,} of {total:,} {desc} matched')
        st.caption(say('benchmark_caption'))


STYLES = (HERE / "styles.css").read_text(encoding="utf-8")


def main():
    st.set_page_config(page_title='IPEDS Research Companion', page_icon='📚', layout='wide', initial_sidebar_state='collapsed')
    page_styles = '''[data-testid="stMainBlockContainer"]{max-width:none;padding-left:2rem;padding-right:2rem}
    @media(max-width:750px){[data-testid="stMainBlockContainer"]{padding-left:1rem;padding-right:1rem}}''' if st.session_state.get('main_page') == 'Ask & Analyze' else ''
    st.markdown('<style>' + STYLES + page_styles + '</style>', unsafe_allow_html=True)
    if not config.LOCAL_DB.exists(): st.error(say('error_database')); st.stop()
    s = st.session_state
    defaults = {'main_page': 'Explore IPEDS', 'app_banner_open': True, 'transcript_revision': 0, 'turns': [], 'conversation': {},
                'topic_id': 'admissions', 'topic_open': False, 'active_tool': None, 'pending_action': None,
                'model_choice': config.INTERPRET_MODEL if config.INTERPRET_MODEL in MODEL_OPTIONS else next(iter(MODEL_OPTIONS)),
                'session_id': str(uuid.uuid4())}
    for k, v in defaults.items():
        if k not in s: s[k] = v
    for panel in ['ideas_open', 'tools_open']:
        if panel not in s: s[panel] = True
    is_chat = s.main_page == 'Ask & Analyze' and not s.active_tool
    # A persistent header boundary prevents downstream blocks shifting on collapse.
    with st.container(key='app_header'):
        if is_chat or s.app_banner_open or s.main_page == 'Explore IPEDS':
            brand, nav, about_col, collapse = st.columns([4, 4, 2, .5], vertical_alignment='top')
            with brand: st.markdown('<div class="brand">IPEDS Research Companion<span class="eyebrow">Beta</span></div>', unsafe_allow_html=True)
            with nav:
                with st.container(key='main_navigation'):
                    for col, page, key in zip(st.columns(2), ['Explore IPEDS', 'Ask & Analyze'], ['nav_explore', 'nav_ask']):
                        col.button(page, key=key, on_click=navigate, args=(page,), type='primary' if s.main_page == page else 'secondary', width='stretch')
            with about_col: st.button('About this prototype', key='nav_about', on_click=navigate, args=('Ask & Analyze', 'about'), width='stretch')
            if not is_chat and s.main_page != 'Explore IPEDS':
                collapse.button('⌃', key='hide_app_banner', on_click=toggle_panel, args=('app_banner_open',), help='Collapse header and introduction')
            st.markdown('<div class="banner-rule"></div>', unsafe_allow_html=True)
        elif not is_chat:
            _, _, _, restore = st.columns([4, 4, 2, .5], vertical_alignment='top')
            restore.button('⌄', key='show_app_banner', on_click=toggle_panel, args=('app_banner_open',), help='Expand header and introduction')
    if s.main_page == 'Explore IPEDS': render_home()
    elif s.active_tool == 'definitions': render_definitions()
    elif s.active_tool == 'about': render_about()
    else: render_chat()
