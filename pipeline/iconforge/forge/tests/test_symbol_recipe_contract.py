"""Smoke the FORGE-28 Helm symbol recipe contract.

Run:
  python3 -m forge.tests.test_symbol_recipe_contract
"""
from __future__ import annotations

from copy import deepcopy

from .. import semantic_evidence_db, symbol_recipe_contract


def _row(result: dict, symbol_id: str) -> dict:
    for row in result["rows"]:
        if row["symbol_id"] == symbol_id:
            return row
    raise AssertionError(f"missing symbol row {symbol_id}")


def _assert_ready_recipe(row: dict, shape_family: str, colours: list[str], pattern: str) -> None:
    recipe = row["helm_symbol_recipe"]
    assert row["helm_symbol_recipe_status"] == "recipe_ready"
    assert recipe["status"] == "recipe_ready"
    assert recipe["shape_family"] == shape_family
    assert recipe["color_tokens"] == colours
    assert recipe["pattern_token"] == pattern
    assert recipe["palette_version"] == symbol_recipe_contract.PALETTE_VERSION
    assert recipe["style_version"] == symbol_recipe_contract.STYLE_VERSION
    assert recipe["backend_resolved"] is True
    assert recipe["browser_business_logic_allowed"] is False
    assert recipe["runtime_export_allowed"] is False


