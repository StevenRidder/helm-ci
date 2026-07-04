"""Smoke Standard Repair Batch 36.

Run:  python3 -m forge.tests.test_standard_repair_batch36
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch36


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch44.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch36.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 14
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch36.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert ">RoRo</text>" in _svg("ROLROL01", result)
    assert "M32 27 V43" in _svg("TERMNL01", result)
    assert "M18 38 H46" in _svg("TERMNL02", result)
    assert 'fill="var(--red)"' in _svg("TERMNL03", result)
    assert 'fill="var(--white)"' in _svg("TERMNL04", result)
    assert ">OIL</text>" in _svg("TERMNL05", result)
    assert ">FUEL</text>" in _svg("TERMNL06", result)
    assert ">CH</text>" in _svg("TERMNL07", result)
    assert ">LIQ</text>" in _svg("TERMNL08", result)
    assert 'fill="var(--red)"' in _svg("TERMNL09", result)
    assert "C26 24 38 24" in _svg("TERMNL10", result)
    assert "M20 36 H45" in _svg("TERMNL11", result)
    assert '<rect x="22" y="23" width="20" height="20"' in _svg("TERMNL12", result)
    assert ">RoRo</text>" in _svg("TERMNL13", result)

    for asset in standard_repair_batch36.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch36\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 14
    assert (ROOT / "catalog" / "owned_repair_batch44.md").exists()
    print("standard repair batch 36: OK")


if __name__ == "__main__":
    main()
