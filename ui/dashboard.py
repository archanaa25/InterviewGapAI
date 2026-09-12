"""
Evaluation dashboard for the interviewer view.

Charts are Altair (already a Streamlit dependency - no new package). Every
panel pairs a chart with the table behind it, because the per-query-type
detail is where the interesting failures live and a bar chart cannot show it.

Colour rules followed here:
  - The metric triad is a fixed categorical order, never cycled, and was
    checked with the dataviz validator: worst adjacent pair ΔE 24.7 under
    protanopia, all six checks pass on this surface.
  - Latency never shares an axis with a quality percentage. Two scales on one
    plot is the one chart mistake worth refusing outright, so latency is a
    table column and a caption, not a second y-axis.
  - Values stay in ink; colour beside them carries series identity.
"""

from __future__ import annotations

import html

import altair as alt
import pandas as pd
import streamlit as st

from ui import eval_reports as reports


# Validated categorical triad (see module docstring).
METRIC_COLORS = ["#2a78d6", "#eb6834", "#4a3aa7"]
METRIC_ORDER = ["Recall@1", "MRR", "NDCG@5"]

SINGLE_SERIES = "#2a78d6"
NEGATIVE_SERIES = "#eda100"
CHART_SURFACE = "#ffffff"

# Competencies wear a fixed identity hue across the product - the same hue the
# candidate's plan cards use - so colouring these bars follows the entity
# rather than its rank. That is the one legitimate reason to colour a nominal
# bar chart: a value-ramp keyed to bar height would be double-encoding.
#
# Validated in this chart's sort order, which matters: the shipped amber for
# ai_evaluation sat ΔE 13.7 from agentic_ai's orange once the two became
# adjacent here, under the hard floor of 15. The orange is re-stepped to
# #e2572a for charts; all six checks then pass.
COMPETENCY_HUES = {
    "RAG": "#2a78d6",
    "Agentic AI": "#e2572a",
    "AI Evaluation": "#eda100",
    "LLM Fundamentals": "#1baf7a",
    "Python / SWE": "#e87ba4",
    "AI System Design": "#008300",
    "AI Security": "#4a3aa7",
}

# Difficulty is an ordered tier, so it takes a single-hue light-to-dark ramp,
# validated with --ordinal. A categorical set here would imply the three are
# unrelated; a ramp says basic < intermediate < advanced.
DIFFICULTY_RAMP = {
    "Basic": "#74b5e2",
    "Intermediate": "#2f7cc0",
    "Advanced": "#10517f",
}

# Question types have no identity elsewhere in the product and no order, so
# these are plain categorical slots, assigned in fixed order and never cycled.
QUESTION_TYPE_HUES = {
    "Conceptual": "#2a78d6",
    "Design": "#eb6834",
    "Troubleshooting": "#4a3aa7",
    "Scenario": "#008300",
}

# Concept-coverage is a state, not a series: reserved status hues.
COVERAGE_COLORS = {"Covered": "#008300", "Partial": "#eda100", "Not Covered": "#c2402a"}


def _no_data(what: str) -> None:
    st.info(f"No {what} on disk yet. Run its evaluation script to populate this panel.")


# Four judgement outcomes. Validated with the dataviz palette script: all six
# checks pass, worst adjacent pair ΔE 23.1 normal / 11.9 deutan. An earlier
# red (#c2402a) sat ΔE 11.9 from the orange under normal vision - below the
# hard floor of 15 - so the fourth slot is magenta, not red.
OUTCOME_COLORS = {
    "Correct Evidence": "#008300",
    "Correct Unknown": "#2a78d6",
    "Over Credit": "#eb6834",
    "Under Credit": "#c2185b",
}


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _panel_head(
    icon: str,
    title: str,
    subtitle: str,
    *,
    tint: str = "#eef1fe",
    ink: str = "#4a3aa7",
    stamp: str | None = None,
) -> None:
    """Icon, title pair, and an optional run stamp on the right."""

    stamp_markup = (
        f'<span class="ig-stamp">Last run<b>{_escape(stamp)}</b></span>'
        if stamp
        else ""
    )
    st.markdown(
        '<div class="ig-panel-head">'
        f'<span class="ig-panel-ico" style="background:{tint};color:{ink}">{icon}</span>'
        f'<span class="ig-panel-title"><b>{_escape(title)}</b>'
        f"<i>{_escape(subtitle)}</i></span>"
        f"{stamp_markup}"
        "</div>",
        unsafe_allow_html=True,
    )


