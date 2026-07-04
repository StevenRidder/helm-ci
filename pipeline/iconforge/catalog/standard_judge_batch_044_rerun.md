# Standard Judge Batch 044 Rerun

- Project: `vulkan`
- Task: `FORGE-14`
- Agent: `codex/FORGE-14-batch44-judge`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch44.json`
- Source table: `pipeline/iconforge/catalog/standard_source_table.json`
- Scope: `ROLROL01, TERMNL01, TERMNL02, TERMNL03, TERMNL04, TERMNL05, TERMNL06, TERMNL07, TERMNL08, TERMNL09, TERMNL10, TERMNL11, TERMNL12, TERMNL13`

Pass means `judge_pass_pending_final_approval` only. This rerun grants zero final approvals.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 14 |
| Pass pending human | 9 |
| Fail | 5 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `ROLROL01` | Pass pending human | 0.93 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: RoRo text semantics and black colour family are restored. Typography/scale differ from the provider witnesses, so this is not a final approval. |
| `TERMNL01` | Fail | 0.90 | Replace the generic person/cross glyph with the TERMNL01 passenger-terminal circular vessel/passenger detail matching the provider witness. | wrong_glyph_semantics, missing_terminal_detail, reference_mismatch | Fail: the terminal circle is restored, but the inner glyph changes the passenger/ferry terminal witness into a generic person marker. Required passenger/ferry terminal detail is still missing. |
| `TERMNL02` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: the diamond is gone and the circular ferry/boat detail matches the required ferry-terminal family. Stroke/fill simplification remains for human crop review. |
| `TERMNL03` | Fail | 0.95 | Replace the red-only bars with the TERMNL03 circular multicolour container-stack glyph matching the provider witness colour/detail family. | wrong_colour_family, missing_container_detail, reference_mismatch | Fail: circular terminal form is restored, but the provider witness is a multicolour container stack. The candidate drops the green/grey/multicolour container detail and changes the reference family. |
| `TERMNL04` | Fail | 0.91 | Replace the generic triangle with the TERMNL04 circular bulk/material terminal glyph preserving the provider witness black/white pile/handling detail. | wrong_shape, missing_terminal_detail, reference_mismatch | Fail: the candidate keeps a circle and black/white family, but the inner mark is a generic triangle rather than the bulk/material handling witness shape. |
| `TERMNL05` | Pass pending human | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: circular terminal form, oil text semantics, and black colour family are restored. Case/style differences are non-final human-review details. |
| `TERMNL06` | Pass pending human | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: circular terminal form, fuel label semantics, and black colour family are restored. No final approval implied. |
| `TERMNL07` | Fail | 0.93 | Replace the CH label with the TERMNL07 circular chemical-terminal label matching the provider witness text cue. | wrong_text_glyph, missing_text_label, reference_mismatch | Fail: the provider witness reads as the chemical label Che; shortening it to CH changes the text/glyph semantics for this terminal row. |
| `TERMNL08` | Pass pending human | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: circular terminal form and liquid-goods label semantics are restored in the required black family. No final approval implied. |
| `TERMNL09` | Pass pending human | 0.84 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human, low confidence: the candidate restores the circular explosive-goods terminal family and required red/black cue. The provider witness has richer flame colour/detail, so this remains human/crop review only. |
| `TERMNL10` | Pass pending human | 0.89 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: fish-terminal semantics, circular terminal family, and black colour family are restored. Fill/style differences remain non-final. |
| `TERMNL11` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: vehicle detail and circular terminal family match the required car-transshipment semantics. No final approval implied. |
| `TERMNL12` | Fail | 0.92 | Replace the plain box with the TERMNL12 circular general-cargo terminal glyph preserving the provider witness cargo-handling detail. | wrong_shape, missing_cargo_detail, reference_mismatch | Fail: the plain square is too generic and does not preserve the general-cargo handling/detail witness shown by the reference. |
| `TERMNL13` | Pass pending human | 0.92 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: circular terminal form, RoRo text cue, and black colour family are restored. No final approval implied. |

## Pass Notes

- `ROLROL01`: Pass pending human: RoRo text semantics and black colour family are restored. Typography/scale differ from the provider witnesses, so this is not a final approval.
- `TERMNL02`: Pass pending human: the diamond is gone and the circular ferry/boat detail matches the required ferry-terminal family. Stroke/fill simplification remains for human crop review.
- `TERMNL05`: Pass pending human: circular terminal form, oil text semantics, and black colour family are restored. Case/style differences are non-final human-review details.
- `TERMNL06`: Pass pending human: circular terminal form, fuel label semantics, and black colour family are restored. No final approval implied.
- `TERMNL08`: Pass pending human: circular terminal form and liquid-goods label semantics are restored in the required black family. No final approval implied.
- `TERMNL09`: Pass pending human, low confidence: the candidate restores the circular explosive-goods terminal family and required red/black cue. The provider witness has richer flame colour/detail, so this remains human/crop review only.
- `TERMNL10`: Pass pending human: fish-terminal semantics, circular terminal family, and black colour family are restored. Fill/style differences remain non-final.
- `TERMNL11`: Pass pending human: vehicle detail and circular terminal family match the required car-transshipment semantics. No final approval implied.
- `TERMNL13`: Pass pending human: circular terminal form, RoRo text cue, and black colour family are restored. No final approval implied.

## Failed Symbols

- `TERMNL01`: Replace the generic person/cross glyph with the TERMNL01 passenger-terminal circular vessel/passenger detail matching the provider witness.
- `TERMNL03`: Replace the red-only bars with the TERMNL03 circular multicolour container-stack glyph matching the provider witness colour/detail family.
- `TERMNL04`: Replace the generic triangle with the TERMNL04 circular bulk/material terminal glyph preserving the provider witness black/white pile/handling detail.
- `TERMNL07`: Replace the CH label with the TERMNL07 circular chemical-terminal label matching the provider witness text cue.
- `TERMNL12`: Replace the plain box with the TERMNL12 circular general-cargo terminal glyph preserving the provider witness cargo-handling detail.

## Evidence Notes

- Actual repaired SVGs were read from `pipeline/iconforge/assets/svg/owned_repair_batch44/`.
- Candidate day/dusk/night renders were read from `pipeline/iconforge/out/standard_repair_batch36/renders/` and compared against available provider witnesses.
- Provider references used include each row's `semantic_brief`, prior failed judge metadata, OpenCPN local render references, and S-101 or Chart No.1 references where listed by the row or prior judge.
- `ROLROL01` has an S-101 exact SVG witness; `TERMNL09` through `TERMNL13` include Chart No.1 crop references from the prior judge, but those crop files are broad panel crops and were not treated as final-approval evidence.
- No Aqua Map provider references were listed for these selected rows in the source table snapshot; OpenCPN references were treated as visual witnesses only, not copied artwork.
- Passes remain pass-pending-human only and do not grant final approval.
