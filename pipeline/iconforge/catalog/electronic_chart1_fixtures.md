# Electronic Chart 1 Synthetic Fixtures

FORGE-40 deterministic synthetic fixture set generated from the FORGE-39 DB-backed contract.

- schema: `helm.forge.electronic_chart1_fixtures.v1`
- status: `fixtures_ready`
- source_rows: `3057`
- fixture_rows: `2523`
- hard_pile_rows: `534`
- unaccounted_rows: `0`

## Policy

- Fixtures are generated from backend DB contract rows only.
- Browser/UI consumers may display the generated facts but must not infer missing symbol meaning.
- Static JSON fallbacks are forbidden; missing or under-specified rows stay in the hard pile.
- Synthetic geometries are test inputs only and do not promote any symbol to runtime eligibility.

## Fixture Taxonomy

| Taxonomy | Count |
| --- | ---: |
| `area_fill` | 100 |
| `conditional_rule` | 188 |
| `line_style` | 283 |
| `point_symbol` | 1843 |
| `text_rule` | 109 |

## Hard Pile Taxonomy

| Taxonomy | Count |
| --- | ---: |
| `non_reviewable_construct` | 273 |
| `placeholder_manual` | 238 |
| `point_symbol` | 7 |
| `runtime_overlay` | 16 |

## Top Hard Pile Reasons

| Reason | Count |
| --- | ---: |
| `human_final_approval:pending` | 416 |
| `presentation_library_construct_not_direct_chart1_symbol` | 273 |
| `manual_mapping_required` | 238 |
| `s57_tuple:colour_sequence` | 153 |
| `s57_tuple:topmark_cardinal_direction` | 45 |
| `s101_resolver_row:missing` | 38 |
| `s101_feature_type:missing_or_not_applicable` | 31 |
| `runtime_overlay_profile_required` | 16 |
| `s57_tuple:topmark_daymark_shape` | 8 |
| `s52_instruction_ast:SY:unclosed_nested_paren_depth_1` | 7 |
| `s52_instruction_ast:not_complete` | 7 |
| `s52_instruction_ast:partial` | 7 |
| `s52_instruction_ast:unclosed_paren_depth_1` | 7 |
| `s52_parse_error:SY:unclosed_nested_paren_depth_1` | 7 |
| `s52_parse_error:unclosed_paren_depth_1` | 7 |
