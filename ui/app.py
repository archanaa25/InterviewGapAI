"""Candidate-facing Streamlit flow over the existing InterviewGapAI backend."""

from __future__ import annotations

import hashlib
import html
import json
import sys
from datetime import datetime
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

from src.observability import configure_observability, log_event

# Application startup owns configuration (see docs/OBSERVABILITY.md). Without
# this, src.observability's logger has no handler and every stage failure
# vanishes silently instead of reaching stdout as a structured event.
# Streamlit re-executes this module on every rerun; repeated calls replace
# the handler rather than duplicate it, so that is safe here.
configure_observability()

from ui.gateway import (
    CandidateIntake,
    CandidatePlan,
    IntakeIntegrationError,
    build_candidate_plan,
    prefetch_resume,
    resolve_interview_questions,
)
from ui.resume_upload import (
    ResumeUploadError,
    SUPPORTED_RESUME_TYPES,
    extract_resume,
)
from ui.auth import (
    INTERVIEWER_PASSWORD_VAR,
    InterviewerAuthUnavailable,
    Role,
    interviewer_auth_configured,
    interviewer_username,
    verify_interviewer,
)
from ui.answer_store import AnswerStoreError, load_run, save_run, saved_runs
from ui.session import InterviewProgress
from ui.styles import APP_STYLES


SCREEN_KEY = "ig_screen"
PLAN_KEY = "ig_plan"
INTAKE_KEY = "ig_intake"
PROGRESS_KEY = "ig_progress"
PREFETCH_KEY = "ig_prefetch"
ROLE_KEY = "ig_role"
RUN_PATH_KEY = "ig_run_path"

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
    st.session_state.setdefault(PREFETCH_KEY, None)
    # Candidate is the default audience: an interview link should not need an
    # account. Only a verified sign-in ever writes the interviewer role.
    st.session_state.setdefault(ROLE_KEY, Role.CANDIDATE.value)
    st.session_state.setdefault(RUN_PATH_KEY, None)


def _reset() -> None:
    """Discard UI state without mutating backend artifacts."""

    st.session_state[SCREEN_KEY] = "upload"
    st.session_state[PLAN_KEY] = None
    st.session_state[INTAKE_KEY] = None
    st.session_state[PROGRESS_KEY] = None
    st.session_state[PREFETCH_KEY] = None
    st.session_state[RUN_PATH_KEY] = None


def _sign_out() -> None:
    """Drop interviewer access and return to the candidate landing."""

    _reset()
    st.session_state[ROLE_KEY] = Role.CANDIDATE.value


