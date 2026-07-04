"""Smoke the FORGE-14 exact Chart No.1 crop gate.

Run:  python -m forge.tests.test_exact_crop_gate
"""
from __future__ import annotations

from .. import exact_crop_gate


def main():
    result = exact_crop_gate.build()
    summary = result["summary"]
    rows = result["rows"]
    hard_pile = [row for row in rows if not row["final_approval"]]

    assert summary["status"] == "review_required"
    assert summary["gate_assets"] == 362
    assert summary["final_approved"] == 0
    assert summary["hard_pile_entries"] == 362
    assert summary["hard_pile_entries"] == len(hard_pile)
    assert set(summary["status_counts"]) <= set(result["status_taxonomy"])
    assert summary["evidence_counts"]["exact_symbol_crop"] == 139
    assert summary["evidence_counts"]["class_panel_reference"] == 20
    assert summary["evidence_counts"]["multi_symbol_reference"] == 175
    assert summary["evidence_counts"]["manual_exception"] == 28
    assert summary["status_counts"] == {
        "class_reference_only": 16,
        "commons_pd_candidate_needs_review": 20,
        "exact_crop_failed_verifier": 139,
        "license_blocked_reference_only": 23,
        "manual_exception": 28,
        "multi_symbol_reference_only": 136,
    }

    approved = [row for row in rows if row["status"] == "exact_crop_approved"]
    assert len(approved) == 0
    assert all(row["reference_evidence_status"] == "exact_symbol_crop" for row in approved)
    assert all(row["final_approval"] for row in approved)

    failed_exact = [row for row in rows if row["status"] == "exact_crop_failed_verifier"]
    assert len(failed_exact) == 139
    assert failed_exact[0]["asset"] == "TOPMA100"
    assert "wrong_silhouette_or_symbol_body" in failed_exact[0]["reason_codes"]

    for row in rows:
        if row["reference_evidence_status"] in {"class_panel_reference", "multi_symbol_reference"}:
            assert not row["final_approval"]
            assert row["status"] != "exact_crop_approved"
        assert "OpenCPN GPL rastersymbol sprites" in row["forbidden_sources"]
        assert row["strict_invariants"], row["asset"]

    assert any(row["status"] == "commons_pd_candidate_needs_review" for row in rows)
    assert any(row["status"] == "license_blocked_reference_only" for row in rows)
    assert any(row["status"] == "manual_exception" for row in rows)
    assert any(row["status"] == "multi_symbol_reference_only" for row in rows)
    assert any(row["status"] == "class_reference_only" for row in rows)
    print("exact crop gate: OK")


if __name__ == "__main__":
    main()
