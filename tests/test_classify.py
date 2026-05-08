"""Exception classification tests."""

from __future__ import annotations

from agent_budget import classify_exception, fingerprint_exception


class _Retryable(Exception):
    pass


class _Fatal(Exception):
    pass


def test_classified_retryable() -> None:
    assert classify_exception(_Retryable(), retry_on=(_Retryable,)) == "retryable"


def test_classified_fatal_takes_precedence_over_retryable() -> None:
    class _Both(_Retryable, _Fatal):
        pass

    assert (
        classify_exception(
            _Both(),
            retry_on=(_Retryable,),
            fatal_on=(_Fatal,),
        )
        == "fatal"
    )


def test_classified_unknown_when_in_neither_set() -> None:
    assert classify_exception(ValueError("x")) == "unknown"


def test_fingerprint_combines_type_and_message() -> None:
    fp = fingerprint_exception(ValueError("boom"))
    assert "ValueError" in fp
    assert "boom" in fp


def test_fingerprint_truncates_long_messages() -> None:
    big = "x" * 5000
    fp = fingerprint_exception(ValueError(big))
    assert len(fp) < 300
