"""Tests for the cascade evaluator — multi-stage skill pipeline gating."""
from __future__ import annotations

import pytest
from cascade import StageResult, aggregate_scores, evaluate_cascade


def _stages(*scores_and_weights):
    return [
        StageResult(name=f"stage{i}", score=s, weight=w)
        for i, (s, w) in enumerate(scores_and_weights)
    ]


class TestAggregate:
    def test_mean(self):
        stages = _stages((0.9, 1), (0.7, 1), (0.8, 1))
        assert aggregate_scores(stages, "mean") == pytest.approx(0.8)

    def test_min(self):
        stages = _stages((0.9, 1), (0.4, 1), (0.8, 1))
        assert aggregate_scores(stages, "min") == pytest.approx(0.4)

    def test_product(self):
        stages = _stages((0.9, 1), (0.5, 1), (0.8, 1))
        assert aggregate_scores(stages, "product") == pytest.approx(0.36)

    def test_product_clamps_out_of_range(self):
        stages = _stages((1.5, 1), (0.5, 1))  # 1.5 clamped to 1.0
        assert aggregate_scores(stages, "product") == pytest.approx(0.5)

    def test_weighted_mean(self):
        # (0.9*1 + 0.5*3) / (1+3) = (0.9 + 1.5) / 4 = 0.6
        stages = _stages((0.9, 1), (0.5, 3))
        assert aggregate_scores(stages, "weighted_mean") == pytest.approx(0.6)

    def test_weighted_mean_zero_weights_returns_zero(self):
        stages = _stages((0.9, 0), (0.5, 0))
        assert aggregate_scores(stages, "weighted_mean") == 0.0

    def test_empty_stages_returns_zero(self):
        assert aggregate_scores([], "mean") == 0.0

    def test_unknown_aggregation_raises(self):
        with pytest.raises(ValueError):
            aggregate_scores(_stages((0.5, 1)), "median")  # type: ignore[arg-type]


class TestEvaluateCascade:
    def test_all_stages_pass_meets_threshold(self):
        stages = _stages((0.9, 1), (0.85, 1), (0.95, 1))
        result = evaluate_cascade(
            stages,
            aggregation="mean",
            aggregate_threshold=0.8,
            stage_floor=0.7,
        )
        assert result.gate_passed is True
        assert result.aggregate == pytest.approx(0.9)

    def test_stage_floor_blocks_even_when_aggregate_would_pass(self):
        # Aggregate 0.66 with a 0.1 stage — a mean-only gate at threshold 0.5
        # would let this through; the stage_floor stops it.
        stages = _stages((0.95, 1), (0.95, 1), (0.10, 1))
        result = evaluate_cascade(
            stages,
            aggregation="mean",
            aggregate_threshold=0.5,
            stage_floor=0.5,
        )
        assert result.gate_passed is False
        assert "stage2" in result.reason

    def test_aggregate_below_threshold(self):
        stages = _stages((0.5, 1), (0.6, 1), (0.4, 1))
        result = evaluate_cascade(
            stages,
            aggregation="mean",
            aggregate_threshold=0.8,
            stage_floor=0.3,
        )
        assert result.gate_passed is False
        assert result.aggregate == pytest.approx(0.5)
        assert "below threshold" in result.reason

    def test_empty_cascade_rejected(self):
        result = evaluate_cascade([])
        assert result.gate_passed is False
        assert result.aggregate == 0.0
        assert "no stages" in result.reason

    def test_min_aggregation_is_conservative(self):
        stages = _stages((0.95, 1), (0.60, 1))
        result = evaluate_cascade(
            stages,
            aggregation="min",
            aggregate_threshold=0.7,
            stage_floor=0.5,
        )
        # min = 0.60, below 0.7 → reject even though stage floor is met
        assert result.gate_passed is False

    def test_weighted_mean_respects_weights(self):
        # Draft stage weighted 3x — its 0.6 dominates the 0.95 filter
        stages = [
            StageResult(name="filter", score=0.95, weight=1.0),
            StageResult(name="draft", score=0.60, weight=3.0),
        ]
        result = evaluate_cascade(
            stages,
            aggregation="weighted_mean",
            aggregate_threshold=0.75,
            stage_floor=0.5,
        )
        # weighted = (0.95 + 1.80) / 4 = 0.6875 → below 0.75
        assert result.gate_passed is False
        assert result.aggregate == pytest.approx(0.6875)
