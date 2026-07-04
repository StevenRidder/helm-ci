"""Smoke Standard Repair Batch 22.

Run:  python3 -m forge.tests.test_standard_repair_batch22
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch22


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch30.json"


def _svg(asset: str) -> str:
    return (ROOT / "assets" / "svg" / "owned_repair_batch30" / f"{asset}.svg").read_text()


def main():
    result = standard_repair_batch22.build(render_outputs=True)

    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 8
    assert not result["blockers"]

    rows = {row["asset"]: row for row in result["symbols"]}
    assert set(rows) == {
        "FAIRWY51",
        "FAIRWY52",
        "FLDSTR01",
        "FRYARE51",
        "FSHFAC02",
        "FSHFAC03",
        "HRBFAC09",
        "PILPNT02",
    }

    for row in rows.values():
        assert row["qa"]["visual_parity"] == "repaired_pending_judge_rerun"
        assert row["provenance"]["origin"] == "generated-owned-artwork"
        assert len(row["after_renders"]) == 3
        for render_path in row["after_renders"].values():
            assert (ROOT / render_path).exists()

    fairway_one = _svg("FAIRWY51")
    assert "var(--gray)" in fairway_one
    assert "var(--black)" not in fairway_one
    assert "M26 50 H38 V25 H46 L32 11 L18 25 H26 Z" in fairway_one

    fairway_two = _svg("FAIRWY52")
    assert "var(--gray)" in fairway_two
    assert "M26 14 H38 V39 H46 L32 53 L18 39 H26 Z" in fairway_two

    flood = _svg("FLDSTR01")
    assert "M32 33 L42 43" in flood
    assert "M23 38 H41" not in flood

    ferry = _svg("FRYARE51")
    assert "var(--magenta)" in ferry
    assert "M22 34 H40 L47 38 L40 42 H22 Z" in ferry
    assert "var(--black)" not in ferry

    assert "var(--gray)" in _svg("FSHFAC02")
    assert "var(--brown)" not in _svg("FSHFAC02")
    assert "var(--gray)" in _svg("FSHFAC03")
    assert "var(--brown)" not in _svg("FSHFAC03")

    harbour = _svg("HRBFAC09")
    assert "var(--magenta)" in harbour
    assert "<circle" not in harbour
    assert ">F</text>" not in harbour

    pile = _svg("PILPNT02")
    assert '<circle cx="32" cy="32" r="12"' in pile
    assert "var(--black)" in pile
    assert "<ellipse" not in pile

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 8
    assert (ROOT / "catalog" / "owned_repair_batch30.md").exists()
    print("standard repair batch 22: OK")


if __name__ == "__main__":
    main()
