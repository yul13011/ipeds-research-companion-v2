"""How one answer is shown, and the codebook records of the definitions browser (Part 6b).

Version 1's look (agent-redesign/prototype/components.py and ui.py render_answer, 2026-11-26): "Interpreted as" as a
grey caption, the summary above the result, warnings, the single-number tile, the "Display table" switch, the table,
"Show underlying counts and data status", the chart, and the "Definitions & sources" popover. Every figure is
version 2's own: the page object from path/answer.py, unchanged. Version 2's own elements (statements, provisional
notes, the data-release line, offer buttons) use version 1's caption, warning and button styles only.
"""
import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import config
from path import answer
from path.log import Log

SCRIPT = (Path(__file__).parent / 'transcript_scroll.js').read_text(encoding='utf-8')


def render(request, editing=False):
    """Version 1's transcript scrolling: keeps the newest answer in view."""
    settings = json.dumps({'request': int(request), 'editing': bool(editing)})
    with st.container(key='transcript_scroll_driver'):
        st.html('<script>' + SCRIPT + '\nwindow.ipedsTranscriptScroll.update(' + settings + ');</script>', unsafe_allow_javascript=True)


def _md(text):
    """Escape dollar signs, so currency is not read as mathematics (version 1's reason)."""
    return (text or '').replace('$', '\\$')


def frame(part):
    return pd.DataFrame(part['rows'], columns=part['columns'])


def has_chart(spec):
    return bool(spec) and any(v is not None for _, _, v in spec['points'])


def chart(spec):
    """The automatic chart: a line over the years for a trend, bars for a comparison in one year (Part 5c)."""
    c = config.CHART
    data = pd.DataFrame(spec['points'], columns=[spec['x'], 'Series', 'Value'])
    fmt = '.1f' if spec.get('unit') == 'percent' else '$,.0f' if spec.get('unit') in ('dollars', 'average') else ',.0f'
    color = alt.Color('Series:N', scale=alt.Scale(range=c['palette']), legend=alt.Legend(title=None, orient='bottom'))
    order = list(dict.fromkeys(data[spec['x']]))
    if spec['kind'] == 'line':                          # a gap stays a gap: missing years break the line
        graph = alt.Chart(data).mark_line(point=alt.OverlayMarkDef(size=c['point_size']), strokeWidth=c['line_width'],
                                          invalid='break-paths-show-domains').encode(
            x=alt.X(f"{spec['x']}:O", sort=order, title=None), y=alt.Y('Value:Q', title=None, axis=alt.Axis(format=fmt)),
            color=color, tooltip=[spec['x'], 'Series', alt.Tooltip('Value:Q', format=fmt)])
    else:
        graph = alt.Chart(data.dropna()).mark_bar(color=c['palette'][0]).encode(
            y=alt.Y(f"{spec['x']}:N", sort=order, title=None), x=alt.X('Value:Q', title=None, axis=alt.Axis(format=fmt)),
            tooltip=[spec['x'], alt.Tooltip('Value:Q', format=fmt)])
    graph = graph.properties(width='container').configure(font=c['font']).configure_axis(
        labelFontSize=c['font_size'], titleFontSize=c['font_size'], labelColor=c['text'], titleColor=c['text'],
        gridColor=c['grid'], domainColor=c['domain']).configure_legend(labelFontSize=c['font_size']).configure_view(stroke=None)
    st.altair_chart(graph, width='stretch')


def written_summary(page, model):
    """The summary: streamed as it is written, then kept only if every number checks out (Part 5e)."""
    if page.get('summary_pending'):
        page['summary_pending'] = False
        box = st.empty()
        with st.spinner(answer.status('writing')):
            so_far = []
            def show_piece(piece):
                so_far.append(piece)
                box.markdown(_md(''.join(so_far)))
            conversation = st.session_state.get('conversation', {})
            page['summary'] = answer.summarize(page, conversation, Log(), model=model, on_text=show_piece)
        if page['summary']: box.markdown(_md(page['summary']))
        else: box.empty()                               # dropped: a number was not in the table (logged)
    elif page.get('summary'):
        st.markdown(_md(page['summary']))


def definitions_popover(page):
    with st.popover('Definitions & sources'):
        for d in page['definitions']:
            st.markdown('**' + d['measure'] + '**')
            st.write('Scope: ' + d['scope']); st.write('Reporting period: ' + d['period'])
            st.write(_md(d['definition']))
            if d['calculation']: st.write('Calculation: ' + _md(d['calculation']))
            st.caption('Source tables: ' + d['sources'])
            if d['notes']: st.caption('Note on words: ' + d['notes'])


