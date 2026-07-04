"""Smoke-test the first owned SVG writing batch."""
from __future__ import annotations

from pathlib import Path

from forge import owned_symbol_batch50


ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> None:
    report = owned_symbol_batch50.build()
    assert report["format"] == "helm.iconforge.owned_symbol_batch50.report.v1"
    assert report["style_contract"]["style_id"] == "helm-s52-owned-svg-v1"
    assert report["asset_count"] == 50
    assert report["structural_pass"] == 50
    assert report["visual_parity"] == "pending_visual_model_and_human_review"
    assert (ROOT / report["outputs"]["manifest"]).exists()
    assert (ROOT / report["outputs"]["contact_sheet"]).exists()
    for symbol in report["symbols"]:
        svg = ROOT / symbol["asset"]["canonical"]
        assert svg.exists()
        assert symbol["qa"]["structural_pass"] is True
        assert symbol["qa"]["visual_parity"] == "pending_visual_model_and_human_review"
        assert "data-style-contract=\"helm-s52-owned-svg-v1\"" in svg.read_text()

    print("owned symbol batch50: OK")


if __name__ == "__main__":
    main()
