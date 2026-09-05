"""Shared pytest wiring — add ``worker/`` to sys.path so its modules
import as ``rrss_gate`` / ``cascade`` without needing an install step.
"""
from __future__ import annotations

import sys
from pathlib import Path

_WORKER = Path(__file__).resolve().parent.parent / "worker"
if str(_WORKER) not in sys.path:
    sys.path.insert(0, str(_WORKER))
