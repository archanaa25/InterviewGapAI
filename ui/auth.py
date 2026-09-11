"""
Role gating for the two audiences this UI serves.

The candidate side is deliberately open: an interview link should not need an
account. The interviewer side is not, because it shows marking rubrics,
must-have concepts, probe priorities and interview strategy - everything the
candidate screens work to withhold.

The credential lives in the environment, never in this file. A password
committed to the repository is a password published to everyone with read
access to it, and rotating it would mean a commit.

This is an application-level gate, not an identity system: one shared
interviewer credential, no accounts, no password reset, no lockout. It keeps
the interviewer screens away from a candidate who is handed the app URL. It
is not a substitute for real auth if this is ever exposed to the internet.
"""

from __future__ import annotations

import hmac
import os
from enum import Enum


INTERVIEWER_USER_VAR = "INTERVIEWER_USERNAME"
INTERVIEWER_PASSWORD_VAR = "INTERVIEWER_PASSWORD"

DEFAULT_INTERVIEWER_USERNAME = "admin"


class Role(str, Enum):
    """Which audience a session is being served."""

    CANDIDATE = "candidate"
    INTERVIEWER = "interviewer"


class InterviewerAuthUnavailable(RuntimeError):
    """Raised when no interviewer credential is configured."""


def interviewer_username() -> str:
    """The configured interviewer login name."""

    return os.getenv(INTERVIEWER_USER_VAR) or DEFAULT_INTERVIEWER_USERNAME


def interviewer_auth_configured() -> bool:
    """True when a password is present to check against."""

    return bool(os.getenv(INTERVIEWER_PASSWORD_VAR))


def verify_interviewer(username: str, password: str) -> bool:
    """
    Check one interviewer login attempt.

    Refuses rather than admits when no password is configured: a missing
    environment variable must not turn into an open door onto the rubrics.
    """

    expected_password = os.getenv(INTERVIEWER_PASSWORD_VAR)

    if not expected_password:
        raise InterviewerAuthUnavailable(
            f"{INTERVIEWER_PASSWORD_VAR} is not set, so the interviewer view "
            "cannot be opened. Set it in the environment and restart."
        )

    # compare_digest on both fields: a plain == on the password leaks its
    # length and prefix through timing. Comparing the username the same way
    # costs nothing and keeps the two checks symmetrical.
    username_ok = hmac.compare_digest(
        (username or "").strip(),
        interviewer_username(),
    )
    password_ok = hmac.compare_digest(password or "", expected_password)

    # Evaluate both before returning so the answer does not reveal which of
    # the two fields was wrong.
    return username_ok and password_ok


__all__ = [
    "DEFAULT_INTERVIEWER_USERNAME",
    "INTERVIEWER_PASSWORD_VAR",
    "INTERVIEWER_USER_VAR",
    "InterviewerAuthUnavailable",
    "Role",
    "interviewer_auth_configured",
    "interviewer_username",
    "verify_interviewer",
]
