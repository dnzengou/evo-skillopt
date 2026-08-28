"""Tests for the RRSS gate — resilience-scored candidate acceptance."""
from __future__ import annotations

import math

import pytest
from rrss_gate import (
    RRSSComponents,
    compute_rrss,
    reliabilify_score,
    robustify_score,
    rrss_gate,
    solidify_score,
    stabilize_score,
)


class TestRobustify:
    def test_empty_scores(self):
        assert robustify_score([]) == 0.0

    def test_single_item(self):
        assert robustify_score([0.7]) == pytest.approx(0.7)

    def test_worst_quartile(self):
        # 8 items → k = 8 // 4 = 2 → mean of two lowest = (0.1 + 0.2) / 2
        scores = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.2, 0.1]
        assert robustify_score(scores) == pytest.approx(0.15)

    def test_clamps_out_of_range(self):
        # Negative values clamped to 0, > 1 clamped to 1
        assert robustify_score([-0.5, 2.0, 0.5, 0.5]) == pytest.approx(0.0)


class TestReliabilify:
    def test_empty_and_single_are_perfect(self):
        assert reliabilify_score([]) == 1.0
        assert reliabilify_score([0.5]) == 1.0

    def test_constant_scores(self):
        # No variance → perfect reliability
        assert reliabilify_score([0.6, 0.6, 0.6, 0.6]) == pytest.approx(1.0)

    def test_high_variance_lowers_score(self):
        low = reliabilify_score([0.1, 0.9, 0.1, 0.9])
        high = reliabilify_score([0.5, 0.51, 0.49, 0.5])
        assert 0.0 <= low < high <= 1.0

    def test_zero_mean_returns_zero(self):
        assert reliabilify_score([0.0, 0.0, 0.0]) == 0.0


class TestSolidify:
    def test_empty_returns_zero(self):
        assert solidify_score({}) == 0.0

    def test_worst_category_wins(self):
        buckets = {"faq": [0.9, 0.95], "billing": [0.1, 0.2], "escalation": [0.8]}
        assert solidify_score(buckets) == pytest.approx(0.15)

    def test_empty_category_treated_as_zero(self):
        buckets = {"a": [1.0], "b": []}
        assert solidify_score(buckets) == 0.0


class TestStabilize:
    def test_nothing_previously_passed(self):
        assert stabilize_score([False, False, False], [False, False, True]) == 1.0

    def test_no_regression(self):
        assert stabilize_score([True, True, False], [True, True, True]) == 1.0

    def test_one_regression(self):
        # 2 previously passed, 1 still passes → 0.5
        assert stabilize_score([True, True, False], [True, False, False]) == 0.5

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            stabilize_score([True, True], [True])


class TestComputeRRSS:
    def test_composite_is_weighted_mean(self):
        # Equal weights, known axis inputs
        c = compute_rrss(
            per_item_scores=[0.8, 0.8, 0.8, 0.8],
            repeated_scores=[0.8, 0.8, 0.8],
            scores_by_category={"only": [0.8]},
            prev_pass=[True, True, True],
            cand_pass=[True, True, True],
        )
        # robustify=0.8, reliabilify=1.0, solidify=0.8, stabilize=1.0 → mean 0.9
        assert c.robustify == pytest.approx(0.8)
        assert c.reliabilify == pytest.approx(1.0)
        assert c.solidify == pytest.approx(0.8)
        assert c.stabilize == pytest.approx(1.0)
        assert c.composite == pytest.approx(0.9)

    def test_partial_inputs_use_safe_defaults(self):
        # Only per-item scores supplied → other axes fall back
        c = compute_rrss(per_item_scores=[0.5, 0.5, 0.5, 0.5])
        assert c.reliabilify == 1.0  # no repeats → treated as stable
        assert c.solidify == 0.0     # no categories → 0
        assert c.stabilize == 1.0    # nothing to regress against

    def test_custom_weights_renormalized(self):
        c = compute_rrss(
            per_item_scores=[1.0, 1.0, 1.0, 1.0],
            repeated_scores=[0.0, 0.0, 0.0],  # reliabilify = 0
            scores_by_category={"a": [1.0]},
            prev_pass=[True], cand_pass=[True],
            weights={"robustify": 8, "reliabilify": 2, "solidify": 0, "stabilize": 0},
        )
        # Renormalized: robustify=0.8, reliabilify=0.2 → 0.8*1.0 + 0.2*0.0 = 0.8
        assert c.composite == pytest.approx(0.8)

    def test_missing_weight_axis_raises(self):
        with pytest.raises(ValueError):
            compute_rrss(
                per_item_scores=[0.5],
                weights={"robustify": 1.0},  # missing three axes
            )


class TestRRSSGate:
    def _sample(self, composite=0.7) -> RRSSComponents:
        return RRSSComponents(
            robustify=composite,
            reliabilify=composite,
            solidify=composite,
            stabilize=composite,
            composite=composite,
        )

    def test_improvement_passes(self):
        d = rrss_gate(self._sample(0.80), previous_composite=0.75, min_improvement=0.02)
        assert d.passed is True
        assert d.delta == pytest.approx(0.05)

    def test_no_improvement_rejects(self):
        d = rrss_gate(self._sample(0.76), previous_composite=0.75, min_improvement=0.05)
        assert d.passed is False
        assert "below" not in d.reason  # this is the composite path, not floor path
        assert d.delta == pytest.approx(0.01)

    def test_axis_floor_rejects_even_with_improvement(self):
        c = RRSSComponents(
            robustify=0.90,
            reliabilify=0.90,
            solidify=0.10,   # below floor
            stabilize=0.90,
            composite=0.90,
        )
        d = rrss_gate(
            c,
            previous_composite=0.50,
            min_improvement=0.0,
            axis_floors={"solidify": 0.5},
        )
        assert d.passed is False
        assert "solidify" in d.reason

    def test_unknown_axis_floor_raises(self):
        with pytest.raises(ValueError):
            rrss_gate(
                self._sample(0.5),
                previous_composite=0.0,
                axis_floors={"not_an_axis": 0.5},
            )

    def test_composite_is_clamped(self):
        # Even if inputs somehow overshoot, composite is [0, 1]
        c = compute_rrss(per_item_scores=[1.0])
        assert 0.0 <= c.composite <= 1.0
        assert not math.isnan(c.composite)
