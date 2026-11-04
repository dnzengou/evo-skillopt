"""Tests for the worker JSON logger."""

from __future__ import annotations

import io
import json
import logging
import sys
from pathlib import Path

_WORKER_DIR = Path(__file__).resolve().parent.parent / "worker"
if str(_WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(_WORKER_DIR))


def _emit(record_kwargs: dict, level: int = logging.INFO) -> dict:
    """Format one LogRecord via JsonFormatter and return the parsed dict."""
    from log import JsonFormatter  # noqa: PLC0415

    logger = logging.getLogger("test-log-" + record_kwargs.get("msg", "x"))
    logger.handlers.clear()
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False

    msg = record_kwargs.pop("msg")
    logger.log(level, msg, extra=record_kwargs)
    return json.loads(stream.getvalue().strip())


def test_json_shape_has_required_fields():
    row = _emit({"msg": "hello"})
    assert row["msg"] == "hello"
    assert row["level"] == "INFO"
    assert row["ts"].endswith("Z")
    assert "logger" in row


def test_extras_promoted_to_top_level():
    row = _emit({"msg": "training", "bot_id": "acme/bot", "job_id": "abc123", "version": "0.1.0"})
    assert row["bot_id"] == "acme/bot"
    assert row["job_id"] == "abc123"
    assert row["version"] == "0.1.0"


def test_reserved_logrecord_attrs_not_leaked():
    row = _emit({"msg": "x"})
    assert "args" not in row
    assert "created" not in row
    assert "pathname" not in row


def test_exception_captured():
    from log import JsonFormatter  # noqa: PLC0415

    logger = logging.getLogger("exc-test")
    logger.handlers.clear()
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)
    logger.propagate = False

    try:
        raise ValueError("kaboom")
    except ValueError:
        logger.exception("failed")

    row = json.loads(stream.getvalue().strip())
    assert row["msg"] == "failed"
    assert "ValueError: kaboom" in row.get("exc", "")


def test_configure_idempotent(monkeypatch):
    import log as log_mod  # noqa: PLC0415

    monkeypatch.setattr(log_mod, "_CONFIGURED", False)
    log_mod.configure()
    assert log_mod._CONFIGURED is True
    before = len(logging.getLogger().handlers)
    log_mod.configure()
    assert len(logging.getLogger().handlers) == before
