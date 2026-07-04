"""Smoke Standard Repair Batch 69.

Run:  python3 -m forge.tests.test_standard_repair_batch69
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch69


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch77.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch69.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == len(standard_repair_batch69.TARGETS)
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch69.TARGETS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["source_judge"] for row in result["symbols"]} == {
        "catalog/standard_judge_batch_008.json",
        "catalog/standard_judge_batch_010.json",
        "catalog/standard_judge_batch_043_rerun.json",
    }

    assert 'data-repair-batch="standard-repair-batch69"' in _svg("HECMTR01", result)
    assert '<polygon points="32,28 36,32 32,36 28,32"' in _svg("HECMTR01", result)
    assert '<path d="M28 32 H36"' in _svg("OSPONE02", result)
    assert '<path d="M26 32 H38"' in _svg("OSPSIX02", result)
    assert 'stroke="var(--orange)"' in _svg("POSITN02", result)
    assert '>HW</text>' in _svg("HGWTMK01", result)
    assert 'fill="var(--blue)"' in _svg("NOTMRK03", result)
    assert '<circle cx="32" cy="32" r="9"' in _svg("ISODGR51", result)
    assert 'C27 35 25 28 24 21' in _svg("PRICKE03", result)
    assert 'C37 35 39 28 40 21' in _svg("PRICKE04", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == len(standard_repair_batch69.TARGETS)
    assert (ROOT / "catalog" / "owned_repair_batch77.md").exists()
    print("standard repair batch 69: OK")


if __name__ == "__main__":
    main()
