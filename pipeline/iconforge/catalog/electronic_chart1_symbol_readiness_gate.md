# Electronic Chart 1 Symbol Readiness Gate

CHART-10 release/verifier gate for Forge symbols in chartplotter render paths.

- schema: `helm.forge.electronic_chart1_symbol_readiness_gate.v1`
- status: `release_blocked`
- release_ready: `false`
- total_release_rows: `3057`
- registry_symbols: `2636`
- registry_semantic_accepted_rows: `1225`
- final_approved_rows: `0`
- runtime_export_rows: `0`
- hard_pile_rows: `698`
- unsupported_extension_profile_rows: `494`

## Decision

Runtime export remains zero and human/visual/runtime gates are blocked; CHART-10 records the current fail-closed release state.

## Checks

| Check | Status | Evidence |
| --- | --- | --- |
| `mapping_audit` | `pass` | `pipeline/iconforge/catalog/s101_mapping_audit.json` |
| `proof_gallery_and_human_signoff` | `blocked` | `pipeline/iconforge/proof/manifest.json`<br>`pipeline/iconforge/proof/package-proof-data.json`<br>`pipeline/iconforge/proof/compare-opencpn.html` |
| `cxx_loader_validates_package` | `pass` | `pipeline/iconforge/catalog/runtime_db_contract.json`<br>`pipeline/iconforge/catalog/runtime_evidence_snapshot.json`<br>`engine/test-symbol-package-loader.sh` |
| `attribute_fixture_suite` | `pass` | `engine/test/fixtures/symbol-selection/fixtures.json`<br>`engine/test-symbol-selection-fixtures.sh` |
| `vulkan_day_dusk_night_smoke` | `pass` | `engine/test/fixtures/vulkan-render/symbol-selection/manifest.json`<br>`engine/test-vulkan-symbol-selection-render.sh` |
| `opencpn_baseline_comparison` | `pass` | `pipeline/iconforge/catalog/electronic_chart1_opencpn_baseline.json` |
| `runtime_eligibility_gate` | `pass` | `pipeline/iconforge/catalog/electronic_chart1_runtime_promotion_gate.json`<br>`engine/test-symbol-runtime-gate.sh` |
| `adapter_handoff` | `pass` | `engine/vendor/cli/helm_symbol_render_handoff.cpp`<br>`engine/vendor/cli/helm_symbol_render_handoff_smoke.cpp`<br>`engine/test-symbol-render-handoff.sh`<br>`docs/VULKAN-RENDER-ADAPTERS.md` |

## Remaining Blockers

| Reason | Count |
| --- | ---: |
| `human_review_status:needs_human_review` | 3057 |
| `runtime_gate:fail_closed` | 3057 |
| `runtime_gate:promotion_not_allowed` | 3057 |
| `runtime_gate:runtime_eligible_false` | 3057 |
| `proof_gate:red` | 2891 |
| `visual_gate:red` | 2652 |
| `proof_gate:human_qa:pending` | 2359 |
| `proof_gate:runtime_gate:fail_closed` | 2359 |
| `proof_gate:visual_gate:red` | 1954 |
| `visual_gate:visual_palette:dusk:red` | 1954 |
| `visual_gate:visual_palette:night:red` | 1954 |
| `visual_gate:visual_palette:day:red` | 1952 |

## Validation Commands

- `PYTHONPATH=pipeline/iconforge python3 -m forge.tests.test_s101_mapping_audit`
- `PYTHONPATH=pipeline/iconforge python3 -m forge.tests.test_runtime_db_contract`
- `engine/test-symbol-package-loader.sh`
- `engine/test-symbol-selection-fixtures.sh`
- `engine/test-symbol-runtime-gate.sh`
- `engine/test-vulkan-symbol-selection-render.sh`
- `PYTHONPATH=pipeline/iconforge python3 -m forge.tests.test_electronic_chart1_opencpn_baseline`
- `engine/test-symbol-render-handoff.sh`
