"""Smoke the clean-room symbol package manifest.

Run:  python3 -m forge.tests.test_cleanroom_symbol_manifest
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import cleanroom_symbol_manifest


def main() -> None:
    payload = cleanroom_symbol_manifest.build_manifest()
    assert payload["schema"] == "helm.symbol.cleanroom-registry.v1"
    assert payload["summary"]["db_candidates"] == 3057
    assert payload["summary"]["symbols"] == 2636
    assert payload["summary"]["blocked_non_symbol_candidates"] == 421
    assert payload["summary"]["runtime_rows"] == 0
    assert payload["summary"]["hard_pile_rows"] == 3057
    assert payload["source"]["db"] == "artifacts/opencpn_s52_portrayal.sqlite"
    assert payload["source"]["semantic_evidence"] == "pipeline/iconforge/catalog/semantic_evidence_db.json"
    assert payload["source"]["proof_manifest"] == "pipeline/iconforge/proof/manifest.json"
    assert set(cleanroom_symbol_manifest.RENDER_TARGETS).issubset(set(payload["render_targets"]))
    assert payload["source_boundary"]["forbidden_source_assets"]
    assert payload["blocked_candidates"]

    rows = {row["symbol_id"]: row for row in payload["symbols"] if row["symbol_id"]}
    boypil60 = rows["BOYPIL60"]
    assert boypil60["source_refs"]["s101"]["feature_type"] == "LateralBuoy"
    assert boypil60["source_refs"]["s101"]["attributes"]["colour"] == ["red"]
    assert boypil60["assets"]["canonical_svg"].endswith("BOYPIL60.svg")
    assert boypil60["qa"]["status"] in {"blocked", "needs_review"}
    assert boypil60["qa"]["runtime_eligible"] is False
    assert boypil60["provenance"]["source_boundary"]["third_party_artwork_is_source"] is False

    assert all(
        (row["assets"].get("canonical_svg") or row["rendering"].get("recipe"))
        for row in payload["symbols"]
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        result = cleanroom_symbol_manifest.write_manifest(
            json_path=tmp / "symbols.json",
            yaml_path=tmp / "symbols.yaml",
            schema_path=tmp / "symbol.schema.json",
        )
        written = json.loads((tmp / "symbols.json").read_text())
        schema = json.loads((tmp / "symbol.schema.json").read_text())
        assert result["summary"]["symbols"] == 2636
        assert written["schema"] == payload["schema"]
        assert schema["properties"]["symbols"]["items"]["properties"]["assets"]
        assert json.loads((tmp / "symbols.yaml").read_text())["schema"] == payload["schema"]

    print("cleanroom symbol manifest: OK")


if __name__ == "__main__":
    main()
