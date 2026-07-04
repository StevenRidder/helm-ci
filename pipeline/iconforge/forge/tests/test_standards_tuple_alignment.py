"""Smoke the full-catalog standards tuple alignment.

Run:  python -m forge.tests.test_standards_tuple_alignment
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import standards_tuple_alignment


def _row(result: dict, asset: str) -> dict:
    for row in result["rows"]:
        if row["semantic_tuple"]["s52_symbol_id"] == asset:
            return row
    raise AssertionError(f"missing asset {asset}")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "standards_tuple_alignment.json"
        md = Path(tmp) / "standards_tuple_alignment.md"
        result = standards_tuple_alignment.build()

        assert result["schema"] == "helm.forge.standards-tuple-alignment.v1"
        assert result["status"] == "provisional_standards_alignment_ready"
        assert result["coverage"]["rows"] == 824
        assert sum(result["coverage"]["tuple_status_counts"].values()) == 824
        assert sum(result["coverage"]["s101_mapping_type_counts"].values()) == 824
        assert result["coverage"]["s101_mapping_type_counts"] == {
            "acceptable_deviation": 108,
            "direct_asset_match": 244,
            "rule_derived_equivalent": 215,
            "unresolved": 257,
        }
        assert "OpenCPN GPL rasters" in result["clean_room_boundary"]["not_bundled_as_source_artwork"]
        serialized = json.dumps(result)
        for dirty in [
            "TOPSHP09;TE",
            "TOPSHP15;TE",
            "TOPSHP73;TE",
            "TOPSHP81;TE",
            "TOPSHP89;TE",
            "TOPSHPT8;TE",
            "TOWERS74|;TX",
            "QUAPOS01;TX(OBJNAM",
        ]:
            assert dirty not in serialized

        achare02 = _row(result, "ACHARE02")
        assert achare02["s101_mapping_type"] == "direct_asset_match"
        assert achare02["s101"]["symbol_id"] == "ACHARE02"
        assert achare02["s101"]["feature_type"] == "Obstruction"

        boycan60 = _row(result, "BOYCAN60")
        assert boycan60["semantic_tuple"]["shape"] == "can"
        assert boycan60["semantic_tuple"]["colour_sequence"] == ["red"]
        assert boycan60["semantic_tuple"]["category"] in {"lateral_aid", "special_purpose_aid"}
        assert boycan60["s101_mapping_type"] in {"direct_asset_match", "rule_derived_equivalent", "acceptable_deviation"}
        assert boycan60["s101"]["attributes"]["buoyShape"] == "can"

        topmar01 = _row(result, "TOPMAR01")
        assert topmar01["semantic_tuple"]["geometry"] == "conditional"
        assert topmar01["s101_mapping_type"] in {"direct_asset_match", "rule_derived_equivalent", "acceptable_deviation", "unresolved"}

        topshp09 = _row(result, "TOPSHP09")
        assert topshp09["s101_mapping_type"] == "rule_derived_equivalent"
        assert topshp09["s101"]["feature_type"] == "Daymark"
        assert topshp09["s101"]["feature_rule_file"] == "PortrayalCatalog/Rules/Daymark.lua"

        arcsln01 = _row(result, "ARCSLN01")
        assert arcsln01["s101_mapping_type"] == "acceptable_deviation"
        assert arcsln01["s101"]["feature_type"] == "ArchipelagicSeaLaneArea"

        for asset in ("DWLDEF01", "DWRTCL05"):
            row = _row(result, asset)
            assert row["s101_mapping_type"] == "acceptable_deviation"
            assert row["s101"]["feature_type"] == "DeepWaterRouteCentreline"

        standards_tuple_alignment._write(out, result)
        md.write_text(standards_tuple_alignment._md(result))
        disk = json.loads(out.read_text())
        assert disk["coverage"]["rows"] == 824
        assert "Standards Tuple Alignment" in md.read_text()

    print("standards tuple alignment: OK")


if __name__ == "__main__":
    main()
