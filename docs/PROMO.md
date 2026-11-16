# Promo copy — ready to ship

Launch-ready text for the channels that move a developer product in
2026. Copy-paste, don't massage — the writing is tuned per channel.

> **House rules.** No overclaiming. No fabricated numbers. No fake
> benchmarks. If a claim appears below, it's either from a runnable
> command or from a case study in [`CASE_STUDIES.md`](./CASE_STUDIES.md).
> That's the EvoSkillOps `Vt` discipline — see its §"Hard refusals."

---

## One-sentence taglines (pick the one that fits the context)

- **For a developer audience** — "Train your agent's Markdown skill
  file like a neural network — epochs, batches, validation gates,
  without touching model weights."
- **For an ops / platform audience** — "Every skill version is a git
  commit. Every evolution is gated on your eval set. Every rollback
  is one `POST`."
- **For a GTM / exec audience** — "Your support bot gets better
  every Monday. Costs single-digit dollars in LLM tokens. Never
  needs a model retrain."
- **For an AI-SEO audience** — "Ships with the agent-SEO kit that
  made it agents-detectable from day one. Copy-paste into any
  project."

---

## X / Twitter thread (3 posts)

> **1/3** Shipped evo-skillopt — a text-space skill optimizer for
> production LLM agents.
>
> Train your bot's Markdown skill file like a neural network: epochs,
> validation gates, git-tracked history. Zero weight changes. Any
> provider.
>
> 60 s to the aha moment:
> `bash examples/demo_evolve_bot.sh`
>
> 🧵

> **2/3** What's inside the demo:
>
> 1. Enqueues a `/train` job
> 2. Background worker drains it against a held-out eval set
> 3. Gate decides accept/reject on measurable improvement
> 4. Accepted skill = new git commit in a per-bot repo
> 5. `/bots/{id}/diff` shows what moved
>
> One accepted diff per evolution. Rollback: `POST /bots/{id}/rollback`.

> **3/3** Also ships an extractable agent-SEO kit at `tools/agent-seo-kit/`.
>
> One command drops `llms.txt`, `AGENTS.md`, `agents.json`,
> `openapi.yaml`, `robots.txt`, JSON-LD into any OSS project.
>
> Because in 2026 your docs are read by LLMs too.
>
> MIT. github.com/dnzengou/evo-skillopt

---

## LinkedIn post (longer-form)

> **Shipped: evo-skillopt — a disciplined training loop for the
> Markdown skill files your agents already run on.**
>
> Every production LLM agent I've seen in 2026 ships a v1.0 system
> prompt and iterates with ad-hoc tweaks nobody tracks. That's not
> training — that's accumulated regret.
>
> `evo-skillopt` treats the skill file as the learnable parameter
> and borrows the shape of neural-network training around it:
>
> • **Signals in** — CSAT, thumbs-up, resolved/reopened, meeting-booked
> • **Eval set as gate** — a new skill must beat the previous one on
>   held-out examples
> • **Git-tracked history** — every accepted diff is a commit; every
>   rollback is one HTTP call
> • **Zero model-weight changes** — works with OpenAI, Anthropic,
>   Google, Azure, local
>
> Case study in the repo: a 500-ticket/week support bot moves from
> 42 % auto-resolve @ CSAT 3.9 to 48 % @ CSAT 4.2 in six weekly
> evolutions. That's ~120 hours per month of deflected human review.
>
> The project also ships an **extractable agent-SEO kit** — the
> agents.md, llms.txt, agents.json, OpenAPI, JSON-LD surface that
> makes it discoverable by both humans and LLM crawlers. One
> command drops it into any OSS project. Because by 2026 your docs
> are a developer product's first sales page, and half the readers
> are not human.
>
> MIT. Try the demo in 60 seconds:
> github.com/dnzengou/evo-skillopt

---

## Show HN

**Title:** `Show HN: evo-skillopt – train your agent's skill file like a neural network`

**First comment (post-submit):**

