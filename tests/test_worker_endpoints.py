"""Smoke tests for the worker's cascade and RRSS-overlay run paths."""
from __future__ import annotations

import pytest

# Importing the worker module triggers its own sys.path shim for rrss_gate/cascade.
from skillopt_worker import run_cascade


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
