"""Smoke Standard Repair Batch 55.

Run:  python3 -m forge.tests.test_standard_repair_batch55
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch55


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch63.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch55.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 44
    assert not result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert sum(1 for row in result["symbols"] if row["asset"].startswith("BOYCAN")) == 23
    assert sum(1 for row in result["symbols"] if row["asset"].startswith("BOYCON")) == 21

    assert 'data-repair-batch="standard-repair-batch55"' in _svg("BOYCAN60", result)
    assert 'points="20,16 44,16 48,48 16,48"' in _svg("BOYCAN60", result)
    assert 'points="32,11 16,48 48,48"' in _svg("BOYCON60", result)
    assert 'fill="var(--red)"' in _svg("BOYCAN60", result)
    assert 'fill="var(--green)"' in _svg("BOYCAN61", result)
    assert 'fill="var(--yellow)"' in _svg("BOYCON62", result)
    assert _svg("BOYCAN74", result).count('data-pattern="horizontal-buoy-band"') == 5
    assert _svg("BOYCON78", result).count('data-pattern="vertical-buoy-band"') == 2
    assert 'data-pattern="mixed-horizontal-buoy-band"' in _svg("BOYCON81", result)
    assert 'data-pattern="mixed-vertical-buoy-band"' in _svg("BOYCON81", result)

    for row in result["symbols"]:
        svg = _svg(row["asset"], result)
        assert "generated-owned-artwork" in svg
        assert row["chart1_parity_gate"]

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 44
    assert (ROOT / "catalog" / "owned_repair_batch63.md").exists()
    print("standard repair batch 55: OK")


if __name__ == "__main__":
    main()
