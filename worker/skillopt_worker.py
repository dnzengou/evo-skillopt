#!/usr/bin/env python3
"""
SkillOpt worker — bridges evo-metaclaw ↔ SkillOpt training loop.

Listens for `POST /train` from evo-metaclaw with:
  {
    "bot_id":          "author/name",
    "skill_version":   "0.1.4",
    "skill_path":      "/data/bots/author-name/skills/main.md",
    "eval_split_dir":  "/data/bots/author-name/eval",
    "config":          "configs/searchqa/default.yaml",   # or bot-supplied
    "num_epochs":      1
  }

Responds with:
  {
    "ok":              true,
    "gate_passed":     true,
    "gate_score_delta": 0.073,
    "next_version":    "0.1.5",
    "output_dir":      "outputs/author-name-v0.1.5-<ts>",
    "duration_s":      412
  }

Deployment: run on same host as `scripts/train.py`. Not exposed publicly
— evo-metaclaw calls it over the private Fly.io 6PN network via the
service's internal DNS name.

Zero external deps: stdlib only (http.server, json, subprocess).
"""

import json
import os
import re
import subprocess
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "").strip()
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "outputs/evo")).resolve()
TRAIN_SCRIPT = Path(os.environ.get("TRAIN_SCRIPT", "scripts/train.py")).resolve()
PORT = int(os.environ.get("PORT", "9000"))

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def bump(v: str) -> str:
    if not VERSION_RE.match(v):
        return "0.1.1"
    a, b, c = v.split(".")
    return f"{a}.{b}.{int(c) + 1}"


def parse_gate_delta(output_dir: Path) -> float:
    """Read history.json and diff the last two epoch mean rewards.

    Returns 0.0 if we can't read a signal; keeps evo-metaclaw's gate
    from tripping on transient IO errors.
    """
    history = output_dir / "history.json"
    if not history.exists():
        return 0.0
    try:
        data = json.loads(history.read_text())
        steps = data.get("steps", [])
        if len(steps) < 2:
            return 0.0
        return float(steps[-1].get("val_reward", 0.0) - steps[-2].get("val_reward", 0.0))
    except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
        return 0.0


def run_training(job: dict) -> dict:
    bot_id = job["bot_id"]
    skill_version = job.get("skill_version", "0.1.0")
    next_version = bump(skill_version)
    slug = bot_id.replace("/", "-")
    ts = int(time.time())
    output_dir = OUTPUT_ROOT / f"{slug}-v{next_version}-{ts}"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, str(TRAIN_SCRIPT),
        "--config", job.get("config", "configs/searchqa/default.yaml"),
        "--out_root", str(output_dir),
        "--num_epochs", str(int(job.get("num_epochs", 1))),
    ]
    if "skill_path" in job:
        cmd.extend(["--skill", job["skill_path"]])
    if "eval_split_dir" in job:
        cmd.extend(["--split_dir", job["eval_split_dir"]])

    start = time.time()
    try:
        # Reasonable ceiling; long training runs should tune this
        proc = subprocess.run(cmd, capture_output=True, timeout=3600, check=False)
    except subprocess.TimeoutExpired:
        return {
            "ok": False, "error": "training-timeout",
            "duration_s": int(time.time() - start),
        }
    duration = int(time.time() - start)

    if proc.returncode != 0:
        return {
            "ok": False, "error": "training-failed",
            "returncode": proc.returncode,
            "stderr": proc.stderr.decode(errors="replace")[-2000:],
            "duration_s": duration,
        }

    delta = parse_gate_delta(output_dir)
    gate_min = float(job.get("gate_min_improvement", 0.05))
    return {
        "ok": True,
        "gate_passed": delta >= gate_min,
        "gate_score_delta": round(delta, 4),
        "next_version": next_version if delta >= gate_min else skill_version,
        "output_dir": str(output_dir),
        "duration_s": duration,
    }


class Handler(BaseHTTPRequestHandler):
    def _write(self, code: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _authed(self) -> bool:
        if not WORKER_TOKEN:
            return True  # Dev mode: no auth required
        auth = self.headers.get("authorization", "")
        return auth.startswith("Bearer ") and auth[7:] == WORKER_TOKEN

    def do_GET(self) -> None:
        if self.path == "/health":
            self._write(200, {"service": "skillopt-worker", "status": "ok"})
        else:
            self._write(404, {"error": "not-found"})

    def do_POST(self) -> None:
        if self.path != "/train":
            self._write(404, {"error": "not-found"})
            return
        if not self._authed():
            self._write(401, {"error": "unauthorized"})
            return
        length = int(self.headers.get("content-length", "0"))
        if length <= 0 or length > 1_000_000:
            self._write(400, {"error": "bad-body"})
            return
        try:
            job = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self._write(400, {"error": "invalid-json"})
            return
        if not isinstance(job, dict) or not job.get("bot_id"):
            self._write(400, {"error": "missing-bot-id"})
            return
        job_id = str(uuid.uuid4())
        print(f"[{job_id}] training bot={job['bot_id']} v={job.get('skill_version')}", flush=True)
        result = run_training(job)
        result["job_id"] = job_id
        code = 200 if result.get("ok") else 500
        self._write(code, result)

    def log_message(self, fmt: str, *args) -> None:
        # Route access log through print so container log aggregators pick it up
        print(f"[worker] {self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"SkillOpt worker listening on :{PORT} (output_root={OUTPUT_ROOT})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
