"""@budget decorator tests."""

from __future__ import annotations

import time

import pytest

from agent_budget import (
    AdversarialLoopDetected,
    AttemptEvent,
    BudgetExceeded,
    budget,
)


class _Throttled(Exception):
    pass


class _Fatal(Exception):
    pass


def test_success_on_first_attempt_returns_result() -> None:
    @budget(max_attempts=3)
    def f() -> str:
        return "ok"

    assert f() == "ok"


def test_retries_on_retryable_then_succeeds() -> None:
    calls = {"n": 0}

    @budget(
        max_attempts=5,
        retry_on=(_Throttled,),
        backoff_initial_s=0.0,
    )
    def f() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise _Throttled("rate limited")
        return "ok"

    assert f() == "ok"
    assert calls["n"] == 3


def test_does_not_retry_unknown_exception() -> None:
    calls = {"n": 0}

    @budget(max_attempts=5, retry_on=(_Throttled,))
    def f() -> str:
        calls["n"] += 1
        raise ValueError("unknown")

    with pytest.raises(ValueError):
        f()
    assert calls["n"] == 1


def test_fatal_exception_re_raises_immediately() -> None:
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

    with pytest.raises(_Fatal):
        f()
    assert calls["n"] == 1


def test_attempts_budget_exhausted_raises_budget_exceeded() -> None:
    @budget(
        max_attempts=3,
        retry_on=(_Throttled,),
        backoff_initial_s=0.0,
        detect_adversarial_loop=False,
    )
    def f() -> str:
        raise _Throttled("always")

    with pytest.raises(BudgetExceeded) as exc_info:
        f()
    assert exc_info.value.kind == "attempts"
    assert exc_info.value.attempts == 3
    assert isinstance(exc_info.value.last_error, _Throttled)


def test_wall_clock_budget_short_circuits() -> None:
    @budget(
        max_attempts=100,
        max_wall_clock_s=0.1,
        retry_on=(_Throttled,),
        backoff_initial_s=0.0,
    )
    def f() -> str:
        time.sleep(0.05)
        raise _Throttled("slow")

    with pytest.raises(BudgetExceeded) as exc_info:
        f()
    assert exc_info.value.kind == "wall_clock_s"


def test_cost_budget_enforced_after_successful_call() -> None:
    @budget(
        max_attempts=3,
        max_cost_usd=0.05,
        cost_extractor=lambda r: r["cost"],
    )
    def f() -> dict:
        return {"cost": 0.10}

    with pytest.raises(BudgetExceeded) as exc_info:
        f()
    assert exc_info.value.kind == "cost_usd"
    assert exc_info.value.observed == 0.10


def test_cost_budget_passes_under_limit() -> None:
    @budget(
        max_attempts=3,
        max_cost_usd=1.00,
        cost_extractor=lambda r: r["cost"],
    )
    def f() -> dict:
        return {"cost": 0.10, "data": "ok"}

    assert f() == {"cost": 0.10, "data": "ok"}


def test_adversarial_loop_detected_after_threshold() -> None:
    @budget(
        max_attempts=10,
        retry_on=(_Throttled,),
        adversarial_threshold=3,
        backoff_initial_s=0.0,
    )
    def f() -> str:
        # always-same exception fingerprint
        raise _Throttled("always identical message")

    with pytest.raises(AdversarialLoopDetected) as exc_info:
        f()
    assert exc_info.value.repetitions == 3
    assert "_Throttled" in exc_info.value.fingerprint


def test_adversarial_detection_can_be_disabled() -> None:
    @budget(
        max_attempts=4,
        retry_on=(_Throttled,),
        detect_adversarial_loop=False,
        backoff_initial_s=0.0,
    )
    def f() -> str:
        raise _Throttled("identical")

    # Without adversarial detection, hits attempts budget
    with pytest.raises(BudgetExceeded) as exc_info:
        f()
    assert exc_info.value.kind == "attempts"


def test_adversarial_resets_when_error_changes() -> None:
    n = {"i": 0}

    @budget(
        max_attempts=10,
        retry_on=(_Throttled,),
        adversarial_threshold=3,
        backoff_initial_s=0.0,
    )
    def f() -> str:
        n["i"] += 1
        # alternating error messages — fingerprint changes each time
        raise _Throttled(f"error variant {n['i'] % 2}")

    # Should hit attempts budget, NOT adversarial detection
    with pytest.raises(BudgetExceeded) as exc_info:
        f()
    assert exc_info.value.kind == "attempts"


def test_on_attempt_callback_receives_lifecycle_events() -> None:
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

    assert f() == "ok"
    kinds = [e.kind for e in events]
    assert "start" in kinds
    assert "retry" in kinds
    assert "success" in kinds


def test_on_attempt_carries_cumulative_metadata() -> None:
    events: list[AttemptEvent] = []

    @budget(
        max_attempts=2,
        retry_on=(_Throttled,),
        backoff_initial_s=0.0,
        on_attempt=events.append,
    )
    def f() -> str:
        raise _Throttled("x")

    with pytest.raises(BudgetExceeded):
        f()
    failure = [e for e in events if e.kind == "failure"][0]
    assert failure.attempt == 2
    assert isinstance(failure.last_error, _Throttled)
    assert failure.cumulative_latency_s >= 0


def test_on_attempt_callback_exceptions_do_not_break_call() -> None:
    def bad_hook(_evt: AttemptEvent) -> None:
        raise RuntimeError("hook crashed")

    @budget(max_attempts=2, on_attempt=bad_hook)
    def f() -> str:
        return "ok"

    assert f() == "ok"


def test_backoff_scales_geometrically(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", sleeps.append)

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

    with pytest.raises(BudgetExceeded):
        f()
    # 3 retries; sleeps roughly 0.5, 1.0, 2.0 (give or take rounding)
    assert len(sleeps) == 3
    assert sleeps[0] == pytest.approx(0.5)
    assert sleeps[1] == pytest.approx(1.0)
    assert sleeps[2] == pytest.approx(2.0)


def test_backoff_clamped_to_remaining_wall_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", sleeps.append)

    @budget(
        max_attempts=5,
        max_wall_clock_s=0.6,
        retry_on=(_Throttled,),
        backoff_initial_s=0.5,
        backoff_factor=10.0,
        detect_adversarial_loop=False,
    )
    def f() -> str:
        raise _Throttled("x")

    with pytest.raises((_Throttled, BudgetExceeded)):
        f()
    # Final backoff should never exceed remaining budget
    for s in sleeps:
        assert s <= 0.6
