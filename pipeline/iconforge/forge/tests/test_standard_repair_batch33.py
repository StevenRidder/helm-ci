"""Smoke Standard Repair Batch 33.

Run:  python3 -m forge.tests.test_standard_repair_batch33
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch33


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch41.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch33.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 15
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch33.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert 'fill="var(--red)"' in _svg("NMKPRH02", result)
    assert "M18 46 L46 18" in _svg("NMKPRH02", result)
    assert "M23 44 V20" in _svg("NMKPRH06", result)
    assert "M20 20 V47" in _svg("NMKPRH07", result)
    assert "M32 17 V43" in _svg("NMKPRH08", result)
    assert "C43 22 34 17" in _svg("NMKPRH10", result)
    assert "C22 24 27 34" in _svg("NMKPRH11", result)
    assert "points=\"32,12 32,52 12,32\"" in _svg("NMKPRH12", result)
    assert "points=\"32,12 52,32 32,52\"" in _svg("NMKPRH13", result)
    assert "M31 39 V26 H41 V39" in _svg("NMKPRH14", result)

    assert 'fill="var(--yellow)"' in _svg("NMKRCD01", result)
    assert "M21 32 H43" in _svg("NMKRCD01", result)
    assert "M24 31 H43" in _svg("NMKRCD02", result)
    assert 'fill="var(--green)"' in _svg("NMKRCD03", result)
    assert 'fill="var(--green)"' in _svg("NMKRCD04", result)
    assert "M45 32 H20" in _svg("NMKRCD05", result)
    assert "M19 32 H44" in _svg("NMKRCD06", result)

    for asset in standard_repair_batch33.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch33\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 15
    assert (ROOT / "catalog" / "owned_repair_batch41.md").exists()
    print("standard repair batch 33: OK")


if __name__ == "__main__":
    main()
