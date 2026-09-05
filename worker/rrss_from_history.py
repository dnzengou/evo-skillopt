"""Derive RRSS axis inputs from a training run's on-disk outputs.

Closes the gap between the abstract RRSS gate (``rrss_gate.compute_rrss``)
and what a real training run actually produces. Reads:

* ``history.json``  — per-epoch aggregate metrics (val_reward, etc.)
* ``rollouts/*.jsonl``  (optional) — per-item outcomes for the current
  and previous versions, so we can compute Stabilize.

Everything is best-effort: missing files or malformed rows fall back to
empty inputs, and ``compute_rrss`` treats those as safe defaults. That
keeps the RRSS overlay from failing a training run just because the
rollout dumper hasn't landed yet.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RRSSInputs:
    """Inputs shaped for ``rrss_gate.compute_rrss``."""

    per_item_scores: list[float]
    repeated_scores: list[float]
    scores_by_category: dict[str, list[float]]
    prev_pass: list[bool]
    cand_pass: list[bool]


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # skip malformed rows rather than fail the whole gate
    except OSError:
        return []
    return rows


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def derive_inputs(
    output_dir: Path,
    *,
    prev_rollouts_path: Path | None = None,
    pass_threshold: float = 0.5,
) -> RRSSInputs:
    """Read the run's outputs and shape them for ``compute_rrss``.

    Conventions this expects (all optional — missing files degrade to
    empty inputs):

    * ``<output_dir>/rollouts/current.jsonl`` — one row per eval item:
      ``{"score": 0.83, "category": "billing"}``.
    * ``<output_dir>/history.json`` — the trainer's per-epoch summary;
      ``steps[*].val_reward`` seeds ``repeated_scores`` across epochs.
    * ``prev_rollouts_path`` — same shape as ``current.jsonl`` for the
      previously-accepted skill. Used only for Stabilize.
    """
    output_dir = Path(output_dir)
    current_rows = _read_jsonl(output_dir / "rollouts" / "current.jsonl")

    per_item_scores: list[float] = []
    scores_by_category: dict[str, list[float]] = {}
    cand_pass: list[bool] = []
    for row in current_rows:
        try:
            score = float(row.get("score", 0.0))
        except (TypeError, ValueError):
            continue
        per_item_scores.append(score)
        cand_pass.append(score >= pass_threshold)
        cat = str(row.get("category", "")) or "_uncategorized"
        scores_by_category.setdefault(cat, []).append(score)

    history = _read_json(output_dir / "history.json")
    repeated_scores: list[float] = []
    for step in history.get("steps", []) or []:
        try:
            repeated_scores.append(float(step.get("val_reward", 0.0)))
        except (TypeError, ValueError):
            continue

    prev_pass: list[bool] = []
    if prev_rollouts_path is not None:
        for row in _read_jsonl(prev_rollouts_path):
            try:
                score = float(row.get("score", 0.0))
            except (TypeError, ValueError):
                continue
            prev_pass.append(score >= pass_threshold)
        # Align: if lengths differ we drop prev_pass to avoid a spurious
        # ValueError from stabilize_score. Callers see stabilize=1.0.
        if len(prev_pass) != len(cand_pass):
            prev_pass = []

    return RRSSInputs(
        per_item_scores=per_item_scores,
        repeated_scores=repeated_scores,
        scores_by_category=scores_by_category,
        prev_pass=prev_pass,
        cand_pass=cand_pass if prev_pass else [],
    )
