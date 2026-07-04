"""Smoke the Q20-Q25 buoy body primitive drafts.

Run:  python -m forge.tests.test_buoy_body_primitives
"""
from __future__ import annotations

from pathlib import Path

from .. import buoy_body_primitives


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    output = buoy_body_primitives.build()
    summary = output["summary"]
    specs = output["specs"]
    skipped = output["skipped_assets"]

    assert summary["official_rows"] == 6
    assert summary["generated_specs"] == 100
    assert summary["generated_svgs"] == 100
    assert summary["skipped_assets"] == 6
    assert summary["visual_approvals"] == 0
    assert summary["shape_counts"] == {
        "barrel_buoy": 4,
        "can_buoy": 28,
        "conical_buoy": 24,
        "pillar_buoy": 17,
        "spar_buoy": 13,
        "spherical_buoy": 14,
    }

    by_id = {spec["id"]: spec for spec in specs}
    assert "Q20-BOYCON60" in by_id
    assert "Q21-BOYCAN60" in by_id
    assert "Q22-BOYSPH60" in by_id
    assert "Q23-BOYPIL60" in by_id
    assert "Q24-BOYSPR60" in by_id
    assert "Q25-BOYBAR60" in by_id

    q20 = by_id["Q20-BOYCON60"]
    assert q20["geometry"]["primitive"] == "conical_buoy"
    assert q20["geometry"]["required_condition"] == "BOYSHP1"
    assert q20["geometry"]["color_tokens"] == ["red"]
    assert q20["source_refs"][0]["int1"] == "Q20"
    assert q20["source_refs"][0]["official_name"] == "Conical buoy, nun buoy, ogival buoy"
    assert q20["source_refs"][0]["symbol_reference_crop"].endswith("Q20.png")

    q25 = by_id["Q25-BOYBAR60"]
    assert q25["geometry"]["primitive"] == "barrel_buoy"
    assert q25["geometry"]["required_condition"] == "BOYSHP6"

    for spec in specs:
        assert spec["s52_asset"].startswith("BOY")
        assert spec["qa"]["semantic_source_match"] is True
        assert spec["qa"]["visual_parity"] == "pending"
        assert spec["qa"]["final_approved"] is False
        assert spec["asset"]["status"] == "generated_owned_draft"
        assert spec["provenance"]["origin"] == "generated-owned-artwork"
        assert "canonical_asset_source" in spec["provenance"]["forbidden_sources"]
        assert spec["source_refs"][0]["status"] == "reference_only_not_canonical_artwork"
        svg_path = ROOT / spec["asset"]["canonical"]
        assert svg_path.exists()
        svg = svg_path.read_text()
        assert f'data-s52-asset="{spec["s52_asset"]}"' in svg
        assert "fill=\"red\"" not in svg
        assert "fill=\"#" not in svg
        assert "var(--" in svg
        assert "star" not in svg.lower()

    assert {row["asset"] for row in skipped} == {
        "BCNGEN64",
        "BCNGEN65",
        "BCNSTK78",
        "BCNSTK79",
        "BCNSTK80",
        "BCNSTK81",
    }
    assert all("non_buoy_asset_in_body_shape_row" in row["reasons"] for row in skipped)

    assert (ROOT / "catalog" / "symbol_specs_q20_q25.json").exists()
    assert (ROOT / "catalog" / "symbol_specs_q20_q25.yaml").exists()
    assert (ROOT / "catalog" / "symbol_specs_q20_q25.md").exists()
    assert "generated_specs: 100" in (ROOT / "catalog" / "symbol_specs_q20_q25.yaml").read_text()
    print("buoy body primitives: OK")


if __name__ == "__main__":
    main()
