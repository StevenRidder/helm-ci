"""Smoke FORGE-53 public clean-room symbol package export.

Run:
  python3 -m forge.tests.test_public_cleanroom_symbol_export
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import electronic_chart1_proof_bundle
from .. import public_cleanroom_symbol_export


def main() -> None:
    payload = public_cleanroom_symbol_export.build_public_package()
    manifest = payload["manifest"]
    coverage = payload["coverage"]
    proof_data = payload["proof_data"]

    assert manifest["schema"] == "helm.forge.public_cleanroom_symbol_package.v1"
    assert manifest["status"] == "public_review_package_release_blocked"
    assert manifest["forum_packaging_decision"]["package_first"] is True
    assert manifest["forum_packaging_decision"]["opencpn_comparison_target_only"] is True
    assert manifest["forum_packaging_decision"]["s101_reference_trace_not_bundled_artwork"] is True
    assert coverage["total_rows"] == 3057
    assert coverage["registry_symbols"] == 2636
    assert coverage["runtime_export_rows"] == 0
    assert coverage["runtime_blocked_rows"] == 3057
    assert coverage["rows_with_committed_svg_palette"] > 700
    assert len(proof_data["rows"]) == 3057
    assert payload["chartplotter_rule_input"]["runtime_export_rows"] == []
    assert payload["hard_pile"]["rows"]
    assert all(row["reason_codes"] for row in payload["hard_pile"]["rows"])

    first = proof_data["rows"][0]
    assert first["clean_room_boundary"]["opencpn_role"] == "comparison_target_only"
    assert first["clean_room_boundary"]["s101_role"] == "standards_vocabulary_and_rule_trace_only"
    assert first["runtime"]["eligible"] is False
    assert first["runtime"]["reason_codes"]

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        proof_bundle_dir = tmp / "proof-bundle"
        electronic_chart1_proof_bundle.build_bundle(
            out_dir=proof_bundle_dir,
            catalog_json_path=None,
            catalog_markdown_path=None,
            copy_images=False,
        )
        result = public_cleanroom_symbol_export.write_public_package(
            proof_dir=tmp / "public-proof",
            proof_bundle_dir=proof_bundle_dir,
        )
        assert result["summary"]["total_rows"] == 3057
        proof_dir = tmp / "public-proof"
        written_manifest = json.loads((proof_dir / "manifest.json").read_text())
        written_data = json.loads((proof_dir / "package-proof-data.json").read_text())
        written_hard_pile = json.loads((proof_dir / "missing-hard-pile.json").read_text())
        html = (proof_dir / "compare-opencpn.html").read_text()
        assert written_manifest["coverage"]["runtime_export_rows"] == 0
        assert len(written_data["rows"]) == 3057
        assert written_hard_pile["rows"]
        assert "package-proof-data.json" in html
        assert "OpenCPN comparison" in html
        assert "Helm S-101 trace render" in html
        assert "no static fallback is allowed" in html
        assert json.loads((proof_dir / "provenance-inventory.json").read_text())["files"]["package_proof_data"]

    print("public clean-room symbol export: OK")


if __name__ == "__main__":
    main()
