"""Build one-symbol-at-a-time LLM judge packets for Icon Forge repairs.

This is the strict QA lane after source-priority repair batches. Each packet
contains exactly one candidate symbol, the official S-57/S-52/S-101 context,
all mapped visual references, and a repair-agent handoff template. The LLM
judge decides pass/fail; a separate renderer agent acts only on failed packets.

Run:
  python -m forge.source_priority_llm_judge_loop --asset WRECKS01
  python -m forge.source_priority_llm_judge_loop --limit 25 --render
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from . import source_priority_repair_queue


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
OUT = ROOT / "out" / "source_priority_llm_judge_loop"
PACKETS_JSON = OUT / "judge_packets.json"
NEXT_PACKET_JSON = OUT / "next_symbol_packet.json"
README = OUT / "README.md"

SOURCE_PACK = CATALOG / "source_priority_icon_pack.json"
MASTER = CATALOG / "master_symbol_list.json"
CROSSWALK = CATALOG / "s52_s57_s101_crosswalk.json"


JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "asset": {"type": "string"},
        "source_refs_sufficient": {"type": "boolean"},
        "candidate_matches_references": {"type": "boolean"},
        "overall_pass": {"type": "boolean"},
        "recognized_as": {"type": "string"},
        "expected_symbol": {"type": "string"},
        "observed_problem": {"type": "string"},
        "required_change": {"type": "string"},
        "judge_comments": {"type": "array", "items": {"type": "string"}},
        "safety_reason_codes": {"type": "array", "items": {"type": "string"}},
        "reference_used": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
    },
    "required": [
        "asset",
        "source_refs_sufficient",
        "candidate_matches_references",
        "overall_pass",
        "recognized_as",
        "expected_symbol",
        "observed_problem",
        "required_change",
        "judge_comments",
        "safety_reason_codes",
        "reference_used",
        "confidence",
    ],
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _symbol_rows_by_asset() -> dict[str, dict]:
    pack = _read_json(SOURCE_PACK)
    return {row["asset"]: row for row in pack["symbols"]}


def _master_by_asset() -> dict[str, dict]:
    if not MASTER.exists():
        return {}
    return {row["asset"]: row for row in _read_json(MASTER)["rows"]}


def _crosswalk_by_asset() -> dict[str, dict]:
    if not CROSSWALK.exists():
        return {}
    out = {}
    for row in _read_json(CROSSWALK)["rows"]:
        s52 = row.get("s52") or {}
        asset = s52.get("asset") or row.get("asset")
        if asset:
            out[asset] = row
    return out


def _owned_candidates_by_asset() -> dict[str, dict]:
    candidates: dict[str, dict] = {}
    for path in sorted(CATALOG.glob("owned_repair_batch*.json")):
        data = _read_json(path)
        for row in data.get("symbols", []):
            asset = row.get("asset")
            if asset and row.get("after_svg"):
                candidates[asset] = {
                    "asset": asset,
                    "svg": row["after_svg"],
                    "renders": row.get("after_renders") or {},
                    "source_batch": str(path.relative_to(ROOT)),
                    "queue_action": row.get("queue_action"),
                    "repair_note": row.get("repair_note"),
                    "qa": row.get("qa", {}),
                    "provenance": row.get("provenance", {}),
                }
    return candidates


def _candidate_for(job: dict, owned: dict[str, dict], palette: str) -> dict:
    owned_candidate = owned.get(job["asset"])
    if owned_candidate:
        return {
            "candidate_role": "latest_generated_owned_repair_candidate",
            "svg": owned_candidate["svg"],
            "render": owned_candidate["renders"].get(palette),
            "renders": owned_candidate["renders"],
            "source_batch": owned_candidate["source_batch"],
            "repair_note": owned_candidate.get("repair_note"),
            "qa": owned_candidate.get("qa", {}),
            "provenance": owned_candidate.get("provenance", {}),
        }
    return {
        "candidate_role": "source_priority_staging_candidate",
        "svg": job["candidate"]["svg"],
        "render": job["candidate"].get("render"),
        "renders": {},
        "source_batch": None,
        "repair_note": None,
        "qa": job["candidate"].get("qa", {}),
        "provenance": job["candidate"].get("provenance", {}),
    }


def _official_context(symbol: dict, master: dict | None, crosswalk: dict | None) -> dict:
    s52 = (crosswalk or {}).get("s52") or {}
    s57 = (crosswalk or {}).get("s57") or {}
    s101 = (crosswalk or {}).get("s101") or {}
    commons = (crosswalk or {}).get("commons") or {}
    usage_parts = [
        f"Render asset {symbol['asset']} for {symbol.get('name') or s52.get('description') or 'unknown symbol'}.",
    ]
    object_class = s57.get("object_class") or (master or {}).get("s57_object_class")
    conditions = s57.get("conditions") or (master or {}).get("s57_conditions") or []
    instruction = s52.get("instruction") or (master or {}).get("s52_instruction")
    if object_class:
        usage_parts.append(f"S-57 object class: {object_class}.")
    if conditions:
        usage_parts.append(f"Applies under conditions: {', '.join(conditions)}.")
    if instruction:
        usage_parts.append(f"S-52 presentation instruction: {instruction}.")
    if s101.get("feature_rule"):
        usage_parts.append(f"S-101 feature rule: {s101['feature_rule']}.")
    return {
        "asset": symbol["asset"],
        "name": symbol.get("name"),
        "kind": symbol.get("kind"),
        "family": symbol.get("family"),
        "usage_description": " ".join(usage_parts),
        "s57": {
            "object_class": object_class,
            "conditions": conditions,
            "lookup_id": s57.get("lookup_id") or (master or {}).get("lookup_id"),
            "rcid": s57.get("rcid"),
        },
        "s52": {
            "asset_kind": s52.get("asset_kind") or symbol.get("kind"),
            "description": s52.get("description") or symbol.get("name"),
            "family": s52.get("family") or symbol.get("family"),
            "instruction": instruction,
        },
        "s101": {
            "exact_symbol_match": s101.get("exact_symbol_match"),
            "symbol_id": s101.get("symbol_id") or (master or {}).get("s101_symbol_id"),
            "symbol_file": s101.get("symbol_file") or (master or {}).get("s101_symbol_file"),
            "symbol_description": s101.get("symbol_description"),
            "feature_rule": s101.get("feature_rule"),
            "feature_rule_file": s101.get("feature_rule_file"),
            "license_status": s101.get("license_status"),
        },
        "chart1": {
            "mapping_refs": (master or {}).get("chart1_mappings_refs") or [],
            "chart1_verdict": (master or {}).get("chart1_verdict"),
            "visual_approval": (master or {}).get("visual_approval"),
        },
        "commons": commons,
        "current_art_state": (master or {}).get("art_state"),
        "catalog_next_action": (master or {}).get("next_action"),
    }


def _reference_candidates(job: dict, candidate: dict, palette: str) -> list[dict]:
    references = []
    if candidate.get("render"):
        references.append({
            "source": "helm_current_owned_candidate_render",
            "role": "candidate_under_judgment",
            "status": "generated_owned_pending_visual_judge",
            "path": candidate["render"],
            "priority": -2,
        })
    references.append({
        "source": "helm_current_owned_candidate_svg",
        "role": "candidate_svg_under_judgment",
        "status": "generated_owned_pending_visual_judge",
        "path": candidate["svg"],
        "priority": -1,
    })
    for example in job.get("visual_examples", []):
        if example.get("source") == "helm_generated_draft_svg":
            continue
        normalized = dict(example)
        if not normalized.get("path") and normalized.get("palette_paths"):
            normalized["path"] = normalized["palette_paths"].get(palette)
        if not normalized.get("path") and normalized.get("paths"):
            normalized["path"] = normalized["paths"].get(palette)
        references.append(normalized)
    return sorted(references, key=lambda item: item.get("priority", 999))


def _image_inputs(references: list[dict]) -> list[dict]:
    image_like = []
    for ref in references:
        path = ref.get("path") or ref.get("local_path")
        if not path:
            continue
        if str(path).lower().endswith((".png", ".jpg", ".jpeg", ".svg")):
            image_like.append({
                "source": ref.get("source"),
                "role": ref.get("role"),
                "path": path,
                "priority": ref.get("priority"),
            })
    return image_like


def _judge_prompt(packet: dict) -> str:
    refs = "\n".join(
        f"- [{ref.get('priority')}] {ref.get('source')} / {ref.get('role')} / "
        f"{ref.get('status')}: {ref.get('path') or ref.get('local_path') or ref.get('url') or ref.get('description_url')}"
        for ref in packet["reference_candidates"]
    )
    official = packet["official_context"]
    return (
        "You are the strict visual judge for one nautical chart symbol. Judge exactly one symbol.\n"
        "Use the official S-57/S-52/S-101 metadata to understand what the symbol means and where it is used.\n"
        "Use all reference candidates as visual evidence. The current Helm owned candidate is the image/SVG under judgment.\n"
        "Judge against the references one-to-one: same recognizable marine-chart symbol, same silhouette, orientation, "
        "topmarks, letters, and semantic colors. Do not reward style novelty or decorative reinterpretation.\n"
        "If it fails, write concise judge_comments and a concrete required_change for a separate renderer agent. "
        "Do not output a final SVG.\n"
        "Return only JSON matching the provided schema.\n\n"
        f"Asset: {packet['asset']}\n"
        f"Name: {official.get('name')}\n"
        f"Usage: {official.get('usage_description')}\n"
        f"S-57: {json.dumps(official.get('s57'), sort_keys=True)}\n"
        f"S-52: {json.dumps(official.get('s52'), sort_keys=True)}\n"
        f"S-101: {json.dumps(official.get('s101'), sort_keys=True)}\n"
        f"Candidate SVG: {packet['candidate']['svg']}\n"
        f"Candidate render: {packet['candidate'].get('render')}\n"
        f"References:\n{refs}\n"
        f"Output schema: {json.dumps(JUDGE_SCHEMA, sort_keys=True)}\n"
    )


def _repair_agent_instruction(packet: dict) -> str:
    return (
        f"Repair {packet['asset']} only if the visual judge returns overall_pass=false.\n"
        "Read the judge JSON and use its required_change as the source of truth. "
        "Open every referenced image/SVG path in priority order and match the reference symbol as closely as possible. "
        "Redraw a Helm-owned SVG; "
        "do not copy GPL/OpenCPN pixels or license-pending S-101 source art directly. "
        "Preserve the 64x64 viewBox, CSS color variables, Helm/OpenBridge stroke style, "
        "and the current manifest shape. Render day/dusk/night, then send the repaired "
        "candidate back through this same one-symbol judge before moving on.\n\n"
        f"Candidate SVG to replace or supersede: {packet['candidate']['svg']}\n"
        f"Official usage: {packet['official_context']['usage_description']}\n"
    )


def _repair_queue_item(packet: dict) -> dict:
    return {
        "status": "queued_if_judge_fails",
        "asset": packet["asset"],
        "candidate_svg": packet["candidate"]["svg"],
        "candidate_render": packet["candidate"].get("render"),
        "required_input": "judge JSON with overall_pass=false and required_change",
        "renderer_agent_task": packet["repair_agent_instruction"],
        "return_to_gate": "rerun source_priority_llm_judge_loop for this asset after repair",
    }


def _packet(job: dict, symbol: dict, master: dict | None, crosswalk: dict | None, candidate: dict, index: int) -> dict:
    references = _reference_candidates(job, candidate, job.get("palette") or "day")
    packet = {
        "schema_version": 1,
        "sequence_index": index,
        "status": "ready_for_one_symbol_llm_judge",
        "asset": job["asset"],
        "name": symbol.get("name") or job.get("name"),
        "queue_action": job["queue_action"],
        "risk_bucket": job["risk_bucket"],
        "official_context": _official_context(symbol, master, crosswalk),
        "candidate": candidate,
        "reference_candidates": references,
        "image_inputs": _image_inputs(references),
        "judge_schema": JUDGE_SCHEMA,
        "judge_prompt": "",
        "repair_agent_instruction": "",
        "repair_queue_item": {},
        "decision_policy": {
            "approved_status": "approved_by_llm_visual_judge_pending_human_spot_check",
            "fail_status": "repair_required",
            "move_to_next_symbol_when": "judge JSON has been recorded and either approved or repair task emitted",
            "never_auto_approve": [
                "missing candidate render",
                "invalid or unrelated primary reference",
                "wrong orientation/topmark/color",
                "generic fallback shape",
                "recognized_as differs from expected_symbol",
            ],
        },
    }
    packet["judge_prompt"] = _judge_prompt(packet)
    packet["repair_agent_instruction"] = _repair_agent_instruction(packet)
    packet["repair_queue_item"] = _repair_queue_item(packet)
    return packet


def _ordered_jobs(render_candidate: bool) -> list[dict]:
    queue = source_priority_repair_queue.build(
        limit=None,
        render_candidate=render_candidate,
        include_s101_redraw=True,
    )
    return queue["jobs"]


def build(
    *,
    limit: int | None = 1,
    offset: int = 0,
    asset: str | None = None,
    render_candidate: bool = False,
) -> dict:
    symbol_by_asset = _symbol_rows_by_asset()
    master = _master_by_asset()
    crosswalk = _crosswalk_by_asset()
    owned = _owned_candidates_by_asset()
    jobs = _ordered_jobs(render_candidate=render_candidate)
    if asset:
        jobs = [job for job in jobs if job["asset"] == asset]
    else:
        jobs = jobs[offset:] if limit is None else jobs[offset:offset + limit]

    packets = []
    for index, job in enumerate(jobs, start=offset):
        symbol = symbol_by_asset[job["asset"]]
        candidate = _candidate_for(job, owned, job.get("palette") or "day")
        packets.append(_packet(
            job,
            symbol,
            master.get(job["asset"]),
            crosswalk.get(job["asset"]),
            candidate,
            index,
        ))

    sources = Counter()
    for packet in packets:
        sources.update(ref["source"] for ref in packet["reference_candidates"])

    result = {
        "schema_version": 1,
        "generator": "iconforge-source-priority-llm-judge-loop",
        "status": "ready_for_one_symbol_at_a_time_judging",
        "mode": "sequential_symbol_gate",
        "selection": {
            "asset": asset,
            "limit": limit,
            "offset": offset,
            "selected_packets": len(packets),
            "render_candidate": render_candidate,
            "reference_source_counts": dict(sorted(sources.items())),
        },
        "loop_contract": [
            "Judge one symbol at a time.",
            "Use official metadata plus every mapped reference candidate.",
            "Record judge JSON with comments before moving to the next symbol.",
            "If overall_pass is false, enqueue repair_queue_item and do not count the symbol as complete.",
            "A repaired SVG must come back through the same one-symbol judge packet before approval.",
        ],
        "packets": packets,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    PACKETS_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if packets:
        NEXT_PACKET_JSON.write_text(json.dumps(packets[0], indent=2, sort_keys=True) + "\n")
    _write_readme(result)
    return result


def _write_readme(result: dict) -> None:
    lines = [
        "# Source-Priority LLM Judge Loop",
        "",
        "Strict one-symbol visual judging packet output.",
        "",
        "## Contract",
        "",
    ]
    for line in result["loop_contract"]:
        lines.append(f"- {line}")
    lines.extend([
        "",
        "## Current Selection",
        "",
        f"- Selected packets: {result['selection']['selected_packets']}",
        f"- Asset filter: {result['selection']['asset']}",
        f"- Offset: {result['selection']['offset']}",
        f"- Limit: {result['selection']['limit']}",
        "",
        "## Outputs",
        "",
        f"- Full packet set: `{PACKETS_JSON.relative_to(ROOT)}`",
        f"- Next packet: `{NEXT_PACKET_JSON.relative_to(ROOT)}`",
    ])
    README.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", help="build a packet for one asset id")
    parser.add_argument("--limit", type=int, default=1, help="number of sequential packets; pass 0 for all")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--render", action="store_true", help="include source-priority candidate renders")
    args = parser.parse_args(argv)
    limit = None if args.limit == 0 else args.limit
    result = build(
        limit=limit,
        offset=args.offset,
        asset=args.asset,
        render_candidate=args.render,
    )
    print(f"llm judge loop: {result['status']}")
    print(f"selected packets: {result['selection']['selected_packets']}")
    print(f"reference sources: {result['selection']['reference_source_counts']}")
    print(f"next packet: {NEXT_PACKET_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
