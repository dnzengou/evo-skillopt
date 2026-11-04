# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (observability · v0.2 progress)
- **`GET /metrics`** — Prometheus RED-method exposition on the worker.
  Counters + histograms for requests (by method · path · code), gate
  decisions (base · rrss · cascade — pass/fail), and training outcomes
  (accepted · rejected · failed · timeout). Degrades gracefully to a
  503 with an install hint when `prometheus_client` is not installed.
  High-cardinality paths like `/bots/<id>/skill` are label-collapsed
  to `/bots/{id}/skill` to bound metric cardinality.
- **Structured JSON logs** — `worker/log.py` installs a `JsonFormatter`
  on the root logger. Every log line is a single `{ts, level, logger,
  msg, ...extras}` object with `bot_id` / `job_id` promoted to top-level
  fields. Honors `LOG_LEVEL` env. Datadog / Loki / Vector / CloudWatch
  parse these without further config.
- **CI tightened** — `pytest` and `ruff` are now authoritative (previously
  "informational"). `prometheus-client` installed in the test env so the
  metrics module is exercised with its real dependency. `py_compile`
  covers every `worker/*.py`.

### Added (agent-era GTM · v1.2 of the Blueprint)
- **Live-worker agent discovery.** The worker now serves `GET /` (service
  card JSON), `GET /.well-known/agents.json`, `GET /.well-known/openapi.yaml`,
  `GET /openapi.yaml`, `GET /llms.txt`, `GET /llms-full.txt`, and
  `GET /AGENTS.md` from its own root. Any AI agent landing on the
  live service can self-discover capabilities without a trip back to GitHub.
- **`GTM.md`** — product-neutral go-to-market playbook for agent-era
  products. Three audiences (humans, answer engines, agent runtimes),
  channel mix, metrics, 30-day plan, anti-patterns.
- **`docs/AI_SEO.md`** — implementation notes on the agent-era SEO
  surface.
- **JSON-LD in `docs/index.md`** — `SoftwareApplication` + `HowTo` +
  `FAQPage` for rich-result eligibility in AI answer engines.
- **`.github/workflows/publish-docs.yml`** — deploys MkDocs to GitHub
  Pages so the agents-SEO files are reachable at `site_url`; resolves
  symlinks under `docs/` into real files before build.
- **GitHub repo hygiene.** PR template, bug-report + feature-request
  issue templates, `config.yml` disabling blank issues.
- **Container update.** Dockerfile now copies the full `worker/` dir
  (fixes `rrss_gate`/`cascade`/`arm_signals` imports at runtime) and
  the discovery files to `/app`; sets `DISCOVERY_ROOT=/app`.
- **Blueprint v1.2.** RRSS gate, auto-derive, cascade, ARM, and the
  entire agent-era SEO stack ticked as shipped under `v0.2`.

### Added
- `worker/` layout — stdlib-only Python HTTP service wrapping SkillOpt's `scripts/train.py`.
- `worker/Dockerfile` — multi-stage build, non-root user, tini init, healthcheck.
- `worker/docker-compose.yml` — one-command self-host with named volume + restart policy.
- `worker/fly.toml` — Fly.io deploy template with concurrency + volume mount.
- `worker/README.md` — endpoint and operations reference.
- `INSTALL.md` — comprehensive standalone install guide (pipx, editable, Docker,
  Compose, Fly.io, systemd, Kubernetes, Homebrew, Windows/WSL2, Raspberry Pi).
- `USE_CASES.md` — 10 low-hanging-fruit patterns with ROI math and guardrails.
- `EvoSkillOpt_Blueprint.md` — living roadmap v0.1 → v1.0.
- `docs/CONCEPT.md` — core-idea deep-dive.
- `docs/GLOSSARY.md` — terminology reference.
- `examples/{telegram-summarizer,discord-moderator,slack-standup}/` — starter
  skill.md + eval/held_out.json per pattern.
- `NOTICE`, `TRADEMARKS.md`, `DISCLAIMER.md` — legal safety.
- Modernized CI: py compile · ruff · pytest · shellcheck · docker build + smoke.
- Modernized `pyproject.toml`: renamed project to `evo-skillopt`,
  added `[worker]`, `[claude]`, `[gemini]` extras, ruff/pytest config.

### Removed
- Product-specific / venture-specific docs and assets that did not belong in a
  standalone open-source repo (see git history if you need them).
- `vercel.json`, `api/`, and other single-tenant deploy artifacts.

### Security
- Worker container now runs as non-root, uses tini as PID 1, and has a
  built-in Docker `HEALTHCHECK`.

## [0.1.0] — 2026-08-09

Initial vendored release of the SkillOpt library under evo-skillopt.
