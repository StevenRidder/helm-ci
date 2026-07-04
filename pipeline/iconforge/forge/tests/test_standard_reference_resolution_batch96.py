"""Smoke Standard Reference Resolution Batch 96.

Run:  python3 -m forge.tests.test_standard_reference_resolution_batch96
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import standard_reference_resolution_batch96


ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "catalog" / "standard_reference_resolution_batch96.json"
SPECS = ROOT / "catalog" / "symbol_specs_batch96.json"


def main():
    result = standard_reference_resolution_batch96.build()
    summary = result["summary"]
    assert result["status"] == "reference_resolution_batch96_written"
    assert summary["rows_classified"] == 26
    assert summary["symbol_specs"] == 7
    assert summary["renderable_from_s57_symbolspec"] == 2
    assert summary["reference_blocked_official_symbol"] == 3
    assert summary["manual_exception_newobj_placeholder"] == 2
    assert summary["style_primitive_not_standalone_icon"] == 4
    assert summary["portrayal_rule_not_standalone_icon"] == 15
    by_asset = {row["asset"]: row for row in result["records"]}
    assert by_asset["BCNCON81"]["next_action"] == "render_batch_from_symbolspec"
    assert by_asset["boyspp50"]["next_action"] == "render_batch_from_symbolspec"
    assert by_asset["DANGER53"]["next_action"] == "attach_tight_reference_before_render"
    assert by_asset["NEWOBJ01"]["classification"] == "manual_exception_newobj_placeholder"
    assert by_asset["DASH"]["classification"] == "style_primitive_not_standalone_icon"
    assert by_asset["RESARE01"]["classification"] == "portrayal_rule_not_standalone_icon"
    specs = {row["id"]: row for row in result["symbol_specs"]}
    assert set(specs) == {
        "BCNCON81",
        "DANGER53",
        "DGPS01DRFSTA01",
        "NEWOBJ 01",
        "NEWOBJ01",
        "VEHTRF01",
        "boyspp50",
    }
    assert specs["BCNCON81"]["geometry"]["colours"] == ["blue", "red", "white", "blue"]
    assert specs["boyspp50"]["geometry"]["colours"] == ["yellow"]
    assert REPORT.exists()
    assert SPECS.exists()
    assert (ROOT / "catalog" / "standard_reference_resolution_batch96.csv").exists()
    assert (ROOT / "catalog" / "standard_reference_resolution_batch96.md").exists()
    assert (ROOT / "catalog" / "symbol_specs_batch96.yaml").exists()
    assert (ROOT / "catalog" / "symbol_specs_batch96.md").exists()
    saved = json.loads(REPORT.read_text())
    assert saved["summary"]["rows_classified"] == 26
    print("standard reference resolution batch 96: OK")


if __name__ == "__main__":
    main()
