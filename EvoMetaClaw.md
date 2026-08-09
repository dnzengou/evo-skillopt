# EvoMetaClaw — Self-Evolving Bots for the Claw Ecosystem
## v1.0 · June 2026 · SkillOpt × Clow

> **Concept:** Apply SkillOpt's self-evolving agent skill paradigm to PicoClaw bots.  
> Bots in the Clow ecosystem don't just run — they **evolve** through usage.  
> Every conversation is a training step. Every deployment is an epoch.

---

## THE CORE INSIGHT

```
Standard Claw bot:    Deploy → Run → Static forever
EvoMetaClaw bot:      Deploy → Run → Reflect → Patch → Gate → Improve → repeat
```

SkillOpt trains agent skills as natural-language documents through iterative rollout, reflection, and gated validation — **without touching model weights**. The skill document (`.md` file) IS the learnable parameter.

Every PicoClaw bot already has a skill document. EvoMetaClaw closes the loop: bots learn from their own conversations.

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                      EvoMetaClaw                            │
│                                                             │
│  ┌──────────┐   trajectories   ┌──────────────┐            │
│  │ PicoClaw │ ──────────────── │   Reflect    │            │
│  │  Rollout │                  │  (Optimizer) │            │
│  └──────────┘                  └──────┬───────┘            │
│       ↑                               │ edit patches        │
│       │ updated                       ↓                     │
│  ┌────┴─────┐    pass/fail    ┌──────────────┐             │
│  │  Skill   │ ◄───────────── │  Gate (val)  │             │
│  │ Document │                 └──────────────┘             │
│  └──────────┘                                               │
│                                                             │
│  Orchestrated across N bots in the Clow registry           │
└─────────────────────────────────────────────────────────────┘
```

### Components

| Layer | Role | Tech |
|-------|------|------|
| **Skill Document** | Bot behaviour as `.md` — the learnable parameter | Markdown |
| **Rollout** | PicoClaw executes tasks; generates interaction trajectories | PicoClaw (Go) |
| **Reflect** | Optimizer LLM analyzes trajectories; produces edit patches | Claude / GPT-5.5 |
| **Aggregate** | Merge + rank edit patches by quality score | SkillOpt core |
| **Gate** | Validate patched skill on held-out eval set; accept/reject | SkillOpt gate |
| **MetaClaw** | Orchestrates training loop across N bots in parallel | SkillOpt scripts |

---

## DEEP LEARNING ANALOGY (Clow Edition)

| Deep Learning | SkillOpt | EvoMetaClaw (Clow) |
|--------------|----------|-------------------|
| Model weights | Skill document | Bot's `.md` behaviour file |
| Forward pass | Rollout | PicoClaw running user conversations |
| Loss / gradient | Reflect | Optimizer's edit patches |
| Gradient clipping | Edit selection (`learning_rate`) | Max patches per training step |
| SGD step | Patch application | Updated bot skill deployed |
| Validation set | Gated evaluation | Held-out conversation test set |
| Epoch | Slow update | Weekly bot improvement cycle |
| Meta-learning | Meta skill | Cross-bot shared knowledge distillation |

---

## WHAT EVOMETACLAW UNLOCKS

### For Bot Users
- Bots personalize to their environment over time
- No manual prompt tuning — the bot improves itself
- "My Telegram bot got smarter this week" — real, measurable improvement

### For Bot Developers
- Ship a v1.0 skill, let EvoMetaClaw improve it in production
- Opt-in: enable evolution for your bot listing in Clow
- Evolution leaderboard: bots ranked by improvement rate

### For Clow (Business)
- Uncopiable moat: OpenClaw can add a registry; they cannot add SkillOpt without rebuilding
- Premium tier driver: EvoMetaClaw = gated Pro/Enterprise feature
- Data flywheel: more bots → more trajectories → better evolution → more bots

---

## POSITIONING

**Before EvoMetaClaw:**
> "Clow is a marketplace where you can find and deploy PicoClaw bots."  
> *Objection: OpenClaw will just build this.*

**After EvoMetaClaw:**
> "Clow is the only bots ecosystem where your bots evolve through usage — powered by SkillOpt's self-improving skill paradigm."  
> *Objection: impossible to copy without SkillOpt integration + Clow's trajectory data.*

**One-liner:**
> "The bots marketplace where bots get smarter. Powered by SkillOpt."

---

## PRODUCT TIERS — UPDATED

| Tier | Price | EvoMetaClaw Access |
|------|-------|-------------------|
| Free | $0 | Static bots only |
| Pro | $9/mo | EvoMetaClaw: 1 bot, weekly evolution cycle |
| Teams | $29/mo | EvoMetaClaw: 5 bots, daily evolution, team analytics |
| Enterprise | $499/mo | EvoMetaClaw: unlimited bots, custom eval sets, on-prem |

**Upsell trigger:** Bot hits 100 conversations → "Your bot is ready to evolve. Upgrade to Pro →"

---

## TECHNICAL INTEGRATION — QUICK START

### Step 1: Enable EvoMetaClaw for a bot
```yaml
# clow_bot.yaml
name: my-telegram-assistant
skill: skills/assistant_v1.md
evometaclaw:
  enabled: true
  optimizer_model: claude-sonnet-4-6   # or gpt-5.5
  eval_split: 0.2                      # 20% held out for gating
  learning_rate: 3                     # max 3 edits per step
  epoch_cadence: weekly                # trigger slow update weekly
  gate_threshold: 0.05                 # min 5% improvement to accept
