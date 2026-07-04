"""Smoke Standard Repair Batch 71.

Run:  python3 -m forge.tests.test_standard_repair_batch71
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch71


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch79.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch71.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == len(standard_repair_batch71.TARGETS)
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch71.TARGETS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert all(row["source_judge"] for row in result["symbols"])

    assert '<circle cx="32" cy="32" r="5" fill="var(--brown)"' in _svg("SILBUI01", result)
    assert '<circle cx="32" cy="32" r="5" fill="var(--black)"' in _svg("SILBUI11", result)
    assert 'M26 24 V40 M32 24 V40 M38 24 V40' in _svg("TMBYRD01", result)
    assert _svg("TNKFRM01", result).count('r="2.1"') == 4
    assert 'stroke="var(--magenta)"' in _svg("TRNBSN01", result)
    assert 'S34 41 37 36' in _svg("WATTUR02", result)
    assert 'M20 35 C28 31 36 37 44 32' in _svg("WEDKLP03", result)
    assert '>WL</text>' in _svg("WTLVGG01", result)
    assert '<rect x="29" y="20" width="7" height="24"' in _svg("WTLVGG02", result)
    assert '<circle cx="32" cy="32" r="8"' in _svg("WAYPNT01", result)
    assert '<circle cx="32" cy="32" r="4"' in _svg("WAYPNT11", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == len(standard_repair_batch71.TARGETS)
    assert (ROOT / "catalog" / "owned_repair_batch79.md").exists()
    print("standard repair batch 71: OK")


if __name__ == "__main__":
    main()
