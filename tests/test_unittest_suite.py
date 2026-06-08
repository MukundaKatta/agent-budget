"""Standard-library ``unittest`` test suite for agent-budget.

The project's primary test suite (``test_budget.py`` / ``test_classify.py``)
is written for ``pytest``. This module mirrors and extends that coverage using
only the Python standard library, so the package can be validated in
environments without any third-party test dependencies::

    python3 -m unittest discover -s tests

It imports and exercises the real public API. If ``agent_budget`` is not yet
installed (e.g. running straight from a checkout), it falls back to importing
from the in-tree ``src/`` layout.
"""

from __future__ import annotations

import os
import sys
import time
import unittest

# Allow running the suite directly from a source checkout without installing
# the package first (``src`` layout).
try:  # pragma: no cover - exercised implicitly depending on environment
    import agent_budget  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - depends on environment
    _SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
    if _SRC not in sys.path:
        sys.path.insert(0, _SRC)

from agent_budget import (  # noqa: E402
    AdversarialLoopDetected,
    AgentBudgetError,
    AttemptEvent,
    BudgetExceeded,
    __version__,
    budget,
    classify_exception,
    fingerprint_exception,
)


class _Throttled(Exception):
    pass


class _Fatal(Exception):
    pass


class BudgetSuccessTests(unittest.TestCase):
    def test_success_on_first_attempt_returns_result(self) -> None:
        @budget(max_attempts=3)
        def f() -> str:
            return "ok"

        self.assertEqual(f(), "ok")

    def test_decorator_preserves_function_metadata(self) -> None:
        @budget(max_attempts=2)
        def documented() -> int:
            """A docstring that must survive wrapping."""
            return 1

        self.assertEqual(documented.__name__, "documented")
        self.assertEqual(documented.__doc__, "A docstring that must survive wrapping.")

    def test_arguments_are_passed_through(self) -> None:
        @budget(max_attempts=2)
        def add(a: int, b: int, *, c: int = 0) -> int:
            return a + b + c

        self.assertEqual(add(1, 2, c=3), 6)


class BudgetRetryTests(unittest.TestCase):
    def test_retries_on_retryable_then_succeeds(self) -> None:
        calls = {"n": 0}

        @budget(max_attempts=5, retry_on=(_Throttled,), backoff_initial_s=0.0)
        def f() -> str:
            calls["n"] += 1
            if calls["n"] < 3:
                raise _Throttled("rate limited")
            return "ok"

        self.assertEqual(f(), "ok")
        self.assertEqual(calls["n"], 3)

    def test_does_not_retry_unknown_exception(self) -> None:
        calls = {"n": 0}

        @budget(max_attempts=5, retry_on=(_Throttled,))
        def f() -> str:
            calls["n"] += 1
            raise ValueError("unknown")

        with self.assertRaises(ValueError):
            f()
        self.assertEqual(calls["n"], 1)

    def test_fatal_exception_re_raises_immediately(self) -> None:
        calls = {"n": 0}

        @budget(
            max_attempts=5,
            retry_on=(_Throttled, _Fatal),
            fatal_on=(_Fatal,),
            backoff_initial_s=0.0,
        )
        def f() -> str:
            calls["n"] += 1
            raise _Fatal("nope")

        with self.assertRaises(_Fatal):
            f()
        self.assertEqual(calls["n"], 1)


class BudgetLimitTests(unittest.TestCase):
    def test_attempts_budget_exhausted_raises_budget_exceeded(self) -> None:
        @budget(
            max_attempts=3,
            retry_on=(_Throttled,),
            backoff_initial_s=0.0,
            detect_adversarial_loop=False,
        )
        def f() -> str:
            raise _Throttled("always")

        with self.assertRaises(BudgetExceeded) as ctx:
            f()
        self.assertEqual(ctx.exception.kind, "attempts")
        self.assertEqual(ctx.exception.attempts, 3)
        self.assertIsInstance(ctx.exception.last_error, _Throttled)

    def test_wall_clock_budget_short_circuits(self) -> None:
        @budget(
            max_attempts=100,
            max_wall_clock_s=0.1,
            retry_on=(_Throttled,),
            backoff_initial_s=0.0,
        )
        def f() -> str:
            time.sleep(0.05)
            raise _Throttled("slow")

        with self.assertRaises(BudgetExceeded) as ctx:
            f()
        self.assertEqual(ctx.exception.kind, "wall_clock_s")

    def test_cost_budget_enforced_after_successful_call(self) -> None:
        @budget(max_attempts=3, max_cost_usd=0.05, cost_extractor=lambda r: r["cost"])
        def f() -> dict:
            return {"cost": 0.10}

        with self.assertRaises(BudgetExceeded) as ctx:
            f()
        self.assertEqual(ctx.exception.kind, "cost_usd")
        self.assertAlmostEqual(ctx.exception.observed, 0.10)

    def test_cost_budget_passes_under_limit(self) -> None:
        @budget(max_attempts=3, max_cost_usd=1.00, cost_extractor=lambda r: r["cost"])
        def f() -> dict:
            return {"cost": 0.10, "data": "ok"}

        self.assertEqual(f(), {"cost": 0.10, "data": "ok"})

    def test_cost_extractor_errors_are_swallowed_as_zero(self) -> None:
        # A cost_extractor that blows up must not abort an otherwise good call;
        # it contributes 0.0 to the cumulative cost.
        def boom(_result: object) -> float:
            raise KeyError("usage")

        @budget(max_attempts=2, max_cost_usd=0.01, cost_extractor=boom)
        def f() -> str:
            return "ok"

        self.assertEqual(f(), "ok")

    def test_cost_accumulates_across_extractor(self) -> None:
        # Single successful call: extracted cost must reach the event.
        events: list[AttemptEvent] = []

        @budget(
            max_attempts=2,
            max_cost_usd=1.0,
            cost_extractor=lambda r: 0.25,
            on_attempt=events.append,
        )
        def f() -> str:
            return "ok"

        self.assertEqual(f(), "ok")
        success = [e for e in events if e.kind == "success"][0]
        self.assertAlmostEqual(success.cumulative_cost_usd, 0.25)


