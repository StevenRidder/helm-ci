"""Smoke OpenCPN/S-52 reference raster/vector renders.

Run:  python -m forge.tests.test_opencpn_reference_render
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from .. import opencpn_reference_render


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    output = opencpn_reference_render.build()
    summary = output["summary"]
    rows = output["rows"]
    by_asset = {row["asset"]: row for row in rows}

    assert summary["master_rows"] == 824
    assert summary["palettes"] == ["day", "dusk", "night"]
    assert summary["rendered_assets"] == 777
    assert summary["bitmap_rendered_assets"] == 728
    assert summary["vector_rendered_assets"] == 49
    assert summary["reference_pngs"] == 2331
    assert summary["status_counts"]["rendered"] == 728
    assert summary["status_counts"]["rendered_vector"] == 49
    assert summary["status_counts"]["missing_opencpn_asset_definition"] == 47

    for asset in ["BOYCON60", "BOYCAR01", "ACHARE02", "TOPMA114", "WRECKS04"]:
        row = by_asset[asset]
        assert row["status"] == "rendered"
        assert set(row["palette_paths"]) == {"day", "dusk", "night"}
        assert row["source"]["license_boundary"] == "reference_oracle_not_canonical_artwork"
        assert "canonical_owned_svg_source" in row["source"]["forbidden_use"]
        for rel_path in row["palette_paths"].values():
            path = ROOT / rel_path
            assert path.exists()
            image = Image.open(path)
            assert image.width == row["bitmap"]["width"]
            assert image.height == row["bitmap"]["height"]

    achare51 = by_asset["ACHARE51"]
    assert achare51["status"] == "rendered"
    assert achare51["render_source"] == "bitmap_crop"
    assert achare51["opencpn_definition"]["kind"] == "symbol"

    cblsub06 = by_asset["CBLSUB06"]
    assert cblsub06["status"] == "rendered_vector"
    assert cblsub06["render_source"] == "hpgl_vector"
    assert cblsub06["opencpn_definition"]["kind"] == "line-style"
    assert set(cblsub06["palette_paths"]) == {"day", "dusk", "night"}

    boycon = by_asset["BOYCON60"]
    assert boycon["bitmap"] == {
        "height": 16,
        "origin": {"x": 0, "y": 0},
        "pivot": {"x": 9, "y": 12},
        "width": 19,
        "x": 167,
        "y": 415,
    }

    assert (ROOT / "out" / "opencpn_s52_reference" / "report.json").exists()
    assert (ROOT / "out" / "opencpn_s52_reference" / "README.md").exists()
    print("OpenCPN reference renders: OK")


if __name__ == "__main__":
    main()
