"""Smoke Standard Repair Batch 44.

Run:  python3 -m forge.tests.test_standard_repair_batch44
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch44


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch52.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch44.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 9
    assert not result["blockers"]
    assert {row["asset"] for row in result["symbols"]} == set(standard_repair_batch44.REPAIRS)
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assert 'data-repair-batch="standard-repair-batch44"' in _svg("TOPSHPT2", result)
    assert 'points="24,10 52,18 40,54 12,46"' in _svg("TOPSHPT2", result)
    assert 'fill="var(--black)"' in _svg("TOPSHPT3", result)
    assert 'fill="var(--orange)"' in _svg("TOPSHPT6", result)
    assert 'clip_TOPSHPT8_TE_s' in _svg("TOPSHPT8;TE('%s'", result)
    assert '>T</text>' in _svg("TOPSHPT8;TE('%s'", result)
    assert 'points="32,10 14,50 50,50"' in _svg("TOPSHPU1", result)
    assert 'fill="var(--green)"' in _svg("TOPSHPU1", result)
    assert 'fill="var(--red)"' in _svg("TOPSHPU2", result)

    for asset in standard_repair_batch44.REPAIRS:
        svg = _svg(asset, result)
        assert "data-repair-batch=\"standard-repair-batch44\"" in svg
        assert "generated-owned-artwork" in svg

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 9
    assert (ROOT / "catalog" / "owned_repair_batch52.md").exists()
    print("standard repair batch 44: OK")


if __name__ == "__main__":
    main()
