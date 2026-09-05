"""Smoke tests for the worker's cascade and RRSS-overlay run paths."""
from __future__ import annotations

import pytest

# Importing the worker module triggers its own sys.path shim for rrss_gate/cascade.
from skillopt_worker import run_arm_fitness, run_cascade


class TestRunCascade:
    def test_happy_path(self):
        out = run_cascade(
            {
                "bot_id": "acme/support",
                "stages": [
                    {"name": "filter", "score": 0.94},
                    {"name": "classify", "score": 0.88},
                    {"name": "draft", "score": 0.91},
                ],
                "aggregation": "mean",
                "aggregate_threshold": 0.85,
                "stage_floor": 0.60,
            }
        )
        assert out["ok"] is True
        assert out["gate_passed"] is True
        assert out["aggregate"] == pytest.approx(0.9100, abs=1e-4)
        assert len(out["stages"]) == 3

    def test_missing_stages(self):
        out = run_cascade({"bot_id": "acme/support"})
        assert out["ok"] is False
        assert out["error"] == "cascade-missing-stages"

    def test_stage_floor_blocks(self):
        out = run_cascade(
            {
                "bot_id": "acme/support",
                "stages": [
                    {"name": "filter", "score": 0.10},
                    {"name": "draft", "score": 0.95},
                ],
                "stage_floor": 0.5,
                "aggregate_threshold": 0.5,
            }
        )
        assert out["gate_passed"] is False
        assert "filter" in out["reason"]

    def test_bad_stage_shape(self):
        out = run_cascade(
            {
                "bot_id": "acme/support",
                "stages": [{"name": "no-score"}],
            }
        )
        assert out["ok"] is False
        assert out["error"].startswith("cascade-bad-stage")


class TestRunARMFitness:
    def test_happy_path(self):
        out = run_arm_fitness(
            {
                "bot_id": "acme/support",
                "signals": [
                    {"bucket": "acquire", "delta": 1.0, "kind": "trial"},
                    {"bucket": "retain", "delta": 0.5, "kind": "csat_5"},
                    {"bucket": "monetize", "delta": 2.0, "kind": "upgrade"},
                ],
                "weights": {"acquire": 0.3, "retain": 0.5, "monetize": 0.2},
            }
        )
        assert out["ok"] is True
        # 0.3*1.0 + 0.5*0.5 + 0.2*2.0 = 0.95
        assert out["composite"] == pytest.approx(0.95)
        assert len(out["per_bucket"]) == 3

    def test_missing_signals_returns_zero_fitness(self):
        # Missing/empty signals is a legitimate "quiet window" answer,
        # not an error — the worker replies with composite 0 and empty
        # per-bucket rows so upstream can still record the check-in.
        out = run_arm_fitness({"bot_id": "acme/support"})
        assert out["ok"] is True
        assert out["composite"] == 0.0
        assert all(b["count"] == 0 for b in out["per_bucket"])

    def test_non_list_signals_rejected(self):
        out = run_arm_fitness({"bot_id": "acme/support", "signals": "nope"})
        assert out["ok"] is False
        assert out["error"] == "arm-missing-signals"

    def test_bad_signal_shape(self):
        out = run_arm_fitness(
            {
                "bot_id": "acme/support",
                "signals": [{"bucket": "acquire"}],  # missing delta
            }
        )
        assert out["ok"] is False
        assert out["error"].startswith("arm-bad-signal")

    def test_bad_weights_surface_as_error(self):
        out = run_arm_fitness(
            {
                "bot_id": "acme/support",
                "signals": [{"bucket": "acquire", "delta": 1.0}],
                "weights": {"acquire": 1.0},  # missing retain, monetize
            }
        )
        assert out["ok"] is False
        assert out["error"].startswith("arm-bad-weights")
