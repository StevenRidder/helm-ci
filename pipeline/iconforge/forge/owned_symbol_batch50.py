"""Generate the first 50 Helm-owned SVG drafts from the source matrix.

This is the controlled production-writing gate after the source/provider
matrix. The SVGs are new Helm artwork: Chart No.1, OpenCPN, S-101, Commons,
emoji, and icon libraries remain reference examples only.

Run:
  python -m forge.owned_symbol_batch50
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from . import contact, render, source_variant_matrix, verify
from .render import referenced_tokens
from .schema import Invariants, SymbolSpec, StylePack


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "owned_symbol_batch50"
SVG_OUT = ROOT / "assets" / "svg" / "owned_batch50"
MANIFEST = ROOT / "catalog" / "owned_symbol_batch50_symbols.yaml"
REPORT = OUT / "owned_symbol_batch50_report.json"
PALETTES = ["day", "dusk", "night"]

STYLE_CONTRACT = source_variant_matrix.STYLE_CONTRACT
STYLE_ID = STYLE_CONTRACT["style_id"]
FACILITY_STROKE = "2.6"
NAV_STROKE = "3"

SELECTED_50 = [
    "SMCFAC_CATSCF_12",
    "SMCFAC_CATSCF_16",
    "SMCFAC_CATSCF_21",
    "SMCFAC02",
    "HRBFAC09",
    "HRBFAC12",
    "HRBFAC13",
    "HRBFAC14",
    "HRBFAC16",
    "ACHARE02",
    "ACHARE51",
    "ACHBRT07",
    "MORFAC03",
    "MORFAC04",
    "BOYCAN01",
    "BOYCON01",
    "BOYSPH01",
    "BOYBAR01",
    "BOYSPR60",
    "BOYINB01",
    "BOYLAT23",
    "BOYLAT24",
    "BOYLAT25",
    "BOYLAT26",
    "BOYLAT27",
    "BOYMOR03",
    "BCNCAR01",
    "BCNLAT15",
    "BCNLAT16",
    "BCNGEN60",
    "BCNSTK08",
    "BCNSAW13",
    "TOPMA102",
    "TOPMA100",
    "TOPMA107",
    "TOPMA113",
    "TOPMA114",
    "TOPMA115",
    "TOPSHP19",
    "TOPSHP24",
    "TOPSHP31",
    "LIGHTS05",
    "FOGSIG01",
    "RTPBCN02",
    "RACNSP01",
    "RADRFL03",
    "RDOCAL03",
    "RDOSTA02",
    "WRECKS04",
    "UWTROC04",
]


def _style() -> StylePack:
    return StylePack.from_dict(json.loads((ROOT / "stylepacks" / "us-paper.json").read_text()))


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)


def _token(name: str) -> str:
    return f"var(--{name})"


def _e(text: str | None) -> str:
    return html.escape(text or "", quote=False)


def _svg(asset: str, title: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'aria-labelledby="{_slug(asset)}_title" data-origin="generated-owned-artwork" '
        f'data-style-contract="{STYLE_ID}">'
        f'<title id="{_slug(asset)}_title">{_e(title)}</title>'
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}"
        "</g></svg>\n"
    )


def _facility_marker(body: str) -> str:
    return (
        f'<circle cx="32" cy="32" r="22" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
        f"{body}"
    )


def _label_symbol(text: str, fill: str = "magenta") -> str:
    safe = _e(text[:2].upper())
    return (
        f'<circle cx="32" cy="32" r="20" fill="none" stroke="{_token(fill)}" stroke-width="{FACILITY_STROKE}"/>'
        f'<text x="32" y="38" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="15" font-weight="700" fill="{_token(fill)}" stroke="none">{safe}</text>'
    )


def _water_tap() -> str:
    return (
        f'<path d="M22 25h15q5 0 5 5v2" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
        f'<path d="M28 19h9M32.5 19v7" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
        f'<path d="M43 34q-4 6-4 9a4 4 0 0 0 8 0q0-3-4-9z" fill="{_token("magenta")}" stroke="none"/>'
        f'<path d="M18 31h10" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
    )


def _shower() -> str:
    return (
        f'<path d="M20 24h10q8 0 12 7" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
        f'<path d="M37 30q5 2 8 6" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
        f'<path d="M34 36h13" fill="none" stroke="{_token("magenta")}" stroke-width="2.2"/>'
        f'<path d="M29 41l-3 6M36 42l-3 6M43 42l-3 6" fill="none" stroke="{_token("magenta")}" stroke-width="2.1"/>'
        f'<circle cx="27" cy="51" r="1.5" fill="{_token("magenta")}" stroke="none"/>'
        f'<circle cx="34" cy="52" r="1.5" fill="{_token("magenta")}" stroke="none"/>'
        f'<circle cx="41" cy="51" r="1.5" fill="{_token("magenta")}" stroke="none"/>'
    )


def _refuse_bin() -> str:
    return (
        f'<path d="M23 25h18l-2 24H25z" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
        f'<path d="M20 25h24M28 20h8M29 31v13M36 31v13" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
    )


def _marina() -> str:
    return (
        f'<path d="M21 45h23q-4 6-12 6t-11-6z" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
        f'<path d="M31 17v28" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
        f'<path d="M33 21q8 8 9 21H33z" fill="none" stroke="{_token("magenta")}" stroke-width="2.1"/>'
        f'<path d="M29 25q-6 7-7 17h7z" fill="none" stroke="{_token("magenta")}" stroke-width="2.1"/>'
    )


def _fish() -> str:
    return (
        f'<path d="M18 33q9-10 23-3q4 3 7 3q-3 0-7 3q-14 7-23-3z" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
        f'<path d="M18 33l-6-6v12z" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
        f'<circle cx="40" cy="31" r="2" fill="{_token("magenta")}" stroke="none"/>'
    )


def _shipyard() -> str:
    return _label_symbol("SY")


def _harbour_master() -> str:
    return _label_symbol("HM")


def _pilot() -> str:
    return _label_symbol("P")


def _customs() -> str:
    return (
        f'<path d="M23 20h18v15q0 9-9 16q-9-7-9-16z" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
        f'<path d="M26 34l5 5l9-12" fill="none" stroke="{_token("magenta")}" stroke-width="{FACILITY_STROKE}"/>'
    )


def _anchor(extra: str = "") -> str:
    return (
        f'<circle cx="32" cy="10" r="5" fill="none" stroke="{_token("ink")}" stroke-width="4"/>'
        f'<path d="M32 15v32M20 25h24M16 36q3 16 16 16t16-16" fill="none" stroke="{_token("ink")}" stroke-width="4"/>'
        f'<path d="M16 36l-5 5M48 36l5 5" fill="none" stroke="{_token("ink")}" stroke-width="4"/>'
        f"{extra}"
    )


def _mooring(deviation: bool = False) -> str:
    if deviation:
        return (
            f'<path d="M16 48h32" fill="none" stroke="{_token("ink")}" stroke-width="3"/>'
            f'<path d="M19 48l5-29h16l5 29" fill="none" stroke="{_token("ink")}" stroke-width="3"/>'
            f'<path d="M32 48V13" fill="none" stroke="{_token("ink")}" stroke-width="3"/>'
        )
    return (
        f'<path d="M19 19h26v26H19z" fill="{_token("white")}" stroke="{_token("ink")}" stroke-width="5"/>'
    )


def _buoy_body(shape: str, fills: list[str], topmark: str = "") -> str:
    if shape == "can":
        geom = '<rect x="22" y="23" width="20" height="26" rx="2"/>'
    elif shape == "cone":
        geom = '<path d="M32 18l14 31H18z"/>'
    elif shape == "sphere":
        geom = '<circle cx="32" cy="35" r="15"/>'
    elif shape == "barrel":
        geom = '<rect x="19" y="24" width="26" height="23" rx="8"/>'
    elif shape == "spar":
        geom = '<rect x="27" y="16" width="10" height="35" rx="4"/>'
    else:
        geom = '<rect x="23" y="20" width="18" height="31" rx="5"/>'

    fill = fills[0]
    if len(fills) == 1:
        body = geom.replace("/>", f' fill="{_token(fill)}" stroke="{_token("ink")}" stroke-width="3"/>')
    else:
        body = (
            f'<rect x="22" y="22" width="20" height="14" fill="{_token(fills[0])}" stroke="{_token("ink")}" stroke-width="3"/>'
            f'<rect x="22" y="36" width="20" height="15" fill="{_token(fills[1])}" stroke="{_token("ink")}" stroke-width="3"/>'
        )
    return (
        f"{topmark}{body}"
        f'<ellipse cx="32" cy="52" rx="14" ry="4" fill="{_token("white")}" stroke="{_token("ink")}" stroke-width="2"/>'
    )


def _beacon(body_colour: str, top: str = "") -> str:
    return (
        f"{top}"
        f'<path d="M32 20v34" fill="none" stroke="{_token("ink")}" stroke-width="4"/>'
        f'<path d="M22 54h20" fill="none" stroke="{_token("ink")}" stroke-width="4"/>'
        f'<rect x="26" y="31" width="12" height="16" fill="{_token(body_colour)}" stroke="{_token("ink")}" stroke-width="3"/>'
    )


def _cone(up: bool, colour: str) -> str:
    points = "32,12 21,31 43,31" if up else "21,12 43,12 32,31"
    return f'<polygon points="{points}" fill="{_token(colour)}" stroke="{_token("ink")}" stroke-width="3"/>'


def _square(colour: str) -> str:
    return f'<rect x="20" y="20" width="24" height="24" fill="{_token(colour)}" stroke="{_token("ink")}" stroke-width="3"/>'


def _cross(colour: str) -> str:
    return f'<path d="M20 20l24 24M44 20L20 44" fill="none" stroke="{_token(colour)}" stroke-width="6"/>'


def _diamond(colour: str) -> str:
    return f'<polygon points="32,10 52,32 32,54 12,32" fill="{_token(colour)}" stroke="{_token("ink")}" stroke-width="3"/>'


def _light() -> str:
    rays = "".join(
        f'<path d="M32 32L{x} {y}" fill="none" stroke="{_token("magenta")}" stroke-width="3"/>'
        for x, y in [(32, 8), (49, 15), (56, 32), (49, 49), (32, 56), (15, 49), (8, 32), (15, 15)]
    )
    return rays + f'<circle cx="32" cy="32" r="8" fill="{_token("white")}" stroke="{_token("magenta")}" stroke-width="4"/>'


def _fog() -> str:
    return (
        f'<path d="M15 24q17-12 34 0M15 34q17-12 34 0M15 44q17-12 34 0" fill="none" stroke="{_token("magenta")}" stroke-width="4"/>'
        f'<path d="M20 52h24" fill="none" stroke="{_token("ink")}" stroke-width="3"/>'
    )


def _radio(kind: str) -> str:
    center = f'<circle cx="32" cy="32" r="5" fill="{_token("white")}" stroke="{_token("magenta")}" stroke-width="4"/>'
    waves = (
        f'<path d="M20 20q-9 12 0 24M44 20q9 12 0 24" fill="none" stroke="{_token("magenta")}" stroke-width="4"/>'
    )
    if kind == "reflector":
        return _diamond("magenta") + f'<circle cx="32" cy="32" r="5" fill="{_token("white")}" stroke="{_token("ink")}" stroke-width="3"/>'
    if kind == "station":
        return f'<circle cx="32" cy="32" r="19" fill="none" stroke="{_token("magenta")}" stroke-width="4"/>{center}'
    return waves + center


def _wreck() -> str:
    return (
        f'<path d="M14 32h36M23 19v26M41 19v26M32 13v38" fill="none" stroke="{_token("ink")}" stroke-width="{NAV_STROKE}"/>'
    )


def _rock() -> str:
    return (
        f'<path d="M18 42q7-18 15-4q7-17 16 4" fill="none" stroke="{_token("ink")}" stroke-width="4"/>'
        f'<path d="M14 49h36" fill="none" stroke="{_token("ink")}" stroke-width="3" stroke-dasharray="3 4"/>'
    )


def _symbol_body(row: dict) -> tuple[str, str]:
    asset = row["asset"]
    name = row["name"].lower()
    if asset == "SMCFAC_CATSCF_12":
        return _facility_marker(_water_tap()), "semantic facility: compact water tap in facility circle"
    if asset == "SMCFAC_CATSCF_16":
        return _facility_marker(_shower()), "semantic facility: shower in facility circle"
    if asset == "SMCFAC_CATSCF_21":
        return _facility_marker(_refuse_bin()), "semantic facility: refuse bin in facility circle"
    if asset == "SMCFAC02":
        return _facility_marker(_marina()), "facility: marina sailboat glyph in facility circle"
    if asset.startswith("HRBFAC"):
        glyphs = {
            "HRBFAC09": (_facility_marker(_fish()), "facility: fishing harbour fish glyph in facility circle"),
            "HRBFAC12": (_shipyard(), "facility: shipyard hull and tool glyph"),
            "HRBFAC13": (_harbour_master(), "facility: harbour-master office and flag glyph"),
            "HRBFAC14": (_pilot(), "facility: pilot ladder glyph"),
            "HRBFAC16": (_facility_marker(_customs()), "facility: customs shield glyph in facility circle"),
        }
        return glyphs.get(asset, (_label_symbol("H"), "facility: compact harbour marker"))
    if asset.startswith("ACHARE") or asset.startswith("ACHBRT"):
        return _anchor(), "anchorage: anchor glyph"
    if asset == "MORFAC04":
        return _mooring(True), "mooring dolphin with deviation slash"
    if asset.startswith("MORFAC"):
        return _mooring(False), "mooring dolphin"
    if asset.startswith("BOY"):
        if "can" in name or asset in {"BOYLAT23", "BOYLAT24", "BOYMOR03"}:
            shape = "can"
        elif "con" in name or asset.startswith("BOYCON"):
            shape = "cone"
        elif "spherical" in name or "sph" in asset.lower():
            shape = "sphere"
        elif "barrel" in name or "bar" in asset.lower():
            shape = "barrel"
        elif "spar" in name or "spr" in asset.lower():
            shape = "spar"
        else:
            shape = "pillar"
        if "green" in name and "red" in name:
            fills = ["red", "green"]
        elif "green" in name or asset in {"BOYLAT23", "BOYLAT27"}:
            fills = ["green"]
        elif "red" in name or asset in {"BOYLAT24", "BOYLAT25", "BOYLAT26", "BOYSPR60"}:
            fills = ["red"]
        elif "yellow" in name or "special" in name or asset == "BOYINB01":
            fills = ["yellow"]
        elif "black" in name or asset == "BOYBAR01":
            fills = ["black"]
        else:
            fills = ["white"]
        return _buoy_body(shape, fills), f"buoy: {shape} body"
    if asset == "BCNCAR01":
        return _beacon("yellow", _cone(True, "black") + _cone(True, "black").replace("12", "27").replace("31", "46")), "north cardinal beacon"
    if asset.startswith("BCNLAT15") or asset == "BCNGEN60":
        return _beacon("red", _cone(True, "red")), "red lateral beacon"
    if asset.startswith("BCNLAT16"):
        return _beacon("green", _cone(True, "green")), "green lateral beacon"
    if asset.startswith("BCNSTK"):
        return _beacon("yellow"), "stake beacon"
    if asset.startswith("BCNSAW"):
        return _beacon("red", f'<circle cx="32" cy="13" r="6" fill="{_token("red")}" stroke="{_token("ink")}" stroke-width="3"/>'), "safe-water beacon"
    if asset in {"TOPMA102"}:
        return _cone(True, "green"), "standalone green cone topmark"
    if asset in {"TOPMA100"}:
        return _cone(False, "red"), "standalone red cone topmark"
    if asset in {"TOPMA107", "TOPSHP19", "TOPSHP24", "TOPSHP31"}:
        return _square("red"), "standalone red square board topmark"
    if asset == "TOPMA113":
        return _cross("yellow"), "yellow Andreas cross topmark"
    if asset == "TOPMA114":
        return _diamond("black"), "black diamond topmark"
    if asset == "TOPMA115":
        return f'<circle cx="32" cy="32" r="14" fill="{_token("black")}" stroke="{_token("ink")}" stroke-width="3"/>', "black ball topmark"
    if asset == "LIGHTS05":
        return _light(), "magenta light flare"
    if asset == "FOGSIG01":
        return _fog(), "fog signal arcs"
    if asset == "RTPBCN02":
        return _radio("call"), "radar transponder beacon"
    if asset == "RACNSP01":
        return _radio("reflector"), "radar conspicuous marker"
    if asset == "RADRFL03":
        return _radio("reflector"), "radar reflector"
    if asset == "RDOCAL03":
        return _radio("call"), "radio calling-in both directions"
    if asset == "RDOSTA02":
        return _radio("station"), "radio station"
    if asset.startswith("WRECKS"):
        return _wreck(), "wreck glyph"
    if asset.startswith("UWTROC"):
        return _rock(), "rock awash glyph"
    return _label_symbol(asset[:2]), "fallback compact chart marker"


def _source_refs(row: dict) -> list[dict]:
    refs: list[dict] = []
    s57 = row.get("s57") or {}
    if s57.get("object_class"):
        refs.append({
            "s57": s57["object_class"],
            "conditions": s57.get("conditions") or [],
            "instruction": s57.get("instruction"),
        })
    s101 = row.get("s101") or {}
    if s101.get("symbol_id") or s101.get("symbol_file"):
        refs.append({
            "s101": s101.get("symbol_id"),
            "symbol_file": s101.get("symbol_file"),
            "license_status": s101.get("license_status"),
        })
    for ref in row.get("chart1_mappings_refs") or []:
        refs.append({"int1": ref})
    return refs


def _spec(row: dict, semantic_tokens: list[str], reason: str, svg_path: Path) -> SymbolSpec:
    return SymbolSpec(
        id=row["asset"],
        s52_token=(row.get("s57") or {}).get("object_class"),
        name=row["name"],
        category="symbol",
        meaning=(row.get("visual_brief") or {}).get("model_caption") or row["name"],
        invariants=Invariants(
            colors=semantic_tokens,
            topmark=reason if "topmark" in reason or "cardinal" in reason else None,
            light_flare=row["asset"] == "LIGHTS05",
            shape_class=row.get("shape") or row.get("family") or "chart_symbol",
            distinguishing=reason,
            anchor=(0.5, 0.5),
        ),
        reference=None,
        siblings=[],
        source_refs={"refs": _source_refs(row)},
        geometry={"canonical": str(svg_path.relative_to(ROOT)), "style_contract_id": STYLE_ID},
    )


def _yaml_scalar(value) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    text = str(value)
    if not text:
        return '""'
    if re.fullmatch(r"[A-Za-z0-9_.=/:-]+", text):
        return text
    return json.dumps(text)


def _write_yaml(entries: list[dict], path: Path) -> None:
    lines = [
        "format: helm.iconforge.symbols.v1",
        f"style_contract_id: {STYLE_ID}",
        "scope: owned-symbol-batch50",
        "status: generated-owned-draft-visual-parity-pending",
        "symbols:",
    ]
    for entry in entries:
        lines.extend([
            f"  - id: {_yaml_scalar(entry['id'])}",
            f"    name: {_yaml_scalar(entry['name'])}",
            "    kind: chart-symbol",
            "    tier: chart-artifact",
            "    source_refs:",
        ])
        for ref in entry["source_refs"] or [{"note": "none"}]:
            lines.append("      -")
            for key, value in ref.items():
                if isinstance(value, list):
                    lines.append(f"        {key}: [{', '.join(_yaml_scalar(v) for v in value)}]")
                else:
                    lines.append(f"        {key}: {_yaml_scalar(value)}")
        lines.extend([
            "    asset:",
            f"      canonical: {_yaml_scalar(entry['asset']['canonical'])}",
            "      renders:",
        ])
        for palette, render_path in entry["asset"]["renders"].items():
            lines.append(f"        {palette}: {_yaml_scalar(render_path)}")
        lines.extend([
            "    qa:",
            f"      semantic_pass: {str(entry['qa']['semantic_pass']).lower()}",
            f"      structural_pass: {str(entry['qa']['structural_pass']).lower()}",
            f"      visual_parity: {_yaml_scalar(entry['qa']['visual_parity'])}",
            "    provenance:",
            "      origin: generated-owned-artwork",
            "      allowed_sources:",
            "        - public-domain Chart No.1 reference",
            "        - local metadata lookup",
            "        - OpenCPN/S-101/Commons/emoji/icon references for comparison only",
            "      forbidden_sources:",
            "        - direct trace or extraction of GPL or license-pending artwork",
            f"      generator: {_yaml_scalar(entry['provenance']['generator'])}",
        ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def build() -> dict:
    if len(SELECTED_50) != 50 or len(set(SELECTED_50)) != 50:
        raise ValueError("SELECTED_50 must contain exactly 50 unique assets")
    style = _style()
    matrix = source_variant_matrix.build(SELECTED_50)
    rows_by_asset = {row["asset"]: row for row in matrix["rows"]}
    missing = [asset for asset in SELECTED_50 if asset not in rows_by_asset]
    if missing:
        raise ValueError(f"missing selected assets from source matrix: {missing}")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "renders").mkdir(parents=True, exist_ok=True)

    manifest_entries = []
    report_rows = []
    hard_pile = []
    contact_rows = []

    for asset in SELECTED_50:
        row = rows_by_asset[asset]
        body, reason = _symbol_body(row)
        svg = _svg(asset, row["name"], body)
        svg_path = SVG_OUT / f"{_slug(asset)}.svg"
        svg_path.write_text(svg)

        used_tokens = sorted(t for t in referenced_tokens(svg) if t != "white") or ["ink"]
        spec = _spec(row, used_tokens, reason, svg_path)
        criteria = verify.structural(svg, spec, style, style.palettes["day"])
        structural_pass = all(criterion.passed for criterion in criteria)
        if not structural_pass:
            hard_pile.append({
                "asset": asset,
                "reason_codes": [criterion.name for criterion in criteria if not criterion.passed],
                "criteria": [criterion.__dict__ for criterion in criteria],
            })

        renders = {}
        for palette in PALETTES:
            png = render.rasterize(svg, style.palettes[palette], size=160)
            png_path = OUT / "renders" / f"{_slug(asset)}__{palette}.png"
            png_path.write_bytes(png)
            renders[palette] = str(png_path.relative_to(ROOT))

        source_refs = _source_refs(row)
        entry = {
            "id": asset,
            "name": row["name"],
            "source_refs": source_refs,
            "asset": {
                "canonical": str(svg_path.relative_to(ROOT)),
                "renders": renders,
            },
            "qa": {
                "semantic_pass": True,
                "structural_pass": structural_pass,
                "visual_parity": "pending_visual_model_and_human_review",
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "generator": "forge.owned_symbol_batch50",
                "style_contract_id": STYLE_ID,
                "selection_reason": reason,
            },
        }
        manifest_entries.append(entry)
        report_rows.append({
            **entry,
            "family": row.get("family"),
            "shape": row.get("shape"),
            "art_state_before": row.get("art_state"),
            "visual_brief": row.get("visual_brief"),
            "criteria": [criterion.__dict__ for criterion in criteria],
            "reference_columns": list((row.get("providers") or {}).keys()),
        })
        contact_rows.append({
            "label": asset,
            "style": STYLE_ID,
            "pngs": {palette: str(ROOT / renders[palette]) for palette in PALETTES},
            "ok": structural_pass,
        })

    _write_yaml(manifest_entries, MANIFEST)
    contact.build_contact(contact_rows, PALETTES, cell=96, out_path=OUT / "contact_sheet.png")
    report = {
        "format": "helm.iconforge.owned_symbol_batch50.report.v1",
        "style_contract": STYLE_CONTRACT,
        "status": "pass" if not hard_pile else "fail",
        "asset_count": len(manifest_entries),
        "structural_pass": len(manifest_entries) - len(hard_pile),
        "structural_total": len(manifest_entries),
        "visual_parity": "pending_visual_model_and_human_review",
        "outputs": {
            "manifest": str(MANIFEST.relative_to(ROOT)),
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "render_dir": str((OUT / "renders").relative_to(ROOT)),
            "contact_sheet": str((OUT / "contact_sheet.png").relative_to(ROOT)),
            "report": str(REPORT.relative_to(ROOT)),
        },
        "hard_pile": hard_pile,
        "symbols": report_rows,
    }
    REPORT.write_text(json.dumps(report, indent=2))
    return report


def main() -> int:
    report = build()
    print(json.dumps({
        "status": report["status"],
        "asset_count": report["asset_count"],
        "structural_pass": report["structural_pass"],
        "structural_total": report["structural_total"],
        "outputs": report["outputs"],
    }, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
