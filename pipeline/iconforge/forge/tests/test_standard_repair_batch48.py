"""Smoke Standard Repair Batch 48.

Run:  python3 -m forge.tests.test_standard_repair_batch48
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch48


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch56.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch48.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 17
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch48.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}
    assert {row["source_judge"] for row in result["symbols"]} == {"catalog/standard_judge_batch_054_rerun.json"}

    assert 'data-repair-batch="standard-repair-batch48"' in _svg("BOYCON78", result)
    assert _svg("BOYCON78", result).count('data-pattern="vertical-stripe"') == 4
    assert 'points="32,11 16,48 48,48"' in _svg("BOYCON78", result)
    assert 'points="32,11 16,48 48,48"' not in _svg("BOYCON79", result)
    assert 'M32 10 V56' in _svg("BOYCON79", result)
    assert 'fill="var(--green)"' in _svg("BOYCON79", result)

    assert _svg("BOYISD12", result).count('data-mark="paired-red"') == 2
    assert 'data-mark="mooring-ring"' in _svg("BOYMOR01", result)
    assert 'fill="var(--green)"' in _svg("BOYMOR03", result)
    assert 'fill="var(--black)"' in _svg("BOYMOR03", result)
    assert 'data-mark="mooring-ring"' in _svg("BOYMOR11", result)
    assert 'points="24,12 40,12 46,48 18,48"' in _svg("BOYPIL01", result)
    assert 'fill="var(--black)"' in _svg("BOYPIL01", result)
    assert _svg("BOYPIL73", result).count('data-pattern="vertical-stripe"') == 4
    assert '<circle cx="32" cy="32" r="18" fill="var(--red)"' in _svg("BOYSAW12", result)
    assert 'fill="var(--red)"' in _svg("BOYSPH01", result)
    assert 'fill="var(--black)"' in _svg("BOYSPH01", result)
    assert _svg("BOYSPH65", result).count('data-pattern="vertical-stripe"') == 4

    assert 'fill="var(--yellow)"' in _svg("BOYSPP11", result)
    assert 'points="32,11 16,48 48,48"' in _svg("BOYSPP15", result)
    assert 'fill="var(--yellow)"' in _svg("BOYSPP15", result)
    assert 'points="20,16 44,16 48,48 16,48"' in _svg("BOYSPP25", result)
    assert 'fill="var(--yellow)"' in _svg("BOYSPP25", result)
    assert 'points="18,18 46,18 52,40 42,52 22,52 12,40"' in _svg("BOYSUP01", result)
    assert 'data-topmark="lanby-asterisk"' in _svg("BOYSUP03", result)
    assert _svg("BOYSUP65", result).count('data-pattern="vertical-stripe"') == 4

    for asset in standard_repair_batch48.REPAIRS:
        svg = _svg(asset, result)
        assert "generated-owned-artwork" in svg
        assert "var(--" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 17
    assert (ROOT / "catalog" / "owned_repair_batch56.md").exists()
    print("standard repair batch 48: OK")


if __name__ == "__main__":
    main()
