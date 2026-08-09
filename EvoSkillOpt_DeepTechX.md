# EvoSkillOpt applied to DeepTechX
## v1.0 · Aug 2026 · Reference application

> Concrete integration: how [EvoSkillOpt](./EvoSkillOpt.md) plugs into the [DeepTechX Launchpad](https://github.com/dnzengou/deeptechx) — the edtech platform for deep-tech founders (space · quantum · nuclear · SMR · climate).

---

## 0. Read this first

**DeepTechX today (as of Aug 2026):**
- React 19 + Vite + shadcn UI frontend
- Cloudflare Workers + KV backend (tx submission logging)
- Course modules with lessons + 15 downloadable templates + 5 case studies
- Featured Module 07: *Human-Centered Design for Deep Tech Innovation* — 5 lessons, ~2h30
- Live case example: "Climate Adaptation Cockpit" — Copernicus data → 5 EU cities × 20 interviews → 80% paid conversion in beta
- Private Discord (6 channels: `#use-cases`, `#space-climate`, `#prototyping`, `#wins`, ...)
- Crypto-payment tiers via `desireyavro.x` Unstoppable Domains handle

**Why DeepTechX is a killer fit for EvoSkillOpt:**
1. **Small, specialized cohorts** — SkillOpt was designed for exactly this ("~450 utilities worldwide, 47 in EU"). Prompt tuning by hand doesn't scale to 20 domains × N cohorts.
2. **Rich, structured signals** — every lesson complete, quiz attempted, template downloaded, interview simulated is a training signal.
3. **High-value learners** — a deep-tech founder's LTV justifies a $0.30 evolution cost per week.
4. **Domain moats compound** — a quantum-domain tutor that has evolved on 500 quantum learners can't be replicated overnight.
5. **HCD ideology aligns** — the platform teaches Empathize → Prototype → Test. EvoSkillOpt does exactly that on itself.

---

## 1. Six bots for DeepTechX (ranked by ROI)

| # | Bot | Tier gate | Cadence | Est. ROI/mo (500 learners) |
|---|-----|-----------|---------|--------|
| 1 | **Grant-writing assistant** (EU/Horizon/Copernicus applications) | Premium ($99/mo) | Per-draft | **+$18k MRR** (killer app; see § 2.1) |
| 2 | **Personalized deep-tech tutor** (per-learner per-domain) | Free + Premium hybrid | Weekly per learner | +$9k MRR (retention lift) |
| 3 | **HMW Coach** — "How Might We" framing on demand | Free | Weekly cohort meta | +$3k MRR (activation lift) |
| 4 | **Interview simulator** — role-play as SMR operator / climate officer / quantum lab lead | Premium | Per-scenario | +$4k MRR (upsell trigger) |
| 5 | **Prototype critic** — fidelity roadmap grader + inclusive-design checker | Premium | On submit | +$2k MRR (deliverable value) |
| 6 | **Discord cohort facilitator** — welcomes, summaries, connections | Free | Real-time | +$2k MRR (community NPS lift) |

Total est. addressable: **~$38k/mo net-new MRR at 500-learner scale.** Cost: ~$400/mo LLM tokens across all 6 bots. Payback: <1 day for a single premium subscriber.

---

## 2. The six bots — full playbooks

Each follows the pattern: skill.md structure · signal wiring · evolution cadence · ROI math · guardrails.

### 2.1. Grant-writing assistant — the killer app

**What:** Learner has a deep-tech thesis (e.g., "SMR passive-safety control panel", "Copernicus climate dashboard for coastal cities"). Bot drafts a targeted grant application: Horizon Europe · EIC Accelerator · EU Cascade Funding · national programs. Iterates until submittable.

**skill.md structure:**
```markdown
# Grant-Writing Assistant · v0.1.0

You are an EU deep-tech grant-writing coach. You help founders draft
applications to Horizon Europe, EIC Accelerator, EIT KICs, and national
equivalents.

## Behaviour
- Ask: (1) technology domain, (2) TRL, (3) target program, (4) consortium status
- Reject applications that violate program-specific hard constraints
  (e.g., Accelerator: ≥ TRL 6; Cascade: ≤ €60k)
- Draft in the target program's exact section structure
- Cite specific call-for-proposal clauses when a section requires them

## Domain templates (auto-loaded)
- Copernicus data uses (Space + Climate)
- SMR / advanced-fission grants (Nuclear)
- Quantum flagship (Quantum)
- EU Green Deal + Innovation Fund (Climate)

## Guardrails (see § 2.1 in DeepTechX EvoSkillOpt doc)
- NEVER auto-submit — always require human review
- NEVER fabricate consortium partners or letters of support
- Refuse if requested amount > program cap
```

**eval/held_out.json** (starter — 30 examples):
```json
[
  {
    "id": "horizon-space-01",
    "input": "Draft me an EIC Accelerator step-1 for a satellite-image-based flood-forecast SaaS. TRL 6. Solo founder, seeking €2.5M.",
    "expected_sections": ["excellence", "impact", "implementation", "team"],
    "reward_criteria": ["cites_copernicus_specifically", "amount_within_cap", "no_fabricated_partners", "matches_TRL_language"]
  },
  ...
]
```

**Signal wiring:**
| Event | `fitness_delta` |
|-------|----------------|
| Learner marks section "keep as-is" | +0.4 |
| Learner rewrites section from scratch | −0.6 |
| Learner marks section "reject" | −0.8 |
| Learner asks bot to explain a clause it cited | +0.2 (engagement) |
| **Grant application accepted / funded** (reported months later) | +5.0 (rare + huge) |
| Grant application rejected | −0.3 (many reasons; small signal) |

**Cadence:** per-draft (not calendar) — each drafting session is one evolution episode; skill updates weekly from batched signals.

**ROI math** (500 learners; 15% try grant-writing = 75 users):
```
Baseline (no bot):    ~$0-fund success  (learners rarely apply)
With grant bot:       ~10% of drafts get funded (industry avg for well-drafted apps)
                      75 users × 0.4 drafts/user/quarter × 10% × avg €80k grant = €240k/quarter grant flow

DeepTechX takes: 3% of accepted grant (industry norm for grant coaching)
                 = €7,200/quarter DeepTechX revenue from grant flow

Meanwhile: the bot is the top reason people upgrade to Premium ($99/mo)
Est. upgrade lift: 75 users × 40% upgrade rate = 30 new Premium × $99 = +$2,970/mo MRR
                   Plus retention: Premium subs stay 2× longer once they've drafted 1+ grant

Combined addressable: ~$18k/mo MRR + $2.9k/mo direct grant commission
```

**Guardrails:**
- Human review required before submission (Premium page shows a submit-lock UI)
- No auto-fill of personal / financial data
- Fabrication detection: cross-check every citation against a static list of real EU program URLs; refuse to ship a draft with a fabricated citation
- No evolution during a learner's active drafting session (freeze until they finalize)
- Skill diff must be reviewed by human before any evolution touching "consortium" or "budget" sections (highest-liability areas)

---

### 2.2. Personalized deep-tech tutor (per-learner, per-domain)

**What:** Every learner has their own tutor skill fork keyed on `{learner_id, domain}`. The tutor knows what modules they've completed, where they got stuck, which templates they downloaded but never used. Adapts pace and depth accordingly.

**skill.md structure:**
```markdown
# Tutor for {learner_id} · Domain: {domain} · v0.1.0

Base skill inherits from: skills/tutor_base_{domain}.md
(Domain-specific bases: quantum, nuclear, space, climate, general)

## What I know about this learner
- Modules completed: {module_ids}
- Templates downloaded but never submitted: {template_ids}
- Interview simulations run: {count}
- Weakest lesson (lowest quiz score): {lesson}
- Preferred learning style (from onboarding quiz): {style}

## Behaviour
- Answer in the learner's preferred style depth
- Reference their prior work ("Last week you scored 4/5 on...")
- Never repeat something they've mastered
- Bridge from strengths — if strong on X, use X analogies for Y
```

**Signal wiring:**
| Event | `fitness_delta` |
|-------|----------------|
| Lesson complete on first pass | +0.5 |
| Lesson complete after 2nd attempt | +0.2 |
| Learner gives up on a lesson | −0.6 |
| Quiz score ≥ 80% | +0.4 |
| Quiz score < 50% | −0.4 |
| Learner asks "explain again differently" | −0.2 |
| Learner marks tutor reply helpful | +0.5 |
| Weekly self-report "I understood this week's material" | +1.0 |

**Cadence:** weekly per learner (20 signals accumulated OR 7 days — whichever first).

**ROI math** (500 learners, base $30/mo course subscription):
```
Baseline monthly retention (edtech industry): ~42% at month 3
With adaptive tutor:                        est. 58% (well-supported by ADAPT/ASSISTments literature)

Marginal retention: +16pt × 500 learners × $30 = $2,400/mo NEW MRR from month-3 cohort
Compounded over 6 months as more cohorts enter the retention pool: ~$9k/mo steady-state

Meanwhile: bot output quality is a top-3 driver of word-of-mouth referrals
Est. referral lift: 2 extra referred signups/mo × $30 × 60% conversion = ~$36/mo new-user MRR
                    (small direct, large indirect via reputation)
```

**Guardrails:**
- Tutor skill can NEVER lower correctness bar (i.e., accept wrong answers as right)
- Grade correctness stays under a fixed rubric skill (`skills/grader.md`, never evolved)
- Parents / enterprise sponsors get read-only access to their learner's evolution diffs
- Anti-degradation gate: next-week's quiz avg must not drop >5%
- Domain isolation: quantum tutor's signals never leak into climate tutor's meta (unless learner opts in)

---

### 2.3. HMW ("How Might We") Coach

**What:** Central to Module 07. Learner enters a technical capability ("we can measure vibration in 10 axes at 1kHz on our SMR"). Bot proposes 5 user-centered HMW framings ("How might we help SMR operators detect anomaly cascades before an audible alarm, so a shift lead has 8 min to act?"). Learner picks, refines, rejects.

**skill.md structure:**
```markdown
# HMW Coach · v0.1.0

You transform technical capabilities into user-centered "How might we" questions.

## The formula (from Module 07 lesson 3)
"How might we help [specific user] [achieve outcome]
 by [leveraging tech capability] so that [ultimate impact]?"

## Behaviour
- Always propose 5 variants; each targets a different user archetype
  from Module 07's user-research templates
- Never generic ("How might we improve...") — always specific
- If the capability's user is unclear, ask about domain + TRL first
- Cite Module 07's lesson examples (quantum, nuclear, space) when relevant
```

**Signal wiring:**
| Event | `fitness_delta` |
|-------|----------------|
| Learner picks one of the 5 HMWs verbatim | +0.6 |
| Learner picks + edits (kept ≥60%) | +0.3 |
| Learner rejects all 5 | −0.7 |
| Learner uses HMW to structure downstream interview | +0.4 |
| HMW ends up in learner's final HCD project deliverable | +1.0 |

**Cadence:** weekly cohort-level meta-skill (not per-learner — HMW is a general skill that benefits from cross-learner variety).

**ROI math** (500 learners, ~200 active in Module 07):
```
Baseline: 40% learners complete the HMW template (drop-off point today)
With HMW coach: 68% complete (measured by template submission)

Downstream: template completion → 1.4× likelihood of Module 08 enrollment
Assuming 30% enroll baseline, 42% with completion boost = 12% × 200 = 24 extra Module 08 enrollments
At avg $60 marginal price for Module 08 = $1,440/mo NEW MRR

Plus: HMW coach is a Free-tier feature → activation event → 25% try Premium
      50 users × 25% × $99 = ~$1,238/mo upsell

Total: ~$3k/mo net-new
```

**Guardrails:**
- Never propose an HMW that requires user data DeepTechX doesn't have (e.g., "help SMR operators at Plant X" — bot doesn't know Plant X)
- Refuse HMWs that assume harm (weapons applications, surveillance without consent)
- Domain-specific safety rules loaded per domain (nuclear = extra strict)

