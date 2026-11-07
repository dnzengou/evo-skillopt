# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (operational hygiene · v0.2 RRSS closure list)
- **SIGTERM / SIGINT graceful drain** (Stabilize.1). Receiving a
  shutdown signal flips a shared `_shutting_down` flag; new POSTs
  get 503 with a `retry_after_s` hint while in-flight work finishes;
  GETs on `/health`, `/metrics`, and the discovery paths stay answered
  so orchestrators and agents can observe the drain. Bounded by
  `SHUTDOWN_GRACE_SECONDS` (default 30, matches Kubernetes'
  `terminationGracePeriodSeconds`). Logged as `signal-received` →
  `worker-draining` → `worker-drained-clean` (or
  `worker-forcing-shutdown` if the grace window ran out).
- **`OUTPUT_ROOT` retention policy** (Stabilize.2). New module
  `worker/retention.py` prunes training run dirs per bot, keeping the
  most-recent `OUTPUT_RETENTION_PER_BOT` (default 30). Called
  opportunistically after every `/train`, so disk stays bounded without
  a cron. Pure stdlib, path-escape safe, idempotent, graceful (a single
  delete failure doesn't abort the sweep). Pruning events emitted as
  structured `retention` log lines with `pruned` / `failed` / `kept`
  counts.
- `.env.example` now documents `SHUTDOWN_GRACE_SECONDS` and
  `OUTPUT_RETENTION_PER_BOT`.
- Tests — `tests/test_retention.py` (8 cases): regex matching, keep-N
  semantics, idempotency, per-bot isolation, unrelated-dir safety,
  empty/missing root, report shape. `tests/test_shutdown.py` (8
  cases): in-flight counter round-trip, concurrent-begin safety,
  drain-flag flip, idempotent shutdown, grace-window drain-wait.

### Added (SHOWCASE — drop-in integration recipes)
- **`SHOWCASE.md`** — eight runnable recipes any coding agent can
  lift verbatim into a customer app: OpenAI SDK (Python),
  Anthropic SDK, LangChain (`PromptTemplate`), LlamaIndex,
  CrewAI (`@tool evolve_skill`), Vercel AI SDK (TypeScript Next.js
  edge route), shell/cron loop, and a cost-estimator-first pattern
  so autonomous agents don't fire `/train` blind. Every snippet
  uses only `EVO_URL` + `EVO_TOKEN` as config and the receiver's
  native HTTP client — no evo-skillopt Python dependency required.
- Discovery surface — README docs table, `llms.txt`, and
  `.well-known/agents.json` `entry_points` all list SHOWCASE.md
  so answer engines and coding agents find it at any discovery
  entry point.

### Added (git-tracked audit trail · v0.2 progress)
- **Opt-in git tracking in `worker/skill_store.py`** — when
  `SKILL_STORE_USE_GIT=1` is set (default **off**), every
  `put_version` and `rollback` additionally commits to a per-bot git
  repo at `<slug>/.git/` with `git init --initial-branch=main` on the
  first write. The resulting commit SHA is written into that entry's
  `history.json` row. Author identity is configurable via
  `SKILL_STORE_GIT_NAME` / `SKILL_STORE_GIT_EMAIL` env.
- **Graceful fallback.** A missing `git` binary never fails the
  file-store write — `_git_commit` catches subprocess failures and
  returns None; the version lands on disk either way and `history.json`
  simply has no `sha` field for that entry.
- **Container ships git** and sets `SKILL_STORE_USE_GIT=1` by default
  so containerized installs get the audit trail out of the box.
- **Tests** — `tests/test_skill_store_git.py` (5 cases): commit
  creation on put_version, SHA present in history entry, rollback
  appears in git log, SKILL_STORE_USE_GIT=False leaves the dir untouched,
  rollback SHA persisted to history. Skips gracefully when git is
  unavailable.
- **Docs** — Blueprint v0.2 "git-tracked skill versioning" ticked.
  Glossary entries added for *skill store* and *git-tracked audit trail*.

### Added (cost estimator · v0.2 progress)
- **`worker/cost_estimator.py`** — pure planning-time estimator. Given
  a `Workload` (num_epochs, n_train_items, n_eval_items,
  mean_tokens_per_item, rollouts_per_item, reflections_per_item,
  output_token_ratio) and a model name, returns input/output tokens,
  per-phase dollar breakdown (rollout / reflect / gate), total cost,
  and the assumptions dict. Caller can override prices at the call
  site. Built-in registry covers 13 models across OpenAI, Anthropic,
  Google, and `local` (free).
- **`GET /cost/models`** — the price registry as JSON.
  **Unauthenticated** so an agent picking a model can read it before
  it even holds a token.
- **`POST /cost/estimate`** — pre-run estimate for one evolution.
  Validates unknown workload fields instead of silently dropping them.
- Discovery surface updated — AGENTS.md, llms.txt, `.well-known/agents.json`,
  `.well-known/openapi.yaml`, service card at `GET /`.
- Blueprint v0.2 "cost accounting" tick: planning-time estimator shipped;
  runtime token counter deferred (needs hooking the vendored SkillOpt
  LLM client — separate PR).

### Added (release automation)
- **`.github/workflows/release.yml`** — tag-driven (`v*.*.*`) release
  pipeline: builds sdist + wheel with `python -m build`, runs
  `twine check --strict`, publishes to PyPI via **Trusted Publisher**
  (OIDC — no stored API tokens), then creates a GitHub Release with
  the artifacts attached and the matching CHANGELOG section as notes.
  Manual run via `workflow_dispatch` is build-only (no publish) for
  pre-release smoke tests.
- **`RELEASING.md`** — one-time PyPI Trusted Publisher setup (pending
  publisher, workflow, environment) plus the every-release procedure
  (bump → changelog → tick blueprint → verify → commit → tag → push).

### Added (rollback endpoint set · v0.2 progress)
- **`worker/skill_store.py`** — versioned, path-escape-safe file store
  for bot skill files. Layout: `<slug>/meta.json` (current pointer) +
  `history.json` (chronological entries) + `v<version>.md` (immutable
  version content). `put_version` is idempotent on identical content,
  raises on divergent content for the same version. `slugify` lowercases
  and replaces `/` with `-`, enforces a strict regex, caps length at 100.
- **`GET /bots/{id}/skill`** — current skill content + current pointer.
  Query `?version=X.Y.Z` to fetch a specific version.
- **`GET /bots/{id}/history`** — version history with `{version, ts,
  gate_score_delta, source, note}` per entry.
- **`GET /bots/{id}/diff?from=A.B.C&to=X.Y.Z`** — unified diff between
  two versions as `text/x-diff`.
- **`POST /bots/{id}/rollback?to=X.Y.Z`** — point `current` at an older
  version. Rollbacks are recorded in history with source `"rollback"`.
  Never destructive. Accepts `to` and `note` via query string or JSON
  body. Refuses rollback to the current version (409-equivalent 404
  with explanation) and to non-existent versions.
- **Discovery surface updated** — AGENTS.md endpoint table, llms.txt,
  `.well-known/agents.json`, `.well-known/openapi.yaml`, and the
  service card at `GET /` all list the four new bot endpoints.
- **Dockerfile** — now creates `/data/bots` with proper ownership and
  sets `SKILL_STORE_ROOT=/data/bots`.
- **`.env.example`** — documents `SKILL_STORE_ROOT` and `LOG_LEVEL`.

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
