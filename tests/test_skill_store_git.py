"""Tests for the opt-in git-tracked audit trail in skill_store.

These tests require ``git`` on PATH. They skip gracefully if not.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_WORKER_DIR = Path(__file__).resolve().parent.parent / "worker"
if str(_WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(_WORKER_DIR))

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git not available"
)


@pytest.fixture
def git_store(tmp_path, monkeypatch):
    """Turn on git tracking and point the store at a tmp dir."""
    import skill_store as m  # noqa: PLC0415

    monkeypatch.setattr(m, "SKILL_STORE_ROOT", tmp_path)
    monkeypatch.setattr(m, "SKILL_STORE_USE_GIT", True)
    return m, tmp_path


def _git_log(bot_dir: Path) -> list[str]:
    res = subprocess.run(
        ["git", "log", "--pretty=%s"],
        cwd=str(bot_dir), capture_output=True, text=True, check=True,
    )
    return [line for line in res.stdout.splitlines() if line]


class TestGitIntegration:
    def test_put_version_creates_commits(self, git_store):
        m, tmp = git_store
        m.put_version("acme/bot", "0.1.0", "# v0\n", root=tmp)
        bot_dir = tmp / "acme-bot"
        assert (bot_dir / ".git").exists()
        subjects = _git_log(bot_dir)
        # Two commits: the skill and the history-append.
        assert any("skill v0.1.0" in s for s in subjects)
        assert any("history: v0.1.0" in s for s in subjects)

    def test_history_entry_has_sha(self, git_store):
        m, tmp = git_store
        m.put_version("acme/bot", "0.1.0", "# v0\n", root=tmp)
        history = m.list_versions("acme/bot", root=tmp)
        assert len(history) == 1
        entry = history[0]
        assert "sha" in entry
        assert len(entry["sha"]) >= 7
        assert all(c in "0123456789abcdef" for c in entry["sha"])

    def test_rollback_appears_in_git_log(self, git_store):
        m, tmp = git_store
        m.put_version("acme/bot", "0.1.0", "# a\n", root=tmp)
        m.put_version("acme/bot", "0.1.1", "# b\n", root=tmp)
        m.rollback("acme/bot", "0.1.0", note="regression", root=tmp)
        bot_dir = tmp / "acme-bot"
        subjects = _git_log(bot_dir)
        assert any("rollback" in s and "v0.1.0" in s for s in subjects)

    def test_git_off_still_works(self, tmp_path, monkeypatch):
        """With SKILL_STORE_USE_GIT=False we must NOT create a git repo."""
        import skill_store as m  # noqa: PLC0415

        monkeypatch.setattr(m, "SKILL_STORE_ROOT", tmp_path)
        monkeypatch.setattr(m, "SKILL_STORE_USE_GIT", False)
        m.put_version("acme/bot", "0.1.0", "# v0\n", root=tmp_path)
        assert not (tmp_path / "acme-bot" / ".git").exists()
        history = m.list_versions("acme/bot", root=tmp_path)
        assert "sha" not in history[0]

    def test_rollback_sha_persisted_in_history(self, git_store):
        m, tmp = git_store
        m.put_version("acme/bot", "0.1.0", "# a\n", root=tmp)
        m.put_version("acme/bot", "0.1.1", "# b\n", root=tmp)
        m.rollback("acme/bot", "0.1.0", root=tmp)
        history = m.list_versions("acme/bot", root=tmp)
        rollback_entry = history[-1]
        assert rollback_entry["source"] == "rollback"
        assert "sha" in rollback_entry
