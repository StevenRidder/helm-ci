# Standard Judge Batch 083/084 Rerun

- Project: `vulkan`
- Task: `FORGE-15`
- Agent: `codex/FORGE-15-judge-loop-current`
- Source batches: `owned_repair_batch83`, `owned_repair_batch84`
- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.

## Summary

| Result | Count |
| --- | ---: |
| Selected | 21 |
| Pass pending human | 17 |
| Fail | 4 |
| Final approved | 0 |

## Verdicts

| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |
| --- | --- | ---: | --- | --- | --- |
| `BCNCON81` | Fail | 0.72 | Refine BCNCON81 against a true one-symbol crop or explicit SymbolSpec: preserve the required blue/red/white/blue pattern, but do not promote a conical substitute until the exact crop confirms body, stem, and any text/topmark cue. | exact_crop_ambiguous, unverified_symbol_semantics, unsafe_symbol_confusion | FAIL. The repaired candidate is a blue/red/white/blue conical buoy body, but the available exact crop shows multiple local symbol components and does not validate that this simplified cone is the exact BCNCON81 beacon symbol. |
| `BCNGEN68` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: beacon/daymark body preserves black-over-yellow semantics from the OpenCPN/Chart 1 witness. No final approval is granted. |
| `BCNGEN69` | Pass pending human | 0.88 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: beacon/daymark body preserves yellow-over-black semantics from the OpenCPN/Chart 1 witness. No final approval is granted. |
| `BCNGEN79` | Pass pending human | 0.87 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: solid orange beacon/daymark body matches the source-table colour requirement and witness family. No final approval is granted. |
| `BCNGEN80` | Pass pending human | 0.87 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: solid black beacon/daymark body matches the source-table colour requirement and witness family. No final approval is granted. |
| `BCNSPR62` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: yellow spar/stake beacon body matches the required vertical spar family. No final approval is granted. |
| `BOYISD12` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: two red isolated-danger dots match the simplified witness and required danger semantics. No final approval is granted. |
| `BOYMOR01` | Pass pending human | 0.84 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: mooring/spherical buoy cue and black outline match the provider witnesses closely enough for human review. No final approval is granted. |
| `BOYMOR03` | Pass pending human | 0.82 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: can/cylindrical mooring silhouette matches the OpenCPN/Chart 1 witness; colour is treated as reference-defined because the S-57 row has no explicit COLOUR condition. No final approval is granted. |
| `BOYMOR11` | Pass pending human | 0.82 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: black mooring-installation silhouette matches the simplified witness family closely enough for human review. No final approval is granted. |
| `BOYMOR31` | Pass pending human | 0.84 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: white can/cylindrical mooring silhouette matches the witness and explicit white colour condition. No final approval is granted. |
| `BOYSAW12` | Pass pending human | 0.90 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: red safe-water simplified target mark matches the provider witnesses. No final approval is granted. |
| `BOYSPP11` | Pass pending human | 0.84 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: yellow special-purpose simplified mark matches the OpenCPN/Chart 1 witness better than a generic diamond. No final approval is granted. |
| `BOYSPP15` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: yellow conical/TSS starboard simplified triangle matches the witness family. No final approval is granted. |
| `BOYSPP25` | Pass pending human | 0.86 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: yellow can/TSS port simplified slanted can mark matches the witness family. No final approval is granted. |
| `TOPSHP09;TE('%s'` | Pass pending human | 0.80 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: upright triangle silhouette matches the exact crop and restores red/red/green source-table semantics with a text-bearing cue. No final approval is granted. |
| `TOPSHP15;TE('%s'` | Pass pending human | 0.80 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: upright triangle silhouette matches the exact crop and restores red/red/yellow source-table semantics with a text-bearing cue. No final approval is granted. |
| `TOPSHP33` | Pass pending human | 0.91 | No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact. | - | Pass pending human: slanted hollow square topmark matches the exact Chart 1 crop silhouette. No final approval is granted. |
| `TOWERS74|;TX(OBJNAM` | Fail | 0.86 | Create or attach a true TOWERS74 one-symbol crop/render witness, then rerun the judge; keep the tower silhouette direction, but do not promote from broad table evidence. | source_crop_not_symbol_tight, insufficient_visual_evidence, manual_review_required | FAIL. The candidate is a reasonable thin tower pictogram with orange crossbars, but the available Chart 1 evidence is a broad page/table crop, not a one-symbol source crop for TOWERS74. |
| `VEHTRF01` | Fail | 0.88 | Attach a true VEHTRF01 one-symbol reference crop/render and redraw or confirm the vehicle-traffic geometry from that witness before promotion. | source_crop_not_symbol_tight, insufficient_visual_evidence, reference_mismatch_unproven | FAIL. The candidate replaces the diamond placeholder with a traffic-signal pictogram, but the row lacks a tight VEHTRF01 reference crop and has only broad page evidence. |
| `boyspp50` | Fail | 0.84 | Generate or attach a tight boyspp50 OpenCPN/Chart 1 witness, then redraw the yellow buoy-family symbol to that exact body/topmark before promotion. | source_crop_not_symbol_tight, insufficient_visual_evidence, buoy_body_unverified | FAIL. The candidate is a yellow buoy-family pictogram instead of the old diamond, but the only visible Chart 1 evidence is a broad table crop and does not prove the correct boyspp50 body/topmark. |

## Failed Symbols

- `BCNCON81`: Refine BCNCON81 against a true one-symbol crop or explicit SymbolSpec: preserve the required blue/red/white/blue pattern, but do not promote a conical substitute until the exact crop confirms body, stem, and any text/topmark cue.
- `TOWERS74|;TX(OBJNAM`: Create or attach a true TOWERS74 one-symbol crop/render witness, then rerun the judge; keep the tower silhouette direction, but do not promote from broad table evidence.
- `VEHTRF01`: Attach a true VEHTRF01 one-symbol reference crop/render and redraw or confirm the vehicle-traffic geometry from that witness before promotion.
- `boyspp50`: Generate or attach a tight boyspp50 OpenCPN/Chart 1 witness, then redraw the yellow buoy-family symbol to that exact body/topmark before promotion.

## Evidence Notes

- Judged only current repaired rows from owned_repair_batch83 and owned_repair_batch84.
- Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.
- Rows backed only by broad page/table crops are failed back to the repair/evidence queue rather than promoted.
- Verdicts used standard_source_table semantic_brief, S-57 conditions, current generated SVGs/renders, and available Chart 1/OpenCPN/provider witnesses.