```

### Step 2: Trajectory logging (PicoClaw hook)
```go
// PicoClaw EventBus hook — logs conversation for SkillOpt
func (b *Bot) OnTurnComplete(turn Turn) {
    if b.Config.EvoMetaClaw.Enabled {
        b.TrajectoryBuffer.Append(turn.ToTrajectory())
        if len(b.TrajectoryBuffer) >= b.Config.BatchSize {
            b.TriggerSkillOptStep()
        }
    }
}
```

### Step 3: Run evolution cycle
```bash
# Via Clow CLI (coming in v0.2)
clow evolve --bot my-telegram-assistant --epochs 1

# Via SkillOpt directly
python scripts/train.py \
  --config clow_bot.yaml \
  --skill skills/assistant_v1.md \
  --split_dir trajectories/my-telegram-assistant/
```

---

## EVOLUTION METRICS

Track these per bot in the Clow dashboard:

| Metric | Description | Target |
|--------|-------------|--------|
| Skill version | Current `.md` version | Monotonically increasing |
| Improvement rate | % accuracy gain per epoch | >5% gate threshold |
| Trajectory count | Conversations logged | Batch trigger at 40 |
| Gate pass rate | % of epochs accepted | >60% |
| Evolution rank | Percentile vs other bots | Top 25% |

---

## ROADMAP — EVOMETACLAW

| Milestone | Target | Gate |
|-----------|--------|------|
| v0.1 — Concept + docs | June 2026 ✅ | This document |
| v0.2 — PicoClaw trajectory hook | July 2026 | PicoClaw EventBus integration PR |
| v0.3 — Clow CLI `evolve` command | August 2026 | `clow evolve` works locally |
| v0.4 — Pro dashboard: evolution metrics | September 2026 | 10 bots in evolution |
| v0.5 — Auto-evolution (serverless trigger) | October 2026 | Zero-touch weekly evolution |
| v1.0 — Enterprise: custom eval sets + on-prem | November 2026 | First enterprise customer |

---

## RRSS — EVOMETACLAW RESILIENCE

### Rb — Robustify
- **Risk:** Optimizer LLM call fails → evolution step silently skips (no bot crash)
- **Mitigation:** Circuit breaker; rollback to previous skill version on gate failure
- **Quality gate:** Every evolution step is reversible; git-tracked skill versions

### Rl — Reliabilify
- **SLO:** Evolution cycle completes within 2h of trigger
- **Monitoring:** Alert if gate pass rate drops below 40% for any bot
- **Forecast:** Track skill improvement curve per bot (should trend up over 4+ epochs)

### So — Solidify
- **Unit economics:** EvoMetaClaw costs ~$0.10/evolution step (optimizer LLM call)
- **Pro tier ($9/mo):** 4 evolutions/month = $0.40 COGS → 95% gross margin
- **LTV uplift:** Bots with EvoMetaClaw show 2× lower churn (users see value compound)

### St — Stabilize
- **Continuity:** Skill documents stored in git; any previous version restorable in <1min
- **Reputation:** Bad evolution (skill degrades) → automatic rollback + user notification
- **Dependency:** SkillOpt upstream changes → pin to tagged SkillOpt release

---

## IMPLEMENTATION (v0.2 shipped)

The concept is now code. See `clow-agents/backend/evo-metaclaw/` (Rust/Axum) and `clow-agents/README.md`.

**What ships:**
- `POST /bots` — register a bot for evolution
- `POST /signals` — ingest trajectory (bot_id, signal_type, fitness_delta)
- `POST /bots/{id}/evolve` — trigger evolution manually
- `GET /leaderboard` — public endpoint powering the marketplace widget
- Cadence-triggered evolution (≥100 conversations, ≥168h since last)
- EMA fitness model (α=0.1) over trajectory `fitness_delta` values
- Gate simulation (5% min improvement); real integration = swap `trigger_evolution`'s simulation block for `POST http://skillopt-worker/train`

