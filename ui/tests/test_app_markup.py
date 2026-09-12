"""Focused rendering-regression tests for generated UI markup."""

from types import SimpleNamespace

from ui.app import (
    _competency_bars,
    _competency_heading,
    _concept_list,
    _donut,
    _evidence_rows,
    _evidence_tally,
    _person_row,
    _plan_cards,
    _results_markdown,
)


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


def test_concept_marks_cover_every_real_judgement_status() -> None:
    """
    The trace view's status labels must be the schema's own status values.

    This existed as a live defect: the evaluation trace counted judgements
    whose status equalled "MET", which is not a ConceptJudgementStatus
    member, so a fully demonstrated answer still read "0/3 concepts". The
    names are checked against the enum rather than retyped.
    """

    from src.schemas.answer_evaluation import ConceptJudgementStatus
    from ui.app import CONCEPT_MARKS

    assert set(CONCEPT_MARKS) == {
        status.value for status in ConceptJudgementStatus
    }


def test_question_text_is_borrowed_for_the_stage_that_stores_only_ids() -> None:
    """An evaluation names question ids; the wording comes from elsewhere."""

    from ui.app import _asked_questions

    asked = _asked_questions(
        {
            "interview questions": {
                "questions": [
                    {"question_id": "RAG-RET-ADV-001", "question": "Corpus wording."},
                    {"question_id": "PY-APP-BAS-001", "question": "Only in the set."},
                ]
            },
            # The answers were written at submission time, so they carry the
            # wording this candidate actually saw and must win.
            "answers": {
                "answers": [
                    {"question_id": "RAG-RET-ADV-001", "question": "As asked."},
                ]
            },
        }
    )

    assert asked["RAG-RET-ADV-001"] == "As asked."
    assert asked["PY-APP-BAS-001"] == "Only in the set."


def test_asked_questions_tolerates_stages_that_have_not_run() -> None:
    """Traces render mid-interview, so missing stages are normal, not an error."""

    from ui.app import _asked_questions

    assert _asked_questions({}) == {}
    assert _asked_questions({"answers": None, "interview questions": None}) == {}


def _scorecard(overall: float | None, competencies: list) -> SimpleNamespace:
    band = "GAP" if overall is not None and overall < 70 else "DEVELOPING"
    return SimpleNamespace(
        overall_score=overall,
        band="NOT_SCORED" if overall is None else band,
        competencies=competencies,
    )


def test_donut_fills_the_ring_to_the_overall_score() -> None:
    """The ring is the score: a wrong sweep is a wrong result on screen."""

    markup = _donut(_scorecard(74.0, []))

    assert "conic-gradient" in markup
    assert "0 74.0%" in markup
    assert ">74<" in markup


def test_unscored_interview_draws_an_empty_ring_not_a_zero() -> None:
    """An unscorable interview must never read as a score of zero."""

    markup = _donut(_scorecard(None, []))

    assert "0 0.0%" in markup
    assert ">--<" in markup
    assert ">0<" not in markup


def test_competency_bars_are_ordered_strongest_first() -> None:
    """Bar order carries meaning, so it cannot follow interview order."""

    markup = _competency_bars(
        _scorecard(
            70.0,
            [
                SimpleNamespace(competency="ai_security", score=51.0, band="GAP"),
                SimpleNamespace(competency="rag", score=84.0, band="DEVELOPING"),
                SimpleNamespace(
                    competency="agentic_ai", score=None, band="NOT_SCORED"
                ),
            ],
        )
    )

    assert markup.index("RAG") < markup.index("AI Security")
    # An unscored competency sorts last rather than to the bottom of the scale.
    assert markup.index("AI Security") < markup.index("Agentic AI")
    assert "width:84.0%" in markup


def test_concept_list_escapes_backend_text_and_caps_its_length() -> None:
    """Concept text reaches the page from the model and stays inert."""

    markup = _concept_list([f"<b>concept {index}</b>" for index in range(9)], limit=3)

    assert "<b>" not in markup
    assert "&lt;b&gt;concept 0&lt;/b&gt;" in markup
    assert "+6 more" in markup


