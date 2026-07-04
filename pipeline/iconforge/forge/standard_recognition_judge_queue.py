"""Build visual-model recognition packets for current Helm symbol candidates.

The output is not an approval result. It is the queue a visual judge should use
to compare Helm art against reference witnesses with full semantic metadata.

Run:
  python3 -m forge.standard_recognition_judge_queue
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
STYLE_AUDIT = CATALOG / "standard_style_audit.json"
CRAFT_AUDIT = CATALOG / "standard_craft_audit.json"
REPORT_JSON = CATALOG / "standard_recognition_judge_queue.json"
REPORT_CSV = CATALOG / "standard_recognition_judge_queue.csv"
REPORT_MD = CATALOG / "standard_recognition_judge_queue.md"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _audit_rows(path: Path) -> dict[str, dict]:
    return {row["asset"]: row for row in _load_json(path).get("rows", [])}


def _source_rows() -> list[dict]:
    return _load_json(SOURCE_TABLE).get("rows", [])


def _existing(path: str | None) -> str | None:
    if not path:
        return None
    local = ROOT / path
    return path if local.exists() else None


def _reference_images(row: dict) -> list[dict]:
    refs = row.get("reference_providers") or {}
    images = []
    for item in refs.get("opencpn_render", []):
        paths = item.get("paths") or {}
        for palette in ("day", "dusk", "night"):
            path = _existing(paths.get(palette) or item.get(palette))
            if path:
                images.append({
                    "provider": "opencpn_render",
                    "palette": palette,
                    "path": path,
                    "role": "local visual oracle; reference only",
                })
    for item in refs.get("s101", []):
        path = _existing(item.get("path"))
        if path:
            images.append({
                "provider": "s101",
                "palette": "source",
                "path": path,
                "role": "license-pending reference; do not import as canonical art",
            })
    for item in refs.get("aquamap", []):
        path = _existing(item.get("path"))
        if path:
            images.append({
                "provider": "aquamap",
                "palette": "source",
                "path": path,
                "role": "copyrighted visual reference; redraw only",
            })
    return images


def _helm_images(asset: str, helm: dict) -> list[dict]:
    images = []
    canonical = _existing(helm.get("canonical_svg"))
    if canonical:
        images.append({"kind": "svg", "path": canonical})
    render_path = _existing(f"out/triad_reference_candidate_pack/renders/{asset}__day.png")
    if render_path:
        images.append({"kind": "render_day", "path": render_path})
    return images


def _packet(row: dict, style_by_asset: dict[str, dict], craft_by_asset: dict[str, dict]) -> dict | None:
    helm = row.get("helm_candidate") or {}
    if not helm.get("canonical_svg"):
        return None
    asset = row["asset"]
    references = _reference_images(row)
    helm_images = _helm_images(asset, helm)
    style = style_by_asset.get(asset, {})
    craft = craft_by_asset.get(asset, {})

    blockers = []
    if not references:
        blockers.append("no_reference_images")
    if not helm_images:
        blockers.append("no_helm_candidate_image")
    if style.get("status") == "style_blocked":
        blockers.append("style_blocked")
    if craft.get("status") == "craft_blocked":
        blockers.append("craft_blocked")

    if blockers:
        status = "recognition_blocked"
    elif craft.get("status") == "craft_review" or style.get("status") == "style_review":
        status = "recognition_ready_with_style_notes"
    else:
        status = "recognition_ready"

    return {
        "asset": asset,
        "name": row.get("name"),
        "status": status,
        "blockers": blockers,
        "helm_candidate": {
            "status": helm.get("candidate_status"),
            "source_batch": helm.get("source_batch"),
            "images": helm_images,
        },
        "style_audit": {
            "status": style.get("status"),
            "issues": style.get("issues", []),
        },
        "craft_audit": {
            "status": craft.get("status"),
            "issues": craft.get("issues", []),
            "metrics": craft.get("metrics", {}),
        },
        "semantic_brief": row.get("semantic_brief"),
        "s57_structure": row.get("s57_structure"),
        "opencpn_s52_spine": row.get("opencpn_s52_spine"),
        "reference_images": references,
        "judge_contract": {
            "question": "Does the Helm candidate read as the same chart-symbol family as the references at chart scale?",
            "must_check": [
                "symbol family and required shape",
                "load-bearing colour and colour order",
                "topmark count/orientation when present",
                "legibility at small chart sizes",
                "Helm/OpenBridge-like thin-stroke clean geometric style without cartoon/doodle embellishment",
            ],
            "approval": "Approve only if a navigator would recognize the Helm SVG as the same symbol class as the reference witnesses.",
            "on_fail": "Return concrete renderer instructions: what shape/colour/detail is wrong, which reference to follow first, and whether it is a style/craft issue or a semantic mismatch.",
        },
    }


def build() -> dict:
    style_by_asset = _audit_rows(STYLE_AUDIT)
    craft_by_asset = _audit_rows(CRAFT_AUDIT)
    packets = [
        packet
        for row in _source_rows()
        if (packet := _packet(row, style_by_asset, craft_by_asset))
    ]
    status_counts = Counter(packet["status"] for packet in packets)
    blocker_counts = Counter(blocker for packet in packets for blocker in packet["blockers"])
    provider_counts = Counter(
        image["provider"]
        for packet in packets
        for image in packet["reference_images"]
    )
    result = {
        "schema_version": 1,
        "status": "recognition_judge_queue_built",
        "summary": {
            "packets": len(packets),
            "recognition_ready": status_counts["recognition_ready"],
            "recognition_ready_with_style_notes": status_counts["recognition_ready_with_style_notes"],
            "recognition_blocked": status_counts["recognition_blocked"],
            "blocker_counts": dict(sorted(blocker_counts.items())),
            "provider_image_counts": dict(sorted(provider_counts.items())),
        },
        "packets": sorted(packets, key=lambda item: (item["status"], item["asset"])),
    }
    _write_reports(result)
    return result


def _write_reports(result: dict) -> None:
    REPORT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    with REPORT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["asset", "status", "blockers", "reference_count", "helm_count", "style_status", "craft_status"],
            lineterminator="\n",
        )
        writer.writeheader()
        for packet in result["packets"]:
            writer.writerow({
                "asset": packet["asset"],
                "status": packet["status"],
                "blockers": ";".join(packet["blockers"]),
                "reference_count": len(packet["reference_images"]),
                "helm_count": len(packet["helm_candidate"]["images"]),
                "style_status": packet["style_audit"].get("status"),
                "craft_status": packet["craft_audit"].get("status"),
            })

    lines = [
        "# Standard Recognition Judge Queue",
        "",
        "Visual-model queue for comparing Helm candidates against reference witnesses with full semantic metadata.",
        "",
        f"- packets: `{result['summary']['packets']}`",
        f"- recognition_ready: `{result['summary']['recognition_ready']}`",
        f"- recognition_ready_with_style_notes: `{result['summary']['recognition_ready_with_style_notes']}`",
        f"- recognition_blocked: `{result['summary']['recognition_blocked']}`",
        "",
        "## Blocker Counts",
        "",
        "| Blocker | Count |",
        "| --- | ---: |",
    ]
    for blocker, count in result["summary"]["blocker_counts"].items():
        lines.append(f"| `{blocker}` | {count} |")
    lines.extend([
        "",
        "## Provider Image Counts",
        "",
        "| Provider | Images |",
        "| --- | ---: |",
    ])
    for provider, count in result["summary"]["provider_image_counts"].items():
        lines.append(f"| `{provider}` | {count} |")
    lines.extend([
        "",
        "## Blocked / Style-Note Packets",
        "",
        "| Asset | Status | Blockers | Refs | Style | Craft |",
        "| --- | --- | --- | ---: | --- | --- |",
    ])
    for packet in result["packets"]:
        if packet["status"] == "recognition_ready":
            continue
        lines.append(
            f"| `{packet['asset']}` | `{packet['status']}` | `{', '.join(packet['blockers'])}` | "
            f"{len(packet['reference_images'])} | `{packet['style_audit'].get('status')}` | "
            f"`{packet['craft_audit'].get('status')}` |"
        )
    lines.append("")
    REPORT_MD.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    result = build()
    print(json.dumps({"status": result["status"], "summary": result["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
