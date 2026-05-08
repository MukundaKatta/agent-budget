"""agent-budget — production retry/budget primitive for LLM and agent calls.

What's missing from ``tenacity`` and the SDK ``max_retries`` integers:

- LLM-aware cost cap (USD per call, accumulated across retries).
- Adversarial-loop detection — fingerprint repeated identical errors and
  abort instead of letting a prompt-injected response always-fail-validation
  burn budget (Instructor #2056).
- Structured per-attempt events with attempt #, cumulative cost,
  cumulative latency, last error, and a classification — so logging can
  distinguish a retryable mid-flight failure from a final one
  (Instructor #2222).

Quick start::

    from agent_budget import budget

    @budget(
        max_attempts=5,
        max_cost_usd=0.10,
        max_wall_clock_s=30,
        retry_on=(RateLimitError, APITimeoutError),
        fatal_on=(ContentPolicyError,),
        cost_extractor=lambda result: result.usage.cost_usd,
    )
    def extract_invoice(image_bytes: bytes) -> Invoice:
        ...
"""

from __future__ import annotations

from ._budget import budget
from ._classify import classify_exception, fingerprint_exception
from ._errors import (
    AdversarialLoopDetected,
    AgentBudgetError,
    BudgetExceeded,
)
from ._events import AttemptEvent

__version__ = "0.1.0"

__all__ = [
    "AdversarialLoopDetected",
    "AgentBudgetError",
    "AttemptEvent",
    "BudgetExceeded",
    "__version__",
    "budget",
    "classify_exception",
    "fingerprint_exception",
]
