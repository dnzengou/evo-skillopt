"""OUTPUT_ROOT retention — keep N most-recent evolution dirs per bot.

Training runs write to ``<OUTPUT_ROOT>/<slug>-v<version>-<ts>/``. Over
weeks of evolutions that directory tree grows unboundedly, eating disk
until the volume fills and training crashes with no space. This module
deletes the oldest run dirs per bot while keeping the most-recent N.

Keep-count is set with ``OUTPUT_RETENTION_PER_BOT`` (default 30). The
retention sweep runs opportunistically after each ``/train`` so there's
no new scheduler to operate.

Design properties
-----------------
- Pure stdlib (``pathlib``, ``shutil``, ``time``).
- Idempotent: a second sweep over a pruned tree is a no-op.
- Path-escape safe: only entries directly under ``root`` are considered,
  only ones whose names match the ``<slug>-v<ver>-<ts>`` pattern are
  touched, and nothing outside ``root`` is ever removed.
- Observable: returns a summary dict the caller can log or surface in
  the ``/train`` response.
- Graceful: a single removal failure doesn't abort the sweep; the
  summary records how many failed.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

# <slug>-v<ver>-<ts> — must match what skillopt_worker.run_training writes.
RUN_DIR_RE = re.compile(r"^(?P<slug>[a-z0-9._-]+)-v\d+\.\d+\.\d+-\d+$")

DEFAULT_KEEP_PER_BOT = int(os.environ.get("OUTPUT_RETENTION_PER_BOT", "30"))


@dataclass
class RetentionReport:
    """Summary of one retention sweep."""

    root: str
    keep_per_bot: int
    examined: int = 0       # total run-dirs seen
    kept: int = 0           # left in place
    pruned: int = 0         # successfully removed
    failed: int = 0         # tried but could not remove
    bots_seen: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "keep_per_bot": self.keep_per_bot,
            "examined": self.examined,
            "kept": self.kept,
            "pruned": self.pruned,
            "failed": self.failed,
            "bots_seen": sorted(self.bots_seen),
        }


def _group_by_slug(root: Path) -> dict[str, list[Path]]:
    """Index entries directly under root by parsed slug."""
    buckets: dict[str, list[Path]] = {}
    try:
        for child in root.iterdir():
            if not child.is_dir():
                continue
            m = RUN_DIR_RE.match(child.name)
            if not m:
                continue
            buckets.setdefault(m["slug"], []).append(child)
    except OSError:
        return {}
    return buckets


def _order_oldest_first(dirs: list[Path]) -> list[Path]:
    """Order a bot's run dirs oldest-first by the trailing timestamp."""
    def _ts(p: Path) -> int:
        try:
            return int(p.name.rsplit("-", 1)[-1])
        except (ValueError, IndexError):
            return 0
    return sorted(dirs, key=_ts)


def prune(
    root: str | Path | None = None,
    keep_per_bot: int | None = None,
) -> RetentionReport:
    """Keep the most-recent ``keep_per_bot`` run dirs per bot; delete the rest.

    Returns a RetentionReport. Never raises for a missing root or a
    failed delete — those are surfaced in the report counters instead.
    """
    if root is None:
        root = os.environ.get("OUTPUT_ROOT", "outputs/evo")
    root_path = Path(root).resolve()
    keep = keep_per_bot if keep_per_bot is not None else DEFAULT_KEEP_PER_BOT
    report = RetentionReport(root=str(root_path), keep_per_bot=keep)

    if not root_path.exists() or not root_path.is_dir():
        return report

    for slug, dirs in _group_by_slug(root_path).items():
        report.bots_seen.add(slug)
        report.examined += len(dirs)
        ordered = _order_oldest_first(dirs)
        n_prune = max(0, len(ordered) - keep)
        for target in ordered[:n_prune]:
            try:
                target.resolve().relative_to(root_path)
            except ValueError:
                report.failed += 1
                continue
            try:
                shutil.rmtree(target)
                report.pruned += 1
            except OSError:
                report.failed += 1
        report.kept += len(ordered) - n_prune
    return report
