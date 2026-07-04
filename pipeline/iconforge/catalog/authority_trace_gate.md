# Authority Trace Gate

FORGE-34 backend-owned trace from S-57/S-52 inputs to Helm runtime/package gating.

- schema: `helm.iconforge.authority_trace_gate.v1`
- status: `authority_trace_gate_complete`
- s52_lookup_rows: `3057`
- authority_trace_rows: `3057`
- authority_trace_gap_rows: `18816`
- asset_summary_rows: `824`
- runtime_blocker_rows: `3057`
- runtime_blocker_rows_from_classifier: `3057`

## Policy

- Backend/DB owns the authority chain. Browser pages display it only.
- Runtime export remains fail-closed when any required authority link is missing.
- OpenCPN rendered assets and S-101 SVG witnesses are comparison/evidence inputs, not Helm-owned artwork source.
- S-101 Lua files may be hashed as local audit references but are not vendored into the generated symbol package.

## Status Counts

| Status | Count |
| --- | ---: |
| `blocked` | 3057 |

## Top Gap Reasons

| Reason | Count |
| --- | ---: |
| `authority_trace:runtime_candidate_not_eligible` | 3057 |
| `authority_trace:runtime_gate_visual_approval_pending` | 3057 |
| `authority_trace:s101_feature_catalogue_missing` | 2043 |
| `authority_trace:helm_interpretation_not_ready` | 1710 |
| `authority_trace:s101_rule_file_not_hashed` | 1490 |
| `authority_trace:helm_recipe_not_ready` | 1232 |
| `authority_trace:runtime_gate_s101_crosswalk_evidence_pending` | 942 |
| `authority_trace:s101_resolver_unresolved_reasons_present` | 834 |
| `authority_trace:s57_attribute_predicates_empty` | 698 |
| `authority_trace:s101_rule_file_missing` | 553 |
| `authority_trace:s101_feature_type_missing` | 453 |
| `authority_trace:colour_authority_missing` | 421 |
| `authority_trace:helm_recipe_sidecar_missing` | 421 |
| `authority_trace:s101_resolver_row_missing` | 421 |
| `authority_trace:semantic_sidecar_missing` | 421 |
| `authority_trace:non_s101_or_inland_extension` | 396 |
| `authority_trace:runtime_gate_s57_semantic_tuple_blocked` | 206 |
| `authority_trace:runtime_gate_topmark_daymark_special_cases_blocked` | 127 |
| `authority_trace:non_s101_runtime_construct` | 119 |
| `authority_trace:s101_crosswalk_class_unresolved` | 78 |

## Top Blocker Categories

| Category | Count |
| --- | ---: |
| `runtime_eligibility_blocker` | 3057 |
| `visual_human_approval_blocker` | 3057 |
| `s101_feature_catalogue_source_missing` | 2043 |
| `s101_rule_file_missing` | 2043 |
| `helm_interpretation_missing` | 1710 |
| `helm_recipe_evidence_missing` | 1653 |
| `s101_resolver_evidence_missing` | 1333 |
| `runtime_gate_blocker` | 1155 |
| `s57_semantic_evidence_missing` | 698 |
| `non_s101_scope_boundary` | 515 |
| `s101_feature_catalogue_binding_missing` | 453 |
| `colour_authority_blocker` | 421 |
| `semantic_sidecar_missing` | 421 |
| `visual_special_case_blocker` | 198 |
| `s52_instruction_evidence_missing` | 59 |

## Golden Fixture Coverage

| Symbol | Trace rows | Status counts |
| --- | ---: | --- |
| `BOYLAT13` | 7 | `{'blocked': 7}` |
| `BOYLAT23` | 6 | `{'blocked': 6}` |
| `BOYLAT25` | 2 | `{'blocked': 2}` |
| `BOYLAT52` | 5 | `{'blocked': 5}` |
| `BOYLAT53` | 5 | `{'blocked': 5}` |
| `BOYLAT54` | 4 | `{'blocked': 4}` |
| `BOYLAT55` | 16 | `{'blocked': 16}` |
| `BOYLAT56` | 14 | `{'blocked': 14}` |
| `BOYSPH79` | 1 | `{'blocked': 1}` |
| `TOPSHP28` | 1 | `{'blocked': 1}` |
| `TOPMAR01` | 54 | `{'blocked': 54}` |
| `VRMEBL01` | 2 | `{'blocked': 2}` |
| `CLRLIN01` | 3 | `{'blocked': 3}` |
| `BORDER01` | 2 | `{'blocked': 2}` |
