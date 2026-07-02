#!/usr/bin/env python3
"""One-command real-weather bake: generate a pack-factory job for an Open-Meteo
run anchored on a GPS position (or explicit bbox) and publish it (WX-36).

    python3 scripts/wx_bake_openmeteo.py --anchor 177.4,-17.6 --out ~/.helm/wx-packs

Reads HELM_WX_OPENMETEO_KEY (commercial hosts only — there is NO free-host
fallback; a keyless run fails loud before any fetch). Prints the exact API call
count before fetching so a bake is never a surprise on a metered link.

This is reference/cloud-job tooling per docs/RUNTIME-SERVICES.md — not a boat
daemon. The factory (scripts/wx_pack_factory.py) does the fetching, quantizing,
packing, verification, and atomic release publish; this script only writes the
job JSON and invokes it.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTORY = ROOT / "scripts" / "wx_pack_factory.py"
DEFAULT_SOURCE_SPEC = ROOT / "services" / "wx" / "fixtures" / "wx-openmeteo-source.json"
BATCH = 140

PROFILES = {
    # dx/dy + half-spans (lon, lat) around the anchor. route-high ~= a passage
    # window; global-low is the budget-honest overview tier.
    "route-high": {"res": 0.25, "half_lon": 20.0, "half_lat": 15.0, "zoom": [4, 10]},
    "global-low": {"res": 1.0, "half_lon": 180.0, "half_lat": 90.0, "zoom": [0, 4]},
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)


def iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anchor", help="lon,lat GPS anchor (route-high default window around it)")
    ap.add_argument("--bbox", help="explicit w,s,e,n (east may exceed 180 for antimeridian passages)")
    ap.add_argument("--profile", choices=sorted(PROFILES), default="route-high")
    ap.add_argument("--layers", default="wind,rain,waves,swell,current",
                    help="comma-separated layers (default: the core five)")
    ap.add_argument("--frames", type=int, default=4, help="number of valid times (default 4)")
    ap.add_argument("--step-hours", type=int, default=3, help="hours between valid times (default 3)")
    ap.add_argument("--res", type=float, help="override grid resolution in degrees")
    ap.add_argument("--out", required=True, help="release output directory")
    ap.add_argument("--source-spec", default=str(DEFAULT_SOURCE_SPEC))
    ap.add_argument("--dry-run", action="store_true", help="print the job + call estimate, fetch nothing")
    args = ap.parse_args(argv[1:])

    profile = PROFILES[args.profile]
    res = float(args.res or profile["res"])
    if args.bbox:
        west, south, east, north = (float(v) for v in args.bbox.split(","))
    elif args.anchor:
        lon, lat = (float(v) for v in args.anchor.split(","))
        west, east = lon - profile["half_lon"], lon + profile["half_lon"]
        south = max(-85.0, lat - profile["half_lat"])
        north = min(85.0, lat + profile["half_lat"])
    else:
        ap.error("--anchor or --bbox is required")
    if east <= west or north <= south:
        ap.error("bbox must have east > west (use east > 180 for antimeridian passages) and north > south")

    layers = [l.strip() for l in args.layers.split(",") if l.strip()]
    now = utc_now()
    run_time = now - timedelta(hours=now.hour % args.step_hours)
    valid_times = [iso(run_time + timedelta(hours=i * args.step_hours)) for i in range(max(2, args.frames))]

    width = round((east - west) / res) + 1
    height = round((north - south) / res) + 1
    points = width * height
    spec = json.loads(Path(args.source_spec).read_text(encoding="utf-8"))
    hosts_needed = {("marine" if layer in ("waves", "swell", "current", "sst") else "forecast") for layer in layers}
    calls = len(hosts_needed) * math.ceil(points / BATCH)
    print(f"bake plan: {args.profile} {west},{south} -> {east},{north} @ {res} deg "
          f"= {width}x{height} = {points} points; layers {','.join(layers)}; "
          f"{len(valid_times)} frames (frames are free); ~{calls} Open-Meteo calls", file=sys.stderr)

    for layer in layers:
        if layer not in (spec.get("layers") or {}):
            print(f"error: layer {layer} is not in the source spec", file=sys.stderr)
            return 2

    job = {
        "schema": "helm.wx.pack_factory.job.v1",
        "generatedAt": iso(datetime.now(timezone.utc).replace(microsecond=0)),
        "maxSourceAgeHours": 24,
        "modelRun": {
            "provider": "open-meteo",
            "model": "gfs-seamless",
            "runTime": valid_times[0],
            "validTimes": valid_times,
            "timeStepSeconds": args.step_hours * 3600,
        },
        "sources": [{
            "id": "open-meteo-live",
            "type": "open-meteo",
            "path": str(Path(args.source_spec).resolve()),
            "generatedAt": iso(datetime.now(timezone.utc).replace(microsecond=0)),
            "provider": "open-meteo",
            "license": "Open-Meteo commercial subscription",
            "provenance": f"Open-Meteo customer API bake; ~{calls} calls; {points} grid points",
        }],
        "packs": [{
            "profile": args.profile,
            "tier": args.profile,
            "anchor": (args.anchor or f"{west}_{south}").replace(",", "_"),
            "layers": layers,
            "tierSpec": {
                "role": "passage" if args.profile == "route-high" else "overview",
                "crs": "OGC:CRS84",
                "grid": {"dx": res, "dy": res},
                "clientZoomRange": profile["zoom"],
            },
            "coverage": {
                "crs": "OGC:CRS84",
                "global": False,
                "bbox": [west, south, east, north],
                "wrap": "antimeridian",
                "crossesAntimeridian": east > 180.0,
            },
            "chunks": [{"bbox": [west, south, east, north]}],
        }],
    }

    if args.dry_run:
        print(json.dumps(job, indent=2, sort_keys=True))
        return 0

    with tempfile.TemporaryDirectory() as td:
        job_path = Path(td) / "openmeteo-job.json"
        job_path.write_text(json.dumps(job, indent=2, sort_keys=True), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(FACTORY), "publish", str(job_path),
                               "--out", args.out, "--allow-network", "--replace"])
        return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
