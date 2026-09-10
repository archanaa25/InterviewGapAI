"""Pure UI session state for asking a frozen contributor question set."""

from __future__ import annotations

from dataclasses import dataclass


class InterviewStateError(ValueError):
    """Raised when the UI attempts an invalid interview transition."""


@dataclass(frozen=True, slots=True)
class Answer:
    """One candidate answer captured without evaluating it."""

    question_id: str
    text: str

    @property
    def skipped(self) -> bool:
        """Treat a deliberately blank submission as a skip."""

        return not self.text.strip()


@dataclass(frozen=True, slots=True)
class InterviewProgress:
    """Immutable progress through a fixed ordered set of question IDs."""

    question_ids: tuple[str, ...]
    answers: tuple[Answer, ...] = ()
    submitted: bool = False

    @classmethod
    def start(cls, question_ids: tuple[str, ...]) -> "InterviewProgress":
        """Start only when the backend supplied a non-empty unique question set."""

        if not question_ids:
            raise InterviewStateError("An interview needs at least one question.")
        if len(question_ids) != len(set(question_ids)):
            raise InterviewStateError("Interview question IDs must be unique.")
        return cls(question_ids=question_ids)

    @property
    def current_index(self) -> int:
        """Return the zero-based position currently shown to the candidate."""

        return min(len(self.answers), len(self.question_ids) - 1)

    @property
    def is_final_question(self) -> bool:
        """Return whether the current question is the final frozen question."""

        return len(self.answers) == len(self.question_ids) - 1

    def record_current(self, text: str) -> "InterviewProgress":
        """Save the current answer and submit only after the final question."""

        if self.submitted:
            raise InterviewStateError("The interview has already been submitted.")
        if len(self.answers) >= len(self.question_ids):
            raise InterviewStateError("No unanswered interview question remains.")

        answer = Answer(
            question_id=self.question_ids[len(self.answers)],
            text=text.strip(),
        )
        updated = self.answers + (answer,)
        return InterviewProgress(
            question_ids=self.question_ids,
            answers=updated,
            submitted=len(updated) == len(self.question_ids),
        )

    @property
    def answered_count(self) -> int:
        """Count non-blank candidate answers."""

        return sum(not answer.skipped for answer in self.answers)

    @property
    def skipped_count(self) -> int:
        """Count explicit blank submissions."""

        return sum(answer.skipped for answer in self.answers)


__all__ = ["Answer", "InterviewProgress", "InterviewStateError"]
