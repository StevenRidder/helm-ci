"""Smoke Standard Repair Batch 27.

Run:  python3 -m forge.tests.test_standard_repair_batch27
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch27


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch35.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch27.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 11
    assert not result["blockers"]

    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch27.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert "var(--orange)" in _svg("TIDCUR01", result)
    assert "M32 55 V10" in _svg("TIDCUR01", result)
    assert '<circle cx="43" cy="13"' in _svg("TIDCUR02", result)
    assert '<rect x="18" y="23"' in _svg("TIDCUR03", result)

    tide_height = _svg("TIDEHT01", result)
    assert "var(--gray)" in tide_height
    assert "C18 20 34 20" in tide_height

    assert "M32 11 L53 32 L32 53 L11 32 Z" in _svg("TIDSTR01", result)
    assert "C14 36 14 25" in _svg("SNDWAV02", result)
    assert "M16 48 H48" in _svg("SPRING02", result)
    assert "M14 18 V46 H50 V18" in _svg("SWPARE51", result)

    mine = _svg("PRDINS02", result)
    assert "var(--brown)" in mine
    assert "<circle" not in mine

    quarry = _svg("QUARRY01", result)
    assert '<circle cx="32" cy="32" r="24"' in quarry
    assert "var(--brown)" in quarry

    pssa = _svg("PSSARE01", result)
    assert ">PSSA</text>" in pssa
    assert "var(--magenta)" in pssa

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 11
    assert (ROOT / "catalog" / "owned_repair_batch35.md").exists()
    print("standard repair batch 27: OK")


if __name__ == "__main__":
    main()
