"""Smoke FORGE-47 Electronic Chart 1 runtime promotion gate.

Run:
  python3 -m forge.tests.test_electronic_chart1_runtime_promotion_gate
"""
from __future__ import annotations

import copy
import tempfile
from pathlib import Path

from .. import electronic_chart1_proof_bundle
from .. import electronic_chart1_runtime_promotion_gate as gate


def _temp_proof_bundle(tmp: Path) -> Path:
    proof_dir = tmp / "proof"
    electronic_chart1_proof_bundle.build_bundle(
        out_dir=proof_dir,
        catalog_json_path=None,
        catalog_markdown_path=None,
        copy_images=False,
    )
    return proof_dir


def _make_green(row: dict) -> dict:
    green = copy.deepcopy(row)
    green["status"] = "proof_row"
    green["gates"]["visual"] = {"gate": "green", "reason_codes": []}
    green["gates"]["semantic"] = {"gate": "green", "reason_codes": []}
    green["gates"]["proof"] = {"gate": "green", "reason_codes": [], "runtime_promoted": False, "runtime_promotion_allowed": True}
    green["gates"]["runtime"] = {
        "runtime_eligible": True,
        "runtime_promotion_allowed": True,
        "fail_closed": False,
    }
    green["gates"]["authority_status"] = "authority_text_ready"
    green["gates"]["human_review_status"] = "approved"
    green["review_controls"]["runtime_approval_allowed"] = False
    green["standards"]["s101"]["present"] = True
    green["standards"]["s101"]["trace"]["classification"] = "direct"
    green["standards"]["s101"]["trace"]["db_backed"] = True
    green["standards"]["s101"]["trace"]["filename_only_match"] = False
    green["display"]["helm_interpretation"]["clean_room_boundary"] = "backend clean-room boundary"
    return green


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        proof_dir = _temp_proof_bundle(Path(tmp_dir))
        payload = gate.build_promotion_gate(proof_dir=proof_dir)

    assert payload["schema"] == "helm.forge.electronic_chart1_runtime_promotion_gate.v1"
    assert payload["status"] == "fail_closed"
    assert payload["summary"]["authority_rows"] == 3057
    assert payload["summary"]["proof_rows"] == 2359
    assert payload["summary"]["hard_pile_rows"] == 698
    assert payload["summary"]["backend_runtime_eligible_rows"] == 0
    assert payload["summary"]["backend_runtime_promotion_allowed_rows"] == 0
    assert payload["summary"]["runtime_export_rows"] == 0
    assert payload["summary"]["blocked_rows"] == 3057
    assert payload["runtime_export"]["rows"] == []
    assert payload["runtime_export"]["status"] == "fail_closed"
    assert "runtime_gate:runtime_eligible_false" in payload["summary"]["reason_counts"]
    assert "human_review_status:needs_human_review" in payload["summary"]["reason_counts"]
    assert "proof_bundle:hard_pile" in payload["summary"]["reason_counts"]
    assert all(row["reason_codes"] for row in payload["blocked_rows"])
    assert all(row["remediation_hints"] for row in payload["blocked_rows"])

    first_blocked = payload["blocked_rows"][0]
    assert first_blocked["source_hashes"]["day"]["helm_s57"]["source_sha256"]
    assert first_blocked["source_hashes"]["day"]["visual_diff"]["source_sha256"]
    assert first_blocked["s101_trace"]["filename_only_match"] is False

    with tempfile.TemporaryDirectory() as tmp_dir:
        proof_dir = _temp_proof_bundle(Path(tmp_dir))
        _, proof_rows, _, _ = gate._load_proof_bundle(proof_dir)  # noqa: SLF001 - contract-level mutation test.

    ui_only = copy.deepcopy(proof_rows[0])
    ui_only["gates"]["human_review_status"] = "approved"
    ui_only["review_controls"]["runtime_approval_allowed"] = True
    ui_decision = gate._promotion_decision(ui_only)  # noqa: SLF001
    assert not ui_decision["eligible"]
    assert "review_controls:ui_runtime_approval_forbidden" in ui_decision["reason_codes"]
    assert "runtime_gate:runtime_eligible_false" in ui_decision["reason_codes"]

    filename_only = _make_green(proof_rows[0])
    filename_only["standards"]["s101"]["trace"]["filename_only_match"] = True
    filename_decision = gate._promotion_decision(filename_only)  # noqa: SLF001
    assert not filename_decision["eligible"]
    assert filename_decision["reason_codes"] == ["s101_trace:filename_only_match_forbidden"]

    fully_green = _make_green(proof_rows[0])
    green_decision = gate._promotion_decision(fully_green)  # noqa: SLF001
    assert green_decision["eligible"], green_decision["reason_codes"]
    runtime_row = gate._runtime_row(fully_green, {"proof_rows_sha256": "abc"})  # noqa: SLF001
    assert runtime_row["render_trace"]["day"]["helm_s57"]["source_sha256"]
    assert runtime_row["s101_trace"]["db_backed"] is True

    print("electronic Chart 1 runtime promotion gate: OK")


if __name__ == "__main__":
    main()