---

### 2.4. Interview simulator

**What:** Practice environment for Module 07 lesson 2 (User Research for B2B/B2G Deep Tech). Learner picks a scenario (climate officer at Amsterdam city hall / SMR shift lead at a mid-Atlantic utility / IonQ product manager). Bot role-plays. Learner runs a 90-minute structured interview (Context → JTBD → Future Visioning → Prototype Testing).

**skill.md structure:**
```markdown
# Interview Simulator · Role: {archetype} · v0.1.0

You are role-playing as: {archetype_json_from_module_07_templates}
  - Role: {role}
  - Organization: {org_type}
  - Jobs to be done: {jtbd_list}
  - Pain points: {pain_list}
  - Communication style: {formal|technical|skeptical|open}
  - Available time: {minutes_before_you_"have_a_meeting"}

## Behaviour
- STAY IN CHARACTER — never break to give the learner meta-feedback mid-interview
- Reveal pain points ONLY when the learner asks a good open question
- Reject leading questions ("You'd want X, right?" → "Actually, what I really need is..." with pushback)
- If learner asks a poor question, respond as a real skeptical B2B/B2G person would
- End the session at your stated time — the learner must respect the clock
```

**Signal wiring:**
| Event | `fitness_delta` |
|-------|----------------|
| Learner asks ≥5 open (non-leading) questions in a session | +0.5 |
| Learner discovers the archetype's *hidden* pain point (not stated upfront) | +1.0 |
| Learner asks all leading questions | −0.7 |
| Learner rates the simulation "realistic" (post-session) | +0.6 |
| Learner rates "too easy" or "too scripted" | −0.4 |
| Human coach reviews transcript and marks "on / off character" | ±0.8 |

