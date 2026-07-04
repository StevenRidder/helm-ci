"""Smoke Standard Repair Batch 41.

Run:  python3 -m forge.tests.test_standard_repair_batch41
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch41


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch49.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch41.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 20
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch41.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert 'data-repair-batch="standard-repair-batch41"' in _svg("TOPSHP47", result)
    assert '<rect x="19" y="12" width="26" height="40" fill="var(--red)"' in _svg("TOPSHP47", result)
    assert '<rect x="19" y="12" width="26" height="40" fill="var(--green)"' in _svg("TOPSHP48", result)
    assert 'points="32,8 56,32 32,56 8,32"' in _svg("TOPSHP51", result)
    assert 'clip_TOPSHP51' in _svg("TOPSHP51", result)
    assert 'fill="var(--black)"' in _svg("TOPSHP52", result)
    assert 'fill="var(--yellow)"' in _svg("TOPSHP53", result)
    assert 'fill="var(--orange)"' in _svg("TOPSHP61", result)
    assert 'fill="var(--green)"' in _svg("TOPSHP64", result)
    assert 'fill="var(--red)"' in _svg("TOPSHP72", result)
    assert 'clip_TOPSHP73_TE_s' in _svg("TOPSHP73;TE('%s'", result)
    assert '>T</text>' in _svg("TOPSHP73;TE('%s'", result)
    assert _svg("TOPSHP74", result).count('fill="var(--red)"') >= 2

    for asset in standard_repair_batch41.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch41\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 20
    assert (ROOT / "catalog" / "owned_repair_batch49.md").exists()
    print("standard repair batch 41: OK")


if __name__ == "__main__":
    main()
