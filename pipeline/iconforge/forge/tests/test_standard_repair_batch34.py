"""Smoke Standard Repair Batch 34.

Run:  python3 -m forge.tests.test_standard_repair_batch34
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch34


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch42.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch34.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 13
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch34.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert '<rect x="23" y="23" width="18" height="18"' in _svg("NMKREG01", result)
    assert "M44 32 H20" in _svg("NMKREG02", result)
    assert "M20 32 H44" in _svg("NMKREG03", result)
    assert ">STOP</text>" in _svg("NMKREG10", result)
    assert "M18 38 H25 L37 47" in _svg("NMKREG11", result)
    assert "M32 18 V38" in _svg("NMKREG12", result)
    assert "M40 28 L47 35 L40 42" in _svg("NMKREG13", result)
    assert "M17 32 H47" in _svg("NMKREG14", result)
    assert ">VHF</text>" in _svg("NMKREG15", result)
    assert ">D</text>" in _svg("NMKREG16", result)
    assert "M32 20 V44" in _svg("NMKREG17", result)
    assert '<rect x="14" y="16" width="14" height="32"' in _svg("NMKREG19", result)
    assert '<rect x="36" y="16" width="14" height="32"' in _svg("NMKREG20", result)

    for asset in standard_repair_batch34.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch34\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 13
    assert (ROOT / "catalog" / "owned_repair_batch42.md").exists()
    print("standard repair batch 34: OK")


if __name__ == "__main__":
    main()
