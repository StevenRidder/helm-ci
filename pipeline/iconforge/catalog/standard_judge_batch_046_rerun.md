# Standard Judge Batch 046 Rerun

- Project: `vulkan`
- Task: `FORGE-14`
- Agent: `codex/FORGE-14-judge46`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch46.json`
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Scope: `TOPMA100, TOPMA102, TOPMA106, TOPMA107, TOPMA109, TOPMA111, TOPMA113, TOPMA114, TOPMA115, TOPMA116, TOPMA117, TOPMAR01, TOPMAR87, TOPMAR88, TOPMAR90, TOPMAR91, TOPMAR92, TOPMAR93, TOPMAR98, TOPMAR99`

Pass means `judge_pass_pending_final_approval` only. This rerun grants zero final approvals.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 20 |
| Pass pending human | 9 |
| Fail | 11 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `TOPMA100` | Pass pending human | 0.92 | No further repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: red cone silhouette and point-down orientation are restored against the semantic brief and prior judge expectation. No final approval is granted without exact crop/human signoff. |
| `TOPMA102` | Pass pending human | 0.92 | No further repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: green cone silhouette and point-up orientation are restored. This remains pending exact crop/human review, not final approval. |
| `TOPMA106` | Fail | 0.90 | Redraw TOPMA106 as the exact white-red-white square-board topmark/proportions from the reference, not a tall rectangular sign. | wrong_shape, wrong_board_proportion, reference_mismatch | Fail: the colour order is restored, but the repaired shape is a tall vertical rectangle while the source spine records a 15x15 square board. Topmark shape/proportion is load-bearing for this batch. |
| `TOPMA107` | Fail | 0.89 | Redraw TOPMA107 as the exact red-bordered square-board topmark with square proportions. | wrong_shape, wrong_board_proportion, reference_mismatch | Fail: red-bordered board semantics are partly restored, but the candidate is a tall rectangle rather than the square board recorded by the 15x15 source metadata. |
| `TOPMA109` | Fail | 0.94 | Redraw TOPMA109 as the exact green-boarded diagonal square/diamond board topmark, preserving white/green pattern semantics. | wrong_shape, wrong_orientation, wrong_colour_pattern, reference_mismatch | Fail: the circle is gone, but the repaired glyph lacks the diagonal square/diamond board family and does not show the required diagonal green treatment/orientation. |
| `TOPMA111` | Pass pending human | 0.90 | No further repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: the repaired glyph restores the yellow upright cross family and removes the prior disk. Stroke weight/proportion remain human-review details. |
| `TOPMA113` | Pass pending human | 0.90 | No further repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: the diagonal yellow cross family is restored and the previous disk is gone. No final approval is implied. |
| `TOPMA114` | Fail | 0.91 | Redraw TOPMA114 to the exact narrow red topmark silhouette/proportions from the reference, not a generic rectangle. | wrong_shape, wrong_reference_family, reference_mismatch | Fail: the repair changes disk to board, but the row metadata records a narrow 8x23 topmark silhouette. A broad rectangle does not prove the exact reference family. |
| `TOPMA115` | Fail | 0.96 | Redraw TOPMA115 as the exact green cone/triangle-style topmark silhouette from the reference. | wrong_shape, wrong_topmark_family, reference_mismatch | Fail: the prior judge explicitly expected a green cone/triangle-style topmark. The repaired candidate is a rectangle and therefore remains the wrong topmark shape family. |
| `TOPMA116` | Fail | 0.93 | Redraw TOPMA116 as the exact red-white-red entry-prohibited board topmark with correct board proportions and band order. | wrong_shape, wrong_board_proportion, reference_mismatch | Fail: red-white-red order is present, but the source spine records a short/wide 14x10 board; the candidate is a tall rectangle and does not match the reference board shape. |
| `TOPMA117` | Pass pending human | 0.88 | No further repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: the missing green portion is restored and the glyph is a red/green sphere rather than a plain red disk. Exact crop review is still required before final approval. |
| `TOPMAR01` | Pass pending human | 0.84 | No further repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human, moderate confidence: the single red disk is replaced by a red/green sphere. The source spine has unusual dimensions/colour tokens, so this remains human-review only. |
| `TOPMAR87` | Fail | 0.95 | Remove the extra crossbar and redraw TOPMAR87 as the exact three-stroke black point-down besom reference shape. | wrong_shape, extra_stroke, reference_mismatch | Fail: orientation is close, but the available S-101 exact reference has only the central stem and two diagonal broom strokes. The added crossbar changes the topmark silhouette. |
| `TOPMAR88` | Fail | 0.95 | Remove the extra crossbar and redraw TOPMAR88 as the exact three-stroke black point-up besom reference shape. | wrong_shape, extra_stroke, reference_mismatch | Fail: point-up orientation is close, but the S-101 exact reference has no crossbar. The added stroke makes the silhouette/reference family wrong. |
| `TOPMAR90` | Pass pending human | 0.82 | No further repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human, low confidence: point-down Pricken/stake family is restored and the disk is gone. Exact OpenCPN crop/render is absent in the tracked checkout, so this cannot be final-approved. |
| `TOPMAR91` | Fail | 0.88 | Redraw TOPMAR91 against the exact reference silhouette for that symbol, preserving red colour without substituting a generic rectangle. | wrong_shape, generic_board_substitution, reference_mismatch | Fail: the prior disk is gone, but the generic rectangular board does not prove the exact TOPMAR91 reference family/proportions recorded by the source row. |
| `TOPMAR92` | Fail | 0.88 | Redraw TOPMAR92 against the exact reference silhouette for that symbol, preserving green colour without substituting a generic rectangle. | wrong_shape, generic_board_substitution, reference_mismatch | Fail: the repair replaces a disk with a rectangle, but the exact TOPMAR92 topmark family/proportions are still not matched. |
| `TOPMAR93` | Pass pending human | 0.82 | No further repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human, low confidence: point-up Pricken/stake family is restored and the disk is gone. Exact OpenCPN crop/render is absent in the tracked checkout, so this cannot be final-approved. |
| `TOPMAR98` | Fail | 0.89 | Redraw TOPMAR98 as the exact diagonal square/diamond board topmark, preserving the row colour pattern. | wrong_shape, wrong_orientation, reference_mismatch | Fail: the diagonal colour split is present, but the repaired silhouette is a vertical rectangle. The source spine uses TOPSHP12/diamond-square topmark semantics, so shape/orientation still do not match. |
| `TOPMAR99` | Pass pending human | 0.86 | No further repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human, moderate confidence: the yellow diamond shape requested by the prior judge is restored. The row metadata has conflicting colour tokens, so this remains pending human/reference signoff. |

## Pass Notes

- `TOPMA100`: Pass pending human: red cone silhouette and point-down orientation are restored against the semantic brief and prior judge expectation. No final approval is granted without exact crop/human signoff.
- `TOPMA102`: Pass pending human: green cone silhouette and point-up orientation are restored. This remains pending exact crop/human review, not final approval.
- `TOPMA111`: Pass pending human: the repaired glyph restores the yellow upright cross family and removes the prior disk. Stroke weight/proportion remain human-review details.
- `TOPMA113`: Pass pending human: the diagonal yellow cross family is restored and the previous disk is gone. No final approval is implied.
- `TOPMA117`: Pass pending human: the missing green portion is restored and the glyph is a red/green sphere rather than a plain red disk. Exact crop review is still required before final approval.
- `TOPMAR01`: Pass pending human, moderate confidence: the single red disk is replaced by a red/green sphere. The source spine has unusual dimensions/colour tokens, so this remains human-review only.
- `TOPMAR90`: Pass pending human, low confidence: point-down Pricken/stake family is restored and the disk is gone. Exact OpenCPN crop/render is absent in the tracked checkout, so this cannot be final-approved.
- `TOPMAR93`: Pass pending human, low confidence: point-up Pricken/stake family is restored and the disk is gone. Exact OpenCPN crop/render is absent in the tracked checkout, so this cannot be final-approved.
- `TOPMAR99`: Pass pending human, moderate confidence: the yellow diamond shape requested by the prior judge is restored. The row metadata has conflicting colour tokens, so this remains pending human/reference signoff.

## Failed Symbols

- `TOPMA106`: Redraw TOPMA106 as the exact white-red-white square-board topmark/proportions from the reference, not a tall rectangular sign.
- `TOPMA107`: Redraw TOPMA107 as the exact red-bordered square-board topmark with square proportions.
- `TOPMA109`: Redraw TOPMA109 as the exact green-boarded diagonal square/diamond board topmark, preserving white/green pattern semantics.
- `TOPMA114`: Redraw TOPMA114 to the exact narrow red topmark silhouette/proportions from the reference, not a generic rectangle.
- `TOPMA115`: Redraw TOPMA115 as the exact green cone/triangle-style topmark silhouette from the reference.
- `TOPMA116`: Redraw TOPMA116 as the exact red-white-red entry-prohibited board topmark with correct board proportions and band order.
- `TOPMAR87`: Remove the extra crossbar and redraw TOPMAR87 as the exact three-stroke black point-down besom reference shape.
- `TOPMAR88`: Remove the extra crossbar and redraw TOPMAR88 as the exact three-stroke black point-up besom reference shape.
- `TOPMAR91`: Redraw TOPMAR91 against the exact reference silhouette for that symbol, preserving red colour without substituting a generic rectangle.
- `TOPMAR92`: Redraw TOPMAR92 against the exact reference silhouette for that symbol, preserving green colour without substituting a generic rectangle.
- `TOPMAR98`: Redraw TOPMAR98 as the exact diagonal square/diamond board topmark, preserving the row colour pattern.

## Evidence Notes

- Actual repaired SVGs were read from pipeline/iconforge/assets/svg/owned_repair_batch46/.
- Before SVG paths resolve to the repaired canonical SVGs in this detached checkout; before-state semantics therefore come from the prior failed judge observations embedded in standard_source_table.json and catalog/standard_judge_batch_012.json.
- Candidate day/dusk/night render paths are listed by owned_repair_batch46 metadata under pipeline/iconforge/out/standard_repair_batch38/renders/, but those generated PNGs are not present in the tracked detached checkout.
- Provider references used include each row semantic_brief, source-table row metadata, prior failed judge feedback, OpenCPN S-52 spine metadata/reference-render records, Chart No.1 reference metadata where recorded, and available S-101 exact SVG witnesses for TOPMAR87/TOPMAR88.
- Passes remain judge_pass_pending_final_approval only and grant zero final approvals.
