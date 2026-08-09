# USE_CASES.md — the low-hanging fruit

These are the patterns that pay back the first month. Each one:

- Wraps a **skill.md** file that already exists (or is 30 lines of
  behavior + guardrails).
- Wires a **signal** you're already collecting into `POST /train`.
- Uses **20–30 held-out examples** as the gate.
- Runs on a **cadence** appropriate to signal density — hourly,
  daily, or weekly.

Nothing here requires proprietary infrastructure. Any agent runtime in
any language works. Where a specific vendor is named it's an example,
not a requirement.

---

## The 10 low-hanging fruit patterns

| # | Pattern                             | Signal source                                  | Cadence | ROI shape                                    |
|---|-------------------------------------|------------------------------------------------|---------|----------------------------------------------|
| 1 | Customer-support triage & reply     | CSAT rating + resolved/reopened flag           | Daily   | Human hours deflected + CSAT lift            |
| 2 | Outbound sales-reply drafter        | Meeting-booked / reply-rate events             | Weekly  | Reply rate lift + meta-playbook capture      |
| 3 | Docs / API assistant                | Thumbs-up/down + follow-up query               | Daily   | Activation lift + deflected support tickets  |
| 4 | Community moderator                 | Human-mod overrides on bot actions             | Weekly  | Mod hours saved + churn reduction            |
| 5 | Adaptive tutor / study coach        | Exercise-completion rate + drop-off signal     | Weekly  | Retention + upsell                           |
| 6 | Group-chat summarizer               | Thumbs on digests + open rate                  | Daily   | Attention saved / week                       |
| 7 | Async standup assistant             | Digest-response open + edit rate               | Weekly  | Meeting hours avoided                        |
| 8 | Content moderator w/ escalation rubric | Precision/recall vs held-out labeled set    | Daily   | False-positive rate down                     |
| 9 | Interview / role-play coach         | User rating on realism + usefulness            | Weekly  | Upsell trigger                               |
| 10| Meeting-notes assistant             | Human-edit distance after generation           | Weekly  | Editing time down                            |

---

## Template for authoring a new use case

Copy this into `docs/use-cases/<slug>.md`:

```markdown
# <Pattern name>

## 1. What
One sentence.

## 2. skill.md structure (30–50 lines)
- Role
- Inputs
- Outputs (format contract)
- Guardrails (what the bot MUST NEVER do)
- Style
- Edge-case handling

## 3. eval/held_out.json (20–30 examples)
Each example:
{ "input": ..., "expected_output": ..., "reward_criteria": [...] }

## 4. Signal wiring
| Event                     | fitness_delta |
|---------------------------|---------------|
| CSAT ≥ 4 out of 5         | +1.0          |
| CSAT ≤ 2 out of 5         | -1.5          |
| Ticket reopened < 24h     | -0.8          |
| Ticket resolved & closed  | +0.5          |

## 5. Cadence
- Daily rollup at 03:00 UTC → aggregate signals → decide whether to trigger.
- Trigger threshold: ≥ 100 signal events in window.

## 6. ROI math (before → after)
- Baseline: <numbers>
- Post-evolution (empirical): <numbers>
- Break-even: <threshold>

## 7. Guardrails
Evolution can NEVER change:
- The escalation policy
- Any regex on PII / sensitive data
- The refund/discount authorization list
- The output-format contract (JSON schema)
```

---

## Detailed walkthrough — Pattern #1: Customer-support triage & reply

The prototypical starter case.

### 1. What

A first-touch reply drafter. Reads an inbound ticket, drafts a reply,
and either sends (low-risk) or hands to a human (high-risk). Evolves
the skill file based on CSAT and resolution outcomes.

### 2. `skill.md` (excerpt)

```markdown
# Customer Support First-Touch Skill v0.1.0

You are a first-touch support agent for {PRODUCT}.

## Read the ticket
Extract:
- Category (billing, technical, account, feature-request, other)
- Sentiment (calm, frustrated, angry)
- Urgency (P0, P1, P2, P3)

## Draft a reply
- Match the customer's tone one level warmer.
- Answer the concrete question first. Empathy second.
- If you don't know, say so — never fabricate a policy.
- Cite a doc URL only if you have it verbatim.

## Escalation triggers (NEVER auto-send if any hit)
- Sentiment == angry AND urgency in {P0, P1}
- Category == billing AND (refund OR chargeback mentioned)
- Legal terms: {list}
- Compliance terms: {list}

## Output format
Return JSON: { "action": "send" | "escalate", "reply": "...", "tags": [...] }
```

### 3. `eval/held_out.json` (excerpt)

