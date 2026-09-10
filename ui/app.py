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

# override=True is deliberate. python-dotenv will not replace a variable that
# is already exported in the launching shell, so a stale PINECONE_INDEX_NAME
# silently points retrieval at the wrong index, every search returns nothing,
# and the run fails at question selection with an exhausted-corpus message
# that names the wrong cause.
load_dotenv(PROJECT_ROOT / ".env", override=True)

from ui.gateway import (
    CandidateIntake,
    CandidatePlan,
    IntakeIntegrationError,
    build_candidate_plan,
    resolve_interview_questions,
)
from ui.resume_upload import (
    ResumeUploadError,
    SUPPORTED_RESUME_TYPES,
    extract_resume,
)
from ui.session import InterviewProgress
from ui.styles import APP_STYLES


SCREEN_KEY = "ig_screen"
PLAN_KEY = "ig_plan"
INTAKE_KEY = "ig_intake"
PROGRESS_KEY = "ig_progress"

# What each backend stage is called while the candidate waits on it. The
# gateway names stages for error messages; these are the candidate-facing
# equivalents.
STAGE_LABELS = {
    "resume extraction": "Reading your resume",
    "resume analysis": "Matching it against the competency map",
    "interview planning": "Designing your question plan",
    "question selection": "Choosing your questions",
}

# Evidence levels are a statement about the resume, not about the candidate.
# The UI wording has to carry that, because the raw enum names do not.
EVIDENCE_PRESENTATION = {
    "DEMONSTRATED": (
        "ig-ev-shown",
        "\u25cf",
        "Evidenced in your resume",
    ),
    "PARTIAL_EVIDENCE": (
        "ig-ev-partial",
        "\u25d0",
        "Partly evidenced \u2014 room to go deeper",
    ),
    "UNKNOWN_NEEDS_PROBING": (
        "ig-ev-explore",
        "\u25cb",
        "Not covered by your resume \u2014 your chance to show us",
    ),
}

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
    st.session_state.setdefault(PLAN_KEY, None)
    st.session_state.setdefault(INTAKE_KEY, None)
    st.session_state.setdefault(PROGRESS_KEY, None)


def _reset() -> None:
    """Discard UI state without mutating backend artifacts."""

    st.session_state[SCREEN_KEY] = "upload"
    st.session_state[PLAN_KEY] = None
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
            # Three model calls run back to back here. An opaque spinner makes
            # that read as a hang, so each stage announces itself as it starts.
            with st.status(
                "Preparing your interview…", expanded=True,
            ) as status:

                def on_stage(stage: str) -> None:
                    label = STAGE_LABELS.get(stage, stage)
                    status.update(label=label)
                    st.write(f"› {label}")

                prepared = build_candidate_plan(document, on_stage=on_stage)
                status.update(
                    label="Your interview plan is ready",
                    state="complete",
                    expanded=False,
                )
        except ResumeUploadError as error:
            st.error(str(error))
        except IntakeIntegrationError as error:
            st.error(f"Could not complete {error.stage}. {error}")
        else:
            st.session_state[PLAN_KEY] = prepared
            st.session_state[SCREEN_KEY] = "plan"
            st.rerun()


def _facts_block(resume: object) -> str:
    """Stage 1 output as read-back, not judgement: what the parser saw."""

    skills = list(getattr(resume, "skills", []) or [])
    chips = "".join(
        f'<span class="ig-chip">{_safe(skill)}</span>' for skill in skills[:9]
    )
    if len(skills) > 9:
        chips += f'<span class="ig-chip">+{len(skills) - 9} more</span>'

    facts = [
        ("NAME", _safe(getattr(resume, "name", None) or "Not stated")),
        ("TARGET ROLE", _safe(getattr(resume, "target_role", None) or "Not stated")),
        ("ROLES", f'{len(getattr(resume, "work_experience", []) or [])}'),
        ("PROJECTS", f'{len(getattr(resume, "projects", []) or [])}'),
    ]
    cells = "".join(
        f'<div><span class="ig-fact-label">{label}</span>'
        f'<span class="ig-fact-value">{value}</span></div>'
        for label, value in facts
    )
    return '<div class="ig-facts">' + cells + "</div>" + (
        f'<div class="ig-chips">{chips}</div>' if chips else ""
    )


