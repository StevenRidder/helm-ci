# Standard Source Table

Normalized S-52/S-57 source table for Icon Forge. OpenCPN/S-52 metadata is the spine; S-101, Aqua Map, and OpenCPN rendered references are provider witnesses; Helm SVGs and judge state attach to the same row.

## Summary

- rows: `824`
- judge_queue_rows: `798`
- repair_queue_rows: `0`
- routed_queue_rows: `26`
- s101_rows: `244`
- aquamap_rows: `109`
- opencpn_rows: `777`
- opencpn_definitions_total: `863`
- opencpn_lookup_links_total: `3177`
- candidate_status_counts: `{'chart1_parity_witness_needed': 2, 'judge_pass_pending_final_approval': 798, 'manual_policy_exception': 2, 'portrayal_rule_registry': 15, 'style_primitive_registry': 4, 'witness_needed_official_symbol': 3}`
- routing_bucket_counts: `{'chart1_parity_witness_needed': 2, 'manual_policy_exception': 2, 'portrayal_rule_registry': 15, 'style_primitive_registry': 4, 'witness_needed_official_symbol': 3}`
- semantic_shape_judge_queue_rows: `798`

## Outputs

- JSON: `catalog/standard_source_table.json`
- CSV: `catalog/standard_source_table.csv`
- Judge queue: `out/standard_source_table/judge_queue.json`
- Semantic shape judge queue: `catalog/standard_semantic_shape_judge_queue.json`
- Routed queue: `catalog/standard_routed_queue.json`

## Process

1. Normalize OpenCPN/S-52 definitions and lookup rows into `opencpn_s52_spine`.
2. Map S-101, Aqua Map, and OpenCPN rendered references into `reference_providers`.
3. Attach deterministic `semantic_brief` shape/use/colour requirements for judge and renderer.
4. Attach Helm-owned SVG/renders and QA state in `helm_candidate`.
5. Judge consumes the full row packet. Failures produce a row-scoped `repair_queue_item`.
6. Renderer repairs only that row, regenerates the table, then the same judge packet runs again.
7. Batch-98 routed rows are excluded from ordinary icon-art queues and sent to witness/manual/style/rule registries.
