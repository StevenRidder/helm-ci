"""Smoke Standard Repair Batch 19.

Run:  python3 -m forge.tests.test_standard_repair_batch19
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch19


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch27.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch19.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 5
    assert not result["blockers"]

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch19.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}

    dangerous_rock = _svg("UWTROC03", result)
    assert 'data-repair-batch="standard-repair-batch19"' in dangerous_rock
    assert '<circle cx="32" cy="32" r="20" fill="var(--blue)"' in dangerous_rock
    assert "M32 17 V47 M17 32 H47" in dangerous_rock
    assert dangerous_rock.count('r="2.2" fill="var(--black)"') == 20

    awash = _svg("UWTROC04", result)
    assert "M15 32 H49" in awash
    assert "M21 16 L43 48 M43 16 L21 48" in awash
    assert "var(--blue)" not in awash

    exposed = _svg("WRECKS01", result)
    assert "M15 42 H49" in exposed
    assert "M20 22 L41 42 H23 Z" in exposed
    assert "var(--black)" in exposed
    assert "var(--gray)" not in exposed
    assert "var(--blue)" not in exposed

    non_dangerous = _svg("WRECKS04", result)
    assert "M15 32 H49" in non_dangerous
    assert "M22 20 V44 M32 16 V48 M42 20 V44" in non_dangerous
    assert "var(--blue)" not in non_dangerous

    dangerous_wreck = _svg("WRECKS05", result)
    assert "fill=\"var(--blue)\"" in dangerous_wreck
    assert dangerous_wreck.count('r="2.2" fill="var(--black)"') == 18
    assert "M24 22 V42 M32 18 V46 M40 22 V42" in dangerous_wreck

    shapes = {asset: _svg(asset, result) for asset in repaired}
    assert len(set(shapes.values())) == len(shapes)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 5
    assert (ROOT / "catalog" / "owned_repair_batch27.md").exists()
    print("standard repair batch 19: OK")


if __name__ == "__main__":
    main()
