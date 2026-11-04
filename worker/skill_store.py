"""Versioned skill storage — the backing store for the rollback endpoints.

Layout under ``SKILL_STORE_ROOT`` (default ``./bots`` or
``/data/bots`` in the container, settable via ``$SKILL_STORE_ROOT``):

    <slug>/
        meta.json                     # { "bot_id": "...", "current": "0.1.3" }
        history.json                  # [ { "version": "...", "ts": 1699..., "gate_score_delta": 0.07, "source": "/train"|"rollback"|"import", "note": "..." }, ... ]
        v0.1.0.md
        v0.1.1.md
        v0.1.2.md

Stdlib only. Append-only on versions; the "current" pointer is the only
thing that moves. A rollback is never destructive — it points `current`
at an older version and records the event in `history.json`.

Slugs are the lowercase, URL-safe transliteration of a bot_id
(``author/name`` → ``author-name``). The slug must match
``^[a-z0-9][a-z0-9._-]*$`` with length 1..100; everything else is
rejected before touching disk.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SKILL_STORE_ROOT = Path(os.environ.get("SKILL_STORE_ROOT", "bots")).resolve()

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class StoreError(Exception):
    """Raised for invalid inputs or missing state."""


@dataclass(frozen=True)
class VersionEntry:
    version: str
    ts: int
    gate_score_delta: float
    source: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "ts": self.ts,
            "gate_score_delta": self.gate_score_delta,
            "source": self.source,
            "note": self.note,
        }


def slugify(bot_id: str) -> str:
    """Turn ``author/name`` into ``author-name``. Raises on bad input."""
    if not isinstance(bot_id, str) or not bot_id:
        raise StoreError("bot_id must be a non-empty string")
    slug = bot_id.strip().lower().replace("/", "-")
    if not _SLUG_RE.match(slug) or len(slug) > 100:
        raise StoreError(f"invalid bot_id slug: {slug!r}")
    return slug


def _validate_slug(slug: str) -> str:
    if not _SLUG_RE.match(slug) or len(slug) > 100:
        raise StoreError(f"invalid slug: {slug!r}")
    return slug


def _validate_version(version: str) -> str:
    if not _VERSION_RE.match(version):
        raise StoreError(f"invalid version: {version!r}")
    return version


def _bot_dir(slug: str, root: Path | None = None) -> Path:
    """Return the directory for this slug, path-escape-safe."""
    base = (root or SKILL_STORE_ROOT).resolve()
    _validate_slug(slug)
    path = (base / slug).resolve()
    # Defence in depth — the slug regex already forbids path separators,
    # but re-check in case SKILL_STORE_ROOT is ever changed to allow them.
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise StoreError("slug escaped store root") from exc
    return path


def _read_json(fp: Path, default: Any) -> Any:
    try:
        return json.loads(fp.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(fp: Path, obj: Any) -> None:
    fp.parent.mkdir(parents=True, exist_ok=True)
    tmp = fp.with_suffix(fp.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    tmp.replace(fp)


def put_version(
    bot_id: str,
    version: str,
    content: str,
    *,
    gate_score_delta: float = 0.0,
    source: str = "import",
    note: str = "",
    set_current: bool = True,
    root: Path | None = None,
) -> VersionEntry:
    """Add a new skill version. Idempotent: writing the same content
    for the same version is a no-op; a different content for the same
    version raises (versions are immutable).

    Returns the recorded VersionEntry.
    """
    slug = slugify(bot_id)
    _validate_version(version)
    bot_dir = _bot_dir(slug, root)
    bot_dir.mkdir(parents=True, exist_ok=True)

    skill_fp = bot_dir / f"v{version}.md"
    if skill_fp.exists():
        existing = skill_fp.read_text()
        if existing != content:
            raise StoreError(
                f"version {version} already exists with different content; "
                "versions are immutable"
            )
    else:
        skill_fp.write_text(content)

    history_fp = bot_dir / "history.json"
    history = _read_json(history_fp, [])
    entry = VersionEntry(
        version=version,
        ts=int(time.time()),
        gate_score_delta=round(float(gate_score_delta), 4),
        source=source,
        note=note,
    )
    # Dedup: don't record the same (version, source) twice in a row.
    if not history or (history[-1].get("version") != version or history[-1].get("source") != source):
        history.append(entry.to_dict())
        _write_json(history_fp, history)

    if set_current:
        _set_current_pointer(slug, version, root=root)
    return entry


def _set_current_pointer(slug: str, version: str, root: Path | None = None) -> None:
    bot_dir = _bot_dir(slug, root)
    meta_fp = bot_dir / "meta.json"
    meta = _read_json(meta_fp, {})
    meta["bot_id"] = meta.get("bot_id") or slug.replace("-", "/")
    meta["current"] = version
    _write_json(meta_fp, meta)


def get_current(bot_id: str, root: Path | None = None) -> str | None:
    slug = slugify(bot_id)
    meta_fp = _bot_dir(slug, root) / "meta.json"
    meta = _read_json(meta_fp, {})
    return meta.get("current")


def get_skill(bot_id: str, version: str | None = None, root: Path | None = None) -> str:
    """Return the skill file text. If version is None, uses the current."""
    slug = slugify(bot_id)
    bot_dir = _bot_dir(slug, root)
    if version is None:
        version = get_current(bot_id, root=root) or ""
    if not version:
        raise StoreError(f"no current skill for {bot_id!r}")
    _validate_version(version)
    fp = bot_dir / f"v{version}.md"
    if not fp.exists():
        raise StoreError(f"version {version} not found for {bot_id!r}")
    return fp.read_text()


def list_versions(bot_id: str, root: Path | None = None) -> list[dict[str, Any]]:
    """Return the history for this bot in chronological order."""
    slug = slugify(bot_id)
    history_fp = _bot_dir(slug, root) / "history.json"
    return list(_read_json(history_fp, []))


def rollback(
    bot_id: str,
    to_version: str,
    *,
    note: str = "",
    root: Path | None = None,
) -> VersionEntry:
    """Point `current` at an existing older version.

    The version must already exist in the store; this never fabricates
    one. Records the rollback in `history.json` so the decision is
    auditable.
    """
    slug = slugify(bot_id)
    bot_dir = _bot_dir(slug, root)
    _validate_version(to_version)
    skill_fp = bot_dir / f"v{to_version}.md"
    if not skill_fp.exists():
        raise StoreError(f"cannot rollback to {to_version}: version not found")
    current = get_current(bot_id, root=root)
    if current == to_version:
        raise StoreError(f"already at {to_version}; nothing to roll back")

    _set_current_pointer(slug, to_version, root=root)

    history_fp = bot_dir / "history.json"
    history = _read_json(history_fp, [])
    entry = VersionEntry(
        version=to_version, ts=int(time.time()),
        gate_score_delta=0.0, source="rollback",
        note=note or (f"rolled back from {current}" if current else ""),
    )
    history.append(entry.to_dict())
    _write_json(history_fp, history)
    return entry


def diff_skills(
    bot_id: str,
    from_version: str,
    to_version: str,
    root: Path | None = None,
) -> str:
    """Return a unified diff between two versions of this bot's skill."""
    from_text = get_skill(bot_id, from_version, root=root)
    to_text = get_skill(bot_id, to_version, root=root)
    return "".join(
        difflib.unified_diff(
            from_text.splitlines(keepends=True),
            to_text.splitlines(keepends=True),
            fromfile=f"v{from_version}.md",
            tofile=f"v{to_version}.md",
            n=3,
        )
    )
