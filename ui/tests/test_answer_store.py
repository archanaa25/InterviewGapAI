"""Tests for persisting a completed interview."""

from types import SimpleNamespace

import pytest

from ui import answer_store
from ui.answer_store import AnswerStoreError, load_run, save_run, saved_runs
from ui.session import Answer, InterviewProgress


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch, tmp_path):
    """Never write a real candidate's answers during a test run."""

    monkeypatch.setattr(answer_store, "RUN_DIR", tmp_path / "runs")


def _intake(candidate_id: str = "upload-abc123"):
    question = SimpleNamespace(
        question_id="RAG-PROD-ADV-001",
        question="Describe a production RAG architecture.",
        competency=SimpleNamespace(value="rag"),
        difficulty="advanced",
    )
    return SimpleNamespace(
        upload=SimpleNamespace(
            filename="cv.pdf", sha256="a" * 64, extraction_method="pypdf",
        ),
        plan=SimpleNamespace(candidate_id=candidate_id),
        question_set=SimpleNamespace(questions=[question]),
    )


def _progress(text: str = "Separate ingestion from query.") -> InterviewProgress:
    return InterviewProgress(
        question_ids=("RAG-PROD-ADV-001",),
        answers=(Answer(question_id="RAG-PROD-ADV-001", text=text),),
        submitted=True,
    )


def test_a_completed_interview_can_be_read_back() -> None:
    path = save_run(_intake(), _progress())

    assert path.is_file()

    run = load_run("upload-abc123")
    assert run is not None
    assert run["submitted"] is True
    assert run["answered"] == 1
    assert run["skipped"] == 0
    assert run["answers"][0]["text"] == "Separate ingestion from query."
    # The question text is copied in so the run still reads if the corpus is
    # re-curated later.
    assert run["answers"][0]["question"].startswith("Describe a production")
    assert run["answers"][0]["competency"] == "rag"


def test_a_skipped_answer_is_recorded_as_skipped() -> None:
    save_run(_intake(), _progress(text="   "))

    run = load_run("upload-abc123")
    assert run["answers"][0]["skipped"] is True
    assert run["answered"] == 0
    assert run["skipped"] == 1


def test_no_rubric_or_evaluation_is_stored() -> None:
    """This module records what happened; it does not judge it."""

    save_run(_intake(), _progress())
    run = load_run("upload-abc123")

    serialised = repr(run)
    for forbidden in ("expected_concepts", "must_have", "score", "evaluation"):
        assert forbidden not in serialised


def test_an_unknown_candidate_reads_back_as_none() -> None:
    assert load_run("upload-never-seen") is None


def test_saved_runs_lists_what_was_recorded() -> None:
    assert saved_runs() == []

    save_run(_intake("upload-one"), _progress())
    save_run(_intake("upload-two"), _progress())

    assert set(saved_runs()) == {"upload-one", "upload-two"}


@pytest.mark.parametrize("candidate_id", ["../escape", "..", "/", ""])
def test_a_candidate_id_is_never_trusted_as_a_path(candidate_id) -> None:
    """
    The id arrives from an upload, so it cannot select where a file lands.

    "../escape" sanitises to a usable name rather than climbing out of the
    run directory; ids with nothing usable left are refused outright.
    """

    if candidate_id in {"..", "/", ""}:
        with pytest.raises(AnswerStoreError):
            save_run(_intake(candidate_id), _progress())
        return

    path = save_run(_intake(candidate_id), _progress())
    assert path.parent == answer_store.RUN_DIR


def test_the_run_directory_is_created_on_first_write() -> None:
    assert not answer_store.RUN_DIR.exists()

    save_run(_intake(), _progress())

    assert answer_store.RUN_DIR.is_dir()
