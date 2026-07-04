# Electronic Chart 1 OpenCPN/S-52 Reference Harness

FORGE-41 fixture-oriented reference renders from local OpenCPN/S-52 presentation resources.

- schema: `helm.forge.electronic_chart1_opencpn_reference.v1`
- status: `reference_ready`
- fixture_rows: `2523`
- rendered_rows: `2460`
- render_hard_pile_rows: `63`
- source_hard_pile_rows: `534`
- produced_reference_pngs: `7380`

## Policy

- OpenCPN/S-52 output is comparison evidence only.
- These PNGs are not Helm canonical artwork and must not be packaged as owned SVG source.
- Browser/UI consumers may display this backend-generated report but must not infer missing renders.
- Unrenderable fixture rows remain explicit hard-pile entries with reason codes.

## Rendered Status Counts

| Status | Count |
| --- | ---: |
| `rendered` | 2378 |
| `rendered_with_warnings` | 82 |

## Row Taxonomy Counts

| Taxonomy | Count |
| --- | ---: |
| `area_fill` | 100 |
| `conditional_rule` | 141 |
| `line_style` | 282 |
| `point_symbol` | 1828 |
| `text_rule` | 109 |

## Top Hard Pile Reasons

| Reason | Count |
| --- | ---: |
| `opencpn_reference_render:missing_palette_output` | 63 |
| `symbol_ref:FLTHAZ02:missing_opencpn_asset_definition` | 10 |
| `conditional_ref:OBSTRN04:no_direct_asset` | 9 |
| `conditional_ref:SLCONS03:no_direct_asset` | 6 |
| `conditional_ref:LIGHTS05:no_direct_asset` | 6 |
| `conditional_ref:SYMINS01:no_direct_asset` | 5 |
| `conditional_ref:DEPARE01:no_direct_asset` | 4 |
| `conditional_ref:DATCVR01:no_direct_asset` | 4 |
| `conditional_ref:RESARE02:no_direct_asset` | 4 |
| `conditional_ref:WRECKS02:no_direct_asset` | 4 |
| `conditional_ref:DEPARE02:no_direct_asset` | 2 |
| `conditional_ref:DEPCNT02:no_direct_asset` | 2 |
| `symbol_ref:VEHTRF01:missing_opencpn_asset_definition` | 2 |
| `opencpn_reference_render:blank_or_no_renderable_instruction` | 1 |
| `conditional_ref:LEGLIN02:no_direct_asset` | 1 |
| `symbol_ref:NEWOBJ 01:missing_opencpn_asset_definition` | 1 |
| `symbol_ref:DGPS01DRFSTA01:missing_opencpn_asset_definition` | 1 |
| `symbol_ref:NEWOBJ01:missing_opencpn_asset_definition` | 1 |
