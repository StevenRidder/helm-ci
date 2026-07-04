"""Smoke Standard Repair Batch 60.

Run:  python3 -m forge.tests.test_standard_repair_batch60
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_repair_batch60


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "owned_repair_batch68.json"


def _svg(asset: str, result: dict) -> str:
    by_asset = {row["asset"]: row for row in result["symbols"]}
    return (ROOT / by_asset[asset]["after_svg"]).read_text()


def main():
    result = standard_repair_batch60.build(render_outputs=True)
    assert result["status"] == "repair_batch_pending_judge_rerun"
    assert result["summary"]["failed_repaired"] == 14
    assert not result["blockers"]
    assert {len(row.get("after_renders") or {}) for row in result["symbols"]} == {3}
    assert {row["qa"]["visual_parity"] for row in result["symbols"]} == {"repaired_pending_judge_rerun"}

    for row in result["symbols"]:
        svg = _svg(row["asset"], result)
        assert 'data-repair-batch="standard-repair-batch60"' in svg
        assert "generated-owned-artwork" in svg
        assert row["chart1_parity_gate"]

    assert 'points="32,11 16,48 48,48"' in _svg("BOYLAT13", result)
    assert 'points="32,11 16,48 48,48"' in _svg("BOYLAT14", result)
    assert 'points="20,16 44,16 48,48 16,48"' in _svg("BOYLAT23", result)
    assert 'points="20,16 44,16 48,48 16,48"' in _svg("BOYLAT24", result)
    assert '<circle cx="32" cy="32" r="18"' in _svg("BOYLAT25", result)
    assert 'points="28,10 36,10 40,52 24,52"' in _svg("BOYLAT26", result)
    assert 'points="28,10 36,10 40,52 24,52"' in _svg("BOYLAT27", result)
    assert 'points="20,16 44,16 48,48 16,48"' in _svg("BOYLAT52", result)
    assert 'fill="var(--green)"' in _svg("BOYLAT13", result)
    assert 'fill="var(--red)"' in _svg("BOYLAT14", result)
    assert _svg("BOYLAT55", result).count('data-pattern="horizontal-lateral-band"') == 2

    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["failed_repaired"] == 14
    assert (ROOT / "catalog" / "owned_repair_batch68.md").exists()
    print("standard repair batch 60: OK")


if __name__ == "__main__":
    main()
