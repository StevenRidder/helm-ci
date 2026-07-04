"""Shared S-52 instruction and asset-id normalization helpers."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


CANONICAL_ASSET_ALIASES = {
    "TOPSHP09;TE('%s'": "TOPSHP09",
    "TOPSHP15;TE('%s'": "TOPSHP15",
    "TOPSHP73;TE('%s'": "TOPSHP73",
    "TOPSHP81;TE('%s'": "TOPSHP81",
    "TOPSHP89;TE('%s'": "TOPSHP89",
    "TOPSHPT8;TE('%s'": "TOPSHPT8",
    "TOWERS74|;TX(OBJNAM": "TOWERS74",
    "QUAPOS01;TX(OBJNAM": "QUAPOS01_TX_OBJNAM",
}

ALIASES_BY_CANONICAL: dict[str, list[str]] = defaultdict(list)
for _legacy_asset, _canonical_asset in CANONICAL_ASSET_ALIASES.items():
    ALIASES_BY_CANONICAL[_canonical_asset].append(_legacy_asset)


def canonical_asset(asset: str) -> str:
    return CANONICAL_ASSET_ALIASES.get(asset, asset)


def asset_keys(source_asset: str, canonical_id: str | None = None) -> list[str]:
    canonical = canonical_id or canonical_asset(source_asset)
    keys = [source_asset, canonical]
    keys.extend(ALIASES_BY_CANONICAL.get(canonical, []))
    return list(dict.fromkeys(keys))


def repair_s52_instruction(instruction: str | None) -> str | None:
    if not instruction:
        return instruction
    instruction = re.sub(
        r"SY\((TOPSHP(?:09|15|73|81|89)|TOPSHPT8);TE\(",
        r"SY(\1);TE(",
        instruction,
    )
    instruction = instruction.replace("SY(TOWERS74|;TX(", "SY(TOWERS74);TX(")
    return re.sub(
        r"CS\(QUAPOS01;TX\((.*?)\)\)",
        r"CS(QUAPOS01);TX(\1)",
        instruction,
    )


def canonicalize_legacy_text(text: str) -> str:
    repaired = repair_s52_instruction(text) or text
    for legacy, canonical in CANONICAL_ASSET_ALIASES.items():
        repaired = repaired.replace(legacy, canonical)
    return repaired


def canonicalize_legacy_value(value: Any) -> Any:
    if isinstance(value, str):
        return canonicalize_legacy_text(value)
    if isinstance(value, list):
        return [canonicalize_legacy_value(item) for item in value]
    if isinstance(value, dict):
        return {key: canonicalize_legacy_value(item) for key, item in value.items()}
    return value
