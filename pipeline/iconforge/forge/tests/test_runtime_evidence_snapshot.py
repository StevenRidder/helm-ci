"""Smoke the FORGE-37 runtime-evidence snapshot.

Run:  python3 -m forge.tests.test_runtime_evidence_snapshot
"""
from __future__ import annotations

import json

from .. import runtime_evidence_snapshot


def main() -> None:
    saved = json.loads(runtime_evidence_snapshot.SNAPSHOT_JSON.read_text())
    saved_mtime = runtime_evidence_snapshot.SNAPSHOT_JSON.stat().st_mtime_ns

    payload = runtime_evidence_snapshot.build_snapshot(write_reports=False)
    assert payload["schema"] == "helm.iconforge.runtime_evidence_snapshot.v1"
    assert payload["status"] == "snapshot_ready"
    assert payload["policy"]["browser_business_logic_allowed"] is False
    assert payload["policy"]["visual_or_svg_inputs_used"] is False
    assert payload["summary"]["review_rows"] == 3057
    assert payload["summary"]["snapshot_rows"] == 3057
    assert payload["summary"]["runtime_rows"] == 0
    assert payload["summary"]["hard_pile_rows"] == 3057
    assert payload["summary"]["runtime_eligible_db_rows"] == 0
    assert payload["summary"]["runtime_state_counts"]["runtime_blocked"] == 3057
    assert payload["summary"]["matches_runtime_promotion_gate"] is True
    assert payload["summary"]["mismatch_rows"] == []
    assert payload["summary"]["warning_only_rows"] == 0
    assert payload["summary"]["runtime_effect_counts"]["blocks_runtime"] == 17326
    assert payload["summary"]["blocker_category_counts"]["runtime_eligibility_blocker"] == 3057
    assert payload["summary"]["blocker_category_counts"]["visual_human_approval_blocker"] == 3057
    assert payload["summary"]["blocker_category_counts"]["s101_feature_catalogue_source_missing"] == 2043

    rows = {row["symbol_id"]: row for row in payload["rows"]}
    boylat25 = rows["BOYLAT25"]
    assert boylat25["runtime_state"] == "runtime_blocked"
    assert boylat25["fail_closed"] is True
    assert boylat25["runtime_record"]["present_in_hard_pile"] is True
    assert boylat25["runtime_record"]["present_in_runtime_export"] is False
    assert boylat25["review_gates"]["visual_human_approval_blocked"] is True
    assert boylat25["blocker_categories"]["runtime_eligibility_blocker"] == 1
    assert "authority_trace:runtime_candidate_not_eligible" in boylat25["runtime_gate_reason_codes"]
    assert any(
        item["blocker_category"] == "s101_feature_catalogue_source_missing"
        and item["evidence"]["parse_status"] == "missing"
        for item in boylat25["authority_source_evidence"]
    )
    assert any("S-101 FeatureCatalogue.xml" in hint for hint in boylat25["remediation_hints"])

    topmark = rows["TOPSHQ28"]
    assert topmark["runtime_state"] == "runtime_blocked"
    assert topmark["blocker_categories"]["visual_special_case_blocker"] >= 1

    non_s101 = rows["VRMEBL01"]
    assert non_s101["blocker_categories"]["non_s101_scope_boundary"] >= 1

    assert saved == payload
    assert runtime_evidence_snapshot.SNAPSHOT_JSON.read_text() == runtime_evidence_snapshot.canonical_json(payload)
    assert runtime_evidence_snapshot.SNAPSHOT_JSON.stat().st_mtime_ns == saved_mtime
    assert saved["summary"]["matches_runtime_promotion_gate"] is True
    assert runtime_evidence_snapshot.SNAPSHOT_MD.exists()

    print("runtime evidence snapshot: OK")


if __name__ == "__main__":
    main()
