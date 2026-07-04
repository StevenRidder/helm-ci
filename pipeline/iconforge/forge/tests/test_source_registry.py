"""Smoke the source registry and exhaustive inventory artifacts.

Run:  python -m forge.tests.test_source_registry
"""
from __future__ import annotations

import json

from .. import source_registry


def main():
    commons = source_registry._json(source_registry.COMMONS_REGISTRY)
    s101 = source_registry._json(source_registry.S101_REGISTRY)
    crosswalk = source_registry._json(source_registry.CROSSWALK)
    exhaustive = source_registry._json(source_registry.EXHAUSTIVE)

    assert commons["counts"]["files"] == 223
    assert commons["counts"]["canonical_eligible_files"] > 150
    assert "public_domain_or_cc0" in commons["counts"]["license_status"]
    assert any(row["canonical_eligible"] for row in commons["files"])
    assert any(not row["canonical_eligible"] for row in commons["files"])

    assert s101["counts"]["svg_symbols"] == 725
    assert s101["counts"]["line_styles"] == 65
    assert s101["counts"]["area_fills"] == 25
    assert s101["counts"]["rules"] == 216
    assert s101["source"]["license_status"] == "no_license_file_detected_in_audit"
    assert s101["source"]["status"] == "license_pending_reference"
    assert s101["counts"]["svg_source_metadata"]

    assert crosswalk["counts"]["rows"] == 824
    assert crosswalk["counts"]["s101_exact_symbol_matches"] >= 240
    assert crosswalk["counts"]["commons_public_domain_candidate_rows"] > 0
    assert crosswalk["counts"]["s101_feature_rule_candidates"] > 100
    serialized_crosswalk = json.dumps(crosswalk)
    for dirty in [
        "TOPSHP09;TE",
        "TOPSHP15;TE",
        "TOPSHP73;TE",
        "TOPSHP81;TE",
        "TOPSHP89;TE",
        "TOPSHPT8;TE",
        "TOWERS74|;TX",
        "QUAPOS01;TX(OBJNAM",
    ]:
        assert dirty not in serialized_crosswalk
    first = crosswalk["rows"][0]
    assert {"s52", "s57", "s101", "commons"} <= set(first)

    statuses = exhaustive["counts"]["statuses"]
    assert exhaustive["counts"]["rows"] == 824
    assert set(statuses) <= set(exhaustive["status_taxonomy"])
    assert statuses["ready"] == 133
    assert statuses["license_blocked"] > 0
    assert statuses["generate_owned"] > 0
    assert exhaustive["counts"]["chart1_mappings_q_rows"] == 62
    print("source registry: OK")


if __name__ == "__main__":
    main()
