# Electronic Chart 1 Runtime Promotion Gate

FORGE-47 fail-closed runtime/package eligibility contract.

- schema: `helm.forge.electronic_chart1_runtime_promotion_gate.v1`
- status: `fail_closed`
- authority_rows: `3057`
- proof_rows: `2359`
- hard_pile_rows: `698`
- runtime_export_rows: `0`
- blocked_rows: `3057`
- backend_runtime_eligible_rows: `0`
- backend_runtime_promotion_allowed_rows: `0`

## Policy

- Runtime export defaults to fail-closed.
- UI feedback/status cannot promote an icon.
- Filename-only S-101 matches cannot promote an icon.
- Promotion requires green visual, semantic, and proof gates.
- Promotion requires authority text, DB-backed S-101 trace, render source hashes, clean-room provenance, and final QA approval.
- OpenCPN remains comparison evidence only; Helm runtime output uses generated-owned render evidence.

## Top Blockers

| Reason | Count |
| --- | ---: |
| `authority_status:authority_text_manual_required` | 511 |
| `authority_status:authority_text_pending_source` | 1657 |
| `human_review_status:needs_human_review` | 3057 |
| `proof_bundle:diff:helm_s57_render_missing` | 683 |
| `proof_bundle:diff:opencpn_reference_missing` | 597 |
| `proof_bundle:diff:unsupported_taxonomy:non_reviewable_construct` | 273 |
| `proof_bundle:diff:unsupported_taxonomy:placeholder_manual` | 238 |
| `proof_bundle:diff:unsupported_taxonomy:runtime_overlay` | 16 |
| `proof_bundle:hard_pile` | 698 |
| `proof_bundle:helm_recipe:missing` | 683 |
| `proof_bundle:helm_s101_trace:missing` | 534 |
| `proof_bundle:helm_s57_render:missing` | 683 |
| `proof_bundle:helm_shape_family:missing` | 230 |
| `proof_bundle:opencpn_reference_render:missing` | 597 |
| `proof_bundle:s101_db_backing:missing` | 150 |
| `proof_bundle:s101_feature_type:missing` | 349 |
| `proof_bundle:s101_forge43_trace:missing` | 534 |
| `proof_bundle:s52_instruction:missing` | 52 |
| `proof_bundle:s52_parse_status:partial` | 7 |
| `proof_gate:diff:helm_s57_render_missing` | 683 |
| `proof_gate:diff:opencpn_reference_missing` | 597 |
| `proof_gate:diff:unsupported_taxonomy:non_reviewable_construct` | 273 |
| `proof_gate:diff:unsupported_taxonomy:placeholder_manual` | 238 |
| `proof_gate:diff:unsupported_taxonomy:runtime_overlay` | 16 |
| `proof_gate:helm_recipe:missing` | 683 |
| `proof_gate:helm_s101_trace:missing` | 534 |
| `proof_gate:helm_s57_render:missing` | 683 |
| `proof_gate:helm_shape_family:missing` | 230 |
| `proof_gate:human_qa:pending` | 2359 |
| `proof_gate:opencpn_reference_render:missing` | 597 |
| `proof_gate:red` | 2891 |
| `proof_gate:runtime_gate:fail_closed` | 2359 |
| `proof_gate:s101_db_backing:missing` | 150 |
| `proof_gate:s101_feature_type:missing` | 349 |
| `proof_gate:s101_forge43_trace:missing` | 534 |
| `proof_gate:s52_instruction:missing` | 52 |
| `proof_gate:s52_parse_status:partial` | 7 |
| `proof_gate:semantic_gate:red` | 897 |
| `proof_gate:semantic_gate:yellow` | 766 |
| `proof_gate:visual_gate:red` | 1954 |

## Remediation Hints

| Hint | Count |
| --- | ---: |
| Clear proof-bundle blockers before runtime review. | 3057 |
| Complete backend authority text and source-language evidence. | 2168 |
| Keep runtime promotion blocked until the backend gate explicitly allows it. | 3057 |
| Record final QA/human approval outside the proof UI. | 3057 |
| Regenerate render outputs with source paths and sha256 hashes. | 698 |
| Repair Helm visual output and rerun the visual diff engine. | 2823 |
| Repair S-101 resolver trace, DB backing, rule evidence, or mapping classification. | 1374 |
| Repair authority, S-57, S-101, or recipe semantics and rerun proof. | 2361 |
| Repair missing proof inputs before runtime review. | 698 |
| Repair the source evidence that produced this blocker and rerun the proof chain. | 698 |
| Resolve the fail-closed runtime gate in the DB contract. | 3057 |
| Set runtime eligibility only from the DB promotion contract after every gate passes. | 3057 |
