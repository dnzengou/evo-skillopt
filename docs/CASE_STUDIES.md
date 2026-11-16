# Case studies — four illustrations of the pattern in production

Four short case studies showing the evo-skillopt loop (and the broader
**EvoSkillOps** discipline it is part of) applied to real projects.
Each one is a self-contained read with a signal → cadence → outcome
shape so you can map it onto your own bot.

> **Naming note.** `evo-skillopt` (lowercase, kebab-case) is this
> repo — a service that evolves Markdown skill files. `EvoSkillOps`
> (CamelCase) is a sibling meta-development discipline authored by
> the same project owner — a command-driven toolkit (`Evo`, `Un`,
> `Vt`, `Pz`, `Tr`, …) for keeping any evolving repository healthy.
> The two compose: EvoSkillOps' `Vt`/`Pz` commands are what we used
> to ship evo-skillopt's own agent-SEO kit. Attribution:
> [`EVOSKILLOPS_SKILL.md`](https://github.com/dnzengou) v1.2.

---

## 1. kali-webOS — EvoSkillOps' `Vt` discipline, then `Pz` productized it

**Context.** A webOS-themed app surface shipped by the same owner.
When its visibility posture needed to catch up with the product
itself, the owner fired EvoSkillOps' `Vt` (Visibility) command
inline — JSON-LD, `llms.txt`, `agents.json`, security.txt — and
observed that the recipe was repeatable across projects.

**Move.** `Pz` (Productize). The `Vt` recipe became
`@aetherclaw/ai-seo` — a standalone npm package with a validator-first
posture: config in, files out, CI gate on, hard refusals for
manipulative tactics baked into the test suite rather than a style
guide.

**Outcome.** Any project can now consume the same posture with one
`npm i` and one config file. The policy doc and the validator stay
synchronized (Discipline **D-08 POLICY-IN-CODE**) because tests
assert refusal 1:1 with the documented refusals.

**Why it's useful here.** It's the **template** for how this repo
produced [`tools/agent-seo-kit/`](../tools/agent-seo-kit/). Same
pattern, Python+Bash instead of TypeScript. See case #2.

**References.**
- External: `@aetherclaw/ai-seo` on npm (not affiliated with this
  repo; linked for pattern reference only).
- `EVOSKILLOPS_SKILL.md` v1.2, § `Vt` + `Pz` + D-08.

---

## 2. evo-skillopt — the same pattern applied to this repo

**Context.** We were shipping an agent-SEO surface for this project
(AGENTS.md, llms.txt, agents.json, OpenAPI, JSON-LD) and noticed the
work generalized: any OSS project wanting to be agents-detectable
needs the same artifacts with the same shape.

**Move.** Mirror the `Vt` → `Pz` sequence from case #1.
[`tools/agent-seo-kit/`](../tools/agent-seo-kit/) is the result —
templates + a `scaffold.sh` renderer + a `verify.sh` gate.

**Outcome.** One command drops the full agent-SEO surface into a
fresh project:

```bash
PROJECT_NAME=my-tool PROJECT_OWNER=myuser PROJECT_REPO=my-tool \
  bash /path/to/evo-skillopt/tools/agent-seo-kit/scaffold.sh
bash .agent-seo-verify.sh
```

Verified live by scaffolding a throwaway target: nine files
rendered, agents.json parses as JSON, openapi.yaml as YAML, every
probe exits 0.

**What it costs.** Zero dependencies (pure shell + stdlib Python
for template substitution). No network calls. ~150 LOC in the kit
itself.

**Who should copy this.** Anyone shipping a developer product in
2026. The cost to add the surface is one command; the cost to leave
it off is an agent citation going to a competitor who did add it.

**References.** [`GTM.md`](../GTM.md) for the strategy,
[`docs/AI_SEO.md`](./AI_SEO.md) for the implementation notes.

---

## 3. Customer-support bot — the canonical "signal-rich" pattern

**Context.** A 500-ticket-per-week customer-support bot on a SaaS
product. CSAT surveys fire on every closed ticket; reopened tickets
generate a strong negative signal; resolution is binary.

**Move.** Wire the signal → fitness table from
[`USE_CASES.md § Pattern #1`](../USE_CASES.md#detailed-walkthrough--pattern-1-customer-support-triage--reply)
and trigger `POST /train` nightly at 03:00 UTC when total events ≥ 100.

**Signal wiring:**

| Event                                      | Δ    |
|--------------------------------------------|------|
| CSAT survey ≥ 4 / 5                        | +1.0 |
| CSAT survey ≤ 2 / 5                        | -1.5 |
| Ticket reopened within 24 h                | -0.8 |
| Ticket resolved & closed w/o reopen        | +0.5 |
| Escalated correctly (matched a rule)       |  0.0 |
| Escalated unnecessarily (reviewer flagged) | -0.3 |

**Outcome at six weeks.** Static baseline resolves 42 % of tickets
auto with CSAT 3.9. After six weekly-accepted evolutions the same
bot resolves 48 % with CSAT 4.2.

**ROI math.** (0.06 × 400 × 15 min / 60) × 20 workdays = 120 h/mo.
At $30/hr fully-loaded = **~$3.6k/mo saved**. Evolution cost:
single-digit dollars in tokens per run (see
[`/cost/estimate`](../.well-known/openapi.yaml)).

**Try it now.** [`examples/demo_evolve_bot.sh`](../examples/demo_evolve_bot.sh)
runs the full evolution flow (with a stubbed trainer) in under 15
seconds and shows you the gated diff.

**Guardrails** (what evolution can NEVER change):
- The escalation trigger regex list
- The output-format JSON schema
- The refund authorization pathway
- Any PII redaction rules

---

## 4. Docs / API assistant — the fastest-density signal source

**Context.** A docs-site-embedded bot answers "how do I do X?"
questions on a developer product. Thumbs-up/down on the answer,
follow-up query within 60 s, snippet-copied events — three signal
streams hitting every page view.

**Move.** Hourly cadence (signal density is 10×+ a support bot).
Reward criteria: never fabricate a function name; cite doc URLs
verbatim; prefer the shortest correct answer.

**Signal wiring:**

| Event                                      | Δ    |
|--------------------------------------------|------|
| 👍                                          | +1.0 |
| 👎                                          | -1.0 |
| Follow-up query within 60 s                | -0.5 |
| User copied the code snippet               | +0.8 |
| Time-to-successful-integration < 10 min    | +1.5 |

**Outcome shape.** Every doc question that lands is one deflected
support ticket. At any mid-size SaaS this pays back the whole
evo-skillopt deployment several times per month.

**Deeper read.** [`USE_CASES.md § Pattern #3`](../USE_CASES.md).

---

## Next cases to add (by signal density)

The cases above are ordered from "pattern template" to "fastest
feedback loop." These are the natural next ones to document:

| Pattern                             | Signal source                        | Why next |
|-------------------------------------|--------------------------------------|----------|
| Community moderator                 | Human-mod overrides on bot actions   | Dense, low-latency, high-trust |
| Async standup assistant             | Digest-response open + edit rate     | Weekly cadence, well-bounded |
| Adaptive tutor / study coach        | Exercise completion + drop-off       | Clear upsell path |
| Meeting-notes assistant             | Human-edit distance after generation | Operational — every org has this |

Contribute a case study by opening a PR that adds a section to this
file with the same structure (context, move, outcome, references).

---

## See also

- [`USE_CASES.md`](../USE_CASES.md) — 10 low-hanging-fruit patterns
  with ROI math
- [`SHOWCASE.md`](../SHOWCASE.md) — 8 drop-in integration recipes
- [`QUICKSTART.md`](../QUICKSTART.md) — 60-second onboarding
- [`GTM.md`](../GTM.md) — agent-era go-to-market playbook
- [`tools/agent-seo-kit/`](../tools/agent-seo-kit/) — extractable
  agent-SEO surface
