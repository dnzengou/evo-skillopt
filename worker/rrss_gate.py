"""RRSS gate — resilience-scored validation gate.

Extension of the vendored ``skillopt.evaluation.gate`` module. Where the
upstream gate projects a candidate to a single (hard|soft|mixed) scalar,
the RRSS gate scores across four resilience axes named in
``EvoSkillOpt_Blueprint.md § 12``:

* **R**\\ obustify   — worst-quartile score on the eval set (adversarial floor)
* **R**\\ eliabilify — consistency of repeated rollouts (1 - CV, clamped)
* **S**\\ olidify    — coverage across labeled categories (min-per-category score)
* **S**\\ tabilize   — non-regression: items that used to pass and still pass

Each axis is a scalar in ``[0, 1]``. The composite RRSS score is the
weighted mean; defaults are equal-weighted. Callers may override.

Pure module: no I/O, no dependency on the vendored trainer. Wired into
the worker via a ``gate_metric: "rrss"`` mode.
"""
from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class RRSSComponents:
    """Four-axis resilience decomposition of a candidate skill.

    All fields are in ``[0, 1]``; ``composite`` is the weighted mean.
    """

    robustify: float
    reliabilify: float
    solidify: float
    stabilize: float
    composite: float


DEFAULT_WEIGHTS: Mapping[str, float] = {
    "robustify": 0.25,
    "reliabilify": 0.25,
    "solidify": 0.25,
    "stabilize": 0.25,
}


def _clamp01(x: float) -> float:
    if math.isnan(x):
        return 0.0
    return max(0.0, min(1.0, float(x)))


