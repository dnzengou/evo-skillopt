"""Tests for the worker metrics module."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_WORKER_DIR = Path(__file__).resolve().parent.parent / "worker"
if str(_WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(_WORKER_DIR))


@pytest.fixture
def metrics_fresh(monkeypatch):
    """Reload metrics with a fresh registry for each test."""
    import metrics as m  # noqa: PLC0415
    importlib.reload(m)
    m.init()
    return m


def test_metrics_available_after_install(metrics_fresh):
    pytest.importorskip("prometheus_client")
    assert metrics_fresh.is_available() is True


def test_label_path_collapses_bot_id(metrics_fresh):
    assert metrics_fresh._label_path("/bots/acme-bot/skill") == "/bots/{id}/skill"
    assert metrics_fresh._label_path("/bots/acme-bot/skill?version=0.1.0") == "/bots/{id}/skill"
    assert metrics_fresh._label_path("/health") == "/health"
    assert metrics_fresh._label_path("/.well-known/agents.json") == "/.well-known/agents.json"


def test_record_request_and_render(metrics_fresh):
    pytest.importorskip("prometheus_client")
    metrics_fresh.record_request("GET", "/health", 200, 0.012)
    metrics_fresh.record_request("POST", "/train", 200, 42.0)
    metrics_fresh.inflight_inc("POST", "/train")
    metrics_fresh.inflight_dec("POST", "/train")
    metrics_fresh.record_training("accepted", 120.0)
    metrics_fresh.record_gate("base", True)
    metrics_fresh.record_gate("rrss", False)

    body, ctype = metrics_fresh.render_metrics()
    assert "text/plain" in ctype or "openmetrics" in ctype
    text = body.decode()
    assert 'evo_skillopt_requests_total{code="200",method="GET",path="/health"} 1.0' in text
    assert "evo_skillopt_training_runs_total" in text
    assert 'result="pass"' in text
    assert 'result="fail"' in text


def test_render_without_prometheus_degrades_gracefully(monkeypatch):
    """When prometheus_client is not importable the module should still work."""
    import metrics as m  # noqa: PLC0415
    monkeypatch.setattr(m, "_AVAILABLE", False)
    monkeypatch.setattr(m, "_REGISTRY", None)
    body, ctype = m.render_metrics()
    assert b"requires prometheus_client" in body
    assert ctype.startswith("text/plain")
    # These helpers must be no-ops under degraded mode.
    m.record_request("GET", "/health", 200, 0.01)  # does not raise
