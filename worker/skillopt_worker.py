#!/usr/bin/env python3
"""
evo-skillopt worker — productized SkillOpt training loop as an HTTP service.

Any agent runtime calls `POST /train` with:
  {
    "bot_id":          "author/name",
    "skill_version":   "0.1.4",
    "skill_path":      "/data/bots/author-name/skills/main.md",
    "eval_split_dir":  "/data/bots/author-name/eval",
    "config":          "configs/searchqa/default.yaml",   # or caller-supplied
    "num_epochs":      1
  }

The worker responds with gate outcome + next version. Pure endpoints
(`/train/cascade`, `/fitness/arm`) aggregate pre-computed scores
without shelling out to training.

Agent discovery (unauthenticated, read-only):
  GET /                            — service card JSON (name, endpoints, docs)
  GET /.well-known/agents.json     — machine-readable capabilities manifest
  GET /llms.txt                    — llms.txt-convention LLM crawl aid
  GET /openapi.yaml                — OpenAPI 3.1 contract for every endpoint

These are served from `DISCOVERY_ROOT` (the repo root by default) so any
agent that hits the live worker can self-discover everything it needs
to call the API safely — no out-of-band docs required.

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

# Local, stdlib-only extensions
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from arm_signals import Signal, compute_fitness  # noqa: E402
from cascade import StageResult, evaluate_cascade  # noqa: E402
from rrss_from_history import derive_inputs  # noqa: E402
from rrss_gate import compute_rrss, rrss_gate  # noqa: E402
from skill_store import (  # noqa: E402
    StoreError,
    diff_skills,
    get_current,
    get_skill,
    list_versions,
    rollback as rollback_skill,
)

import metrics as _metrics  # noqa: E402
from log import get_logger  # noqa: E402

log = get_logger("worker")
_metrics.init()

WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "").strip()
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "outputs/evo")).resolve()
TRAIN_SCRIPT = Path(os.environ.get("TRAIN_SCRIPT", "scripts/train.py")).resolve()
PORT = int(os.environ.get("PORT", "9000"))

# Repo root (or whatever directory holds llms.txt + .well-known/).
# In the container this is /app; in dev it's two levels up from this file.
DISCOVERY_ROOT = Path(os.environ.get("DISCOVERY_ROOT", _HERE.parent)).resolve()

# Static files served under /.well-known and the repo-root discovery paths.
# Mapped { request_path: (file_path_relative_to_DISCOVERY_ROOT, content_type) }.
DISCOVERY_FILES = {
    "/llms.txt": ("llms.txt", "text/plain; charset=utf-8"),
    "/llms-full.txt": ("llms-full.txt", "text/plain; charset=utf-8"),
    "/.well-known/agents.json": (".well-known/agents.json", "application/json"),
    "/.well-known/openapi.yaml": (".well-known/openapi.yaml", "application/yaml"),
    "/openapi.yaml": (".well-known/openapi.yaml", "application/yaml"),
    "/AGENTS.md": ("AGENTS.md", "text/markdown; charset=utf-8"),
}

SERVICE_CARD_ENDPOINTS_EXTRA = (
    {"method": "GET", "path": "/metrics", "auth": "none"},
)

SERVICE_CARD = {
    "service": "evo-skillopt",
    "version": "0.2",
    "description": (
        "Text-space skill optimization for production LLM agents. "
        "Evolves a Markdown skill file against a held-out eval set, "
        "over HTTP, without touching model weights."
    ),
    "docs": "https://github.com/dnzengou/evo-skillopt",
    "discovery": {
        "agents_manifest": "/.well-known/agents.json",
        "openapi": "/.well-known/openapi.yaml",
        "llms_txt": "/llms.txt",
        "llms_full": "/llms-full.txt",
        "agent_orientation": "/AGENTS.md",
    },
    "endpoints": [
        {"method": "GET", "path": "/health", "auth": "none"},
        {"method": "GET", "path": "/metrics", "auth": "none"},
        {"method": "POST", "path": "/train", "auth": "bearer"},
        {"method": "POST", "path": "/train/cascade", "auth": "bearer"},
        {"method": "POST", "path": "/fitness/arm", "auth": "bearer"},
        {"method": "GET", "path": "/bots/{id}/skill", "auth": "bearer"},
        {"method": "GET", "path": "/bots/{id}/history", "auth": "bearer"},
        {"method": "GET", "path": "/bots/{id}/diff", "auth": "bearer"},
        {"method": "POST", "path": "/bots/{id}/rollback", "auth": "bearer"},
    ],
}

_BOT_PATH_RE = re.compile(r"^/bots/([^/]+)/(skill|history|diff|rollback)$")

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
        duration_s = time.time() - start
        _metrics.record_training("timeout", duration_s)
        return {
            "ok": False, "error": "training-timeout",
            "duration_s": int(duration_s),
        }
    duration_s = time.time() - start
    duration = int(duration_s)

    if proc.returncode != 0:
        _metrics.record_training("failed", duration_s)
        return {
            "ok": False, "error": "training-failed",
            "returncode": proc.returncode,
            "stderr": proc.stderr.decode(errors="replace")[-2000:],
            "duration_s": duration,
        }

    delta = parse_gate_delta(output_dir)
    gate_min = float(job.get("gate_min_improvement", 0.05))
    base_passed = delta >= gate_min
    result = {
        "ok": True,
        "gate_passed": base_passed,
        "gate_score_delta": round(delta, 4),
        "next_version": next_version if base_passed else skill_version,
        "output_dir": str(output_dir),
        "duration_s": duration,
    }
    _metrics.record_gate("base", base_passed)
    _metrics.record_training("accepted" if base_passed else "rejected", duration_s)

    # Optional RRSS overlay: caller passes ``rrss`` payload with the four
    # axis inputs; the RRSS composite becomes the authoritative gate.
    # If ``rrss.auto_from_history`` is set, inputs are derived from the
    # run's output_dir instead of being passed inline.
    rrss_payload = job.get("rrss")
    if isinstance(rrss_payload, dict):
        if rrss_payload.get("auto_from_history"):
            prev_path = rrss_payload.get("prev_rollouts_path")
            derived = derive_inputs(
                output_dir,
                prev_rollouts_path=Path(prev_path) if prev_path else None,
                pass_threshold=float(rrss_payload.get("pass_threshold", 0.5)),
            )
            per_item_scores = derived.per_item_scores
            repeated_scores = derived.repeated_scores
            scores_by_category = derived.scores_by_category
            prev_pass = derived.prev_pass
            cand_pass = derived.cand_pass
        else:
            per_item_scores = rrss_payload.get("per_item_scores", [])
            repeated_scores = rrss_payload.get("repeated_scores", [])
            scores_by_category = rrss_payload.get("scores_by_category") or {}
            prev_pass = rrss_payload.get("prev_pass", [])
            cand_pass = rrss_payload.get("cand_pass", [])
        components = compute_rrss(
            per_item_scores=per_item_scores,
            repeated_scores=repeated_scores,
            scores_by_category=scores_by_category,
            prev_pass=prev_pass,
            cand_pass=cand_pass,
            weights=rrss_payload.get("weights"),
        )
        decision = rrss_gate(
            components,
            previous_composite=float(rrss_payload.get("previous_composite", 0.0)),
            min_improvement=float(rrss_payload.get("min_improvement", 0.0)),
            axis_floors=rrss_payload.get("axis_floors") or {},
        )
        result["gate_passed"] = decision.passed
        result["next_version"] = next_version if decision.passed else skill_version
        result["rrss"] = {
            "composite": round(components.composite, 4),
            "robustify": round(components.robustify, 4),
            "reliabilify": round(components.reliabilify, 4),
            "solidify": round(components.solidify, 4),
            "stabilize": round(components.stabilize, 4),
            "delta": round(decision.delta, 4),
            "reason": decision.reason,
        }
        _metrics.record_gate("rrss", decision.passed)
    return result


def run_arm_fitness(job: dict) -> dict:
    """Reduce a stream of ARM-bucketed signals to one composite fitness.

    Expected payload:
        {
          "bot_id":  "author/name",
          "signals": [
            {"bucket": "acquire",  "delta": 1.0, "kind": "trial_started"},
            {"bucket": "retain",   "delta": 0.5, "kind": "csat_5"},
            {"bucket": "monetize", "delta": 2.0, "kind": "plan_upgrade"}
          ],
          "weights": {"acquire": 0.3, "retain": 0.5, "monetize": 0.2}
        }

    Pure aggregation — no training, no side effects. Meant to be called
    by upstream systems that collect production signals so they can hand
    the worker a single composite fitness score.
    """
    raw = job.get("signals") or []
    if not isinstance(raw, list):
        return {"ok": False, "error": "arm-missing-signals"}
    try:
        signals = [
            Signal(
                bucket=str(s["bucket"]),  # type: ignore[arg-type]
                delta=float(s["delta"]),
                kind=str(s.get("kind", "")),
            )
            for s in raw
        ]
    except (KeyError, TypeError, ValueError) as exc:
        return {"ok": False, "error": f"arm-bad-signal: {exc}"}
    try:
        fit = compute_fitness(signals, weights=job.get("weights"))
    except ValueError as exc:
        return {"ok": False, "error": f"arm-bad-weights: {exc}"}
    return {
        "ok": True,
        "composite": round(fit.composite, 6),
        "weights": dict(fit.weights),
        "per_bucket": [
            {
                "bucket": s.bucket,
                "count": s.count,
                "sum_delta": round(s.sum_delta, 6),
                "mean_delta": round(s.mean_delta, 6),
            }
            for s in fit.per_bucket
        ],
    }


def run_cascade(job: dict) -> dict:
    """Score a cascade of skills as one behavior contract.

    Expected payload:
        {
          "bot_id":    "author/name",
          "stages": [
            {"name": "filter",    "score": 0.94, "weight": 1.0},
            {"name": "classify",  "score": 0.88},
            {"name": "draft",     "score": 0.91}
          ],
          "aggregation":         "mean" | "min" | "product" | "weighted_mean",
          "aggregate_threshold": 0.85,
          "stage_floor":         0.60
        }

    Per-stage scores must already be produced (e.g. by prior ``/train``
    calls). The cascade endpoint is pure aggregation + gating — it does
    not run training, so it responds in milliseconds and can be called
    from CI to enforce pipeline-level acceptance criteria.
    """
    raw_stages = job.get("stages") or []
    if not isinstance(raw_stages, list) or not raw_stages:
        return {"ok": False, "error": "cascade-missing-stages"}
    try:
        stages = tuple(
            StageResult(
                name=str(s["name"]),
                score=float(s["score"]),
                weight=float(s.get("weight", 1.0)),
                passed=bool(s.get("passed", True)),
            )
            for s in raw_stages
        )
    except (KeyError, TypeError, ValueError) as exc:
        return {"ok": False, "error": f"cascade-bad-stage: {exc}"}
    outcome = evaluate_cascade(
        stages,
        aggregation=job.get("aggregation", "mean"),
        aggregate_threshold=float(job.get("aggregate_threshold", 0.0)),
        stage_floor=float(job.get("stage_floor", 0.0)),
    )
    _metrics.record_gate("cascade", outcome.gate_passed)
    return {
        "ok": True,
        "gate_passed": outcome.gate_passed,
        "aggregate": round(outcome.aggregate, 4),
        "aggregation": outcome.aggregation,
        "reason": outcome.reason,
        "stages": [
            {"name": s.name, "score": round(s.score, 4), "weight": s.weight}
            for s in outcome.stages
        ],
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

    def _write_bytes(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        # Let LLM crawlers and agent registries cache these for a few hours.
        if code == 200:
            self.send_header("cache-control", "public, max-age=3600")
            self.send_header("access-control-allow-origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_discovery(self, path: str) -> bool:
        """Serve a static discovery file; return True if handled."""
        entry = DISCOVERY_FILES.get(path)
        if entry is None:
            return False
        rel, ctype = entry
        fp = (DISCOVERY_ROOT / rel).resolve()
        # Prevent path-escape tricks — must sit under DISCOVERY_ROOT.
        try:
            fp.relative_to(DISCOVERY_ROOT)
        except ValueError:
            self._write(404, {"error": "not-found"})
            return True
        if not fp.exists() or not fp.is_file():
            self._write(404, {"error": "discovery-file-missing", "path": path})
            return True
        try:
            self._write_bytes(200, fp.read_bytes(), ctype)
        except OSError:
            self._write(500, {"error": "discovery-read-failed", "path": path})
        return True

    def _begin(self) -> None:
        self._t0 = time.time()
        _metrics.inflight_inc(self.command or "?", self.path)

    def _finish(self, code: int) -> None:
        dur = time.time() - getattr(self, "_t0", time.time())
        _metrics.inflight_dec(self.command or "?", self.path)
        _metrics.record_request(self.command or "?", self.path, code, dur)
        self._last_code = code

    # Inject around every call by pre/post-hooking do_GET / do_POST.
    def _parse_query(self) -> dict[str, str]:
        from urllib.parse import parse_qs, urlsplit

        q = urlsplit(self.path).query
        out: dict[str, str] = {}
        for k, v in parse_qs(q, keep_blank_values=False).items():
            if v:
                out[k] = v[-1]
        return out

    def _match_bot_path(self) -> tuple[str, str] | None:
        from urllib.parse import urlsplit

        path = urlsplit(self.path).path
        m = _BOT_PATH_RE.match(path)
        if not m:
            return None
        return m.group(1), m.group(2)

    def _handle_bot_get(self, slug: str, verb: str) -> int:
        if not self._authed():
            self._write(401, {"error": "unauthorized"})
            return 401
        qs = self._parse_query()
        try:
            if verb == "skill":
                content = get_skill(slug, version=qs.get("version"))
                current = get_current(slug)
                body = {
                    "bot_id": slug.replace("-", "/"),
                    "version": qs.get("version") or current,
                    "current": current,
                    "skill": content,
                }
                self._write(200, body)
                return 200
            if verb == "history":
                body = {"bot_id": slug.replace("-", "/"),
                        "current": get_current(slug),
                        "versions": list_versions(slug)}
                self._write(200, body)
                return 200
            if verb == "diff":
                f, t = qs.get("from"), qs.get("to")
                if not f or not t:
                    self._write(400, {"error": "diff-requires-from-and-to"})
                    return 400
                patch = diff_skills(slug, f, t)
                self._write_bytes(
                    200,
                    patch.encode(),
                    "text/x-diff; charset=utf-8",
                )
                return 200
        except StoreError as exc:
            self._write(404, {"error": "store-error", "detail": str(exc)})
            return 404
        self._write(404, {"error": "not-found"})
        return 404

    def _handle_bot_rollback(self, slug: str) -> int:
        if not self._authed():
            self._write(401, {"error": "unauthorized"})
            return 401
        qs = self._parse_query()
        # Allow `to` either in query string or JSON body.
        to_version = qs.get("to", "")
        note = qs.get("note", "")
        length = int(self.headers.get("content-length", "0"))
        if length > 0:
            if length > 1_000_000:
                self._write(400, {"error": "bad-body"})
                return 400
            try:
                body = json.loads(self.rfile.read(length))
            except json.JSONDecodeError:
                self._write(400, {"error": "invalid-json"})
                return 400
            if isinstance(body, dict):
                to_version = to_version or str(body.get("to", ""))
                note = note or str(body.get("note", ""))
        if not to_version:
            self._write(400, {"error": "rollback-requires-to"})
            return 400
        try:
            entry = rollback_skill(slug, to_version, note=note)
        except StoreError as exc:
            self._write(404, {"error": "store-error", "detail": str(exc)})
            return 404
        log.info(
            "rollback",
            extra={"bot_id": slug.replace("-", "/"), "to": to_version, "note": note},
        )
        self._write(200, {
            "ok": True,
            "bot_id": slug.replace("-", "/"),
            "rolled_back_to": to_version,
            "entry": entry.to_dict(),
        })
        return 200

    def _dispatch_GET(self) -> int:
        if self.path == "/health":
            self._write(200, {"service": "skillopt-worker", "status": "ok"})
            return 200
        if self.path in ("/", ""):
            self._write(200, SERVICE_CARD)
            return 200
        if self.path == "/metrics":
            body, ctype = _metrics.render_metrics()
            code = 200 if _metrics.is_available() else 503
            self._write_bytes(code, body, ctype)
            return code
        matched = self._match_bot_path()
        if matched and matched[1] in ("skill", "history", "diff"):
            return self._handle_bot_get(*matched)
        if self._serve_discovery(self.path.split("?", 1)[0]):
            return getattr(self, "_last_code", 200)
        self._write(404, {"error": "not-found"})
        return 404

    def _dispatch_POST(self) -> int:
        matched = self._match_bot_path()
        if matched and matched[1] == "rollback":
            return self._handle_bot_rollback(matched[0])
        if self.path.split("?", 1)[0] not in ("/train", "/train/cascade", "/fitness/arm"):
            self._write(404, {"error": "not-found"})
            return 404
        if not self._authed():
            self._write(401, {"error": "unauthorized"})
            return 401
        length = int(self.headers.get("content-length", "0"))
        if length <= 0 or length > 1_000_000:
            self._write(400, {"error": "bad-body"})
            return 400
        try:
            job = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self._write(400, {"error": "invalid-json"})
            return 400
        if not isinstance(job, dict) or not job.get("bot_id"):
            self._write(400, {"error": "missing-bot-id"})
            return 400
        job_id = str(uuid.uuid4())
        if self.path == "/train/cascade":
            log.info(
                "cascade",
                extra={"bot_id": job["bot_id"], "job_id": job_id,
                       "stages": len(job.get("stages") or [])},
            )
            result = run_cascade(job)
        elif self.path == "/fitness/arm":
            log.info(
                "arm",
                extra={"bot_id": job["bot_id"], "job_id": job_id,
                       "signals": len(job.get("signals") or [])},
            )
            result = run_arm_fitness(job)
        else:
            log.info(
                "training",
                extra={"bot_id": job["bot_id"], "job_id": job_id,
                       "version": job.get("skill_version")},
            )
            result = run_training(job)
        result["job_id"] = job_id
        code = 200 if result.get("ok") else 500
        self._write(code, result)
        return code

    def do_GET(self) -> None:
        self._begin()
        self._last_code = 200
        try:
            code = self._dispatch_GET()
        finally:
            self._finish(getattr(self, "_last_code", 500) if "code" not in locals() else code)

    def do_POST(self) -> None:
        self._begin()
        self._last_code = 200
        try:
            code = self._dispatch_POST()
        finally:
            self._finish(getattr(self, "_last_code", 500) if "code" not in locals() else code)

    def log_message(self, fmt: str, *args) -> None:
        log.info("access", extra={"peer": self.address_string(), "line": fmt % args})


if __name__ == "__main__":
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    log.info(
        "worker-start",
        extra={
            "port": PORT, "output_root": str(OUTPUT_ROOT),
            "discovery_root": str(DISCOVERY_ROOT),
            "prometheus": _metrics.is_available(),
        },
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
