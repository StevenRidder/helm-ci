#!/usr/bin/env python3
"""Validate the minimal helm.env.grid.v1 manifest invariants.

This is intentionally small and dependency-free. It is a contract tripwire for WX-31:
future work should not drift back to PNG/image-pyramid storage or hidden fallback semantics.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_FAILURE_POLICY = {
    "missingChunk": "fail-loud",
    "unsupportedCapability": "fail-loud",
    "upstreamFetchDuringGesture": "forbidden",
    "substitution": "forbidden",
}


def fail(message: str) -> None:
    raise SystemExit(f"check-env-grid-v1: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def validate(path: Path) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))

    require(doc.get("schema") == "helm.env.grid.pack.v1", "schema must be helm.env.grid.pack.v1")
    require(doc.get("encoding") == "helm.env.grid.v1", "encoding must be helm.env.grid.v1")
    require(doc.get("productFamily") == "met-ocean", "productFamily must be met-ocean")

    transport = doc.get("transport") or {}
    require(transport.get("payload") == "helm.env.grid.chunk.v1", "transport payload must be grid chunks")
    require(str(transport.get("container", "")).lower() in {"pmtiles", "directory", "archive"},
            "transport container must be a pack/archive/index, not a PNG pyramid")
    require(transport.get("rangeReadable") is True, "transport must be range-readable")

    failure_policy = doc.get("failurePolicy") or {}
    for key, expected in REQUIRED_FAILURE_POLICY.items():
        require(failure_policy.get(key) == expected, f"failurePolicy.{key} must be {expected}")

    require(doc.get("tiers"), "at least one tier is required")
    require(doc.get("layers"), "at least one layer is required")
    require(doc.get("chunks"), "at least one chunk index entry is required")

    for layer_id, layer in (doc.get("layers") or {}).items():
        require(layer.get("bands"), f"layer {layer_id} must declare bands")
        for band_id, band in (layer.get("bands") or {}).items():
            require(band.get("type") in {"int16", "uint16", "float16", "float32"},
                    f"layer {layer_id} band {band_id} has unsupported type")
            require("nodata" in band, f"layer {layer_id} band {band_id} must declare nodata")
            require("unit" in band, f"layer {layer_id} band {band_id} must declare unit")

    for chunk_key, chunk in (doc.get("chunks") or {}).items():
        require(chunk.get("schema") == "helm.env.grid.chunk.v1",
                f"chunk {chunk_key} must declare helm.env.grid.chunk.v1")
        require("byteRange" in chunk or "path" in chunk,
                f"chunk {chunk_key} must be addressable by byteRange or path")


def main(argv: list[str]) -> int:
    paths = [Path(arg) for arg in argv[1:]]
    if not paths:
        paths = [Path("services/wx/fixtures/helm-env-grid-v1.json")]
    for path in paths:
        validate(path)
    print(f"check-env-grid-v1: ok ({len(paths)} manifest{'s' if len(paths) != 1 else ''})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
