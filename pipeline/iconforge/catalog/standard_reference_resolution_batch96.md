# Standard Reference Resolution Batch 96

- Project: `vulkan`
- Task: `FORGE-15`
- Purpose: classify the remaining 7 repair blockers plus 19 pending/no-reference rows before any more rendering.
- Final approval: none; this is a routing and SymbolSpec gate only.

## Summary

| Metric | Count |
| --- | ---: |
| `rows_classified` | 26 |
| `symbol_specs` | 7 |
| `renderable_from_s57_symbolspec` | 2 |
| `reference_blocked_official_symbol` | 3 |
| `manual_exception_newobj_placeholder` | 2 |
| `style_primitive_not_standalone_icon` | 4 |
| `portrayal_rule_not_standalone_icon` | 15 |

## Classifications

| Asset | Classification | Next action | Resolution |
| --- | --- | --- | --- |
| `ARCSLN01` | `style_primitive_not_standalone_icon` | `cover_by_renderer_style_contract_and_exclude_from_icon_art_gate` | arc/sector line style primitive; renderer stroke contract, not a standalone icon |
| `BCNCON81` | `renderable_from_s57_symbolspec` | `render_batch_from_symbolspec` | Generate owned beacon/conical special-purpose mark from explicit S-57 conditions; no external art import required. |
| `DANGER53` | `reference_blocked_official_symbol` | `attach_tight_reference_before_render` | Official S-52 danger symbol row exists, but no tight OpenCPN/S-101/AquaMap/Chart-1 one-symbol witness is attached. |
| `DASH` | `style_primitive_not_standalone_icon` | `cover_by_renderer_style_contract_and_exclude_from_icon_art_gate` | generic dashed line primitive used by many lookups; style contract, not a standalone icon |
| `DATCVR01` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | data-coverage conditional procedure |
| `DEPARE01` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | depth-area conditional procedure |
| `DEPARE02` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | depth-area conditional procedure |
| `DEPCNT02` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | depth-contour conditional procedure |
| `DGPS01DRFSTA01` | `reference_blocked_official_symbol` | `split_or_attach_dgps_and_radio_station_reference` | DGPS/radio-station composite row exists, but current merged token lacks a tight symbol witness. |
| `DOTT` | `style_primitive_not_standalone_icon` | `cover_by_renderer_style_contract_and_exclude_from_icon_art_gate` | generic dotted line primitive used by obstruction/foul-area rules; style contract, not a standalone icon |
| `LEGLIN02` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | leg-line conditional procedure |
| `NEWOBJ 01` | `manual_exception_newobj_placeholder` | `manual_exception_or_runtime_placeholder_policy` | NEWOBJ is a placeholder/new-object hook, not a stable nautical symbol to visually promote. |
| `NEWOBJ01` | `manual_exception_newobj_placeholder` | `manual_exception_or_runtime_placeholder_policy` | NEWOBJ area symbol is a placeholder/new-object hook; line style is handled by the renderer, not a canonical pictogram. |
| `OWNSHP02` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | own-ship conditional procedure |
| `QUAPOS01;TX(OBJNAM` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | quality-of-position/text conditional procedure |
| `RESARE01` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | restricted-area conditional procedure |
| `RESARE02` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | restricted-area conditional procedure |
| `RESTRN01` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | restriction conditional procedure |
| `SLCONS03` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | shoreline-construction conditional procedure |
| `SOLD` | `style_primitive_not_standalone_icon` | `cover_by_renderer_style_contract_and_exclude_from_icon_art_gate` | generic solid line primitive used by many area/contour rules; style contract, not a standalone icon |
| `SYMINS01` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | symbol-instruction conditional procedure |
| `TOPMARI1` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | topmark conditional procedure |
| `VEHTRF01` | `reference_blocked_official_symbol` | `attach_tight_reference_before_render` | Vehicle-traffic area row exists, but no tight witness is attached; keep blocked until a symbol crop/render is available. |
| `VESSEL01` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | vessel conditional procedure |
| `VRMEBL01` | `portrayal_rule_not_standalone_icon` | `track_in_rule_registry_not_icon_art_queue` | VRM/EBL conditional procedure |
| `boyspp50` | `renderable_from_s57_symbolspec` | `render_batch_from_symbolspec` | Lowercase legacy special-purpose waterway mark can be generated from S-57 conditions as a yellow special-purpose buoy marker. |
