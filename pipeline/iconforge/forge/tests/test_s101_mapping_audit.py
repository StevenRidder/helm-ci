"""Smoke the S-101 mapping audit.

Run:  python3 -m forge.tests.test_s101_mapping_audit
"""
from __future__ import annotations

from .. import s101_mapping_audit


def main() -> None:
    result = s101_mapping_audit.build()
    coverage = result["coverage"]
    checks = result["consistency_checks"]
    assert result["schema"] == "helm.forge.s101-mapping-audit.v1"
    assert result["status"] == "pass"
    assert coverage["rows"] == 824
    assert coverage["all_rows_accounted_for"] is True
    assert coverage["all_rows_classified"] is True
    assert coverage["all_rows_s101_feature_equivalent"] is False
    assert coverage["s101_feature_equivalent"] == 657
    assert coverage["non_s101_or_extension"] == 167
    assert coverage["unresolved"] == 0
    assert coverage["resolver_status_counts"] == {
        "classified_extension_requires_profile": 123,
        "classified_non_s101_runtime": 44,
        "resolved_direct": 244,
        "resolved_rule": 215,
        "resolved_rule_catalogue": 90,
        "resolved_with_deviation": 108,
    }
    assert coverage["s101_crosswalk_class_counts"] == {
        "non_s101_or_inland_extension": 123,
        "non_s101_runtime_construct": 44,
        "s101_feature_equivalent": 549,
        "s101_feature_equivalent_with_documented_deviation": 108,
    }
    assert checks["resolved_colour_attribute_mismatches"] == []
    assert checks["human_review_s101_missing_symbol_id"] == []
    assert checks["human_review_s101_missing_shape_witness_note"] == []
    assert checks["passed"] is True
    assert result["unresolved_rows"] == []
    print("S-101 mapping audit: OK")


if __name__ == "__main__":
    main()
