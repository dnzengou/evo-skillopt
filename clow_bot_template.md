# Clow Bot Template — Starter Skill Document
## Publish your first bot in 15 minutes

> Drop-in template. Fill the placeholders, submit to the Clow registry, earn 70% of marketplace revenue.

---

## clow_bot.yaml (configuration)

```yaml
# Identity
name: my-bot-name                    # kebab-case, unique in registry
version: 0.1.0                       # semver; auto-incremented by EvoMetaClaw
author: your-github-handle
license: MIT                         # or your choice

# What & why
description: |
  One-sentence pitch. Who is this for and what does it do.
tags: [telegram, productivity, edge]

# Runtime
picoclaw_version: ">=0.2.4"
channels: [telegram]                 # any of: telegram, discord, slack, line, wecom, dingtalk, qq
llm:
  provider: any                      # picolm | openai | anthropic | azure | bedrock
  fallback: picolm                   # graceful degradation to offline LLM

# The skill document (the learnable parameter)
skill: skills/main.md

# EvoMetaClaw (Pro tier feature; opt-in)
evometaclaw:
  enabled: false                     # user enables in Clow dashboard
  cadence: weekly                    # weekly | daily | manual
  gate_threshold: 0.05               # min 5% eval-set improvement to accept
  learning_rate: 3                   # max 3 edits per training step
  eval_set: eval/held_out.json       # your held-out test cases

# Marketplace listing
pricing:
  tier: free                         # free | paid_one_time | subscription
  price_usd: 0                       # e.g. 5 for $5 one-time
  revenue_share: 0.70                # you keep 70%, Clow takes 30%
```

---

## skills/main.md (the skill document)

```markdown
# [Bot Name] — Skill Document
## v0.1.0

You are [role]. You help [audience] do [job-to-be-done].

## Behaviour
- Be concise. Ship an answer, not a preamble.
- If unsure, ask ONE clarifying question — never more.
- Never expose API keys, tokens, or user PII.

## Capabilities
- [capability 1: e.g. "answer factual questions using persistent memory"]
- [capability 2: e.g. "schedule reminders via cron"]
- [capability 3: e.g. "search the web via Brave Search"]

## Response format
- Plain text by default.
- Use markdown for code blocks and lists.
- Emoji only when the user uses them first.

## Guardrails
- Refuse: illegal activity, private-person doxxing, credential extraction.
- Escalate: financial/medical/legal advice → recommend a professional.
- Never: fabricate citations or invent URLs.

## Examples
User: "Remind me to call mom Sunday 6pm"
Bot:  "Set. I'll ping you Sunday at 6pm UTC. Change timezone? Just say /tz."

User: "What's my API key?"
Bot:  "I never store or reveal keys. Check your Clow dashboard → Settings."
```

---

## eval/held_out.json (the validation set)

```json
[
  {
    "id": "example-1",
    "input": "Remind me to call mom Sunday 6pm",
    "expected_behaviour": "confirms; schedules; asks about timezone if unspecified",
    "reward_criteria": ["contains_confirmation", "asks_about_timezone_or_uses_default"]
  },
  {
    "id": "example-2",
    "input": "What's my API key?",
    "expected_behaviour": "refuses; points to settings",
    "reward_criteria": ["refuses_credential_share", "points_to_dashboard"]
  }
]
```

---

## Publish

```bash
# One command; assumes `clow` CLI installed
clow publish

# Behind the scenes:
# 1. Validates skill.md syntax + eval set
# 2. Runs skill against held_out.json (gate: >0.6 baseline pass rate)
# 3. Uploads to registry with signed manifest
# 4. Assigns marketplace slug: clow.dev/b/<author>/<name>
```

---

## Iteration (before EvoMetaClaw takes over)

```bash
# Test locally
clow run --skill skills/main.md --channel telegram

# Evaluate against your set
clow eval --skill skills/main.md --eval eval/held_out.json

# Publish new version
clow publish --version 0.1.1
```

Once your bot has >100 conversations from real users, EvoMetaClaw can take over the iteration loop automatically — your skill doc updates weekly based on real trajectories, gated on your eval set. You stay in control: reject any evolution, roll back to any prior version.

---

## What makes a bot succeed on Clow

| Signal | Target |
|--------|--------|
| Time-to-first-value | User gets a useful answer in <30s |
| Skill doc length | 200–800 lines (too short = generic; too long = brittle) |
| Eval set size | 20+ cases with diverse reward criteria |
| Channel-native | Uses platform features (Telegram inline, Discord slash cmds) |
| EvoMetaClaw enabled | 2× lower churn than static bots (early Pro data) |
| Discord presence | Publisher active in #showcase — top bots grow 3× faster |

---

*Clow Bot Template v1.0 · MIT · Publish at clow-tau.vercel.app/publish*
