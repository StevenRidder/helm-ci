"""Smoke Standard Repair Batch 63.

Run:  python3 -m forge.tests.test_standard_repair_batch63
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch63


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch71.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch63.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 10
    assert not result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assets = {row["asset"] for row in result["symbols"]}
    assert assets == {
        "TOPMA100", "TOPMA102", "TOPMA106", "TOPMA107", "TOPMA109",
        "TOPMA113", "TOPMA114", "TOPMA115", "TOPMA116", "TOPMA117",
    }

    assert 'data-repair-batch="standard-repair-batch63"' in _svg("TOPMA100", result)
    assert "generated-owned-artwork" in _svg("TOPMA100", result)
    assert 'points="18,16 46,16 32,50"' in _svg("TOPMA100", result)
    assert 'points="32,14 18,48 46,48"' in _svg("TOPMA102", result)
    assert 'data-pattern="horizontal-topmark-band"' in _svg("TOPMA106", result)
    assert 'stroke="var(--red)" stroke-width="4"' in _svg("TOPMA107", result)
    assert 'points="32,14 50,32 32,50 14,32"' in _svg("TOPMA109", result)
    assert 'stroke="var(--yellow)" stroke-width="5"' in _svg("TOPMA113", result)
    assert '<circle cx="32" cy="32" r="17"' in _svg("TOPMA117", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 10
    assert (ROOT / "catalog" / "owned_repair_batch71.md").exists()
    print("standard repair batch 63: OK")


if __name__ == "__main__":
    main()
