"""Smoke Standard Repair Batch 25.

Run:  python3 -m forge.tests.test_standard_repair_batch25
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch25


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch33.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch25.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 11
    assert not result["blockers"]

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch25.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert "var(--magenta)" in _svg("DAYSQR01", result)
    assert '<rect x="18" y="12"' in _svg("DAYSQR01", result)
    assert '<circle cx="32" cy="39"' in _svg("DAYSQR01", result)
    assert '<circle cx="32" cy="49"' in _svg("DAYSQR21", result)
    assert "M32 10 L52 43 H12 Z" in _svg("DAYTRI01", result)
    assert "M12 17 H52 L32 50 Z" in _svg("DAYTRI05", result)

    for asset in ("LITFLT01", "LITFLT02", "LITVES01", "LITVES02"):
        svg = _svg(asset, result)
        assert "var(--black)" in svg
        assert "M13 39 H51 L45 51 H19 Z" in svg
        assert "diamond" not in svg

    assert "M32 17 V38" in _svg("LITVES01", result)
    assert "M32 18 V39" in _svg("LITVES02", result)

    reflector = _svg("RADRFL03", result)
    assert "var(--magenta)" in reflector
    assert '<circle cx="32" cy="32" r="13"' in reflector
    assert "M32 8 V20" in reflector

    scanner = _svg("RASCAN01", result)
    assert "var(--brown)" in scanner
    assert "M20 54 H44" in scanner
    assert "M18 15 H46" in scanner

    conspicuous = _svg("RASCAN11", result)
    assert "var(--black)" in conspicuous
    assert "var(--brown)" not in conspicuous

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 11
    assert (ROOT / "catalog" / "owned_repair_batch33.md").exists()
    print("standard repair batch 25: OK")


if __name__ == "__main__":
    main()
