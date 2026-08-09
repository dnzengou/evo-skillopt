# Security policy

## Supported versions

`evo-skillopt` is pre-1.0 software. Only the current `main` branch
receives security fixes. Once we tag `v1.0`, we will maintain a
formal support window here.

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Preferred channels, in order:

1. **GitHub Private Vulnerability Reporting** — open a private report
   from the repository's *Security* tab. This is the fastest path and
   creates an auditable record.
2. **Email** — if private vulnerability reporting is not available to
   you, email the maintainer(s) listed on the repository's contact
   page and put `[evo-skillopt security]` in the subject line.

Please include:

- A clear description of the issue and its impact.
- Steps to reproduce (proof-of-concept preferred).
- Affected version(s) and platform(s).
- Any suggested mitigation you already know about.

We aim to acknowledge reports within **72 hours** and to ship or
document a fix within **30 days** for high-severity issues.

## Scope

In scope:

- The worker HTTP surface (`worker/skillopt_worker.py`).
- The container image and its base configuration.
- Documented deployment templates (Compose, Fly, systemd, Kubernetes).

Out of scope:

- Vulnerabilities in third-party LLM providers or SDKs — please report
  those to the vendor directly.
- Vulnerabilities in the vendored SkillOpt code (report upstream);
  we will mirror any fix here.
- Denial-of-service resulting from running the worker with
  auth disabled (`WORKER_TOKEN` unset). Dev mode is dev mode.

## Coordinated disclosure

We follow a coordinated-disclosure model. Please give us a reasonable
window to ship a fix before publishing details. We will credit you in
the changelog and release notes unless you request otherwise.

## Related documents

- [`DISCLAIMER.md`](./DISCLAIMER.md) — no-warranty statement
- [`TRADEMARKS.md`](./TRADEMARKS.md) — non-affiliation with upstream
- [`NOTICE`](./NOTICE) — third-party attributions
