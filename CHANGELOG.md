# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