def _kpis(cards: list[dict]) -> None:
    """
    A row of KPI cards.

    A card shows a meter only when its value is a real 0-1 fraction. A count
    has no meaningful full-width, so drawing a bar for it would invent one.
    """

    blocks = []
    for card in cards:
        meter = ""
        if card.get("fraction") is not None:
            width = max(0.0, min(1.0, float(card["fraction"]))) * 100
            meter = (
                '<div class="ig-meter-track">'
                f'<div class="ig-meter-fill" style="width:{width:.1f}%;'
                f'background:{card["ink"]}"></div></div>'
            )
        badge = (
            f'<span class="ig-kpi-badge">{_escape(card["badge"])}</span>'
            if card.get("badge")
            else ""
        )
        blocks.append(
            '<div class="ig-kpi"><div class="ig-kpi-top">'
            f'<span class="ig-kpi-ico" style="background:{card["tint"]};'
            f'color:{card["ink"]}">{card["icon"]}</span>'
            f'<span class="ig-kpi-label">{_escape(card["label"])}</span></div>'
            f'<div class="ig-kpi-value">{_escape(card["value"])}</div>'
            f"{meter}{badge}</div>"
        )

    st.markdown(f'<div class="ig-kpis">{"".join(blocks)}</div>', unsafe_allow_html=True)


def _insight(text: str, *, title: str = "Key insight") -> None:
    st.markdown(
        '<div class="ig-insight"><span class="ig-insight-ico">◐</span>'
        f"<span><b>{_escape(title)}</b><span>{_escape(text)}</span></span></div>",
        unsafe_allow_html=True,
    )


