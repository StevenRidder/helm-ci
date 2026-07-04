# Electronic Chart 1 Authority Corpus

FORGE-44 backend-generated authority text for Electronic Chart 1 rows.

- schema: `helm.forge.electronic_chart1_authority_corpus.v1`
- status: `electronic_chart1_authority_corpus_ready`
- authority_rows: `3057`
- fixture_rows: `2523`
- runtime_eligible_rows: `0`

## Policy

- Authority prose is generated from backend/export evidence, not browser code.
- Missing source language is recorded as row-level gaps.
- Global language covers colors, bands/stripes, topmarks, simplified symbols, line styles, area fills, and conditional rules.
- Runtime export remains fail-closed.

## Interpretation Status Counts

| Status | Count |
| --- | ---: |
| `authority_text_manual_required` | 511 |
| `authority_text_pending_source` | 1657 |
| `authority_text_ready` | 889 |

## Validation Counts

| Status | Count |
| --- | ---: |
| `passed` | 3057 |

## Source Language Gaps

| Gap | Count |
| --- | ---: |
| `s101_feature_type:missing` | 1395 |
| `helm_shape_family:missing` | 1165 |
| `s101_db_backing:missing` | 958 |
| `helm_recipe:missing` | 683 |
| `helm_s57_render:missing` | 683 |
| `opencpn_reference_render:missing` | 597 |
| `helm_s101_trace:missing` | 534 |
| `s101_forge43_trace:missing` | 534 |
| `s52_instruction:missing` | 52 |
| `s52_parse_status:partial` | 7 |
| `s101_classification:unresolved` | 6 |
