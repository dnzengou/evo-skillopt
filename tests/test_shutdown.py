"""Tests for the SIGTERM graceful-drain machinery.

Exercises the state primitives directly rather than spinning a server
thread. The signal wiring itself is a thin wrapper around
``signal.signal`` and is covered by an integration smoke in CI.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

_WORKER_DIR = Path(__file__).resolve().parent.parent / "worker"
if str(_WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(_WORKER_DIR))


@pytest.fixture
def fresh(monkeypatch):
    """Reset the module-level shutdown state between tests."""
    import skillopt_worker as sw  # noqa: PLC0415

    monkeypatch.setattr(sw, "_shutting_down", threading.Event())
    monkeypatch.setattr(sw, "_inflight_count", 0)
    monkeypatch.setattr(sw, "_inflight_lock", threading.Lock())
    return sw


class TestInflightTracking:
    def test_begin_end_round_trip(self, fresh):
        assert fresh._inflight_snapshot() == 0
        fresh._inflight_begin()
        fresh._inflight_begin()
        assert fresh._inflight_snapshot() == 2
        fresh._inflight_end()
        assert fresh._inflight_snapshot() == 1
        fresh._inflight_end()
        assert fresh._inflight_snapshot() == 0

    def test_end_below_zero_clamps(self, fresh):
        fresh._inflight_end()
        fresh._inflight_end()
        assert fresh._inflight_snapshot() == 0

    def test_concurrent_begin(self, fresh):
        import concurrent.futures  # noqa: PLC0415

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            list(ex.map(lambda _: fresh._inflight_begin(), range(200)))
        assert fresh._inflight_snapshot() == 200


class TestDrainAndShutdown:
    def test_flag_flips_and_server_shutdown_scheduled(self, fresh):
        calls = []

        class FakeServer:
            def shutdown(self):
                calls.append("shutdown")

        srv = FakeServer()
        fresh._drain_and_shutdown(srv)
        assert fresh._shutting_down.is_set()
        # shutdown() runs in a daemon thread — let it catch up.
        for _ in range(50):
            if calls:
                break
            import time as _t
            _t.sleep(0.05)
        assert calls == ["shutdown"]

    def test_idempotent(self, fresh):
        calls = []

        class FakeServer:
            def shutdown(self):
                calls.append("shutdown")

        srv = FakeServer()
        fresh._drain_and_shutdown(srv)
        fresh._drain_and_shutdown(srv)
        # Only one shutdown fires even if signal arrives twice.
        import time
        time.sleep(0.1)
        assert calls.count("shutdown") <= 1

    def test_shutdown_waits_for_inflight(self, fresh, monkeypatch):
        """With inflight > 0, drain blocks until it falls to zero."""
        import time as t

        calls = []

        class FakeServer:
            def shutdown(self):
                calls.append(t.time())

        srv = FakeServer()
        monkeypatch.setattr(fresh, "SHUTDOWN_GRACE_SECONDS", 2.0)

        # Pretend one request is in flight.
        fresh._inflight_begin()
        start = t.time()
        drain_thread = threading.Thread(
            target=fresh._drain_and_shutdown, args=(srv,), daemon=True,
        )
        drain_thread.start()
        # Simulate the request finishing after 300 ms.
        t.sleep(0.3)
        fresh._inflight_end()
        drain_thread.join(timeout=3)
        assert calls, "drain should have scheduled shutdown"
        # Total time should be roughly the sleep, not the full grace.
        elapsed = t.time() - start
        assert 0.25 < elapsed < 1.5
