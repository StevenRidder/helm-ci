#!/usr/bin/env python3
"""Validate Vulkan renderer fixture manifests.

The checker is intentionally dependency-free. It verifies the committed fixture
corpus before a Vulkan backend exists, and it can keep validating command-stream
and golden-image hashes once renderer output is added.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPO_ROOT / "engine" / "test" / "fixtures" / "vulkan-render"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def json_sha256(path: Path) -> str:
    return hashlib.sha256(canonical_json_bytes(load_json(path))).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def flatten_commands(scene: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for group in scene.get("command_groups", []):
        out.extend(group.get("commands", []))
    return out


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def check_fixture(fixture_dir: Path, print_hashes: bool) -> tuple[int, int]:
    errors: list[str] = []
    manifest_path = fixture_dir / "manifest.json"
    if not manifest_path.exists():
        return (0, 0)

    manifest = load_json(manifest_path)
    fixture_id = manifest.get("fixture_id", fixture_dir.name)

    source_path = fixture_dir / manifest.get("source_file", "source.json")
    scene_path = fixture_dir / manifest.get("scene_file", "scene.commands.json")
    provenance_path = fixture_dir / manifest.get("provenance_file", "provenance.json")

    for path in (source_path, scene_path, provenance_path):
        if not path.exists():
            fail(errors, f"{fixture_id}: missing {path.name}")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return (1, 0)

    source = load_json(source_path)
    scene = load_json(scene_path)
    provenance = load_json(provenance_path)

    expected = manifest.get("expected_hashes", {})
    actual_hashes = {
        "source_json_sha256": json_sha256(source_path),
        "scene_commands_json_sha256": json_sha256(scene_path),
        "provenance_json_sha256": json_sha256(provenance_path),
    }

    for key, actual in actual_hashes.items():
        want = expected.get(key)
        if want != actual:
            fail(errors, f"{fixture_id}: {key} mismatch: manifest={want!r} actual={actual}")

    if source.get("fixture_id") != fixture_id:
        fail(errors, f"{fixture_id}: source fixture_id mismatch")
    if scene.get("scene_id") != manifest.get("scene_id"):
        fail(errors, f"{fixture_id}: scene_id mismatch")
    if scene.get("schema_version") != manifest.get("schema_version"):
        fail(errors, f"{fixture_id}: schema_version mismatch")

    commands = flatten_commands(scene)
    command_types = {cmd.get("type") for cmd in commands}
    for required in manifest.get("required_command_types", []):
        if required not in command_types:
            fail(errors, f"{fixture_id}: missing command type {required}")

    provenance_ids = {record.get("provenance_id") for record in provenance.get("provenance_table", [])}
    for cmd in commands:
        if not cmd.get("command_id"):
            fail(errors, f"{fixture_id}: command missing command_id")
        if not cmd.get("type"):
            fail(errors, f"{fixture_id}: command {cmd.get('command_id')} missing type")
        for prov_id in cmd.get("provenance_refs", []):
            if prov_id not in provenance_ids:
                fail(errors, f"{fixture_id}: command {cmd.get('command_id')} references missing provenance {prov_id}")

    for image in manifest.get("expected_images", []):
        image_path = fixture_dir / image["path"]
        if not image_path.exists():
            fail(errors, f"{fixture_id}: missing expected image {image['path']}")
            continue
        actual = file_sha256(image_path)
        if image.get("sha256") != actual:
            fail(errors, f"{fixture_id}: image {image['path']} sha256 mismatch: manifest={image.get('sha256')!r} actual={actual}")

    if print_hashes:
        print(f"{fixture_id}:")
        for key, value in actual_hashes.items():
            print(f"  {key}: {value}")
        for image in manifest.get("expected_images", []):
            image_path = fixture_dir / image["path"]
            if image_path.exists():
                print(f"  {image['path']}: {file_sha256(image_path)}")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return (1, 0)

    print(f"ok {fixture_id}: {len(commands)} commands, {len(provenance_ids)} provenance records")
    return (0, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--print-hashes", action="store_true", help="print canonical hashes for fixture manifests")
    args = parser.parse_args()

    if not args.root.exists():
        print(f"fixture root does not exist: {args.root}", file=sys.stderr)
        return 2

    failures = 0
    checked = 0
    for manifest in sorted(args.root.rglob("manifest.json")):
        failed, count = check_fixture(manifest.parent, args.print_hashes)
        failures += failed
        checked += count

    if checked == 0 and failures == 0:
        print(f"no fixtures found under {args.root}", file=sys.stderr)
        return 2
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
