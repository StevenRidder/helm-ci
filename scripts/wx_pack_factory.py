#!/usr/bin/env python3
"""Publish compact Helm environmental grid packs from an explicit factory job.

WX-34's pack factory is meant for a cloud/VM/R2 worker, not a laptop daemon.
It reads a declared model-run job, materializes compact helm.env.grid.v1 packs
through the WX-32 PMTiles/packd transport, and atomically advances a release
catalog only after every pack verifies.

This first slice is intentionally dependency-free and fixture/local-source
oriented. Provider adapters may be added later, but surprise network fetches are
forbidden unless the caller opts in and the adapter implements them.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import env_grid_pack


JOB_SCHEMA = "helm.wx.pack_factory.job.v1"
RELEASE_SCHEMA = "helm.wx.pack_factory.release.v1"
FAILURE_POLICY = {
    "missingChunk": "fail-loud",
    "staleRun": "show-stale-status",
    "unsupportedCapability": "fail-loud",
    "upstreamFetchDuringGesture": "forbidden",
    "substitution": "forbidden",
}
ADAPTERS = {
    "fixture": {"requiresNetwork": False, "implemented": True},
    "manifest": {"requiresNetwork": False, "implemented": True},
    "open-meteo": {"requiresNetwork": True, "implemented": False},
    "noaa": {"requiresNetwork": True, "implemented": False},
    "predictwind": {"requiresNetwork": True, "implemented": False},
}
ENV_GRID_FAILURE_CODES = {
    "missing_range",
    "checksum_mismatch",
    "bad_chunk_magic",
    "unsupported_chunk_version",
    "truncated_chunk_header",
    "bad_chunk_schema",
    "chunk_key_mismatch",
    "unsupported_band_type",
}


class FactoryError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def fail(code: str, message: str, details: dict[str, Any] | None = None) -> None:
    raise FactoryError(code, message, details)


def stable_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail("missing_source", f"file not found: {path}", {"path": str(path)})
    except json.JSONDecodeError as exc:
        fail("invalid_json", f"invalid JSON in {path}: {exc}", {"path": str(path)})
    if not isinstance(data, dict):
        fail("invalid_json", f"{path} must contain a JSON object", {"path": str(path)})
    return data


def parse_time(raw: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        fail("invalid_time", f"{field} must be ISO-8601 UTC", {"field": field, "value": raw})
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        fail(
            "invalid_time",
            f"{field} must include a UTC offset or Z",
            {"field": field, "value": raw},
        )
    return parsed.astimezone(timezone.utc)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slug(value: str) -> str:
    out = []
    for ch in value.lower():
        out.append(ch if ch.isalnum() else "-")
    compact = "-".join(part for part in "".join(out).split("-") if part)
    return compact or "pack"


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(stable_json(value), encoding="utf-8")
    os.replace(tmp, path)


def validate_job(job: dict[str, Any]) -> None:
    if job.get("schema") != JOB_SCHEMA:
        fail("invalid_job", f"job schema must be {JOB_SCHEMA}", {"schema": job.get("schema")})
    if not isinstance(job.get("sources"), list) or not job["sources"]:
        fail("invalid_job", "job must declare at least one source")
    if not isinstance(job.get("packs"), list) or not job["packs"]:
        fail("invalid_job", "job must declare at least one pack")
    model_run = job.get("modelRun") or {}
    for key in ("provider", "model", "runTime", "validTimes"):
        if key not in model_run:
            fail("invalid_job", f"modelRun.{key} is required")
    if not isinstance(model_run.get("validTimes"), list) or not model_run["validTimes"]:
        fail("invalid_job", "modelRun.validTimes must be a non-empty list")
    parse_time(str(model_run["runTime"]), "modelRun.runTime")
    for idx, valid_time in enumerate(model_run["validTimes"]):
        parse_time(str(valid_time), f"modelRun.validTimes[{idx}]")


def release_id_for(job: dict[str, Any]) -> str:
    return str(job.get("releaseId") or slug(f"{job['modelRun']['provider']}-{job['modelRun']['model']}-{job['modelRun']['runTime']}"))


def source_reference_time(job: dict[str, Any], replay_clock: bool) -> datetime:
    if replay_clock:
        return parse_time(job.get("generatedAt") or now_utc(), "generatedAt")
    return datetime.now(timezone.utc)


def adapter_config(adapter: str, source_id: str, allow_network: bool) -> dict[str, Any]:
    config = ADAPTERS.get(adapter)
    if config is None:
        fail("unsupported_source_adapter", f"unsupported source adapter: {adapter}", {"source": source_id, "adapter": adapter})
    if config.get("requiresNetwork") and not allow_network:
        fail(
            "network_forbidden",
            f"source {source_id} would require network; rerun on the cloud worker with explicit network permission",
            {"source": source_id, "adapter": adapter},
        )
    if not config.get("implemented"):
        fail("unsupported_source_adapter", f"source adapter is not implemented yet: {adapter}", {"source": source_id, "adapter": adapter})
    return config


def load_sources(job: dict[str, Any], base: Path, allow_network: bool, replay_clock: bool) -> dict[str, dict[str, Any]]:
    reference_time = source_reference_time(job, replay_clock)
    loaded: dict[str, dict[str, Any]] = {}
    for source in job.get("sources", []):
        if not isinstance(source, dict):
            fail("invalid_source", "source entries must be objects")
        source_id = str(source.get("id") or "")
        if not source_id:
            fail("invalid_source", "source.id is required")
        adapter = str(source.get("type") or "manifest")
        adapter_config(adapter, source_id, allow_network)
        path_raw = source.get("path")
        if not path_raw:
            fail("invalid_source", f"source {source_id} must declare path")
        path = Path(path_raw)
        if not path.is_absolute():
            path = base / path
        manifest = load_json(path)
        source_generated = str(source.get("generatedAt") or manifest.get("generatedAt") or "")
        if not source_generated:
            fail("missing_source_time", f"source {source_id} must declare generatedAt")
        source_time = parse_time(source_generated, f"sources.{source_id}.generatedAt")
        max_age_hours = float(source.get("maxSourceAgeHours", job.get("maxSourceAgeHours", 24)))
        age_hours = (reference_time - source_time).total_seconds() / 3600.0
        if age_hours > max_age_hours:
            fail(
                "stale_source",
                f"source {source_id} is stale: {age_hours:.1f}h old > {max_age_hours:.1f}h",
                {"source": source_id, "ageHours": round(age_hours, 3), "maxSourceAgeHours": max_age_hours},
            )
        loaded[source_id] = {"decl": source, "manifest": manifest, "path": str(path), "ageHours": round(age_hours, 3)}
    return loaded


def selected_source(job: dict[str, Any], sources: dict[str, dict[str, Any]], pack: dict[str, Any]) -> dict[str, Any]:
    source_id = str(pack.get("source") or job.get("defaultSource") or next(iter(sources)))
    if source_id not in sources:
        fail("missing_source", f"pack references unknown source {source_id}", {"source": source_id})
    return sources[source_id]


def source_layers(source_manifest: dict[str, Any], layer_names: list[str]) -> dict[str, Any]:
    available = source_manifest.get("layers") or {}
    layers: dict[str, Any] = {}
    for layer in layer_names:
        if layer not in available:
            fail("missing_layer", f"source does not contain layer {layer}", {"layer": layer})
        layers[layer] = copy.deepcopy(available[layer])
    return layers


def source_tier(source_manifest: dict[str, Any], tier_id: str, override: dict[str, Any] | None = None) -> dict[str, Any]:
    if override:
        return copy.deepcopy(override)
    tiers = source_manifest.get("tiers") or {}
    if tier_id not in tiers:
        fail("missing_tier", f"source does not contain tier {tier_id}", {"tier": tier_id})
    return copy.deepcopy(tiers[tier_id])


def build_chunks(pack: dict[str, Any], layer_names: list[str], valid_times: list[str], tier_id: str) -> dict[str, Any]:
    chunk_specs = pack.get("chunks")
    if not isinstance(chunk_specs, list) or not chunk_specs:
        fail("invalid_pack", f"pack {pack.get('profile')} must declare chunks")
    chunks: dict[str, Any] = {}
    for spec in chunk_specs:
        if not isinstance(spec, dict):
            fail("invalid_chunk", "chunk specs must be objects")
        layers = spec.get("layers") or spec.get("layer") or layer_names
        if isinstance(layers, str):
            layers = [layers]
        times = spec.get("validTimes") or spec.get("validTime") or valid_times
        if isinstance(times, str):
            times = [times]
        bbox = spec.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            fail("invalid_chunk", "chunk spec bbox must be [west,south,east,north]")
        anchor = str(spec.get("anchor") or f"{bbox[0]}_{bbox[1]}")
        explicit_chunk_key = spec.get("chunkKey")
        if explicit_chunk_key and (len(layers) > 1 or len(times) > 1):
            fail(
                "invalid_chunk",
                "explicit chunkKey can only be used with exactly one layer and one validTime",
                {"chunkKey": explicit_chunk_key},
            )
        for layer in layers:
            if layer not in layer_names:
                fail("invalid_chunk", f"chunk references layer outside pack: {layer}", {"layer": layer})
            for valid_time in times:
                if valid_time not in valid_times:
                    fail("invalid_chunk", f"chunk references validTime outside modelRun: {valid_time}")
                time_id = valid_time.replace("-", "").replace(":", "")
                chunk_key = str(explicit_chunk_key or f"{tier_id}/{layer}/{time_id}/{anchor}")
                if chunk_key in chunks:
                    fail("duplicate_chunk_key", f"duplicate chunk key: {chunk_key}", {"chunkKey": chunk_key})
                chunks[chunk_key] = {
                    "schema": "helm.env.grid.chunk.v1",
                    "layer": layer,
                    "tier": tier_id,
                    "validTime": valid_time,
                    "bbox": bbox,
                }
    return chunks


def translate_env_grid_failure(exc: SystemExit, context: str) -> None:
    raw = str(exc)
    message = raw
    if raw.startswith("env-grid-pack: "):
        message = raw.split("env-grid-pack: ", 1)[1]
    candidate = message.split(":", 1)[0].strip()
    if "float16 fixture packing is not implemented" in message:
        candidate = "unsupported_band_type"
    code = candidate if candidate in ENV_GRID_FAILURE_CODES else "pack_verification_failed"
    fail(code, f"{context}: {message}", {"context": context})


def build_pack_manifest(job: dict[str, Any], pack: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    source_manifest = source["manifest"]
    model_run = job["modelRun"]
    valid_times = list(model_run["validTimes"])
    layer_names = list(pack.get("layers") or source_manifest.get("layers", {}).keys())
    tier_id = str(pack.get("tier") or pack.get("profile") or "global-low")
    profile = str(pack.get("profile") or tier_id)
    anchor = str(pack.get("anchor") or ("global" if profile == "global-low" else "route"))
    pack_id = str(pack.get("packId") or f"{model_run['provider']}/{model_run['model']}/{model_run['runTime']}/{profile}/{anchor}")

    source_decl = source["decl"]
    coverage = copy.deepcopy(pack.get("coverage") or source_manifest.get("coverage") or {})
    if not coverage:
        fail("invalid_pack", f"pack {profile} must declare coverage")
    tier = source_tier(source_manifest, tier_id, pack.get("tierSpec"))
    layers = source_layers(source_manifest, layer_names)
    chunks = build_chunks(pack, layer_names, valid_times, tier_id)
    generated_at = job.get("generatedAt") or now_utc()

    return {
        "schema": "helm.env.grid.pack.v1",
        "encoding": "helm.env.grid.v1",
        "packId": pack_id,
        "productFamily": "met-ocean",
        "generatedAt": generated_at,
        "source": {
            "provider": source_decl.get("provider") or source_manifest.get("source", {}).get("provider") or model_run["provider"],
            "model": model_run["model"],
            "advisoryOnly": bool(source_decl.get("advisoryOnly", True)),
            "notForNavigation": bool(source_decl.get("notForNavigation", True)),
            "license": source_decl.get("license", "source-controlled"),
            "provenance": source_decl.get("provenance", source_manifest.get("source", {}).get("provenance", "pack-factory source")),
        },
        "run": {
            "runTime": model_run["runTime"],
            "validTimes": valid_times,
            "timeStepSeconds": int(model_run.get("timeStepSeconds", 10800)),
        },
        "transport": {
            "container": "pmtiles",
            "payload": "helm.env.grid.chunk.v1",
            "rangeReadable": True,
            "servedBy": "helm-packd",
            "requiredRuntime": "C++",
            "byteRangeSemantics": "offset-length",
            "checksumAlgorithm": "sha256",
        },
        "coverage": coverage,
        "tiers": {tier_id: tier},
        "layers": layers,
        "chunks": chunks,
        "failurePolicy": copy.deepcopy(job.get("failurePolicy") or FAILURE_POLICY),
        "renderContract": copy.deepcopy(source_manifest.get("renderContract") or {}),
        "serviceBoundaries": {
            "packServing": "helm-packd",
            "runtimeEnvService": "helm-envd",
            "cloudPackFactory": "optional-cloud-vm-r2",
            "requiredRuntime": "C++",
            "pythonRole": "cloud-job-reference-tooling-not-boat-daemon",
        },
    }


def pack_manifest(manifest: dict[str, Any], out_pack: Path, out_manifest: Path) -> None:
    chunks_obj = manifest.get("chunks")
    if not isinstance(chunks_obj, dict) or not chunks_obj:
        fail("invalid_pack", "manifest must contain chunks")
    out_pack.parent.mkdir(parents=True, exist_ok=True)
    chunk_items = sorted(chunks_obj.items())
    chunk_bytes = []
    try:
        for chunk_key, chunk in chunk_items:
            chunk_bytes.append(env_grid_pack.make_chunk(manifest, chunk_key, chunk))
        data_offset, _data_length = env_grid_pack.write_pmtiles_shell(out_pack, manifest, chunk_bytes)
    except SystemExit as exc:
        translate_env_grid_failure(exc, f"packing {out_pack.name}")
    packed = copy.deepcopy(manifest)
    offset = data_offset
    for (chunk_key, _chunk), blob in zip(chunk_items, chunk_bytes):
        packed["chunks"][chunk_key]["byteRange"] = [offset, len(blob)]
        packed["chunks"][chunk_key]["checksum"] = "sha256:" + hashlib.sha256(blob).hexdigest()
        offset += len(blob)
    packed["transport"]["packUrl"] = out_pack.name
    packed["transport"]["byteRangeSemantics"] = "offset-length"
    packed["transport"]["checksumAlgorithm"] = "sha256"
    out_manifest.write_text(stable_json(packed), encoding="utf-8")
    sidecar_out = out_pack.with_suffix(".metadata.json")
    sidecar_out.write_text(
        stable_json(env_grid_pack.public_sidecar(packed, out_pack.name, generated_by="scripts/wx_pack_factory.py")),
        encoding="utf-8",
    )
    for chunk_key, chunk in sorted(packed["chunks"].items()):
        try:
            env_grid_pack.verify_chunk(chunk_key, chunk, out_pack)
        except SystemExit as exc:
            translate_env_grid_failure(exc, f"verifying {out_pack.name}")


def relative(path: Path, base: Path) -> str:
    return str(path.relative_to(base)).replace(os.sep, "/")


def build_release(job: dict[str, Any], sources: dict[str, dict[str, Any]], staging: Path, release_id: str) -> dict[str, Any]:
    packs_dir = staging / "packs"
    release_packs: list[dict[str, Any]] = []
    seen_pack_names: set[str] = set()
    for pack in job["packs"]:
        if not isinstance(pack, dict):
            fail("invalid_pack", "pack entries must be objects")
        source = selected_source(job, sources, pack)
        manifest = build_pack_manifest(job, pack, source)
        profile_slug = slug(str(pack.get("profile") or pack.get("tier") or "pack"))
        anchor_slug = slug(str(pack.get("anchor") or manifest["packId"]))
        pack_name = f"{release_id}-{profile_slug}-{anchor_slug}.pmtiles"
        if pack_name in seen_pack_names:
            fail("duplicate_pack_name", f"duplicate pack output name: {pack_name}", {"packName": pack_name})
        seen_pack_names.add(pack_name)
        pack_path = packs_dir / pack_name
        manifest_path = packs_dir / f"{pack_name}.manifest.json"
        pack_manifest(manifest, pack_path, manifest_path)
        packed_manifest = load_json(manifest_path)
        pack_size = pack_path.stat().st_size
        manifest_size = manifest_path.stat().st_size
        sidecar_size = pack_path.with_suffix(".metadata.json").stat().st_size
        release_packs.append({
            "packId": packed_manifest["packId"],
            "profile": pack.get("profile") or pack.get("tier"),
            "tier": next(iter(packed_manifest["tiers"])),
            "packUrl": relative(pack_path, staging),
            "manifestUrl": relative(manifest_path, staging),
            "sidecarUrl": relative(pack_path.with_suffix(".metadata.json"), staging),
            "sizeBytes": pack_size,
            "manifestBytes": manifest_size,
            "sidecarBytes": sidecar_size,
            "totalDownloadBytes": pack_size + manifest_size,
            "chunkCount": len(packed_manifest.get("chunks") or {}),
            "layers": sorted((packed_manifest.get("layers") or {}).keys()),
            "validTimes": packed_manifest.get("run", {}).get("validTimes", []),
            "coverage": packed_manifest.get("coverage", {}),
            "source": packed_manifest.get("source", {}),
            "checksums": {
                "packSha256": hashlib.sha256(pack_path.read_bytes()).hexdigest(),
                "manifestSha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            },
        })
    total_bytes = sum(pack["totalDownloadBytes"] for pack in release_packs)
    return {
        "schema": RELEASE_SCHEMA,
        "releaseId": release_id,
        "generatedAt": job.get("generatedAt") or now_utc(),
        "modelRun": copy.deepcopy(job["modelRun"]),
        "noSurpriseDownloads": True,
        "networkPolicy": "forbidden-unless-explicit-cloud-worker",
        "refresh": {
            "atomic": True,
            "strategy": "write-complete-release-then-atomically-repoint-current",
        },
        "failurePolicy": copy.deepcopy(job.get("failurePolicy") or FAILURE_POLICY),
        "sources": [
            {
                "id": source_id,
                "type": data["decl"].get("type"),
                "provider": data["decl"].get("provider"),
                "generatedAt": data["decl"].get("generatedAt") or data["manifest"].get("generatedAt"),
                "ageHours": data["ageHours"],
                "provenance": data["decl"].get("provenance", data["manifest"].get("source", {}).get("provenance")),
            }
            for source_id, data in sorted(sources.items())
        ],
        "packs": release_packs,
        "totals": {
            "packs": len(release_packs),
            "chunks": sum(pack["chunkCount"] for pack in release_packs),
            "totalDownloadBytes": total_bytes,
        },
    }


def ensure_no_png_payloads(release_dir: Path) -> None:
    pngs = [path for path in release_dir.rglob("*") if path.suffix.lower() == ".png"]
    if pngs:
        fail("png_payload_forbidden", "pack factory emitted PNG payloads", {"paths": [str(p) for p in pngs]})


def publish_command(args: argparse.Namespace) -> int:
    job_path = Path(args.job)
    job = load_json(job_path)
    validate_job(job)
    base = job_path.parent
    out = Path(args.out)
    sources = load_sources(job, base, allow_network=bool(args.allow_network), replay_clock=bool(args.replay_clock))
    release_id = release_id_for(job)
    staging = out / ".staging" / f"{release_id}.{int(time.time() * 1000)}"
    final = out / "releases" / release_id
    if final.exists() and not args.replace:
        fail("release_exists", f"release already exists: {release_id}", {"releaseId": release_id})
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    backup: Path | None = None
    try:
        release = build_release(job, sources, staging, release_id)
        atomic_write_json(staging / "index.json", release)
        ensure_no_png_payloads(staging)
        if final.exists():
            backup = out / "releases" / f".{release_id}.previous.{int(time.time() * 1000)}"
            if backup.exists():
                shutil.rmtree(backup)
            os.replace(final, backup)
        final.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(staging, final)
        except BaseException:
            if backup is not None and backup.exists() and not final.exists():
                os.replace(backup, final)
            raise
        current = {
            "schema": "helm.wx.pack_factory.current.v1",
            "releaseId": release_id,
            "indexUrl": f"releases/{release_id}/index.json",
            "generatedAt": release["generatedAt"],
            "modelRun": release["modelRun"],
            "totals": release["totals"],
        }
        try:
            atomic_write_json(out / "current.json", current)
        except BaseException:
            failed = out / "releases" / f".{release_id}.failed.{int(time.time() * 1000)}"
            if final.exists():
                os.replace(final, failed)
            if backup is not None and backup.exists():
                os.replace(backup, final)
            raise
        if backup is not None and backup.exists():
            shutil.rmtree(backup)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        if backup is not None and backup.exists() and not final.exists():
            os.replace(backup, final)
        raise
    print(stable_json({"releaseId": release_id, "index": str(final / "index.json"), "current": str(out / "current.json")}), end="")
    return 0


def inspect_command(args: argparse.Namespace) -> int:
    index = load_json(Path(args.index))
    if index.get("schema") != RELEASE_SCHEMA:
        fail("invalid_release", f"release schema must be {RELEASE_SCHEMA}", {"schema": index.get("schema")})
    print(stable_json({
        "releaseId": index.get("releaseId"),
        "packs": len(index.get("packs") or []),
        "chunks": index.get("totals", {}).get("chunks"),
        "totalDownloadBytes": index.get("totals", {}).get("totalDownloadBytes"),
        "noSurpriseDownloads": index.get("noSurpriseDownloads"),
    }), end="")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    publish = sub.add_parser("publish", help="materialize and atomically publish a release catalog")
    publish.add_argument("job")
    publish.add_argument("--out", required=True)
    publish.add_argument("--allow-network", action="store_true", help="permit adapters that require network")
    publish.add_argument("--replace", action="store_true", help="replace an existing release id")
    publish.add_argument(
        "--replay-clock",
        action="store_true",
        help="measure source freshness against job.generatedAt for deterministic fixture replay",
    )
    publish.set_defaults(func=publish_command)
    inspect = sub.add_parser("inspect", help="summarize a release index")
    inspect.add_argument("index")
    inspect.set_defaults(func=inspect_command)
    args = parser.parse_args(argv[1:])
    try:
        return int(args.func(args))
    except FactoryError as exc:
        payload = {"error": exc.code, "message": str(exc), "details": exc.details}
        print("wx-pack-factory: " + json.dumps(payload, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
