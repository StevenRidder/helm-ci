"""Smoke the FORGE-34 authority trace gate.

Run:  python3 -m forge.tests.test_authority_trace_gate
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import authority_trace_gate


ROOT = Path(__file__).resolve().parent.parent.parent


def _by_symbol(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for row in rows:
        out.setdefault(row["symbol_id"], []).append(row)
    return out


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _exercise_feature_catalogue_present() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        feature_catalogue = root / "FeatureCatalogue.xml"
        _write(
            feature_catalogue,
            """<S100_FC_FeatureCatalogue>
  <S100_FC_FeatureType name="LateralBuoy">
    <S100_FC_AttributeBinding />
  </S100_FC_FeatureType>
</S100_FC_FeatureCatalogue>
""",
        )
        _write(root / "PortrayalCatalog" / "Rules" / "LateralBuoy.lua", "-- fixture rule\n")

        payload = authority_trace_gate.build(
            s101_roots=[root],
            feature_catalogue_path=feature_catalogue,
        )
        source = payload["source"]["s101_feature_catalogue"]
        assert source["status"] == "present"
        assert source["parse_status"] == "parsed"
        assert source["sha256"]
        assert source["feature_type_count"] == 1
        assert source["attribute_binding_count"] == 1
        assert "LateralBuoy" in source["feature_types"]

        boylat25 = _by_symbol(payload["rows"])["BOYLAT25"][0]
        assert boylat25["s101_mapping"]["rule_file_local_path"] == str(root / "PortrayalCatalog" / "Rules" / "LateralBuoy.lua")
        assert boylat25["s101_mapping"]["rule_file_sha256"]
        assert boylat25["s101_mapping"]["feature_catalogue_sha256"] == source["sha256"]
        assert boylat25["s101_mapping"]["feature_catalogue_parse_status"] == "parsed"
        assert boylat25["s101_mapping"]["feature_catalogue_feature_present"] is True
        assert "authority_trace:s101_feature_catalogue_missing" not in boylat25["reason_codes"]
        assert "authority_trace:s101_feature_catalogue_unparsed" not in boylat25["reason_codes"]

        bcns = _by_symbol(payload["rows"])["BCNSTK02"][0]
        assert bcns["s101_mapping"]["feature_type"] == "CardinalBeacon"
        assert bcns["s101_mapping"]["feature_catalogue_feature_present"] is False
        assert "authority_trace:s101_feature_catalogue_feature_not_found" in bcns["reason_codes"]


def _exercise_feature_catalogue_malformed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        feature_catalogue = root / "FeatureCatalogue.xml"
        _write(feature_catalogue, "<S100_FC_FeatureCatalogue>")
        _write(root / "PortrayalCatalog" / "Rules" / "LateralBuoy.lua", "-- fixture rule\n")

        payload = authority_trace_gate.build(
            s101_roots=[root],
            feature_catalogue_path=feature_catalogue,
        )
        source = payload["source"]["s101_feature_catalogue"]
        assert source["status"] == "present"
        assert source["parse_status"] == "malformed_xml"
        assert source["sha256"]

        boylat25 = _by_symbol(payload["rows"])["BOYLAT25"][0]
        assert "authority_trace:s101_feature_catalogue_unparsed" in boylat25["reason_codes"]
        assert "authority_trace:s101_feature_catalogue_missing" not in boylat25["reason_codes"]


def main() -> None:
    _exercise_feature_catalogue_present()
    _exercise_feature_catalogue_malformed()

    payload = authority_trace_gate.build()
    assert payload["schema"] == "helm.iconforge.authority_trace_gate.v1"
    assert payload["status"] == "authority_trace_gate_complete"
    assert payload["summary"]["s52_lookup_rows"] == 3057
    assert payload["summary"]["authority_trace_rows"] == 3057
    assert payload["summary"]["asset_summary_rows"] == 824
    assert payload["summary"]["authority_trace_gap_rows"] > 0
    assert payload["summary"]["runtime_blocker_rows"] == 3057
    assert payload["tables"]["authority_trace"]["row_count"] == payload["summary"]["authority_trace_rows"]
    assert payload["tables"]["authority_trace_gap"]["row_count"] == payload["summary"]["authority_trace_gap_rows"]
    assert payload["tables"]["authority_asset_summary"]["row_count"] == payload["summary"]["asset_summary_rows"]

    reasons = payload["summary"]["reason_counts"]
    assert reasons["authority_trace:runtime_candidate_not_eligible"] == 3057
    assert reasons["authority_trace:s101_feature_catalogue_missing"] > 0
    assert "authority_trace:s101_rule_file_not_hashed" not in reasons
    assert "authority_trace:unknown_dictionary_code:COLPAT" not in reasons
    assert payload["source"]["s57_dictionary_decode"]["attdecode_sha256"]
    assert payload["source"]["s57_dictionary_decode"]["attdecode_colpat_values"]["5"] == "stripes (direction unknown)"
    assert payload["source"]["s57_dictionary_decode"]["attdecode_colpat_values"]["6"] == "border stripe"

    rows_by_symbol = _by_symbol(payload["rows"])
    for symbol_id in payload["golden_fixtures"]["required_symbols"]:
        assert rows_by_symbol.get(symbol_id), f"missing fixture trace for {symbol_id}"

    colour_fixture = next(
        row for row in rows_by_symbol["BOYLAT13"]
        if any(item.get("raw") == "COLOUR4,3,4" for item in row["s57_feature"]["raw_attribute_predicates"])
    )
    colour_decode = next(
        item for item in colour_fixture["s57_feature"]["decoded_attribute_predicates"]
        if item["attribute"] == "COLOUR" and item["raw"] == "COLOUR4,3,4"
    )
    assert colour_decode["decoded_value"] == ["green", "red", "green"]
    assert colour_fixture["s57_dictionary_decode"]["decoded_colours"] == ["green", "red", "green"]
    assert "hashed_attdecode.COLPAT" in colour_fixture["s57_dictionary_decode"]["source"]

    colpat6 = next(
        item
        for row in payload["rows"]
        for item in row["s57_feature"]["decoded_attribute_predicates"]
        if item["attribute"] == "COLPAT" and item["raw"] == "COLPAT6"
    )
    assert colpat6["decoded_value"] == "border stripe"
    assert colpat6["dictionary"] == "S57_PATTERNS+attdecode.COLPAT"

    colpat12 = next(
        item
        for row in payload["rows"]
        for item in row["s57_feature"]["decoded_attribute_predicates"]
        if item["attribute"] == "COLPAT" and item["raw"] == "COLPAT1,2"
    )
    assert colpat12["decoded_value"] == ["horizontal stripes", "vertical stripes"]

    boylat25 = rows_by_symbol["BOYLAT25"][0]
    assert boylat25["s52_lookup"]["instruction"].startswith("SY(BOYLAT25)")
    assert boylat25["s52_visual_recipe"]["selected_symbol_refs"]
    assert boylat25["s101_mapping"]["feature_type"] == "LateralBuoy"
    assert boylat25["helm_recipe"]["status"] in {"recipe_ready", "manual_exception_required", "missing"}
    assert "authority_trace:runtime_candidate_not_eligible" in boylat25["reason_codes"]

    topshp = rows_by_symbol["TOPSHP28"][0]
    assert topshp["s57_feature"]["object_class"]
    assert topshp["s52_visual_recipe"]["selected_symbol_refs"]

    non_s101_runtime = rows_by_symbol["VRMEBL01"][0]
    assert non_s101_runtime["s101_mapping"]["crosswalk_class"] == "non_s101_runtime_construct"
    assert "authority_trace:non_s101_runtime_construct" in non_s101_runtime["reason_codes"]

    inland_extension = rows_by_symbol["BORDER01"][0]
    assert inland_extension["s101_mapping"]["crosswalk_class"] == "non_s101_or_inland_extension"
    assert inland_extension["runtime_blocker"] is True

    malformed_gap = {
        row["reason_code"]
        for row in payload["gap_rows"]
        if row["symbol_id"] == "BOYLAT13"
    }
    assert "authority_trace:runtime_candidate_not_eligible" in malformed_gap

    saved = json.loads((ROOT / "catalog" / "authority_trace_gate.json").read_text())
    assert saved["summary"]["authority_trace_rows"] == 3057
    assert (ROOT / "catalog" / "authority_trace_gate.md").exists()

    print("authority trace gate: OK")


if __name__ == "__main__":
    main()
