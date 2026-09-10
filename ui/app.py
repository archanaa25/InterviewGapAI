"""Candidate-facing Streamlit flow over the existing InterviewGapAI backend."""

from __future__ import annotations

import html
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=False)

from ui.gateway import CandidateIntake, IntakeIntegrationError, build_candidate_intake
from ui.resume_upload import (
    ResumeUploadError,
    SUPPORTED_RESUME_TYPES,
    extract_resume,
)
from ui.session import InterviewProgress
from ui.styles import APP_STYLES


SCREEN_KEY = "ig_screen"
INTAKE_KEY = "ig_intake"
PROGRESS_KEY = "ig_progress"

COMPETENCY_LABELS = {
    "rag": ("◉", "RAG"),
    "agentic_ai": ("⌁", "Agentic AI"),
    "ai_ml_llm_fundamentals": ("✦", "AI & LLM Fundamentals"),
    "ai_evaluation": ("✓", "AI Evaluation"),
    "python_software_engineering": ("⌘", "Python Engineering"),
    "ai_system_design": ("◇", "AI System Design"),
    "ai_security": ("⬡", "AI Security"),
}


def _initialize_state() -> None:
    """Create only UI-owned state keys."""

    st.session_state.setdefault(SCREEN_KEY, "upload")
    st.session_state.setdefault(INTAKE_KEY, None)
    st.session_state.setdefault(PROGRESS_KEY, None)


def _reset() -> None:
    """Discard UI state without mutating backend artifacts."""

    st.session_state[SCREEN_KEY] = "upload"
    st.session_state[INTAKE_KEY] = None
    st.session_state[PROGRESS_KEY] = None


