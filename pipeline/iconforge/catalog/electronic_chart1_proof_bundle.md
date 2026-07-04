# Electronic Chart 1 Proof Bundle

FORGE-46 backend-fed proof UI/public bundle contract.

- schema: `helm.forge.electronic_chart1_proof_bundle.v1`
- status: `proof_bundle_ready`
- authority_rows: `3057`
- proof_rows: `2359`
- hard_pile_rows: `698`
- runtime_eligible_rows: `0`
- image_files_copied: `28308`

## Policy

- Browser business logic is forbidden; the page renders backend payloads.
- Static JSON fallback is forbidden; backend/API failures are visible alerts.
- OpenCPN images are comparison targets only.
- Helm images are generated-owned candidates.
- Runtime promotion remains blocked until FORGE-47.

## Sections

| Section | Count |
| --- | ---: |
| `area_fills` | 100 |
| `conditional_rules` | 188 |
| `line_styles` | 283 |
| `manual_placeholders` | 238 |
| `non_reviewable_construct` | 273 |
| `point_symbols` | 1626 |
| `runtime_overlays` | 16 |
| `text_rules` | 109 |
| `topmarks_daymarks` | 224 |

## Hard Pile Reasons

| Reason | Count |
| --- | ---: |
| `diff:helm_s57_render_missing` | 683 |
| `helm_recipe:missing` | 683 |
| `helm_s57_render:missing` | 683 |
| `diff:opencpn_reference_missing` | 597 |
| `opencpn_reference_render:missing` | 597 |
| `helm_s101_trace:missing` | 534 |
| `s101_forge43_trace:missing` | 534 |
| `s101_feature_type:missing` | 349 |
| `diff:unsupported_taxonomy:non_reviewable_construct` | 273 |
| `diff:unsupported_taxonomy:placeholder_manual` | 238 |
| `helm_shape_family:missing` | 230 |
| `s101_db_backing:missing` | 150 |
| `s52_instruction:missing` | 52 |
| `diff:unsupported_taxonomy:runtime_overlay` | 16 |
| `s52_parse_status:partial` | 7 |
