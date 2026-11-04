"""Prometheus metrics with graceful degradation.

Importing ``prometheus_client`` is optional — if it is not installed,
``is_available`` returns False and ``render_metrics`` returns a short
message. The worker then responds to ``GET /metrics`` with 503 so
operators see a clear install instruction.

Metrics shipped (RED-method):
    evo_skillopt_requests_total{method,path,code}           — counter
    evo_skillopt_request_duration_seconds{method,path}      — histogram
    evo_skillopt_inflight_requests{method,path}             — gauge
    evo_skillopt_training_runs_total{outcome}               — counter
    evo_skillopt_training_duration_seconds                  — histogram
    evo_skillopt_gate_pass_total{gate_kind,result}          — counter

Training and gate metrics are populated only when the relevant code
path actually ran; discovery / health GETs do not touch them.
"""

from __future__ import annotations

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
    _AVAILABLE = True
except ImportError:  # pragma: no cover
    _AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"


_REGISTRY = None
_REQ_TOTAL = None
_REQ_DURATION = None
_REQ_INFLIGHT = None
_TRAIN_TOTAL = None
_TRAIN_DURATION = None
_GATE_TOTAL = None


def is_available() -> bool:
    return _AVAILABLE


def init() -> None:
    """Create the registry + metric objects. Idempotent."""
    global _REGISTRY, _REQ_TOTAL, _REQ_DURATION, _REQ_INFLIGHT
    global _TRAIN_TOTAL, _TRAIN_DURATION, _GATE_TOTAL

    if not _AVAILABLE or _REGISTRY is not None:
        return

    _REGISTRY = CollectorRegistry()
    _REQ_TOTAL = Counter(
        "evo_skillopt_requests_total",
        "Total HTTP requests served by the worker.",
        ["method", "path", "code"],
        registry=_REGISTRY,
    )
    _REQ_DURATION = Histogram(
        "evo_skillopt_request_duration_seconds",
        "Wall-clock duration of HTTP requests.",
        ["method", "path"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 300, 1800, 3600),
        registry=_REGISTRY,
    )
    _REQ_INFLIGHT = Gauge(
        "evo_skillopt_inflight_requests",
        "In-flight HTTP requests.",
        ["method", "path"],
        registry=_REGISTRY,
    )
    _TRAIN_TOTAL = Counter(
        "evo_skillopt_training_runs_total",
        "Total training runs.",
        ["outcome"],  # accepted | rejected | failed | timeout
        registry=_REGISTRY,
    )
    _TRAIN_DURATION = Histogram(
        "evo_skillopt_training_duration_seconds",
        "Wall-clock duration of /train subprocess invocations.",
        buckets=(1, 5, 15, 30, 60, 120, 300, 600, 1800, 3600),
        registry=_REGISTRY,
    )
    _GATE_TOTAL = Counter(
        "evo_skillopt_gate_pass_total",
        "Gate decisions.",
        ["gate_kind", "result"],  # kind: base|rrss|cascade — result: pass|fail
        registry=_REGISTRY,
    )


def _label_path(raw_path: str) -> str:
    """Collapse high-cardinality paths so metric cardinality stays bounded."""
    base = raw_path.split("?", 1)[0]
    # Bot-scoped endpoints like /bots/<id>/skill become /bots/{id}/skill.
    if base.startswith("/bots/"):
        parts = base.split("/")
        if len(parts) >= 4:
            parts[2] = "{id}"
            return "/".join(parts[:4] + parts[4:]) if len(parts) > 4 else "/".join(parts)
    return base


def record_request(method: str, raw_path: str, code: int, duration_s: float) -> None:
    if _REQ_TOTAL is None or _REQ_DURATION is None:
        return
    path = _label_path(raw_path)
    _REQ_TOTAL.labels(method=method, path=path, code=str(code)).inc()
    _REQ_DURATION.labels(method=method, path=path).observe(duration_s)


def inflight_inc(method: str, raw_path: str) -> None:
    if _REQ_INFLIGHT is None:
        return
    _REQ_INFLIGHT.labels(method=method, path=_label_path(raw_path)).inc()


def inflight_dec(method: str, raw_path: str) -> None:
    if _REQ_INFLIGHT is None:
        return
    _REQ_INFLIGHT.labels(method=method, path=_label_path(raw_path)).dec()


def record_training(outcome: str, duration_s: float) -> None:
    if _TRAIN_TOTAL is None or _TRAIN_DURATION is None:
        return
    _TRAIN_TOTAL.labels(outcome=outcome).inc()
    _TRAIN_DURATION.observe(duration_s)


def record_gate(gate_kind: str, passed: bool) -> None:
    if _GATE_TOTAL is None:
        return
    _GATE_TOTAL.labels(gate_kind=gate_kind, result="pass" if passed else "fail").inc()


def render_metrics() -> tuple[bytes, str]:
    """Return (body, content-type) for the ``/metrics`` endpoint."""
    if not _AVAILABLE or _REGISTRY is None:
        msg = (
            b"# evo-skillopt /metrics requires prometheus_client\n"
            b"# install with: pip install -e '.[worker]'\n"
        )
        return msg, "text/plain; charset=utf-8"
    return generate_latest(_REGISTRY), CONTENT_TYPE_LATEST
