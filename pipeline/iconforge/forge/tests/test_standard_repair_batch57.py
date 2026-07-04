"""Smoke Standard Repair Batch 57.

Run:  python3 -m forge.tests.test_standard_repair_batch57
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch57


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch65.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch57.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 15
    assert not result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["asset"] for row in result["symbols"]} == {
        "BOYPIL01", "BOYPIL59", "BOYPIL60", "BOYPIL61", "BOYPIL62", "BOYPIL66",
        "BOYPIL67", "BOYPIL68", "BOYPIL69", "BOYPIL70", "BOYPIL71", "BOYPIL72",
        "BOYPIL73", "BOYPIL74", "BOYPIL81",
    }

    assert 'data-repair-batch="standard-repair-batch57"' in _svg("BOYPIL60", result)
    assert 'points="24,12 40,12 46,48 18,48"' in _svg("BOYPIL60", result)
    assert 'fill="var(--red)"' in _svg("BOYPIL60", result)
    assert 'fill="var(--green)"' in _svg("BOYPIL61", result)
    assert 'fill="var(--orange)"' in _svg("BOYPIL59", result)
    assert _svg("BOYPIL66", result).count('data-pattern="horizontal-pillar-band"') == 3
    assert _svg("BOYPIL70", result).count('fill="var(--black)"') >= 2
    assert _svg("BOYPIL70", result).count('fill="var(--yellow)"') == 1
    assert _svg("BOYPIL73", result).count('data-pattern="vertical-pillar-band"') == 2

    for row in result["symbols"]:
        assert row["chart1_parity_gate"]
        assert "generated-owned-artwork" in _svg(row["asset"], result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 15
    assert (ROOT / "catalog" / "owned_repair_batch65.md").exists()
    print("standard repair batch 57: OK")


if __name__ == "__main__":
    main()
