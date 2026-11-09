"""SQLite-backed job queue for /train.

Default `/train` stays synchronous. Opt in with ``{"async": true}`` in
the request body: the worker enqueues the job, returns 202 + job_id,
and background threads drain the queue. Callers poll ``/jobs/{id}``
for status + result.

Why SQLite:
  - no new dependency (stdlib `sqlite3`)
  - survives container restart (WAL mode + a persistent file)
  - good enough for 10 writes/sec × a few bots (our real load shape)

Not in scope here:
  - cross-host clustering (one worker, one queue file — if you need
    more, put a real broker like Redis/NATS behind this interface)
  - priorities beyond FIFO
  - cancellation after start (job runs to completion)

Status machine:
    queued → running → (succeeded | failed | timeout)

A job that was `running` when the worker crashed is reclaimed on next
startup by resetting rows whose `started_at` is older than
``STALE_RUNNING_SECONDS`` back to `queued`. The runner never deletes
rows; call ``vacuum`` on a cadence if you need disk back.

Public API
----------
    open_db(path) -> sqlite3.Connection
    enqueue(db, bot_id, payload, job_id=None) -> dict
    claim_next(db, now_fn=time.time) -> dict | None    (atomic)
    complete(db, job_id, result=None, error=None, status="succeeded")
    get(db, job_id) -> dict | None
    list_jobs(db, status=None, bot_id=None, limit=50, offset=0) -> list[dict]
    recover_stale(db, max_running_seconds=STALE_RUNNING_SECONDS) -> int
    delete_old(db, keep_last=10_000) -> int           (optional vacuum)
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from collections.abc import Callable
from pathlib import Path

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_TIMEOUT = "timeout"

STATUSES = (STATUS_QUEUED, STATUS_RUNNING, STATUS_SUCCEEDED, STATUS_FAILED, STATUS_TIMEOUT)
TERMINAL_STATUSES = (STATUS_SUCCEEDED, STATUS_FAILED, STATUS_TIMEOUT)

DEFAULT_DB = os.environ.get("JOB_QUEUE_DB", "jobs.db")
STALE_RUNNING_SECONDS = int(os.environ.get("JOB_QUEUE_STALE_SECONDS", "7200"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    bot_id        TEXT NOT NULL,
    payload_json  TEXT NOT NULL,
    status        TEXT NOT NULL,
    created_at    INTEGER NOT NULL,
    started_at    INTEGER,
    finished_at   INTEGER,
    result_json   TEXT,
    error         TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_bot_id        ON jobs(bot_id, created_at DESC);
"""


def open_db(path: str | Path | None = None) -> sqlite3.Connection:
    """Open (or create) the queue DB in WAL mode. Thread-safe handle."""
    db_path = str(path or DEFAULT_DB)
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        db_path,
        isolation_level=None,            # autocommit; we use BEGIN explicitly
        timeout=10.0,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.executescript(SCHEMA)
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    # Hydrate JSON columns for the caller's convenience.
    for k in ("payload_json", "result_json"):
        v = d.get(k)
        if v is None:
            continue
        try:
            d[k.replace("_json", "")] = json.loads(v)
        except (ValueError, TypeError):
            d[k.replace("_json", "")] = None
    d.pop("payload_json", None)
    d.pop("result_json", None)
    return d