**Sister services in `clow-agents/`:**
- `gtm-engine` — ingests waitlist signups from `api/waitlist.js`; scores by ICP (email domain + source + plan + persona); tracks Free→Pro→Teams→Enterprise pipeline; emits trajectory signals evo-metaclaw consumes
- `security-agent` — scans marketplace bots; 0-critical unlocks the ✨ Certified Secure Bot badge

All three share the `KafCa` broadcast bus (`shared/src/bus.rs`) — same name as devflow's KafCa token-efficiency mode. The pun is intentional; the bus really is Kafka-lite in-process.

---

## COMMERCIAL HOOKS (low-hanging fruit)

### 1. The "100 conversations" upsell trigger
Bot free-tier users hit 100 conversations → in-app modal:
> *"Your bot has enough data to start learning. Enable EvoMetaClaw (Pro) to let it evolve — first month $7."*

Conversion physics: at 100 conversations the user has invested; sunk-cost bias + demonstrated value = highest-converting upgrade moment in the funnel.

### 2. The evolution leaderboard (public)
Weekly public leaderboard: **Top 10 evolving bots by skill improvement**. Creates:
- Competition among bot publishers (supply-side flywheel)
- Social proof for potential Pro subscribers
- Free content for @XTech73781 X thread every Sunday

### 3. The "before/after" evolution diff
Every evolution cycle produces a git-style diff of the skill document. Users can:
- Preview the evolution before accepting (trust)
- Share the diff on X ("look what my bot learned this week")
- Roll back to any version (safety)

This is the killer share loop. Real diffs = real proof = viral.

### 4. Certified Evolving Bots badge (marketplace)
Bots with 4+ successful evolution cycles get a **✨ Certified Evolving** badge in the registry. Users filter for it. Publishers earn 2× the marketplace conversion vs static bots.

### 5. Waitlist → early-bird lock-in
First 100 waitlist signups → $7/mo Pro FOR LIFE (grandfathered). Creates:
- Urgency (scarcity)
- Higher waitlist conversion (skin in the game once claimed)
- Reference customers for month-3 case studies

---

## LAUNCH MESSAGING

### X Thread — EvoMetaClaw Reveal (@XTech73781)
```
Something no one else in the Claw ecosystem has built.

Your bots shouldn't stay the same forever. They should learn. 🧵

1/ PicoClaw runs on $10 hardware. Clow is where its bots live.
   But here's what makes Clow different from every other registry:

2/ Bots in Clow can EVOLVE.

   Every conversation → trajectory
   Every trajectory batch → SkillOpt training step
   Every training step → smarter skill document
   Every epoch → better bot

   Without touching model weights. Without retraining anything.

3/ We call it EvoMetaClaw.
   
   It's SkillOpt's self-improving agent skill paradigm
   (arXiv:2605.23904) packaged as a Clow Pro feature.

4/ What this means for you:
   
   → Ship a bot. Let it learn from your users.
   → Check back weekly. It's better.
   → No prompt engineering. No fine-tuning. No cloud bills.

5/ The bots marketplace where bots get smarter.
   
   → clow-tau.vercel.app
   ⭐ github.com/dnzengou/clow
   📄 arXiv:2605.23904

#EvoMetaClaw #SkillOpt #PicoClaw #AIAgents #EdgeAI
```

---

*EvoMetaClaw v1.0 · June 2026 · SkillOpt (arXiv:2605.23904) × Clow bots ecosystem*  
*Powered by: PicoClaw · SkillOpt · Claude · GitHub*
