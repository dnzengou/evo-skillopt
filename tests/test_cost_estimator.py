"""Tests for the cost estimator — pure math, plus the HTTP shim."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_WORKER_DIR = Path(__file__).resolve().parent.parent / "worker"
if str(_WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(_WORKER_DIR))

from cost_estimator import (  # noqa: E402
    MODELS,
    ModelPrice,
    Workload,
    estimate_cost,
    list_models,
)


class TestRegistry:
    def test_known_openai_models_present(self):
        assert "gpt-4o-mini" in MODELS
        assert "gpt-4o" in MODELS

    def test_known_anthropic_models_present(self):
        assert "claude-opus-4" in MODELS
        assert "claude-3-5-sonnet" in MODELS

    def test_local_is_free(self):
        p = MODELS["local"]
        assert p.input_per_1m == 0.0
        assert p.output_per_1m == 0.0

    def test_list_models_shape(self):
        rows = list_models()
        assert len(rows) >= 10
        for row in rows:
            assert {"name", "provider", "input_per_1m_usd", "output_per_1m_usd", "updated_at"} <= set(row)


class TestEstimateMath:
    def test_defaults_are_small_and_positive(self):
        est = estimate_cost(Workload(), "gpt-4o-mini")
        assert est.total_tokens > 0
        assert est.est_cost_usd > 0
        # gpt-4o-mini @ default workload should be well under $1.
        # (~112k input + ~45k output tokens @ $0.15/$0.60 per 1M ≈ $0.04)
        assert est.est_cost_usd < 1.0
        assert set(est.breakdown) == {"rollout", "reflect", "gate"}

    def test_zero_epochs_zero_cost(self):
        est = estimate_cost(Workload(num_epochs=0), "gpt-4o-mini")
        assert est.total_tokens == 0
        assert est.est_cost_usd == 0.0

    def test_doubling_epochs_doubles_cost(self):
        one = estimate_cost(Workload(num_epochs=1), "gpt-4o")
        two = estimate_cost(Workload(num_epochs=2), "gpt-4o")
        assert two.est_cost_usd == pytest.approx(2 * one.est_cost_usd, rel=1e-6)
        assert two.total_tokens == 2 * one.total_tokens

    def test_breakdown_sums_to_total(self):
        est = estimate_cost(Workload(), "gpt-4o-mini")
        assert sum(est.breakdown.values()) == pytest.approx(est.est_cost_usd, abs=1e-9)

    def test_output_ratio_moves_output_tokens(self):
        low = estimate_cost(Workload(output_token_ratio=0.1), "gpt-4o-mini")
        high = estimate_cost(Workload(output_token_ratio=0.9), "gpt-4o-mini")
        assert high.total_output_tokens > low.total_output_tokens
        assert high.est_cost_usd > low.est_cost_usd

    def test_local_model_is_free(self):
        est = estimate_cost(Workload(), "local")
        assert est.est_cost_usd == 0.0
        assert est.total_tokens > 0

    def test_opus_costs_more_than_haiku(self):
        wl = Workload()
        opus = estimate_cost(wl, "claude-opus-4").est_cost_usd
        haiku = estimate_cost(wl, "claude-haiku-4").est_cost_usd
        assert opus > haiku * 10   # ~15x on input, ~18x on output

    def test_unknown_model_raises(self):
        with pytest.raises(KeyError):
            estimate_cost(Workload(), "no-such-model")

    def test_caller_price_override(self):
        wl = Workload()
        override = {"custom": ModelPrice("custom", 1.0, 2.0, "test", "2026-11")}
        est = estimate_cost(wl, "custom", prices=override)
        assert est.model == "custom"
        assert est.est_cost_usd > 0


class TestHTTPShim:
    def setup_method(self):
        import skillopt_worker as sw  # noqa: PLC0415
        self.sw = sw

    def test_happy_path(self):
        out = self.sw.run_cost_estimate(
            {
                "bot_id": "acme/bot",
                "model": "gpt-4o-mini",
                "workload": {"num_epochs": 2, "n_train_items": 50},
            }
        )
        assert out["ok"] is True
        assert out["model"] == "gpt-4o-mini"
        assert out["total_tokens"] > 0
        assert out["est_cost_usd"] > 0
        assert out["assumptions"]["num_epochs"] == 2
        assert out["assumptions"]["n_train_items"] == 50

    def test_missing_model(self):
        out = self.sw.run_cost_estimate({"bot_id": "a/b"})
        assert out["ok"] is False
        assert out["error"] == "cost-missing-model"

    def test_unknown_field_rejected(self):
        out = self.sw.run_cost_estimate(
            {"bot_id": "a/b", "model": "gpt-4o", "workload": {"evil": 1}}
        )
        assert out["ok"] is False
        assert "unknown-field" in out["error"]

    def test_unknown_model_surfaced(self):
        out = self.sw.run_cost_estimate({"bot_id": "a/b", "model": "nope"})
        assert out["ok"] is False
        assert "unknown-model" in out["error"]

    def test_bad_workload_type(self):
        out = self.sw.run_cost_estimate(
            {"bot_id": "a/b", "model": "gpt-4o", "workload": "oops"}
        )
        assert out["ok"] is False
        assert out["error"] == "cost-bad-workload"
