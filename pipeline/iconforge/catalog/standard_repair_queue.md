# Standard Repair Queue

Row-scoped renderer repair queue generated from the normalized source table.

- repair_queue_rows: `0`
- normal_icon_art_repair_queue_rows: `0`
- routed_queue_rows: `26`
- witness_needed_queue_rows: `5`
- manual_exception_queue_rows: `2`
- style_primitive_registry_rows: `4`
- portrayal_rule_registry_rows: `15`
- routing_bucket_counts: `{'chart1_parity_witness_needed': 2, 'manual_policy_exception': 2, 'portrayal_rule_registry': 15, 'style_primitive_registry': 4, 'witness_needed_official_symbol': 3}`
- safety_blocked_rows: `0`

## Items


## Routed Items

### `chart1_parity_witness_needed`
- `BCNCON81`: attach_exact_chart1_or_equivalent_witness_then_rerun_parity_gate
- `boyspp50`: attach_exact_chart1_or_equivalent_witness_then_rerun_parity_gate

### `manual_policy_exception`
- `NEWOBJ 01`: decide_runtime_placeholder_policy_or_explicit_manual_exception
- `NEWOBJ01`: decide_runtime_placeholder_policy_or_explicit_manual_exception

### `portrayal_rule_registry`
- `DATCVR01`: cover_by_portrayal_rule_or_runtime_renderer_test
- `DEPARE01`: cover_by_portrayal_rule_or_runtime_renderer_test
- `DEPARE02`: cover_by_portrayal_rule_or_runtime_renderer_test
- `DEPCNT02`: cover_by_portrayal_rule_or_runtime_renderer_test
- `LEGLIN02`: cover_by_portrayal_rule_or_runtime_renderer_test
- `OWNSHP02`: cover_by_portrayal_rule_or_runtime_renderer_test
- `QUAPOS01;TX(OBJNAM`: cover_by_portrayal_rule_or_runtime_renderer_test
- `RESARE01`: cover_by_portrayal_rule_or_runtime_renderer_test
- `RESARE02`: cover_by_portrayal_rule_or_runtime_renderer_test
- `RESTRN01`: cover_by_portrayal_rule_or_runtime_renderer_test
- `SLCONS03`: cover_by_portrayal_rule_or_runtime_renderer_test
- `SYMINS01`: cover_by_portrayal_rule_or_runtime_renderer_test
- `TOPMARI1`: cover_by_portrayal_rule_or_runtime_renderer_test
- `VESSEL01`: cover_by_portrayal_rule_or_runtime_renderer_test
- `VRMEBL01`: cover_by_portrayal_rule_or_runtime_renderer_test

### `style_primitive_registry`
- `ARCSLN01`: cover_by_renderer_style_contract_tests
- `DASH`: cover_by_renderer_style_contract_tests
- `DOTT`: cover_by_renderer_style_contract_tests
- `SOLD`: cover_by_renderer_style_contract_tests

### `witness_needed_official_symbol`
- `DANGER53`: attach_tight_reference_before_render
- `DGPS01DRFSTA01`: attach_tight_reference_before_render
- `VEHTRF01`: attach_tight_reference_before_render
