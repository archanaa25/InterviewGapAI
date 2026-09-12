"""Tests for candidate navigation and the final-submission boundary."""

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

    progress = progress.submit("Final answer")
    assert progress.submitted
    assert progress.answered_count == 2
    assert progress.skipped_count == 1


def test_reaching_the_last_question_does_not_submit_on_its_own() -> None:
    """Submission stays a deliberate act, not a side effect of saving."""

    progress = InterviewProgress.start(("Q-1", "Q-2"))
    progress = progress.record_current("First answer")
    progress = progress.record_current("Last answer")

    assert not progress.submitted
    assert progress.current_index == 1


def test_submitted_interview_cannot_accept_more_answers() -> None:
    progress = InterviewProgress.start(("Q-1",)).submit("Done")

    with pytest.raises(InterviewStateError):
        progress.record_current("Duplicate")


def test_question_ids_must_be_non_empty_and_unique() -> None:
    with pytest.raises(InterviewStateError):
        InterviewProgress.start(())

    with pytest.raises(InterviewStateError):
        InterviewProgress.start(("Q-1", "Q-1"))


class TestRevisingAnAnswer:
    def test_going_back_returns_the_earlier_answer_to_the_candidate(self) -> None:
        progress = InterviewProgress.start(("Q-1", "Q-2"))
        progress = progress.record_current("First answer")

        progress = progress.go_previous("")

        assert progress.current_index == 0
        assert progress.response_at(0) == "First answer"
        assert progress.is_revisiting is True

    def test_a_revised_answer_replaces_the_original(self) -> None:
        progress = InterviewProgress.start(("Q-1", "Q-2"))
        progress = progress.record_current("First draft")
        progress = progress.go_previous("")
        progress = progress.record_current("Second draft")

        assert [answer.text for answer in progress.answers] == ["Second draft"]
        assert progress.current_index == 1

    def test_navigating_back_keeps_what_was_typed_on_screen(self) -> None:
        """Stepping back is not a request to throw away an unfinished answer."""

        progress = InterviewProgress.start(("Q-1", "Q-2"))
        progress = progress.record_current("First answer")

        progress = progress.go_previous("Half-written second answer")

        assert progress.response_at(1) == "Half-written second answer"

    def test_the_first_question_has_nothing_behind_it(self) -> None:
        progress = InterviewProgress.start(("Q-1", "Q-2"))

        assert progress.is_first_question is True
        with pytest.raises(InterviewStateError):
            progress.go_previous("")

    def test_a_submitted_interview_can_no_longer_be_revised(self) -> None:
        progress = InterviewProgress.start(("Q-1", "Q-2"))
        progress = progress.record_current("First answer")
        progress = progress.submit("Second answer")

        with pytest.raises(InterviewStateError):
            progress.go_previous("Too late")

    def test_revising_a_skip_into_an_answer_moves_the_counts(self) -> None:
        progress = InterviewProgress.start(("Q-1", "Q-2"))
        progress = progress.record_current("")
        assert (progress.answered_count, progress.skipped_count) == (0, 1)

        progress = progress.go_previous("")
        progress = progress.record_current("Thought better of it")

        assert (progress.answered_count, progress.skipped_count) == (1, 0)


class TestUnreachedQuestions:
    def test_unreached_questions_are_not_counted_as_skips(self) -> None:
        """A mid-interview record must not claim skips not yet made."""

        progress = InterviewProgress.start(("Q-1", "Q-2", "Q-3"))
        progress = progress.record_current("Only answer so far")

        assert progress.skipped_count == 0
        assert [answer.question_id for answer in progress.answers] == ["Q-1"]

    def test_a_blank_answer_differs_from_an_unreached_question(self) -> None:
        progress = InterviewProgress.start(("Q-1", "Q-2"))
        progress = progress.record_current("")

        assert progress.response_at(0) == ""
        assert progress.response_at(1) is None

    def test_submission_leaves_every_question_recorded(self) -> None:
        progress = InterviewProgress.start(("Q-1", "Q-2"))
        progress = progress.record_current("First")
        progress = progress.submit("Second")

        assert len(progress.answers) == 2

    def test_submitting_early_is_refused(self) -> None:
        progress = InterviewProgress.start(("Q-1", "Q-2"))

        with pytest.raises(InterviewStateError, match="final question"):
            progress.submit("Not yet")

    def test_response_at_rejects_a_position_outside_the_interview(self) -> None:
        progress = InterviewProgress.start(("Q-1",))

        with pytest.raises(InterviewStateError):
            progress.response_at(5)


class TestSteppingBackOffABlank:
    def test_passing_back_over_an_untouched_question_records_no_skip(self) -> None:
        """Only pressing Next on a blank is a skip; walking back over it is not."""

        progress = InterviewProgress.start(("Q-1", "Q-2"))
        progress = progress.record_current("First answer")

        progress = progress.go_previous("")

        assert progress.response_at(1) is None
        assert progress.skipped_count == 0

    def test_clearing_an_existing_answer_is_kept_as_a_deliberate_edit(self) -> None:
        progress = InterviewProgress.start(("Q-1", "Q-2"))
        progress = progress.record_current("First answer")
        progress = progress.record_current("Second answer")
        progress = progress.go_previous("")

        assert progress.response_at(1) == ""
        assert progress.skipped_count == 1
