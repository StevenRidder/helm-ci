"""Smoke Standard Repair Batch 62.

Run:  python3 -m forge.tests.test_standard_repair_batch62
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch62


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch70.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch62.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 12
    assert result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    assets = {row["asset"] for row in result["symbols"]}
    assert assets == {
        "TOPSHP00", "TOPSHP01", "TOPSHP02", "TOPSHP03", "TOPSHP04", "TOPSHP08",
        "TOPSHP16", "TOPSHP17", "TOPSHP18", "TOPSHP19", "TOPSHP20", "TOPSHP21",
    }

    assert 'data-repair-batch="standard-repair-batch62"' in _svg("TOPSHP00", result)
    assert "generated-owned-artwork" in _svg("TOPSHP00", result)
    assert '<path d="M32 24 V40 M24 32 H40"' in _svg("TOPSHP00", result)
    assert 'data-pattern="vertical-topshape-band"' in _svg("TOPSHP01", result)
    assert 'fill="var(--orange)"' in _svg("TOPSHP01", result)
    assert 'fill="var(--black)"' in _svg("TOPSHP02", result)
    assert 'data-pattern="horizontal-topshape-band"' in _svg("TOPSHP08", result)
    assert 'fill="var(--yellow)"' in _svg("TOPSHP19", result)
    assert '<rect x="18" y="14" width="28" height="36"' in _svg("TOPSHP21", result)

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 12
    assert (ROOT / "catalog" / "owned_repair_batch70.md").exists()
    print("standard repair batch 62: OK")


if __name__ == "__main__":
    main()
