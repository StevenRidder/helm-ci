"""Smoke Standard Repair Batch 64.

Run:  python3 -m forge.tests.test_standard_repair_batch64
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch64


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch72.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch64.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 9
    assert not result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assets = {row["asset"] for row in result["symbols"]}
    assert assets == {
        "TOPMAR01", "TOPMAR87", "TOPMAR88", "TOPMAR90", "TOPMAR91",
        "TOPMAR92", "TOPMAR93", "TOPMAR98", "TOPMAR99",
    }

    assert 'data-repair-batch="standard-repair-batch64"' in _svg("TOPMAR01", result)
    assert '<circle cx="32" cy="32" r="17"' in _svg("TOPMAR01", result)
    assert 'M32 18 V45' in _svg("TOPMAR87", result)
    assert 'M24 22 L32 45 L40 22' in _svg("TOPMAR87", result)
    assert 'M32 46 V19' in _svg("TOPMAR88", result)
    assert 'M24 42 L32 19 L40 42' in _svg("TOPMAR88", result)
    assert 'M32 16 V46' in _svg("TOPMAR90", result)
    assert 'M32 48 V18' in _svg("TOPMAR93", result)
    assert '<rect x="27" y="25" width="10" height="14"' in _svg("TOPMAR91", result)
    assert 'points="32,13 51,32 32,51 13,32"' in _svg("TOPMAR98", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 9
    assert (ROOT / "catalog" / "owned_repair_batch72.md").exists()
    print("standard repair batch 64: OK")


if __name__ == "__main__":
    main()
