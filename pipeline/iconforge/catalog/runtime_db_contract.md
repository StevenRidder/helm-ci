# Runtime DB Contract

FORGE-50 backend proof for the runtime symbol DB gate contract.

- schema: `helm.iconforge.runtime_db_contract.v1`
- status: `contract_pass`
- db: `artifacts/opencpn_s52_portrayal.sqlite`
- lookup_rows: `3057`
- runtime_symbol_portrayal_rows: `0`
- blocker_rows: `4410`

## View Invariants

### `runtime_symbol_candidate_v1`
- one row per OpenCPN s52_portrayal_lookup row
- broad browse/review surface; not runtime serving approval
- runtime_eligible must agree with candidate_status and blocked/pending gate state

### `runtime_symbol_blocker_v1`
- one row per blocked or pending runtime_symbol_gate
- every ineligible candidate must have at least one blocker row
- gate_name, gate_status, severity, detail, and JSON evidence are mandatory

### `runtime_symbol_portrayal_v1`
- strict runtime serving surface
- requires runtime_eligible=1, candidate_status=runtime_eligible, every named required gate present, zero blocking gates, zero pending gates
- also excludes rows with any blocked or pending runtime_symbol_gate

## Checks

| Check | Status | Detail |
| --- | --- | --- |
| `sqlite_integrity_check` | `pass` | SQLite pages and indexes are valid. |
| `sqlite_foreign_key_check` | `pass` | Foreign-key graph is intact. |
| `runtime_candidate_view_covers_lookup_rows` | `pass` | runtime_symbol_candidate_v1 is the complete review/browse surface. |
| `runtime_blocker_view_explains_ineligible_rows` | `pass` | runtime_symbol_blocker_v1 exposes queryable blocked/pending reasons. |
| `runtime_portrayal_view_is_strict_gate_clear_surface` | `pass` | runtime_symbol_portrayal_v1 fails closed from complete named gate state, not just one flag. |
| `runtime_required_gates_cover_all_candidates` | `pass` | runtime promotion is structurally blocked unless every named required gate exists for the row. |
| `runtime_eligibility_matches_gate_state` | `pass` | candidate_status/runtime_eligible agree with blocking and pending gates. |
| `blocker_rows_are_queryable` | `pass` | Each blocker row has gate name/status/severity/detail and valid JSON evidence. |
| `zero_runtime_rows_are_deliberate_fail_closed` | `pass` | The empty runtime surface is an approval gate state, not missing DB data. |
| `import_audit_has_no_fail_rows` | `pass` | The checked-in import audit has no hidden failures. |
