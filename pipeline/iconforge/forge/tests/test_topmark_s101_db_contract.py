"""Smoke the DB-backed S-52 TOPSHP -> S-101 TOPMAR mapping contract.

Run:  python3 -m forge.tests.test_topmark_s101_db_contract
"""
from __future__ import annotations

from .. import topmark_s101_db_contract


def _asset(result: dict, asset: str) -> dict:
    for row in result["asset_rows"]:
        if row["asset"] == asset:
            return row
    raise AssertionError(f"missing asset {asset}")


def _rows(result: dict, asset: str) -> list[dict]:
    return [row for row in result["rows"] if row.get("asset") == asset]


def main():
    result = topmark_s101_db_contract.build(write=False)
    summary = result["summary"]

    assert summary["schema"] == "helm.forge.s101-topmark-db-mapping.v1"
    assert summary["row_level_mappings"] >= 280
    assert summary["shape_safe_row_mappings"] >= 180
    assert summary["shape_safe_asset_overlays"] >= 120

    # TOPSHP 28 is T-shape. Daymark/beacon context must resolve through the
    # rigid TOPMAR02 table to TOPMAR89, not to a host beacon shape.
    topshq28 = _asset(result, "TOPSHQ28")
    assert topshq28["asset_status"] == "unambiguous_shape_witness"
    assert topshq28["source_topmark_shape_code"] == 28
    assert topshq28["topmark_context"] == "rigid"
    assert topshq28["s101_symbol_id"] == "TOPMAR89"
    assert topshq28["shape_safe"] == 1

    # "Other" and standalone flag cases are S-101 rule outputs, but not
    # shape-safe witnesses for drawing promotion.
    topshp00 = _asset(result, "TOPSHP00")
    assert topshp00["asset_status"] == "default_witness_not_shape_safe"
    assert topshp00["shape_safe"] == 0
    assert all(row["s101_symbol_id"] == "TMARDEF1" for row in _rows(result, "TOPSHP00"))

    topshpj3 = _asset(result, "TOPSHPJ3")
    assert topshpj3["asset_status"] == "context_required"
    assert topshpj3["shape_safe"] == 0

    # S-52 and S-101 direct-looking TOPMAR filenames are not trusted as a
    # one-to-one mapping. The shape code decides the S-101 witness.
    topmar87 = _asset(result, "TOPMAR87")
    topmar88 = _asset(result, "TOPMAR88")
    assert topmar87["source_topmark_shape_code"] == 15
    assert topmar87["s101_symbol_id"] == "TOPMAR88"
    assert topmar88["source_topmark_shape_code"] == 16
    assert topmar88["s101_symbol_id"] == "TOPMAR87"

    # Multi-meaning asset ids stay manual instead of being collapsed to one
    # misleading preview witness.
    topmar01 = _asset(result, "TOPMAR01")
    assert topmar01["asset_status"] == "manual_review_ambiguous_asset"
    assert topmar01["shape_safe"] == 0
    assert not topmar01["s101_symbol_id"]

    unsafe_assets = [
        row
        for row in result["asset_rows"]
        if row["shape_safe"] and row.get("s101_symbol_id") in topmark_s101_db_contract.DEFAULT_WITNESSES
    ]
    assert not unsafe_assets

    print("topmark S-101 DB contract: OK")


if __name__ == "__main__":
    main()