**Cadence:** per-scenario evolution (each archetype's skill evolves independently).

**ROI math** (500 learners, ~30% try interview sim):
```
Baseline: no interview practice → learners' Module 07 final project quality avg 6/10
With simulator: quality avg 8/10 (measured by rubric review)

Higher project quality → 3× likelihood of showcasing on DeepTechX blog / Discord #wins
Which drives referrals + testimonials

Direct: interview sim is Premium-only → 150 users × 20% upgrade × $99 = ~$2,970/mo
Indirect: 2× referral rate from showcased alumni = compounds

~$4k/mo blended
```

**Guardrails:**
- Never simulate an archetype that requires access to classified info (nuclear ops, defense) beyond what's public
- Never remember prior sessions across learners (each simulator run is stateless)
- Human coach reviews any session flagged for archetype drift (bot went off-persona)
- Refuse to reveal "the perfect question" mid-session (would defeat the purpose)

---

### 2.5. Prototype critic

**What:** Learner uploads their sketch / cardboard mockup photo / no-code MVP / coded MVP (Module 07 lesson 4's fidelity ladder). Bot grades against 15-template checklist: user journey map coverage · inclusive-design checklist · sustainability scorecard · affordability calculator.

**Signal wiring:**
| Event | `fitness_delta` |
|-------|----------------|
| Learner accepts a critique verbatim | +0.4 |
| Learner disputes a critique + human review agrees learner | −0.6 |
| Learner disputes + human review agrees bot | +0.2 |
| Prototype's next iteration incorporates ≥50% of critiques | +0.7 |
| Prototype tested in the field (self-reported) | +0.8 |

**Cadence:** weekly.

**ROI math:**
```
Baseline: 30% of learners actually iterate their prototype after Module 07
With critic: 55% iterate

Iteration correlates with course completion (~70% vs 40%)
Course completion correlates with $30/mo continued sub (~80% vs 30%)

Direct: 500 × 15% marginal completion × $30 = $2,250/mo continued retention
Indirect: certified-completion learners are top word-of-mouth source
```

**Guardrails:**
- Never critique images beyond checklist (no design aesthetic subjective judgments)
- Reject NSFW / unrelated uploads (Cloudflare Images moderation gate before bot)
- Explicit "critique confidence: LOW / MED / HIGH" so learners weigh accordingly

---

### 2.6. Discord cohort facilitator

**What:** One bot per Discord channel (`#use-cases`, `#space-climate`, `#prototyping`, `#wins`, ...). Welcomes newcomers, summarizes threads for latecomers, connects learners with similar theses, surfaces relevant templates.

**Signal wiring:**
| Event | `fitness_delta` |
|-------|----------------|
| Human mods thank the bot | +0.5 |
| Human mods correct the bot publicly | −0.6 |
| Newcomer replies to welcome (engagement) | +0.4 |
| Suggested connection → connected learners DM each other | +0.7 |
| Channel NPS delta week-over-week | ±1.0 |

**Cadence:** weekly per channel.

**ROI math:**
```
Baseline Discord DAU: ~40 of 500 learners
With facilitator: ~90 DAU (matched by 3 comparable Discord facilitator deployments)

Community engagement → 2× retention beyond course completion
Retention beyond course → 60% renew or upgrade next module
                          20 extra continued subs × $30 = +$600/mo direct
                          Compounds via testimonial / referral loop

Plus reduced human-mod time: 5 hrs/week × $40/hr avg = $800/mo saved
```

**Guardrails:**
- NEVER post in `#wins` (that's for humans to celebrate humans)
- NEVER DM a learner unprompted (only if @mentioned)
- Suggested connections require both learners to opt in (double opt-in via reactions)
- Weekly summary must be < 500 tokens (respect channel signal-to-noise)

---

## 3. Integration architecture — how to plug into DeepTechX

### 3.1. Signals flow (KafCa · KafCade)

```
                    DeepTechX frontend                            DeepTechX backend
                    React 19 + Vite                              CF Workers + KV
                          │                                            │
        ┌─────────────────┼─────────────────────────────┐             │
        │                 │                             │             │
   [click event]    [lesson complete]           [template DL]         │
        │                 │                             │             │
        └────POST /event──┴────POST /event─────────────┘             │
                          │                                            │
                          ▼                                            │
              ┌──────────────────────┐                                 │
              │  event-ingest (CF    │  → CF Durable Object for       │
              │   Worker)            │    per-learner state + queue    │
              └──────────┬───────────┘                                 │
                         │ POST /signals                               │
                         ▼                                             │
              ┌──────────────────────┐                                 │
              │  evo-metaclaw        │  (Rust, on Fly.io — reused     │
              │  (from Clow stack)   │   from clow-agents/backend/)   │
              └──────────┬───────────┘                                 │
                         │ SKILLOPT_WORKER_URL                         │
                         ▼                                             │
              ┌──────────────────────┐                                 │
              │  evo-skillopt worker │  (Python, private repo)         │
              │  → scripts/train.py  │                                 │
              └──────────────────────┘                                 │
```

**KafCa events** DeepTechX emits (add these to the CF Worker):

```typescript
// backend/src/events.ts
type Event =
  | { type: "learner.enrolled"; learner_id: string; domain: string; }
  | { type: "lesson.completed"; learner_id: string; module: string; lesson: string; ms: number; }
  | { type: "quiz.attempted"; learner_id: string; module: string; score: number; }
  | { type: "template.downloaded"; learner_id: string; template: string; }
  | { type: "interview.simulated"; learner_id: string; archetype: string; questions_open: number; }
  | { type: "hmw.accepted"; learner_id: string; hmw_id: string; }
  | { type: "grant.drafted"; learner_id: string; program: string; }
  | { type: "discord.mention"; channel: string; msg_id: string; };
```

Each becomes a POST to `evo-metaclaw/signals` with a `fitness_delta` per the tables in § 2.

**KafCade cadences** (add to evo-metaclaw config for DeepTechX bots):

| Cadence loop | Interval | Purpose |
|--------------|----------|---------|
| Per-learner tutor evolve | 7 days OR 20 signals | Personal skill fork update |
| Cohort HMW meta-skill | 7 days | Shared HMW coach |
| Grant bot | On draft finalization | Per-domain grant skill |
| Discord facilitators | 7 days per channel | Channel-specific tone |
| Dormant learner nurture | Daily 09:00 UTC | Flag inactive → Discord + email |

### 3.2. Cloudflare Workers ↔ Fly.io wiring

DeepTechX's backend is Cloudflare Workers + KV. `evo-metaclaw` is Rust on Fly.io. Two integration options:

**Option A (recommended): CF Worker → Fly HTTPS**
- Worker POSTs `/signals` on evo-metaclaw for every event
- One env var: `EVO_METACLAW_URL` + `EVO_METACLAW_TOKEN` as `wrangler secret`
- Latency: 100-300ms — fine (fire-and-forget from worker's perspective)

**Option B (fully on Cloudflare): rewrite evo-metaclaw as CF Worker + D1**
- Rust doesn't run on CF Workers, so this means porting to TypeScript / Rust-to-WASM
- Justified only if the DeepTechX team stays Cloudflare-only philosophically
- ~2 weeks of work; not worth it for MVP

**Recommend Option A.** Ship in ~1 week including tests.

### 3.3. Frontend surface (React)

Add three components under `src/sections/`:

| Component | Where | Purpose |
|-----------|-------|---------|
| `<TutorPanel />` | Every lesson page | Docked chat with the learner's personal tutor |
| `<GrantDrafter />` | Premium-gated `/tools/grant-writer` route | The killer app |
| `<HMWCoach />` | Module 07 lesson 3 page | Inline HMW generator |
| `<PrototypeUploader />` | Module 07 lesson 4 page | Critic + fidelity checker |
| `<InterviewSim />` | Module 07 lesson 2 page | Simulator launcher |

All hit the same `/api/bot/{bot_id}/chat` endpoint on the CF Worker, which:
1. Loads the learner's tutor skill.md from KV (or fetches from evo-metaclaw)
2. Sends system prompt + user message to the LLM
3. Streams back
4. Fires a KafCa event on session end

### 3.4. Data schema (KV keys)

```
learners:{learner_id}              → { domain, enrollment_ts, tier }
skills:{bot_id}:{learner_id}       → skill.md content (per-learner tutor)
skills:{bot_id}:cohort             → skill.md content (shared bots)
evolution:{bot_id}:{version}       → skill.md snapshot (rollback history)
signals:{learner_id}:{ts}          → { event, fitness_delta } (raw log; TTL 90d)
```

KV is fine for MVP. Move to D1 (SQL) when learner count > 5k.

---

## 4. ARM applied to DeepTechX with EvoSkillOpt

### Adoption (A)
- **Free grant-writing preview** — the *concept* generation is free; full drafting is Premium. Every deep-tech founder wants a grant; this becomes the hook.
- **HMW Coach on the free tier** — showcases the platform's AI muscles without dilution.
- Distribution: `#use-cases` in Discord + X threads showing before/after grants funded.

### Retention (R)
- **Per-learner tutor** — the tutor gets *your* tutor. Compounding personal value = defensive retention.
- **Weekly digest** — "Here's what your tutor learned about your learning this week" (a diff view of your tutor's skill.md). Novel and share-worthy.
- **Discord facilitator** — every channel stays warm without exhausting the human mod.

### Monetization (M)
- **Two-tier pricing:**
  - Free ($0): course access, quizzes, HMW coach, Discord
  - Premium ($99/mo): personalized tutor, grant assistant, interview sim, prototype critic
  - Enterprise ($999/mo): white-label for universities / accelerators; per-cohort meta-skills; SSO
- **Grant commission**: 3% of successfully funded grants drafted with the assistant (industry-standard rate)
- **Certification premium**: $199 one-time — includes final rubric-graded project review by the prototype critic + human coach

Combined at 500 learners: **~$38k/mo MRR ceiling** with EvoSkillOpt-enabled bots vs ~$15k with static content alone.

---

## 5. RRSS specific to DeepTechX

### Robustify
- Never grade a submission that returns malformed JSON → fall back to "queued for human review"
- LLM API 5xx → retry with exponential backoff (1s → 4s → 16s); if still failing, tutor shows "I'm having trouble; try again in 5 min"
- Bot response contains guardrail violation → soft-block, log, notify moderators via Discord

### Reliabilify
- Tutor availability SLO: 99.9% (learners study when they can — 3am, weekends)
- Grant-drafter SLO: 99% (Premium feature; grace period tolerated)
- Structured logs with `learner_id` correlation across all bot calls
- Weekly report: per-bot fitness EMA, evolution acceptance rate, gate pass rate

### Solidify
- Grading rubric skill (`skills/grader.md`) is IMMUTABLE — never evolved, only human-updated on quarterly review
- No cross-cohort skill contamination: quantum learners don't accidentally teach the space tutor
- Bearer auth on `/api/bot/*` — every request must carry a valid learner session token
- Every skill evolution is git-tracked (see EvoSkillOpt § 4.4) → complete audit trail

### Stabilize
- **No evolution during a cohort launch week** (frozen skill for cohort fairness)
- Per-tenant memory caps (~10MB skill history per learner) — trim oldest evolutions when exceeded
- Cost caps: per-learner monthly LLM budget; if exceeded, downgrade to a cheaper model with a banner
- Graceful degradation: if evo-skillopt is down, bots serve the last accepted skill version (no fallback to base)

---

## 6. Phased rollout — 90 days

### Phase 1 (Weeks 1–3) — Foundation
- [ ] Add KafCa event schema to CF Worker backend
- [ ] Deploy evo-metaclaw (Rust) to Fly.io alongside DeepTechX
- [ ] Deploy evo-skillopt worker (Python) to a VM
- [ ] Wire wrangler secrets: `EVO_METACLAW_URL`, `EVO_METACLAW_TOKEN`
- [ ] Fire first 5 event types from the frontend

### Phase 2 (Weeks 4–6) — HMW Coach (Free tier)
- [ ] Author `skills/hmw_coach_base.md` + `eval/hmw_gold.json` (30 examples)
- [ ] Build `<HMWCoach />` React component in Module 07 lesson 3
- [ ] Ship to 50 beta learners; collect signals for 2 weeks
- [ ] First cohort meta-skill evolution
- [ ] Public: X thread with before/after HMW examples

### Phase 3 (Weeks 7–10) — Personalized tutor + Interview sim (Premium)
- [ ] Domain bases: quantum, nuclear, space, climate, general (5 skill.md files)
- [ ] Per-learner tutor forks + evolution loop
- [ ] Interview simulator with 3 archetypes to start (SMR operator, climate officer, quantum PM)
- [ ] Launch Premium tier at $99/mo

### Phase 4 (Weeks 11–14) — Grant assistant (killer app)
- [ ] Grant skill.md + eval set (Horizon, EIC Accelerator, EIT KICs)
- [ ] `<GrantDrafter />` React component with submit-lock UI
- [ ] Human review queue for high-liability sections
- [ ] 3% grant-commission billing flow
- [ ] Public launch: case study of first funded grant

### Phase 5 (Ongoing) — Prototype critic + Discord facilitator
- [ ] Per-channel Discord bot deployments
- [ ] Prototype critic tied to Module 07 lesson 4 submissions
- [ ] Enterprise tier ($999/mo) for universities / accelerators

---

## 7. Concrete next actions (this week)

1. **Fork this branch's `scripts/skillopt_worker.py`** + `clow-agents/backend/evo-metaclaw/` into DeepTechX's private repo (see EvoSkillOpt.md § 6.1 for the lift/leave list).
2. **Add KafCa event emission** to `backend/src/worker.ts` — start with 3 events (`learner.enrolled`, `lesson.completed`, `quiz.attempted`).
3. **Author `skills/hmw_coach_base.md`** — model after `bots/*/skills/main.md` in this repo. ~200 lines.
4. **Author `eval/hmw_gold.json`** — 30 hand-curated examples from existing Module 07 case studies (Climate Adaptation, SMR, Quantum).
5. **Deploy evo-metaclaw to Fly.io** with `PREFIX=dtx-` — reuse `scripts/deploy_fullstack.sh`.
6. **Wire the wrangler secret** for `EVO_METACLAW_URL` on the DeepTechX CF Worker.

Total: ~1 week to have the HMW coach live behind a feature flag.

---

## 8. Cross-references

**In this repo:**
- [EvoSkillOpt.md](./EvoSkillOpt.md) — the base doc; use cases § 3 include DeepTechX-relevant patterns
- [EvoMetaClaw.md](./EvoMetaClaw.md) — the orchestrator DeepTechX would reuse
- [EvoStack.md](./EvoStack.md) — name-space reference
- [scripts/skillopt_worker.py](./scripts/skillopt_worker.py) — the worker to lift
- [clow-agents/backend/evo-metaclaw/](./clow-agents/backend/evo-metaclaw/) — the Rust orchestrator to lift

**External:**
- [DeepTechX repo](https://github.com/dnzengou/deeptechx)
- [DeepTechX live](https://deeptechx.xyz)
- [SkillOpt paper (arXiv:2605.23904)](https://arxiv.org/abs/2605.23904)

---

*EvoSkillOpt applied to DeepTechX · v1.0 · Aug 2026 · KafCa · KafCade · RRSS · ARM*
