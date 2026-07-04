# S-52 / S-101 Rule Contract

Status: `provisional_rule_contract_ready`

Helm uses S-101 Lua/catalogue evidence to derive and audit symbol mappings, but does not yet claim full runtime-grade S-101 Lua rule execution. Runtime promotion remains fail-closed until S-52/S-101 instruction interpretation, recipes, stored Helm interpretation, visual proof, and human approval all pass.

This FORGE-27 artifact parses S-52 instructions into a normalized AST
and records an S-101 rule-contract status for every semantic evidence
row. It does not execute S-101 Lua and it does not approve runtime
export.

- rows: `824`
- s52_instruction_ast_status_counts: `{'parsed': 776, 'parsed_with_conditional_references': 48}`
- s101_rule_contract_status_counts: `{'catalogue_rule_reference_ready': 90, 'direct_symbol_contract_ready': 244, 'documented_deviation_review': 108, 'non_s101_or_extension_profile_required': 123, 'non_s101_runtime_construct': 44, 'rule_contract_ready': 215}`
- s52_command_counts: `{'AC': 26, 'AP': 28, 'CS': 48, 'LC': 43, 'LS': 71, 'SY': 787, 'TE': 363, 'TX': 82}`
- conditional_procedure_counts: `{'CLRLIN01': 1, 'DATCVR01': 1, 'DEPARE01': 1, 'DEPARE02': 1, 'DEPCNT02': 1, 'LEGLIN02': 1, 'LIGHTS05': 1, 'OBSTRN04': 3, 'OWNSHP02': 1, 'PASTRK01': 1, 'QUAPOS01': 3, 'RESARE01': 1, 'RESARE02': 2, 'RESTRN01': 20, 'SLCONS03': 3, 'SOUNDG02': 1, 'SYMINS01': 1, 'TOPMAR01': 1, 'TOPMARI1': 1, 'VESSEL01': 1, 'VRMEBL01': 1, 'WRECKS02': 1}`
- runtime_contract_ready: `0`
- runtime_contract_blocked_or_pending: `824`

What Helm follows now:

- S-52 `SY`, `LS`, `LC`, `AP`, `AC`, `TE`, `TX`, and `CS` tokens are parsed
  into a backend-owned AST.
- S-101 evidence is normalized as direct symbol, rule-derived, catalogue-rule,
  documented-deviation, runtime-construct, or extension/profile contract state.
- Missing S-101 filenames are not treated as missing mapping when the resolver
  has rule-derived or catalogue-rule evidence.

What remains provisional:

- S-101 Lua is not executed as runtime portrayal logic in this artifact.
- Conditional procedures are named and gated, not rendered by hidden fallback.
- Runtime export stays blocked until FORGE-31 sees complete rule, recipe,
  visual, provenance, and human-approval gates.