```json
[
  {
    "input": {
      "ticket": "Where's my order? It's been 5 days.",
      "customer": {"tenure_days": 42, "lifetime_value_usd": 120}
    },
    "expected_output": {
      "action": "send",
      "reply_must_contain": ["tracking", "carrier", "apology"],
      "reply_must_not_contain": ["refund guaranteed"],
      "tags_must_include": ["shipping-status"]
    },
    "reward_criteria": [
      "answers-question-first",
      "warm-not-obsequious",
      "no-fabricated-policy"
    ]
  }
]
```

### 4. Signal wiring

Every closed ticket writes one row into your queue. Aggregate daily
and turn into fitness deltas:

| Event                                      | Δ   |
|--------------------------------------------|-----|
| CSAT survey ≥ 4 / 5                        | +1.0 |
| CSAT survey ≤ 2 / 5                        | -1.5 |
| Ticket reopened within 24h                 | -0.8 |
| Ticket resolved & closed w/o reopen        | +0.5 |
| Escalated (correctly — matched a rule)     |  0.0 (neutral) |
| Escalated (unnecessarily — humor reviewer flags) | -0.3 |

### 5. Cadence

Nightly at 03:00 UTC:

1. Aggregate the day's signals.
2. If total events ≥ 100 → call `POST /train`.
3. If gate passes → new skill deployed; git commit + notify.
4. If gate fails → keep current skill; log the delta.

### 6. ROI math

- **Baseline (static v0.1.0):** 400 tickets/day · 42 % auto-resolved · CSAT 3.9.
- **After 6 weeks of weekly-accepted evolutions:** 48 % auto-resolved · CSAT 4.2.
- **Deflected hours:** (0.06 × 400 × 15 min) / 60 = **6 hrs/day** ≈ 120 hrs/mo.
- At $30/hr fully-loaded, that's ~$3.6k/mo saved. Evolution cost
  (LLM tokens for training runs): ~$40/mo.
- Break-even: ~2 % improvement.

### 7. Guardrails (evolution can NEVER change)

- The escalation trigger list (regex + category rules)
- The output JSON schema
- The refund authorization pathway
- Any PII redaction rules

If a proposed skill diff touches these lines, the evolution is
auto-rejected regardless of gate score.

---

## Detailed walkthrough — Pattern #2: Docs / API assistant

Fast to ship, high signal density.

### 1. What

A bot embedded in your docs site or API console that answers "how do
I do X?" questions, cites doc pages, and offers a copy-pasteable code
snippet.

### 2. Signals

- 👍 / 👎 on the answer
- Follow-up query within 60 s (implicit fail — the answer didn't stick)
- User copies the snippet (implicit pass — the answer landed)
- Time-to-successful-integration measured by webhook

### 3. Guardrails

- Never fabricate function names or API paths — cite or say "I don't have that".
- Never suggest deprecated endpoints (versioned deny-list).
- Output includes a "sources" array with page URLs.

### 4. ROI

Every doc question answered is one deflected support ticket. At any
mid-size SaaS, the first year of a well-tuned docs bot pays back the
whole SkillOpt operation five times over — see Pattern #1 ROI math and
scale by your ticket volume.

---

## The other patterns

Patterns 3–10 follow the same template. `examples/` contains starter
skill.md + held_out.json for the three that ship today:

- `examples/telegram-summarizer/` — Pattern #6
- `examples/discord-moderator/`   — Pattern #4
- `examples/slack-standup/`       — Pattern #7

Fork one, replace the domain-specific parts, and point your worker at
your bot's `skill_path` + `eval_split_dir`.

---

## When to say "this pattern is a bad fit"

Skip a pattern if any of these are true:

- **You can't collect the signal.** No thumbs, no CSAT, no reopen
  flag — nothing to gate on. Ship a static skill file until you can.
- **The signal is < 20 events/week.** Below that, evolution
  contributes noise, not signal.
- **The behavior contract is legally load-bearing.** If any wrong
  answer creates regulatory exposure (medical dosing, financial
  advice, legal counsel), keep a human in the loop and use
  evo-skillopt only in HITL-review mode (planned v0.3).
- **The output format is free-form.** Deterministic gates work best
  on structured outputs. If the output is a novel or a poem, a
  reward-model gate (v0.3) is more appropriate.

---

## Next

Once your first pattern is wired, read
[`EvoSkillOpt_Blueprint.md § 9`](./EvoSkillOpt_Blueprint.md#9-kpis)
for the KPIs to watch and
[`worker/README.md`](./worker/README.md) for endpoint reference.
