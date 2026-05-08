# Changelog

All notable changes to `agent-budget` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-08

Initial release. The retry/budget primitive `tenacity` isn't, with the three things that matter for production LLM-shaped work: cost cap, structured per-attempt events, and adversarial-loop detection.

### Added
- `@budget` decorator wrapping any callable with: `max_attempts`, `max_cost_usd`, `max_wall_clock_s`, `retry_on`/`fatal_on` exception sets, `cost_extractor` for post-success accounting, exponential backoff (configurable initial/max/factor), and optional `on_attempt` hook.
- `AttemptEvent` dataclass (`start`/`retry`/`success`/`failure`) carrying attempt number, cumulative cost, cumulative latency, last error, and exception classification — closes the metadata gap from Instructor #2222.
- `AdversarialLoopDetected` raised when the same exception fingerprint repeats `adversarial_threshold` times in a row (default 3) — closes the retry-amplification class of bug from Instructor #2056.
- `BudgetExceeded` with typed `kind` (`attempts`/`cost_usd`/`wall_clock_s`).
- `classify_exception()` and `fingerprint_exception()` exposed for callers who want the same logic outside the decorator.
- Hook callbacks that raise exceptions are swallowed; the wrapped call is never broken by an instrumentation bug.
- Backoff sleep is automatically clamped to remaining wall-clock budget so a long sleep never overruns the cap.

### Notes
- 21 unit tests, 98% line coverage.
- Zero runtime dependencies. Pure stdlib.
