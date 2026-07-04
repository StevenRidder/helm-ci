# FORGE-14 Standards Alignment Gate

Status: `review_required`

This rollup aligns the standards evidence currently built for Icon Forge.
It does not approve rows; it tells downstream tasks which evidence is safe
to consume and why FORGE-22/23/24 remain provisional.

## Blockers
- `chart1_parity_status_not_pass`
- `no_final_approved_chart1_rows`
- `chart1_hard_pile_not_empty`
- `topmark_unresolved_rows_not_empty`

## Chart No.1 Parity

- rows: `824`
- gate_assets: `362`
- final_approved: `0`
- hard_pile_entries: `362`
- crop_count: `36`
- evidence_counts: `{'class_panel_reference': 20, 'exact_symbol_crop': 139, 'manual_exception': 28, 'multi_symbol_reference': 175, 'out_of_scope': 462}`
- verdict_counts: `{'deferred': 462, 'fail': 306, 'manual': 56}`

## Standard Source Table

- rows: `824`
- judge_queue_rows: `798`
- semantic_shape_judge_queue_rows: `798`
- candidate_status_counts: `{'chart1_parity_witness_needed': 2, 'judge_pass_pending_final_approval': 798, 'manual_policy_exception': 2, 'portrayal_rule_registry': 15, 'style_primitive_registry': 4, 'witness_needed_official_symbol': 3}`

## S-52/S-57/S-101 Crosswalk

- rows: `824`
- s101_exact_symbol_matches: `244`
- s101_feature_rule_candidates: `545`

## Topmark Standards

- topmark_rows_needing_special_pass: `137`
- resolved_exact_or_inferred_shape_rows: `134`
- ambiguous_or_unresolved_rows: `3`
- candidate_status_counts: `{'judge_pass_pending_final_approval': 136, 'portrayal_rule_registry': 1}`

## Clean-Room Boundary

OpenCPN, IHO, S-101, and Chart No.1 references are standards/comparison
evidence. They are not bundled source artwork for the generated Helm
symbol package.
