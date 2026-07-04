"""Smoke Standard Repair Batch 61.

Run:  python3 -m forge.tests.test_standard_repair_batch61
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch61


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch69.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch61.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 10
    assert not result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assets = {row["asset"] for row in result["symbols"]}
    assert assets == {
        "BOYSPR02", "BOYSPR03", "BOYSPR04", "BOYSPR05", "BOYSPR60",
        "BOYSPR61", "BOYSPR62", "BOYSPR65", "BOYSPR68", "BOYSPR69",
    }

    for row in result["symbols"]:
        svg = _svg(row["asset"], result)
        assert 'data-repair-batch="standard-repair-batch61"' in svg
        assert "generated-owned-artwork" in svg
        assert row["chart1_parity_gate"]
        assert 'points="28,8 36,8 40,54 24,54"' in svg
        assert 'data-pattern="horizontal-spar-band"' in svg

    assert 'fill="var(--green)"' in _svg("BOYSPR02", result)
    assert 'fill="var(--red)"' in _svg("BOYSPR03", result)
    assert _svg("BOYSPR04", result).count('data-pattern="horizontal-spar-band"') == 2
    assert 'fill="var(--orange)"' in _svg("BOYSPR04", result)
    assert 'fill="var(--yellow)"' in _svg("BOYSPR62", result)
    assert 'fill="var(--black)"' in _svg("BOYSPR68", result)
    assert 'fill="var(--yellow)"' in _svg("BOYSPR69", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 10
    assert (ROOT / "catalog" / "owned_repair_batch69.md").exists()
    print("standard repair batch 61: OK")


if __name__ == "__main__":
    main()