def _donut(frame: pd.DataFrame, *, name: str, value: str, colors: dict) -> alt.Chart:
    """
    Part-to-whole for a handful of segments.

    Legitimate here because there are four segments and the exact counts and
    shares are direct-labelled in the legend beside it - the arcs give the
    shape, the numbers do the comparing, which is what a donut cannot do when
    two values are close.
    """

    present = [key for key in colors if key in set(frame[name])]

    return (
        alt.Chart(frame)
        .mark_arc(innerRadius=58, outerRadius=92, stroke=CHART_SURFACE, strokeWidth=2)
        .encode(
            theta=alt.Theta(f"{value}:Q", stack=True),
            color=alt.Color(
                f"{name}:N",
                scale=alt.Scale(domain=present, range=[colors[k] for k in present]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip(f"{name}:N", title="Outcome"),
                alt.Tooltip(f"{value}:Q", title="Judgements"),
            ],
        )
        .properties(height=240)
        .configure_view(strokeWidth=0, fill=CHART_SURFACE)
    )


def _legend(rows: list[dict], *, colors: dict, total: int) -> None:
    """Swatch, label, count and share - so identity is never colour alone."""

    body = "".join(
        '<div class="ig-legend-row">'
        f'<span class="ig-legend-dot" style="background:{colors.get(row["outcome"], SINGLE_SERIES)}"></span>'
        f'<span>{_escape(row["outcome"])}</span>'
        f'<span>{row["count"]}</span>'
        f'<span>{(row["count"] / total * 100 if total else 0):.1f}%</span>'
        "</div>"
        for row in rows
    )
    st.markdown(f'<div class="ig-legend">{body}</div>', unsafe_allow_html=True)


def _bar(
    frame: pd.DataFrame,
    *,
    x: str,
    y: str,
    hues: dict[str, str] | None = None,
    sort: list[str] | None = None,
    label_format: str = "d",
    height: int = 290,
) -> alt.LayerChart:
    """
    One categorical bar chart with direct value labels and a recessive axis.

    hues maps category to colour. Every bar is named on the axis and carries
    its value, so the hue reinforces identity rather than carrying it.
    """

    base = alt.Chart(frame).encode(
        # Sorted by value, not alphabetically: the ranking is the message.
        x=alt.X(
            f"{x}:N",
            sort=sort,
            title=None,
            axis=alt.Axis(labelAngle=0, labelLimit=110, grid=False, domainColor="#d9e3ec"),
        ),
        y=alt.Y(
            f"{y}:Q",
            title=None,
            axis=alt.Axis(grid=True, gridColor="#eef3f8", domain=False, tickCount=5),
        ),
    )

    bars = base.mark_bar(
        # 4px rounded data-ends, anchored to the baseline.
        cornerRadiusTopLeft=4,
        cornerRadiusTopRight=4,
        width=alt.RelativeBandSize(0.62),
    )

    if hues:
        present = [key for key in hues if key in set(frame[x])]
        bars = bars.encode(
            color=alt.Color(
                f"{x}:N",
                scale=alt.Scale(domain=present, range=[hues[key] for key in present]),
                # The axis already labels every bar, so a legend box would
                # repeat it.
                legend=None,
            ),
            tooltip=[alt.Tooltip(f"{x}:N", title="Category"),
                     alt.Tooltip(f"{y}:Q", title="Count")],
        )
    else:
        bars = bars.encode(color=alt.value(SINGLE_SERIES))

    labels = base.mark_text(dy=-8, fontSize=11, fontWeight=700, color="#172033").encode(
        text=alt.Text(f"{y}:Q", format=label_format)
    )

    return (bars + labels).properties(height=height).configure_view(
        strokeWidth=0, fill=CHART_SURFACE
    )


def _metric_chart(rows: list[dict], *, height: int = 320) -> alt.LayerChart:
    """Grouped bars for the three quality metrics, ordered by MRR."""

    order = [row["strategy"] for row in rows]

    frame = pd.DataFrame(
        [
            {"strategy": row["strategy"], "metric": metric, "value": row[key] or 0.0}
            for row in rows
            for metric, key in (
                ("Recall@1", "recall_at_1"),
                ("MRR", "mrr"),
                ("NDCG@5", "ndcg_at_5"),
            )
        ]
    )

    base = alt.Chart(frame).encode(
        x=alt.X("strategy:N", sort=order, title=None,
                axis=alt.Axis(labelAngle=0, labelLimit=120, grid=False, domainColor="#d9e3ec")),
        y=alt.Y("value:Q", title=None, scale=alt.Scale(domain=[0, 1]),
                axis=alt.Axis(format="%", grid=True, gridColor="#eef3f8", domain=False)),
        # xOffset gives the 2px surface gap between adjacent fills.
        xOffset=alt.XOffset("metric:N", sort=METRIC_ORDER),
    )

    bars = base.mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        color=alt.Color(
            "metric:N",
            sort=METRIC_ORDER,
            scale=alt.Scale(domain=METRIC_ORDER, range=METRIC_COLORS),
            legend=alt.Legend(orient="top", title=None, direction="horizontal"),
        ),
        tooltip=[
            alt.Tooltip("strategy:N", title="Strategy"),
            alt.Tooltip("metric:N", title="Metric"),
            alt.Tooltip("value:Q", title="Score", format=".1%"),
        ],
    )

    return bars.properties(height=height).configure_view(
        strokeWidth=0, fill=CHART_SURFACE
    )


def _percent_table(rows: list[dict], columns: list[tuple[str, str]]) -> None:
    """The numbers behind a chart, percentages formatted as percentages."""

    frame = pd.DataFrame(rows)[[key for key, _ in columns]]
    frame.columns = [title for _, title in columns]

    percent = [title for key, title in columns if key.startswith(("recall", "mrr", "ndcg"))]
    styler = frame.style.format(
        {**{title: "{:.1%}" for title in percent},
         **({"Latency": "{:,.0f} ms"} if "Latency" in frame.columns else {})}
    )
    st.dataframe(styler, use_container_width=True, hide_index=True)


