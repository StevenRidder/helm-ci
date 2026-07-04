"""Smoke the FORGE-46 Electronic Chart 1 proof bundle.

Run:
  python3 -m forge.tests.test_electronic_chart1_proof_bundle
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from PIL import Image

from .. import electronic_chart1_proof_bundle


def _first(rows: list[dict], row_key: str) -> dict:
    for row in rows:
        if row["row_key"] == row_key:
            return row
    raise AssertionError(f"missing row: {row_key}")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        out_dir = tmp_dir / "proof"
        result = electronic_chart1_proof_bundle.build_bundle(
            out_dir=out_dir,
            catalog_json_path=tmp_dir / "catalog.json",
            catalog_markdown_path=tmp_dir / "catalog.md",
            row_limit=2600,
        )
        manifest = json.loads((out_dir / "manifest.json").read_text())
        coverage = manifest["coverage"]
        rows_payload = json.loads((out_dir / "rows.json").read_text())
        hard_payload = json.loads((out_dir / "hard-pile.json").read_text())
        rows = rows_payload["rows"]
        hard_pile = hard_payload["rows"]

        assert result["status"] == "proof_bundle_written"
        assert manifest["schema"] == "helm.forge.electronic_chart1_proof_bundle.v1"
        assert manifest["status"] == "proof_bundle_ready"
        assert manifest["policy"]["backend_generated"] is True
        assert manifest["policy"]["browser_business_logic_allowed"] is False
        assert manifest["policy"]["static_json_fallback_allowed"] is False
        assert manifest["policy"]["runtime_promotion_allowed"] is False
        assert manifest["policy"]["missing_data_visible_alert_required"] is True
        assert manifest["local_server"]["api"]["rows"] == "/api/electronic-chart1-proof/rows"
        assert manifest["local_server"]["api"]["feedback"] == "/api/electronic-chart1-proof/feedback"

        assert coverage["authority_rows"] == 2600
        assert coverage["proof_rows"] == 2016
        assert coverage["hard_pile_rows"] == 584
        assert coverage["runtime_eligible_rows"] == 0
        assert coverage["runtime_promotion_allowed_rows"] == 0
        assert coverage["image_files_copied"] == 2016 * 12
        assert coverage["missing_media_references"] == 0
        assert coverage["section_counts"]["point_symbols"] > 0
        assert coverage["section_counts"]["line_styles"] > 0
        assert coverage["section_counts"]["area_fills"] > 0
        assert coverage["section_counts"]["conditional_rules"] > 0
        assert coverage["section_counts"]["topmarks_daymarks"] > 0
        assert coverage["section_counts"]["text_rules"] > 0
        assert coverage["section_counts"]["manual_placeholders"] > 0
        assert coverage["hard_pile_reason_counts"]["diff:helm_s57_render_missing"] > 0
        assert coverage["hard_pile_reason_counts"]["diff:opencpn_reference_missing"] > 0

        for name in [
            "manifest.json",
            "coverage.json",
            "rows.json",
            "hard-pile.json",
            "schema.json",
            "index.html",
        ]:
            assert (out_dir / name).exists(), name

        assert rows_payload["schema"] == "helm.forge.electronic_chart1_proof_bundle.v1"
        assert hard_payload["schema"] == "helm.forge.electronic_chart1_proof_bundle.v1"
        assert len(rows) == 2016
        assert len(hard_pile) == 584
        assert all(row["runtime_promotion_allowed"] is False for row in rows + hard_pile)
        assert all(row["review_controls"]["runtime_approval_allowed"] is False for row in rows + hard_pile)

        boycan60 = _first(rows, "BOYLAT_BOYCAN60_1907_30184_1907")
        assert boycan60["section"] == "point_symbols"
        assert boycan60["gates"]["semantic"]["gate"] == "green"
        assert boycan60["gates"]["proof"]["gate"] == "red"
        assert "runtime_gate:fail_closed" in boycan60["visible_gaps"]
        assert boycan60["standards"]["s101"]["trace"]["classification"] == "rule_derived"
        assert boycan60["standards"]["s101"]["trace"]["rule_file"] == "PortrayalCatalog/Rules/SpecialPurposeGeneralBuoy.lua"
        media = boycan60["media"]["day"]
        for key in ["opencpn", "helm_s57", "helm_s101", "visual_diff"]:
            assert media[key]["copied"] is True
            assert media[key]["url"]
            media_path = out_dir / media[key]["url"]
            assert media_path.exists()
            with Image.open(media_path) as image:
                assert image.size == (128, 128)
                assert image.convert("RGBA").getbbox() is not None

        topshq28 = _first(rows, "TOPMAR_TOPSHQ28_2433_93904_2430")
        assert topshq28["section"] == "topmarks_daymarks"
        assert topshq28["standards"]["s101"]["trace"]["rule_file"] == "PortrayalCatalog/Rules/Daymark.lua"

        bridge = _first(rows, "BRIDGE_text-only_15_32051_15")
        assert bridge["section"] == "text_rules"
        assert bridge["gates"]["semantic"]["gate"] == "red"
        assert "s101_trace:db_backing_missing" in bridge["visible_gaps"]

        topmar = _first(hard_pile, "DAYMAR_TOPMAR01_2118_93812_2119")
        assert topmar["status"] == "proof_hard_pile"
        assert "diff:helm_s57_render_missing" in topmar["reason_codes"]
        assert topmar["available_inputs"]["diff_verdict"] is False

        html = (out_dir / "index.html").read_text()
        assert "const API='/api/electronic-chart1-proof'" in html
        assert "${API}/summary" in html
        assert "${API}/rows" in html
        assert "No static JSON fallback is allowed" in html
        assert "BOYCAN60" not in html
        assert "BRIDGE_text-only_15_32051_15" not in html

        schema = json.loads((out_dir / "schema.json").read_text())
        assert schema["frontend_contract"]["must_fetch_backend"] is True
        assert schema["frontend_contract"]["static_json_fallback_allowed"] is False
        assert schema["frontend_contract"]["business_logic_allowed"] is False

        summary_api = electronic_chart1_proof_bundle.api_summary(out_dir)
        assert summary_api["status"] == "ok"
        assert summary_api["summary"]["authority_rows"] == 2600
        point_api = electronic_chart1_proof_bundle.api_rows("section=point_symbols&limit=5", out_dir)
        assert point_api["pagination"]["returned"] == 5
        assert all(row["section"] == "point_symbols" for row in point_api["rows"])
        red_api = electronic_chart1_proof_bundle.api_rows("gate=red&limit=10", out_dir)
        assert red_api["pagination"]["returned"] == 10
        assert all(row["gates"]["proof"]["gate"] == "red" for row in red_api["rows"])
        search_api = electronic_chart1_proof_bundle.api_rows("q=SpecialPurposeGeneralBuoy.lua&limit=20", out_dir)
        assert any(row["row_key"] == "BOYLAT_BOYCAN60_1907_30184_1907" for row in search_api["rows"])
        hard_api = electronic_chart1_proof_bundle.api_hard_pile("limit=5", out_dir)
        assert hard_api["pagination"]["returned"] == 5

        feedback = electronic_chart1_proof_bundle._write_feedback(out_dir, [{
            "row_key": "BOYLAT_BOYCAN60_1907_30184_1907",
            "chart1_row_id": "echart1-1908",
            "decision": "needs_repair",
            "needs_remediation": True,
            "feedback": "shape differs from OpenCPN witness",
            "expected_change": "repair visual recipe, keep runtime blocked",
        }])
        assert feedback["status"] == "saved"
        assert (out_dir / feedback["feedback_json"]).exists()
        assert (out_dir / feedback["feedback_csv"]).exists()

        catalog_md = (tmp_dir / "catalog.md").read_text()
        assert "backend-fed proof UI/public bundle" in catalog_md
        assert "runtime_eligible_rows: `0`" in catalog_md

    print("electronic Chart 1 proof bundle: OK")


if __name__ == "__main__":
    main()
