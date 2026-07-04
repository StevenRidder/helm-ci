# Runtime Evidence Snapshot

FORGE-37 downstream runtime-readiness snapshot generated from backend DB/proof data.

- schema: `helm.iconforge.runtime_evidence_snapshot.v1`
- status: `snapshot_ready`
- snapshot_rows: `3057`
- runtime_rows: `0`
- hard_pile_rows: `3057`
- warning_only_rows: `0`
- matches_runtime_promotion_gate: `True`

## Runtime States

| State | Count |
| --- | ---: |
| `runtime_blocked` | 3057 |

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