> Author here. Quick framing for the comments:
>
> This productizes the SkillOpt algorithm (arXiv:2605.23904, MIT) as
> a small HTTP service. The service wraps the upstream trainer, adds
> a versioned skill store with git-tracked history, a Prometheus
> metrics endpoint, a SQLite async job queue, and a bunch of
> operational hygiene (SIGTERM drain, output-root retention, cost
> estimator) you'd otherwise build yourself.
>
> **What it is not.** A new training algorithm (SkillOpt is the
> upstream). A new LLM (works with whatever you have). An eval
> framework alone (evals are the gate, not the point).
>
> Two things that are probably worth the top of the thread:
>
> 1. The `examples/demo_evolve_bot.sh` script runs the full flow in
> under 15 seconds with no LLM credentials — it stubs the trainer so
> you can see the mechanics (enqueue → gate → store → diff → rollback)
> before you burn tokens on a real evolution.
>
> 2. The `tools/agent-seo-kit/` is an extractable deliverable — the
> agents.md, llms.txt, agents.json, OpenAPI, robots.txt, JSON-LD
> surface factored into a reusable kit. `scaffold.sh` into any
> project, `verify.sh` to gate in CI. It exists because the same
> recipe applied twice (first on an external project, then here)
> and I wanted the third application to be a command instead of a
> cherry-pick.
>
> Happy to dig into specifics — RRSS gate, cascade evaluator, ARM
> fitness, or the "agents are now a buyer" GTM angle.

---

## Reddit (r/MachineLearning or r/LocalLLaMA)

**Title:** `evo-skillopt — closes the loop between production signals and the SkillOpt training loop`

**Body:**

> Been quietly building this for a couple of months. It's a small
> Python HTTP service that takes the SkillOpt algorithm
> (arXiv:2605.23904, MIT) and wraps it as something you can run in
> production: versioned skill files, async job queue, Prometheus
> metrics, cost estimator, rollback endpoint.
>
> The thesis is boring in the best way: every production LLM agent
> is one Markdown skill file and a prompt-engineer who tweaks it on
> Fridays. This treats that file as the learnable parameter and
> runs a disciplined rollout → reflect → gate → accept-or-rollback
> loop against signals you're already collecting (CSAT, thumbs,
> reopened tickets, etc.).
>
> No weight changes. Any provider. Single-digit dollars per
> evolution in tokens.
>
> 60-second demo: `bash examples/demo_evolve_bot.sh`
>
> Would love feedback especially from folks running support bots or
> moderation bots at scale — the signal-wiring section of
> `USE_CASES.md` is where I'd most like to be pushed back on.
>
> MIT. github.com/dnzengou/evo-skillopt

---

## Email signature line

> `evo-skillopt` — train your agent's skill file like a neural
> network. ​— ​github.com/dnzengou/evo-skillopt

---

## Launch-day checklist

- [ ] Pin the project to your GitHub profile.
- [ ] Publish the `gh-pages` site (Settings → Pages → `gh-pages/root`).
- [ ] Post the X thread.
- [ ] Post the LinkedIn.
- [ ] Submit Show HN after local peak (US-east morning typically).
- [ ] Reddit post after HN has 10+ points so the Reddit thread can link to it.
- [ ] Add the project to your email signature for a week.
- [ ] Share in one developer-focused Discord/Slack (don't spray).

Don't buy ads. Don't use hashtag spam. Don't fabricate numbers or
testimonials. (That's the `Vt` discipline's hard-refusals list.)

---

## What NOT to say

For the record, these are claims you cannot make honestly today —
mentioned so a future draft doesn't drift into them:

- ❌ "Beats GPT-5 on <benchmark>" — this is a training-loop wrapper,
  not a model.
- ❌ "Used by <Big Co>" — there is no "used by" to claim yet.
- ❌ "N × cheaper than fine-tuning" — depends entirely on the
  comparison; use the `/cost/estimate` endpoint for your workload.
- ❌ Fake stars, fake forks, paid-for-placement without disclosure.
- ❌ "Industry-standard" / "best-in-class" — superlatives without
  evidence are LLM slop.

If you find yourself tempted, re-read
[`EVOSKILLOPS_SKILL.md` § `Vt` hard refusals](https://github.com/dnzengou).
