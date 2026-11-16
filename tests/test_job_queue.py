"""Tests for the SQLite-backed job queue."""

from __future__ import annotations

import concurrent.futures
import sys
import threading
from pathlib import Path

import pytest

_WORKER_DIR = Path(__file__).resolve().parent.parent / "worker"
if str(_WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(_WORKER_DIR))

import job_queue  # noqa: E402


@pytest.fixture
def db():
    """In-memory DB per test."""
    conn = job_queue.open_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def file_db(tmp_path):
    """Persistent DB per test for restart-survival checks."""
    path = tmp_path / "jobs.db"
    conn = job_queue.open_db(path)
    yield conn, path
    conn.close()


class TestSchema:
    def test_open_creates_table(self, db):
        rows = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
        ).fetchall()
        assert len(rows) == 1


class TestEnqueueAndGet:
    def test_enqueue_returns_row(self, db):
        row = job_queue.enqueue(db, "acme/bot", {"skill_version": "0.1.0"})
        assert row["status"] == "queued"
        assert row["bot_id"] == "acme/bot"
        assert row["payload"] == {"skill_version": "0.1.0"}
        assert "id" in row

    def test_enqueue_idempotent_on_job_id(self, db):
        row1 = job_queue.enqueue(db, "acme/bot", {}, job_id="fixed-id")
        row2 = job_queue.enqueue(db, "acme/bot", {}, job_id="fixed-id")
        assert row1["id"] == row2["id"]
        assert job_queue.counts_by_status(db)["queued"] == 1

    def test_get_missing_returns_none(self, db):
        assert job_queue.get(db, "no-such-id") is None


class TestClaimNext:
    def test_claim_returns_oldest(self, db):
        job_queue.enqueue(db, "a/b", {"n": 1}, now_fn=lambda: 1_000)
        job_queue.enqueue(db, "a/b", {"n": 2}, now_fn=lambda: 2_000)
        claimed = job_queue.claim_next(db)
        assert claimed is not None
        assert claimed["payload"] == {"n": 1}
        assert claimed["status"] == "running"
        assert claimed["started_at"] is not None

    def test_claim_empty_queue(self, db):
        assert job_queue.claim_next(db) is None

    def test_claim_skips_running(self, db):
        job_queue.enqueue(db, "a/b", {})
        first = job_queue.claim_next(db)
        second = job_queue.claim_next(db)
        assert first is not None
        assert second is None

    def test_concurrent_claim_single_winner(self, file_db):
        """Two threads racing claim_next — exactly one wins."""
        _conn, path = file_db
        for i in range(10):
            job_queue.enqueue(_conn, "a/b", {"n": i})

        results: list[dict] = []
        results_lock = threading.Lock()

        def claim_once():
            # Each worker opens its own connection (per the module's
            # thread-safety guidance) and claims one job.
            conn = job_queue.open_db(path)
            try:
                job = job_queue.claim_next(conn)
                if job is not None:
                    with results_lock:
                        results.append(job)
            finally:
                conn.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            list(ex.map(lambda _: claim_once(), range(10)))

        claimed_ids = {r["id"] for r in results}
        # Each claim should return a different row — no doubles.
        assert len(claimed_ids) == len(results) == 10


class TestComplete:
    def test_succeeded(self, db):
        row = job_queue.enqueue(db, "a/b", {})
        job_queue.claim_next(db)
        done = job_queue.complete(db, row["id"],
                                  result={"gate_passed": True},
                                  status=job_queue.STATUS_SUCCEEDED)
        assert done["status"] == "succeeded"
        assert done["result"] == {"gate_passed": True}
        assert done["finished_at"] is not None

    def test_failed_carries_error(self, db):
        row = job_queue.enqueue(db, "a/b", {})
        job_queue.claim_next(db)
        done = job_queue.complete(db, row["id"],
                                  error="training-failed",
                                  status=job_queue.STATUS_FAILED)
        assert done["status"] == "failed"
        assert done["error"] == "training-failed"

    def test_non_terminal_status_rejected(self, db):
        with pytest.raises(ValueError):
            job_queue.complete(db, "any", status="running")  # type: ignore[arg-type]


class TestListJobs:
    def test_newest_first(self, db):
        r1 = job_queue.enqueue(db, "a/b", {"n": 1}, now_fn=lambda: 1_000)
        r2 = job_queue.enqueue(db, "a/b", {"n": 2}, now_fn=lambda: 2_000)
        rows = job_queue.list_jobs(db)
        assert [r["id"] for r in rows] == [r2["id"], r1["id"]]

    def test_filter_by_status(self, db):
        job_queue.enqueue(db, "a/b", {})
        job_queue.enqueue(db, "a/b", {})
        running = job_queue.claim_next(db)
        job_queue.complete(db, running["id"], status=job_queue.STATUS_SUCCEEDED)
        assert len(job_queue.list_jobs(db, status="queued")) == 1
        assert len(job_queue.list_jobs(db, status="succeeded")) == 1

    def test_filter_by_bot_id(self, db):
        job_queue.enqueue(db, "acme/bot", {})
        job_queue.enqueue(db, "widget/bot", {})
        assert len(job_queue.list_jobs(db, bot_id="acme/bot")) == 1

    def test_counts_by_status(self, db):
        job_queue.enqueue(db, "a/b", {})
        job_queue.enqueue(db, "a/b", {})
        job_queue.claim_next(db)
        counts = job_queue.counts_by_status(db)
        assert counts["queued"] == 1
        assert counts["running"] == 1
        assert counts["succeeded"] == 0


class TestRecoverStale:
    def test_resets_old_running_rows(self, db):
        row = job_queue.enqueue(db, "a/b", {}, now_fn=lambda: 1_000_000)
        # Simulate a stale running row.
        db.execute(
            "UPDATE jobs SET status='running', started_at=? WHERE id=?",
            (1_000_000, row["id"]),
        )
        recovered = job_queue.recover_stale(
            db, max_running_seconds=60, now_fn=lambda: 2_000_000,
        )
        assert recovered == 1
        assert job_queue.get(db, row["id"])["status"] == "queued"

    def test_leaves_fresh_running_rows(self, db):
        row = job_queue.enqueue(db, "a/b", {}, now_fn=lambda: 1_000_000)
        job_queue.claim_next(db, now_fn=lambda: 1_999_999)
        recovered = job_queue.recover_stale(
            db, max_running_seconds=3600, now_fn=lambda: 2_000_000,
        )
        assert recovered == 0
        assert job_queue.get(db, row["id"])["status"] == "running"


class TestPersistence:
    def test_survives_reopen(self, file_db):
        _conn, path = file_db
        row = job_queue.enqueue(_conn, "a/b", {"k": "v"})
        _conn.close()
        fresh = job_queue.open_db(path)
        got = job_queue.get(fresh, row["id"])
        assert got is not None
        assert got["payload"] == {"k": "v"}


class TestDeleteOld:
    def test_keeps_newest_n(self, db):
        for i in range(10):
            row = job_queue.enqueue(db, "a/b", {}, now_fn=lambda i=i: i)
            job_queue.claim_next(db, now_fn=lambda i=i: i)
            job_queue.complete(db, row["id"],
                               status=job_queue.STATUS_SUCCEEDED,
                               now_fn=lambda i=i: i)
        deleted = job_queue.delete_old(db, keep_last=3)
        assert deleted >= 6
        remaining = job_queue.list_jobs(db, limit=100)
        assert len(remaining) == 3