def main() -> None:
    semantic = semantic_evidence_db.build()
    contract = symbol_recipe_contract.build()

    assert contract["schema"] == "helm.forge.symbol-recipe-contract.v1"
    assert contract["status"] == "provisional_symbol_recipe_contract_ready"
    assert contract["coverage"]["rows"] == 824
    assert contract["coverage"]["status_counts"] == {
        "manual_exception_required": 206,
        "recipe_missing": 44,
        "recipe_ready": 574,
    }
    assert contract["consumer_contract"]["backend_db_source_of_truth"] is True
    assert contract["consumer_contract"]["browser_business_logic_allowed"] is False
    assert contract["consumer_contract"]["hidden_fallbacks_allowed"] is False
    assert contract["consumer_contract"]["runtime_export_allowed"] is False

    defaults = contract["global_defaults"]
    assert set(defaults["palettes"]) == {"day", "dusk", "night"}
    for token in ["red", "green", "yellow", "black", "white", "magenta", "blue"]:
        assert token in defaults["supported_color_tokens"]
        assert token in defaults["palettes"]["day"]
    for pattern in [
        "solid",
        "horizontal_bands",
        "vertical_stripes",
        "ordered_sequence",
        "notice_pictogram",
        "line_dash",
    ]:
        assert pattern in defaults["patterns"]
    for family in [
        "buoy_can",
        "buoy_cone",
        "buoy_pillar",
        "buoy_spar",
        "buoy_sphere",
        "buoy_barrel",
        "beacon_general",
        "beacon_stake",
        "beacon_tower",
        "tower_lighthouse",
        "topmark_standard",
        "daymark_panel",
        "notice_mark",
        "isolated_danger_mark",
    ]:
        assert family in defaults["shape_families"]

    for row in semantic["rows"]:
        recipe = row["helm_symbol_recipe"]
        assert row["helm_symbol_recipe_status"] == recipe["status"]
        assert row["consumer_contract"]["browser_business_logic_allowed"] is False
        assert row["consumer_contract"]["browser_symbol_recipe_logic_allowed"] is False
        assert row["consumer_contract"]["symbol_recipe_source"] == "FORGE-28:helm_symbol_recipe_v1"
        assert row["runtime_gate_summary"]["helm_symbol_recipe_status"] == recipe["status"]
        assert row["runtime_gate_summary"]["helm_symbol_recipe_ready"] == (recipe["status"] == "recipe_ready")

    boycan60 = _row(semantic, "BOYCAN60")
    _assert_ready_recipe(boycan60, "buoy_can", ["red"], "solid")
    boycan_svg = symbol_recipe_contract.render_recipe_svg(boycan60["helm_symbol_recipe"])
    assert 'viewBox="0 0 64 64"' in boycan_svg
    assert 'data-shape-family="buoy_can"' in boycan_svg
    assert 'data-color-order="red"' in boycan_svg
    assert 'stroke="var(--ink)"' in boycan_svg
    assert 'stroke-width="1.8"' in boycan_svg
    assert 'data-optical-center="32,32"' in boycan_svg

    boylat53 = _row(semantic, "BOYLAT53")
    _assert_ready_recipe(boylat53, "buoy_generic", ["green", "red", "green"], "horizontal_bands")
    boylat_svg = symbol_recipe_contract.render_recipe_svg(boylat53["helm_symbol_recipe"])
    assert 'data-band-orientation="horizontal"' in boylat_svg
    assert 'data-color-order="green,red,green"' in boylat_svg
    assert boylat_svg.count('data-token="green"') == 2

    boycon63 = _row(semantic, "BOYCON63")
    _assert_ready_recipe(boycon63, "buoy_cone", ["black", "red", "black"], "horizontal_bands")
    assert boycon63["helm_symbol_recipe"]["color_source"] == "s57_description.required_colours_repair"
    boycon_svg = symbol_recipe_contract.render_recipe_svg(boycon63["helm_symbol_recipe"])
    assert 'data-band-orientation="horizontal"' in boycon_svg
    assert 'data-color-order="black,red,black"' in boycon_svg
    assert boycon_svg.count("<rect") == 3

    topshq28 = _row(semantic, "TOPSHQ28")
    _assert_ready_recipe(topshq28, "daymark_panel", ["red", "black", "white"], "vertical_stripes")
    topshq_svg = symbol_recipe_contract.render_recipe_svg(topshq28["helm_symbol_recipe"])
    assert 'data-band-orientation="vertical"' in topshq_svg
    assert 'data-color-order="red,black,white"' in topshq_svg
    assert topshq_svg.count("<rect") == 3

    topma114 = _row(semantic, "TOPMA114")
    _assert_ready_recipe(topma114, "topmark_standard", ["red"], "solid")

    nmkinf02 = _row(semantic, "NMKINF02")
    _assert_ready_recipe(nmkinf02, "notice_mark", ["black", "white"], "notice_pictogram")
    assert "non_s101_or_extension_profile_required" in nmkinf02["helm_symbol_recipe"]["reason_codes"]

    wrecks01 = _row(semantic, "WRECKS01")
    assert wrecks01["helm_symbol_recipe_status"] == "manual_exception_required"
    assert wrecks01["helm_symbol_recipe"]["shape_family"] == "wreck_symbol"
    assert "colour_sequence_missing_or_reference_defined" in wrecks01["helm_symbol_recipe"]["reason_codes"]
    try:
        symbol_recipe_contract.render_recipe_svg(wrecks01["helm_symbol_recipe"])
    except ValueError as exc:
        assert "manual_exception_required" in str(exc)
    else:
        raise AssertionError("unresolved wreck recipe rendered silently")

    ais = _row(semantic, "AISVES01")
    assert ais["helm_symbol_recipe_status"] == "manual_exception_required"
    assert ais["helm_symbol_recipe"]["shape_family"] == "ais_target"
    assert "non_s101_runtime_construct_runtime_profile_required" in ais["helm_symbol_recipe"]["reason_codes"]

    isodgr = _row(semantic, "ISODGR51")
    assert isodgr["helm_symbol_recipe"]["shape_family"] == "isolated_danger_mark"
    assert isodgr["helm_symbol_recipe_status"] == "manual_exception_required"

    route = _row(semantic, "DASH")
    assert route["helm_symbol_recipe"]["color_tokens"] == ["magenta"]
    assert route["helm_symbol_recipe"]["color_source"] == "s52_instruction_ast.line_styles"
    assert route["helm_symbol_recipe"]["pattern_token"] == "line_dash"

    bad = deepcopy(boycan60)
    bad["s57_attribute_tuple"]["colour_sequence"] = ["not_a_chart_colour"]
    bad_recipe = symbol_recipe_contract.recipe_for_row(bad)
    assert bad_recipe["status"] == "recipe_missing"
    assert "unsupported_color_token:not_a_chart_colour" in bad_recipe["reason_codes"]

    print("symbol recipe contract: OK")


if __name__ == "__main__":
    main()