def render_result(page, key, latest, on_button):
    for warning in page['warnings']: st.warning(_md(warning))
    t = page.get('tile')
    if t:
        st.metric(label=t['label'], value=t['value'])
        st.caption(' · '.join(x for x in (t['who'], t['period']) if x))
    spec = page.get('chart')
    charted = has_chart(spec)
    if page['table']['rows']:
        # "Display table": off by default when a chart is shown, on when there is none (owner decision, 2026-11-26)
        if st.toggle('Display table', value=not charted, key=key + '_table'):
            st.dataframe(frame(page['table']), hide_index=True, width='stretch')
            if (page['counts']['rows'] or page['status']) and st.checkbox('Show underlying counts and data status', key=key + '_counts'):
                if page['counts']['rows']: st.dataframe(frame(page['counts']), hide_index=True, width='stretch')
                for line in page['status']: st.caption(_md(line))
    if charted: chart(spec)
    for note in page['notes']: st.caption(_md(note))
    if page.get('data_release'): st.caption(page['data_release'])
    if latest:
        for i, label in enumerate(page.get('offers') or []):
            st.button(label, key=key + f'_offer_{i}', on_click=on_button, args=('offer', i, label))
    if page['definitions']:
        with st.container(horizontal=True):
            definitions_popover(page)


def render_answer(page, key, latest=False, on_button=None, model=None, number=None):
    kind = page['kind']
    if kind == 'many':                                  # several answers in one turn: numbered, as version 1's tasks
        for i, part in enumerate(page['pages'], 1):
            render_answer(part, f'{key}_task_{i}', latest and i == len(page['pages']), on_button, model, number=i)
        return
    if kind == 'answer':
        if number: st.markdown(f'**{number}. {_md(page["interpreted"])}**')
        else: st.caption('Interpreted as: ' + _md(page['interpreted']))
        if page.get('message'): st.write(_md(page['message']))
        above = st.container()                          # the summary sits above the result, as in version 1, but is
        render_result(page, key, latest, on_button)     # written after it, so the table never waits for the summary
        with above: written_summary(page, model)
    elif kind == 'clarify':
        st.write(_md(page['message']))
        if latest and page['options']:
            for i, (col, label) in enumerate(zip(st.columns(len(page['options'])), page['options'])):
                col.button(label, key=key + f'_choice_{i}', on_click=on_button, args=('option', i, label))
            st.caption('Choose an option, or type a change to refine it.')
    elif kind == 'picker':
        render_picker(page, key, latest, on_button)
    else:                                               # a decline or a short reply: plain text, as in version 1
        st.write(_md(page['message']))


def render_picker(page, key, latest, on_button):
    """Version 1's school confirmation: a dropdown, a refine box, Continue and Cancel."""
    st.write(_md(page['message']))
    if not latest: return
    s = st.session_state
    st.write('Institution: ' + page['name'])
    selector = st.empty()
    refine = st.text_input('None of these? Refine by name, city/state or UNITID', key=key + '_refine')
    options = dict(page['candidates'])
    if refine.strip():
        from path import shortlist
        options = {c['id']: f"{c['name']} ({c['city']}, {c['state']})" for c in shortlist.search_schools(refine, config.LOCAL_DB.as_posix())}
    if not options: st.caption('No plausible matches. Enter a fuller name, location or UNITID above.')
    chosen = selector.selectbox('Which institution did you mean?', list(options), index=None, placeholder='Select an institution',
                                format_func=lambda u: options[u], key=key + '_choice_' + refine)
    a, b = st.columns(2)
    if a.button('Continue', key=key + '_continue'):
        if chosen is None: st.warning('Select an institution for each name, or refine the search.')
        else: on_button('school', chosen, options[chosen]); st.rerun()
    if b.button('Cancel', key=key + '_cancel'):
        answer.cancel(s.conversation)
        s.turns[-1] = (s.turns[-1][0], dict(kind='decline', message='Cancelled. No analysis ran.'))
        s.transcript_revision += 1; st.rerun()


def render_evidence(records, key, say):
    """The definitions browser's results: version 1's table, then one record's full definition and code labels."""
    from tools import codebook
    if not records: st.info('No matching source records. Try a shorter topic or an exact variable name.'); return
    st.caption(say('evidence_caption'))
    from tools import about
    folder = {year: release for year, release, _ in about.releases()}   # version 1 shows the release folder's name
    display = pd.DataFrame([{'Source release': folder.get(r['year'], r['release']), 'Record type': codebook.KINDS[r['kind']], 'Table': r['table'],
                             'Variable': r['variable'] or '', 'Description': r['title']} for r in records])
    st.dataframe(display, hide_index=True, width='stretch')
    st.caption(f'Showing {len(records)} ranked records. Choose one to read its full definition and any coded categories.')
    chosen = st.selectbox('Read a definition', range(len(records)),
                          format_func=lambda n: f"{records[n]['variable'] or records[n]['table']} — {records[n]['title']} ({records[n]['release']})",
                          key=key + '_selected_record')
    r = records[chosen]
    st.markdown(f"**{r['title']}**")
    st.write(_md(r['text']))
    codes = codebook.detail(r)
    if codes:
        st.write('**Coded categories**')
        st.dataframe(pd.DataFrame(codes, columns=['Code', 'Meaning']), hide_index=True, width='stretch')
    with st.expander('Original source reference'):
        st.write(f"Table: {r['table'] or '—'} · Variable: {r['variable'] or '—'}")
        st.caption(say('source_reference', release=r['release']))
