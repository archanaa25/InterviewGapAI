"""Focused rendering-regression tests for generated UI markup."""

from types import SimpleNamespace

from ui.app import _plan_cards


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
    assert markup.startswith('<div class="ig-grid">')
    assert markup.endswith("</div>")
    assert markup.count('<div class="ig-card">') == 2


def test_plan_card_content_is_html_escaped() -> None:
    """Backend plan text cannot inject markup into the candidate page."""

    target = SimpleNamespace(
        competency="rag",
        basic=1,
        intermediate=0,
        advanced=0,
        question_count=1,
        reason='<script>alert("x")</script>',
    )
    intake = SimpleNamespace(plan=SimpleNamespace(competency_targets=[target]))

    markup = _plan_cards(intake)

    assert "<script>" not in markup
    assert "&lt;script&gt;" in markup
