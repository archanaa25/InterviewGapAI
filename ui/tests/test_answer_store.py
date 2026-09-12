"""Tests for persisting a completed interview."""

from types import SimpleNamespace

import pytest

from ui import answer_store
from ui.answer_store import AnswerStoreError, load_run, save_run, saved_runs
from ui.session import InterviewProgress


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch, tmp_path):
    """Never write a real candidate's answers during a test run."""

    monkeypatch.setattr(answer_store, "RUN_DIR", tmp_path / "runs")


class _Dumpable(SimpleNamespace):
    """Stands in for a Pydantic stage output, which the store serialises."""

    def __init__(self, payload: dict, **attributes) -> None:
        super().__init__(**attributes)
        self._payload = payload

    def model_dump(self, mode: str = "python") -> dict:
        return dict(self._payload)


def _intake(candidate_id: str = "upload-abc123"):
    question = SimpleNamespace(
        question_id="RAG-PROD-ADV-001",
        question="Describe a production RAG architecture.",
        competency=SimpleNamespace(value="rag"),
        difficulty="advanced",
    )
    return SimpleNamespace(
        upload=SimpleNamespace(
            filename="cv.pdf",
            format=SimpleNamespace(value="pdf"),
            media_type="application/pdf",
            size_bytes=2048,
            sha256="a" * 64,
            candidate_id=candidate_id,
            extraction_method="pypdf",
            text="Resume text",
            warnings=(),
        ),
        resume=_Dumpable({"candidate_id": candidate_id, "name": "Test Candidate"}),
        analysis=_Dumpable({"candidate_id": candidate_id, "competency_evidence": []}),
        plan=_Dumpable({"candidate_id": candidate_id}, candidate_id=candidate_id),
        question_set=_Dumpable(
            {"questions": [{"question_id": question.question_id}]},
            questions=[question],
        ),
    )


def _progress(text: str = "Separate ingestion from query.") -> InterviewProgress:
    return InterviewProgress.start(("RAG-PROD-ADV-001",)).submit(text)


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


def test_every_earlier_stage_is_stored_too() -> None:
    """
    A real upload has no files under data/prepared/, so the run must carry
    its own resume, evidence, plan and question set - otherwise an
    interviewer in another session sees answers with nothing behind them.
    """

    save_run(_intake(), _progress())
    run = load_run("upload-abc123")

    assert set(run["stages"]) == {
        "resume extraction",
        "resume evidence",
        "interview plan",
        "interview questions",
    }
    for payload in run["stages"].values():
        assert payload


def test_upload_provenance_survives_the_session() -> None:
    save_run(_intake(), _progress())
    upload = load_run("upload-abc123")["upload"]

    assert upload["filename"] == "cv.pdf"
    assert upload["sha256"] == "a" * 64
    assert upload["characters_extracted"] == len("Resume text")


def _prepared(candidate_id: str = "upload-abc123"):
    """A CandidatePlan: stages 1-3 only, before any interview exists."""

    intake = _intake(candidate_id)
    return SimpleNamespace(
        upload=intake.upload,
        resume=intake.resume,
        analysis=intake.analysis,
        plan=intake.plan,
    )


def test_an_intake_is_recorded_before_any_interview_starts() -> None:
    """
    Uploading a resume is the first moment someone looks for a candidate in
    another tab, so the record cannot wait for question selection.
    """

    from ui.answer_store import save_intake

    save_intake(_prepared())
    run = load_run("upload-abc123")

    assert run is not None
    assert run["submitted"] is False
    assert run["answers"] == []
    assert set(run["stages"]) == {
        "resume extraction", "resume evidence", "interview plan",
    }
    # No interview yet, so there is no question count to claim.
    assert run["total"] is None


def test_the_completed_run_replaces_the_intake_record() -> None:
    from ui.answer_store import save_intake

    save_intake(_prepared())
    assert load_run("upload-abc123")["answers"] == []

    save_run(_intake(), _progress())
    run = load_run("upload-abc123")

    assert len(run["answers"]) == 1
    assert "interview questions" in run["stages"]
    assert run["total"] == 1


class _Evaluation:
    """Stands in for InterviewEvaluation, whose counts are properties."""

    def __init__(self, evaluated=2, skipped=1, review=1):
        self.evaluated_count = evaluated
        self.skipped_count = skipped
        self.review_count = review

    def model_dump(self, mode: str = "python") -> dict:
        return {
            "candidate_id": "upload-abc123",
            "questions": [
                {
                    "question_id": "RAG-PROD-ADV-001",
                    "status": "EVALUATED",
                    # A real ConceptJudgementStatus value. "MET" is not one,
                    # and a fixture inventing a status lets a status-counting
                    # bug pass here - the trace view had exactly that bug.
                    "concept_judgements": [
                        {"concept": "c", "status": "DEMONSTRATED"}
                    ],
                }
            ],
        }


def test_an_evaluation_is_attached_to_the_interview_it_judged() -> None:
    from ui.answer_store import save_evaluation

    save_run(_intake(), _progress())
    save_evaluation("upload-abc123", _Evaluation())

    run = load_run("upload-abc123")

    # The answers must survive: an evaluation without the work it judged is
    # not reviewable, which is why this merges rather than writing beside.
    assert len(run["answers"]) == 1
    assert run["answers"][0]["text"] == "Separate ingestion from query."

    evaluation = run["evaluation"]
    assert evaluation["evaluated_count"] == 2
    assert evaluation["skipped_count"] == 1
    assert evaluation["review_count"] == 1
    assert evaluation["result"]["questions"][0]["question_id"] == "RAG-PROD-ADV-001"
    assert evaluation["evaluated_at"]


def test_an_evaluation_without_a_recorded_interview_is_refused() -> None:
    """
    An evaluation alone is not worth keeping, and silently creating a record
    for one would produce a judgement with no answers behind it.
    """

    from ui.answer_store import save_evaluation

    with pytest.raises(AnswerStoreError):
        save_evaluation("upload-never-recorded", _Evaluation())


def test_re_evaluating_replaces_the_previous_judgement() -> None:
    from ui.answer_store import save_evaluation

    save_run(_intake(), _progress())
    save_evaluation("upload-abc123", _Evaluation(evaluated=1))
    save_evaluation("upload-abc123", _Evaluation(evaluated=3))

    assert load_run("upload-abc123")["evaluation"]["evaluated_count"] == 3


def test_no_rubric_reaches_the_stored_evaluation() -> None:
    """The marking scheme stays in the corpus, not beside a candidate's work."""

    from ui.answer_store import save_evaluation

    save_run(_intake(), _progress())
    save_evaluation("upload-abc123", _Evaluation())

    stored = repr(load_run("upload-abc123")["evaluation"])
    for forbidden in ("expected_concepts", "must_have", "bonus"):
        assert forbidden not in stored
