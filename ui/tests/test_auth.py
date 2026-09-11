"""Tests for the interviewer credential gate."""

import pytest

from ui.auth import (
    INTERVIEWER_PASSWORD_VAR,
    INTERVIEWER_USER_VAR,
    InterviewerAuthUnavailable,
    Role,
    interviewer_auth_configured,
    interviewer_username,
    verify_interviewer,
)


# Deliberately not the deployment's real password. A credential written into
# a test is a credential published to everyone who can read the repository,
# which is the whole reason it lives in the environment instead.
TEST_USERNAME = "admin"
TEST_PASSWORD = "test-only-secret"


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv(INTERVIEWER_USER_VAR, TEST_USERNAME)
    monkeypatch.setenv(INTERVIEWER_PASSWORD_VAR, TEST_PASSWORD)


def test_correct_credentials_are_accepted(configured) -> None:
    assert verify_interviewer(TEST_USERNAME, TEST_PASSWORD) is True


def test_surrounding_whitespace_in_the_username_is_tolerated(configured) -> None:
    """A trailing space from a copy-paste is not a failed login."""

    assert verify_interviewer("  admin  ", TEST_PASSWORD) is True


@pytest.mark.parametrize(
    "username, password",
    [
        ("admin", "TEST-ONLY-SECRET"),   # password case matters
        ("admin", "test-only-secret "),  # password whitespace matters
        ("Admin", "test-only-secret"),   # username case matters
        ("candidate", "test-only-secret"),  # wrong user, right password
        ("admin", ""),                   # empty password
        ("", ""),                        # nothing supplied
    ],
)
def test_bad_credentials_are_rejected(configured, username, password) -> None:
    assert verify_interviewer(username, password) is False


def test_an_unset_password_closes_the_view_rather_than_opening_it(
    monkeypatch,
) -> None:
    """
    A missing environment variable must not become an open door.

    This is the failure that matters: the interviewer view carries the
    marking rubrics, so an unconfigured deployment has to refuse, not admit.
    """

    monkeypatch.delenv(INTERVIEWER_PASSWORD_VAR, raising=False)

    assert interviewer_auth_configured() is False

    with pytest.raises(InterviewerAuthUnavailable):
        verify_interviewer("admin", "")

    with pytest.raises(InterviewerAuthUnavailable):
        verify_interviewer("admin", "any-guess")


def test_username_defaults_and_can_be_overridden(monkeypatch) -> None:
    monkeypatch.delenv(INTERVIEWER_USER_VAR, raising=False)
    assert interviewer_username() == "admin"

    monkeypatch.setenv(INTERVIEWER_USER_VAR, "lead-interviewer")
    assert interviewer_username() == "lead-interviewer"


def test_roles_are_distinct_values() -> None:
    assert Role.CANDIDATE.value != Role.INTERVIEWER.value
