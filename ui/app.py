"""Candidate-facing Streamlit flow over the existing InterviewGapAI backend."""

from __future__ import annotations

import html
import sys
from pathlib import Path
from types import SimpleNamespace

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


# One fixed hue per competency, assigned in order and never cycled. Validated
# as a categorical set against the white card surface: worst adjacent CVD
# ΔE 9.1, worst normal-vision ΔE 19.6. Three of these sit under 3:1 contrast,
# so colour is carried by borders and swatches only - every label stays in ink.
COMPETENCY_COLORS = {
    "rag": "#2a78d6",
    "agentic_ai": "#eb6834",
    "ai_ml_llm_fundamentals": "#1baf7a",
    "ai_evaluation": "#eda100",
    "python_software_engineering": "#e87ba4",
    "ai_system_design": "#008300",
    "ai_security": "#4a3aa7",
}
DEFAULT_COMPETENCY_COLOR = "#607087"

# Coverage hues, validated all-pairs (worst normal-vision ΔE 29.0) because the
# three meter segments sit side by side.
COVERAGE_COLORS = {
    "DEMONSTRATED": "#008300",
    "PARTIAL_EVIDENCE": "#eda100",
    "UNKNOWN_NEEDS_PROBING": "#2a78d6",
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


SECTION_TITLES = (
    "Your profile",
    "Resume evidence",
    "Interview plan",
)

SECTION_PENDING = (
    "Reading your resume…",
    "Reviewing your experience…",
    "Preparing your questions…",
)

# What the progress bar says while each stage runs. Deliberately describes
# the candidate's experience, not the pipeline: how areas are prioritised is
# interview strategy and stays out of the candidate's view.
STAGE_PROGRESS = {
    "resume extraction": (0.08, "Reading your resume…"),
    "resume analysis": (0.38, "Reviewing your experience…"),
    "interview planning": (0.72, "Preparing your questions…"),
}


def _paint_profile(container: object, resume: object) -> None:
    """Section 1: stage 1 output, the moment extraction returns."""

    container.caption("Facts read from your file. No judgement here.")
    container.markdown(_facts_block(resume), unsafe_allow_html=True)


def _paint_evidence(container: object, analysis: object) -> None:
    """
    Section 2: what the resume evidenced, while planning is still running.

    The analyzer's overall summary is not rendered. It names which areas it
    considers unproven and says they require probing, which tells the
    candidate where the interview intends to push. Per-area state is shown
    instead: it is what the candidate needs, without the strategy.
    """

    container.markdown(_evidence_tally(analysis), unsafe_allow_html=True)
    container.markdown(
        '<p class="ig-reassure">This is a reading of your <strong>resume</strong>, not a '
        "score. An area your resume does not mention is not a gap in your ability — it "
        "simply gets more of the interview, so you can speak to it directly.</p>",
        unsafe_allow_html=True,
    )
    container.markdown(_evidence_rows(analysis), unsafe_allow_html=True)


def _paint_plan(container: object, plan: object) -> None:
    """
    Section 3: what the interview covers and how long it is.

    Only the shape of the interview belongs here. The planner's per-area
    reasoning explains which areas are being probed and why, which is the
    interviewer's strategy, so it is not rendered for the candidate.
    """

    container.markdown(
        _plan_cards(SimpleNamespace(plan=plan)), unsafe_allow_html=True,
    )


def _intake_sections() -> tuple:
    """Three stacked sections, all visible, each filling as its stage lands."""

    holders = []

    for title, pending in zip(SECTION_TITLES, SECTION_PENDING):
        st.markdown(f'<div class="ig-section-title">{title}</div>', unsafe_allow_html=True)
        holder = st.empty()
        holder.markdown(f'<p class="ig-pending">{pending}</p>', unsafe_allow_html=True)
        holders.append(holder)

    return tuple(holders)


def _competency_color(value: object) -> str:
    """The fixed identity hue for one competency."""

    key = str(getattr(value, "value", value))
    return COMPETENCY_COLORS.get(key, DEFAULT_COMPETENCY_COLOR)


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
              <div class="ig-note-title">Why upload?</div>
              <div class="ig-note-row"><span class="ig-note-ico" style="background:#e8f1fc;color:#2a78d6">◎</span>
                <span><b>Tailored coverage</b><i>Questions matched to your background</i></span></div>
              <div class="ig-note-row"><span class="ig-note-ico" style="background:#fdf0e8;color:#eb6834">◈</span>
                <span><b>Evidence-led planning</b><i>Built from what your resume shows</i></span></div>
              <div class="ig-note-row"><span class="ig-note-ico" style="background:#e8f5ee;color:#008300">◔</span>
                <span><b>No surprises</b><i>Marking rubrics stay hidden throughout</i></span></div>
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
            # Three model calls run back to back. All three sections are on
            # screen from the start and each fills as its stage returns, so
            # the wait shows real progress instead of a blank spinner.
            st.markdown(
                '<div class="ig-kicker">PREPARING YOUR INTERVIEW</div>',
                unsafe_allow_html=True,
            )
            meter = st.progress(0.0, text="Reading your resume…")
            profile_slot, evidence_slot, plan_slot = _intake_sections()
            painters = {
                "resume extraction": lambda value: _paint_profile(
                    profile_slot.container(), value,
                ),
                "resume analysis": lambda value: _paint_evidence(
                    evidence_slot.container(), value,
                ),
                "interview planning": lambda value: _paint_plan(
                    plan_slot.container(), value,
                ),
            }

            def on_stage(stage: str) -> None:
                fraction, message = STAGE_PROGRESS.get(stage, (0.0, "Working…"))
                meter.progress(fraction, text=message)

            def on_result(stage: str, value: object) -> None:
                painter = painters.get(stage)
                if painter is not None:
                    painter(value)

            prepared = build_candidate_plan(
                document, on_stage=on_stage, on_result=on_result,
            )
            meter.progress(1.0, text="Your interview plan is ready")
        except ResumeUploadError as error:
            st.error(str(error))
        except IntakeIntegrationError as error:
            st.error(f"Could not complete {error.stage}. {error}")
        else:
            st.session_state[PLAN_KEY] = prepared
            st.session_state[SCREEN_KEY] = "plan"
            st.rerun()


def _initials(name: str) -> str:
    """Up to two initials for the avatar, falling back to a neutral mark."""

    parts = [part for part in str(name).split() if part[:1].isalnum()]
    if not parts:
        return "\u2022"
    return (parts[0][:1] + (parts[-1][:1] if len(parts) > 1 else "")).upper()


def _facts_block(resume: object) -> str:
    """Stage 1 output as read-back, not judgement: what the parser saw."""

    name = getattr(resume, "name", None) or "Not stated"
    role = getattr(resume, "target_role", None) or "Not stated"
    roles = len(getattr(resume, "work_experience", []) or [])
    projects = len(getattr(resume, "projects", []) or [])

    skills = list(getattr(resume, "skills", []) or [])
    chips = "".join(
        f'<span class="ig-chip">{_safe(skill)}</span>' for skill in skills[:9]
    )
    if len(skills) > 9:
        chips += f'<span class="ig-chip ig-chip-more">+{len(skills) - 9} more</span>'

    # Counts sit in their own tiles so the name and role can carry the card.
    stats = "".join(
        f'<div class="ig-stat"><div class="ig-stat-n">{number}</div>'
        f'<div class="ig-stat-l">{label}</div></div>'
        for number, label in ((roles, "ROLES"), (projects, "PROJECTS"))
    )

    return (
        '<div class="ig-profile">'
        '<div class="ig-profile-head">'
        f'<span class="ig-avatar">{_safe(_initials(name))}</span>'
        '<span class="ig-profile-id">'
        f'<span class="ig-profile-name">{_safe(name)}</span>'
        f'<span class="ig-profile-role">{_safe(role)}</span>'
        "</span>"
        f'<span class="ig-stats">{stats}</span>'
        "</div>"
        + (f'<div class="ig-chips">{chips}</div>' if chips else "")
        + "</div>"
    )


def _evidence_rows(analysis: object) -> str:
    """
    Stage 2 output as interview coverage rather than a verdict.

    The analyzer's own docstring says an evidence level is not a skill
    rating. Showing raw enum names and a confidence float invites the
    opposite reading, so each row states plainly what the resume showed.
    Colour marks which area the row is about; the state is always spelled
    out in words beside it, never carried by colour alone.
    """

    rows: list[str] = []
    for item in analysis.competency_evidence:
        icon, label = _competency(item.competency)
        colour = _competency_color(item.competency)
        _, mark, phrasing = EVIDENCE_PRESENTATION.get(
            item.evidence_level.value,
            ("", "\u25cb", item.evidence_level.value),
        )
        state_colour = COVERAGE_COLORS.get(
            item.evidence_level.value, DEFAULT_COMPETENCY_COLOR,
        )
        rows.append(
            f'<div class="ig-ev" style="border-left-color:{colour};'
            f'background:linear-gradient(100deg,{colour}14,#ffffff 58%)">'
            f'<span class="ig-ev-mark" style="color:{colour}">{mark}</span>'
            '<span class="ig-ev-body">'
            f'<span class="ig-ev-name">{_safe(icon)} &nbsp;{_safe(label)}</span>'
            f'<div class="ig-ev-state">'
            f'<span class="ig-dot" style="background:{state_colour}"></span>'
            f"{_safe(phrasing)}</div>"
            "</span>"
            "</div>"
        )
    return "".join(rows)


def _evidence_tally(analysis: object) -> str:
    """
    A proportion bar over three colour-keyed tiles.

    The bar shows how the areas divide; the tiles name and count them, so
    each segment has a labelled swatch and the colour never has to be read
    on its own. Counts stay in ink - only the marks are coloured.
    """

    order = ("DEMONSTRATED", "PARTIAL_EVIDENCE", "UNKNOWN_NEEDS_PROBING")
    titles = ("EVIDENCED", "PARTLY EVIDENCED", "TO EXPLORE WITH YOU")

    counts = {key: 0 for key in order}
    for item in analysis.competency_evidence:
        if item.evidence_level.value in counts:
            counts[item.evidence_level.value] += 1

    total = sum(counts.values()) or 1

    segments = "".join(
        f'<span class="ig-meter-seg" style="width:{counts[key] / total * 100:.2f}%;'
        f'background:{COVERAGE_COLORS[key]}"></span>'
        for key in order
        if counts[key]
    )

    tiles = "".join(
        f'<div class="ig-tally-item" style="border-top-color:{COVERAGE_COLORS[key]}">'
        f'<div class="ig-tally-n">{counts[key]}</div>'
        f'<div class="ig-tally-l">'
        f'<span class="ig-dot" style="background:{COVERAGE_COLORS[key]}"></span>'
        f"{title}</div></div>"
        for key, title in zip(order, titles)
    )

    return (
        f'<div class="ig-meter">{segments}</div>'
        f'<div class="ig-tally">{tiles}</div>'
    )


def _plan_cards(intake: object) -> str:
    """
    One compact card per area: what it is and how many questions it gets.

    The plan also carries the planner's reasoning for each allocation. That
    text says which areas are considered unproven and why they are being
    probed, so it is interview strategy rather than candidate information
    and is deliberately not rendered.
    """

    cards: list[str] = []
    for target in intake.plan.competency_targets:
        icon, label = _competency(target.competency)
        colour = _competency_color(target.competency)
        cards.append(
            f'<div class="ig-card" style="border-top:3px solid {colour}">'
            f'<div class="ig-card-title">'
            f'<span class="ig-dot" style="background:{colour}"></span>'
            f'{_safe(icon)} &nbsp;{_safe(label)}</div>'
            f'<div class="ig-card-count">{target.question_count}</div>'
            f'<div class="ig-card-meta">question(s)</div>'
            "</div>"
        )
    return '<div class="ig-grid ig-grid-compact">' + "".join(cards) + "</div>"


def _render_plan(prepared: CandidatePlan) -> None:
    """Present stages 1-3 before paying for question selection."""

    _header("plan")
    st.markdown('<div class="ig-kicker">READY TO BEGIN</div>', unsafe_allow_html=True)
    st.title("Your interview plan")
    for warning in prepared.upload.warnings:
        st.warning(warning)

    sections = (
        (SECTION_TITLES[0], _paint_profile, prepared.resume),
        (SECTION_TITLES[1], _paint_evidence, prepared.analysis),
        (SECTION_TITLES[2], _paint_plan, prepared.plan),
    )
    for title, painter, value in sections:
        st.markdown(f'<div class="ig-section-title">{title}</div>', unsafe_allow_html=True)
        painter(st.container(), value)

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
