"""Tests for the worker.skill_store module."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_WORKER_DIR = Path(__file__).resolve().parent.parent / "worker"
if str(_WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(_WORKER_DIR))

from skill_store import (  # noqa: E402
    StoreError,
    diff_skills,
    get_current,
    get_skill,
    list_versions,
    put_version,
    rollback,
    slugify,
)


@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    """Point the store at a tmp dir for the test."""
    import skill_store as m  # noqa: PLC0415
    monkeypatch.setattr(m, "SKILL_STORE_ROOT", tmp_path)
    return tmp_path


class TestSlugify:
    def test_simple(self):
        assert slugify("acme/support-bot") == "acme-support-bot"

    def test_lowercases(self):
        assert slugify("Acme/Bot") == "acme-bot"

    @pytest.mark.parametrize("bad", ["", "..", "../etc/passwd", "a b c", "sym#bol", "x" * 101])
    def test_rejects_bad(self, bad):
        with pytest.raises(StoreError):
            slugify(bad)


class TestPutAndGet:
    def test_put_then_get_current(self, tmp_store):
        put_version("acme/bot", "0.1.0", "## v0\n", root=tmp_store)
        assert get_current("acme/bot", root=tmp_store) == "0.1.0"
        assert get_skill("acme/bot", root=tmp_store) == "## v0\n"

    def test_put_moves_current_forward(self, tmp_store):
        put_version("acme/bot", "0.1.0", "a", root=tmp_store)
        put_version("acme/bot", "0.1.1", "b", root=tmp_store)
        assert get_current("acme/bot", root=tmp_store) == "0.1.1"
        assert get_skill("acme/bot", "0.1.0", root=tmp_store) == "a"
        assert get_skill("acme/bot", "0.1.1", root=tmp_store) == "b"

    def test_versions_are_immutable(self, tmp_store):
        put_version("acme/bot", "0.1.0", "original", root=tmp_store)
        with pytest.raises(StoreError, match="immutable"):
            put_version("acme/bot", "0.1.0", "DIFFERENT", root=tmp_store)

    def test_same_content_is_idempotent(self, tmp_store):
        put_version("acme/bot", "0.1.0", "x", root=tmp_store)
        put_version("acme/bot", "0.1.0", "x", root=tmp_store)  # no raise
        assert get_skill("acme/bot", "0.1.0", root=tmp_store) == "x"

    def test_invalid_version_rejected(self, tmp_store):
        with pytest.raises(StoreError):
            put_version("acme/bot", "v1", "x", root=tmp_store)
        with pytest.raises(StoreError):
            put_version("acme/bot", "0.1", "x", root=tmp_store)


class TestHistory:
    def test_history_appended_in_order(self, tmp_store):
        put_version("acme/bot", "0.1.0", "a", gate_score_delta=0.0, source="import", root=tmp_store)
        put_version("acme/bot", "0.1.1", "b", gate_score_delta=0.07, source="/train", root=tmp_store)
        h = list_versions("acme/bot", root=tmp_store)
        assert [e["version"] for e in h] == ["0.1.0", "0.1.1"]
        assert h[1]["gate_score_delta"] == 0.07
        assert h[1]["source"] == "/train"


class TestRollback:
    def test_rollback_moves_current(self, tmp_store):
        put_version("acme/bot", "0.1.0", "a", root=tmp_store)
        put_version("acme/bot", "0.1.1", "b", root=tmp_store)
        put_version("acme/bot", "0.1.2", "c", root=tmp_store)
        assert get_current("acme/bot", root=tmp_store) == "0.1.2"

        entry = rollback("acme/bot", "0.1.0", note="regression", root=tmp_store)
        assert entry.version == "0.1.0"
        assert entry.source == "rollback"
        assert get_current("acme/bot", root=tmp_store) == "0.1.0"
        assert get_skill("acme/bot", root=tmp_store) == "a"

    def test_rollback_to_unknown_version_raises(self, tmp_store):
        put_version("acme/bot", "0.1.0", "a", root=tmp_store)
        with pytest.raises(StoreError, match="version not found"):
            rollback("acme/bot", "0.9.9", root=tmp_store)

    def test_rollback_to_current_raises(self, tmp_store):
        put_version("acme/bot", "0.1.0", "a", root=tmp_store)
        with pytest.raises(StoreError, match="already at"):
            rollback("acme/bot", "0.1.0", root=tmp_store)

    def test_rollback_records_history_entry(self, tmp_store):
        put_version("acme/bot", "0.1.0", "a", root=tmp_store)
        put_version("acme/bot", "0.1.1", "b", root=tmp_store)
        rollback("acme/bot", "0.1.0", note="ouch", root=tmp_store)
        h = list_versions("acme/bot", root=tmp_store)
        assert h[-1]["source"] == "rollback"
        assert h[-1]["version"] == "0.1.0"
        assert "ouch" in h[-1]["note"]


class TestDiff:
    def test_diff_basic(self, tmp_store):
        put_version("acme/bot", "0.1.0", "one\ntwo\nthree\n", root=tmp_store)
        put_version("acme/bot", "0.1.1", "one\ntwo\nTHREE\nfour\n", root=tmp_store)
        patch = diff_skills("acme/bot", "0.1.0", "0.1.1", root=tmp_store)
        assert "--- v0.1.0.md" in patch
        assert "+++ v0.1.1.md" in patch
        assert "-three" in patch
        assert "+THREE" in patch
        assert "+four" in patch

    def test_diff_identical_is_empty(self, tmp_store):
        put_version("acme/bot", "0.1.0", "same\n", root=tmp_store)
        put_version("acme/bot", "0.1.1", "same\n", root=tmp_store)
        assert diff_skills("acme/bot", "0.1.0", "0.1.1", root=tmp_store) == ""


class TestPathEscapeProtection:
    def test_slug_rejects_parent_dir(self):
        with pytest.raises(StoreError):
            slugify("../../../etc/passwd")

    def test_slug_rejects_leading_dot(self):
        with pytest.raises(StoreError):
            slugify(".hidden")

    def test_slug_rejects_whitespace(self):
        with pytest.raises(StoreError):
            slugify("foo bar")
