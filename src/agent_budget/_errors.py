"""Typed errors for agent-budget."""

from __future__ import annotations

from typing import Literal


class AgentBudgetError(Exception):
    """Base for all agent-budget errors."""


class BudgetExceeded(AgentBudgetError):
    """A configured budget was exceeded before the call could succeed."""

    def __init__(
        self,
        *,
        kind: Literal["attempts", "cost_usd", "wall_clock_s"],
        limit: float,
        observed: float,
        attempts: int,
        last_error: BaseException | None = None,
    ) -> None:
        super().__init__(
            f"agent_budget {kind} budget exceeded: observed={observed} > limit={limit} "
            f"after {attempts} attempt(s)"
        )
        self.kind = kind
        self.limit = limit
        self.observed = observed
        self.attempts = attempts
        self.last_error = last_error


class AdversarialLoopDetected(AgentBudgetError):
    """The function failed identically N times in a row.

    Catches Instructor-style retry-amplification (jxnl/instructor#2056),
    where a prompt-injected or malformed LLM response always fails
    validation and silently burns budget.
    """

    def __init__(self, *, repetitions: int, fingerprint: str) -> None:
        super().__init__(
            f"adversarial loop detected: {repetitions} consecutive identical failures "
            f"(fingerprint={fingerprint!r})"
        )
        self.repetitions = repetitions
        self.fingerprint = fingerprint