def enqueue(
    db: sqlite3.Connection,
    bot_id: str,
    payload: dict,
    job_id: str | None = None,
    now_fn: Callable[[], float] = time.time,
) -> dict:
    """Enqueue one job. Idempotent on job_id (returns the existing row)."""
    job_id = job_id or str(uuid.uuid4())
    now = int(now_fn())
    db.execute(
        """INSERT OR IGNORE INTO jobs
           (id, bot_id, payload_json, status, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (job_id, bot_id, json.dumps(payload), STATUS_QUEUED, now),
    )
    return get(db, job_id)  # type: ignore[return-value]


def claim_next(
    db: sqlite3.Connection,
    now_fn: Callable[[], float] = time.time,
) -> dict | None:
    """Atomically pull the oldest queued job and mark it running.

    Returns None if nothing's queued. Uses BEGIN IMMEDIATE to block
    other claim_next calls from racing on the same row.
    """
    now = int(now_fn())
    try:
        db.execute("BEGIN IMMEDIATE;")
    except sqlite3.OperationalError:
        return None
    try:
        row = db.execute(
            """SELECT id FROM jobs
               WHERE status = ?
               ORDER BY created_at ASC
               LIMIT 1""",
            (STATUS_QUEUED,),
        ).fetchone()
        if row is None:
            db.execute("COMMIT;")
            return None
        job_id = row["id"]
        db.execute(
            """UPDATE jobs
               SET status = ?, started_at = ?
               WHERE id = ? AND status = ?""",
            (STATUS_RUNNING, now, job_id, STATUS_QUEUED),
        )
        db.execute("COMMIT;")
    except Exception:
        db.execute("ROLLBACK;")
        raise
    return get(db, job_id)


def complete(
    db: sqlite3.Connection,
    job_id: str,
    result: dict | None = None,
    error: str | None = None,
    status: str = STATUS_SUCCEEDED,
    now_fn: Callable[[], float] = time.time,
) -> dict | None:
    """Mark a running job terminal. Safe to call once per job."""
    if status not in TERMINAL_STATUSES:
        raise ValueError(f"not a terminal status: {status!r}")
    now = int(now_fn())
    db.execute(
        """UPDATE jobs
           SET status = ?, finished_at = ?, result_json = ?, error = ?
           WHERE id = ?""",
        (
            status, now,
            json.dumps(result) if result is not None else None,
            error,
            job_id,
        ),
    )
    return get(db, job_id)


def get(db: sqlite3.Connection, job_id: str) -> dict | None:
    row = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_dict(row)


def list_jobs(
    db: sqlite3.Connection,
    status: str | None = None,
    bot_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Newest first. Combined status + bot_id filter supported."""
    clauses, args = [], []
    if status:
        clauses.append("status = ?")
        args.append(status)
    if bot_id:
        clauses.append("bot_id = ?")
        args.append(bot_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (
        f"SELECT * FROM jobs {where} "
        "ORDER BY created_at DESC LIMIT ? OFFSET ?"
    )
    args.extend([max(1, min(limit, 200)), max(0, offset)])
    rows = db.execute(sql, args).fetchall()
    return [_row_to_dict(r) for r in rows]  # type: ignore[misc]


def recover_stale(
    db: sqlite3.Connection,
    max_running_seconds: int = STALE_RUNNING_SECONDS,
    now_fn: Callable[[], float] = time.time,
) -> int:
    """Reset rows stuck in `running` back to `queued` so they get retried.

    A worker crash while a job was running leaves the row claimed with
    no one draining it. Call this on startup to recover.
    """
    cutoff = int(now_fn()) - max_running_seconds
    cur = db.execute(
        """UPDATE jobs
           SET status = ?, started_at = NULL
           WHERE status = ? AND started_at IS NOT NULL AND started_at < ?""",
        (STATUS_QUEUED, STATUS_RUNNING, cutoff),
    )
    return cur.rowcount or 0


def delete_old(
    db: sqlite3.Connection,
    keep_last: int = 10_000,
) -> int:
    """Delete all but the most-recent ``keep_last`` terminal rows.

    Optional — the queue works fine without this. Call on a cadence
    if you want disk back.
    """
    # SQLite doesn't support LIMIT in DELETE directly without a build
    # flag, so select the cutoff first.
    row = db.execute(
        """SELECT created_at FROM jobs
           WHERE status IN (?, ?, ?)
           ORDER BY created_at DESC
           LIMIT 1 OFFSET ?""",
        (STATUS_SUCCEEDED, STATUS_FAILED, STATUS_TIMEOUT, keep_last),
    ).fetchone()
    if row is None:
        return 0
    cur = db.execute(
        """DELETE FROM jobs
           WHERE status IN (?, ?, ?) AND created_at <= ?""",
        (STATUS_SUCCEEDED, STATUS_FAILED, STATUS_TIMEOUT, row["created_at"]),
    )
    return cur.rowcount or 0


def counts_by_status(db: sqlite3.Connection) -> dict[str, int]:
    """Convenience for /health or /metrics."""
    rows = db.execute(
        "SELECT status, COUNT(*) AS n FROM jobs GROUP BY status"
    ).fetchall()
    out = {s: 0 for s in STATUSES}
    for r in rows:
        out[r["status"]] = r["n"]
    return out
