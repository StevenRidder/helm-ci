"""Sat-first region bundle profile validation (OFFLINE-L-1).

Validates manifests that conform to docs/proposals/interfaces/region-bundle-sat-first-v1.md.
The builder remains pipeline/region_bundle.py; this module is the read-only gate for
OFFLINE-L-2 bake output and OFFLINE-L-3 download planning.
"""
from __future__ import annotations

from region_bundle import REGION_BUNDLE_SCHEMA

SAT_FIRST_PROFILE = "sat_first"
RASTER_CONTAINERS = {"mbtiles", "pmtiles"}
SATELLITE_RASTER_KINDS = {"satellite", "imagery"}
PRIVATE_PATH_KEYS = {
    "_path",
    "path",
    "file_path",
    "filepath",
    "local_path",
    "private_path",
    "directory",
    "dir",
}


class SatFirstBundleError(ValueError):
    """Raised when a bundle violates the sat-first profile."""


def _basemap_components(components: list[dict]) -> list[dict]:
    return [c for c in components if str(c.get("role") or "").lower() == "basemap"]


def _is_raster_basemap(component: dict) -> bool:
    container = str(component.get("container") or "").lower()
    kind = str(component.get("kind") or "").lower()
    pack_type = str(component.get("type") or "").lower()
    return (
        container in RASTER_CONTAINERS
        and pack_type == "raster"
        and kind in SATELLITE_RASTER_KINDS
    )


def _private_path_locations(value, path: str) -> list[str]:
    """Return nested component keys that expose private filesystem metadata."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            if key_text.lower() in PRIVATE_PATH_KEYS:
                found.append(child_path)
            found.extend(_private_path_locations(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_private_path_locations(child, f"{path}[{index}]"))
    return found


def validate_sat_first_bundle(bundle: dict | None, *, require_profile: bool = False) -> dict:
    """Validate a region bundle against the sat-first profile.

    Returns a summary dict on success. Raises SatFirstBundleError on hard failures.
    """
    if not bundle or not isinstance(bundle, dict):
        raise SatFirstBundleError("bundle manifest required")

    if bundle.get("schema") != REGION_BUNDLE_SCHEMA:
        raise SatFirstBundleError(
            f"expected schema {REGION_BUNDLE_SCHEMA!r}, got {bundle.get('schema')!r}"
        )

    profile = bundle.get("profile")
    if require_profile and profile != SAT_FIRST_PROFILE:
        raise SatFirstBundleError(f"profile must be {SAT_FIRST_PROFILE!r}")
    if profile not in (None, SAT_FIRST_PROFILE):
        raise SatFirstBundleError(f"unsupported profile {profile!r}")

    components = bundle.get("components")
    if not isinstance(components, list) or not all(isinstance(c, dict) for c in components):
        raise SatFirstBundleError("invalid_components: components must be a list of objects")

    basemaps = _basemap_components(components)
    if not basemaps:
        raise SatFirstBundleError("missing_basemap: sat-first bundle requires a basemap component")

    invalid_basemaps = [c.get("id") for c in basemaps if not _is_raster_basemap(c)]
    if invalid_basemaps:
        raise SatFirstBundleError(
            "invalid_basemap: basemap components must be satellite raster pmtiles/mbtiles: "
            + ", ".join(str(x) for x in invalid_basemaps if x)
        )

    primary_charts = [
        c.get("id")
        for c in components
        if str(c.get("role") or "").lower() == "chart" and c.get("primary") is True
    ]
    if primary_charts:
        raise SatFirstBundleError("chart_not_basemap: chart components cannot be primary in sat-first bundles")

    primary_basemaps = [c for c in basemaps if c.get("primary") is True]
    if len(primary_basemaps) > 1:
        raise SatFirstBundleError(
            "multiple_primary_basemaps: sat-first bundles may declare at most one primary basemap"
        )

    summary = bundle.get("summary")
    roles = summary.get("roles") if isinstance(summary, dict) else None
    if not isinstance(roles, dict) or "basemap" not in roles:
        raise SatFirstBundleError("missing_basemap: summary.roles.basemap is required")
    basemap_count = roles["basemap"]
    if isinstance(basemap_count, bool) or not isinstance(basemap_count, int):
        raise SatFirstBundleError("invalid_basemap_count: summary.roles.basemap must be an integer")
    if basemap_count < 1:
        raise SatFirstBundleError("missing_basemap: summary.roles.basemap must be >= 1")
    if basemap_count != len(basemaps):
        raise SatFirstBundleError(
            "basemap_count_mismatch: summary.roles.basemap must match basemap components"
        )

    primary = primary_basemaps[0] if primary_basemaps else min(
        basemaps, key=lambda c: str(c.get("id") or "")
    )
    warnings: list[str] = []
    private_path_leaks: list[str] = []
    for component in components:
        inspection = component.get("inspection") or {}
        if str(component.get("role") or "").lower() == "basemap":
            if inspection.get("semantic_objects") not in (None, "unavailable"):
                warnings.append(f"{component.get('id')}: basemap should not expose semantic_objects")
        private_path_leaks.extend(
            _private_path_locations(component, str(component.get("id") or "component"))
        )

    if private_path_leaks:
        raise SatFirstBundleError(
            "private_path_leak: private filesystem metadata must be stripped: "
            + ", ".join(private_path_leaks)
        )

    return {
        "profile": profile or SAT_FIRST_PROFILE,
        "valid": True,
        "basemap_count": len(basemaps),
        "primary_basemap_id": primary.get("id"),
        "chart_count": sum(1 for c in components if str(c.get("role") or "").lower() == "chart"),
        "depth_count": sum(1 for c in components if str(c.get("role") or "").lower() == "depth"),
        "warnings": warnings,
    }


def annotate_sat_first_bundle(bundle: dict) -> dict:
    """Return a copy of bundle with profile=sat_first set (does not mutate input)."""
    out = dict(bundle)
    out["profile"] = SAT_FIRST_PROFILE
    return out
