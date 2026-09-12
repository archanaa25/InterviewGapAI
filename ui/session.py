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
    """Progress through a fixed ordered set of question IDs.

    The candidate may move back to any question they have already reached and
    change what they wrote. That makes the cursor explicit state rather than
    something derived from how many answers exist: with revision, "how many
    answers are recorded" no longer says where the candidate is standing.

    ``responses`` runs parallel to ``question_ids``. ``None`` means the
    candidate has not reached that question yet, and is deliberately distinct
    from ``""`` - an empty string is a question they saw and left blank, which
    is an explicit skip.
    """

    question_ids: tuple[str, ...]
    responses: tuple[str | None, ...] = ()
    cursor: int = 0
    submitted: bool = False

    @classmethod
    def start(cls, question_ids: tuple[str, ...]) -> "InterviewProgress":
        """Start only when the backend supplied a non-empty unique question set."""

        if not question_ids:
            raise InterviewStateError("An interview needs at least one question.")
        if len(question_ids) != len(set(question_ids)):
            raise InterviewStateError("Interview question IDs must be unique.")
        return cls(
            question_ids=question_ids,
            responses=(None,) * len(question_ids),
        )

    @property
    def current_index(self) -> int:
        """Return the zero-based position currently shown to the candidate."""

        return self.cursor

    @property
    def is_final_question(self) -> bool:
        """Return whether the current question is the final frozen question."""

        return self.cursor == len(self.question_ids) - 1

    @property
    def is_first_question(self) -> bool:
        """Return whether there is anything behind the candidate to go back to."""

        return self.cursor == 0

    @property
    def answers(self) -> tuple[Answer, ...]:
        """Every reached question as an answer, in interview order.

        Questions the candidate has not reached are absent rather than blank,
        so a mid-interview record never claims a skip the candidate has not
        made yet.
        """

        return tuple(
            Answer(question_id=question_id, text=text)
            for question_id, text in zip(self.question_ids, self.responses)
            if text is not None
        )

    def response_at(self, index: int) -> str | None:
        """Return what the candidate wrote for one position, if anything."""

        if not 0 <= index < len(self.question_ids):
            raise InterviewStateError("No such question in this interview.")
        return self.responses[index]

    @property
    def is_revisiting(self) -> bool:
        """Return whether the current question already carries an answer."""

        return self.responses[self.cursor] is not None

    def record_current(self, text: str) -> "InterviewProgress":
        """Save the current answer and move to the next question.

        Recording no longer submits on its own. A candidate who steps back to
        revise and then works forward again would otherwise be submitted by
        the act of re-saving their final answer, without ever asking to be.
        """

        target = self.cursor if self.is_final_question else self.cursor + 1
        return self._write(text, cursor=target)

    def go_previous(self, text: str) -> "InterviewProgress":
        """Keep what is on screen, then step back one question.

        Anything typed is saved rather than discarded: a candidate who
        navigates away mid-sentence has not asked to lose the sentence.

        Stepping back off a blank question the candidate has never answered
        records nothing, because that is not a skip. Pressing Next on a blank
        is a skip; passing back through one is not, and a run file read by an
        interviewer mid-interview should not claim otherwise. Blanking an
        answer that does exist is a real edit and is kept.
        """

        if self.is_first_question:
            raise InterviewStateError("The first question has nothing before it.")
        if not text.strip() and not self.is_revisiting:
            return self._move(self.cursor - 1)
        return self._write(text, cursor=self.cursor - 1)

    def submit(self, text: str) -> "InterviewProgress":
        """Record the final answer and close the interview to further edits."""

        if not self.is_final_question:
            raise InterviewStateError(
                "The interview can only be submitted from its final question."
            )
        return self._write(text, cursor=self.cursor, submitted=True)

    def _move(self, cursor: int) -> "InterviewProgress":
        """Move the cursor without recording anything at the old position."""

        if self.submitted:
            raise InterviewStateError("The interview has already been submitted.")
        return InterviewProgress(
            question_ids=self.question_ids,
            responses=self.responses,
            cursor=cursor,
            submitted=False,
        )

    def _write(
        self,
        text: str,
        *,
        cursor: int,
        submitted: bool = False,
    ) -> "InterviewProgress":
        """Replace the current response and move the cursor in one step."""

        if self.submitted:
            raise InterviewStateError("The interview has already been submitted.")

        responses = list(self.responses)
        responses[self.cursor] = text.strip()
        return InterviewProgress(
            question_ids=self.question_ids,
            responses=tuple(responses),
            cursor=cursor,
            submitted=submitted,
        )

    @property
    def answered_count(self) -> int:
        """Count reached questions carrying a non-blank answer."""

        return sum(not answer.skipped for answer in self.answers)

    @property
    def skipped_count(self) -> int:
        """Count reached questions the candidate left blank."""

        return sum(answer.skipped for answer in self.answers)


__all__ = ["Answer", "InterviewProgress", "InterviewStateError"]
