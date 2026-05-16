## Summary

What does this PR change in 1-3 sentences?

## Linked issue

Closes #

## Scope check

- [ ] Confirmed this fits `CONTRIBUTING.md` scope (LLM-specific retry/budget; not generic retry, not rate limiting, not routing).
- [ ] Public API changes (if any) are documented in the README and CHANGELOG.
- [ ] **No new runtime dependencies.** agent-budget is pure stdlib by design.
- [ ] Hooks that the user can register are wrapped so user errors don't break the wrapped call.

## Tests

- [ ] Added or updated tests covering the behavior change.
- [ ] `uv run pytest` passes locally.
- [ ] `uv run pytest --cov=agent_budget` coverage at or above 95%.
- [ ] Adversarial-loop and budget-exceed paths have deterministic seeded test data.

## Sibling-library impact

agent-budget has JS (`@mukundakatta/agentbudget`) and Go (`agentbudget-go`) siblings.

- [ ] This change is Python-specific and doesn't apply to siblings.
- [ ] Applies to siblings; tracked at: <sibling issue/PR link>
- [ ] Unsure — leaving for maintainer to assess.

## Risk and impact

Anything reviewers should look at extra carefully (exception fingerprinting, cost-cap arithmetic, async behavior, etc.)?

## Notes for the reviewer

Anything off-checklist worth surfacing.
