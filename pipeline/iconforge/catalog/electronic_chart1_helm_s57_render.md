# Electronic Chart 1 Helm S-57 Render Harness

FORGE-42 Helm-owned candidate renders from electronic Chart 1 fixture rows.

- schema: `helm.forge.electronic_chart1_helm_s57_render.v1`
- status: `helm_s57_render_ready`
- fixture_rows: `2523`
- rendered_rows: `2374`
- render_hard_pile_rows: `149`
- source_hard_pile_rows: `534`
- produced_candidate_pngs: `7122`

## Policy

- Candidate renders are generated from backend fixture rows and Helm-owned canonical art/style authority.
- Browser/UI consumers may display this report but must not infer missing render behavior.
- Rows remain fail-closed and are not runtime-promoted by this task.
- Missing art or invalid colour authority remains explicit in hard-pile or warning reason codes.

## Rendered Status Counts

| Status | Count |
| --- | ---: |
| `rendered` | 2356 |
| `rendered_with_warnings` | 18 |

## Row Taxonomy Counts

| Taxonomy | Count |
| --- | ---: |
| `area_fill` | 80 |
| `conditional_rule` | 83 |
| `line_style` | 259 |
| `point_symbol` | 1843 |
| `text_rule` | 109 |

## Recipe Status Counts

| Recipe Status | Count |
| --- | ---: |
| `manual_exception_required` | 472 |
| `missing` | 321 |
| `recipe_missing` | 48 |
| `recipe_ready` | 1533 |

## Top Hard Pile Reasons

| Reason | Count |
| --- | ---: |
| `helm_s57_render:missing_palette_output` | 149 |
| `helm_s57_render:blank_or_no_renderable_instruction` | 106 |
| `helm_line_sample:missing_colour_authority` | 23 |
| `helm_area_sample:missing_colour_or_pattern_authority` | 20 |
