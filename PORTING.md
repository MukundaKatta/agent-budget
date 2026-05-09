# Porting status

Where agent-budget is published, where it's queued, and what's intentionally not happening.

## Current

| Channel | State | URL |
|---|---|---|
| GitHub Release | live | https://github.com/MukundaKatta/agent-budget/releases/tag/v0.1.0 |
| PyPI | queued — waiting on rate-limit / admin lift | https://pypi.org/project/agent-budget/ (404 until publish lands) |
| conda-forge | recipe PR submitted | https://github.com/conda-forge/staged-recipes/pull/33283 |
| nixpkgs | derivation PR submitted | https://github.com/NixOS/nixpkgs/pull/518492 |
| **JavaScript sibling** | v0.2 PR open on existing lib | https://www.npmjs.com/package/@mukundakatta/agentbudget · PR https://github.com/MukundaKatta/AgentBudget/pull/1 |
| **Go sibling** | live | https://pkg.go.dev/github.com/MukundaKatta/agentbudget-go (v0.1.0) |

The JavaScript sibling [`@mukundakatta/agentbudget`](https://www.npmjs.com/package/@mukundakatta/agentbudget) is the JS analogue. v0.1 of that package was the post-call `Budget` class; v0.2 (PR #1) adds `withBudget` — the equivalent of this Python lib's `@budget` decorator — making the two ecosystems API-aligned.

Install Python lib from GitHub Release until PyPI lands:

```bash
pip install https://github.com/MukundaKatta/agent-budget/releases/download/v0.1.0/agent_budget-0.1.0-py3-none-any.whl
```

## Roadmap

### Plausible

| Target | Why | Approx scope |
|---|---|---|
| **Rust port → crates.io** | Linear port via `thiserror` for error enum + generic `Run<T>` function | ~3-4 days |

### Already done (siblings)

| Python (`agent_budget`) | JavaScript (`@mukundakatta/agentbudget`) | Go (`agentbudget-go`) |
|---|---|---|
| `@budget(...)` | `withBudget(fn, opts)` | `Run[T any](ctx, fn, opts)` |
| `BudgetExceeded` | `WithBudgetExceededError` | `*BudgetExceededError` |
| `AdversarialLoopDetected` | `AdversarialLoopDetectedError` | `*AdversarialLoopDetectedError` |
| `AttemptEvent` | `AttemptEvent` (typedef) | `AttemptEvent` (struct) |
| `classify_exception` | `classifyException` | `Classify` |
| `fingerprint_exception` | `fingerprintException` | `Fingerprint` |
| `retry_on=(E,)` | `retryOn: [E]` | `IsRetryable: IsAny(E)` |

### Not planned

Same as the other libs: Java/Ruby/PHP/Perl/Haskell/OCaml ports skipped (no real LLM-tooling community); Homebrew/APT/etc. are wrong category; Docker Hub doesn't apply to libraries.

## How to contribute a port

Open an issue with the target ecosystem and a sketch of the public-API mapping before writing code.
