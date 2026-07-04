# Standard Judge Batch 048 Rerun

- Project: `vulkan`
- Task: `FORGE-14`
- Agent: `codex/FORGE-14-batch48-judge`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch48.json`
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Scope: `TOPSHP22, TOPSHP23, TOPSHP24, TOPSHP25, TOPSHP28, TOPSHP29, TOPSHP30, TOPSHP31, TOPSHP32, TOPSHP33, TOPSHP34, TOPSHP35, TOPSHP36, TOPSHP37, TOPSHP38, TOPSHP40, TOPSHP41, TOPSHP42, TOPSHP43, TOPSHP44`

Pass means `judge_pass_pending_final_approval` only. This rerun grants zero final approvals.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 20 |
| Pass pending human | 0 |
| Fail | 20 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `TOPSHP22` | Fail | 0.96 | Redraw TOPSHP22 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: red. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch | Fail: red fill is present, but the repaired mark is a tall vertical rectangle. The OpenCPN S-52 witness is a compact square board, so the board silhouette/reference family is still wrong. |
| `TOPSHP23` | Fail | 0.96 | Redraw TOPSHP23 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: black. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch | Fail: black fill is present, but the repaired mark is a tall vertical rectangle instead of the compact square board witness. |
| `TOPSHP24` | Fail | 0.96 | Redraw TOPSHP24 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: green. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch | Fail: green fill is present, but the repaired mark keeps the same tall-rectangle board template and does not match the square-board reference silhouette. |
| `TOPSHP25` | Fail | 0.96 | Redraw TOPSHP25 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: white, orange with S-57 colour pattern 6. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: the white/orange colours are present, but the candidate uses full-height side-by-side stripes in a tall rectangle. The reference is a compact square board with S-57 pattern-6 treatment, so silhouette and pattern family still mismatch. |
| `TOPSHP28` | Fail | 0.96 | Redraw TOPSHP28 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: green, white, black. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: the listed green/white/black colours are present, but the tall three-stripe rectangle does not match the compact square-board reference family. |
| `TOPSHP29` | Fail | 0.96 | Redraw TOPSHP29 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: red, green, red with S-57 colour pattern 6. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: the red/green/red colour order is present, but the repaired SVG is a tall vertical stripe board rather than the compact square-board pattern-6 witness. |
| `TOPSHP30` | Fail | 0.96 | Redraw TOPSHP30 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: green, green, yellow with S-57 colour pattern 6. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: the green/green/yellow colour order is present, but the same tall rectangular template remains instead of the compact square-board S-57 pattern-6 witness. |
| `TOPSHP31` | Fail | 0.96 | Redraw TOPSHP31 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: orange, white with S-57 colour pattern 6. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: orange/white colours are present, but the repaired mark is a tall two-stripe rectangle and not the compact square-board S-57 pattern-6 reference. |
| `TOPSHP32` | Fail | 0.96 | Redraw TOPSHP32 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: red, white with vertical bands/stripes in the listed colour order. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: red/white vertical stripes are present, but the board silhouette is the tall rectangle template rather than the compact square-board witness. |
| `TOPSHP33` | Fail | 0.88 | Redraw TOPSHP33 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: green, red, green with S-57 colour pattern 6. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch, missing_direct_opencpn_render_in_checkout | Fail: green/red/green order is present, but the repaired mark uses the same tall vertical rectangle template. The available Chart No.1/source-matrix witness is a compact board family, not this silhouette. |
| `TOPSHP34` | Fail | 0.96 | Redraw TOPSHP34 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: white, orange, white with vertical bands/stripes in the listed colour order. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: white/orange/white order is present, but the vertical stripe treatment is inside a tall rectangle instead of the compact square-board reference family. |
| `TOPSHP35` | Fail | 0.96 | Redraw TOPSHP35 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: yellow. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch | Fail: yellow fill is present, but the repaired board is a tall rectangle and not the compact square board in the OpenCPN witness. |
| `TOPSHP36` | Fail | 0.96 | Redraw TOPSHP36 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: orange. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch | Fail: orange fill is present, but the board silhouette remains a tall rectangle instead of the compact square-board reference. |
| `TOPSHP37` | Fail | 0.96 | Redraw TOPSHP37 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: black, black with S-57 colour pattern 6. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: black fill is present, but the candidate does not encode the compact square-board S-57 pattern-6 witness; it remains the tall rectangle template. |
| `TOPSHP38` | Fail | 0.96 | Redraw TOPSHP38 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: orange, white with S-57 colour pattern 6; squared/checkered pattern in the listed colour order. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: orange/white checker colours are present, but the candidate is a tall 2x2 rectangle/checker. The OpenCPN witness is a compact square-board checker, so both silhouette and pattern proportions mismatch. |
| `TOPSHP40` | Fail | 0.96 | Redraw TOPSHP40 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: white, black with S-57 colour pattern 6. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: white/black colours are present, but the repaired mark is a tall two-stripe rectangle rather than the compact square-board S-57 pattern-6 witness. |
| `TOPSHP41` | Fail | 0.96 | Redraw TOPSHP41 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: orange, orange with horizontal bands/stripes in the listed colour order. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: orange/orange horizontal bands are present, but they are applied to the tall rectangle template. The OpenCPN witness remains a compact square-board family. |
| `TOPSHP42` | Fail | 0.96 | Redraw TOPSHP42 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: red, white with horizontal bands/stripes in the listed colour order. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: red/white horizontal bands are present, but the tall rectangular board does not match the compact square-board reference silhouette. |
| `TOPSHP43` | Fail | 0.96 | Redraw TOPSHP43 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: green, red, green with S-57 colour pattern 6; horizontal bands/stripes in the listed colour order. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: green/red/green horizontal bands are present, but the board silhouette is still the tall rectangle template rather than the compact square-board S-57 pattern-6 witness. |
| `TOPSHP44` | Fail | 0.96 | Redraw TOPSHP44 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: yellow, yellow with S-57 colour pattern 6. | wrong_board_silhouette, wrong_aspect_ratio, reference_mismatch, colour_pattern_mismatch | Fail: yellow fill is present, but the repaired mark remains a tall rectangle and does not match the compact square-board pattern-6 reference family. |

## Failed Symbols

- `TOPSHP22`: Redraw TOPSHP22 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: red.
- `TOPSHP23`: Redraw TOPSHP23 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: black.
- `TOPSHP24`: Redraw TOPSHP24 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: green.
- `TOPSHP25`: Redraw TOPSHP25 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: white, orange with S-57 colour pattern 6.
- `TOPSHP28`: Redraw TOPSHP28 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: green, white, black.
- `TOPSHP29`: Redraw TOPSHP29 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: red, green, red with S-57 colour pattern 6.
- `TOPSHP30`: Redraw TOPSHP30 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: green, green, yellow with S-57 colour pattern 6.
- `TOPSHP31`: Redraw TOPSHP31 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: orange, white with S-57 colour pattern 6.
- `TOPSHP32`: Redraw TOPSHP32 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: red, white with vertical bands/stripes in the listed colour order.
- `TOPSHP33`: Redraw TOPSHP33 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: green, red, green with S-57 colour pattern 6.
- `TOPSHP34`: Redraw TOPSHP34 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: white, orange, white with vertical bands/stripes in the listed colour order.
- `TOPSHP35`: Redraw TOPSHP35 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: yellow.
- `TOPSHP36`: Redraw TOPSHP36 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: orange.
- `TOPSHP37`: Redraw TOPSHP37 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: black, black with S-57 colour pattern 6.
- `TOPSHP38`: Redraw TOPSHP38 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: orange, white with S-57 colour pattern 6; squared/checkered pattern in the listed colour order.
- `TOPSHP40`: Redraw TOPSHP40 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: white, black with S-57 colour pattern 6.
- `TOPSHP41`: Redraw TOPSHP41 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: orange, orange with horizontal bands/stripes in the listed colour order.
- `TOPSHP42`: Redraw TOPSHP42 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: red, white with horizontal bands/stripes in the listed colour order.
- `TOPSHP43`: Redraw TOPSHP43 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: green, red, green with S-57 colour pattern 6; horizontal bands/stripes in the listed colour order.
- `TOPSHP44`: Redraw TOPSHP44 as the compact square-board TOPSHP witness, not a tall vertical rectangle; preserve the required colour order/pattern: yellow, yellow with S-57 colour pattern 6.

## Evidence Notes

- Actual repaired SVGs were read from pipeline/iconforge/assets/svg/owned_repair_batch48/.
- Candidate day/dusk/night render paths are present under pipeline/iconforge/out/standard_repair_batch40/renders/.
- Prior judge feedback came from pipeline/iconforge/catalog/standard_judge_batch_013.json / .md, which failed these TOPSHP rows for circular placeholders missing board silhouette, orientation, and pattern semantics.
- OpenCPN S-52 day references were present under pipeline/iconforge/out/opencpn_s52_reference/ for all selected rows except TOPSHP33; TOPSHP33 was judged against semantic_brief plus source_variant_matrix/Chart No.1 witnesses and the same repaired SVG template.
- All repaired rows replace the circle placeholder, but with a tall vertical rectangle template whose aspect ratio and board silhouette do not match the compact square-board reference family.
- Passes remain judge_pass_pending_final_approval only; this batch has no passes and grants zero final approvals.
