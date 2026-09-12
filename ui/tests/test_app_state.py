"""Session-state transitions the candidate flow depends on."""

from types import SimpleNamespace

import pytest

import ui.app as app


@pytest.fixture
def session(monkeypatch) -> dict:
    """Stand in for Streamlit's session state with a plain dict."""

    state: dict = {}
    monkeypatch.setattr(app.st, "session_state", state)
    return state


def _finished_interview(session: dict) -> None:
    session.update(
        {
            app.PLAN_KEY: "old plan",
            app.INTAKE_KEY: "old question set",
            app.PROGRESS_KEY: "old answers",
            app.EVALUATION_KEY: "old evaluation",
            app.RUN_PATH_KEY: "/tmp/old-run.json",
            app.PREFETCH_KEY: "cached resume",
            app.SCREEN_KEY: "results",
            app._draft_key("RAG-INT-001"): "an answer typed earlier",
        }
    )


def test_a_new_plan_discards_the_previous_interview(session) -> None:
    """Re-uploading must not leave the last interview's answers behind.

    The traces view reads these keys directly, so a surviving progress object
    showed the new upload beside the old interview's submitted answers.
    """

    _finished_interview(session)

    app._discard_interview()

    assert session[app.INTAKE_KEY] is None
    assert session[app.PROGRESS_KEY] is None
    assert session[app.EVALUATION_KEY] is None
    assert session[app.RUN_PATH_KEY] is None


def test_discarding_an_interview_keeps_the_plan_and_prefetch(session) -> None:
    """The plan being prepared is the one thing that must survive."""

    _finished_interview(session)

    app._discard_interview()

    assert session[app.PLAN_KEY] == "old plan"
    assert session[app.PREFETCH_KEY] == "cached resume"


def test_discarding_an_interview_drops_every_answer_draft(session) -> None:
    """A draft keyed by question id would otherwise cross candidates."""

    _finished_interview(session)

    app._discard_interview()

    assert not [key for key in session if key.startswith(app.DRAFT_PREFIX)]


def test_reset_clears_the_plan_as_well(session) -> None:
    _finished_interview(session)

    app._reset()

    assert session[app.PLAN_KEY] is None
    assert session[app.PREFETCH_KEY] is None
    assert session[app.PROGRESS_KEY] is None
    assert session[app.SCREEN_KEY] == "upload"


def test_clear_drafts_leaves_unrelated_session_keys_alone(session) -> None:
    session.update({app._draft_key("Q-1"): "text", "ig_report": "Retrieval"})

    app._clear_drafts()

    assert "ig_report" in session
    assert app._draft_key("Q-1") not in session