class AdversarialLoopTests(unittest.TestCase):
    def test_adversarial_loop_detected_after_threshold(self) -> None:
        @budget(
            max_attempts=10,
            retry_on=(_Throttled,),
            adversarial_threshold=3,
            backoff_initial_s=0.0,
        )
        def f() -> str:
            raise _Throttled("always identical message")

        with self.assertRaises(AdversarialLoopDetected) as ctx:
            f()
        self.assertEqual(ctx.exception.repetitions, 3)
        self.assertIn("_Throttled", ctx.exception.fingerprint)

    def test_default_threshold_is_three(self) -> None:
        @budget(max_attempts=10, retry_on=(_Throttled,), backoff_initial_s=0.0)
        def f() -> str:
            raise _Throttled("identical")

        with self.assertRaises(AdversarialLoopDetected) as ctx:
            f()
        self.assertEqual(ctx.exception.repetitions, 3)

    def test_adversarial_detection_can_be_disabled(self) -> None:
        @budget(
            max_attempts=4,
            retry_on=(_Throttled,),
            detect_adversarial_loop=False,
            backoff_initial_s=0.0,
        )
        def f() -> str:
            raise _Throttled("identical")

        with self.assertRaises(BudgetExceeded) as ctx:
            f()
        self.assertEqual(ctx.exception.kind, "attempts")

    def test_adversarial_resets_when_error_changes(self) -> None:
        n = {"i": 0}

        @budget(
            max_attempts=10,
            retry_on=(_Throttled,),
            adversarial_threshold=3,
            backoff_initial_s=0.0,
        )
        def f() -> str:
            n["i"] += 1
            raise _Throttled(f"error variant {n['i'] % 2}")

        with self.assertRaises(BudgetExceeded) as ctx:
            f()
        self.assertEqual(ctx.exception.kind, "attempts")


class AttemptEventTests(unittest.TestCase):
    def test_on_attempt_callback_receives_lifecycle_events(self) -> None:
        events: list[AttemptEvent] = []
        calls = {"n": 0}

        @budget(
            max_attempts=3,
            retry_on=(_Throttled,),
            backoff_initial_s=0.0,
            on_attempt=events.append,
        )
        def f() -> str:
            calls["n"] += 1
            if calls["n"] < 2:
                raise _Throttled("retry me")
            return "ok"

        self.assertEqual(f(), "ok")
        kinds = [e.kind for e in events]
        self.assertIn("start", kinds)
        self.assertIn("retry", kinds)
        self.assertIn("success", kinds)

    def test_retry_event_classification_is_retryable(self) -> None:
        events: list[AttemptEvent] = []
        calls = {"n": 0}

        @budget(
            max_attempts=3,
            retry_on=(_Throttled,),
            backoff_initial_s=0.0,
            on_attempt=events.append,
        )
        def f() -> str:
            calls["n"] += 1
            if calls["n"] < 2:
                raise _Throttled("retry me")
            return "ok"

        f()
        retry = [e for e in events if e.kind == "retry"][0]
        self.assertEqual(retry.error_classification, "retryable")
        self.assertIsInstance(retry.last_error, _Throttled)

    def test_on_attempt_carries_cumulative_metadata(self) -> None:
        events: list[AttemptEvent] = []

        @budget(
            max_attempts=2,
            retry_on=(_Throttled,),
            backoff_initial_s=0.0,
            on_attempt=events.append,
        )
        def f() -> str:
            raise _Throttled("x")

        with self.assertRaises(BudgetExceeded):
            f()
        failure = [e for e in events if e.kind == "failure"][0]
        self.assertEqual(failure.attempt, 2)
        self.assertIsInstance(failure.last_error, _Throttled)
        self.assertGreaterEqual(failure.cumulative_latency_s, 0)

    def test_on_attempt_callback_exceptions_do_not_break_call(self) -> None:
        def bad_hook(_evt: AttemptEvent) -> None:
            raise RuntimeError("hook crashed")

        @budget(max_attempts=2, on_attempt=bad_hook)
        def f() -> str:
            return "ok"

        self.assertEqual(f(), "ok")

    def test_start_event_has_zeroed_counters(self) -> None:
        events: list[AttemptEvent] = []

        @budget(max_attempts=2, on_attempt=events.append)
        def f() -> str:
            return "ok"

        f()
        start = [e for e in events if e.kind == "start"][0]
        self.assertEqual(start.attempt, 0)
        self.assertEqual(start.cumulative_cost_usd, 0.0)
        self.assertEqual(start.cumulative_latency_s, 0.0)
        self.assertIsNone(start.last_error)

    def test_event_is_frozen_and_has_default_extra(self) -> None:
        evt = AttemptEvent(
            kind="start",
            attempt=0,
            cumulative_cost_usd=0.0,
            cumulative_latency_s=0.0,
        )
        self.assertEqual(evt.error_classification, "none")
        self.assertEqual(evt.extra, {})
        with self.assertRaises(Exception):
            evt.attempt = 5  # type: ignore[misc]


