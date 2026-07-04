"""Smoke Standard Repair Batch 47.

Run:  python3 -m forge.tests.test_standard_repair_batch47
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch47


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch55.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch47.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 1
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == {"BOYCON81"}
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    svg = _svg("BOYCON81", result)
    assert 'data-repair-batch="standard-repair-batch47"' in svg
    assert 'points="32,11 16,48 48,48"' in svg
    assert svg.count('fill="var(--blue)"') >= 3
    assert 'fill="var(--red)"' in svg
    assert 'fill="var(--white)"' in svg
    assert "generated-owned-artwork" in svg
    assert "COLPAT1,2" in result["symbols"][0]["provenance"]["reference_role"]

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 1
    assert (ROOT / "catalog" / "owned_repair_batch55.md").exists()
    print("standard repair batch 47: OK")


if __name__ == "__main__":
    main()
