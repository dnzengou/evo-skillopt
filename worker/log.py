"""Structured JSON logger for the worker.

Replaces scattered ``print(..., flush=True)`` calls with a single
logger that emits one newline-delimited JSON object per log line.
This is the shape every log-aggregator (Datadog, Grafana Loki, Vector,
Fluent Bit, CloudWatch, Fly's Grafana) expects without further parsing.

Lines look like:

    {"ts":"2026-11-04T12:34:56.789Z","level":"INFO","logger":"worker",
     "msg":"training","bot_id":"acme/bot","job_id":"<uuid>","version":"0.1.0"}

Use:

    from log import get_logger
    log = get_logger(__name__)
    log.info("training", extra={"bot_id": bot_id, "job_id": job_id})

Extras become top-level fields on the JSON line.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone

_RESERVED = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName",
}


class JsonFormatter(logging.Formatter):
    """Format a LogRecord as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


_CONFIGURED = False


def configure(level: str | int | None = None) -> None:
    """Install the JSON formatter on the root logger. Idempotent.

    Honors LOG_LEVEL env var (default INFO).
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    lvl = level if level is not None else os.environ.get("LOG_LEVEL", "INFO")
    if isinstance(lvl, str):
        lvl = getattr(logging, lvl.upper(), logging.INFO)
    root.setLevel(lvl)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure()
    return logging.getLogger(name)
