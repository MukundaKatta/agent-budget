# Porting status

Where agent-budget is published, where it's queued, and what's intentionally not happening.

## Current

| Channel | State | URL |
|---|---|---|
| GitHub Release | live | https://github.com/MukundaKatta/agent-budget/releases/tag/v0.1.0 |
| PyPI | queued — waiting on rate-limit / admin lift | https://pypi.org/project/agent-budget/ (404 until publish lands) |
| conda-forge | recipe PR submitted | https://github.com/conda-forge/staged-recipes/pull/33283 |
| **JavaScript sibling** | v0.2 PR open on existing lib | https://www.npmjs.com/package/@mukundakatta/agentbudget · PR https://github.com/MukundaKatta/AgentBudget/pull/1 |

The JavaScript sibling [`@mukundakatta/agentbudget`](https://www.npmjs.com/package/@mukundakatta/agentbudget) is the JS analogue. v0.1 of that package was the post-call `Budget` class; v0.2 (PR #1) adds `withBudget` — the equivalent of this Python lib's `@budget` decorator — making the two ecosystems API-aligned.

Install Python lib from GitHub Release until PyPI lands:

```bash
pip install https://github.com/MukundaKatta/agent-budget/releases/download/v0.1.0/agent_budget-0.1.0-py3-none-any.whl
```

## Roadmap

### Plausible

| Target | Why | Approx scope |
|---|---|---|
| **Go port → pkg.go.dev** | Pure stdlib in Python = clean port to Go; LLM-on-Go community has the same retry-amplification pain class | ~3-4 days |

### Already done (sibling)

The JavaScript port lives at [`@mukundakatta/agentbudget`](https://www.npmjs.com/package/@mukundakatta/agentbudget). It includes both the `Budget` accumulator (which has no Python equivalent, that's the JS side's primary API) and `withBudget` (the JS port of this Python lib's `@budget` decorator). Symbol mapping:

| Python (`agent_budget`) | JavaScript (`@mukundakatta/agentbudget`) |
|---|---|
| `@budget(...)` | `withBudget(fn, opts)` |
| `BudgetExceeded` | `WithBudgetExceededError` |
| `AdversarialLoopDetected` | `AdversarialLoopDetectedError` |
| `AttemptEvent` | `AttemptEvent` (typedef) |
| `classify_exception` | `classifyException` |
| `fingerprint_exception` | `fingerprintException` |

### Not planned

Same as the other libs: Java/Ruby/PHP/Perl/Haskell/OCaml ports skipped (no real LLM-tooling community); Homebrew/APT/etc. are wrong category; Docker Hub doesn't apply to libraries.

## How to contribute a port

Open an issue with the target ecosystem and a sketch of the public-API mapping before writing code.
