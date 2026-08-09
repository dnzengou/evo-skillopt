# Concept — the core idea in depth

## The mental model

Traditional ML training:

```
data → gradients → weights → checkpoint
```

`evo-skillopt` training:

```
signals → reflections → skill.md → git commit
```

**The skill file is the model.** Not a proxy for it — literally the
thing being trained. It's plain Markdown, human-readable, and every
version is a git commit.

## Why this works

Modern LLMs are competent at almost anything they're told to be
competent at. The gap between v1 and v2 of a production AI product is
almost never a smarter base model — it's a sharper set of instructions
about what to do in the messy real world.

`evo-skillopt` treats those instructions as the parameter surface.
Every production interaction is a training example. Every held-out
eval is a validation batch. The optimizer emits a proposed diff to
your skill file. A gate decides whether to accept it.

## The training loop

Each epoch runs the SkillOpt reference algorithm:

1. **Rollout** — the current skill file drives your bot through the
   held-out evaluation set. Trajectories are logged.
2. **Reflect** — a second LLM pass reviews the trajectories and
   proposes textual improvements to the skill.
3. **Aggregate** — reflections are consolidated to remove noise.
4. **Select** — the highest-signal reflections are turned into
   concrete edits.
5. **Update** — the skill file is patched.
6. **Gate** — the patched skill is re-run against the eval set. If
   its score exceeds the previous by ≥ `gate_min_improvement`, it's
   accepted. Otherwise, roll back.

The full loop lives upstream (see the [SkillOpt paper](https://arxiv.org/abs/2605.23904)).
`evo-skillopt` wraps it in an HTTP boundary so any agent runtime,
in any language, can trigger it.

## What SkillOpt gives us

- The algorithm (rollout · reflect · aggregate · select · update · gate)
- Reference benchmarks (SearchQA, ALFWorld, DocVQA, LiveMath, OfficeQA, SpreadsheetBench)
- LLM backend abstractions
- Config-driven runs

## What `evo-skillopt` adds

- **HTTP boundary.** SkillOpt is a Python library; we expose it as
  a service.
- **Bearer auth + subprocess isolation.** Multi-tenant use of a single
  worker.
- **Version bump semantics.** SemVer per bot.
- **Container-first deployment.** Docker multi-stage, non-root, tini,
  healthcheck, Compose for self-host, `fly.toml` for cloud.
- **Attribution + license clarity.** MIT vendored MIT — clean.
- **A blueprint.** Living roadmap from v0.1 to v1.0.

## The economic case

The unit economics are set by:

- Number of skill training runs per week per bot
- Tokens consumed per training run
- Provider $ per token

For most bots, an evolution costs single-digit dollars in tokens and
saves an order of magnitude more in human hours per week
([`USE_CASES.md`](../USE_CASES.md) walks through the math per pattern).
The break-even is a 1–3 % improvement per training run — well within
the noise floor of even a small held-out set.

## The moat

The code is open source. The moat that accumulates inside a company
using `evo-skillopt` is:

1. **The eval set** — the collected, curated, categorized examples
   the gate runs against. These are proprietary and grow every week.
2. **The skill history** — a git log of every accepted evolution, why
   it was accepted, and what it changed. Institutional knowledge in
   diff-viewer form.
3. **The signal wiring** — the mapping from real product events to
   fitness deltas. Fine-tuning this over months is where the highest
   leverage sits.

None of the above is code. All of it is text and configuration. That
means it's portable, auditable, and (importantly) not held hostage to
any specific vendor.

## Comparable tools and how this differs

| Tool                 | What it does                                       | What it doesn't                                    |
|----------------------|----------------------------------------------------|----------------------------------------------------|
| Prompt observability | Logs prompts / responses, shows LLM usage          | Doesn't propose or apply edits                     |
| Eval frameworks      | Runs a fixed set of tests against a prompt         | Doesn't close the loop with production signals    |
| Fine-tuning services | Trains model weights on your data                 | Expensive, opaque, provider-locked, hallucination-prone if data is thin |
| Prompt versioning    | Git-like history for prompts                       | You still write the edits by hand                  |
| `evo-skillopt`       | Closes the loop: signals → training → gated update | Requires a well-defined skill + eval set to start  |

## When *not* to use this

- **You have no signal.** No thumbs, no CSAT, no gate. Static prompts win.
- **You have < 20 signal events per week.** Below that, noise dominates.
- **The behavior is legally load-bearing** and you can't or won't
  keep a human in the loop for changes.
- **Free-form creative output.** Deterministic gates struggle here;
  wait for reward-model gates (v0.3).

## Further reading

- The paper: [arXiv:2605.23904](https://arxiv.org/abs/2605.23904)
- Upstream docs: [microsoft.github.io/SkillOpt](https://microsoft.github.io/SkillOpt)
- Use-cases catalog: [`../USE_CASES.md`](../USE_CASES.md)
- Blueprint & roadmap: [`../EvoSkillOpt_Blueprint.md`](../EvoSkillOpt_Blueprint.md)
- Glossary: [`GLOSSARY.md`](./GLOSSARY.md)
