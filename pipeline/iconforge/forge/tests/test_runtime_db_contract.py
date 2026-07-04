"""Smoke the FORGE-50 runtime DB contract.

Run:  python3 -m forge.tests.test_runtime_db_contract
"""
from __future__ import annotations

import json

from .. import runtime_db_contract


def main() -> None:
    saved = json.loads(runtime_db_contract.CONTRACT_JSON.read_text())
    saved_mtime = runtime_db_contract.CONTRACT_JSON.stat().st_mtime_ns

    payload = runtime_db_contract.build_contract()
    assert payload["schema"] == "helm.iconforge.runtime_db_contract.v1"
    assert payload["status"] == "contract_pass"
    assert payload["summary"]["lookup_rows"] == 3057
    assert payload["summary"]["candidate_rows"] == 3057
    assert payload["summary"]["runtime_eligible_rows"] == 0
    assert payload["summary"]["runtime_symbol_portrayal_rows"] == 0
    assert payload["summary"]["blocker_rows"] == 4410
    assert payload["summary"]["visual_approval_pending_rows"] == 3057
    assert payload["summary"]["candidate_status_counts"] == {
        "blocked": 336,
        "review_candidate": 2721,
    }

    checks = {check["name"]: check for check in payload["checks"]}
    for name in (
        "sqlite_integrity_check",
        "sqlite_foreign_key_check",
        "runtime_candidate_view_covers_lookup_rows",
        "runtime_blocker_view_explains_ineligible_rows",
        "runtime_portrayal_view_is_strict_gate_clear_surface",
        "runtime_eligibility_matches_gate_state",
        "blocker_rows_are_queryable",
        "zero_runtime_rows_are_deliberate_fail_closed",
        "import_audit_has_no_fail_rows",
    ):
        assert checks[name]["status"] == "pass"

    strict = checks["runtime_portrayal_view_is_strict_gate_clear_surface"]["actual"]
    assert strict["runtime_symbol_portrayal_v1"] == 0
    assert strict["derived_gate_clear_rows"] == 0
    assert strict["leaky_rows"] == 0

    fail_closed = checks["zero_runtime_rows_are_deliberate_fail_closed"]["actual"]
    assert fail_closed["runtime_eligible_rows"] == 0
    assert fail_closed["runtime_symbol_portrayal_v1"] == 0
    assert fail_closed["visual_approval_pending_rows"] == 3057

    blockers = checks["runtime_blocker_view_explains_ineligible_rows"]["actual"]
    assert blockers["ineligible_without_blockers"] == 0

    assert saved == payload
    assert runtime_db_contract.CONTRACT_JSON.stat().st_mtime_ns == saved_mtime
    assert runtime_db_contract.CONTRACT_MD.exists()

    print("runtime DB contract: OK")


if __name__ == "__main__":
    main()
