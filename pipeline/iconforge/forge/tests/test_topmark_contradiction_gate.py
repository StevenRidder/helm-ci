"""Smoke the topmark contradiction gate.

Run:  python -m forge.tests.test_topmark_contradiction_gate
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import topmark_contradiction_gate


def _row(result: dict, asset: str) -> dict:
    for row in result["rows"]:
        if row["asset"] == asset:
            return row
    raise AssertionError(f"missing asset {asset}")


def _codes(row: dict) -> set[str]:
    return {finding["code"] for finding in row["findings"]}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "topmark_contradiction_gate.json"
        md = Path(tmp) / "topmark_contradiction_gate.md"
        result = topmark_contradiction_gate.build()

        assert result["schema"] == "helm.forge.topmark-contradiction-gate.v1"
        assert result["status"] == "manual_review_required"
        assert result["summary"]["rows"] == 137
        assert result["summary"]["manual_review_required"] >= 4
        assert result["summary"]["finding_counts"]["primary_s101_witness_contradicts_expected_shape"] >= 1
        assert result["summary"]["finding_counts"]["unresolved_shape_is_pass_pending"] >= 2

        topma107 = _row(result, "TOPMA107")
        assert topma107["gate_status"] == "manual_review_required"
        assert "primary_s101_witness_contradicts_expected_shape" in _codes(topma107)
        assert topma107["expected_shape"]["shape_id"] == "TOPSHP19"
        assert topma107["primary_s101_witness"]["id"] == "TOPMAR33"

        topmar87 = _row(result, "TOPMAR87")
        assert "row_name_contradicts_expected_shape" in _codes(topmar87)
        assert "same_asset_s101_witness_contradicts_expected_shape" in _codes(topmar87)

        topmar88 = _row(result, "TOPMAR88")
        assert "row_name_contradicts_expected_shape" in _codes(topmar88)
        assert "same_asset_s101_witness_contradicts_expected_shape" in _codes(topmar88)

        topmar91 = _row(result, "TOPMAR91")
        assert "unresolved_shape_is_pass_pending" in _codes(topmar91)
        assert "human_rejected_is_pass_pending" in _codes(topmar91)

        topmar92 = _row(result, "TOPMAR92")
        assert "unresolved_shape_is_pass_pending" in _codes(topmar92)
        assert "human_rejected_is_pass_pending" in _codes(topmar92)

        topmark_contradiction_gate._write(out, result)
        md.write_text(topmark_contradiction_gate._md(result))
        disk = json.loads(out.read_text())
        assert disk["summary"]["rows"] == 137
        assert "Topmark Contradiction Gate" in md.read_text()

    print("topmark contradiction gate: OK")


if __name__ == "__main__":
    main()
