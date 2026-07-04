# Standard Routing Batch 98

- Project: `vulkan`
- Task: `FORGE-15`
- Purpose: route the remaining non-pass rows out of the normal icon-art loop.
- Final approval: none; this is a routing/registry gate only.
- Safety: Chart No.1 parity blocks remain blocking.

## Summary

| Metric | Count |
| --- | ---: |
| `total_routed` | 26 |
| `still_normal_icon_art_queue` | 0 |
| `chart1_parity_witness_needed` | 2 |
| `witness_needed_official_symbol` | 3 |
| `manual_policy_exception` | 2 |
| `style_primitive_registry` | 4 |
| `portrayal_rule_registry` | 15 |

## Routes

| Asset | Input status | Bucket | Next action |
| --- | --- | --- | --- |
| `ARCSLN01` | `pending_judge` | `style_primitive_registry` | `cover_by_renderer_style_contract_tests` |
| `BCNCON81` | `chart1_fail_repair_queue` | `chart1_parity_witness_needed` | `attach_exact_chart1_or_equivalent_witness_then_rerun_parity_gate` |
| `DANGER53` | `judge_fail_repair_queue` | `witness_needed_official_symbol` | `attach_tight_reference_before_render` |
| `DASH` | `pending_judge` | `style_primitive_registry` | `cover_by_renderer_style_contract_tests` |
| `DATCVR01` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `DEPARE01` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `DEPARE02` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `DEPCNT02` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `DGPS01DRFSTA01` | `judge_fail_repair_queue` | `witness_needed_official_symbol` | `attach_tight_reference_before_render` |
| `DOTT` | `pending_judge` | `style_primitive_registry` | `cover_by_renderer_style_contract_tests` |
| `LEGLIN02` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `NEWOBJ 01` | `judge_fail_repair_queue` | `manual_policy_exception` | `decide_runtime_placeholder_policy_or_explicit_manual_exception` |
| `NEWOBJ01` | `judge_fail_repair_queue` | `manual_policy_exception` | `decide_runtime_placeholder_policy_or_explicit_manual_exception` |
| `OWNSHP02` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `QUAPOS01;TX(OBJNAM` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `RESARE01` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `RESARE02` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `RESTRN01` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `SLCONS03` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `SOLD` | `pending_judge` | `style_primitive_registry` | `cover_by_renderer_style_contract_tests` |
| `SYMINS01` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `TOPMARI1` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `VEHTRF01` | `judge_fail_repair_queue` | `witness_needed_official_symbol` | `attach_tight_reference_before_render` |
| `VESSEL01` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `VRMEBL01` | `pending_judge` | `portrayal_rule_registry` | `cover_by_portrayal_rule_or_runtime_renderer_test` |
| `boyspp50` | `chart1_fail_repair_queue` | `chart1_parity_witness_needed` | `attach_exact_chart1_or_equivalent_witness_then_rerun_parity_gate` |
