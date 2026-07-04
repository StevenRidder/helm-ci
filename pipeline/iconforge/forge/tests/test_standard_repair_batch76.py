"""Smoke Standard Repair Batch 76.

Run:  python3 -m forge.tests.test_standard_repair_batch76
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch76


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch84.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch76.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == len(standard_repair_batch76.TARGETS)
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch76.TARGETS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["asset"] for row in result["blockers"]} == {"DANGER53", "DGPS01DRFSTA01", "NEWOBJ 01", "NEWOBJ01"}
    assert all(row["source_judge"] for row in result["symbols"])

    bcncon81 = _svg("BCNCON81", result)
    assert bcncon81.index('fill="var(--blue)"') < bcncon81.index('fill="var(--red)"')
    assert bcncon81.count('fill="var(--blue)"') == 2
    assert bcncon81.count('fill="var(--red)"') == 1
    assert bcncon81.count('fill="var(--white)"') >= 1

    topshp09 = _svg("TOPSHP09;TE('%s'", result)
    assert 'fill="var(--green)"' in topshp09
    assert 'data-pattern="s57-horizontal-topmark"' in topshp09
    assert 'data-cue="s52-text-bearing-row"' in topshp09

    topshp15 = _svg("TOPSHP15;TE('%s'", result)
    assert 'fill="var(--yellow)"' in topshp15
    assert 'data-pattern="s57-horizontal-topmark"' in topshp15

    assert 'M27 21 H40 L37 43 H24 Z' in _svg("TOPSHP33", result)
    assert 'stroke="var(--orange)"' in _svg("TOWERS74|;TX(OBJNAM", result)
    assert 'fill="var(--red)"' in _svg("VEHTRF01", result)
    assert 'fill="var(--green)"' in _svg("VEHTRF01", result)
    assert 'fill="var(--yellow)"' in _svg("boyspp50", result)
    assert "generic_symbol" not in "".join(_svg(asset, result) for asset in standard_repair_batch76.TARGETS)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == len(standard_repair_batch76.TARGETS)
    assert (ROOT / "catalog" / "owned_repair_batch84.md").exists()
    print("standard repair batch 76: OK")


if __name__ == "__main__":
    main()
