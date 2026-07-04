"""Smoke Standard Repair Batch 51.

Run:  python3 -m forge.tests.test_standard_repair_batch51
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch51


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch59.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch51.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 58
    assert not result["blockers"]
    assert all(row["asset"].startswith("TOWERS") for row in result["symbols"])
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    for row in result["symbols"]:
        svg = _svg(row["asset"], result)
        assert "generated-owned-artwork" in svg
        assert 'data-repair-batch="standard-repair-batch51"' in svg
        assert 'points="25,12 39,12 49,52 15,52"' in svg
        assert "M13 52 H51" in svg
        assert "var(--" in svg

    assert 'data-pattern="solid-tower"' in _svg("TOWERS60", result)
    assert 'fill="var(--red)"' in _svg("TOWERS60", result)
    assert _svg("TOWERS50", result).count('data-pattern="vertical-tower"') == 2
    assert _svg("TOWERS53", result).count('data-pattern="horizontal-tower"') == 2
    assert _svg("TOWERS55", result).count('data-pattern="diagonal-tower"') >= 3
    assert _svg("TOWERS98", result).count('data-pattern="checker-tower"') == 16

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 58
    assert (ROOT / "catalog" / "owned_repair_batch59.md").exists()
    print("standard repair batch 51: OK")


if __name__ == "__main__":
    main()
