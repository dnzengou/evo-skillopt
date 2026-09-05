"""ARM signal bucketing — group production signals by lifecycle stage.

Production bots emit heterogeneous signals: a thumbs-up on a first
reply, a subscription renewal, an upsell click, a churn cancellation.
Weighting all of them equally when computing a bot's fitness score
loses information about *which lifecycle stage* the bot is failing at.

ARM buckets each signal into one of three stages:

* **A**\\ cquire — first-contact conversion (booking, sign-up, trial start,
  first reply positive rating).
* **R**\\ etain — ongoing satisfaction and re-engagement (CSAT, thumbs-up
  on later replies, follow-up questions answered, ticket resolved).
* **M**\\ onetize — revenue-adjacent events (upsell, renewal, plan upgrade,
  in-app purchase attributable to the interaction).

Composite fitness is the weighted sum of per-bucket rates. Rebalancing
weights (e.g. from acquire-heavy at launch to retain-heavy at scale)
lets a single bot's fitness formula follow the product lifecycle
without touching per-signal delta values.

Pure module: takes typed signal events, returns a bucket breakdown.
No I/O, no dependency on the vendored trainer.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

Bucket = Literal["acquire", "retain", "monetize"]

BUCKETS: tuple[Bucket, ...] = ("acquire", "retain", "monetize")

DEFAULT_WEIGHTS: Mapping[Bucket, float] = {
    "acquire": 1 / 3,
    "retain": 1 / 3,
    "monetize": 1 / 3,
}


@dataclass(frozen=True)
class Signal:
    """One production event tagged with its lifecycle bucket."""

    bucket: Bucket
    delta: float  # positive = fitness reward, negative = penalty
    kind: str = ""  # optional human label, e.g. "csat_5", "trial_started"


@dataclass(frozen=True)
class BucketSummary:
    """Rolled-up totals for one lifecycle bucket."""

    bucket: Bucket
    count: int
    sum_delta: float
    mean_delta: float


@dataclass(frozen=True)
class ARMFitness:
    """Aggregate bot fitness broken down by lifecycle bucket."""

    per_bucket: tuple[BucketSummary, ...]
    composite: float
    weights: Mapping[Bucket, float]


def summarize(signals: Iterable[Signal]) -> tuple[BucketSummary, ...]:
    """Roll signals up into per-bucket count / sum / mean triples.

    Every bucket appears in the output even if it received no signals —
    downstream weighting is stable across time windows that happen to
    have no acquire (or no monetize) events.
    """
    totals: dict[Bucket, list[float]] = {b: [] for b in BUCKETS}
    for s in signals:
        if s.bucket not in totals:
            raise ValueError(f"unknown ARM bucket {s.bucket!r}")
        totals[s.bucket].append(float(s.delta))
    return tuple(
        BucketSummary(
            bucket=b,
            count=len(vals),
            sum_delta=sum(vals),
            mean_delta=(sum(vals) / len(vals)) if vals else 0.0,
        )
        for b, vals in totals.items()
    )


def _normalize_weights(weights: Mapping[Bucket, float]) -> Mapping[Bucket, float]:
    missing = set(BUCKETS) - weights.keys()
    if missing:
        raise ValueError(f"ARM weights missing buckets: {sorted(missing)}")
    total = sum(float(weights[b]) for b in BUCKETS)
    if total <= 0:
        raise ValueError("ARM weights must sum to > 0")
    return {b: float(weights[b]) / total for b in BUCKETS}


def compute_fitness(
    signals: Iterable[Signal],
    *,
    weights: Mapping[Bucket, float] | None = None,
) -> ARMFitness:
    """Reduce a stream of signals to one composite fitness score.

    The composite is the weighted mean of per-bucket **mean deltas** —
    not sums — so a chatty acquire funnel does not drown a quieter
    monetize signal. Empty buckets contribute 0.

    Rebalance weights over the product lifecycle:
      * launch:   acquire=0.6, retain=0.3, monetize=0.1
      * growth:   acquire=0.3, retain=0.5, monetize=0.2
      * mature:   acquire=0.1, retain=0.4, monetize=0.5
    """
    ws = _normalize_weights(weights or DEFAULT_WEIGHTS)
    summaries = summarize(signals)
    composite = sum(ws[s.bucket] * s.mean_delta for s in summaries)
    return ARMFitness(per_bucket=summaries, composite=composite, weights=ws)