def test_results_markup_stays_on_one_line() -> None:
    """Indented HTML reaches Streamlit as a code block, not as markup.

    Streamlit renders markdown before HTML, so a four-space indent turns the
    whole results card into visible source on the candidate's screen.
    """

    competency = SimpleNamespace(competency="rag", score=84.0, band="DEVELOPING")
    builders = {
        "donut": _donut(_scorecard(74.0, [])),
        "bars": _competency_bars(_scorecard(74.0, [competency])),
        "heading": _competency_heading(competency),
        "concepts": _concept_list(["chunking strategy"]),
    }

    for name, markup in builders.items():
        assert "\n" not in markup, f"{name} markup would render as a code block"


def test_person_row_is_one_line_and_escapes_catalog_text() -> None:
    person = SimpleNamespace(
        name="<script>x</script>",
        role="AI & Data",
        url="https://example.com/in/someone",
    )

    markup = _person_row(person)

    assert "\n" not in markup
    assert "<script>" not in markup
    assert "AI &amp; Data" in markup
    assert 'href="https://example.com/in/someone"' in markup


def _export_fixtures():
    competency = SimpleNamespace(
        competency="rag",
        score=51.0,
        band="GAP",
        strong_concepts=["hybrid retrieval"],
        missing_concepts=["reranking", "chunk overlap"],
    )
    scorecard = SimpleNamespace(
        overall_score=51.0,
        band="GAP",
        competencies=[competency],
        questions=[object()],
        scored_count=1,
        strengths=[],
        gaps=[competency],
    )
    plan = SimpleNamespace(
        recommendations=[
            SimpleNamespace(
                display_name="RAG",
                score=51.0,
                is_priority=True,
                reason="Priority gap.",
                resources=[
                    SimpleNamespace(
                        title="Advanced RAG",
                        url="https://example.com/rag",
                        provider="DeepLearning.AI",
                    )
                ],
            )
        ],
        featured=SimpleNamespace(
            title="From The Gen Academy",
            highlight=SimpleNamespace(
                title="Mastering Agentic AI",
                url="https://example.com/cohort",
                note="Next cohort starts 3 October 2026",
            ),
            reading=[
                SimpleNamespace(title="AI with Aish", url="https://example.com/sub")
            ],
            people=[
                SimpleNamespace(
                    name="Aishwarya Srinivasan",
                    url="https://example.com/in/aish",
                    role="AI Entrepreneur",
                )
            ],
            community=SimpleNamespace(
                name="The Gen Academy",
                url="https://example.com/company",
                role="Follow for new cohorts",
            ),
        ),
    )
    intake = SimpleNamespace(plan=SimpleNamespace(candidate_id="upload-abc"))
    return intake, scorecard, plan


def test_downloaded_results_carry_the_score_gaps_and_plan() -> None:
    """The export is what the candidate keeps once the session ends."""

    intake, scorecard, plan = _export_fixtures()

    document = _results_markdown(intake, scorecard, plan)

    assert "**Overall score:** 51 / 100" in document
    assert "| RAG | 51% |" in document
    assert "## Areas to improve" in document
    assert "reranking" in document
    assert "[Advanced RAG](https://example.com/rag)" in document


def test_downloaded_results_end_with_the_academy_links() -> None:
    intake, scorecard, plan = _export_fixtures()

    document = _results_markdown(intake, scorecard, plan)

    assert "## From The Gen Academy" in document
    assert "Next cohort starts 3 October 2026" in document
    # The organisation closes the document, after the individual people.
    assert document.index("in/aish") < document.index("example.com/company")


def test_downloaded_results_survive_a_missing_catalog() -> None:
    """Losing the catalog must not cost the candidate their scores."""

    intake, scorecard, _ = _export_fixtures()

    document = _results_markdown(intake, scorecard, None)

    assert "**Overall score:** 51 / 100" in document
    assert "Learning plan" not in document
