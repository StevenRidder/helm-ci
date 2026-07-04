"""Smoke the Chart 1 Mappings semantic target registry.

Run:  python -m forge.tests.test_chart1_semantic_targets
"""
from __future__ import annotations

from .. import chart1_semantic_targets


def main():
    data = chart1_semantic_targets.load_targets()
    errors = chart1_semantic_targets.validate_targets(data)
    assert not errors, errors

    assert data["source"]["id"] == "chart1_mappings_pdf_semantic_targets"
    assert data["source"]["local_pdf"].endswith("Chart 1 Mappings.pdf")
    assert data["source"]["pdf_sha256"] == "6768d3935f312310686d94dc78683fa29f1e5c00901cd9cf0978481cfd54af64"

    targets = {target["target_id"]: target for target in data["targets"]}
    assert targets["SMCFAC_CATSCF_12"]["official_name"] == "Water tap"
    assert targets["SMCFAC_CATSCF_12"]["source_table"]["symbol_cell_status"] == "source_symbol_present"
    assert targets["SMCFAC_CATSCF_16"]["official_name"] == "Showers"
    assert targets["SMCFAC_CATSCF_16"]["source_table"]["symbol_cell_status"] == "no_symbol_in_source_table"
    assert targets["SMCFAC_CATSCF_21"]["official_name"] == "Refuse bin"
    assert targets["SMCFAC_CATSCF_21"]["generation_target"]["expected_symbol"] == "refuse_bin"

    parsed = chart1_semantic_targets.parse_s57_ref("SMCFAC.CATSCF=16")
    assert parsed == {
        "source_ref": "SMCFAC.CATSCF=16",
        "object": "SMCFAC",
        "attributes": [{
            "attribute": "CATSCF",
            "accepted_values": ["16"],
            "match": "value_any",
        }],
    }

    report = chart1_semantic_targets.build_report()
    assert report["status"] == "pass"
    assert report["target_count"] == 3
    assert report["counts"] == {"semantic_only": 2, "source_symbol_present": 1}
    print("chart1 semantic targets: OK")


if __name__ == "__main__":
    main()
