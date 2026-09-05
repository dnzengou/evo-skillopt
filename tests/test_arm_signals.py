"""Tests for the ARM (Acquire / Retain / Monetize) signal bucketing."""
from __future__ import annotations

import pytest
from arm_signals import (
    BUCKETS,
    Signal,
    compute_fitness,
    summarize,
)


def _sig(bucket, delta, kind=""):
    return Signal(bucket=bucket, delta=delta, kind=kind)


class TestSummarize:
    def test_all_buckets_present_even_when_empty(self):
        result = summarize([_sig("acquire", 1.0)])
        buckets = {s.bucket for s in result}
        assert buckets == set(BUCKETS)

    def test_counts_and_sums(self):
        signals = [
            _sig("acquire", 1.0),
            _sig("acquire", 0.5),
            _sig("retain", -0.2),
            _sig("monetize", 5.0),
        ]
        summaries = {s.bucket: s for s in summarize(signals)}
        assert summaries["acquire"].count == 2
        assert summaries["acquire"].sum_delta == pytest.approx(1.5)
        assert summaries["acquire"].mean_delta == pytest.approx(0.75)
        assert summaries["retain"].count == 1
        assert summaries["retain"].mean_delta == pytest.approx(-0.2)
        assert summaries["monetize"].mean_delta == pytest.approx(5.0)

    def test_empty_bucket_has_zero_mean(self):
        summaries = {s.bucket: s for s in summarize([_sig("acquire", 1.0)])}
        assert summaries["monetize"].count == 0
        assert summaries["monetize"].mean_delta == 0.0

    def test_unknown_bucket_raises(self):
        with pytest.raises(ValueError):
            summarize([Signal(bucket="engage", delta=1.0)])  # type: ignore[arg-type]


class TestComputeFitness:
    def test_default_weights_are_thirds(self):
        # Equal per-bucket means → composite equals that mean
        signals = [
            _sig("acquire", 0.6),
            _sig("retain", 0.6),
            _sig("monetize", 0.6),
        ]
        fit = compute_fitness(signals)
        assert fit.composite == pytest.approx(0.6)

    def test_launch_weighting_favors_acquire(self):
        signals = [
            _sig("acquire", 1.0),
            _sig("retain", 0.0),
            _sig("monetize", 0.0),
        ]
        fit = compute_fitness(
            signals,
            weights={"acquire": 0.6, "retain": 0.3, "monetize": 0.1},
        )
        assert fit.composite == pytest.approx(0.6)

    def test_mean_not_sum_used_per_bucket(self):
        # Chatty acquire funnel with 100 events shouldn't outweigh one big
        # monetize event when the mean deltas are equal.
        signals = [_sig("acquire", 0.5) for _ in range(100)] + [_sig("monetize", 0.5)]
        fit = compute_fitness(
            signals,
            weights={"acquire": 0.5, "retain": 0.0, "monetize": 0.5},
        )
        assert fit.composite == pytest.approx(0.5)

    def test_negative_signals_penalize(self):
        signals = [_sig("retain", -1.0), _sig("acquire", 1.0), _sig("monetize", 0.0)]
        fit = compute_fitness(signals)
        # (1.0 + (-1.0) + 0.0) / 3
        assert fit.composite == pytest.approx(0.0)

    def test_missing_weight_raises(self):
        with pytest.raises(ValueError):
            compute_fitness([_sig("acquire", 1.0)], weights={"acquire": 1.0})  # type: ignore[arg-type]

    def test_zero_weights_raises(self):
        with pytest.raises(ValueError):
            compute_fitness(
                [_sig("acquire", 1.0)],
                weights={"acquire": 0.0, "retain": 0.0, "monetize": 0.0},
            )

    def test_weights_are_renormalized(self):
        # 60/30/10 already sums to 100 — but 6/3/1 (which sums to 10)
        # must give the same composite once renormalized.
        signals = [_sig("acquire", 1.0), _sig("retain", 0.0), _sig("monetize", 0.0)]
        a = compute_fitness(signals, weights={"acquire": 0.6, "retain": 0.3, "monetize": 0.1})
        b = compute_fitness(signals, weights={"acquire": 6, "retain": 3, "monetize": 1})
        assert a.composite == pytest.approx(b.composite)

    def test_empty_input_returns_zero(self):
        fit = compute_fitness([])
        assert fit.composite == 0.0
        assert all(s.count == 0 for s in fit.per_bucket)