def _header(active: str, *, steps: bool = True, sign_in: bool = False) -> None:
    """
    Render the product mark, and optionally the journey and a sign-in button.

    The sign-in button is a real widget rather than a link inside the header
    markup, because only a widget can change screen on click.
    """

    journey = (
        ("upload", "1. UPLOAD"),
        ("plan", "2. PLAN"),
        ("interview", "3. INTERVIEW"),
        ("results", "4. RESULTS"),
    )
    markup = "<span>›</span>".join(
        f'<span class="ig-step {"active" if key == active else ""}">{label}</span>'
        for key, label in journey
    ) if steps else ""

    brand, action = st.columns([5, 1.35], gap="small")

    with brand:
        st.markdown(
            f"""
            <div class="ig-header">
              <div class="ig-brand"><span class="ig-mark">AI</span><span>INTERVIEW<br>GAP AI</span></div>
              <div class="ig-steps">{markup}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with action:
        if sign_in and st.button(
            "Sign in", key="ig-top-signin", use_container_width=True,
        ):
            st.session_state[SCREEN_KEY] = "signin"
            st.rerun()


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

    # sign_in=True puts the interviewer door in the top-right of every
    # candidate screen; it is the only route to the credential form.
    _header("upload", sign_in=True)

    hero_column, rail_column = st.columns([1.25, 1], gap="large")

    with hero_column:
        _render_hero()

        st.markdown(
            '<p class="ig-upload-head">Upload your resume</p>'
            '<p class="ig-upload-formats">PDF, DOCX, DOC, CSV, MD or '
            "MARKDOWN · Max 10 MB</p>",
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader(
            "Upload your resume",
            type=list(SUPPORTED_RESUME_TYPES),
            help="PDF, DOCX, DOC, CSV, MD, or MARKDOWN; maximum 10 MB.",
            max_upload_size=10,
            # The heading above already says this; a second copy from the
            # widget's own label would repeat it.
            label_visibility="collapsed",
        )
        st.markdown(
            '<p class="ig-secure">🔒 Your data is used only to create your '
            "interview and insights.</p>",
            unsafe_allow_html=True,
        )

        document = None
        if uploaded is not None:
            try:
                document = _prepare_upload(uploaded)
            except ResumeUploadError as error:
                st.error(str(error))

        # The call to action belongs beside the illustration, not stretched
        # underneath it.
        started = st.button(
            "Start Your Interview  →",
            type="primary",
            use_container_width=True,
            disabled=document is None,
        )
        st.markdown(
            '<p class="ig-cta-note">Takes a few minutes to set up · '
            "Personalized to your goals</p>",
            unsafe_allow_html=True,
        )

    with rail_column:
        illustration = _hero_image()
        if illustration is not None:
            # A keyed container, not a markdown <div>: each st.markdown block
            # is its own element, so an unclosed div there never wraps the
            # elements that follow it. The key becomes a class to style.
            with st.container(key="ig-hero-art"):
                st.image(str(illustration), use_container_width=True)
        else:
            st.markdown(_journey_rail(), unsafe_allow_html=True)

    if not started:
        # The value strip sits under the fold on the idle landing page, and is
        # dropped once a run starts so it cannot push the live progress
        # sections off screen.
        st.markdown(_feature_strip(), unsafe_allow_html=True)

    if started:
        try:
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
                document,
                prefetched_resume=_pending_resume(document),
                on_stage=on_stage,
                on_result=on_result,
            )
            meter.progress(1.0, text="Your interview plan is ready")
        except IntakeIntegrationError as error:
            st.error(f"Could not complete {error.stage}. {error}")
        else:
            st.session_state[PLAN_KEY] = prepared
            st.session_state[SCREEN_KEY] = "plan"
            st.rerun()


def _render_signin() -> None:
    """Interviewer credentials. Reached from the sign-in button, not the flow."""

    _header("upload", steps=False)
    st.markdown('<div class="ig-kicker">INTERVIEWER SIGN-IN</div>', unsafe_allow_html=True)
    st.title("Sign in")
    st.markdown(
        '<p class="ig-signin-note">The interviewer view shows marking rubrics, '
        "evidence assessments and interview strategy, so it needs a password. "
        "Candidates do not sign in.</p>",
        unsafe_allow_html=True,
    )

    form_column, _ = st.columns([1.2, 1], gap="large")

    with form_column:
        if not interviewer_auth_configured():
            # Closed, not open, when unconfigured - say why rather than fail
            # at the login attempt.
            st.warning(
                f"Interviewer sign-in is unavailable: {INTERVIEWER_PASSWORD_VAR} "
                "is not set in the environment."
            )
        else:
            with st.form("interviewer-login"):
                username = st.text_input("Username", autocomplete="username")
                password = st.text_input(
                    "Password", type="password", autocomplete="current-password",
                )
                submitted = st.form_submit_button(
                    "Sign in", type="primary", use_container_width=True,
                )

            if submitted:
                try:
                    allowed = verify_interviewer(username, password)
                except InterviewerAuthUnavailable as error:
                    st.error(str(error))
                else:
                    if allowed:
                        st.session_state[ROLE_KEY] = Role.INTERVIEWER.value
                        st.rerun()
                    else:
                        # One message for either wrong field: which one was
                        # wrong is not the signer-in's business to learn by
                        # trial.
                        st.error("Those credentials were not accepted.")

        if st.button("← Back to upload", use_container_width=True):
            st.session_state[SCREEN_KEY] = "upload"
            st.rerun()


# The four stages of a run, shown beside the upload control.
JOURNEY = (
    ("Resume Analysis", "We read your experience and skills"),
    ("Personalized Interview", "Questions tailored to your profile"),
    ("Evidence-Based Evaluation", "Answers assessed against expected concepts"),
    ("Interview Insights", "Strengths, skill gaps and next steps"),
)

# Deliberately NOT the four stages again. The strip used to restate three of
# JOURNEY's items a few hundred pixels below it, which read as a bug rather
# than emphasis. These are the commitments a candidate cannot infer from the
# stage names.
FEATURES = (
    ("#e8f5ee", "#008300", "◔", "No surprises",
     "Marking rubrics stay hidden throughout"),
    ("#eef1fe", "#4a3aa7", "▤", "Curated question bank",
     "Reviewed AI-engineering questions, not invented on the spot"),
    ("#fdf0e8", "#eb6834", "◑", "Answer at your pace",
     "One question at a time, and skip anything you want to"),
    ("#e8f1fc", "#2a78d6", "◎", "Learning recommendations",
     "Curated topics and resources to grow further"),
)

# Drop a file at ui/assets/hero.<ext> and it replaces the journey rail in the
# right-hand column. The rail is the fallback, not the default, because an
# illustration that already carries the stage labels would repeat it.
ASSET_DIR = PROJECT_ROOT / "ui" / "assets"
HERO_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".svg")

# Checked in order, then any image in the directory. Matching on a fixed
# filename alone meant a perfectly good illustration saved under its own name
# was silently ignored and the fallback rail rendered instead.
HERO_IMAGE_PREFERRED = ("hero", "image", "landing")


def _hero_image() -> Path | None:
    """The landing illustration, if one has been saved."""

    if not ASSET_DIR.is_dir():
        return None

    images = sorted(
        path
        for path in ASSET_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in HERO_IMAGE_SUFFIXES
    )

    if not images:
        return None

    by_stem = {path.stem.lower(): path for path in images}

    for stem in HERO_IMAGE_PREFERRED:
        if stem in by_stem:
            return by_stem[stem]

    # Something image-shaped is here under another name; prefer it over the
    # fallback rail, since putting it in this folder is the whole signal.
    return images[0]


def _render_hero() -> None:
    """The headline, lede and journey rail above the upload control."""

    st.markdown(
        '<div class="ig-kicker">TECHNICAL INTERVIEWS, POWERED BY AI</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<h1 class="ig-hero-title">Turn Your Experience<br>'
        'Into <span class="ig-hero-accent">What\'s Next.</span></h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="ig-hero-lede">Take a personalized AI-engineering interview '
        "built around your resume. Get evidence-based evaluation, clear "
        "insights, and focused learning recommendations.</p>",
        unsafe_allow_html=True,
    )


def _journey_rail() -> str:
    """The four numbered steps, standing in for the mockup's illustration."""

    items = "".join(
        f'<div class="ig-rail-item"><span class="ig-rail-n">{number}</span>'
        f"<span><b>{_safe(title)}</b><i>{_safe(detail)}</i></span></div>"
        for number, (title, detail) in enumerate(JOURNEY, start=1)
    )
    return f'<div class="ig-rail">{items}</div>'


def _feature_strip() -> str:
    """Four value statements under the fold."""

    cards = "".join(
        f'<div class="ig-feature">'
        f'<span class="ig-feature-ico" style="background:{background};color:{ink}">{icon}</span>'
        f"<b>{_safe(title)}</b><i>{_safe(detail)}</i></div>"
        for background, ink, icon, title, detail in FEATURES
    )
    return f'<div class="ig-features">{cards}</div>'


def _prepare_upload(uploaded: object) -> object:
    """
    Parse the upload and start stage 1 before the candidate presses the button.

    Streamlit reruns the script the moment a file lands, which is several
    seconds before the click. Resume extraction depends only on the uploaded
    bytes, so it can start here and be waiting by the time the run begins.
    The parse and the prefetch are keyed by content, so the reruns that
    ordinary widget interaction causes do not repeat either.
    """

    data = uploaded.getvalue()
    fingerprint = hashlib.sha256(data).hexdigest()

    cached = st.session_state[PREFETCH_KEY]
    if cached is not None and cached[0] == fingerprint:
        return cached[1]

    document = extract_resume(
        filename=uploaded.name,
        data=data,
        content_type=uploaded.type,
    )
    st.session_state[PREFETCH_KEY] = (
        fingerprint,
        document,
        prefetch_resume(document),
    )
    return document


def _pending_resume(document: object) -> object:
    """The in-flight stage 1 run for this upload, if one was started."""

    cached = st.session_state[PREFETCH_KEY]
    if cached is not None and cached[0] == document.sha256:
        return cached[2]
    return None


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
            progress = InterviewProgress.start(question_ids)
            st.session_state[INTAKE_KEY] = intake
            st.session_state[PROGRESS_KEY] = progress
            st.session_state[SCREEN_KEY] = "interview"

            # Record the run as the interview opens, before any answer exists.
            # Waiting for the first answer meant an interviewer watching in
            # another tab could not even find the run in their picker while
            # the candidate sat on question one.
            _record_run(intake, progress)

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

        # Recorded after every answer, not only at submission. Streamlit gives
        # each browser tab its own session, so an interviewer watching in a
        # second tab can never see this one's in-memory state - the file is
        # the only thing both tabs share. Writing once at the end meant the
        # interview was invisible until it was over.
        _record_run(intake, updated)

        if updated.submitted:
            st.session_state[SCREEN_KEY] = "results"
        st.rerun()


def _record_run(intake: CandidateIntake, progress: InterviewProgress) -> None:
    """
    Write the interview so far, tolerating a failure.

    A recording problem is not a submission failure: the candidate answered
    the question either way, so this logs by type and lets them continue.
    """

    try:
        st.session_state[RUN_PATH_KEY] = str(save_run(intake, progress))
    except AnswerStoreError as error:
        st.session_state[RUN_PATH_KEY] = None
        log_event(
            "interview.run_not_saved",
            level="ERROR",
            error_type=type(error).__name__,
        )


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


ARTIFACT_DIR = PROJECT_ROOT / "data" / "prepared"


def _saved_candidates() -> list[str]:
    """
    Candidate IDs with something on disk: a fixture plan or a recorded run.

    Recorded runs come first because they are real interviews someone is
    waiting to read, and the fixtures are reference material.
    """

    plan_dir = ARTIFACT_DIR / "interview_plans"
    fixtures = (
        sorted(
            path.name.removesuffix("_plan.json")
            for path in plan_dir.glob("*_plan.json")
        )
        if plan_dir.is_dir()
        else []
    )

    runs = saved_runs()
    return runs + [name for name in fixtures if name not in set(runs)]


def _load_artifacts(candidate_id: str) -> dict:
    """
    Read one candidate's saved stage outputs.

    Each stage is reported separately so a missing analysis does not hide an
    extraction that ran fine.
    """

    paths = {
        "resume extraction": ARTIFACT_DIR / "resumes" / f"{candidate_id}.json",
        "resume evidence": (
            ARTIFACT_DIR / "resume_analysis" / f"{candidate_id}_analysis.json"
        ),
        "interview plan": (
            ARTIFACT_DIR / "interview_plans" / f"{candidate_id}_plan.json"
        ),
        "interview questions": (
            ARTIFACT_DIR / "interview_questions" / f"{candidate_id}_questions.json"
        ),
    }

    stages = {}

    for stage, path in paths.items():
        if not path.is_file():
            stages[stage] = None
            continue
        try:
            stages[stage] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            stages[stage] = {"error": f"{type(error).__name__}"}

    return stages


TRACE_PROSE_LIMIT = 200


def _clip(text: str, limit: int = TRACE_PROSE_LIMIT) -> str:
    """
    Shorten model prose to a glance.

    The analyzer's summary and the planner's rationale run to full paragraphs.
    The trace view is for scanning several stages at once, so it shows the
    opening and leaves the rest to the raw JSON below it.
    """

    collapsed = " ".join(str(text).split())

    if len(collapsed) <= limit:
        return collapsed

    # Cut on a word boundary rather than mid-word.
    return collapsed[:limit].rsplit(" ", 1)[0] + "…"


def _trace_summary(stage: str, payload: dict) -> list[str]:
    """A few lines saying what the stage produced, not the whole document."""

    if stage == "upload":
        lines = [
            f"**{payload.get('filename')}** · "
            f"{payload.get('format')} · "
            f"{(payload.get('size_bytes') or 0) / 1024:.1f} KB",
            f"{payload.get('characters_extracted')} characters extracted via "
            f"`{payload.get('extraction_method')}` · "
            f"candidate id `{payload.get('candidate_id')}`",
        ]
        for warning in payload.get("warnings") or []:
            lines.append(f"⚠ {warning}")
        return lines

    if stage == "interview questions":
        questions = payload.get("questions") or []
        unfilled = payload.get("unfilled_slots") or []
        lines = [
            f"**{len(questions)} questions selected** across "
            f"{len({q.get('competency') for q in questions})} competencies"
        ]
        if questions:
            relaxed = sum(
                1
                for q in questions
                if (q.get("retrieval") or {}).get("filter_relaxed")
            )
            if relaxed:
                lines.append(
                    f"{relaxed} filled from an adjacent difficulty because the "
                    "requested pool was exhausted."
                )
        for slot in unfilled:
            lines.append(f"⚠ unfilled: {slot.get('reason')}")
        for warning in payload.get("warnings") or []:
            lines.append(f"⚠ {warning}")
        return lines

    if stage == "answers":
        done = (payload.get("answered") or 0) + (payload.get("skipped") or 0)
        total = payload.get("total") or 0
        lines = [
            f"**{payload.get('answered')} answered · "
            f"{payload.get('skipped')} skipped** of {total}"
            + (
                "  — submitted"
                if payload.get("submitted")
                else f"  — in progress, {done} of {total} questions reached"
            ),
        ]
        for answer in payload.get("answers") or []:
            state = "skipped" if answer.get("skipped") else f"{answer['characters']} chars"
            lines.append(
                f"{answer['position']}. `{answer['question_id']}` — {state}"
            )
        return lines

    if stage == "resume extraction":
        return [
            f"**{payload.get('name') or 'Name not stated'}** — "
            f"{payload.get('target_role') or 'role not stated'}",
            f"{len(payload.get('skills') or [])} skills · "
            f"{len(payload.get('work_experience') or [])} roles · "
            f"{len(payload.get('projects') or [])} projects · "
            f"{len(payload.get('education') or [])} education entries",
        ]

    if stage == "resume evidence":
        evidence = payload.get("competency_evidence") or []
        tally: dict[str, int] = {}
        for item in evidence:
            level = item.get("evidence_level", "UNKNOWN")
            tally[level] = tally.get(level, 0) + 1
        lines = [
            " · ".join(f"{count} {level}" for level, count in sorted(tally.items()))
            or "No competency evidence recorded."
        ]
        # The analyzer's own summary names which areas it considers unproven,
        # which is exactly what the candidate screens withhold - so it belongs
        # here and nowhere else.
        if payload.get("overall_summary"):
            lines.append(f"_{_clip(payload['overall_summary'])}_")
        return lines

    targets = payload.get("competency_targets") or []
    distribution = payload.get("difficulty_distribution") or {}
    lines = [
        f"**{payload.get('total_questions', '?')} questions** across "
        f"{len(targets)} competencies — "
        f"{distribution.get('basic', 0)} basic · "
        f"{distribution.get('intermediate', 0)} intermediate · "
        f"{distribution.get('advanced', 0)} advanced",
    ]
    rationale = (payload.get("strategy") or {}).get("rationale")
    if rationale:
        lines.append(f"_{_clip(rationale)}_")
    return lines


def _render_interviewer() -> None:
    """Intake traces and the evaluation dashboard, behind the sign-in."""

    section, report = _interviewer_sidebar()

    title, sign_out = st.columns([3.2, 1])
    with title:
        st.markdown(
            '<div class="ig-kicker">INTERVIEWER VIEW</div>', unsafe_allow_html=True,
        )
        st.title(report if section == "Evaluation reports" and report else section)
        st.markdown(
            '<p class="ig-subtitle">'
            + (
                "Evaluation report · candidate view hidden"
                if section == "Evaluation reports"
                else f"{_safe(section)} · candidate view hidden"
            )
            + "</p>",
            unsafe_allow_html=True,
        )
    if sign_out.button("↪ Sign out", key="ig-signout", use_container_width=True):
        _sign_out()
        st.rerun()

    st.info(
        "These screens show marking rubrics, evidence assessments and "
        "interview strategy. They are withheld from the candidate view."
    )

    if section == "Intake traces":
        _render_intake_traces()
        return

    if section == "Settings":
        _render_interviewer_settings()
        return

    # Imported here so the candidate path never pays for altair/pandas.
    from ui.dashboard import render_overview, render_panel

    if section == "Dashboard":
        render_overview()
        return

    render_panel(report)


def _render_interviewer_settings() -> None:
    """Read-only runtime configuration, so a wrong model is visible not guessed."""

    import os

    st.markdown(
        '<div class="ig-panel-card-title">Runtime configuration</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Read from the environment at startup. Shown to make a misconfigured "
        "run diagnosable without reading the server log."
    )

    rows = [
        ("LLM provider", os.getenv("LLM_PROVIDER", "openai")),
        ("Resume extraction model", os.getenv("RESUME_EXTRACTION_MODEL", "(stage default)")),
        ("Resume analysis model", os.getenv("RESUME_ANALYSIS_MODEL", "(stage default)")),
        ("Interview planning model", os.getenv("INTERVIEW_PLANNING_MODEL", "(stage default)")),
        ("Pinecone index", os.getenv("PINECONE_INDEX_NAME", "(unset)")),
        ("Question namespace", os.getenv("PINECONE_QUESTION_NAMESPACE", "(unset)")),
        ("Evaluation namespace", os.getenv("PINECONE_EVALUATION_NAMESPACE", "(unset)")),
        ("LangSmith tracing", os.getenv("LANGSMITH_TRACING", "false")),
        ("Interviewer sign-in", "configured" if interviewer_auth_configured() else "NOT configured"),
    ]
    st.dataframe(
        [{"Setting": key, "Value": value} for key, value in rows],
        use_container_width=True,
        hide_index=True,
    )
    # Never render the credential itself - only whether one is present.
    st.caption(
        "Secrets are deliberately not shown: only whether a value is present."
    )


INTERVIEWER_SECTIONS = (
    "⌂  Dashboard",
    "▤  Evaluation reports",
    "▦  Intake traces",
    "⚙  Settings",
)


def _section_name(label: str) -> str:
    """The section without its leading glyph."""

    return label.split("  ", 1)[-1]


def _interviewer_sidebar() -> tuple[str, str | None]:
    """
    Sidebar navigation, with the signed-in identity pinned to the bottom.

    Returns the section and, under Reports, the chosen report. The eight
    reports live here rather than in a horizontal tab strip: eight tabs
    overflowed behind a scroll arrow, which hid the reports added most
    recently - exactly the ones worth looking at.
    """

    from ui.dashboard import PANEL_GROUPS

    with st.sidebar:
        st.markdown(
            '<div class="ig-brand"><span class="ig-mark">AI</span>'
            "<span>INTERVIEW<br>GAP AI</span></div>",
            unsafe_allow_html=True,
        )

        chosen = st.radio(
            "Section",
            INTERVIEWER_SECTIONS,
            index=1,
            label_visibility="collapsed",
        )
        section = _section_name(chosen)

        report = None
        if section == "Evaluation reports":
            st.markdown(
                '<div class="ig-subnav-title">Reports</div>', unsafe_allow_html=True,
            )
            # Grouped, and rendered as one radio per group so the group
            # headings survive: a single flat list of eight is what made the
            # tab strip unreadable in the first place.
            with st.container(key="ig-subnav"):
                report = _report_choice(PANEL_GROUPS)

        st.divider()

        name = interviewer_username()
        st.markdown(
            '<div class="ig-side-user">'
            f'<span class="ig-side-avatar">{_safe(name[:1].upper())}</span>'
            f"<span><b>{_safe(name.title())}</b><i>Administrator</i></span></div>",
            unsafe_allow_html=True,
        )

    return section, report


REPORT_KEY = "ig_report"


def _report_slug(name: str) -> str:
    """A widget key from a report name."""

    return "ig_rep_" + "".join(
        character if character.isalnum() else "_" for character in name.lower()
    )


def _report_choice(groups: tuple) -> str:
    """
    One button per report, grouped, with the current one highlighted.

    Buttons rather than a radio per group: independent radios each keep their
    own selection, so clicking in a second group left the first still showing
    one and the sidebar claimed two current reports at once. Buttons hold no
    selection state, so the only source of truth is session state.
    """

    flat = [name for _, names in groups for name in names]
    current = st.session_state.get(REPORT_KEY)
    if current not in flat:
        # Write the default back, so the highlight below and the panel the
        # main area renders are driven by the same value on the first run as
        # on every later one.
        current = flat[0]
        st.session_state[REPORT_KEY] = current

    for group, names in groups:
        st.markdown(
            f'<div class="ig-subnav-group">{_safe(group)}</div>',
            unsafe_allow_html=True,
        )
        for name in names:
            if st.button(name, key=_report_slug(name), use_container_width=True):
                st.session_state[REPORT_KEY] = name
                st.rerun()

    # Highlight the current one. A button cannot carry a checked state, so the
    # active row is styled by its own generated key.
    #
    # The selector deliberately repeats the sidebar and keyed-container
    # attributes. The base rule in styles.py sets these buttons transparent
    # through [data-testid=stSidebar] [class*=st-key-ig_rep_] button, which
    # outranks a bare .st-key-<slug> button even with !important on both, so
    # a shorter selector here silently lost and nothing ever highlighted.
    active = _report_slug(current)
    st.markdown(
        "<style>"
        f'[data-testid="stSidebar"] [class*="st-key-ig_rep_"].st-key-{active} button'
        "{background:#e8f1fc !important;border-color:#bcd9f2 !important}"
        f'[data-testid="stSidebar"] [class*="st-key-ig_rep_"].st-key-{active} button p'
        "{color:#14639e !important;font-weight:800 !important}"
        "</style>",
        unsafe_allow_html=True,
    )

    return current


# How often the traces view re-reads a run when following is switched on.
# Short enough to feel live against a candidate typing an answer, long enough
# that it is not redrawing while someone reads.
AUTO_REFRESH_SECONDS = 3

# The candidate's journey end to end. Stages absent from a source are shown
# as gaps with the reason, because "nothing here" and "never persisted" are
# different problems and only one of them is fixable by re-running.
TRACE_STAGES = (
    "upload",
    "resume extraction",
    "resume evidence",
    "interview plan",
    "interview questions",
    "answers",
)

# Why a stage can be empty. Saying this beats an unexplained blank section.
TRACE_GAPS = {
    "upload": (
        "Upload provenance exists only for a run started in this browser "
        "session; it is not written to disk."
    ),
    "interview questions": (
        "Question selection runs when the candidate presses Start interview. "
        "Saved question sets exist for only some fixture candidates."
    ),
    "answers": (
        "No completed interview recorded for this source. A run appears here "
        "once a candidate submits; fixture candidates have no answers because "
        "nobody sat their interview."
    ),
}


def _live_stages() -> dict:
    """Whatever the current browser session has produced, stage by stage."""

    prepared = st.session_state[PLAN_KEY]
    intake = st.session_state[INTAKE_KEY]
    progress = st.session_state[PROGRESS_KEY]

    stages = dict.fromkeys(TRACE_STAGES)

    if prepared is not None:
        upload = prepared.upload
        stages["upload"] = {
            "filename": upload.filename,
            "format": getattr(upload.format, "value", str(upload.format)),
            "media_type": upload.media_type,
            "size_bytes": upload.size_bytes,
            "sha256": upload.sha256,
            "candidate_id": upload.candidate_id,
            "extraction_method": upload.extraction_method,
            "characters_extracted": len(upload.text),
            "warnings": list(upload.warnings),
        }
        stages["resume extraction"] = prepared.resume.model_dump(mode="json")
        stages["resume evidence"] = prepared.analysis.model_dump(mode="json")
        stages["interview plan"] = prepared.plan.model_dump(mode="json")

    # Stage 4 only exists once the candidate starts the interview, which is a
    # separate click from preparing the plan.
    if intake is not None:
        stages["interview questions"] = intake.question_set.model_dump(mode="json")

    if progress is not None:
        asked = {}
        if intake is not None:
            asked = {q.question_id: q for q in intake.question_set.questions}
        stages["answers"] = {
            "submitted": progress.submitted,
            "answered": progress.answered_count,
            "skipped": progress.skipped_count,
            "total": len(progress.question_ids),
            "answers": [
                {
                    "position": index,
                    "question_id": answer.question_id,
                    "question": getattr(asked.get(answer.question_id), "question", None),
                    "skipped": answer.skipped,
                    "characters": len(answer.text),
                    "text": answer.text,
                }
                for index, answer in enumerate(progress.answers, start=1)
            ],
        }

    return stages


def _render_intake_traces() -> None:
    """The candidate's whole journey, stage by stage, with the strategy shown."""

    live = _live_stages()
    has_live = any(value is not None for value in live.values())
    candidates = _saved_candidates()

    if not has_live and not candidates:
        st.warning(
            "No intake to show. Run a candidate through the candidate view, or "
            f"save artifacts under {ARTIFACT_DIR.name}/."
        )
        return

    # The picker gives up width so the two controls beside it can show
    # their labels: at a narrower split they truncated to "A…" and "↻ …".
    picker, follow, refresh = st.columns([2.4, 1.5, 1.35], gap="small")
    sources = (["This session's run"] if has_live else []) + candidates
    with picker:
        choice = st.selectbox("Intake", sources)
    with follow:
        st.markdown('<div class="ig-refresh-pad"></div>', unsafe_allow_html=True)
        auto = st.toggle(
            "Auto",
            key="ig-traces-auto",
            help=(
                f"Re-read this run every {AUTO_REFRESH_SECONDS} seconds, to "
                "follow an interview happening in another tab. Leave it off "
                "when reading raw JSON: each refresh closes the expanders."
            ),
        )
    with refresh:
        st.markdown('<div class="ig-refresh-pad"></div>', unsafe_allow_html=True)
        # Streamlit reruns on interaction, not on a file changing, so an
        # interview in progress in another tab needs a re-read either way.
        if st.button(
            "↻ Now",
            key="ig-traces-refresh",
            use_container_width=True,
            help="Re-read this run immediately.",
        ):
            st.rerun()

    # Only the stage list polls. A fragment reruns on its own without
    # re-running the page around it, so the source picker keeps its value and
    # the sidebar does not flicker every few seconds.
    @st.fragment(run_every=AUTO_REFRESH_SECONDS if auto else None)
    def _stages() -> None:
        stages = _resolve_stages(choice, live if has_live else {})

        reached = sum(1 for value in stages.values() if value)
        status, note = st.columns([3, 1.4])
        status.caption(
            f"{reached} of {len(TRACE_STAGES)} stages have output for this run."
        )
        if auto:
            # Say when it last looked, so a stalled poll is visible rather
            # than indistinguishable from an interview that stopped.
            note.caption(
                f"↻ {datetime.now().strftime('%H:%M:%S')}",
            )

        # The picker's options are built outside this fragment, so a run that
        # started after this page loaded cannot appear in it on a poll alone.
        # Saying so beats an interviewer waiting on a list that will not change.
        appeared = [name for name in saved_runs() if name not in set(sources)]
        if appeared:
            st.info(
                f"A new interview started: {', '.join(appeared)}. "
                "Press ↻ Now to add it to the list above."
            )

        for stage, payload in stages.items():
            st.markdown(
                f'<div class="ig-section-title">{stage.title()}</div>',
                unsafe_allow_html=True,
            )

            if not payload:
                st.caption(TRACE_GAPS.get(stage, "No saved output for this stage."))
                continue
            if "error" in payload and len(payload) == 1:
                st.error(f"Could not read this stage ({payload['error']}).")
                continue

            for line in _trace_summary(stage, payload):
                st.markdown(line)

            # Summary first, full document behind a click: the analysis alone
            # runs to seven competencies with evidence items and sources.
            with st.expander("Raw JSON"):
                st.json(payload, expanded=False)

    _stages()


def _resolve_stages(choice: str, live: dict) -> dict:
    """
    The stages for one source, re-read from disk on every call.

    Separated out so the polling fragment can call it again: reusing a dict
    captured once would poll and redraw the same data for ever.
    """

    if live and choice == "This session's run":
        # The live session is authoritative for its own run, and its answers
        # are in memory before they reach the file.
        return _live_stages()

    saved = _load_artifacts(choice)
    stages = {stage: saved.get(stage) for stage in TRACE_STAGES}

    # A recorded run carries every stage of the interview it belongs to, so it
    # wins over the fixture files: those exist only for synthetic candidates
    # and would be a different person's intake anyway.
    run = load_run(choice)
    if run:
        stages["answers"] = run
        stages["upload"] = run.get("upload") or stages["upload"]
        for stage, payload in (run.get("stages") or {}).items():
            if stage in stages and payload:
                stages[stage] = payload

    return stages


def main() -> None:
    """Render the current UI-owned candidate state."""

    st.set_page_config(
        page_title="InterviewGapAI",
        page_icon="✦",
        layout="centered",
        # Expanded for the interviewer console; the candidate screens hide
        # the sidebar entirely below, since it is theirs alone.
        initial_sidebar_state="expanded",
    )
    st.markdown(APP_STYLES, unsafe_allow_html=True)
    _initialize_state()

    role = st.session_state[ROLE_KEY]
    screen = st.session_state[SCREEN_KEY]

    if role != Role.INTERVIEWER.value:
        # Only the interviewer console has sidebar navigation. Leaving an
        # empty rail (and its expander arrow) on the candidate screens would
        # advertise a door they cannot open.
        st.markdown(
            "<style>[data-testid='stSidebar'],"
            "[data-testid='stSidebarCollapsedControl'],"
            "[data-testid='collapsedControl']{display:none !important}</style>",
            unsafe_allow_html=True,
        )

    # The interviewer role is only ever written to session state by a verified
    # sign-in, so reaching these screens means the password was supplied in
    # this session.
    if role == Role.INTERVIEWER.value:
        _render_interviewer()
        return

    if screen == "signin":
        _render_signin()
        return

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
