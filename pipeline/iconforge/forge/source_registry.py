"""Build Icon Forge source registries and crosswalks.

This is metadata/provenance work only. It does not vendor external SVG bodies
into Helm. Commons files are admitted as candidates only when per-file metadata
marks them public-domain/CC0; S-101 artwork remains reference-only until an
explicit reusable license or permission is recorded.

Run:  python -m forge.source_registry
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from .s52_normalization import canonical_asset as _canonical_asset
from .s52_normalization import repair_s52_instruction as _repair_s52_instruction


ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = ROOT / "catalog"
FULL_CATALOG = ROOT / "pilots" / "full_catalog.json"
SYMBOLS = ROOT / "symbols.yaml"
CHART1_REPORT = ROOT / "out" / "chart1_parity" / "report.json"
CHART1_Q_MAPPING = CATALOG_DIR / "chart1_mappings_q_table.json"

COMMONS_CATEGORY = "Category:SVG_Nautical_Chart_icons"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_USER_AGENT = "HelmIconForgeAudit/0.1 (https://github.com/StevenRidder/Helm)"

S101_REPO = "https://github.com/iho-ohi/S-101_Portrayal-Catalogue"
S101_DEFAULT_DIR = Path("/tmp/s101-audit")

S101_REGISTRY = CATALOG_DIR / "s101_reference_registry.json"
COMMONS_REGISTRY = CATALOG_DIR / "commons_nautical_chart_icons.json"
CROSSWALK = CATALOG_DIR / "s52_s57_s101_crosswalk.json"
EXHAUSTIVE = CATALOG_DIR / "exhaustive_symbol_inventory.json"

APPROVED_COMMONS_LICENSES = {
    "pd",
    "cc-zero",
    "cc0",
}

S57_TO_S101_FEATURE = {
    "ACHARE": "AnchorageArea",
    "ACHBRT": "AnchorBerth",
    "BCNCAR": "CardinalBeacon",
    "BCNISD": "IsolatedDangerBeacon",
    "BCNLAT": "LateralBeacon",
    "BCNSAW": "SafeWaterBeacon",
    "BCNSPP": "SpecialPurposeGeneralBeacon",
    "BCNGEN": "SpecialPurposeGeneralBeacon",
    "BOYCAR": "CardinalBuoy",
    "BOYISD": "IsolatedDangerBuoy",
    "BOYLAT": "LateralBuoy",
    "BOYMOR": "MooringBuoy",
    "BOYSAW": "SafeWaterBuoy",
    "BOYSPP": "SpecialPurposeGeneralBuoy",
    "BOYGEN": "SpecialPurposeGeneralBuoy",
    "BRIDGE": "Bridge",
    "BUAARE": "BuiltUpArea",
    "BUISGL": "Building",
    "CBLARE": "CableArea",
    "CBLOHD": "CableOverhead",
    "CBLSUB": "CableSubmarine",
    "CHIMNY": "Landmark",
    "CTNARE": "CautionArea",
    "DAYMAR": "Daymark",
    "DEPARE": "DepthArea",
    "DEPCNT": "DepthContour",
    "DMPGRD": "DumpingGround",
    "DOCARE": "DockArea",
    "DRGARE": "DredgedArea",
    "FAIRWY": "Fairway",
    "FERYRT": "FerryRoute",
    "FOGSIG": "FogSignal",
    "FOULGND": "FoulGround",
    "FSHFAC": "FishingFacility",
    "FSHGRD": "FishingGround",
    "HRBFAC": "HarbourFacility",
    "LIGHTS": "LightAllAround",
    "LITFLT": "LightFloat",
    "LITVES": "LightVessel",
    "LNDMRK": "Landmark",
    "MARCUL": "MarineFarmCulture",
    "MORFAC": "MooringArea",
    "OBSTRN": "Obstruction",
    "OFSPLF": "OffshorePlatform",
    "PILPNT": "Pile",
    "PIPARE": "SubmarinePipelineArea",
    "PIPSOL": "PipelineSubmarineOnLand",
    "PONTON": "Pontoon",
    "PRCARE": "PrecautionaryArea",
    "RASCAN": "RadarTransponderBeacon",
    "RCRTCL": "RecommendedRouteCentreline",
    "RECTRC": "RecommendedTrack",
    "RESARE": "RestrictedArea",
    "RTPBCN": "RadarTransponderBeacon",
    "SBDARE": "SeabedArea",
    "SILTNK": "SiloTank",
    "SISTAT": "SignalStationTraffic",
    "SISTAW": "SignalStationWarning",
    "SLCONS": "ShorelineConstruction",
    "SMCFAC": "SmallCraftFacility",
    "SOUNDG": "Sounding",
    "TOPMAR": "TOPMAR02",
    "TOWERS": "Landmark",
    "TSELNE": "TrafficSeparationSchemeBoundary",
    "TSSBND": "TrafficSeparationSchemeBoundary",
    "TSSCRS": "TrafficSeparationSchemeCrossing",
    "TSSLPT": "TrafficSeparationSchemeLanePart",
    "TSSRON": "TrafficSeparationSchemeRoundabout",
    "TSEZNE": "SeparationZoneOrLine",
    "UWTROC": "UnderwaterAwashRock",
    "VEGATN": "Vegetation",
    "WRECKS": "Wreck",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text())


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _prefix(asset: str) -> str:
    match = re.match(r"[A-Z]+", asset)
    return match.group(0) if match else asset


def _commons_get(params: dict) -> dict:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{COMMONS_API}?{query}",
        headers={"User-Agent": COMMONS_USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _commons_category_titles() -> list[str]:
    titles: list[str] = []
    params = {
        "action": "query",
        "format": "json",
        "list": "categorymembers",
        "cmtitle": COMMONS_CATEGORY,
        "cmnamespace": "6",
        "cmlimit": "500",
    }
    while True:
        data = _commons_get(params)
        titles.extend(member["title"] for member in data["query"]["categorymembers"])
        if "continue" not in data:
            break
        params.update(data["continue"])
    return sorted(titles)


def _commons_imageinfo(titles: list[str]) -> list[dict]:
    rows: list[dict] = []
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        data = _commons_get({
            "action": "query",
            "format": "json",
            "prop": "imageinfo",
            "iiprop": "url|mime|size|sha1|extmetadata",
            "titles": "|".join(batch),
        })
        for page in data["query"]["pages"].values():
            info = (page.get("imageinfo") or [{}])[0]
            metadata = {
                key: value.get("value")
                for key, value in (info.get("extmetadata") or {}).items()
            }
            rows.append({
                "title": page["title"],
                "pageid": page.get("pageid"),
                "url": info.get("url"),
                "description_url": info.get("descriptionurl"),
                "mime": info.get("mime"),
                "size": info.get("size"),
                "width": info.get("width"),
                "height": info.get("height"),
                "sha1": info.get("sha1"),
                "license": metadata.get("License"),
                "license_short_name": metadata.get("LicenseShortName"),
                "usage_terms": metadata.get("UsageTerms"),
                "copyrighted": metadata.get("Copyrighted"),
                "artist": metadata.get("Artist"),
                "credit": metadata.get("Credit"),
            })
    return sorted(rows, key=lambda row: row["title"])


def _commons_license_status(row: dict) -> str:
    license_id = (row.get("license") or "").lower()
    short = (row.get("license_short_name") or "").lower()
    terms = (row.get("usage_terms") or "").lower()
    copyrighted = str(row.get("copyrighted") or "").lower()
    if license_id in APPROVED_COMMONS_LICENSES:
        return "public_domain_or_cc0"
    if "public domain" in short or "public domain" in terms:
        return "public_domain_or_cc0"
    if "cc0" in short or "cc0" in terms:
        return "public_domain_or_cc0"
    if copyrighted == "false" and "pd" in license_id:
        return "public_domain_or_cc0"
    if license_id or short:
        return "license_needs_counsel"
    return "license_unknown"


def _commons_candidates(title: str) -> dict:
    name = _slug(title.removeprefix("File:").removesuffix(".svg"))
    s52: list[str] = []
    s57: list[str] = []
    int1: list[str] = []
    confidence = "none"

    def add(asset: str, obj: str, int1_id: str, level: str = "medium") -> None:
        nonlocal confidence
        s52.append(asset)
        s57.append(obj)
        int1.append(int1_id)
        confidence = level if confidence in {"none", "low"} else confidence

    if "canbuoy" in name or "can buoy" in name:
        if "red" in name:
            add("BOYCAN10", "BOYLAT", "Q21", "medium")
        elif "green" in name:
            add("BOYCAN11", "BOYLAT", "Q21", "medium")
        else:
            add("BOYCAN01", "BOYXXX", "Q21", "low")
    if "conicalbuoy" in name or "conical buoy" in name:
        if "red" in name:
            add("BOYCON10", "BOYLAT", "Q20", "medium")
        elif "green" in name:
            add("BOYCON11", "BOYLAT", "Q20", "medium")
        else:
            add("BOYCON01", "BOYXXX", "Q20", "low")
    if "barrelbuoy" in name or "barrel buoy" in name:
        add("BOYBAR01", "BOYXXX", "Q25", "low")
    if "spherical" in name or "sphere" in name:
        add("BOYSPH01", "BOYXXX", "Q22", "low")
    if "pillar" in name:
        add("BOYPIL01", "BOYXXX", "Q23", "low")
    if "spar" in name:
        add("BOYSPR01", "BOYXXX", "Q24", "low")
    if "cardinal simple buoy" in name:
        direction = {" n": "BOYCAR01", " e": "BOYCAR02", " s": "BOYCAR03", " w": "BOYCAR04"}
        for suffix, asset in direction.items():
            if name.endswith(suffix):
                add(asset, "BOYCAR", "Q130", "medium")
    if "cardinal simple beacon" in name:
        direction = {" n": "BCNCAR01", " e": "BCNCAR02", " s": "BCNCAR03", " w": "BCNCAR04"}
        for suffix, asset in direction.items():
            if name.endswith(suffix):
                add(asset, "BCNCAR", "Q130", "medium")
    if "isolateddanger" in name and "buoy" in name:
        add("BOYISD12", "BOYISD", "Q130", "medium")
    if "isolateddanger" in name and "beacon" in name:
        add("BCNISD21", "BCNISD", "Q130", "medium")
    if "safe water" in name or "safewater" in name:
        add("BOYSAW12", "BOYSAW", "Q130", "medium")
    if "anchorage" in name and "area" in name:
        add("ACHARE51", "ACHARE", "N12", "medium")
    elif "anchorage" in name:
        add("ACHARE02", "ACHARE", "N10", "medium")
    if "wreck" in name:
        add("WRECKS05", "WRECKS", "K26", "medium")
    if "rock" in name:
        add("UWTROC04", "UWTROC", "K11", "low")
    if "obstruction" in name:
        add("OBSTRN01", "OBSTRN", "K40", "low")
    if "fishing" in name:
        add("FSHFAC02", "FSHFAC", "K45", "low")
    if "marina" in name:
        add("SMCFAC02", "SMCFAC", "U1", "low")
    if "beacon" in name and not s57:
        add("BCNGEN01", "BCNXXX", "Q80", "low")
    if "lockgate" in name or "lock gate" in name:
        add("SSLOCK01", "LOKBSN", "F41", "low")
    if "custom office" in name:
        add("CUSTOM01", "SMCFAC", "F61", "low")
    if "harbour master" in name:
        add("HRBFAC09", "HRBFAC", "F60", "low")
    elif "harbour" in name and "fishing" not in name:
        add("HRBFAC09", "HRBFAC", "F60", "low")
    if "major light" in name or "minor light" in name or "light chart symbol" in name:
        add("LIGHTS05", "LIGHTS", "P1", "low")
    if "stake" in name:
        add("BCNSTK02", "BCNXXX", "Q90", "low")
    if "perch" in name:
        if "port" in name:
            add("BCNLAT21", "BCNLAT", "Q91", "low")
        elif "starboard" in name:
            add("BCNLAT22", "BCNLAT", "Q91", "low")
        else:
            add("BCNSTK02", "BCNXXX", "Q91", "low")
    if "withy" in name:
        if "port" in name:
            add("BCNLAT15", "BCNLAT", "Q92", "low")
        elif "starboard" in name:
            add("BCNLAT16", "BCNLAT", "Q92", "low")
        else:
            add("BCNSTK03", "BCNXXX", "Q92", "low")
    if "trafficdirection recommended" in name:
        add("DIRBOY01", "M_NSYS", "Q130", "low")
    elif "trafficdirection" in name:
        add("DIRBOYA1", "M_NSYS", "Q130", "low")
        add("DIRBOYB1", "M_NSYS", "Q130", "low")
    if "topmark" in name:
        if "two cone up" in name:
            add("TOPMAR05", "TOPMAR", "Q9", "low")
        elif "two cone down" in name:
            add("TOPMAR06", "TOPMAR", "Q9", "low")
        elif "cone up down" in name:
            add("TOPMAR08", "TOPMAR", "Q9", "low")
        elif "cone down up" in name:
            add("TOPMAR07", "TOPMAR", "Q9", "low")
        elif "cone down" in name:
            add("TOPMAR04", "TOPMAR", "Q9", "low")
        elif "cone" in name:
            add("TOPMAR02", "TOPMAR", "Q9", "low")
        elif "two spheres" in name:
            add("TOPMAR12", "TOPMAR", "Q9", "low")
        elif "sphere" in name:
            add("TOPMAR10", "TOPMAR", "Q9", "low")
        elif "cilinder" in name or "cylinder" in name:
            add("TOPMAR13", "TOPMAR", "Q9", "low")
        elif "saltire" in name:
            add("TOPMAR65", "TOPMAR", "Q9", "low")
        elif "greek cross" in name:
            add("TOPMAR86", "TOPMAR", "Q9", "low")

    return {
        "s52_assets": sorted(set(s52)),
        "s57_objects": sorted(set(s57)),
        "int1": sorted(set(int1)),
        "mapping_confidence": confidence,
    }


def build_commons_registry() -> dict:
    rows = []
    for row in _commons_imageinfo(_commons_category_titles()):
        license_status = _commons_license_status(row)
        candidates = _commons_candidates(row["title"])
        rows.append({
            **row,
            "source": "wikimedia_commons",
            "origin_if_promoted": "public-domain-import",
            "license_status": license_status,
            "canonical_eligible": license_status == "public_domain_or_cc0",
            "allowed_use": [
                "name_mapping",
                "visual_reference",
                "semantic_qa",
                "canonical_asset_candidate" if license_status == "public_domain_or_cc0" else "reference_only",
            ],
            "mapping_status": "auto_candidate" if candidates["s52_assets"] else "manual_mapping_required",
            "mapping_candidates": candidates,
        })
    counts = Counter(row["license_status"] for row in rows)
    mapped = sum(1 for row in rows if row["mapping_candidates"]["s52_assets"])
    return {
        "schema_version": 1,
        "source": {
            "category": COMMONS_CATEGORY,
            "api": COMMONS_API,
            "status": "per_file_license_metadata",
        },
        "counts": {
            "files": len(rows),
            "license_status": dict(counts),
            "mapped_candidate_files": mapped,
            "canonical_eligible_files": sum(1 for row in rows if row["canonical_eligible"]),
        },
        "files": rows,
    }


def _ensure_s101_repo(path: Path) -> Path:
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", S101_REPO, str(path)], check=True)
    return path


def _s101_commit(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def _s101_catalogue(path: Path) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    root = ET.parse(path / "PortrayalCatalog" / "portrayal_catalogue.xml").getroot()

    def text(el: ET.Element, query: str) -> str | None:
        value = el.find(query)
        return value.text.strip() if value is not None and value.text else None

    def rows(tag: str) -> list[dict]:
        found = []
        for el in root.iter(tag):
            found.append({
                "id": el.get("id"),
                "name": text(el, "description/name"),
                "description": text(el, "description/description"),
                "file_name": text(el, "fileName"),
                "file_type": text(el, "fileType"),
                "file_format": text(el, "fileFormat"),
            })
        return sorted(found, key=lambda row: row["id"] or "")

    return rows("symbol"), rows("lineStyle"), rows("areaFill"), rows("ruleFile")


def _svg_metadata(path: Path) -> list[dict]:
    rows = []
    for svg in sorted((path / "PortrayalCatalog" / "Symbols").glob("*.svg")):
        root = ET.fromstring(svg.read_text(errors="ignore"))
        description = {}
        for element in root.iter():
            if element.tag.endswith("Description"):
                description = {key.split("}", 1)[-1]: value for key, value in element.attrib.items()}
                break
        title = root.find("{http://www.w3.org/2000/svg}title")
        desc = root.find("{http://www.w3.org/2000/svg}desc")
        rows.append({
            "id": svg.stem,
            "file": str(svg.relative_to(path)),
            "title": title.text.strip() if title is not None and title.text else svg.stem,
            "description": desc.text.strip() if desc is not None and desc.text else None,
            "width": root.get("width"),
            "height": root.get("height"),
            "viewBox": root.get("viewBox"),
            "metadata": description,
            "license_status": "license_pending_reference",
            "allowed_use": ["name_mapping", "visual_reference", "semantic_qa", "sibling_discovery"],
            "forbidden_use_until_cleared": ["canonical_asset_source", "bulk_vendor_artwork"],
        })
    return rows


def _rule_instruction_refs(path: Path) -> dict[str, list[dict]]:
    refs: dict[str, list[dict]] = defaultdict(list)
    rules_dir = path / "PortrayalCatalog" / "Rules"
    for rule in sorted(rules_dir.glob("*.lua")):
        text = rule.read_text(errors="ignore")
        for kind, symbol in re.findall(r"\b(PointInstruction|LineInstruction|AreaInstruction):([A-Z0-9_]+)", text):
            refs[symbol].append({"rule": rule.stem, "file": str(rule.relative_to(path)), "kind": kind})
    return {key: rows for key, rows in sorted(refs.items())}


def _xml_symbol_refs(path: Path) -> dict[str, list[dict]]:
    refs: dict[str, list[dict]] = defaultdict(list)
    for xml in sorted((path / "PortrayalCatalog" / "LineStyles").glob("*.xml")):
        for symbol in re.findall(r'<symbol\s+reference="([^"]+)"', xml.read_text(errors="ignore")):
            refs[symbol].append({"file": str(xml.relative_to(path)), "kind": "line_style_symbol_ref"})
    for xml in sorted((path / "PortrayalCatalog" / "AreaFills").glob("*.xml")):
        for symbol in re.findall(r'<symbol\s+reference="([^"]+)"', xml.read_text(errors="ignore")):
            refs[symbol].append({"file": str(xml.relative_to(path)), "kind": "area_fill_symbol_ref"})
    return {key: rows for key, rows in sorted(refs.items())}


def build_s101_registry(s101_dir: Path = S101_DEFAULT_DIR) -> dict:
    s101_dir = _ensure_s101_repo(s101_dir)
    symbols, line_styles, area_fills, rules = _s101_catalogue(s101_dir)
    svg = _svg_metadata(s101_dir)
    sources = Counter((row["metadata"].get("source") or "[missing]") for row in svg)
    publishers = Counter((row["metadata"].get("publisher") or "[missing]") for row in svg)
    return {
        "schema_version": 1,
        "source": {
            "repository": S101_REPO,
            "commit": _s101_commit(s101_dir),
            "status": "license_pending_reference",
            "license_status": "no_license_file_detected_in_audit",
        },
        "counts": {
            "svg_symbols": len(svg),
            "catalogue_symbols": len(symbols),
            "line_styles": len(line_styles),
            "area_fills": len(area_fills),
            "rules": len(rules),
            "svg_source_metadata": dict(sources),
            "svg_publisher_metadata": dict(publishers),
        },
        "symbols": symbols,
        "line_styles": line_styles,
        "area_fills": area_fills,
        "rules": rules,
        "svg_symbols": svg,
        "rule_instruction_refs": _rule_instruction_refs(s101_dir),
        "xml_symbol_refs": _xml_symbol_refs(s101_dir),
    }


def _existing_canonical_assets() -> set[str]:
    if not SYMBOLS.exists():
        return set()
    return set(re.findall(r"asset: ([A-Z0-9_]+)", SYMBOLS.read_text()))


def _chart1_status_by_asset() -> dict[str, str]:
    if not CHART1_REPORT.exists():
        return {}
    return {
        row["asset"]: row.get("reference_evidence_status", "unknown")
        for row in _json(CHART1_REPORT).get("rows", [])
    }


def _commons_by_asset(commons: dict) -> dict[str, list[dict]]:
    by_asset: dict[str, list[dict]] = defaultdict(list)
    for row in commons["files"]:
        if row["license_status"] != "public_domain_or_cc0":
            continue
        for asset in row["mapping_candidates"]["s52_assets"]:
            by_asset[asset].append({
                "title": row["title"],
                "url": row["url"],
                "description_url": row["description_url"],
                "license": row["license"],
                "license_short_name": row["license_short_name"],
                "origin_if_promoted": row["origin_if_promoted"],
                "mapping_confidence": row["mapping_candidates"]["mapping_confidence"],
            })
    return dict(sorted(by_asset.items()))


def _catalog_id(entry: dict, asset: str, object_class: str) -> str:
    return "_".join([
        str(object_class or "UNKNOWN"),
        str(asset or "UNKNOWN"),
        str(entry.get("lookup_id") or "UNKNOWN"),
    ])


def build_crosswalk(s101: dict, commons: dict) -> dict:
    full = _json(FULL_CATALOG)["entries"]
    s101_symbols = {row["id"]: row for row in s101["svg_symbols"]}
    s101_rules = {row["id"]: row for row in s101["rules"]}
    rule_refs = s101["rule_instruction_refs"]
    xml_refs = s101["xml_symbol_refs"]
    commons_assets = _commons_by_asset(commons)

    rows = []
    for entry in full:
        source_asset = entry["asset"]
        asset = _canonical_asset(source_asset)
        object_class = entry.get("object_class") or _prefix(asset)
        s101_feature = S57_TO_S101_FEATURE.get(object_class) or S57_TO_S101_FEATURE.get(_prefix(asset))
        s101_symbol = s101_symbols.get(asset)
        instruction = _repair_s52_instruction(entry.get("instruction"))
        rows.append({
            "helm_catalog_id": _catalog_id(entry, asset, object_class),
            "s52": {
                "asset": asset,
                "asset_kind": entry.get("asset_kind"),
                "instruction": instruction,
                "description": entry.get("description"),
                "family": entry.get("family"),
            },
            "s57": {
                "object_class": object_class,
                "lookup_id": entry.get("lookup_id"),
                "rcid": entry.get("rcid"),
                "conditions": entry.get("conditions") or [],
            },
            "s101": {
                "feature_rule": s101_feature,
                "feature_rule_file": f"PortrayalCatalog/Rules/{s101_feature}.lua" if s101_feature in s101_rules else None,
                "exact_symbol_match": bool(s101_symbol),
                "symbol_id": asset if s101_symbol else None,
                "symbol_file": s101_symbol["file"] if s101_symbol else None,
                "symbol_description": s101_symbol["description"] if s101_symbol else None,
                "license_status": "license_pending_reference" if s101_symbol else "not_found_by_exact_asset_id",
                "rule_instruction_refs": rule_refs.get(asset, []),
                "xml_symbol_refs": xml_refs.get(asset, []),
            },
            "commons": {
                "public_domain_candidates": commons_assets.get(asset, []),
            },
        })

    return {
        "schema_version": 1,
        "sources": {
            "helm_full_catalog": str(FULL_CATALOG.relative_to(ROOT)),
            "s101_registry": str(S101_REGISTRY.relative_to(ROOT)),
            "commons_registry": str(COMMONS_REGISTRY.relative_to(ROOT)),
        },
        "counts": {
            "rows": len(rows),
            "s101_exact_symbol_matches": sum(1 for row in rows if row["s101"]["exact_symbol_match"]),
            "commons_public_domain_candidate_rows": sum(1 for row in rows if row["commons"]["public_domain_candidates"]),
            "s101_feature_rule_candidates": sum(1 for row in rows if row["s101"]["feature_rule_file"]),
        },
        "rows": rows,
    }


def build_exhaustive_inventory(crosswalk: dict) -> dict:
    canonical = _existing_canonical_assets()
    chart1 = _chart1_status_by_asset()
    chart1_q = _json(CHART1_Q_MAPPING) if CHART1_Q_MAPPING.exists() else {"rows": []}
    status_counts = Counter()
    rows = []
    for row in crosswalk["rows"]:
        asset = row["s52"]["asset"]
        chart1_status = chart1.get(asset)
        has_commons = bool(row["commons"]["public_domain_candidates"])
        has_s101 = row["s101"]["exact_symbol_match"]

        if asset in canonical:
            status = "ready"
            reason = "canonical SVG already exists in symbols.yaml"
        elif has_commons:
            status = "external_pd_candidate"
            reason = "public-domain/CC0 Commons candidate exists; needs visual and semantic QA before promotion"
        elif chart1_status == "manual_exception":
            status = "manual_exception"
            reason = "Chart No.1 parity gate recorded manual_exception"
        elif has_s101:
            status = "license_blocked"
            reason = "S-101 has a matching SVG, but repository/art license is not cleared for canonical use"
        else:
            status = "generate_owned"
            reason = "no cleared external art candidate; generate owned SVG from approved references and metadata"

        status_counts[status] += 1
        rows.append({
            "asset": asset,
            "helm_catalog_id": row["helm_catalog_id"],
            "status": status,
            "status_reason": reason,
            "s57": row["s57"],
            "s52": row["s52"],
            "chart1_reference_evidence_status": chart1_status,
            "s101": row["s101"],
            "commons": row["commons"],
            "chart1_mappings_q_reference": _chart1_q_refs(asset, chart1_q),
        })

    return {
        "schema_version": 1,
        "status_taxonomy": {
            "ready": "Canonical Helm-owned SVG exists in symbols.yaml.",
            "external_pd_candidate": "External public-domain/CC0 art candidate exists and needs QA before promotion.",
            "generate_owned": "Generate Helm-owned artwork from approved references/metadata.",
            "manual_exception": "Manual sign-off required before asset can be generated or promoted.",
            "license_blocked": "Matching external art exists but license/permission is not cleared for canonical use.",
        },
        "counts": {
            "rows": len(rows),
            "statuses": dict(status_counts),
            "chart1_mappings_q_rows": len(chart1_q.get("rows", [])),
        },
        "rows": rows,
    }


def _chart1_q_refs(asset: str, mapping: dict) -> list[dict]:
    prefix = _prefix(asset)
    source_tokens = [prefix]
    if prefix.startswith("TOP"):
        source_tokens.append("TOPMAR")
    refs = []
    for row in mapping.get("rows", []):
        tokens = " ".join(row.get("s57", []))
        if (
            any(token in tokens for token in source_tokens)
            or (prefix.startswith("BOY") and "BOYXXX" in tokens)
            or (prefix.startswith("BCN") and "BCNXXX" in tokens)
        ):
            refs.append({"int1": row["int1"], "name": row["name"], "s57": row["s57"]})
    return refs[:8]


def build_all() -> dict:
    commons = build_commons_registry()
    s101 = build_s101_registry()
    crosswalk = build_crosswalk(s101, commons)
    exhaustive = build_exhaustive_inventory(crosswalk)
    _write(COMMONS_REGISTRY, commons)
    _write(S101_REGISTRY, s101)
    _write(CROSSWALK, crosswalk)
    _write(EXHAUSTIVE, exhaustive)
    return {
        "commons": commons["counts"],
        "s101": s101["counts"],
        "crosswalk": crosswalk["counts"],
        "exhaustive": exhaustive["counts"],
        "outputs": [
            str(COMMONS_REGISTRY.relative_to(ROOT)),
            str(S101_REGISTRY.relative_to(ROOT)),
            str(CROSSWALK.relative_to(ROOT)),
            str(EXHAUSTIVE.relative_to(ROOT)),
        ],
    }


def main() -> int:
    print(json.dumps(build_all(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