def _evidence_rows(prepared: CandidatePlan) -> str:
    """
    Stage 2 output as interview coverage rather than a verdict.

    The analyzer's own docstring says an evidence level is not a skill
    rating. Showing raw enum names and a confidence float invites the
    opposite reading, so each row states what the resume showed and how
    much interview time the area gets.
    """

    allocated = {
        target.competency.value: target.question_count
        for target in prepared.plan.competency_targets
    }

    rows: list[str] = []
    for item in prepared.analysis.competency_evidence:
        icon, label = _competency(item.competency)
        style, mark, phrasing = EVIDENCE_PRESENTATION.get(
            item.evidence_level.value,
            ("ig-ev-explore", "\u25cb", item.evidence_level.value),
        )
        count = allocated.get(item.competency.value, 0)
        share = f"{count} question(s)" if count else "not scheduled"
        rows.append(
            f'<div class="ig-ev {style}">'
            f'<span class="ig-ev-mark">{mark}</span>'
            '<span class="ig-ev-body">'
            f'<span class="ig-ev-name">{_safe(icon)} &nbsp;{_safe(label)}</span>'
            f'<div class="ig-ev-state">{_safe(phrasing)}</div>'
            "</span>"
            f'<span class="ig-ev-count">{_safe(share)}</span>'
            "</div>"
        )
    return "".join(rows)


def _evidence_tally(prepared: CandidatePlan) -> str:
    """Headline counts, so the summary is scannable before it is readable."""

    counts = {"DEMONSTRATED": 0, "PARTIAL_EVIDENCE": 0, "UNKNOWN_NEEDS_PROBING": 0}
    for item in prepared.analysis.competency_evidence:
        key = item.evidence_level.value
        if key in counts:
            counts[key] += 1

    tiles = (
        (counts["DEMONSTRATED"], "EVIDENCED"),
        (counts["PARTIAL_EVIDENCE"], "PARTLY EVIDENCED"),
        (counts["UNKNOWN_NEEDS_PROBING"], "TO EXPLORE WITH YOU"),
    )
    cells = "".join(
        f'<div class="ig-tally-item"><div class="ig-tally-n">{number}</div>'
        f'<div class="ig-tally-l">{label}</div></div>'
        for number, label in tiles
    )
    return f'<div class="ig-tally">{cells}</div>'


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


def _render_plan(prepared: CandidatePlan) -> None:
    """Present stages 1-3 before paying for question selection."""

    _header("plan")
    st.markdown('<div class="ig-kicker">READY TO BEGIN</div>', unsafe_allow_html=True)
    st.title("Your interview plan")
    st.markdown(
        '<p class="ig-subtitle">Built from your resume. Review it before you start.</p>',
        unsafe_allow_html=True,
    )

    for warning in prepared.upload.warnings:
        st.warning(warning)

    st.subheader("What we read from your resume")
    st.caption(f"Parsed from {prepared.upload.filename}. Facts only — no judgement here.")
    st.markdown(_facts_block(prepared.resume), unsafe_allow_html=True)

    st.subheader("How the interview will cover you")
    st.markdown(_evidence_tally(prepared), unsafe_allow_html=True)
    st.markdown(
        '<p class="ig-reassure">This is a reading of your <strong>resume</strong>, not a '
        "score. An area your resume does not mention is not a gap in your ability — it "
        "simply gets more of the interview, so you can speak to it directly.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(_evidence_rows(prepared), unsafe_allow_html=True)

    with st.expander("Read the full summary"):
        st.markdown(
            f'<div class="ig-summary">{_safe(prepared.analysis.overall_summary)}</div>',
            unsafe_allow_html=True,
        )

    with st.expander("Why each area gets the time it does"):
        st.markdown(_plan_cards(prepared), unsafe_allow_html=True)

    question_count = prepared.plan.total_questions
    candidate_name = prepared.resume.name or "Candidate"
    detail_columns = st.columns(3)
    detail_columns[0].metric("◷ Duration", f"Approx. {question_count * 3 + 5} min")
    detail_columns[1].metric("▤ Format", f"{question_count} questions")
    detail_columns[2].metric("● Candidate", candidate_name)

    st.info(
        "🔒 Questions are shown one at a time. Answers are collected first; "
        "no question-level score or rubric is shown during the interview."
    )

    back, start_column = st.columns([1, 2])
    if back.button("← Back", use_container_width=True):
        _reset()
        st.rerun()
    if start_column.button(
        "▶ Start interview", type="primary", use_container_width=True,
    ):
        # Stage 4 is deferred to here so its latency lands after the candidate
        # has had something to read, rather than in front of the plan.
        try:
            with st.spinner("Choosing your questions…"):
                intake = resolve_interview_questions(prepared)
        except IntakeIntegrationError as error:
            st.error(f"Could not complete {error.stage}. {error}")
        else:
            question_ids = tuple(
                question.question_id for question in intake.question_set.questions
            )
            st.session_state[INTAKE_KEY] = intake
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
    prepared = st.session_state[PLAN_KEY]
    intake = st.session_state[INTAKE_KEY]
    progress = st.session_state[PROGRESS_KEY]

    if screen == "upload":
        _render_upload()
    elif screen == "plan" and prepared is not None:
        _render_plan(prepared)
    elif screen == "interview" and intake is not None and progress is not None:
        _render_interview(intake, progress)
    elif screen == "results" and intake is not None and progress is not None:
        _render_results(intake, progress)
    else:
        _reset()
        st.rerun()


if __name__ == "__main__":
    main()
