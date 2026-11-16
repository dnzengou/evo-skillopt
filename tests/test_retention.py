"""Tests for OUTPUT_ROOT retention."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_WORKER_DIR = Path(__file__).resolve().parent.parent / "worker"
if str(_WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(_WORKER_DIR))

from retention import RUN_DIR_RE, prune  # noqa: E402


def _mk_run(root: Path, slug: str, version: str, ts: int) -> Path:
    d = root / f"{slug}-v{version}-{ts}"
    d.mkdir(parents=True)
    # drop a fake artifact so rmtree has something to delete
    (d / "history.json").write_text(f'{{"version":"{version}"}}')
    return d


class TestRunDirRegex:
    @pytest.mark.parametrize("name", [
        "acme-bot-v0.1.0-1699999999",
        "foo-v1.2.3-0",
        "x-v99.99.99-1700000000",
    ])
    def test_matches(self, name):
        assert RUN_DIR_RE.match(name) is not None

    @pytest.mark.parametrize("name", [
        "", "random-dir", "v0.1.0-1699", "slug-v1-1699",
        "slug-v0.1.0", "../etc/passwd",
    ])
    def test_rejects(self, name):
        assert RUN_DIR_RE.match(name) is None


class TestPrune:
    def test_empty_root(self, tmp_path):
        rep = prune(tmp_path, keep_per_bot=3)
        assert rep.examined == 0
        assert rep.pruned == 0

    def test_missing_root(self, tmp_path):
        rep = prune(tmp_path / "does-not-exist", keep_per_bot=3)
        assert rep.examined == 0
        assert rep.pruned == 0

    def test_keeps_most_recent_n(self, tmp_path):
        for i, v in enumerate(["0.1.0", "0.1.1", "0.1.2", "0.1.3", "0.1.4"]):
            _mk_run(tmp_path, "acme-bot", v, 1000 + i)
        rep = prune(tmp_path, keep_per_bot=3)
        assert rep.examined == 5
        assert rep.kept == 3
        assert rep.pruned == 2
        assert rep.failed == 0
        kept_versions = sorted(p.name for p in tmp_path.iterdir() if p.is_dir())
        # Oldest two (v0.1.0 and v0.1.1) should have been pruned.
        assert all("v0.1.0-" not in n and "v0.1.1-" not in n for n in kept_versions)
        assert any("v0.1.4-" in n for n in kept_versions)

    def test_idempotent_second_sweep_is_noop(self, tmp_path):
        for i, v in enumerate(["0.1.0", "0.1.1", "0.1.2", "0.1.3"]):
            _mk_run(tmp_path, "acme-bot", v, 2000 + i)
        rep1 = prune(tmp_path, keep_per_bot=2)
        assert rep1.pruned == 2
        rep2 = prune(tmp_path, keep_per_bot=2)
        assert rep2.pruned == 0
        assert rep2.kept == 2

    def test_per_bot_isolation(self, tmp_path):
        for i, v in enumerate(["0.1.0", "0.1.1", "0.1.2", "0.1.3"]):
            _mk_run(tmp_path, "acme-bot", v, 3000 + i)
        for i, v in enumerate(["0.1.0", "0.1.1"]):
            _mk_run(tmp_path, "widget-bot", v, 4000 + i)
        rep = prune(tmp_path, keep_per_bot=2)
        assert rep.pruned == 2  # only acme-bot had extras
        assert rep.kept == 4    # 2 acme + 2 widget
        assert rep.bots_seen == {"acme-bot", "widget-bot"}

    def test_keep_count_exceeds_entries(self, tmp_path):
        _mk_run(tmp_path, "acme-bot", "0.1.0", 5000)
        rep = prune(tmp_path, keep_per_bot=30)
        assert rep.pruned == 0
        assert rep.kept == 1

    def test_ignores_unrelated_dirs(self, tmp_path):
        (tmp_path / "some-random-dir").mkdir()
        (tmp_path / "another").mkdir()
        _mk_run(tmp_path, "acme-bot", "0.1.0", 6000)
        rep = prune(tmp_path, keep_per_bot=3)
        assert rep.examined == 1
        # Random dirs survive untouched
        assert (tmp_path / "some-random-dir").exists()

    def test_report_to_dict(self, tmp_path):
        _mk_run(tmp_path, "acme-bot", "0.1.0", 7000)
        rep = prune(tmp_path, keep_per_bot=3)
        d = rep.to_dict()
        assert set(d) == {"root", "keep_per_bot", "examined", "kept",
                           "pruned", "failed", "bots_seen"}
        assert isinstance(d["bots_seen"], list)
