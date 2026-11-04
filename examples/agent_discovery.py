#!/usr/bin/env python3
"""
agent_discovery.py — demo of an AI agent consuming evo-skillopt's
self-discovery surface and then calling the API.

A realistic mental model for how an LLM-powered coding assistant or
autonomous agent interacts with a service it just discovered:

    1. GET / → service card (name, version, endpoint summary, docs)
    2. GET /.well-known/agents.json → machine-readable capabilities
    3. Pick the right endpoint from the manifest
    4. Call it with proper auth

Run against a locally-running worker:

    WORKER_TOKEN=dev-token python3 worker/skillopt_worker.py &
    python3 examples/agent_discovery.py

Or against a remote one:

    EVO_URL=https://your-app.fly.dev \\
    EVO_TOKEN=... \\
    python3 examples/agent_discovery.py

Stdlib only — intentionally no third-party HTTP client, so this can
be a copy-paste starting point for any language that has urllib.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

BASE = os.environ.get("EVO_URL", "http://localhost:9000").rstrip("/")
TOKEN = os.environ.get("EVO_TOKEN") or os.environ.get("WORKER_TOKEN", "")


def _get(path: str) -> Any:
    """GET a discovery path and return parsed JSON (or raw text for text/*)."""
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read()
        ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype:
        return json.loads(body)
    return body.decode("utf-8", errors="replace")


def _post(path: str, payload: dict) -> dict:
    """POST JSON with bearer auth; return parsed JSON response."""
    url = f"{BASE}{path}"
    data = json.dumps(payload).encode()
    headers = {"content-type": "application/json"}
    if TOKEN:
        headers["authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, method="POST", data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        try:
            return {"_status": exc.code, **json.loads(body)}
        except json.JSONDecodeError:
            return {"_status": exc.code, "_body": body[:500]}


def main() -> int:
    print(f"→ discovering {BASE}")
    print()

    # Step 1: service card
    card = _get("/")
    print("1. service card:")
    print(f"   service:     {card['service']}")
    print(f"   version:     {card['version']}")
    print(f"   docs:        {card['docs']}")
    print(f"   endpoints:   {len(card['endpoints'])} declared")
    print()

    # Step 2: capabilities manifest
    manifest = _get("/.well-known/agents.json")
    print("2. manifest:")
    print(f"   license:     {manifest['license']}")
    print(f"   keywords:    {', '.join(manifest['keywords'][:5])}, ...")
    print("   endpoints:")
    for ep in manifest["endpoints"]:
        auth = ep.get("auth", "none")
        idem = "idempotent" if ep.get("idempotent") else "non-idempotent"
        print(f"     {ep['method']:<4} {ep['path']:<34} ({auth}, {idem})")
    print()

    # Step 3: pick an endpoint. For the demo we use /fitness/arm — a pure
    # aggregator that doesn't shell out to the trainer, so it's safe to
    # call without any real bot data.
    fitness_endpoint = next(
        (e for e in manifest["endpoints"] if e["path"] == "/fitness/arm"),
        None,
    )
    if not fitness_endpoint:
        print("✗ /fitness/arm not advertised by this worker — stopping.")
        return 1

    # Step 4: call it with a toy payload
    print(f"3. calling {fitness_endpoint['method']} {fitness_endpoint['path']}")
    response = _post(
        "/fitness/arm",
        {
            "bot_id": "demo/agent-discovery",
            "signals": [
                {"bucket": "acquire", "delta": 1.0, "kind": "trial_started"},
                {"bucket": "retain", "delta": 0.5, "kind": "csat_5"},
                {"bucket": "monetize", "delta": 2.0, "kind": "plan_upgrade"},
            ],
            "weights": {"acquire": 0.3, "retain": 0.5, "monetize": 0.2},
        },
    )
    print("   response:")
    print(json.dumps(response, indent=4))
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
