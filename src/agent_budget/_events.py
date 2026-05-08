"""Structured retry events.

Solves jxnl/instructor#2222: error/last-attempt hooks today receive only
the bare exception with no attempt_number or cumulative state, so logging
cannot distinguish a retryable mid-flight error from a final failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class AttemptEvent:
    """One observable event in a budgeted call's lifecycle."""

    kind: Literal["start", "success", "retry", "failure"]
    attempt: int
    """1-indexed attempt number."""

    cumulative_cost_usd: float
    """Sum of cost extracted from every successful sub-call so far."""

    cumulative_latency_s: float
    """Wall-clock seconds since the @budget call began."""

    last_error: BaseException | None = None
    """The exception that triggered this event, if any."""

    error_classification: Literal["retryable", "fatal", "unknown", "none"] = "none"
    """How the budget classified ``last_error``."""

    extra: dict[str, object] = field(default_factory=dict)
    """Free-form per-event annotations the caller can read in their hook."""
