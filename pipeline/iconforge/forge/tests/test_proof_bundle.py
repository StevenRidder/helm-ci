"""Smoke the public clean-room proof bundle.

Run:  python3 -m forge.tests.test_proof_bundle
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import proof_bundle


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = proof_bundle.build(Path(tmp) / "proof")
        coverage = result["coverage"]
        assert result["status"] == "proof_bundle_written"
        assert coverage["total"] == 824
        assert coverage["generated"] == 824
        assert coverage["accepted"] == 0
        assert coverage["needs_review"] == 824
        assert coverage["manual_review_required"] == 110
        assert coverage["s101_resolver_status_counts"].get("unresolved", 0) == 0
        assert coverage["s101_resolver_status_counts"]["resolved_rule_catalogue"] == 90
        assert coverage["s101_crosswalk_class_counts"]["s101_feature_equivalent"] == 549
        assert coverage["s101_crosswalk_class_counts"]["non_s101_runtime_construct"] == 44

        out = Path(tmp) / "proof"
        for name in [
            "manifest.json",
            "coverage.json",
            "missing-hard-pile.json",
            "chartplotter-rule-input.json",
            "index.html",
            "compare-opencpn.html",
        ]:
            assert (out / name).exists(), name

        manifest = json.loads((out / "manifest.json").read_text())
        assert manifest["schema"] == "helm.symbol.cleanroom-package.v1"
        assert "OpenCPN/Vulkan" in manifest["render_targets"]
        assert "iOS/native" in manifest["render_targets"]
        assert manifest["approval_workflow"]["endpoints"]["save_review"] == "/api/save-review"
        assert manifest["approval_workflow"]["endpoints"]["save_signoff"] == "/api/save-signoff"
        assert manifest["source_boundary"]["publish_gate"].startswith("only accepted")
        assert manifest["coverage"]["s101_crosswalk_class_counts"]["non_s101_or_inland_extension"] == 123
        serialized_manifest = json.dumps(manifest)
        for dirty in [
            "TOPSHP09;TE",
            "TOPSHP15;TE",
            "TOPSHP73;TE",
            "TOPSHP81;TE",
            "TOPSHP89;TE",
            "TOPSHPT8;TE",
            "TOWERS74|;TX",
            "QUAPOS01;TX(OBJNAM",
            "missing_s101_feature_type",
        ]:
            assert dirty not in serialized_manifest

        rules = json.loads((out / "chartplotter-rule-input.json").read_text())
        assert rules["schema"] == "helm.symbol.chartplotter-rule-input.v1"
        assert rules["status"] == "provisional_not_runtime_default"
        assert all(not row["runtime_eligible"] for row in rules["rows"])
        assert all(row["s101_crosswalk_classification"] for row in rules["rows"])

        assert len(list((out / "svg-day").glob("*.svg"))) == 824
        assert len(list((out / "svg-dusk").glob("*.svg"))) == 824
        assert len(list((out / "svg-night").glob("*.svg"))) == 824
        sample = (out / "svg-day" / "ACHARE02.svg").read_text()
        assert "var(--" not in sample
        assert "#c545c3" in sample
        assert "TOPSHP09;TE" not in (out / "svg-day" / "TOPSHP09.svg").read_text()
        assert "TOWERS74|;TX" not in (out / "svg-day" / "TOWERS74.svg").read_text()

        index = (out / "index.html").read_text()
        compare = (out / "compare-opencpn.html").read_text()
        assert "Helm Clean-room Symbol Catalog" in index
        assert "Helm/OpenCPN Symbol Proof" in compare
        assert "comparison target only" in compare
    print("proof bundle: OK")


if __name__ == "__main__":
    main()
