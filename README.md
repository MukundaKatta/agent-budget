# agent-budget

[![PyPI version](https://img.shields.io/pypi/v/agent-budget.svg)](https://pypi.org/project/agent-budget/)
[![Python versions](https://img.shields.io/pypi/pyversions/agent-budget.svg)](https://pypi.org/project/agent-budget/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![CI](https://github.com/MukundaKatta/agent-budget/actions/workflows/test.yml/badge.svg)](https://github.com/MukundaKatta/agent-budget/actions/workflows/test.yml)
[![Zero runtime deps](https://img.shields.io/badge/runtime%20deps-0-brightgreen.svg)](pyproject.toml)

Production retry/budget primitive for LLM and agent calls. The thing `tenacity` isn't.

```bash
pip install agent-budget
```

```python
from agent_budget import budget, BudgetExceeded, AdversarialLoopDetected

@budget(
    max_attempts=5,
    max_cost_usd=0.10,
    max_wall_clock_s=30,
    retry_on=(RateLimitError, APITimeoutError),
    fatal_on=(ContentPolicyError,),
    cost_extractor=lambda result: result.usage.cost_usd,
)
def extract_invoice(image_bytes):
    return llm.extract(image_bytes)
```

## Why exist

| Existing tool | What's missing |
|---|---|
| `tenacity` | Generic retry; no LLM cost cap, no adversarial-loop detection, no structured per-attempt events |
| `openai.max_retries=N` / `anthropic.max_retries=N` | Integer only. No cost cap. No wall-clock. No event taxonomy |
| `instructor` retry hooks ([#2222](https://github.com/jxnl/instructor/issues/2222)) | Hooks fire but don't expose `attempt_number`, cumulative cost, or last-error classification. Can't distinguish a retryable mid-flight error from a final failure |
| Instructor retry mechanism ([#2056 security audit](https://github.com/jxnl/instructor/issues/2056)) | No rate limit on retries. An adversarial / prompt-injected response that always fails validation can drive unbounded retries and cost |

## What `@budget` adds

- **Per-call USD cost cap.** Pass a `cost_extractor`; cumulative cost across retries is enforced after every successful call.
- **Wall-clock cap.** Cumulative time across all attempts and backoffs.
- **Adversarial-loop detection.** Fingerprints repeated identical errors and raises `AdversarialLoopDetected` after 3 in a row (configurable). Stops the Instructor #2056 retry-amplification class of bug.
- **Structured `AttemptEvent` for hooks.** `start` / `retry` / `success` / `failure` events carry attempt number, cumulative cost, cumulative latency, last error, and a classification (`retryable` / `fatal` / `unknown`).
- **No silent retries on unknown exceptions.** Anything not in `retry_on` or `fatal_on` re-raises. You opt in to retrying classes you understand.

## Usage

### Cost-capped retries

```python
from agent_budget import budget

@budget(
    max_attempts=5,
    max_cost_usd=0.50,
    retry_on=(RateLimitError, APITimeoutError),
    cost_extractor=lambda r: r.usage.input_tokens * 3e-6 + r.usage.output_tokens * 1.5e-5,
)
def call(prompt):
    return openai.chat.completions.create(...)
```

### Adversarial-loop kill-switch

The default ``adversarial_threshold=3`` is right for most LLM workflows. The killer story: an Instructor pipeline whose schema and prompt got desynced silently retried the same failing validation 100x per request, costing $300/day before anyone noticed:

```python
from agent_budget import budget, AdversarialLoopDetected

@budget(
    max_attempts=20,
    retry_on=(ValidationError,),
    adversarial_threshold=3,   # default
)
def extract():
    return instructor.from_openai(...).chat.completions.create(...)

try:
    invoice = extract()
except AdversarialLoopDetected as e:
    log.error("validation always failing — fingerprint=%s", e.fingerprint)
    # alert + open ticket; don't keep paying for a broken prompt
```

### Structured per-attempt events

```python
from agent_budget import budget, AttemptEvent

def emit(evt: AttemptEvent) -> None:
    metrics.histogram("llm.attempt", evt.attempt, tags={
        "kind": evt.kind,
        "classification": evt.error_classification,
    })
    if evt.kind == "retry":
        log.warning("retry %d after %.2fs ($ %.4f cumulative)",
                    evt.attempt, evt.cumulative_latency_s, evt.cumulative_cost_usd)

@budget(
    max_attempts=5,
    max_cost_usd=0.10,
    retry_on=(RateLimitError,),
    on_attempt=emit,
)
def call(...):
    ...
```

### Composes with anything

`@budget` only wraps a callable. It doesn't care whether the callable is OpenAI, Anthropic, Bedrock, a chain of agents, an Instructor pipeline, an `httpx` request, or your own function. No provider-specific imports.

## What it explicitly does NOT do

- Not a rate limiter. Use leaky-bucket libs (`limits`, `slowapi`) for that.
- Not a router or fallback library. Doesn't pick another model.
- Not a tracer. Emits structured events; you wire them to your tracer.
- Not provider-specific.
- Not async-only. Sync first; async support in v0.2.

## Roadmap

- v0.2: async variant `@async_budget` for `await`able functions.
- v0.3: `streaming.budget` context manager for token-cap on `for chunk in stream` loops with cooperative cancel.
- v0.4: composable budget chains (parent budget that bounds nested calls).

## License

Apache-2.0. See [LICENSE](./LICENSE).

## Repository Health

This repository includes a dependency-free health check for core documentation, metadata, and CI wiring. Run it locally before publishing changes:

```sh
python3 scripts/check_repository_health.py
```

The same check runs in GitHub Actions on pushes and pull requests.
