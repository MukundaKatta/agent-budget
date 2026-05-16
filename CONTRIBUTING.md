# Contributing to agent-budget

agent-budget is a focused retry/budget primitive for LLM and agent calls. Contributions are welcome where they fit that scope; out-of-scope contributions will be politely declined.

## In scope

- Bug fixes in `@budget`, `BudgetExceeded`, `AdversarialLoopDetected`, `AttemptEvent`, `classify_exception`, `fingerprint_exception`.
- Stronger adversarial-loop detection (alternative fingerprint strategies, configurable detectors), behind keyword arguments.
- New cost-cap modalities (per-tenant, per-feature, sliding-window), as additive options.
- Better hook ergonomics — anything that closes [Instructor #2222](https://github.com/jxnl/instructor/issues/2222) shape gaps.
- Async variant (`@async_budget` for `await`able functions) — planned for v0.2.
- Test coverage improvements (current target: 95%+ line coverage).

## Out of scope

- **Generic retry library.** `tenacity`, `backoff`, and `urllib3.Retry` cover that. agent-budget exists for the LLM-specific failure modes those don't.
- **Rate limiting / leaky bucket.** Use `limits` or `slowapi`.
- **Routing / fallback to different providers.** That's a separate problem from "is this single call's retry safe".
- **Tracing backends.** agent-budget emits structured `AttemptEvent`s; you wire them to your tracer.
- **Provider-specific cost tables.** The `cost_extractor` is BYO so the library doesn't ship and maintain pricing data that goes stale.

## Sibling libraries

agent-budget has language siblings that should keep API parity where possible:

- JavaScript: [`@mukundakatta/agentbudget`](https://www.npmjs.com/package/@mukundakatta/agentbudget) — `withBudget(fn, opts)` mirrors `@budget`.
- Go: [`github.com/MukundaKatta/agentbudget-go`](https://pkg.go.dev/github.com/MukundaKatta/agentbudget-go) — `Run[T](ctx, fn, opts)` mirrors `@budget`.

If you add a new feature to the Python lib that also makes sense in JS or Go, mention it in the PR so the siblings can stay aligned.

## Development setup

```bash
git clone https://github.com/MukundaKatta/agent-budget.git
cd agent-budget
uv sync --group dev
uv run pytest                                # 21 tests
uv run pytest --cov=agent_budget --cov-report=term-missing
uv build                                     # build sdist + wheel
```

Python 3.10+ required. **Zero runtime dependencies** (pure stdlib).

## Workflow

1. Open an issue first for anything bigger than a one-file change.
2. Branch from `main`.
3. Write tests covering the change. Adversarial-loop and budget-exceed paths in particular must have deterministic seeded paths.
4. Run `uv run pytest` and confirm full suite still passes.
5. Open a PR against `main`. Fill in the template.
6. CI must be green before review.

## Coding conventions

- Type hints required on public APIs.
- No new runtime dependencies. Period. The "pure stdlib" promise is part of the value proposition.
- Hooks that the user can register (`on_attempt`) must be wrapped so user errors don't crash the wrapped call.
- Keep public symbols in `__all__`; otherwise they aren't re-exported.

## Release cadence

Releases follow semver. Patches: bug fixes only. Minor versions: new public symbols. Major versions: breaking changes (unlikely in v0.x).

Releases are cut by the maintainer via tag push. See `.github/workflows/release.yml`.
