# Electronic Chart 1 Diff Engine

FORGE-45 visual and semantic diff gates for Electronic Chart 1 rows.

- schema: `helm.forge.electronic_chart1_diff_engine.v1`
- status: `electronic_chart1_diff_engine_ready`
- authority_rows: `3057`
- diff_verdict_rows: `2359`
- diff_hard_pile_rows: `698`
- diff_pngs: `7077`
- runtime_eligible_rows: `0`

## Policy

- OpenCPN renders are comparison references, not Helm source artwork.
- Helm renders are generated-owned candidates.
- Unsupported or missing rows stay in hard-pile with reason codes.
- Visual/semantic diff gates never promote runtime output by themselves.

## Visual Gates

| Gate | Count |
| --- | ---: |
| `green` | 234 |
| `red` | 1954 |
| `yellow` | 171 |

## Semantic Gates

| Gate | Count |
| --- | ---: |
| `green` | 696 |
| `red` | 897 |
| `yellow` | 766 |

## Proof Gates

| Gate | Count |
| --- | ---: |
| `red` | 2193 |
| `yellow` | 166 |

## Hard Pile Reasons

| Reason | Count |
| --- | ---: |
| `diff:helm_s57_render_missing` | 683 |
| `diff:opencpn_reference_missing` | 597 |
| `diff:unsupported_taxonomy:non_reviewable_construct` | 273 |
| `diff:unsupported_taxonomy:placeholder_manual` | 238 |
| `diff:unsupported_taxonomy:runtime_overlay` | 16 |
