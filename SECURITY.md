# Security Policy

## Supported Versions

agent-budget is at v0.1.x. Security fixes will be issued for the current minor (0.1.x). Older minors will not receive backports.

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Reporting a Vulnerability

Please **do not** open a public issue for security vulnerabilities.

Report privately by emailing `mukunda.vjcs6@gmail.com` with the subject `[agent-budget security]`. Include:

- A description of the vulnerability and its impact.
- The version of agent-budget affected (`pip show agent-budget`).
- Reproduction steps or a minimal proof-of-concept.
- Any suggested mitigation, if you have one.

You can expect:

- An acknowledgment within 5 business days.
- A status update within 14 days.
- A coordinated disclosure window of at most 90 days from the acknowledgment.

## Specific Risk Surfaces

agent-budget is a thin pure-stdlib library; the security surface is small, but a few areas are worth special attention:

- **`@budget` retry loop** — the whole reason this library exists is to prevent the [Instructor #2056](https://github.com/jxnl/instructor/issues/2056) class of retry-amplification attack. If you find a way for an adversarial exception payload to bypass `AdversarialLoopDetected` and drive unbounded retries, that's a high-severity report.
- **`fingerprint_exception`** — fingerprinting is `type(exc).__name__` + first 200 chars of `str(exc)`. If an exception type can be crafted such that two semantically-identical failures fingerprint differently (defeating adversarial detection), that's a bug worth reporting.
- **Cost-cap evasion** — if a `cost_extractor` can be tricked into returning negative or non-finite values to bypass `max_cost_usd`, that's a real issue. Currently the library does best-effort sanitization, but edge cases may exist.

We will not pay bug bounties at this time.
