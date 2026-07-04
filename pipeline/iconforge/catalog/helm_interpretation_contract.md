# Helm Interpretation Contract

Status: `provisional_helm_interpretation_contract_ready`

This FORGE-29 artifact stores the human-readable Helm interpretation
for each semantic evidence row. It is generated from backend evidence
and validated against DB fields; it is not generated in browser code.

- rows: `824`
- versions: `{'interpretation': 'helm_interpretation_v1', 'prompt': 'helm_interpretation_prompt_v1', 'output_schema': 'helm_interpretation_output_schema_v1'}`
- status_counts: `{'helm_interpretation_manual_required': 325, 'helm_interpretation_pending_evidence': 44, 'helm_interpretation_ready': 455}`
- validation_counts: `{'passed': 824}`
- reason_counts: `{'helm_symbol_recipe:manual_exception_required': 206, 'helm_symbol_recipe:recipe_missing': 44, 's101_crosswalk:non_s101_or_inland_extension': 123, 's101_crosswalk:non_s101_runtime_construct': 44, 's101_rule_contract:non_s101_or_extension_profile_required': 123, 's101_rule_contract:non_s101_runtime_construct': 44}`

Consumer rule: proof pages, judge prompts, and repair agents display
`helm_interpretation_v1` from the backend payload. They must not infer
meaning, colors, shape family, S-101 equivalence, or runtime eligibility
from filenames or hidden JavaScript fallbacks.

Runtime rule: this artifact explains rows only. FORGE-31 remains the
runtime export gate and must require interpretation status, recipe status,
visual proof, provenance, and human approval before export.
