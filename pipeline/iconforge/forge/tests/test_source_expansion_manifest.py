"""Smoke the FORGE-20 source-expansion manifest.

Run:  python3 -m forge.tests.test_source_expansion_manifest
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import source_expansion_manifest


def main() -> None:
    payload = source_expansion_manifest.build_manifest()
    assert payload["schema"] == "helm.iconforge.source_expansion_manifest.v1"
    assert payload["status"] == "planning_only_not_artwork"
    assert payload["input_correction"]["task_expected_no_helm_candidate_rows"] == 77
    assert payload["input_correction"]["current_no_helm_candidate_rows"] == 0
    assert payload["summary"]["rows"] == 55
    assert payload["summary"]["ready_rows"] == 0
    assert payload["summary"]["selection_reason_counts"]["triad_reference_gap:any_false"] == 41
    assert payload["summary"]["selection_reason_counts"]["triad_reference_gap:opencpn_false"] == 47
    assert payload["summary"]["selection_reason_counts"]["standard_source_row_missing"] == 8
    assert payload["summary"]["selection_reason_counts"]["triad_row_missing"] == 8
    assert all(row["readiness"]["status"] == "not_ready" for row in payload["rows"])
    assert all(not row["readiness"]["may_generate_final_art"] for row in payload["rows"])
    assert any(row["asset"] == "BOYLAT52" for row in payload["rows"])
    assert any(row["asset"] == "FLTHAZ02" for row in payload["rows"])
    assert "apache-design-inspiration" in payload["license_tags"]
    assert "license_pending_reference" in payload["license_tags"]

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        result = source_expansion_manifest.write_manifest(
            json_path=tmp / "source_expansion_manifest.json",
            md_path=tmp / "source_expansion_manifest.md",
        )
        written = json.loads((tmp / "source_expansion_manifest.json").read_text())
        assert result["summary"]["rows"] == 55
        assert written["summary"]["ready_rows"] == 0
        assert "Rows selected: 55" in (tmp / "source_expansion_manifest.md").read_text()

    print("source expansion manifest: OK")


if __name__ == "__main__":
    main()
