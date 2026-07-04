# Electronic Chart 1 Contract

FORGE-39 DB-backed source-of-truth contract for electronic Chart 1 proof rows.

- schema: `helm.forge.electronic_chart1_contract.v1`
- status: `contract_ready`
- rows: `3057`
- runtime_symbol_portrayal_rows: `0`
- non_fail_closed_rows: `0`

## Policy

- This is a proof/review contract, not runtime promotion.
- Browser/UI consumers must display backend facts and must not infer symbol meaning.
- OpenCPN/S-52 and S-101 evidence is reference metadata; no external artwork is bundled here.

## Row Taxonomy

| Taxonomy | Count |
| --- | ---: |
| `area_fill` | 100 |
| `conditional_rule` | 188 |
| `line_style` | 283 |
| `non_reviewable_construct` | 273 |
| `placeholder_manual` | 238 |
| `point_symbol` | 1850 |
| `runtime_overlay` | 16 |
| `text_rule` | 109 |

## Evidence Status

| Status | Count |
| --- | ---: |
| `red` | 245 |
| `yellow` | 2812 |

## Top Reason Codes

| Reason | Count |
| --- | ---: |
| `human_final_approval:pending` | 2636 |
| `s101_feature_type:missing_or_not_applicable` | 1934 |
| `presentation_library_construct_not_direct_chart1_symbol` | 273 |
| `s101_resolver_row:missing` | 271 |
| `manual_mapping_required` | 238 |
| `s57_tuple:colour_sequence` | 153 |
| `s57_tuple:topmark_cardinal_direction` | 45 |
| `runtime_overlay_profile_required` | 16 |
| `s57_tuple:topmark_daymark_shape` | 8 |
| `s52_instruction_ast:SY:unclosed_nested_paren_depth_1` | 7 |
| `s52_instruction_ast:partial` | 7 |
| `s52_instruction_ast:unclosed_paren_depth_1` | 7 |
| `helm_canonical_art:missing` | 4 |
