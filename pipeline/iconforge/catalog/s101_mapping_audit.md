# S-101 Mapping Audit

Status: `pass`

- rows: `824`
- s101_feature_equivalent: `675`
- non_s101_or_extension: `149`
- unresolved: `0`
- resolver_status_counts: `{'classified_extension_requires_profile': 107, 'classified_non_s101_runtime': 42, 'resolved_direct': 244, 'resolved_rule': 92, 'resolved_rule_catalogue': 264, 'resolved_with_deviation': 75}`
- mapping_type_counts: `{'acceptable_deviation': 75, 'direct_asset_match': 244, 'rule_derived_equivalent': 92, 'unresolved': 413}`
- crosswalk_class_counts: `{'non_s101_or_inland_extension': 107, 'non_s101_runtime_construct': 42, 's101_feature_equivalent': 600, 's101_feature_equivalent_with_documented_deviation': 75}`
- all_rows_accounted_for: `True`
- all_rows_classified: `True`
- all_rows_s101_feature_equivalent: `False`

## Consistency Checks

- colour_attribute_mismatches: `0`
- human_review_missing_symbol_id: `0`
- human_review_missing_shape_witness_note: `0`
- passed: `True`

The audit separates S-101 ENC feature-equivalent rows from renderer
runtime constructs and extension/inland profile rows. Do not claim
extension/runtime rows are S-101 ENC features.
