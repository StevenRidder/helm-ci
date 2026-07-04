"""Smoke the FORGE-14 standards-alignment rollup.

Run:  python -m forge.tests.test_standards_alignment_gate
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import standards_alignment_gate


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        out_json = tmp_dir / "standards_alignment_gate.json"
        out_md = tmp_dir / "standards_alignment_gate.md"
        gate = standards_alignment_gate.build()

        assert gate["schema"] == "helm.forge.standards-alignment-gate.v1"
        assert gate["task"] == "FORGE-14"
        assert gate["status"] == "review_required"
        assert "chart1_parity_status_not_pass" in gate["review_state"]["blockers"]
        assert "no_final_approved_chart1_rows" in gate["review_state"]["blockers"]
        assert "chart1_hard_pile_not_empty" in gate["review_state"]["blockers"]
        unresolved_topmarks = gate["topmark_standards"]["summary"]["ambiguous_or_unresolved_rows"]
        if unresolved_topmarks:
            assert "topmark_unresolved_rows_not_empty" in gate["review_state"]["blockers"]

        assert gate["chart1_parity"]["rows"] == 824
        assert gate["chart1_parity"]["gate_assets"] == 362
        assert gate["chart1_parity"]["evidence_counts"]["exact_symbol_crop"] == 139
        assert gate["chart1_parity"]["hard_pile_entries"] == 362
        assert gate["chart1_parity"]["final_approved"] == 0

        assert gate["standard_source_table"]["summary"]["rows"] == 824
        assert gate["s52_s57_s101_crosswalk"]["counts"]["s101_exact_symbol_matches"] == 244
        assert gate["s52_s57_s101_crosswalk"]["counts"]["s101_feature_rule_candidates"] == 545
        assert gate["topmark_standards"]["summary"]["topmark_rows_needing_special_pass"] == 137
        assert unresolved_topmarks >= 0
        assert "OpenCPN GPL raster sprites" in gate["clean_room_boundary"]["not_bundled_as_source_artwork"]
        assert "FORGE-22" in gate["downstream_policy"]

        standards_alignment_gate._write_json(out_json, gate)
        out_md.write_text(standards_alignment_gate._md(gate))
        disk = json.loads(out_json.read_text())
        assert disk["status"] == "review_required"
        assert "FORGE-14 Standards Alignment Gate" in out_md.read_text()

    print("standards alignment gate: OK")


if __name__ == "__main__":
    main()