def _corpus_panel() -> None:
    data = reports.corpus_composition()
    if data is None:
        return _no_data("question corpus")

    top = st.columns(4)
    top[0].metric("Questions", data["question_total"])
    top[1].metric("Competencies", len(data["by_competency"]))
    top[2].metric("Sub-competencies", data["sub_competencies"])
    top[3].metric("Knowledge docs", data["knowledge_total"])

    _panel_head(
        "▤", "Questions per competency",
        f"Curated corpus · {data['question_total']} questions, "
        f"{len(data['by_competency'])} competencies",
        tint="#e8f1fc", ink="#2a78d6",
        stamp=reports.last_run("interview_questions.jsonl", directory=reports.PREPARED_DIR),
    )
    frame = pd.DataFrame(data["by_competency"])
    st.altair_chart(
        _bar(frame, x="name", y="count", sort=list(frame["name"]),
             hues=COMPETENCY_HUES),
        use_container_width=True,
    )
    st.caption(
        "The thin pools are the operational point: the smallest competencies "
        "cannot fill a plan slot on their own, which is why question selection "
        "admits a repeat rather than leaving an interview unfilled."
    )

    left, right = st.columns(2)
    with left:
        st.markdown("**By difficulty**")
        diff = pd.DataFrame(data["by_difficulty"])
        st.altair_chart(
            _bar(diff, x="name", y="count", sort=list(diff["name"]), height=230,
                 hues=DIFFICULTY_RAMP),
            use_container_width=True,
        )
    with right:
        st.markdown("**By question type**")
        kinds = pd.DataFrame(data["by_question_type"])
        st.altair_chart(
            _bar(kinds, x="name", y="count", sort=list(kinds["name"]), height=230,
                 hues=QUESTION_TYPE_HUES),
            use_container_width=True,
        )

    with st.expander("Knowledge documents per competency"):
        st.dataframe(
            pd.DataFrame(data["knowledge_by_competency"]).rename(
                columns={"name": "Competency", "count": "Documents"}
            ),
            use_container_width=True,
            hide_index=True,
        )


