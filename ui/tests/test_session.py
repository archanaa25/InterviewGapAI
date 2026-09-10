"""Tests for the candidate-facing final-submission boundary."""

import pytest

from ui.session import InterviewProgress, InterviewStateError


def test_answers_are_collected_before_final_submission() -> None:
    progress = InterviewProgress.start(("Q-1", "Q-2", "Q-3"))

    progress = progress.record_current("First answer")
    assert not progress.submitted
    assert progress.current_index == 1

    progress = progress.record_current("")
    assert not progress.submitted
    assert progress.current_index == 2

    progress = progress.record_current("Final answer")
    assert progress.submitted
    assert progress.answered_count == 2
    assert progress.skipped_count == 1


def test_submitted_interview_cannot_accept_more_answers() -> None:
    progress = InterviewProgress.start(("Q-1",)).record_current("Done")

    with pytest.raises(InterviewStateError):
        progress.record_current("Duplicate")


def test_question_ids_must_be_non_empty_and_unique() -> None:
    with pytest.raises(InterviewStateError):
        InterviewProgress.start(())

    with pytest.raises(InterviewStateError):
        InterviewProgress.start(("Q-1", "Q-1"))
