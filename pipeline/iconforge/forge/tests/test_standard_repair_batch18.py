"""Smoke Standard Repair Batch 18.

Run:  python3 -m forge.tests.test_standard_repair_batch18
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch18


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch26.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch18.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["human_feedback_rows"] == 5
    assert result["summary"]["failed_repaired"] == 5
    assert not result["blockers"]

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch18.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}

    mooring = _svg("MORFAC03", result)
    assert 'data-repair-batch="standard-repair-batch18"' in mooring
    assert '<rect x="19" y="19" width="26" height="26"' in mooring
    assert "M23 47 V24" not in mooring
    assert "var(--black)" in mooring

    deviation = _svg("MORFAC04", result)
    assert "M17 50 H47" in deviation
    assert "M22 50 L27 23 H37 L42 50" in deviation
    assert "M32 50 V13" in deviation
    assert "<rect" not in deviation

    mast = _svg("MSTCON04", result)
    assert "M27 50 L32 12 L37 50" in mast
    assert '<circle cx="32" cy="50" r="5.3"' in mast
    assert "var(--brown)" in mast
    assert "M32 12 V50" not in mast

    mast_black = _svg("MSTCON14", result)
    assert "M27 50 L32 12 L37 50" in mast_black
    assert "var(--black)" in mast_black

    position = _svg("POSGEN04", result)
    assert '<circle cx="32" cy="32" r="15"' in position
    assert 'r="8"' not in position
    assert 'r="2.8"' not in position
    assert "<path" not in position

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 5
    assert (ROOT / "catalog" / "owned_repair_batch26.md").exists()
    print("standard repair batch 18: OK")


if __name__ == "__main__":
    main()
