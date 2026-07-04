# Electronic Chart 1 OpenCPN Baseline Comparison

CHART-8 manifest joining Forge renders to OpenCPN day/dusk/night reference outputs.

- schema: `helm.forge.electronic_chart1_opencpn_baseline.v1`
- status: `opencpn_baseline_comparison_ready`
- rows: `3057`
- runtime_promotion_allowed_rows: `0`

## Source Boundary

- OpenCPN render paths are reference/comparison only.
- Helm fixture renders are generated-owned candidates.
- Visual diffs and tolerance checks are QA diagnostics, not runtime promotion.

## Comparison Status

| Status | Count |
| --- | ---: |
| `needs-review` | 2353 |
| `not-comparable` | 698 |
| `pass` | 6 |

## Tolerance Checks

| Check/status | Count |
| --- | ---: |
| `blank_render:not-comparable` | 2094 |
| `blank_render:pass` | 7077 |
| `wrong_anchor:needs-review` | 4494 |
| `wrong_anchor:not-comparable` | 2094 |
| `wrong_anchor:pass` | 2583 |
| `wrong_palette:needs-review` | 59 |
| `wrong_palette:not-comparable` | 2094 |
| `wrong_palette:pass` | 7018 |
| `wrong_symbol_class:needs-review` | 5860 |
| `wrong_symbol_class:not-comparable` | 2094 |
| `wrong_symbol_class:pass` | 1217 |

## Human Approval

| State | Count |
| --- | ---: |
| `needs_human_review` | 3057 |
