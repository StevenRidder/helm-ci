"""Smoke the fail-closed runtime promotion gate.

Run:  python3 -m forge.tests.test_runtime_promotion_gate
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import runtime_promotion_gate


def main() -> None:
    payload = runtime_promotion_gate.build_runtime_export()
    assert payload["schema"] == "helm.iconforge.runtime_symbol_export.v1"
    assert payload["status"] == "fail_closed"
    assert payload["summary"]["review_rows"] == 3057
    assert payload["summary"]["runtime_rows"] == 0
    assert payload["summary"]["hard_pile_rows"] == 3057
    assert payload["summary"]["runtime_eligible_db_rows"] == 0
    assert payload["summary"]["runtime_portrayal_db_rows"] == 0
    assert "final_approved:false" in payload["summary"]["reason_counts"]
    assert "style_contract_pending" in payload["summary"]["reason_counts"]
    assert "style_contract_failed" in payload["summary"]["reason_counts"]
    assert "colour_authority_missing" not in payload["summary"]["reason_counts"]
    assert "colour_authority_pending" not in payload["summary"]["reason_counts"]
    assert "authority_trace_blocked" in payload["summary"]["reason_counts"]
    assert "authority_trace_runtime_blocker" in payload["summary"]["reason_counts"]
    assert "authority_trace_missing" not in payload["summary"]["reason_counts"]
    assert "authority_trace:runtime_candidate_not_eligible" in payload["summary"]["reason_counts"]
    assert any(reason.startswith("gate:visual_approval:pending") for reason in payload["summary"]["reason_counts"])
    assert not payload["rows"]
    assert payload["hard_pile"][0]["reason_codes"]
    assert not any(reason.startswith("colour_authority") for reason in payload["summary"]["reason_counts"])
    assert any(reason.startswith("authority_trace:") for reason in payload["summary"]["reason_counts"])

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        result = runtime_promotion_gate.write_runtime_export(
            export_path=tmp / "runtime_symbol_export.json",
            hard_pile_path=tmp / "runtime_symbol_hard_pile.json",
        )
        export = json.loads((tmp / "runtime_symbol_export.json").read_text())
        hard_pile = json.loads((tmp / "runtime_symbol_hard_pile.json").read_text())
        assert result["summary"]["runtime_rows"] == 0
        assert export["rows"] == []
        assert len(hard_pile["rows"]) == 3057

    print("runtime promotion gate: OK")


if __name__ == "__main__":
    main()
