# Glossary

## Core terms

**Skill file** · A Markdown document that specifies what a bot does,
how, and what it must never do. The learnable parameter of
`evo-skillopt`.

**Rollout** · One pass of the current skill file through the
held-out evaluation set, producing trajectories.

**Reflection** · An LLM pass that reads a rollout and proposes
edits to the skill file.

**Gate** · A hard validation check. A proposed skill diff must
improve the eval-set score by at least `gate_min_improvement`
to be accepted.

**Evolution** · One full training cycle: rollout → reflect →
aggregate → select → update → gate. May result in either an
accepted new skill version or a rejected one (rollback).

**Bot** · A named unit of behavior identified by `bot_id`
(convention: `owner/name`). One skill file, one eval set,
one training history.

**Held-out evaluation set** · A JSON file of `{input,
expected_output, reward_criteria}` examples the bot must handle
correctly. Also called `eval/held_out.json` by convention.

**Signal** · An external event (CSAT rating, thumbs-up, ticket
reopened, meeting booked, etc.) that adjusts the bot's fitness
score and eventually triggers an evolution.

**Cadence** · How often evolutions are triggered — typically
hourly, daily, or weekly. Depends on signal density.

## HTTP protocol terms

**`WORKER_TOKEN`** · Bearer token required on `POST /train`
when set. Dev mode (no auth) when unset.

**`OUTPUT_ROOT`** · Directory under which every training run
writes its outputs. Default `outputs/evo`.

**`TRAIN_SCRIPT`** · Path to the SkillOpt `scripts/train.py`
entrypoint. Default resolved relative to the worker.

**`gate_score_delta`** · The measured improvement of the new
skill over the previous one on the eval set. Positive = better.

**`next_version`** · The SemVer-bumped skill version, returned
only when `gate_passed` is true. Otherwise the previous version
is returned unchanged.

## Operational terms

**Fitness delta** · The unitless per-signal contribution to a
bot's rolling fitness score. Configured per use case (see
[`../USE_CASES.md`](../USE_CASES.md)).

**Rollback** · The act of not accepting a proposed skill diff.
Silent (no version bump); logged for post-hoc analysis.

**RRSS** · A four-dimension resilience rubric used in the
[`../EvoSkillOpt_Blueprint.md § 12`](../EvoSkillOpt_Blueprint.md#12-resilience-checklist):
Robustify, Reliabilify, Solidify, Stabilize.

**RRSS gate** · A validation gate that scores candidate skills on all
four RRSS axes, then accepts only when every configured axis clears
its floor AND the weighted-mean composite improves over the previous
accepted version. Implemented in `worker/rrss_gate.py`. Opt-in via the
`rrss` block on `POST /train` — see
[`../configs/examples/rrss_gate.yaml`](../configs/examples/rrss_gate.yaml).

**Cascade** · An ordered list of skills treated as one behavior
contract — e.g. `[filter_pii.md, classify_intent.md, draft_reply.md]`.
Each stage is scored independently against the same held-out set;
gate acceptance requires the aggregate to meet a threshold *and*
every stage to meet its own floor. Implemented in `worker/cascade.py`
and exposed at `POST /train/cascade`.

**ARM** · A three-bucket classifier for production signals —
**A**\ cquire, **R**\ etain, **M**\ onetize — that reduces
heterogeneous events (thumbs-up, renewal, cancellation, upsell)
to one composite fitness score. Per-bucket weights let a single
fitness formula follow the product lifecycle (acquire-heavy at
launch → retain-heavy at scale → monetize-heavy at maturity).
Implemented in `worker/arm_signals.py` and exposed at
`POST /fitness/arm`.

## Related upstream terms (from the SkillOpt paper)

**Aggregate** · Consolidation of multiple reflections into a
coherent proposed edit set.

**Select** · Picking the highest-signal reflection subset for
the update step.

**Reward criteria** · The rubric under which a reflection or
gate evaluation scores a trajectory.

## Not defined here

- Specific vendor product names (see [`../TRADEMARKS.md`](../TRADEMARKS.md))
- Enterprise pricing constructs — this is the OSS repo