def _header(active: str) -> None:
    """Render the compact product mark and candidate journey."""

    steps = (
        ("upload", "1. UPLOAD"),
        ("plan", "2. PLAN"),
        ("interview", "3. INTERVIEW"),
        ("results", "4. RESULTS"),
    )
    markup = "<span>›</span>".join(
        f'<span class="ig-step {"active" if key == active else ""}">{label}</span>'
        for key, label in steps
    )
    st.markdown(
        f"""
        <div class="ig-header">
          <div class="ig-brand"><span class="ig-mark">AI</span><span>INTERVIEW<br>GAP AI</span></div>
          <div class="ig-steps">{markup}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _safe(value: object) -> str:
    """Escape backend-provided text before rendering custom HTML."""

    return html.escape(str(value), quote=True)


def _competency(value: object) -> tuple[str, str]:
    """Return an icon and candidate-friendly competency label."""

    key = getattr(value, "value", value)
    return COMPETENCY_LABELS.get(str(key), ("•", str(key).replace("_", " ").title()))


def _render_upload() -> None:
    """Accept one resume and invoke the existing intake pipeline."""

    _header("upload")
    st.markdown('<div class="ig-kicker">BUILD YOUR INTERVIEW</div>', unsafe_allow_html=True)
    st.title("Upload your resume")
    st.markdown(
        '<p class="ig-subtitle">Submit your CV to prepare a focused AI-engineering interview.</p>',
        unsafe_allow_html=True,
    )

    upload_column, note_column = st.columns([1.55, 1], gap="large")
    with upload_column:
        uploaded = st.file_uploader(
            "Drag and drop or browse",
            type=list(SUPPORTED_RESUME_TYPES),
            help="PDF, DOCX, DOC, CSV, MD, or MARKDOWN; maximum 10 MB.",
            max_upload_size=10,
        )
        st.caption("Supported: PDF, DOCX, DOC, CSV and Markdown · Maximum 10 MB")

    with note_column:
        st.markdown(
            """
            <div class="ig-upload-note">
              <h4>✦ Why upload?</h4>
              <p>🎯 Tailored competency coverage</p>
              <p>🧭 Evidence-led interview planning</p>
              <p>🔒 Rubrics stay hidden during the interview</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button(
        "Prepare interview plan  →",
        type="primary",
        use_container_width=True,
        disabled=uploaded is None,
    ):
        try:
            document = extract_resume(
                filename=uploaded.name,
                data=uploaded.getvalue(),
                content_type=uploaded.type,
            )
            with st.spinner("Preparing your personalized interview…"):
                intake = build_candidate_intake(document)
        except ResumeUploadError as error:
            st.error(str(error))
        except IntakeIntegrationError as error:
            st.error(f"Could not complete {error.stage}. {error}")
        else:
            st.session_state[INTAKE_KEY] = intake
            st.session_state[SCREEN_KEY] = "plan"
            st.rerun()


def _plan_cards(intake: CandidateIntake) -> str:
    """Build escaped competency summary cards from the existing plan."""

    cards: list[str] = []
    for target in intake.plan.competency_targets:
        icon, label = _competency(target.competency)
        difficulty_parts = [
            f"{count} {difficulty}"
            for difficulty, count in (
                ("basic", target.basic),
                ("intermediate", target.intermediate),
                ("advanced", target.advanced),
            )
            if count
        ]
        # Keep each card flush-left and contiguous. Indented HTML after a blank
        # line is a Markdown code block even when unsafe_allow_html is enabled.
        cards.append(
            '<div class="ig-card">'
            f'<div class="ig-card-title">{_safe(icon)} &nbsp;{_safe(label)}</div>'
            f'<div class="ig-card-meta">{target.question_count} question(s) · '
            f"{_safe(', '.join(difficulty_parts))}</div>"
            f'<div class="ig-card-copy">{_safe(target.reason)}</div>'
            "</div>"
        )
    return '<div class="ig-grid">' + "".join(cards) + "</div>"


def _render_plan(intake: CandidateIntake) -> None:
    """Present only candidate-relevant plan details before starting."""

    _header("plan")
    st.markdown('<div class="ig-kicker">READY TO BEGIN</div>', unsafe_allow_html=True)
    st.title("Your interview plan")
    st.markdown(
        '<p class="ig-subtitle">Review the format before starting your AI-assisted assessment.</p>',
        unsafe_allow_html=True,
    )

    st.info(
        f"📄 Selected: {intake.upload.filename} · "
        f"Prepared from the existing resume-analysis and interview-planning pipeline."
    )
    for warning in intake.upload.warnings:
        st.warning(warning)

    st.subheader("Section summary")
    st.markdown(_plan_cards(intake), unsafe_allow_html=True)

    question_count = len(intake.question_set.questions)
    candidate_name = intake.resume.name or "Candidate"
    detail_columns = st.columns(3)
    detail_columns[0].metric("◷ Duration", f"Approx. {question_count * 3 + 5} min")
    detail_columns[1].metric("▤ Format", f"{question_count} questions")
    detail_columns[2].metric("● Candidate", candidate_name)

    st.info(
        "🔒 Questions are shown one at a time. Answers are collected first; "
        "no question-level score or rubric is shown during the interview."
    )

    back, start = st.columns([1, 2])
    if back.button("← Back", use_container_width=True):
        _reset()
        st.rerun()
    if start.button("▶ Start interview", type="primary", use_container_width=True):
        question_ids = tuple(
            question.question_id for question in intake.question_set.questions
        )
        st.session_state[PROGRESS_KEY] = InterviewProgress.start(question_ids)
        st.session_state[SCREEN_KEY] = "interview"
        st.rerun()


def _render_interview(intake: CandidateIntake, progress: InterviewProgress) -> None:
    """Collect answers sequentially without exposing evaluation material."""

    _header("interview")
    questions = tuple(intake.question_set.questions)
    position = progress.current_index
    question = questions[position]
    icon, label = _competency(question.competency)

    st.markdown('<div class="ig-kicker">INTERVIEW IN PROGRESS</div>', unsafe_allow_html=True)
    st.title(f"Question {position + 1} of {len(questions)}")
    st.progress((position + 1) / len(questions))
    st.markdown(
        f'<span class="ig-pill">{_safe(icon)} {_safe(label)}</span>'
        f'<span class="ig-pill">{_safe(question.difficulty.title())}</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="ig-question">{_safe(question.question)}</div>',
        unsafe_allow_html=True,
    )

    with st.form(f"answer-{question.question_id}", clear_on_submit=True):
        answer = st.text_area(
            "Your answer",
            height=220,
            placeholder="Explain your reasoning, trade-offs, and a concrete example…",
        )
        st.caption("A blank submission is recorded as a skipped question.")
        label_text = (
            "Submit complete interview"
            if progress.is_final_question
            else "Save answer and continue  →"
        )
        submitted = st.form_submit_button(
            label_text,
            type="primary",
            use_container_width=True,
        )

    if submitted:
        updated = progress.record_current(answer)
        st.session_state[PROGRESS_KEY] = updated
        if updated.submitted:
            st.session_state[SCREEN_KEY] = "results"
        st.rerun()


def _render_results(intake: CandidateIntake, progress: InterviewProgress) -> None:
    """Confirm final submission without fabricating unavailable evaluation."""

    _header("results")
    st.markdown(
        """
        <div class="ig-complete">
          <div style="font-size:2rem">✓</div>
          <h2>Interview submitted</h2>
          <p>Your complete answer set was captured before evaluation begins.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    summary = st.columns(3)
    summary[0].metric("✓ Answered", progress.answered_count)
    summary[1].metric("↷ Skipped", progress.skipped_count)
    summary[2].metric("▤ Total", len(progress.question_ids))

    st.warning(
        "Evaluation and report generation are not yet implemented in the contributor "
        "backend. This UI does not invent scores: answers remain in the current "
        "Streamlit session until that backend handoff is available."
    )

    with st.expander("Review submitted answers"):
        question_by_id = {
            question.question_id: question for question in intake.question_set.questions
        }
        for index, answer in enumerate(progress.answers, start=1):
            question = question_by_id[answer.question_id]
            st.markdown(f"**{index}. {question.question}**")
            st.write(answer.text if answer.text else "_Skipped_")
            st.divider()

    if st.button("Start over", use_container_width=True):
        _reset()
        st.rerun()


def main() -> None:
    """Render the current UI-owned candidate state."""

    st.set_page_config(
        page_title="InterviewGapAI",
        page_icon="✦",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown(APP_STYLES, unsafe_allow_html=True)
    _initialize_state()

    screen = st.session_state[SCREEN_KEY]
    intake = st.session_state[INTAKE_KEY]
    progress = st.session_state[PROGRESS_KEY]

    if screen == "upload":
        _render_upload()
    elif screen == "plan" and intake is not None:
        _render_plan(intake)
    elif screen == "interview" and intake is not None and progress is not None:
        _render_interview(intake, progress)
    elif screen == "results" and intake is not None and progress is not None:
        _render_results(intake, progress)
    else:
        _reset()
        st.rerun()


if __name__ == "__main__":
    main()
