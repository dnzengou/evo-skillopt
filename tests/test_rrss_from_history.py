"""Tests for the training-run → RRSS-inputs adapter."""
from __future__ import annotations

import json
from pathlib import Path

from rrss_from_history import derive_inputs


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class TestDeriveInputs:
    def test_missing_files_return_empty_inputs(self, tmp_path):
        result = derive_inputs(tmp_path)
        assert result.per_item_scores == []
        assert result.repeated_scores == []
        assert result.scores_by_category == {}
        assert result.prev_pass == []
        assert result.cand_pass == []

    def test_reads_current_rollouts(self, tmp_path):
        _write_jsonl(
            tmp_path / "rollouts" / "current.jsonl",
            [
                {"score": 0.9, "category": "faq"},
                {"score": 0.4, "category": "billing"},
                {"score": 0.7, "category": "faq"},
            ],
        )
        result = derive_inputs(tmp_path, pass_threshold=0.5)
        assert result.per_item_scores == [0.9, 0.4, 0.7]
        assert result.scores_by_category == {"faq": [0.9, 0.7], "billing": [0.4]}

    def test_missing_category_bucketed_as_uncategorized(self, tmp_path):
        _write_jsonl(
            tmp_path / "rollouts" / "current.jsonl",
            [{"score": 0.6}, {"score": 0.8}],
        )
        result = derive_inputs(tmp_path)
        assert "_uncategorized" in result.scores_by_category
        assert result.scores_by_category["_uncategorized"] == [0.6, 0.8]

    def test_malformed_row_skipped(self, tmp_path):
        path = tmp_path / "rollouts" / "current.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"score": 0.7}\nnot-json\n{"score": 0.3}\n')
        result = derive_inputs(tmp_path)
        assert result.per_item_scores == [0.7, 0.3]

    def test_reads_history_for_repeated_scores(self, tmp_path):
        _write_json(
            tmp_path / "history.json",
            {"steps": [{"val_reward": 0.6}, {"val_reward": 0.7}, {"val_reward": 0.65}]},
        )
        result = derive_inputs(tmp_path)
        assert result.repeated_scores == [0.6, 0.7, 0.65]

    def test_stabilize_pairs_only_when_lengths_match(self, tmp_path):
        _write_jsonl(
            tmp_path / "rollouts" / "current.jsonl",
            [{"score": 0.9}, {"score": 0.8}, {"score": 0.4}],
        )
        prev_path = tmp_path / "prev.jsonl"
        _write_jsonl(prev_path, [{"score": 0.9}, {"score": 0.4}, {"score": 0.6}])
        result = derive_inputs(tmp_path, prev_rollouts_path=prev_path, pass_threshold=0.5)
        # prev_pass: [T, F, T]; cand_pass: [T, T, F]
        assert result.prev_pass == [True, False, True]
        assert result.cand_pass == [True, True, False]

    def test_stabilize_dropped_on_length_mismatch(self, tmp_path):
        _write_jsonl(
            tmp_path / "rollouts" / "current.jsonl",
            [{"score": 0.9}, {"score": 0.8}],
        )
        prev_path = tmp_path / "prev.jsonl"
        _write_jsonl(prev_path, [{"score": 0.9}])
        result = derive_inputs(tmp_path, prev_rollouts_path=prev_path)
        # Length mismatch → both dropped so compute_rrss doesn't raise
        assert result.prev_pass == []
        assert result.cand_pass == []
