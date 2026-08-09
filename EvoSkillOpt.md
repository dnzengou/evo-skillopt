# EvoSkillOpt — What it does, where it goes
## v1.0 · Aug 2026 · Private-repo brief

> The productized wrapper around [SkillOpt](https://arxiv.org/abs/2605.23904) that makes text-space skill optimization usable as a service for production LLM agents.

---

## 0. Name — kebab-case vs CamelCase

- **Doc / branding:** `EvoSkillOpt` (matches `EvoMetaClaw`, `EvoStack`, `EvoForge`)
- **Crate / service:** `evo-skillopt` (matches `evo-metaclaw`, `gtm-engine`)
- **Product tier name:** "SkillOpt-as-a-Service" — for pitches; internally use EvoSkillOpt

Both refer to the same thing.

---

## 1. What it is, concretely

**Not a research paper. A production service.**

EvoSkillOpt takes SkillOpt (the paper's training loop) and puts it behind an HTTP endpoint that any agent runtime can call. One request in, one gate outcome out.

**Anatomy today:**

```
your agent runtime           evo-skillopt-worker           SkillOpt (existing)
  (Rust / Go / Node)   ──►   scripts/skillopt_worker.py ──►  scripts/train.py
       │                          │                                │
       │  POST /train             │  subprocess.run()              │  rollout → reflect
       │  {bot_id,                │  parse history.json            │  → aggregate → select
       │   skill_path,            │  compute gate_delta            │  → update → gate
       │   skill_version,         │                                │
       │   eval_split_dir,        │                                │
       │   config,                │                                │
       │   num_epochs}            │                                │
       │◄─────────────────────────┤                                │
       │  {ok,                    │                                │
       │   gate_passed,           │                                │
       │   gate_score_delta,      │                                │
       │   next_version,          │                                │
       │   output_dir,            │                                │
       │   duration_s}            │                                │
```

**What ships in this repo (`scripts/skillopt_worker.py`, 186 lines, stdlib-only):**
- HTTP server: `ThreadingHTTPServer` (no Flask, no FastAPI, no deps)
- `POST /train`: accepts job → shells out to `python scripts/train.py` → parses `outputs/*/history.json` for the last-two-epoch val_reward diff → returns pass/fail
- `GET /health`: liveness
- Bearer auth via `WORKER_TOKEN`
- Hard ceilings: 1h training timeout, 1MB body cap, permissive dev mode if token unset

**What SkillOpt itself provides (the core loop, arXiv:2605.23904):**
- Multi-epoch training with slow update + meta skill memory
- Learning-rate schedules: cosine, linear, constant
- Multi-benchmark: SearchQA, ALFWorld, DocVQA, LiveMathBench, SpreadsheetBench, OfficeQA, SWEBench, +5 more
- LLM backends: Azure OpenAI, OpenAI-compatible, Anthropic Claude, Qwen (vLLM)
- Skill = Markdown file — no weights, no fine-tuning cost, git-diffable
- Held-out gate: reject an epoch that doesn't beat the previous
- Auto-resume from checkpoint on crash

---

## 2. What it can do TODAY (capabilities matrix)

| # | Capability | Status | Where |
|---|-----------|--------|-------|
| 1 | Train a skill.md from trajectories | ✅ shipped | `scripts/train.py` (unchanged from SkillOpt) |
| 2 | Expose training as HTTP `POST /train` | ✅ shipped | `scripts/skillopt_worker.py` |
| 3 | Gate on a held-out eval set | ✅ shipped | `scripts/train.py` gate metric |
| 4 | Rollback on gate failure | ✅ shipped | worker returns `next_version = current` if gate fails |
| 5 | Multi-benchmark support | ✅ shipped | `configs/<benchmark>/default.yaml` |
| 6 | Auto-resume on crash | ✅ shipped | `runtime_state.json` |
| 7 | Fitness-signal ingestion (rolling EMA) | ✅ shipped | `clow-agents/backend/evo-metaclaw/` |
| 8 | Cadence-triggered evolution | ✅ shipped | `evo-metaclaw::eligibility_loop` (6h tick) |
| 9 | Concurrency (multiple bots at once) | ⚠️ one-at-a-time | ThreadingHTTPServer accepts; `train.py` serializes on GPU/API |
| 10 | Per-tenant isolation | ⚠️ manual | Separate `OUTPUT_ROOT` per tenant |
| 11 | Cost accounting per evolution | ❌ not tracked | See § 4.7 |
| 12 | Reward model (vs exact-match) | ❌ | See § 4.4 |
| 13 | A/B skill deployment | ❌ | See § 4.6 |
| 14 | Federated meta-learning across tenants | ❌ | See § 4.3 |

---

## 3. High-ROI application use cases

Five concrete cases where EvoSkillOpt beats prompt-engineering-by-hand. Each is a full playbook: setup, signals, cadence, ROI, guardrails.

### 3.1. Customer-support bot (SaaS · 500-user tier)

**Setup:**
```yaml
name: acme-support
skill: skills/main.md              # your standard support agent prompt (v0.1)
eval:  eval/gold_tickets.json      # 50 tickets with ideal resolutions
signal_source: intercom            # each ticket close → signal
```

**Signal wiring:**
- Ticket resolved (customer marked "solved" or no reply for 48h) → `signal_type: "resolution.ok"`, `fitness_delta: +0.3`
- Escalated to human → `fitness_delta: -0.5`
- CSAT thumbs-up on bot reply → `fitness_delta: +0.5`
- CSAT thumbs-down → `fitness_delta: -0.7`

**Cadence:** weekly (7 days OR 100 signals — whichever first)

**ROI math** (typical mid-market SaaS):
```
Baseline (static skill):     resolution rate 45%, CSAT 3.2/5, 8 hours/day human backup
After 8 weeks evolving:      resolution rate 58%, CSAT 3.9/5, 4 hours/day backup

Savings:  4 hrs/day × $35/hr avg support wage × 22 days = $3,080/mo
Retention: +7 CSAT pts historically = ~1.5% churn reduction
           At $50 ARPU × 500 users = $375/mo saved from retention
Total ROI: ~$3,455/mo — vs EvoSkillOpt cost of $12-40/mo LLM tokens per bot
```

**Guardrails:**
- Never evolve while gate pass rate on golden set < 60% (something regressed globally)
- Human-in-the-loop for skills touching refund/billing sections (regex sentinel)
- Weekly diff review before ship (opt out via `auto_deploy: true`)

**High-ROI trigger:** the moment you have 100+ tickets/week and manually iterate the system prompt at all.

---

### 3.2. Outbound SDR / sales-reply bot

**Setup:**
```yaml
name: acme-sdr
skill: skills/sdr_replies.md       # cold/warm reply templates + objection handling
eval:  eval/booked_meetings.json   # 30 canonical "reply → meeting booked" pairs
signal_source: hubspot             # email interactions
```

**Signal wiring:**
- Reply → meeting booked: `fitness_delta: +1.0`
- Reply → prospect replied but no meeting yet: `+0.2`
- No reply within 7 days: `-0.1`
- Unsubscribe: `-0.5`
- Marked spam: `-1.0`

**Cadence:** biweekly (SDR outbound is slower-moving than support)

**ROI math** (Series-A B2B SaaS, $50 AOV monthly):
```
Baseline SDR bot:            2% reply rate, 4% reply→meeting, 30 sends/day = 0.024 meetings/day
After 12 weeks evolving:     3.1% reply rate, 6% reply→meeting = 0.056 meetings/day
Marginal:                    +0.032 meetings/day × 22 days = +0.7 meetings/mo
Assume 25% meeting→close × $50 ARR × 12 months = $150 LTV per closed deal
Marginal MRR added:          0.7 meetings × 25% × $50 = $8.75/mo — small per bot
BUT: multiply by 5 SDR seats × 12 months = $525/yr per seat that compounds
```

**Real leverage:** the *reasons* EvoSkillOpt found for evolution (readable Markdown diffs) become the SDR playbook the whole team learns from. Meta-knowledge extraction is the second-order ROI.

**Guardrails:**
- Never evolve during a campaign week (freeze skill for A/B validity)
- Reject any evolution that mentions competitor names (compliance)
- Cap evolutions at 1/month per bot to keep behavior stable for the sales team

---

### 3.3. Doc/API assistant (developer product)

**Setup:**
```yaml
name: stripe-docs-helper           # generic; works for any dev doc corpus
skill: skills/api_helper.md
eval:  eval/questions_with_correct_snippet.json    # 100 "Q → code snippet from real docs"
signal_source: bot_frontend        # thumbs-up/down + follow-ups
```

**Signal wiring:**
- User marks helpful: `+0.5`
- User marks not helpful: `-0.7`
- User asks follow-up "actually…" or "that's wrong": `-0.8`
- User copies the code snippet (event fires): `+0.3`

**Cadence:** weekly

**ROI math** (dev-tools company):
```
Baseline: 40% first-response resolution → users escalate to Discord + support
Human cost to resolve escalation: ~20 min × $50/hr = $16.67 per escalation
Volume: 500 escalations/mo at baseline

After 6 weeks evolving:
  First-response resolution: 40% → 62%
  Escalations dropped: 500 → 300
  Savings: 200 escalations × $16.67 = $3,334/mo

Second-order: better docs bot → better trials → higher activation
Estimate ~2% activation lift on 1000 monthly signups × 15% paid conv × $99 ARPU
  = ~$300/mo net-new MRR
```

**Guardrails:**
- Skill must always cite doc URLs from an allowlist (regex `docs.acme.com/*`)
- Never evolve to include deprecated API endpoints (maintain a blocklist in eval)
- Version pins: skill v0.X.0 corresponds to docs milestone; hard-block cross-version drift

---

### 3.4. Content moderator (community / forum / Discord)

**Setup:**
```yaml
name: community-mod
skill: skills/mod_policies.md
eval:  eval/moderation_gold.json   # 200 borderline cases with human-agreed correct action
signal_source: mod_console         # human mod overrides
```

**Signal wiring:**
- Bot action + human confirms: `+0.5`
- Bot action + human overrides (was wrong): `-1.0`
- Bot missed something human catches later: `-0.7`
- Community members appeal + bot upheld: `+0.3`
- Community members appeal + bot reversed: `-0.5`

**Cadence:** weekly

**ROI math** (500-member Discord / mid-scale online community):
```
Baseline: 15% false-positive rate (bot warns/mutes users who didn't deserve it)
         Community trust cost: hard to quantify but very real; ~2% churn attributed
After 8 weeks evolving:
         False positive: 15% → 6%
         Churn attributable to bot: 2% → 0.5%

500 members × 1.5% churn saved × $10/mo Pro tier = $75/mo direct
Growth: healthier community → +8% referral signup rate = ~4 new members/mo
Compounds at network-effect scale.
```

**Guardrails:**
- Never evolve without >85% agreement on the gold eval set (catches globally-worse skills)
- Skills touching bans require 2× the gate threshold (bans are hard to reverse)
- Never evolve during a raid/incident (freeze skill; resume after resolution)

---

### 3.5. Personalized tutor (edtech · adaptive learning)

**Setup:**
```yaml
name: math-tutor-{student_id}      # per-student skill fork (see § 4.3)
skill: skills/tutor_base.md         # shared starting point
eval:  eval/tutor_gold.json + eval/{student_id}_progress.json
signal_source: exercise_completions
```

**Signal wiring:**
- Student solves within hint budget: `+0.5`
- Student needed all hints: `-0.2`
- Student gave up: `-0.7`
- Student solves and self-reports "understood": `+1.0`
- Student solves harder problem next → previous concept solidified: `+0.8`

**Cadence:** per-student, after every 20 exercises

**ROI math** (edtech B2C, $30/mo subscription):
```
Baseline retention (month 3): 42% (industry avg)
With per-student evolving tutor: hypothesized 58% (based on adaptive-learning meta-analyses)

Marginal retention: +16pt × 10,000 subs × $30 = +$48,000 MRR/mo
Cost: 10,000 students × 4 evolutions/mo × $0.30/evolution = $12,000/mo LLM
Net: +$36,000/mo net-new MRR

This is the killer application. Per-user skill personalization at inference-time cost.
```

**Guardrails:**
- Skill can never lower the bar (e.g., accept a wrong answer as right) — grade correctness stays fixed
- Anti-degradation gate: student's next-week test score must not drop >5%
- Parents-can-review flag: full skill diff exposed to parent dashboard

---

## 4. Suggested improvements — the roadmap

Ordered by ROI-per-engineering-week.

### 4.1. Multi-tenancy + job queue (Week 1)

**Problem:** current worker serializes on the GPU/LLM API. Two bots evolving at once = one waits.

**Fix:** Redis / SQLite queue in front of the worker. Multiple worker instances scale horizontally. Each job = `{bot_id, skill_path, priority}`.

**Cost:** ~200 LOC. Redis (or SQLite for MVP).

**ROI:** unblocks 10× more bot volume without renting more GPUs.

---

### 4.2. Reward-model gate instead of exact-match (Week 2–3)

**Problem:** exact-match gate is brittle for open-ended generation. Small phrasing changes fail the gate even when quality is same or better.

**Fix:** train a lightweight reward model (or use an LLM-as-judge with structured rubric) on collected human thumbs. Gate = "reward model score of new skill > old skill by threshold".

**Cost:** ~500 LOC + eval + LLM-judge integration.

**ROI:** eval sets 5–10× cheaper to build (no more hand-curating exact expected outputs). Enables use cases 3.1–3.4 above.

---

### 4.3. Federated evolution / meta-skills (Week 3–6)

**Problem:** 10 acme-support bots at 10 companies all learn similar lessons independently. Waste.

**Fix:** shared meta-skill layer. Per-tenant skills fork from meta; meta evolves from anonymized aggregate signals across tenants; new tenants start from current meta (not blank).

Basically: transfer learning without moving raw customer data.

**Cost:** ~1000 LOC. Anonymization + federated aggregation + versioned meta-skill git.

**ROI:** cold-start time for new tenants drops from 6 weeks → day 1. This is your moat once you have >20 tenants.

---

### 4.4. Skill versioning with git (Week 1–2)

**Problem:** current worker writes to `outputs/<bot>-v<version>-<ts>/`. Skills aren't git-tracked; rollback = filesystem juggling.

**Fix:** every accepted skill becomes a commit in a bare git repo (`skills.git`) per tenant. Rollback = `git checkout <sha>`. Evolution history = `git log`. Public diff view for the marketplace ("what did my bot learn this week?").

**Cost:** ~300 LOC. libgit2 bindings or shell out to git.

**ROI:** compliance/audit story (every skill change is signed + timestamped). Debuggability. **Users can share their evolution history as social proof** (Twitter clip of "look how much smarter my bot got").

---

### 4.5. Cost accounting per evolution (Week 1)

**Problem:** no visibility into LLM tokens spent per evolution → hard to price, hard to optimize.

**Fix:** wrap `train.py`'s LLM calls with a token counter; write cost row per evolution.

**Cost:** ~100 LOC.

**ROI:** enables per-tier pricing that actually reflects marginal cost. Enables "which prompt-template is cheapest?" experiments.

---

### 4.6. A/B skill deployment (Week 4–6)

**Problem:** gate says "new skill is better on held-out eval" but real users may disagree. Need production canary.

**Fix:** deploy new skill to `traffic_pct` fraction of production; compare live metrics (fitness signal + CSAT) between v_old and v_new; auto-promote or auto-rollback.

**Cost:** ~500 LOC. Depends on bot runtime supporting per-request skill selection.

**ROI:** biggest single reliability gain — turns "hope the eval set is representative" into "measured it live".

---

### 4.7. Public marketplace of eval sets (Week 6+)

**Problem:** building an eval set is expertise + time. Barrier to entry for new bot categories.

**Fix:** category-standard eval sets. `customer-support-v1`, `discord-moderation-v1`, `sdr-outbound-v1`. Contributed by community, curated by us. Bots opt in.

**Cost:** small code, large curation.

**ROI:** commoditizes the hardest part of onboarding. Category standards → benchmark leaderboards → the "MMLU of bots".

---

### 4.8. Meta-optimization (SkillOpt-eating-SkillOpt) (Month 3+)

**Problem:** the SkillOpt training loop itself uses a system prompt (the "optimizer") that's hand-written.

**Fix:** the optimizer skill is *itself* a skill.md. Use EvoSkillOpt to evolve the optimizer, gated on aggregate downstream gate-pass rates.

**Cost:** ~medium; requires care to avoid feedback loops.

**ROI:** if this works, the whole system improves at compound rates. This is the paper's asymptotic frontier.

---

### 4.9. Rollback UX + skill inspector (Week 2)

**Problem:** operators need to peek inside evolutions and undo bad ones.

**Fix:** three endpoints:
- `GET /bots/{id}/skill?version=v0.1.5` — raw skill.md at that version
- `GET /bots/{id}/diff?from=v0.1.4&to=v0.1.5` — unified diff
- `POST /bots/{id}/rollback?to=v0.1.4` — mark that version current

Dashboard widget: skill viewer with syntax-highlighted diff.

**Cost:** ~400 LOC + dashboard.

**ROI:** operator trust. Without this, "self-evolving bots" sounds like magic and magic scares enterprise buyers.

---

## 5. Outlook — where this goes

### 5.1. Market positioning

**Adjacent categories today** (all raising money, all have angles you can undercut):

| Category | Examples | What EvoSkillOpt does differently |
|----------|----------|-----------------------------------|
| Prompt management | PromptLayer, LangSmith, PromptHub | Dev-time iteration → we do inference-time evolution |
| Fine-tuning platforms | OpenAI FT API, Together AI | Requires model weights + $$$ → we work with any hosted LLM |
| Observability | Helicone, Braintrust | Read-only measurement → we close the loop |
| Agent frameworks | LangChain, CrewAI, AutoGen | Chain composition → we improve the individual agent |
| Eval platforms | Weights & Biases, Braintrust | Static evals → we use them as gates for continuous learning |

**Wedge sentence:**
> "Every AI agent product ships a v1.0 system prompt and iterates via git commits. EvoSkillOpt makes that iteration happen in production, gated on real user signals, without touching model weights."

### 5.2. Regulatory tailwind

AI systems that "learn on the job" attract scrutiny. EvoSkillOpt's design is auditor-friendly:
- Every skill = git commit with signed timestamp
- Every training run = deterministic (same input → same skill) given seed
- Every gate decision = logged with the numeric threshold
- Rollback = one command, atomic

This is a **compliance asset** as EU AI Act + similar rules bite. Position accordingly to enterprise buyers.

### 5.3. Data flywheel

```
More bots
  → more trajectories logged
     → richer meta-skills across categories
        → better cold-start skills for new bots
           → more bots (loop back)
```

This is the moat. It's not the code (open source, replicable). It's the accumulated trajectories + evolved meta-skills across your customer base. Guard it accordingly (federation, differential privacy on aggregate stats).

### 5.4. Product tiers for the private-repo fork

If commercializing:

| Tier | Price | What |
|------|-------|------|
| Solo | $19/mo | 1 bot, weekly evolution, community eval sets |
| Team | $99/mo | 5 bots, daily evolution, private eval sets, git-tracked skills |
| Growth | $499/mo | 50 bots, hourly cadence, A/B skill deploy, cost dashboard |
| Enterprise | custom | on-prem, federated across tenants, SSO, audit exports |

Pricing benchmark: LangSmith is $39/mo/dev seat. EvoSkillOpt provides more (actual improvement, not just observability); can price 2×.

---

## 6. Notes for the private-repo fork

### 6.1. What to lift and what to leave

**Lift into your private repo:**
- `scripts/skillopt_worker.py` (the whole file — 186 lines, MIT-clean)
- `scripts/train.py`, `scripts/eval_only.py`, `skillopt/` package (SkillOpt itself — MIT)
- `configs/*/default.yaml` (base configs to fork from)
- `ckpt/` (packaged pre-trained skills — starting points for cold-start)
- `EvoSkillOpt.md` (this file — for your product docs)

**Leave in the Clow public repo:**
- `clow-agents/backend/evo-metaclaw/` — Clow-specific service (uses EvoSkillOpt but is not it)
- `clow_landing.html`, `use_cases.html`, `dashboard.html` — Clow-specific UI
- Everything under `bots/` — Clow marketplace inventory

### 6.2. First 3 things to build in the private repo

1. **Job queue** (§ 4.1) — unblocks concurrency, ~1 week
2. **Skill versioning with git** (§ 4.4) — audit story + operator UX, ~1 week
3. **Cost accounting** (§ 4.5) — needed to price the product, ~2 days

Total: ~3 weeks to shippable v0.2 of standalone EvoSkillOpt.

### 6.3. Naming as you scale

- Rename `evo-metaclaw` (Clow-specific) to `evo-orchestrator` (product-neutral) in the private-repo variant
- Keep `evo-skillopt` as the service name
- Consider a fresh product name for the commercial offering (EvoSkillOpt is a mouthful for a landing page hero — "AutoTune" / "SkillLoop" / "Meta" are shorter alternatives)

### 6.4. License positioning

SkillOpt is MIT — you can build a proprietary layer on top. Suggested split:
- **Open-source (MIT):** EvoSkillOpt worker + core training loop (already MIT via SkillOpt)
- **Proprietary:** the job queue, multi-tenancy, federated meta-skills, dashboard, A/B deploy
- **Free tier open-source:** so evaluators can try before buying; conversion happens on multi-bot / multi-tenant features

---

## 7. RRSS status (current — pre-fork)

| Dimension | Status | Where |
|-----------|--------|-------|
| **R**obustify | ⚠️ partial | Worker has timeouts (1h train, 1MB body) but no retry-on-transient-fail; `train.py` failures surface via subprocess returncode |
| **R**eliabilify | ⚠️ partial | `/health` endpoint ✓, logging via `print(flush=True)` ✓, no metrics/traces/alerts |
| **S**olidify | ⚠️ partial | `WORKER_TOKEN` bearer auth ✓, dev-mode bypass documented ✓, no formal test suite for the worker itself (relies on SkillOpt's own tests) |
| **S**tabilize | ❌ | No concurrency control (see § 4.1), no rate limiting, no graceful shutdown yet, no memory bounds on `outputs/` |

**Before shipping to real customers, close all 4.** Priority order for the private-repo fork:

1. Stabilize — add graceful shutdown, `outputs/` retention policy, per-tenant memory caps
2. Robustify — retry on transient errors (LLM API 5xx, network flakes)
3. Reliabilify — Prometheus metrics endpoint, structured logs, PagerDuty on gate failure spikes
4. Solidify — integration test suite hitting a mock SkillOpt (avoid burning LLM tokens in CI)

---

## 8. Cross-references

Within this repo:
- [`scripts/skillopt_worker.py`](./scripts/skillopt_worker.py) — the current worker
- [`clow-agents/backend/evo-metaclaw/src/main.rs`](./clow-agents/backend/evo-metaclaw/src/main.rs) — how the Rust side calls the worker (`call_skillopt_worker` function; opt-in via `SKILLOPT_WORKER_URL`)
- [`EvoStack.md`](./EvoStack.md) — where EvoSkillOpt sits in the whole stack
- [`EvoMetaClaw.md`](./EvoMetaClaw.md) — the Clow-specific evolution orchestrator (uses EvoSkillOpt)
- [`README.md`](./README.md) — SkillOpt itself (paper, install, benchmarks)

External:
- [SkillOpt paper (arXiv:2605.23904)](https://arxiv.org/abs/2605.23904)
- [SkillOpt docs](https://microsoft.github.io/SkillOpt/)

---

*EvoSkillOpt v1.0 · Private-repo brief · MIT · Powered by SkillOpt (arXiv:2605.23904) · KafCa · KafCade · RRSS*