def _golden_panel() -> None:
    data = reports.golden_query_set()
    if data is None:
        return _no_data("golden query set")

    top = st.columns(3)
    top[0].metric("Queries", data["total"])
    top[1].metric("Should retrieve", data["retrieval_total"])
    top[2].metric("Should retrieve nothing", data["negative_total"])

    st.markdown("**Golden query set — by query type**")
    st.caption(f"{data['dataset']} · {data['total']} queries")

    frame = pd.DataFrame(data["by_type"])
    frame["Kind"] = frame["negative"].map(
        {
            False: f"Should retrieve something ({data['retrieval_total']})",
            True: f"Should retrieve nothing — negative ({data['negative_total']})",
        }
    )
    order = list(frame["name"])

    base = alt.Chart(frame).encode(
        x=alt.X("name:N", sort=order, title=None,
                axis=alt.Axis(labelAngle=0, labelLimit=110, grid=False, domainColor="#d9e3ec")),
        y=alt.Y("count:Q", title=None,
                axis=alt.Axis(grid=True, gridColor="#eef3f8", domain=False, tickCount=4)),
    )
    bars = base.mark_bar(
        cornerRadiusTopLeft=4, cornerRadiusTopRight=4, width=alt.RelativeBandSize(0.62),
    ).encode(
        # Two kinds, so a legend is always present - identity is never colour
        # alone, and the negative group is also named in its own metric above.
        color=alt.Color(
            "Kind:N",
            scale=alt.Scale(
                domain=list(frame["Kind"].unique()),
                range=[SINGLE_SERIES, NEGATIVE_SERIES]
                if not frame["negative"].iloc[0]
                else [NEGATIVE_SERIES, SINGLE_SERIES],
            ),
            legend=alt.Legend(orient="top", title=None, direction="horizontal", labelLimit=320),
        ),
        tooltip=[alt.Tooltip("name:N", title="Query type"),
                 alt.Tooltip("count:Q", title="Queries")],
    )
    labels = base.mark_text(dy=-8, fontSize=11, fontWeight=700, color="#172033").encode(
        text=alt.Text("count:Q", format="d")
    )
    st.altair_chart(
        (bars + labels).properties(height=300).configure_view(
            strokeWidth=0, fill=CHART_SURFACE
        ),
        use_container_width=True,
    )

    if data["negative_metric"]:
        st.caption(
            "Negative queries are scored differently by design: "
            + "; ".join(data["negative_metric"])
        )

    if data["expected_behavior"]:
        st.dataframe(
            pd.DataFrame(
                [
                    {"Expected behaviour": key.replace("_", " "), "Queries": value}
                    for key, value in data["expected_behavior"].items()
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )


def _strategy_panel(data: dict, *, subtitle: str, derived: bool = False) -> None:
    st.markdown("**Retrieval strategy comparison**")
    st.caption(subtitle)

    st.altair_chart(_metric_chart(data["strategies"]), use_container_width=True)

    st.caption(
        f"Best MRR: {data['winner']}. Latency is deliberately not plotted on "
        "this axis - a percentage and a millisecond figure do not share a "
        "scale. It is the last column of the table."
    )

    _percent_table(
        data["strategies"],
        [
            ("strategy", "Strategy"),
            ("queries", "Queries"),
            ("recall_at_1", "Recall@1"),
            ("recall_at_3", "Recall@3"),
            ("recall_at_5", "Recall@5"),
            ("mrr", "MRR"),
            ("ndcg_at_5", "NDCG@5"),
            ("latency_ms", "Latency"),
        ],
    )

    if derived:
        st.caption(
            "These arms store per-query rows without a summary block, so these "
            "headline figures are averaged from the rows here rather than read "
            "from the experiment file."
        )


def _question_rag_panel() -> None:
    data = reports.question_rag_strategies()
    if data is None:
        return _no_data("question-RAG retrieval results")

    _strategy_panel(
        data,
        subtitle=(
            f"50-query golden set · {data['corpus_size']}-question corpus · "
            "sorted by MRR"
        ),
    )

    st.markdown("**Per query type**")
    st.caption(
        "The headline average hides where a strategy is weak; this is the "
        "breakdown that shows it."
    )
    choice = st.selectbox(
        "Strategy", list(data["breakdowns"]), label_visibility="collapsed",
    )
    rows = data["breakdowns"][choice]
    if rows:
        _percent_table(
            rows,
            [
                ("query_type", "Query type"),
                ("queries", "Queries"),
                ("recall_at_1", "Recall@1"),
                ("recall_at_5", "Recall@5"),
                ("mrr", "MRR"),
                ("ndcg_at_5", "NDCG@5"),
            ],
        )


def _evaluation_rag_panel() -> None:
    data = reports.evaluation_rag_strategies()
    if data is None:
        return _no_data("evaluation-RAG retrieval results")

    _strategy_panel(
        data,
        subtitle=f"{data['golden_total']}-query evaluation golden set · sorted by MRR",
        derived=True,
    )


def _coverage_panel() -> None:
    data = reports.concept_coverage()
    if data is None:
        return _no_data("concept coverage results")

    st.markdown("**Can the knowledge base grade each expected concept?**")
    st.caption(
        f"{data['total']} judgements. This scores the evaluation knowledge, "
        "not any candidate."
    )

    frame = pd.DataFrame(data["levels"])
    base = alt.Chart(frame).encode(
        x=alt.X("level:N", sort=list(frame["level"]), title=None,
                axis=alt.Axis(labelAngle=0, grid=False, domainColor="#d9e3ec")),
        y=alt.Y("count:Q", title=None,
                axis=alt.Axis(grid=True, gridColor="#eef3f8", domain=False, tickCount=4)),
    )
    bars = base.mark_bar(
        cornerRadiusTopLeft=4, cornerRadiusTopRight=4, width=alt.RelativeBandSize(0.5),
    ).encode(
        # Coverage is a state, so it wears the reserved status hues and each
        # bar is named on the axis - never colour alone.
        color=alt.Color(
            "level:N",
            scale=alt.Scale(
                domain=list(COVERAGE_COLORS), range=list(COVERAGE_COLORS.values())
            ),
            legend=None,
        ),
        tooltip=[alt.Tooltip("level:N", title="Coverage"),
                 alt.Tooltip("count:Q", title="Concepts")],
    )
    labels = base.mark_text(dy=-8, fontSize=11, fontWeight=700, color="#172033").encode(
        text=alt.Text("count:Q", format="d")
    )
    st.altair_chart(
        (bars + labels).properties(height=250).configure_view(
            strokeWidth=0, fill=CHART_SURFACE
        ),
        use_container_width=True,
    )

    st.dataframe(
        pd.DataFrame(data["by_competency"]).rename(columns={"name": "Competency"}),
        use_container_width=True,
        hide_index=True,
    )


def _analyzer_panel() -> None:
    data = reports.resume_scorecard()
    if data is None:
        return _no_data("resume analyzer scorecard")

    _panel_head(
        "▤",
        "Resume analyzer vs fixture labels",
        f"{data['judgements']} judgements against the synthetic manifest",
        stamp=reports.last_run("resume_analysis_scorecard.json"),
    )

    _kpis(
        [
            {"icon": "◉", "label": "Accuracy", "value": f"{data['accuracy']:.1%}",
             "fraction": data["accuracy"], "tint": "#e8f5ee", "ink": "#008300"},
            {"icon": "▮", "label": "Precision", "value": f"{data['precision']:.1%}",
             "fraction": data["precision"], "tint": "#eef1fe", "ink": "#4a3aa7"},
            {"icon": "◎", "label": "Recall", "value": f"{data['recall']:.1%}",
             "fraction": data["recall"], "tint": "#e8f1fc", "ink": "#2a78d6"},
            # A count, not a fraction: no meter, because nothing defines its
            # full width. The badge carries the comparison instead.
            {"icon": "★", "label": "Over-credit", "value": data["over_credit"],
             "fraction": None, "tint": "#fdf0e8", "ink": "#eb6834",
             "badge": f"{data['under_credit']} under-credit"},
        ]
    )

    total = data["judgements"] or 1
    frame = pd.DataFrame(data["outcomes"])

    left, right = st.columns(2, gap="medium")

    with left:
        st.markdown(
            '<div class="ig-panel-card-title">Judgement distribution</div>',
            unsafe_allow_html=True,
        )
        chart, legend = st.columns([1, 1.15], gap="small")
        with chart:
            st.altair_chart(
                _donut(frame, name="outcome", value="count", colors=OUTCOME_COLORS),
                use_container_width=True,
            )
        with legend:
            _legend(data["outcomes"], colors=OUTCOME_COLORS, total=total)

    with right:
        st.markdown(
            '<div class="ig-panel-card-title">Outcome breakdown</div>',
            unsafe_allow_html=True,
        )
        table = frame.rename(columns={"outcome": "Outcome", "count": "Judgements"})
        table["%"] = table["Judgements"] / total
        st.dataframe(
            table.style.format({"%": "{:.1%}"}),
            use_container_width=True,
            hide_index=True,
        )

    _insight(
        "The asymmetry is the finding, not the accuracy figure: zero "
        "under-credit means it never reports an evidenced area as unknown, and "
        "every error is in the other direction — claiming evidence a resume did "
        "not give, which costs the interview a probe it should have made."
    )


def _latency_panel() -> None:
    data = reports.latency_report()
    if data is None:
        return _no_data("intake latency report")

    stages = data.get("stages") or []
    totals = data.get("totals") or {}

    st.markdown("**Intake latency, before and after**")
    st.caption(
        f"Generated {str(data.get('generated_at', ''))[:10]} at "
        f"{data.get('git_ref', 'unknown')} · "
        f"{', '.join(f'{k}: {v}' for k, v in (data.get('config', {}).get('optimized_models') or {}).items())}"
    )

    if "before" in totals and "after" in totals:
        top = st.columns(3)
        top[0].metric("Before", f"{totals['before']['seconds']:.1f}s")
        top[1].metric(
            "After",
            f"{totals['after']['seconds']:.1f}s",
            delta=f"-{totals.get('improvement_pct', 0):.0f}%",
            delta_color="inverse",
        )
        reliability = data.get("reliability", {})
        if "optimized" in reliability:
            top[2].metric(
                "Runs completed",
                f"{reliability['optimized']['completed']}/{reliability['optimized']['attempted']}",
            )

    rows = [
        {
            "Stage": entry["stage"].title(),
            "Before": (entry.get("before") or {}).get("seconds"),
            "After": entry["after"]["seconds"],
            "Saved": entry.get("improvement_pct"),
            "Calls": entry["after"].get("calls"),
        }
        for entry in stages
    ]
    if rows:
        st.dataframe(
            pd.DataFrame(rows).style.format(
                {"Before": "{:.1f}s", "After": "{:.1f}s", "Saved": "{:+.0f}%",
                 "Calls": "{:.0f}"},
                na_rep="—",
            ),
            use_container_width=True,
            hide_index=True,
        )

    for observation in data.get("observations") or []:
        with st.expander(observation["title"]):
            st.write(" ".join(observation["detail"].split()))


PANELS = (
    ("Interview corpus", _corpus_panel),
    ("Golden query set", _golden_panel),
    ("Question-RAG retrieval", _question_rag_panel),
    ("Evaluation-RAG retrieval", _evaluation_rag_panel),
    ("Concept coverage", _coverage_panel),
    ("Resume analyzer", _analyzer_panel),
    ("Intake latency", _latency_panel),
)


def render_dashboard() -> None:
    """Render every evaluation panel as a tab."""

    for tab, (_, panel) in zip(st.tabs([name for name, _ in PANELS]), PANELS):
        with tab:
            panel()


def render_overview() -> None:
    """One screen of headline numbers drawn from every report."""

    corpus = reports.corpus_composition()
    golden = reports.golden_query_set()
    question_rag = reports.question_rag_strategies()
    evaluation_rag = reports.evaluation_rag_strategies()
    coverage = reports.concept_coverage()
    scorecard = reports.resume_scorecard()

    _panel_head(
        "◉",
        "Evaluation at a glance",
        "Headline figures from every report on disk",
        tint="#e8f1fc",
        ink="#2a78d6",
    )

    cards = []
    if corpus:
        cards.append({"icon": "▤", "label": "Corpus questions",
                      "value": corpus["question_total"], "fraction": None,
                      "tint": "#e8f1fc", "ink": "#2a78d6",
                      "badge": f"{len(corpus['by_competency'])} competencies"})
    if golden:
        cards.append({"icon": "◎", "label": "Golden queries",
                      "value": golden["total"], "fraction": None,
                      "tint": "#eef1fe", "ink": "#4a3aa7",
                      "badge": f"{golden['negative_total']} negative"})
    if question_rag:
        best = question_rag["strategies"][0]
        cards.append({"icon": "◈", "label": "Question-RAG MRR",
                      "value": f"{best['mrr']:.1%}", "fraction": best["mrr"],
                      "tint": "#e8f5ee", "ink": "#008300"})
    if evaluation_rag:
        best = evaluation_rag["strategies"][0]
        cards.append({"icon": "◇", "label": "Evaluation-RAG MRR",
                      "value": f"{best['mrr']:.1%}", "fraction": best["mrr"],
                      "tint": "#fdf0e8", "ink": "#eb6834"})
    if cards:
        _kpis(cards)

    second = []
    if coverage:
        covered = next(
            (item["count"] for item in coverage["levels"] if item["level"] == "Covered"), 0
        )
        share = covered / coverage["total"] if coverage["total"] else 0
        second.append({"icon": "✓", "label": "Concepts fully covered",
                       "value": f"{share:.1%}", "fraction": share,
                       "tint": "#e8f5ee", "ink": "#008300",
                       "badge": f"{coverage['total']} judged"})
    if scorecard:
        second.append({"icon": "▮", "label": "Analyzer accuracy",
                       "value": f"{scorecard['accuracy']:.1%}",
                       "fraction": scorecard["accuracy"],
                       "tint": "#eef1fe", "ink": "#4a3aa7",
                       "badge": f"{scorecard['over_credit']} over-credit"})
    if second:
        _kpis(second)

    if question_rag:
        st.markdown(
            '<div class="ig-panel-card-title">Retrieval strategies, both corpora</div>',
            unsafe_allow_html=True,
        )
        st.altair_chart(_metric_chart(question_rag["strategies"]), use_container_width=True)
        _insight(
            f"{question_rag['winner']} leads on the question corpus and "
            + (f"{evaluation_rag['winner']} on the evaluation corpus. " if evaluation_rag else "")
            + "Both wins come from metadata filtering before ranking, not from a "
            "better embedding — the same lever the question selector already uses.",
            title="What the retrieval numbers say",
        )


__all__ = ["render_dashboard", "render_overview"]
