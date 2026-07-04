"""Smoke-test owned batch50 comparison against the source matrix."""
from __future__ import annotations

from pathlib import Path

from forge import owned_symbol_batch50_compare


ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> None:
    report = owned_symbol_batch50_compare.build()
    assert report["format"] == "helm.iconforge.owned_batch50_vs_uber_list.v1"
    assert report["asset_count"] == 50
    assert (ROOT / report["outputs"]["pdf"]).exists()
    assert (ROOT / report["outputs"]["html"]).exists()
    assert (ROOT / report["outputs"]["json"]).exists()
    for row in report["rows"]:
        assert row["owned"]["qa"]["structural_pass"] is True
        assert row["owned"]["qa"]["visual_parity"] == "pending_visual_model_and_human_review"
        assert row["references"]

    print("owned batch50 comparison: OK")


if __name__ == "__main__":
    main()
