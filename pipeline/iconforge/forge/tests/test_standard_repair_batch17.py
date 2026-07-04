"""Smoke Standard Repair Batch 17.

Run:  python3 -m forge.tests.test_standard_repair_batch17
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch17


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch25.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch17.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["human_feedback_rows"] == 14
    assert result["summary"]["failed_repaired"] == 14
    assert not result["blockers"]

    repaired = {row["asset"] for row in result["symbols"]}
    assert repaired == set(standard_repair_batch17.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["qa"]["final_approved"] for row in result["symbols"]} == {False}
    assert all(row.get("human_feedback", {}).get("feedback") for row in result["symbols"])

    church = _svg("BUIREL01", result)
    assert 'data-repair-batch="standard-repair-batch17"' in church
    assert "M32 13 V51 M13 32 H51" in church
    assert "M20 20 V27" in church
    assert "V30 L32 17" not in church
    assert "var(--brown)" in church

    church_black = _svg("BUIREL13", result)
    assert "var(--black)" in church_black
    assert "M44 37 V44" in church_black

    gate = _svg("GATCON03", result)
    assert 'r="20"' in gate
    assert "M18 28 H46 M18 36 H46" in gate
    assert "M29 22 L20 32 L29 42 Z" in gate
    assert "M44 22 L35 32 L44 42 Z" in gate
    assert "var(--magenta)" in gate

    gate_closed = _svg("GATCON04", result)
    assert "M18 28 H46 M18 36 H46" in gate_closed
    assert "M32 23 V41" in gate_closed
    assert "var(--black)" not in gate_closed

    hulk = _svg("HULKES01", result)
    assert "M32 12 C43 18" in hulk
    assert "M32 17 V48" in hulk
    assert "V15" not in hulk

    info = _svg("INFORM01", result)
    assert "M20.2 44.8 L38 31" in info
    assert '<rect x="38" y="14" width="17" height="17"' in info

    land = _svg("LNDARE01", result)
    assert 'r="8.5" fill="var(--white)" stroke="var(--brown)"' in land
    assert 'r="5.5" fill="var(--brown)"' in land

    locmag = _svg("LOCMAG01", result)
    assert "M25 49 L38 14 L48 49 Z" in locmag
    assert ">A</text>" not in locmag

    lowacc = _svg("LOWACC01", result)
    assert "M18 20 L46 48" in lowacc
    assert ">?</text>" in lowacc
    assert "<circle" not in lowacc

    magvar = _svg("MAGVAR01", result)
    assert "M30 14 V50" in magvar
    assert "M31 16 L49 25 L31 34 Z" in magvar
    assert ">M</text>" not in magvar

    magvar_line = _svg("MAGVAR51", result)
    assert "M20 50 H43" in magvar_line
    assert "stroke-dasharray" not in magvar_line

    farm = _svg("MARCUL02", result)
    assert '<rect x="14" y="18" width="38" height="30"' in farm
    assert "M21 20 V46" in farm
    assert "C25 25 38 25 47 33" in farm

    monument = _svg("MONUMT02", result)
    assert "M27 30 L36 24" in monument
    assert '<ellipse cx="32" cy="54" rx="7" ry="3.5"' in monument
    assert "var(--brown)" in monument

    monument_black = _svg("MONUMT12", result)
    assert "var(--black)" in monument_black

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 14
    assert (ROOT / "catalog" / "owned_repair_batch25.md").exists()
    print("standard repair batch 17: OK")


if __name__ == "__main__":
    main()
