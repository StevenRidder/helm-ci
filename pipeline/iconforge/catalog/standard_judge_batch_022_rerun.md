# Standard judge batch 022 rerun

- Project: `vulkan`
- Task: `FORGE-18`
- Agent: `codex/FORGE-18-visual-rerun-batch22-local`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch22.json`
- Selection: `owned_repair_batch22.symbols[].qa.visual_parity == repaired_pending_judge_rerun` from batch22 only
- Chart 1 gate: hard; no row is final-approved, automated passes are `pass-pending-human` only

- Judged: 24
- Pass-pending-human: 3
- Fail: 21
- Final approved: 0

| Symbol | Verdict | Confidence | Observed | Required change | Reason codes |
|---|---:|---:|---|---|---|
| BUIREL01 | fail | 0.90 | Candidate is a church/building outline with a Latin cross and boxed doorway; the OpenCPN/S-101 witness is the compact four-lobed Christian religious-building mark. | Redraw as the compact brown Christian religious-building witness shape from S-101/OpenCPN; remove the house outline and doorway. | wrong_shape, invented_building_outline, reference_mismatch |
| BUIREL05 | pass-pending-human | 0.82 | Candidate has the crescent above a vertical stem with base/ring cue, matching the mosque/minaret witness family closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| BUIREL13 | fail | 0.90 | Candidate is a black church/building outline with a Latin cross and boxed doorway; the conspicuous Christian witness is the compact four-lobed religious-building mark. | Redraw as the compact black conspicuous Christian religious-building witness shape from S-101/OpenCPN; remove the house outline and doorway. | wrong_shape, invented_building_outline, reference_mismatch |
| BUIREL15 | pass-pending-human | 0.82 | Candidate has the black crescent above a vertical stem with base/ring cue, matching the conspicuous mosque/minaret witness family closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| GATCON03 | fail | 0.91 | Candidate is a black rectangular lock-gate frame with a chevron/leaf; the witness is a magenta circular navigable lock-gate mark with internal gate geometry. | Redraw GATCON03 to the magenta circular navigable lock-gate witness; do not use a generic black gate frame. | wrong_colour_family, wrong_symbol_body, reference_mismatch |
| GATCON04 | fail | 0.91 | Candidate is a black crossed rectangular gate frame; the witness is a magenta circular non-navigable lock-gate mark with central cross geometry. | Redraw GATCON04 to the magenta circular non-navigable lock-gate witness; remove the generic black gate frame. | wrong_colour_family, wrong_symbol_body, reference_mismatch |
| HULKES01 | fail | 0.86 | Candidate is an outline boat/hull with a mast-like A frame; the witness is a compact filled hulk silhouette without the invented mast frame. | Redraw as the compact HULKES01 hulk silhouette; remove the mast/A-frame and outline-boat substitution. | wrong_shape, invented_mast_detail, reference_mismatch |
| INFARE51 | pass-pending-human | 0.84 | Candidate is a magenta boxed information/restriction-area glyph with central i, matching the reference box-and-i family closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| INFORM01 | fail | 0.88 | Candidate has the leader line and origin circle, but the information mark is a large circle; the witness uses a small square information box at the leader end. | Redraw INFORM01 with the square boxed information marker at the leader end; keep the leader line and origin circle. | wrong_marker_shape, wrong_scale, reference_mismatch |
| ITZARE51 | fail | 0.86 | Candidate shows IT text with an added dashed underline; the witness is the IT text mark without the dashed baseline. | Remove the dashed underline and align the IT letter proportions/stroke with the reference witness. | invented_line_detail, wrong_text_style, reference_mismatch |
| LNDARE01 | fail | 0.90 | Candidate is a large concentric-circle target with centre dot; the witness is a small plain land point/dot. | Redraw LNDARE01 as the small point/dot witness; remove the outer target ring. | invented_ring, wrong_symbol_body, reference_mismatch |
| LOCMAG01 | fail | 0.91 | Candidate is a magenta A-shaped anomaly mark; the witness is a narrow magnetic-anomaly wedge/line glyph. | Redraw LOCMAG01 as the reference wedge/line glyph; remove the A-letter substitution. | wrong_shape, wrong_symbol_semantics, reference_mismatch |
| LOCMAG51 | fail | 0.91 | Candidate is a magenta A-shaped anomaly mark with dashed underline; the witness is a narrow magnetic-anomaly wedge/line glyph without the A letter. | Redraw LOCMAG51 as the reference wedge/line glyph; remove the A-letter body and dashed underline. | wrong_shape, invented_line_detail, reference_mismatch |
| LOWACC01 | fail | 0.84 | Candidate has the question mark and diagonal line, but adds a prominent ring/circle at the upper line end that is not present in the reference witness. | Remove the invented endpoint ring and align LOWACC01 to the question-mark-plus-diagonal-line witness. | invented_endpoint_ring, wrong_internal_detail, reference_mismatch |
| MAGVAR01 | fail | 0.92 | Candidate is a magenta M/A-like line monogram; the witness is a filled magnetic-variation wedge/flag on a vertical line. | Redraw MAGVAR01 as the filled wedge/flag and vertical line witness; remove the M/A monogram. | wrong_shape, wrong_symbol_semantics, reference_mismatch |
| MAGVAR51 | fail | 0.92 | Candidate is a magenta M/A-like line monogram with dashed underline; the witness is a filled magnetic-variation wedge/flag on a vertical line. | Redraw MAGVAR51 as the filled wedge/flag and vertical line witness; remove the M/A monogram and dashed underline. | wrong_shape, invented_line_detail, reference_mismatch |
| MARCUL02 | fail | 0.86 | Candidate is a fish/net motif over a wave line; the witness is a rectangular marine-farm/net frame with fish/net line motif. | Redraw MARCUL02 as the rectangular marine-farm fish/net frame; remove the wave baseline. | wrong_enclosure_shape, invented_wave_line, reference_mismatch |
| MONUMT02 | fail | 0.82 | Candidate is a brown tapered monument with diagonal bands, but it omits the reference base/ring detail under the monument. | Add the reference base/ring cue and align MONUMT02 proportions to the monument witness before visual approval. | missing_base_detail, wrong_proportions, reference_mismatch |
| MONUMT12 | fail | 0.82 | Candidate is a black tapered monument with diagonal bands, but it omits the reference base/ring detail under the conspicuous monument. | Add the reference base/ring cue and align MONUMT12 proportions to the monument witness before visual approval. | missing_base_detail, wrong_proportions, reference_mismatch |
| MORFAC03 | fail | 0.91 | Candidate is a ladder/pile frame with a top ring; the witness is a compact square mooring-dolphin cue. | Redraw MORFAC03 to the compact mooring-dolphin witness; remove the ladder frame and top ring. | wrong_shape, invented_ring_detail, reference_mismatch |
| MORFAC04 | fail | 0.86 | Candidate is an offset pile frame with a top ring and diagonal bar; the witness is a narrow deviation mooring-dolphin structure without the ring. | Redraw MORFAC04 to the narrow deviation mooring-dolphin witness; remove the top ring and oversized frame. | wrong_shape, invented_ring_detail, reference_mismatch |
| MSTCON04 | fail | 0.91 | Candidate is an arrow-like mast with an open base ring; the witness is a narrow mast/needle tower with base crossbar/detail. | Redraw MSTCON04 as the narrow mast/needle tower witness; remove the arrowhead substitution. | wrong_shape, wrong_symbol_semantics, reference_mismatch |
| MSTCON14 | fail | 0.91 | Candidate is a black arrow-like mast with an open base ring; the witness is a narrow conspicuous mast/needle tower with base detail. | Redraw MSTCON14 as the narrow mast/needle tower witness; remove the arrowhead substitution. | wrong_shape, wrong_symbol_semantics, reference_mismatch |
| NORTHAR1 | fail | 0.84 | Candidate is a simple outline arrow with N above the head; the witness has a filled orange arrowhead and the N placed across/beside the stem. | Align NORTHAR1 to the filled arrowhead and reference N placement; do not leave the N floating above the arrowhead. | wrong_n_placement, wrong_arrowhead_style, reference_mismatch |

## Pass-pending-human

BUIREL05, BUIREL15, INFARE51

## Fail

BUIREL01, BUIREL13, GATCON03, GATCON04, HULKES01, INFORM01, ITZARE51, LNDARE01, LOCMAG01, LOCMAG51, LOWACC01, MAGVAR01, MAGVAR51, MARCUL02, MONUMT02, MONUMT12, MORFAC03, MORFAC04, MSTCON04, MSTCON14, NORTHAR1
