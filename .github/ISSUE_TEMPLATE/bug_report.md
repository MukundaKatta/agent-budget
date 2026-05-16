---
name: Bug report
about: Report a defect in agent-budget
title: ''
labels: bug
assignees: ''
---

## What happened

A clear, one-paragraph description of the bug.

## What I expected to happen

What you thought would happen.

## Repro

A minimal code sample that triggers the issue. For retry/budget/adversarial-detection bugs, please include the exception class(es) involved.

```python
from agent_budget import budget

# ...
```

## Environment

- `agent-budget` version: (output of `pip show agent-budget`)
- Python version: (output of `python --version`)
- Operating system:
- LLM provider + SDK version (if relevant): (e.g. anthropic 0.40.0, openai 1.55.0, boto3 1.35.x)

## Stack trace

If applicable, paste the full traceback.

```
```

## What did the AttemptEvent stream look like?

If you registered an `on_attempt` hook, paste the events emitted (with any PII redacted).

```
```

## Anything else

Related links, logs, or context.
