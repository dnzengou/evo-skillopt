"""Cascade evaluator — score a *pipeline* of skills as one composite.

Where the vanilla worker evolves a single ``skill.md`` at a time, a
cascade treats an ordered list of skills as one behavior contract:

    [filter_pii.md, classify_intent.md, draft_reply.md]

Each stage is evaluated independently against the same held-out set,
then aggregated to a cascade score. Gate acceptance requires the
aggregate to meet a threshold *and* every stage to meet its own floor —
so a fluent draft cannot silently mask a broken PII filter upstream.

Pure module: takes per-stage scores as input and returns aggregate +
gate outcome. The worker owns the subprocess orchestration that produces
those per-stage scores.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

Aggregation = Literal["mean", "min", "product", "weighted_mean"]


@dataclass(frozen=True)
class StageResult:
    """One stage's per-run outcome inside a cascade."""

    name: str
    score: float
    weight: float = 1.0
    passed: bool = True


@dataclass(frozen=True)
class CascadeResult:
    """Aggregate outcome across every stage of one cascade run."""

    stages: tuple[StageResult, ...]
    aggregate: float
    aggregation: Aggregation
    gate_passed: bool
    reason: str


def aggregate_scores(
    stages: Sequence[StageResult],
    aggregation: Aggregation = "mean",
) -> float:
    """Reduce per-stage scores to a single cascade score.

    * ``mean``           — arithmetic mean of stage scores.
    * ``min``            — worst stage. Use when every stage matters equally
                           and you want the weakest link to dominate.
    * ``product``        — multiplicative, treating each score as a
                           conditional-success probability. Punishes any
                           stage below 1.0.
    * ``weighted_mean``  — sum(w_i * s_i) / sum(w_i). Use when some stages
                           carry more decision weight than others.
    """
    if not stages:
        return 0.0
    if aggregation == "mean":
        return sum(s.score for s in stages) / len(stages)
    if aggregation == "min":
        return min(s.score for s in stages)
    if aggregation == "product":
        p = 1.0
        for s in stages:
            p *= max(0.0, min(1.0, s.score))
        return p
    if aggregation == "weighted_mean":
        total_w = sum(s.weight for s in stages)
        if total_w <= 0:
            return 0.0
        return sum(s.weight * s.score for s in stages) / total_w
    raise ValueError(f"unknown cascade aggregation {aggregation!r}")


def evaluate_cascade(
    stages: Sequence[StageResult],
    *,
    aggregation: Aggregation = "mean",
    aggregate_threshold: float = 0.0,
    stage_floor: float = 0.0,
) -> CascadeResult:
    """Aggregate + gate a cascade run.

    Passes iff every stage's score is at or above ``stage_floor`` **and**
    the aggregate is at or above ``aggregate_threshold``.
    """
    if not stages:
        return CascadeResult(
            stages=(),
            aggregate=0.0,
            aggregation=aggregation,
            gate_passed=False,
            reason="cascade has no stages",
        )
    weak = [s for s in stages if s.score < stage_floor]
    if weak:
        names = ", ".join(f"{s.name}={s.score:.3f}" for s in weak)
        return CascadeResult(
            stages=tuple(stages),
            aggregate=aggregate_scores(stages, aggregation),
            aggregation=aggregation,
            gate_passed=False,
            reason=f"stage floor {stage_floor:.3f} not met: {names}",
        )
    agg = aggregate_scores(stages, aggregation)
    if agg < aggregate_threshold:
        return CascadeResult(
            stages=tuple(stages),
            aggregate=agg,
            aggregation=aggregation,
            gate_passed=False,
            reason=(
                f"aggregate {agg:.3f} below threshold {aggregate_threshold:.3f} "
                f"({aggregation})"
            ),
        )
    return CascadeResult(
        stages=tuple(stages),
        aggregate=agg,
        aggregation=aggregation,
        gate_passed=True,
        reason=f"aggregate {agg:.3f} ≥ {aggregate_threshold:.3f} ({aggregation})",
    )