def robustify_score(per_item_scores: Sequence[float]) -> float:
    """Worst-quartile mean — the *floor* the skill guarantees on hard items.

    Empty input returns 0.0. Uses the lower quartile (25th percentile
    boundary) — the mean of items with score at or below the p25 threshold.
    A single-item input returns that item's score.
    """
    if not per_item_scores:
        return 0.0
    if len(per_item_scores) == 1:
        return _clamp01(per_item_scores[0])
    ordered = sorted(_clamp01(s) for s in per_item_scores)
    k = max(1, len(ordered) // 4)
    return sum(ordered[:k]) / k


def reliabilify_score(repeated_scores: Sequence[float]) -> float:
    """Consistency across N repeated rollouts, ``1 - CV`` clamped to ``[0, 1]``.

    A skill that always returns the same score gets 1.0. A skill whose
    per-run scores swing wildly relative to their mean approaches 0.
    Empty or single-item input returns 1.0 (no evidence of drift).
    """
    if len(repeated_scores) < 2:
        return 1.0
    mean = statistics.fmean(_clamp01(s) for s in repeated_scores)
    if mean <= 0:
        return 0.0
    stdev = statistics.pstdev(_clamp01(s) for s in repeated_scores)
    return _clamp01(1.0 - (stdev / mean))


def solidify_score(scores_by_category: Mapping[str, Sequence[float]]) -> float:
    """Coverage floor — the *worst* per-category mean.

    A skill that scores 0.9 on FAQ but 0.1 on billing gets a low solidify.
    Empty input returns 0.0.
    """
    if not scores_by_category:
        return 0.0
    means = [
        statistics.fmean(_clamp01(s) for s in items) if items else 0.0
        for items in scores_by_category.values()
    ]
    return min(means) if means else 0.0


def stabilize_score(
    prev_pass: Iterable[bool],
    cand_pass: Iterable[bool],
) -> float:
    """Non-regression rate — items that used to pass and still pass.

    ``prev_pass[i]`` and ``cand_pass[i]`` are aligned per-item outcomes
    for the same eval set. Returns 1.0 when nothing previously passed
    (nothing to protect), else ``|previously-passing ∩ still-passing| /
    |previously-passing|``.
    """
    prev = list(prev_pass)
    cand = list(cand_pass)
    if len(prev) != len(cand):
        raise ValueError(
            f"stabilize_score: length mismatch prev={len(prev)} cand={len(cand)}"
        )
    passing_before = sum(1 for p in prev if p)
    if passing_before == 0:
        return 1.0
    still_passing = sum(1 for p, c in zip(prev, cand, strict=True) if p and c)
    return still_passing / passing_before


def compute_rrss(
    per_item_scores: Sequence[float],
    *,
    repeated_scores: Sequence[float] = (),
    scores_by_category: Mapping[str, Sequence[float]] | None = None,
    prev_pass: Sequence[bool] = (),
    cand_pass: Sequence[bool] = (),
    weights: Mapping[str, float] | None = None,
) -> RRSSComponents:
    """Compute the four RRSS axes and their weighted composite.

    Any axis whose input is empty falls back to a safe default
    (``robustify=0``, ``reliabilify=1``, ``solidify=0``,
    ``stabilize=1``) so partial signals still produce a usable score
    — callers that want to *require* an axis should filter empties
    before calling.
    """
    weights = _normalize_weights(weights or DEFAULT_WEIGHTS)
    r = robustify_score(per_item_scores)
    rel = reliabilify_score(repeated_scores)
    sol = solidify_score(scores_by_category or {})
    stab = stabilize_score(prev_pass, cand_pass)
    composite = (
        weights["robustify"] * r
        + weights["reliabilify"] * rel
        + weights["solidify"] * sol
        + weights["stabilize"] * stab
    )
    return RRSSComponents(
        robustify=r,
        reliabilify=rel,
        solidify=sol,
        stabilize=stab,
        composite=_clamp01(composite),
    )


def _normalize_weights(weights: Mapping[str, float]) -> Mapping[str, float]:
    missing = {"robustify", "reliabilify", "solidify", "stabilize"} - weights.keys()
    if missing:
        raise ValueError(f"rrss weights missing axes: {sorted(missing)}")
    total = sum(float(weights[k]) for k in ("robustify", "reliabilify", "solidify", "stabilize"))
    if total <= 0:
        raise ValueError("rrss weights must sum to > 0")
    return {k: float(weights[k]) / total for k in ("robustify", "reliabilify", "solidify", "stabilize")}


@dataclass(frozen=True)
class RRSSGateDecision:
    """Whether the candidate cleared the gate, and by how much."""

    passed: bool
    components: RRSSComponents
    delta: float
    reason: str


def rrss_gate(
    candidate: RRSSComponents,
    previous_composite: float,
    *,
    min_improvement: float = 0.0,
    axis_floors: Mapping[str, float] | None = None,
) -> RRSSGateDecision:
    """Accept the candidate iff every axis clears its floor AND the
    composite improves by at least ``min_improvement`` over the previous
    accepted skill.

    ``axis_floors`` is optional: if provided, each named axis must meet
    or exceed its floor. Unnamed axes have no floor. An empty mapping
    is treated as no floors.
    """
    floors = dict(axis_floors) if axis_floors else {}
    axis_values = {
        "robustify": candidate.robustify,
        "reliabilify": candidate.reliabilify,
        "solidify": candidate.solidify,
        "stabilize": candidate.stabilize,
    }
    for axis, floor in floors.items():
        if axis not in axis_values:
            raise ValueError(f"unknown rrss axis {axis!r}")
        if axis_values[axis] < floor:
            return RRSSGateDecision(
                passed=False,
                components=candidate,
                delta=candidate.composite - previous_composite,
                reason=f"{axis} {axis_values[axis]:.3f} below floor {floor:.3f}",
            )
    delta = candidate.composite - previous_composite
    if delta < min_improvement:
        return RRSSGateDecision(
            passed=False,
            components=candidate,
            delta=delta,
            reason=(
                f"composite {candidate.composite:.3f} vs prev "
                f"{previous_composite:.3f} = {delta:+.3f} < min "
                f"{min_improvement:+.3f}"
            ),
        )
    return RRSSGateDecision(
        passed=True,
        components=candidate,
        delta=delta,
        reason=(
            f"composite {candidate.composite:.3f} vs prev "
            f"{previous_composite:.3f} = {delta:+.3f} ≥ min "
            f"{min_improvement:+.3f}"
        ),
    )
