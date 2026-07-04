# Standard Judge Batch 045 Rerun

- Project: `vulkan`
- Task: `FORGE-14`
- Agent: `codex/FORGE-14-batch45-judge`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch45.json`
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Scope: `REFDMP01, RFNERY01, RFNERY11, RTLDEF51, SCALEB10, SCALEB11, SILBUI01, SILBUI11, SISTAT02, SSENTR01, SSLOCK01, SSWARS01, STARPT01, TMBYRD01, TNKCON02, TNKCON12, TNKFRM01, TNKFRM11`

Pass means `judge_pass_pending_final_approval` only. This rerun grants zero final approvals.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 18 |
| Pass pending human | 6 |
| Fail | 12 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `REFDMP01` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: refuse-can semantics and green/black colour family are restored. This remains a generated-owned redraw against an OpenCPN-only visual witness, so no final approval is granted. |
| `RFNERY01` | Fail | 0.93 | Redraw RFNERY01 as the brown circular refinery glyph matching the S-101/OpenCPN witness, including the enclosing circle and refinery detail. | wrong_shape, missing_reference_circle, reference_mismatch | Fail: the refinery colour family is brown, but the shape/reference family is still wrong because the exact S-101 witness includes a circular refinery enclosure around the chimney/flame detail. |
| `RFNERY11` | Fail | 0.94 | Redraw RFNERY11 as the black circular conspicuous-refinery glyph matching the S-101/OpenCPN witness, including the enclosing circle. | wrong_shape, missing_reference_circle, reference_mismatch | Fail: the black colour is restored, but the exact/provider family is a circular refinery glyph. The candidate remains an unenclosed generic refinery pictogram. |
| `RTLDEF51` | Pass pending human | 0.83 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human, low confidence: the route/unknown-direction semantics and magenta family are restored. Geometry is simplified versus the exact S-101 witness, so this is human-review only and not final approval. |
| `SCALEB10` | Fail | 0.96 | Redraw SCALEB10 as the thin alternating grey/orange vertical one-mile scale pattern from the S-101/OpenCPN witness; remove black/white blocks, side ticks, and the text label. | wrong_colour_family, wrong_scalebar_pattern, wrong_text_glyph, reference_mismatch | Fail: the orientation is vertical, but the colour family, segment treatment, width, and text semantics still do not match the exact scalebar witness. |
| `SCALEB11` | Fail | 0.95 | Redraw SCALEB11 as the thin alternating black/grey vertical latitude-scale segment pattern from the S-101/OpenCPN witness; remove the block ladder, side ticks, and text label. | wrong_scalebar_pattern, wrong_text_glyph, wrong_shape, reference_mismatch | Fail: the candidate is vertical but still uses a block ladder plus text label rather than the exact thin segmented latitude-scale witness. |
| `SILBUI01` | Fail | 0.94 | Replace the large cylinder with the small brown silo point/circle mark matching the S-101/OpenCPN witness. | wrong_shape, wrong_scale, reference_mismatch | Fail: the diamond is gone and brown is restored, but the reference family is a compact point/circle mark. The tall cylinder changes shape and scale semantics. |
| `SILBUI11` | Fail | 0.94 | Replace the large cylinder with the small black conspicuous silo point/circle mark matching the S-101/OpenCPN witness. | wrong_shape, wrong_scale, reference_mismatch | Fail: black colour is restored, but the candidate substitutes a large silo building pictogram for the exact compact point/circle witness. |
| `SISTAT02` | Pass pending human | 0.82 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human, low confidence: the SS label and board family are restored. The tracked checkout lacks the OpenCPN render PNG and the white fill/scale details still need human crop review before any final approval. |
| `SSENTR01` | Fail | 0.90 | Redraw SSENTR01 as the port-entry signal-station board glyph matching the OpenCPN witness, not a generic PE text sign. | wrong_text_glyph, missing_signal_pictogram, reference_mismatch | Fail: the board/post family is present, but replacing the port-entry pictogram with a PE text label changes the text/glyph semantics and does not match the provider witness. |
| `SSLOCK01` | Fail | 0.91 | Redraw SSLOCK01 as the lock signal-station board glyph matching the OpenCPN witness, preserving the lock/two-light detail instead of an LK label. | wrong_text_glyph, missing_signal_board_detail, reference_mismatch | Fail: LK text does not replace the required lock signal-board detail. The glyph semantics remain a generic label rather than the provider reference. |
| `SSWARS01` | Fail | 0.92 | Redraw SSWARS01 as the triangular wahrschau signal-station board glyph matching the OpenCPN witness; do not substitute a WS text sign. | wrong_shape, wrong_text_glyph, missing_triangular_signal_board, reference_mismatch | Fail: the candidate is a rectangular text sign, but the prior judge specifically required the triangular wahrschau signal-board shape. |
| `STARPT01` | Pass pending human | 0.89 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: star shape and black colour family are restored. Size/proportion remain non-final human-review details. |
| `TMBYRD01` | Fail | 0.91 | Redraw TMBYRD01 as the open brown timber-yard hash/grid with the reference two-horizontal/two-vertical stroke structure and proportions. | wrong_grid_structure, wrong_stroke_count, reference_mismatch | Fail: the enclosure is removed, but the exact S-101 witness is a lighter two-by-two hash with two horizontal and two vertical strokes. The repaired grid still changes the reference structure. |
| `TNKCON02` | Pass pending human | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: simple circular tank-ring shape and brown/land colour family are restored. Stroke/proportion differences still need human review before final approval. |
| `TNKCON12` | Pass pending human | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: black circular conspicuous-tank ring semantics are restored. No final approval implied. |
| `TNKFRM01` | Fail | 0.87 | Redraw TNKFRM01 with the brown circular enclosure and the reference four-dot tank-farm cluster pattern; remove the extra center dot. | wrong_cluster_count, reference_mismatch | Fail: the enclosure is restored, but the internal cluster count/pattern still does not match the exact S-101/OpenCPN witness. |
| `TNKFRM11` | Fail | 0.87 | Redraw TNKFRM11 with the black circular enclosure and the reference four-dot tank-farm cluster pattern; remove the extra center dot. | wrong_cluster_count, reference_mismatch | Fail: the black enclosure is restored, but the internal tank-farm cluster pattern has an extra center dot and remains reference-mismatched. |

## Pass Notes

- `REFDMP01`: Pass pending human: refuse-can semantics and green/black colour family are restored. This remains a generated-owned redraw against an OpenCPN-only visual witness, so no final approval is granted.
- `RTLDEF51`: Pass pending human, low confidence: the route/unknown-direction semantics and magenta family are restored. Geometry is simplified versus the exact S-101 witness, so this is human-review only and not final approval.
- `SISTAT02`: Pass pending human, low confidence: the SS label and board family are restored. The tracked checkout lacks the OpenCPN render PNG and the white fill/scale details still need human crop review before any final approval.
- `STARPT01`: Pass pending human: star shape and black colour family are restored. Size/proportion remain non-final human-review details.
- `TNKCON02`: Pass pending human: simple circular tank-ring shape and brown/land colour family are restored. Stroke/proportion differences still need human review before final approval.
- `TNKCON12`: Pass pending human: black circular conspicuous-tank ring semantics are restored. No final approval implied.

## Failed Symbols

- `RFNERY01`: Redraw RFNERY01 as the brown circular refinery glyph matching the S-101/OpenCPN witness, including the enclosing circle and refinery detail.
- `RFNERY11`: Redraw RFNERY11 as the black circular conspicuous-refinery glyph matching the S-101/OpenCPN witness, including the enclosing circle.
- `SCALEB10`: Redraw SCALEB10 as the thin alternating grey/orange vertical one-mile scale pattern from the S-101/OpenCPN witness; remove black/white blocks, side ticks, and the text label.
- `SCALEB11`: Redraw SCALEB11 as the thin alternating black/grey vertical latitude-scale segment pattern from the S-101/OpenCPN witness; remove the block ladder, side ticks, and text label.
- `SILBUI01`: Replace the large cylinder with the small brown silo point/circle mark matching the S-101/OpenCPN witness.
- `SILBUI11`: Replace the large cylinder with the small black conspicuous silo point/circle mark matching the S-101/OpenCPN witness.
- `SSENTR01`: Redraw SSENTR01 as the port-entry signal-station board glyph matching the OpenCPN witness, not a generic PE text sign.
- `SSLOCK01`: Redraw SSLOCK01 as the lock signal-station board glyph matching the OpenCPN witness, preserving the lock/two-light detail instead of an LK label.
- `SSWARS01`: Redraw SSWARS01 as the triangular wahrschau signal-station board glyph matching the OpenCPN witness; do not substitute a WS text sign.
- `TMBYRD01`: Redraw TMBYRD01 as the open brown timber-yard hash/grid with the reference two-horizontal/two-vertical stroke structure and proportions.
- `TNKFRM01`: Redraw TNKFRM01 with the brown circular enclosure and the reference four-dot tank-farm cluster pattern; remove the extra center dot.
- `TNKFRM11`: Redraw TNKFRM11 with the black circular enclosure and the reference four-dot tank-farm cluster pattern; remove the extra center dot.

## Evidence Notes

- Actual repaired SVGs were read from pipeline/iconforge/assets/svg/owned_repair_batch45/.
- Before SVG paths are recorded from the batch metadata; in this detached copy they currently resolve to the same repaired canonical SVGs for this slice, so the judge relied on the prior failed judge observations for before-state semantics.
- Candidate day/dusk/night render paths are listed by the batch metadata under pipeline/iconforge/out/standard_repair_batch37/renders/, but those generated PNGs are not present in the tracked detached checkout.
- Provider references used include each row semantic_brief, standard_source_table provider coverage, prior failed judge metadata, available S-101 exact SVG witnesses, and OpenCPN reference metadata. No Aqua Map provider references were listed for these selected rows in the source table snapshot.
- Passes remain judge_pass_pending_final_approval only and grant zero final approvals.
