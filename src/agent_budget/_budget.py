"""@budget decorator: wraps any callable with cost/attempts/wall-clock budgets.

Why exist when ``tenacity`` is right there:

- ``tenacity`` is generic. It has no notion of LLM cost.
- Anthropic / OpenAI SDK ``max_retries`` is an integer; no cost cap, no
  attempt-event metadata, no adversarial-loop detection (Instructor #2056).
- Instructor's hooks don't expose ``attempt_number`` / cumulative state
  (Instructor #2222).

``@budget`` adds the three things that matter for production LLM-shaped
work: a per-call USD cap, structured per-attempt events, and adversarial
loop detection that aborts before the loop bills you to oblivion.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from ._classify import classify_exception, fingerprint_exception
from ._errors import AdversarialLoopDetected, BudgetExceeded
from ._events import AttemptEvent

F = TypeVar("F", bound=Callable[..., Any])


def budget(
    *,
    max_attempts: int = 5,
    max_cost_usd: float | None = None,
    max_wall_clock_s: float | None = None,
    retry_on: tuple[type[BaseException], ...] = (),
    fatal_on: tuple[type[BaseException], ...] = (),
    cost_extractor: Callable[[Any], float] | None = None,
    detect_adversarial_loop: bool = True,
    adversarial_threshold: int = 3,
    backoff_initial_s: float = 0.5,
    backoff_max_s: float = 30.0,
    backoff_factor: float = 2.0,
    on_attempt: Callable[[AttemptEvent], None] | None = None,
) -> Callable[[F], F]:
    """Wrap a function with retry + budget enforcement.

    On exception:

    - If the exception is in ``fatal_on``: re-raise immediately.
    - If in ``retry_on``: retry with exponential backoff (capped) until
      ``max_attempts`` / ``max_wall_clock_s`` is reached.
    - Anything else (``unknown``): re-raise. We do not silently retry
      unfamiliar errors.

    On success: ``cost_extractor(result)`` is called (if set) and added to
    the cumulative cost. If the cumulative is over ``max_cost_usd``, raises
    :class:`BudgetExceeded`. Successful return is yielded *only* when the
    cost check passes.

    Adversarial detection: if the same exception fingerprint repeats
    ``adversarial_threshold`` times in a row, raises
    :class:`AdversarialLoopDetected` instead of continuing.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            started = time.monotonic()
            cumulative_cost = 0.0
            attempt = 0
            last_fingerprint: str | None = None
            consecutive_identical = 0
            backoff = backoff_initial_s

            def _emit(event: AttemptEvent) -> None:
                if on_attempt is not None:
                    try:
                        on_attempt(event)
                    except Exception:
                        # Hooks must not crash the wrapped call.
                        pass

            _emit(
                AttemptEvent(
                    kind="start",
                    attempt=0,
                    cumulative_cost_usd=0.0,
                    cumulative_latency_s=0.0,
                )
            )

            while True:
                attempt += 1
                elapsed = time.monotonic() - started
                if max_wall_clock_s is not None and elapsed >= max_wall_clock_s:
                    raise BudgetExceeded(
                        kind="wall_clock_s",
                        limit=max_wall_clock_s,
                        observed=elapsed,
                        attempts=attempt - 1,
                    )

                try:
                    result = fn(*args, **kwargs)
                except BaseException as exc:
                    classification = classify_exception(
                        exc, retry_on=retry_on, fatal_on=fatal_on
                    )
                    fingerprint = fingerprint_exception(exc)

                    if detect_adversarial_loop:
                        if fingerprint == last_fingerprint:
                            consecutive_identical += 1
                        else:
                            consecutive_identical = 1
                        last_fingerprint = fingerprint
                        if consecutive_identical >= adversarial_threshold:
                            _emit(
                                AttemptEvent(
                                    kind="failure",
                                    attempt=attempt,
                                    cumulative_cost_usd=cumulative_cost,
                                    cumulative_latency_s=time.monotonic() - started,
                                    last_error=exc,
                                    error_classification=classification,
                                )
                            )
                            raise AdversarialLoopDetected(
                                repetitions=consecutive_identical,
                                fingerprint=fingerprint,
                            ) from exc

                    if classification == "fatal" or classification == "unknown":
                        _emit(
                            AttemptEvent(
                                kind="failure",
                                attempt=attempt,
                                cumulative_cost_usd=cumulative_cost,
                                cumulative_latency_s=time.monotonic() - started,
                                last_error=exc,
                                error_classification=classification,
                            )
                        )
                        raise

                    if attempt >= max_attempts:
                        _emit(
                            AttemptEvent(
                                kind="failure",
                                attempt=attempt,
                                cumulative_cost_usd=cumulative_cost,
                                cumulative_latency_s=time.monotonic() - started,
                                last_error=exc,
                                error_classification=classification,
                            )
                        )
                        raise BudgetExceeded(
                            kind="attempts",
                            limit=max_attempts,
                            observed=attempt,
                            attempts=attempt,
                            last_error=exc,
                        ) from exc

                    _emit(
                        AttemptEvent(
                            kind="retry",
                            attempt=attempt,
                            cumulative_cost_usd=cumulative_cost,
                            cumulative_latency_s=time.monotonic() - started,
                            last_error=exc,
                            error_classification=classification,
                        )
                    )
                    sleep_for = min(backoff, backoff_max_s)
                    if max_wall_clock_s is not None:
                        remaining = max_wall_clock_s - (time.monotonic() - started)
                        sleep_for = min(sleep_for, max(0.0, remaining))
                    if sleep_for > 0:
                        time.sleep(sleep_for)
                    backoff *= backoff_factor
                    continue

                # success path
                if cost_extractor is not None:
                    try:
                        delta = float(cost_extractor(result))
                    except Exception:
                        delta = 0.0
                    cumulative_cost += delta
                    if max_cost_usd is not None and cumulative_cost > max_cost_usd:
                        raise BudgetExceeded(
                            kind="cost_usd",
                            limit=max_cost_usd,
                            observed=cumulative_cost,
                            attempts=attempt,
                        )

                _emit(
                    AttemptEvent(
                        kind="success",
                        attempt=attempt,
                        cumulative_cost_usd=cumulative_cost,
                        cumulative_latency_s=time.monotonic() - started,
                    )
                )
                return result

        return wrapper  # type: ignore[return-value]

    return decorator
