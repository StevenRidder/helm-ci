"""Smoke Standard Repair Batch 35.

Run:  python3 -m forge.tests.test_standard_repair_batch35
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch35


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch43.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch35.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 14
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch35.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert 'fill="var(--yellow)"' in _svg("NOTBRD12", result)
    assert "M20 44 L44 20" in _svg("NOTMRK01", result)
    assert '<rect x="22" y="22" width="20" height="20"' in _svg("NOTMRK02", result)
    assert ">i</text>" in _svg("NOTMRK03", result)
    assert "M24 22 V42" in _svg("OSPONE02", result)
    assert "M20 32 H44" in _svg("OSPSIX02", result)
    assert '<circle cx="32" cy="32" r="18"' in _svg("OWNSHP01", result)
    assert "M32 8 L45 52 H19 Z" in _svg("OWNSHP05", result)
    assert "M32 15 V32 H48" in _svg("PIER0001", result)
    assert '<ellipse cx="32" cy="32" rx="21" ry="13"' in _svg("PLNPOS01", result)
    assert "M13 32 H51 M32 13 V51" in _svg("PLNPOS02", result)
    assert ">S</text>" in _svg("PLNSPD03", result)
    assert "stroke-dasharray" in _svg("PLNSPD04", result)
    assert "M18 18 L46 46" in _svg("POSITN02", result)

    for asset in standard_repair_batch35.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch35\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 14
    assert (ROOT / "catalog" / "owned_repair_batch43.md").exists()
    print("standard repair batch 35: OK")


if __name__ == "__main__":
    main()
