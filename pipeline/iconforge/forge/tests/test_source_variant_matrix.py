"""Smoke the Unicode-style source/provider variant matrix.

Run:  python -m forge.tests.test_source_variant_matrix
"""
from __future__ import annotations

from pathlib import Path

from .. import source_variant_matrix


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    matrix = source_variant_matrix.build([
        "SMCFAC02",
        "BCNCAR01",
        "SMCFAC_CATSCF_16",
        "ACHARE02",
        "MORFAC03",
        "WRECKS04",
        "UWTROC04",
    ])
    assert matrix["method"].startswith("Unicode emoji chart style")
    assert matrix["style_contract"]["format"] == "helm.iconforge.style_contract.v1"
    assert matrix["style_contract"]["style_id"] == "helm-s52-owned-svg-v1"
    assert len(matrix["rows"]) == 7

    smcfac = next(row for row in matrix["rows"] if row["asset"] == "SMCFAC02")
    assert smcfac["s57"]["object_class"]
    assert smcfac["s101"]["symbol_id"] == "SMCFAC02"
    assert smcfac["providers"]["helm_generated_draft_svg"]
    assert smcfac["providers"]["opencpn_s52_reference_render"]
    assert smcfac["providers"]["opencpn_s52_reference_render"][0]["image"]
    assert smcfac["providers"]["s101_portrayal_catalogue_svg"]
    assert smcfac["providers"]["wikimedia_commons_svg"]
    assert smcfac["providers"]["noto_emoji_concept"]
    assert smcfac["providers"]["openmoji_concept"]
    assert smcfac["providers"]["open_source_icon_concept"]
    assert smcfac["chart1_mappings_refs"] == ["Q45"]
    assert smcfac["visual_brief"]["format"] == "helm.iconforge.visual_brief.v1"
    assert smcfac["visual_brief"]["style_contract_id"] == "helm-s52-owned-svg-v1"
    assert smcfac["visual_brief"]["s57_object_class"] == "HRBFAC"

    bcncar = next(row for row in matrix["rows"] if row["asset"] == "BCNCAR01")
    assert bcncar["s101"]["symbol_id"] == "BCNCAR01"
    assert bcncar["providers"]["chart1_mappings_symbol_reference"]
    assert bcncar["providers"]["noto_emoji_concept"]
    assert "north cardinal" in " ".join(bcncar["visual_brief"]["condition_labels"])

    shower = next(row for row in matrix["rows"] if row["asset"] == "SMCFAC_CATSCF_16")
    assert shower["name"] == "Showers"
    assert shower["s57"]["object_class"] == "SMCFAC"
    assert shower["providers"]["semantic_target"]
    assert shower["providers"]["noto_emoji_concept"]
    assert shower["providers"]["openmoji_concept"]
    assert shower["providers"]["open_source_icon_concept"]
    assert "shower head" in shower["visual_brief"]["model_caption"]

    anchorage = next(row for row in matrix["rows"] if row["asset"] == "ACHARE02")
    assert not anchorage["providers"].get("aquamap_map_symbols")

    morfac = next(row for row in matrix["rows"] if row["asset"] == "MORFAC03")
    morfac_aquamap = [entry["label"] for entry in morfac["providers"]["aquamap_map_symbols"]]
    assert morfac_aquamap == ["Aqua Map Pile", "Aqua Map Mooring Buoy"]

    wreck = next(row for row in matrix["rows"] if row["asset"] == "WRECKS04")
    wreck_aquamap = " ".join(entry["label"] for entry in wreck["providers"]["aquamap_map_symbols"])
    assert "Wreck" in wreck_aquamap
    assert "Rock" not in wreck_aquamap

    rock = next(row for row in matrix["rows"] if row["asset"] == "UWTROC04")
    rock_aquamap = " ".join(entry["label"] for entry in rock["providers"]["aquamap_map_symbols"])
    assert "Rock" in rock_aquamap
    assert "Wreck" not in rock_aquamap

    for output in matrix["outputs"].values():
        assert (ROOT / output).exists(), output
    print("source variant matrix: OK")


if __name__ == "__main__":
    main()
