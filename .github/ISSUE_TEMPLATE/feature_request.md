---
name: Feature request
about: Suggest a new capability or improvement for agent-budget
title: ''
labels: enhancement
assignees: ''
---

## Problem statement

What gap does this close? What is the current pain (concrete: an error you see, a workaround you wrote, a metric you can't get)?

## Proposed surface

A sketch of the API or behavior. Code preferred over prose:

```python
# What you imagine calling
```

## Why this belongs in agent-budget (not tenacity or backoff)

agent-budget exists for LLM-specific retry/budget failure modes that generic retry libs don't address (see `CONTRIBUTING.md`). Explain why this should live here rather than as a wrapper on `tenacity` or in a separate library.

## Cross-language scope

agent-budget has JS (`@mukundakatta/agentbudget`) and Go (`agentbudget-go`) siblings.

- [ ] This feature is Python-specific (e.g. uses `contextvars`, `asyncio`).
- [ ] This feature should also exist in the JS/Go siblings.
- [ ] Unsure — discuss in this issue.

## Alternatives considered

What else have you tried or considered? (Custom decorator? Different lib? Doing nothing?)

## Willing to contribute?

- [ ] I can open a PR for this
- [ ] I can help test it
- [ ] Looking for someone else to build it
