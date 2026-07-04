"""Smoke Standard Repair Batch 70.

Run:  python3 -m forge.tests.test_standard_repair_batch70
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch70


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch78.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch70.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == len(standard_repair_batch70.TARGETS)
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch70.TARGETS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert all(row["source_judge"] for row in result["symbols"])

    assert ">okm</text>" in _svg("DISMAR03", result)
    assert ">km</text>" in _svg("DISMAR04", result)
    assert 'fill="var(--red)"' in _svg("LITVES60", result)
    assert 'fill="var(--green)"' in _svg("LITVES61", result)
    assert '<circle cx="32" cy="32" r="14"' in _svg("OWNSHP01", result)
    assert 'Q32 12 38 18' in _svg("OWNSHP05", result)
    assert 'stroke="var(--yellow)"' in _svg("RFNERY01", result)
    assert 'stroke="var(--black)"' in _svg("RFNERY11", result)
    assert 'stroke="var(--orange)"' in _svg("SCALEB10", result)
    assert 'stroke="var(--black)"' in _svg("SCALEB11", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == len(standard_repair_batch70.TARGETS)
    assert (ROOT / "catalog" / "owned_repair_batch78.md").exists()
    print("standard repair batch 70: OK")


if __name__ == "__main__":
    main()
