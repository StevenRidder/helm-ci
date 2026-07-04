# Semantic Evidence DB View

Status: `provisional_semantic_evidence_db_ready`

Helm uses S-101 Lua/catalogue evidence to derive and audit symbol mappings, but does not yet claim full runtime-grade S-101 Lua rule execution. Runtime promotion remains fail-closed until S-52/S-101 instruction interpretation, recipes, stored Helm interpretation, visual proof, and human approval all pass.

This semantic evidence DB artifact is the backend row contract for proof pages,
judge prompts, and later runtime export gates. It is not a Lua
interpreter and it does not approve any symbol for runtime use. Later
FORGE gates add parsed rule contracts, symbol recipes, and stored
Helm interpretations into this same row payload.

- rows: `824`
- all_required_api_fields_returned: `True`
- required_api_fields_note: `Returned means the key is present in the API payload. Consumers must also check required_api_fields_populated and gap_counts_by_reason; empty S-101 fields are deliberate fail-closed gaps, not approvals.`
- required_api_fields_populated: `{'open_cpn_description': 824, 's57_object': 824, 's57_attribute_tuple': 824, 's57_description': 824, 's52_instruction': 824, 's52_instruction_ast': 824, 's52_instruction_ast_status': 824, 's101_rule_file': 587, 's101_feature_type': 587, 's101_attributes': 590, 's101_mapping_type': 824, 's101_rule_contract': 824, 's101_rule_contract_status': 824, 'resolver_status': 824, 'helm_symbol_recipe': 824, 'helm_symbol_recipe_status': 824, 'helm_interpretation': 824, 'helm_interpretation_status': 824, 'source_refs': 824, 'unresolved_reasons': 365, 'runtime_gate_summary': 824}`
- runtime_gate_counts: `{'runtime_eligible': 0, 'runtime_blocked_or_pending': 824, 'status_counts': {'blocked': 123, 'manual_review_required': 44, 'pending': 657}}`
- resolver_status_counts: `{'classified_extension_requires_profile': 123, 'classified_non_s101_runtime': 44, 'resolved_direct': 244, 'resolved_rule': 215, 'resolved_rule_catalogue': 90, 'resolved_with_deviation': 108}`
- s101_crosswalk_class_counts: `{'non_s101_or_inland_extension': 123, 'non_s101_runtime_construct': 44, 's101_feature_equivalent': 549, 's101_feature_equivalent_with_documented_deviation': 108}`
- s52_instruction_ast_status_counts: `{'parsed': 776, 'parsed_with_conditional_references': 48}`
- s101_rule_contract_status_counts: `{'catalogue_rule_reference_ready': 90, 'direct_symbol_contract_ready': 244, 'documented_deviation_review': 108, 'non_s101_or_extension_profile_required': 123, 'non_s101_runtime_construct': 44, 'rule_contract_ready': 215}`
- helm_symbol_recipe_status_counts: `{'manual_exception_required': 206, 'recipe_missing': 44, 'recipe_ready': 574}`
- helm_interpretation_status_counts: `{'helm_interpretation_manual_required': 325, 'helm_interpretation_pending_evidence': 44, 'helm_interpretation_ready': 455}`
- helm_interpretation_validation_counts: `{'passed': 824}`

Gap counts:

- `helm_interpretation_not_ready`: `369`
- `helm_symbol_recipe_not_ready`: `250`
- `no_opencpn_render_reference`: `47`
- `non_s101_or_inland_extension`: `123`
- `non_s101_runtime_construct`: `44`
- `resolver_has_visible_unresolved_reasons`: `365`
- `runtime_not_eligible`: `824`
- `s57_description_derived_pending_catalogue_prose`: `824`

Consumer rule: browser and static proof pages display this payload only.
They must not derive symbol meaning, colors, mappings, or runtime gates
from filenames or hidden JavaScript fallbacks.

Adjacent gates:

- `s101_mapping_audit`: accepted in `FORGE-23`/`FORGE-24`; the current
  audit accounts for all 824 rows and keeps raw S-101 SVGs labelled as
  shape witnesses rather than color-resolved portrayal.
- `stacked_pr`: accepted and merged via Helm PR #243 into
  `codex/FORGE-12-chart1-parity` at
  `d86fb3ae90e0900597b63bd431618efff19dbd55`.
