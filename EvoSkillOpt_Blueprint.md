# EvoSkillOpt — Blueprint & Living Roadmap
## v1.1 · Aug 2026 · The master doc for this repo

> This is the document you carry forward. Vision, architecture, capabilities,
> use-case catalog, roadmap, KPIs — all live here and are updated in place.

---

## Table of contents

1. [Vision](#1-vision)
2. [What evo-skillopt is](#2-what-evo-skillopt-is)
3. [Architecture](#3-architecture)
4. [Ownership matrix](#4-ownership-matrix)
5. [Capabilities](#5-capabilities)
6. [Use-cases catalog](#6-use-cases-catalog)
7. [Reference deployments](#7-reference-deployments)
8. [Roadmap](#8-roadmap)
9. [KPIs](#9-kpis)
10. [Naming rules](#10-naming-rules)
11. [License & commercialization](#11-license--commercialization)
12. [Resilience checklist](#12-resilience-checklist)
13. [Change management](#13-change-management)

---

## 1. Vision

Every AI agent product ships a v1.0 system prompt and iterates via ad-hoc
prompt edits. **evo-skillopt makes that iteration disciplined:** epochs,
batches, validation gates, git-tracked audit trails — the same rigor a
neural-network trainer takes for granted, applied to natural-language
skill files.

The compounding advantage is not the code (open source). It is the
accumulated evaluation sets and evolved skill artifacts a team builds up
inside their own repo, over time.

---

## 2. What evo-skillopt is

**One sentence:** A productized wrapper around SkillOpt
([arXiv:2605.23904](https://arxiv.org/abs/2605.23904)) that exposes
text-space skill optimization as an HTTP service, callable from any
agent runtime in any language.

**Elevator pitch:**
> Your customer-support bot answers 500 tickets a week. Every ticket is
> a training signal. evo-skillopt takes those signals, runs SkillOpt
> training against your bot's held-out eval set, and ships an updated
> `skill.md` every Monday — only if it beats the previous one. If it
> doesn't, we roll back. Never touches model weights. Typical cost:
> single-digit dollars per evolution in LLM tokens.

**Not:** a new training algorithm · a new LLM · a prompt IDE · a
standalone eval framework.

**Is:** the operations layer that closes the loop between (a) real
production signals and (b) the SkillOpt training loop, at inference-time
cost, with git-tracked audit trails.

---

## 3. Architecture

```
   your agent runtime          evo-skillopt worker           SkillOpt core
   (any language)              (Python HTTP · stdlib)        (vendored MIT)
        │                            │                             │
        │  POST /train               │                             │
        │  {bot_id,                  │                             │
        │   skill_path,              │                             │
        │   skill_version,           │                             │
        │   eval_split_dir,          │                             │
        │   config,                  │                             │
        │   num_epochs,              │                             │
        │   gate_min_improvement}    │                             │
        │───────────────────────────►│                             │
        │                            │ subprocess.run(train.py) ──►│
        │                            │                             │  rollout
        │                            │                             │  reflect
        │                            │                             │  aggregate
        │                            │                             │  select
        │                            │                             │  update
        │                            │                             │  gate
        │                            │◄──── history.json ──────────│
        │◄──────── JSON response ────│  (delta, next_version, dir) │
```

**Components:**

| Component                        | Language          | Where           | Status                     |
|----------------------------------|-------------------|-----------------|----------------------------|
| `worker/skillopt_worker.py`      | Python (stdlib)   | this repo       | ✅ v0.1 shipped            |
| `worker/Dockerfile` + compose    | —                 | this repo       | ✅ shipped                 |
| `worker/fly.toml`                | —                 | this repo       | ✅ shipped                 |
| SkillOpt core                    | Python            | `skillopt/`     | ✅ vendored (MIT upstream) |
| Optional orchestrator            | any               | out-of-repo     | reference only             |
| Job queue                        | SQLite / Redis    | this repo       | ⬜ Q1 target                |
| Reward-model gate                | Python            | this repo       | ⬜ Q2 target                |
| Federated meta-skills            | Python            | this repo       | ⬜ Q3 target                |

---

## 4. Ownership matrix

Bright line between what this repo owns and what it inherits:

| Layer                                        | Owner            | License                | Origin                       |
|----------------------------------------------|------------------|------------------------|------------------------------|
| SkillOpt training loop                       | upstream authors | MIT                    | vendored under `skillopt/`   |
| SkillOpt benchmarks (SearchQA, ALFWorld, …)  | upstream authors | MIT                    | vendored under `configs/`, `ckpt/` |
| LLM backend abstraction                      | upstream authors | MIT                    | vendored                     |
| **HTTP worker**                              | this project     | MIT                    | `worker/skillopt_worker.py`  |
| **Deployment configs**                       | this project     | MIT                    | `worker/Dockerfile`, `fly.toml`, compose |
| **Examples**                                 | this project     | MIT                    | `examples/`                  |
| **Docs**                                     | this project     | MIT (CC-BY optional)   | `docs/`, this file           |
| Job queue (planned)                          | this project     | MIT                    | Q1                           |
| Reward-model gate (planned)                  | this project     | MIT                    | Q2                           |
| Federated meta-skills (planned)              | this project     | MIT                    | Q3                           |

Everything shipped in this repo is MIT. Downstream products that build
on top of it can choose whatever license fits their business.

---

## 5. Capabilities

Version-numbered. Tick capabilities as they ship.

### v0.1 (shipped)

| Capability                                                        | Where |
|-------------------------------------------------------------------|-------|
| ✅ HTTP `POST /train` returning gate outcome                       | `worker/skillopt_worker.py` |
| ✅ Bearer auth via `WORKER_TOKEN`                                  | worker |
| ✅ Body cap (1 MB) + subprocess timeout (1 h)                      | worker |
| ✅ Dev-mode fallback when token unset                              | worker |
| ✅ Parses `history.json` for real gate delta                       | worker |
| ✅ SemVer bump (`0.1.4 → 0.1.5`) semantics                         | worker |
| ✅ Multi-stage Docker image, non-root, tini init                   | `worker/Dockerfile` |
| ✅ Docker Compose one-command self-host                            | `worker/docker-compose.yml` |
| ✅ Fly.io deploy template                                          | `worker/fly.toml` |
| ✅ CI: py compile · ruff · pytest · shellcheck · docker build      | `.github/workflows/ci.yml` |
| ✅ Three runnable example skills + held-out evals                  | `examples/` |

### v0.2 target (Q1 — ~3 weeks)

| Capability                                                         | Notes |
|--------------------------------------------------------------------|-------|
| ✅ RRSS-scored gate (opt-in `rrss` block on `POST /train`)          | `worker/rrss_gate.py` · four axes, per-axis floors, composite delta |
| ✅ Auto-derive RRSS inputs from run's history + rollouts            | `worker/rrss_from_history.py` · `rrss.auto_from_history: true` |
| ✅ Cascade evaluator (`POST /train/cascade`)                        | `worker/cascade.py` · min / mean / product / weighted_mean |
| ✅ ARM lifecycle fitness (`POST /fitness/arm`)                      | `worker/arm_signals.py` · Acquire / Retain / Monetize buckets |
| ✅ Agent-discovery endpoints on the live worker                     | `GET /` card · `/.well-known/agents.json` · `/llms.txt` · `/openapi.yaml` |
| ✅ Agent-era SEO surface (repo + docs site)                         | `AGENTS.md` · `llms.txt` · `llms-full.txt` · `.well-known/{agents.json,openapi.yaml}` · JSON-LD (SoftwareApplication + HowTo + FAQ) · `CITATION.cff` |
| ✅ MkDocs → GitHub Pages publish workflow                           | `.github/workflows/publish-docs.yml` · serves agent-SEO files at `site_url` |
| ⬜ Job queue (SQLite-backed) — concurrent bot evolution             | Priority queue; ~200 LOC |
| ⬜ Git-tracked skill versioning                                     | libgit2 or shell-out `git`; ~300 LOC |
| ⬜ Cost accounting per evolution (LLM token counter)                | Wrap backend calls; ~100 LOC |
| ✅ Rollback endpoint set (`POST /bots/{id}/rollback` + `GET …/skill` + `…/history` + `…/diff`) | `worker/skill_store.py` · versioned file store · versions immutable · path-escape-safe |
| ✅ Structured JSON logs with `bot_id` + `job_id` correlation         | `worker/log.py` · one JSON line / record · extras promoted to top-level keys |
| ✅ Prometheus `/metrics` endpoint                                   | `worker/metrics.py` · RED method + gate + training counters · 503 degradation when `prometheus_client` missing |

### v0.3 target (Q2 — ~6 weeks)

| Capability                                                         | Notes |
|--------------------------------------------------------------------|-------|
| ⬜ Reward-model gate (LLM-as-judge with rubric)                     | ~500 LOC + eval |
| ⬜ A/B skill deployment (canary %)                                  | Requires runtime that supports per-request skill choice |
| ⬜ Dashboard UI (fitness curves, evolution log, cost breakdown)     | Svelte/React single-file OK for MVP |
| ⬜ Per-tenant isolation (SQLite → Postgres)                         | Tenant-scoped storage + audit |
| ⬜ Rate limiting (per-tenant, per-bot)                              | Token bucket |
| ⬜ Human-in-the-loop review queue for sensitive changes             | Regex on skill diff |

### v0.4 target (Q3 — ~9 weeks)

| Capability                                                         | Notes |
|--------------------------------------------------------------------|-------|
| ⬜ Federated meta-skills (cross-tenant learning, no raw data)       | Aggregation + DP layer |
| ⬜ Public marketplace of eval sets                                  | Category standards |
| ⬜ Auto-generated skill diffs as user-facing summaries              | Weekly digest |
| ⬜ Skill inspector — read-only preview + syntax-highlighted diff    | Trust-building UX |
| ⬜ Cost prediction before triggering evolution                      | Historical $/token → estimate |

### v1.0 target (Q4)

| Capability                                                         | Notes |
|--------------------------------------------------------------------|-------|
| ⬜ Meta-optimization (the optimizer prompt is itself an evolving skill) | Optional |
| ⬜ SSO / SAML passthrough                                           | Enterprise ask |
| ⬜ Compliance exports (audit log CSV/PDF, GDPR data export)         | Regulatory story |
| ⬜ Multi-region deployment templates                                | US + EU |
| ⬜ On-prem installer (Docker Compose + Helm chart)                  | Enterprise ask |

---

## 6. Use-cases catalog

Each pattern is described in [`USE_CASES.md`](./USE_CASES.md) with signal
wiring, cadence, ROI math, and guardrails. Summary here:

| # | Pattern                                | Signal source                          | ROI shape                                 |
|---|----------------------------------------|----------------------------------------|-------------------------------------------|
| 1 | Customer-support bot                   | Ticketing CSAT + resolution outcome    | Deflected human hours                     |
| 2 | Outbound sales-reply assistant         | CRM reply/meeting-booked events        | Meta-knowledge → team playbook            |
| 3 | Docs / API assistant                   | Thumbs-up/down + follow-ups            | Deflected support + activation lift       |
| 4 | Community moderator                    | Human-mod overrides                    | Mod hours saved + retention               |
| 5 | Adaptive tutor                         | Exercise completions + progress        | Retention + upsell                        |
| 6 | Group-chat summarizer                  | Thumbs on digests                      | Attention saved / week                    |
| 7 | Async standup assistant                | Digest-response opens                  | Meeting hours avoided                     |
| 8 | Content moderator with escalation rubric | Precision/recall vs held-out set     | False positives ↓                         |
| 9 | Interview / role-play coach            | User rating on realism + usefulness    | Upsell trigger                            |
| 10| Meeting-notes assistant                | Human edits after generation           | Editing time ↓                            |

Each use case must document, in order:

1. **What** — one sentence
2. **skill.md structure** — 30–50 lines of behavior + guardrails
3. **eval/held_out.json structure** — 20–30 examples w/ `reward_criteria`
4. **Signal wiring** — table of events → `fitness_delta`
5. **Cadence** — how often evolution triggers
6. **ROI math** — baseline vs post-evolution with concrete numbers
7. **Guardrails** — what evolution can NEVER change

---

## 7. Reference deployments

Ship one named reference deployment per quarter to prove pattern
generality. Nothing here is a product endorsement or a commercial claim
— they're integration case studies contributed under MIT.

| Q  | Reference deployment            | Status         |
|----|---------------------------------|----------------|
| Q1 | Customer-support SaaS example   | ⬜ open target |
| Q2 | Healthcare-scribe example       | ⬜ open target |
| Q3 | Fintech-KYC assistant example   | ⬜ open target |
| Q4 | Legal-doc-reviewer example      | ⬜ open target |

Contributions welcome — see [`CONTRIBUTING.md`](./CONTRIBUTING.md).

---

## 8. Roadmap

### Quarter by quarter

| Q  | Version | Theme                | Key ships |
|----|---------|----------------------|-----------|
| Q1 | v0.2    | Foundation for scale | Job queue · git-tracked skills · cost accounting · rollback UX · structured logs · Prometheus metrics |
| Q2 | v0.3    | Product-ready        | Reward-model gate · A/B deploy · dashboard UI · per-tenant isolation · rate limiting · HITL queue |
| Q3 | v0.4    | Ecosystem            | Federated meta-skills · eval-set marketplace · weekly-diff digests · skill inspector · cost prediction |
| Q4 | v1.0    | Enterprise           | Meta-optimization · SSO · compliance exports · multi-region · on-prem installer |

### 3-week Q1 micro-plan

**Week 1**
- Sync CI: py compile · ruff · pytest (stub) · docker build · shellcheck
- Author `docs/use-cases/_TEMPLATE.md`
- Stub Solidify.1 (pytest test suite scaffold)

**Week 2**
- Job queue (SQLite-backed, ~200 LOC)
- Cost accounting hook (~100 LOC)
- Structured logs (JSON) with `bot_id` correlation

**Week 3**
- Git-tracked skill versioning
- Rollback + diff endpoints
- Prometheus `/metrics`
- CHANGELOG v0.2 · Docker image publish to GHCR

**Deliverable:** v0.2 tagged release with docker image + green smoke.

---

## 9. KPIs

**Product health (weekly):**
- p50 / p95 evolution wall-time
- Gate pass rate (per bot)
- Cost per evolution (LLM $)
- Cost per accepted evolution (efficiency)
- Rollback rate (should trend < 5%)
- Skill drift: KL-divergence between v0.1.0 and current (safety)

**Ecosystem (quarterly):**
- GHCR image pulls
- GitHub stars / forks
- Community-contributed eval sets (count + categories)
- Named third-party integrations

---

## 10. Naming rules

Preserve consistency. Reject drift.

| Concept                                       | Public / docs   | Code / packages          |
|-----------------------------------------------|-----------------|--------------------------|
| The project                                    | evo-skillopt    | `evo-skillopt`           |
| The worker binary                              | evo-skillopt worker | `worker/skillopt_worker.py` |
| The vendored algorithm                         | SkillOpt        | `skillopt/`              |

**Rules:**
- kebab-case in code and package names
- Never split into three words in public copy (e.g. "evo skill opt" — no)
- Reserve `evo-` prefix for future sibling projects in the same family
  that you author yourself — do not use it to imply relationships that
  don't exist

---

## 11. License & commercialization

**This repo:** MIT. Everything shipped here is free to self-host, fork,
and adapt.

**A commercial hosted offering** can layer proprietary code on top —
job queue at scale, dashboard UI, reward-model gates, federated
learning, enterprise SSO — without contaminating the open core. That
layer lives in a separate repo, not here.

**Suggested tier shapes** (for anyone building a hosted offering):

| Tier         | Scope                                                                     |
|--------------|---------------------------------------------------------------------------|
| Self-host    | Free · MIT · community support · everything in this repo                  |
| Solo         | 1 tenant · 1 bot · weekly evolution · hosted worker · basic dashboard     |
| Team         | 5 bots · daily evolution · private eval sets · cost dashboard             |
| Growth       | 50 bots · hourly cadence · A/B deploy · reward model · HITL queue         |
| Enterprise   | Federated meta-skills · SSO · compliance · on-prem · SLA                  |

Pricing comparables: observability tools (~$40/seat/mo), eval frameworks
(~$100/entry/mo), prompt versioning (~$50/seat/mo). evo-skillopt
covers the union of those and closes the loop.

---

## 12. Resilience checklist

Pre-v0.2 shipping hard-gate:

- [ ] **Stabilize.1** — SIGTERM handler; drain in-flight jobs (~30 LOC)
- [ ] **Stabilize.2** — `OUTPUT_ROOT` retention (keep last 30 per bot, ~50 LOC)
- [ ] **Stabilize.3** — Per-tenant caps on skill history (~30 LOC)
- [ ] **Robustify.1** — Retry on transient LLM 5xx / ECONNRESET (~80 LOC)
- [ ] **Robustify.2** — Circuit breaker on provider (5 fails → trip; probe every 30 s) (~100 LOC)
- [ ] **Reliabilify.1** — Prometheus `/metrics` (~100 LOC)
- [ ] **Reliabilify.2** — Structured JSON logs w/ `bot_id` + `job_id` (~50 LOC)
- [ ] **Reliabilify.3** — Alert wiring (webhook on gate-failure > 40 % for 1 h) (~30 LOC)
- [ ] **Solidify.1** — pytest suite for worker (mock SkillOpt; ~15 tests, ~400 LOC)
- [ ] **Solidify.2** — CI runs pytest + docker build on every push (~30 LOC yml)

Total: ~1000 LOC + tests. ~2 weeks of eng.

---

## 13. Change management

**How to update this Blueprint:**

1. Every commit that ships a capability from §5 → tick `⬜` → `✅` and
   add a one-line changelog entry at the bottom.
2. Every quarterly review → update §8 roadmap + §9 KPI actuals.
3. Every new named reference deployment → append to §7 (never delete
   — history compounds).
4. Every version tag (`v0.2`, `v0.3`, …) → snapshot this file into
   `docs/blueprint-history/vX.Y.md`.

**Cadence:**
- Weekly: tick capabilities
- Monthly: KPI actuals
- Quarterly: full read-through + roadmap re-plan

**Ownership:** this file is the Blueprint. If it disagrees with a
decision made in a meeting, either update it same-day or don't make
that decision.

---

## Agent-era GTM (new in v1.2)

Discovery is now a product feature, not a marketing afterthought.
Every release ships the agent-SEO stack alongside the code:

- `AGENTS.md` at repo root — short, mechanical orientation for coding
  agents and LLM crawlers.
- `llms.txt` + `llms-full.txt` — [llms.txt convention](https://llmstxt.org/)
  entry points.
- `.well-known/agents.json` — machine-readable manifest of endpoints,
  concepts, and entry points.
- `.well-known/openapi.yaml` — OpenAPI 3.1 contract for every endpoint.
- JSON-LD `SoftwareApplication` + `HowTo` + `FAQPage` in `README.md`
  and `docs/index.md` for AI-search answer engines.
- `CITATION.cff` for academic and agent-reference citations.
- `GET /`, `GET /.well-known/agents.json`, `GET /llms.txt`,
  `GET /openapi.yaml` on the **live worker** — any agent that hits
  the running service self-discovers capabilities without a trip
  back to GitHub.

Why: in the agent era, half the funnel is read by an LLM, not a
human. The product that is parseable by an agent wins the agent's
citation; the product that is cited by agents wins a funnel it costs
nothing to re-fill.

The full playbook — three audiences (humans, answer engines, agent
runtimes), channel mix, metrics, 30-day plan, anti-patterns — lives
in [`GTM.md`](./GTM.md). Implementation notes on the SEO surface are
in [`docs/AI_SEO.md`](./docs/AI_SEO.md).

## Changelog

| Version | Date       | Change |
|---------|------------|--------|
| 1.0     | 2026-08-09 | Blueprint created. v0.1 shipped. Q1 → Q4 roadmap set. |
| 1.1     | 2026-08-09 | Scrubbed to product-neutral. Container hardened (multi-stage, non-root, tini). Compose added. Docker healthcheck added. |
| 1.2     | 2026-11-03 | v0.2 capabilities shipped: RRSS gate, auto-derive, cascade, ARM. Agent-era SEO stack shipped: AGENTS.md, llms.txt, agents.json, OpenAPI, JSON-LD (SoftwareApplication + HowTo + FAQ), CITATION.cff, publish-docs workflow. Live worker now self-discovers via `GET /` card + discovery paths. GTM playbook + AI-SEO notes published. |
