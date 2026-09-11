"""Focused rendering-regression tests for generated UI markup."""

from types import SimpleNamespace

from ui.app import _evidence_rows, _evidence_tally, _plan_cards


def test_plan_cards_are_contiguous_html_not_markdown_code() -> None:
    """Every card remains inside one HTML grid instead of becoming code text."""

    targets = [
        SimpleNamespace(
            competency="rag",
            basic=1,
            intermediate=0,
            advanced=0,
            question_count=1,
            reason="Probe retrieval grounding.",
        ),
        SimpleNamespace(
            competency="agentic_ai",
            basic=0,
            intermediate=2,
            advanced=0,
            question_count=2,
            reason="Probe bounded orchestration.",
        ),
    ]
    intake = SimpleNamespace(plan=SimpleNamespace(competency_targets=targets))

    markup = _plan_cards(intake)

    assert "\n" not in markup
    assert markup.startswith('<div class="ig-grid')
    assert markup.endswith("</div>")
    assert markup.count('class="ig-card"') == 2


def test_plan_card_content_is_html_escaped() -> None:
    """Backend plan text cannot inject markup into the candidate page."""

    # The competency name is the backend-supplied string the card still
    # renders; the planner's per-area reason is deliberately not shown, so
    # escaping is asserted on what actually reaches the page.
    target = SimpleNamespace(
        competency='<script>alert("x")</script>',
        basic=1,
        intermediate=0,
        advanced=0,
        question_count=1,
        reason="Probe retrieval grounding.",
    )
    intake = SimpleNamespace(plan=SimpleNamespace(competency_targets=[target]))

    markup = _plan_cards(intake)

    # An unrecognised competency is title-cased into a display label, so the
    # comparison is case-insensitive; what matters is that the angle brackets
    # arrived escaped.
    assert "<script>" not in markup
    assert "&lt;script&gt;" in markup.lower()


def test_plan_cards_omit_the_planners_reasoning() -> None:
    """Allocation reasoning is interview strategy, not candidate content."""

    target = SimpleNamespace(
        competency="rag",
        basic=1,
        intermediate=0,
        advanced=0,
        question_count=1,
        reason="Probe retrieval because the resume shows no evidence of it.",
    )
    intake = SimpleNamespace(plan=SimpleNamespace(competency_targets=[target]))

    markup = _plan_cards(intake)

    assert "Probe retrieval" not in markup
    assert "no evidence" not in markup
    assert ">1<" in markup


def _analysis(summary: str):
    """Minimal stand-in for a ResumeAnalysis with one competency row."""

    item = SimpleNamespace(
        competency="rag",
        evidence_level=SimpleNamespace(value="UNKNOWN_NEEDS_PROBING"),
        probe_priority=SimpleNamespace(value="HIGH"),
        confidence=0.98,
    )
    return SimpleNamespace(overall_summary=summary, competency_evidence=[item])


def test_evidence_markup_omits_the_analyzer_summary() -> None:
    """The summary names areas to probe, which is strategy, not candidate content."""

    analysis = _analysis(
        "RAG and agentic AI require interview probing."
    )

    markup = _evidence_tally(analysis) + _evidence_rows(analysis)

    assert "require interview probing" not in markup
    assert "RAG and agentic AI" not in markup


def test_evidence_rows_state_coverage_without_raw_enum_or_confidence() -> None:
    """A candidate sees plain wording, not the analyzer's internal fields."""

    markup = _evidence_rows(_analysis("unused"))

    assert "UNKNOWN_NEEDS_PROBING" not in markup
    assert "0.98" not in markup
    assert "your chance to show us" in markup
