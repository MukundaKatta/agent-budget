"""Exception classification helpers."""

from __future__ import annotations

from typing import Literal


def classify_exception(
    exc: BaseException,
    *,
    retry_on: tuple[type[BaseException], ...] = (),
    fatal_on: tuple[type[BaseException], ...] = (),
) -> Literal["retryable", "fatal", "unknown"]:
    """Classify an exception against caller-supplied retryable/fatal sets.

    Precedence: ``fatal_on`` beats ``retry_on``. An exception in neither set
    is classified ``unknown`` and the budget defaults to re-raising — never
    blindly retrying. Always passing classification through here means a
    human-readable category lands in :class:`AttemptEvent.error_classification`.
    """
    if fatal_on and isinstance(exc, fatal_on):
        return "fatal"
    if retry_on and isinstance(exc, retry_on):
        return "retryable"
    return "unknown"


def fingerprint_exception(exc: BaseException) -> str:
    """Produce a short stable fingerprint for adversarial-loop detection.

    Uses ``type(exc).__name__`` plus the first 200 chars of ``str(exc)``.
    Two retries with the same fingerprint indicate the LLM is producing
    the same failure repeatedly — Instructor #2056's retry-amplification
    pattern.
    """
    s = str(exc)
    return f"{type(exc).__name__}:{s[:200]}"
