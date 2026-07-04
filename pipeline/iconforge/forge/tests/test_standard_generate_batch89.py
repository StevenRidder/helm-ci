"""Smoke Standard Generate Batch 89.

Run:  python3 -m forge.tests.test_standard_generate_batch89
"""
from __future__ import annotations

from pathlib import Path

from .. import standard_generate_batch89


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = standard_generate_batch89.build(render_outputs=False)
    assert result["status"] == "generated_batch_pending_judge"
    assert result["summary"]["generated"] == 20
    assert result["summary"]["final_approved"] == 0
    assert {row["asset"] for row in result["symbols"]} == set(standard_generate_batch89.TARGETS)
    by_asset = {row["asset"]: row for row in result["symbols"]}
    assert by_asset["FSHHAV02"]["qa"]["visual_parity"] == "pending_llm_judge"
    assert by_asset["RCRTCL13"]["visual_examples"]["opencpn_render"]
    for row in result["symbols"]:
        assert row["qa"]["final_approved"] is False
        assert row["visual_examples"]["opencpn_render"]
        assert (ROOT / row["after_svg"]).exists()
    assert (ROOT / "catalog" / "owned_repair_batch89.json").exists()
    assert (ROOT / "catalog" / "owned_repair_batch89.md").exists()
    print("standard generate batch 89: OK")


if __name__ == "__main__":
    main()
