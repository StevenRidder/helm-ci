"""Smoke Standard Repair Batch 31.

Run:  python3 -m forge.tests.test_standard_repair_batch31
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch31


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch39.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch31.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 16
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch31.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert "M32 32 H14" in _svg("NMKINF25", result)
    assert "M18 48 L46 20" in _svg("NMKINF26", result)
    assert "M46 48 L18 20" in _svg("NMKINF27", result)
    assert "M32 36 L48 20" in _svg("NMKINF28", result)
    assert "M32 36 L16 20" in _svg("NMKINF29", result)
    assert "M20 20 L44 44" in _svg("NMKINF38", result)
    assert "C23 30 34 41" in _svg("NMKINF40", result)
    assert "M28 25 L35 36 L42 26" in _svg("NMKINF43", result)
    assert "M31 17 V45" in _svg("NMKINF44", result)
    assert "M24 30 L42 46" in _svg("NMKINF45", result)
    assert "M31 44 V18" in _svg("NMKINF46", result)
    assert ">VHF</text>" in _svg("NMKINF47", result)
    assert "M33 33 L41 25" in _svg("NMKINF48", result)
    assert "M26 38 L35 27" in _svg("NMKINF49", result)
    assert "M17 48 L47 22" in _svg("NMKINF50", result)
    assert "M18 44 H46" in _svg("NMKINF53", result)

    for asset in standard_repair_batch31.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch31\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 16
    assert (ROOT / "catalog" / "owned_repair_batch39.md").exists()
    print("standard repair batch 31: OK")


if __name__ == "__main__":
    main()
