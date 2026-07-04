"""Smoke Standard Repair Batch 30.

Run:  python3 -m forge.tests.test_standard_repair_batch30
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch30


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch38.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch30.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 12
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch30.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert 'fill="var(--green)"' in _svg("NMKINF01", result)
    assert "M22 18 V46 M42 18 V46" in _svg("NMKINF01", result)
    assert "L25 34 H34" in _svg("NMKINF02", result)
    assert "C23 38 29 48" in _svg("NMKINF03", result)
    assert "M25 35 L32 20 L39 35" in _svg("NMKINF04", result)
    assert "M24 37 V27 H40 V37" in _svg("NMKINF05", result)
    assert "M20 21 V49" in _svg("NMKINF06", result)
    assert "M32 17 V43" in _svg("NMKINF19", result)
    assert "C30 23 36 39" in _svg("NMKINF20", result)
    assert '<rect x="20" y="25" width="18" height="12"' in _svg("NMKINF21", result)
    assert "C43 22 34 17" in _svg("NMKINF22", result)
    assert "M15 32 H49" in _svg("NMKINF23", result)
    assert "M32 32 H50" in _svg("NMKINF24", result)

    for asset in standard_repair_batch30.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch30\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 12
    assert (ROOT / "catalog" / "owned_repair_batch38.md").exists()
    print("standard repair batch 30: OK")


if __name__ == "__main__":
    main()