class BackoffTests(unittest.TestCase):
    def test_backoff_scales_geometrically(self) -> None:
        sleeps: list[float] = []
        original_sleep = time.sleep
        time.sleep = sleeps.append  # type: ignore[assignment]
        try:

            @budget(
                max_attempts=4,
                retry_on=(_Throttled,),
                backoff_initial_s=0.5,
                backoff_max_s=10.0,
                backoff_factor=2.0,
                detect_adversarial_loop=False,
            )
            def f() -> str:
                raise _Throttled("x")

            with self.assertRaises(BudgetExceeded):
                f()
        finally:
            time.sleep = original_sleep  # type: ignore[assignment]

        self.assertEqual(len(sleeps), 3)
        self.assertAlmostEqual(sleeps[0], 0.5)
        self.assertAlmostEqual(sleeps[1], 1.0)
        self.assertAlmostEqual(sleeps[2], 2.0)

    def test_backoff_clamped_to_max(self) -> None:
        sleeps: list[float] = []
        original_sleep = time.sleep
        time.sleep = sleeps.append  # type: ignore[assignment]
        try:

            @budget(
                max_attempts=5,
                retry_on=(_Throttled,),
                backoff_initial_s=1.0,
                backoff_max_s=2.0,
                backoff_factor=10.0,
                detect_adversarial_loop=False,
            )
            def f() -> str:
                raise _Throttled("x")

            with self.assertRaises(BudgetExceeded):
                f()
        finally:
            time.sleep = original_sleep  # type: ignore[assignment]

        for s in sleeps:
            self.assertLessEqual(s, 2.0)


class ClassifyTests(unittest.TestCase):
    def test_classified_retryable(self) -> None:
        self.assertEqual(
            classify_exception(_Throttled(), retry_on=(_Throttled,)), "retryable"
        )

    def test_classified_fatal_takes_precedence_over_retryable(self) -> None:
        class _Both(_Throttled, _Fatal):
            pass

        self.assertEqual(
            classify_exception(_Both(), retry_on=(_Throttled,), fatal_on=(_Fatal,)),
            "fatal",
        )

    def test_classified_unknown_when_in_neither_set(self) -> None:
        self.assertEqual(classify_exception(ValueError("x")), "unknown")

    def test_fingerprint_combines_type_and_message(self) -> None:
        fp = fingerprint_exception(ValueError("boom"))
        self.assertIn("ValueError", fp)
        self.assertIn("boom", fp)

    def test_fingerprint_truncates_long_messages(self) -> None:
        fp = fingerprint_exception(ValueError("x" * 5000))
        self.assertLess(len(fp), 300)

    def test_fingerprint_is_stable_for_equal_inputs(self) -> None:
        a = fingerprint_exception(ValueError("same"))
        b = fingerprint_exception(ValueError("same"))
        self.assertEqual(a, b)


class ErrorHierarchyTests(unittest.TestCase):
    def test_budget_exceeded_is_agent_budget_error(self) -> None:
        err = BudgetExceeded(kind="attempts", limit=3, observed=3, attempts=3)
        self.assertIsInstance(err, AgentBudgetError)
        self.assertIn("attempts", str(err))

    def test_adversarial_loop_is_agent_budget_error(self) -> None:
        err = AdversarialLoopDetected(repetitions=3, fingerprint="X:y")
        self.assertIsInstance(err, AgentBudgetError)
        self.assertEqual(err.repetitions, 3)
        self.assertEqual(err.fingerprint, "X:y")

    def test_version_is_exposed(self) -> None:
        self.assertIsInstance(__version__, str)
        self.assertTrue(__version__)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
