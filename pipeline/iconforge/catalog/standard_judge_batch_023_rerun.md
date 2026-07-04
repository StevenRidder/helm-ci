# Standard judge batch 023 rerun

- Project: `vulkan`
- Task: `FORGE-18`
- Agent: `codex/FORGE-18-visual-rerun-batch23-local`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch23.json`
- Selection: `owned_repair_batch23.symbols[].qa.visual_parity == repaired_pending_judge_rerun` from batch23 only
- Chart 1 gate: hard; no row is final-approved, automated passes are `pass-pending-human` only

- Judged: 24
- Pass-pending-human: 16
- Fail: 8
- Final approved: 0

| Symbol | Verdict | Confidence | Observed | Required change | Reason codes |
|---|---:|---:|---|---|---|
| BRIDGE01 | pass-pending-human | 0.86 | Candidate is a clean magenta concentric opening-bridge ring with no slash or centre clutter, matching the S-101/OpenCPN ring witness closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| CRANES01 | pass-pending-human | 0.80 | Candidate reads as the brown quay/gantry crane family with support legs, top beam, trolley/hook cue, and base, matching the reference class closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| CURDEF01 | pass-pending-human | 0.84 | Candidate preserves the gray current arrow and unknown-direction question marks, matching the reference family closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| DWRTPT51 | pass-pending-human | 0.88 | Candidate is the magenta DW text cue with the invented dashed underline removed, matching the text witness closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| ESSARE01 | pass-pending-human | 0.78 | Candidate is the magenta ESSA text cue with the invented dashed underline removed, matching the S-101 ESSA text witness closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| FAIRWY51 | fail | 0.88 | Candidate now has the correct hollow one-way arrow silhouette, but it renders black while the S-101/OpenCPN witness is the CHGRD/gray fairway stroke family. | Keep the hollow one-way arrow geometry, but move FAIRWY51 from black to the CHGRD/gray reference stroke colour. | wrong_colour_family, reference_mismatch |
| FAIRWY52 | fail | 0.88 | Candidate now has the correct hollow two-way arrow silhouette, but it renders black while the S-101/OpenCPN witness is the CHGRD/gray fairway stroke family. | Keep the hollow two-way arrow geometry, but move FAIRWY52 from black to the CHGRD/gray reference stroke colour. | wrong_colour_family, reference_mismatch |
| FLDSTR01 | fail | 0.82 | Candidate is gray and keeps the flood-stream arrow, but the spring-rate cue is a horizontal crossbar rather than the S-101/OpenCPN slanted tick geometry on the arrow stem. | Replace the horizontal rate crossbar with the S-101/OpenCPN spring-rate tick geometry while preserving the gray flood-stream arrow. | wrong_internal_detail, wrong_rate_marker_geometry, reference_mismatch |
| FLGSTF01 | pass-pending-human | 0.82 | Candidate has the brown flagstaff pole, square flag, and base/foot cue, matching the reference family closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| FLTHAZ02 | pass-pending-human | 0.86 | Candidate has the magenta circled X and lower hazard contour from the S-101 FLTHAZ02 witness; no OpenCPN raster witness is present locally for this row. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| FOGSIG01 | pass-pending-human | 0.87 | Candidate has the three magenta fog-signal arcs and removes the bell/arch placeholder, matching the S-101/OpenCPN arc family closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| FORSTC01 | pass-pending-human | 0.86 | Candidate is the plain brown fortified-structure square outline without battlements, matching the reference family closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| FORSTC11 | pass-pending-human | 0.86 | Candidate is the plain black conspicuous fortified-structure square outline without battlements, matching the reference family closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| FRYARE51 | fail | 0.90 | Candidate has the ferry-on-dashed-route geometry, but it renders black; the S-101/OpenCPN ferry-area witness is magenta/CHMGF. | Keep the ferry-on-dashed-route geometry but change FRYARE51 from black to the magenta CHMGF/reference colour family. | wrong_colour_family, reference_mismatch |
| FRYARE52 | pass-pending-human | 0.80 | Candidate has the black cable-ferry line and ferry outline with wake arcs removed, matching the cable-ferry witness closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| FSHFAC02 | fail | 0.90 | Candidate is a brown rectangular stake panel with extra vertical lattice lines; the S-101/OpenCPN witness is a gray lower rectangle with one diagonal stake/line. | Redraw FSHFAC02 in the gray CHGRD/reference colour and remove the extra vertical lattice lines, keeping the simple rectangle plus one diagonal stake/line. | wrong_colour_family, wrong_pattern, extra_lattice_detail, reference_mismatch |
| FSHFAC03 | fail | 0.87 | Candidate has the horizontal fishing-stakes family, but it renders as tall brown posts; the S-101/OpenCPN pattern is a low gray row of short stakes. | Move FSHFAC03 to the gray CHGRD/reference colour family and compress the posts to the low S-101/OpenCPN fishing-stakes proportions. | wrong_colour_family, wrong_proportions, reference_mismatch |
| FSHHAV01 | pass-pending-human | 0.86 | Candidate preserves the fish silhouette inside a dotted oval fish-haven enclosure, matching the reference family closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| HRBFAC09 | fail | 0.91 | Candidate is a black circled fish with an added F letter; the S-101/OpenCPN fishing-harbour witness is the magenta fish/arc service mark without the black circle/F substitution. | Redraw HRBFAC09 in magenta using the S-101/OpenCPN fish/arc service mark; remove the black enclosing circle and F text. | wrong_colour_family, invented_text, wrong_enclosure_shape, reference_mismatch |
| OBSTRN03 | pass-pending-human | 0.84 | Candidate has a filled/tinted obstruction circle and dotted perimeter, matching the S-101/OpenCPN obstruction witness closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| OFSPLF01 | pass-pending-human | 0.90 | Candidate is the square offshore-platform glyph with central dot, matching the S-101/OpenCPN witness closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| PILBOP02 | pass-pending-human | 0.88 | Candidate is the magenta circle/diamond pilot-boarding witness without P text or stem, matching the reference family closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| PILPNT02 | fail | 0.92 | Candidate is a tapered bollard/post silhouette, but the S-101/OpenCPN PILPNT02 witness is a small filled black point/circle. | Redraw PILPNT02 as the small filled black point/circle witness; remove the tapered bollard/post body. | wrong_shape, wrong_scale, reference_mismatch |
| POSGEN01 | pass-pending-human | 0.90 | Candidate keeps the position ring/dot geometry in the brown reference colour family, matching the S-101/OpenCPN witness closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |

## Pass-pending-human

BRIDGE01, CRANES01, CURDEF01, DWRTPT51, ESSARE01, FLGSTF01, FLTHAZ02, FOGSIG01, FORSTC01, FORSTC11, FRYARE52, FSHHAV01, OBSTRN03, OFSPLF01, PILBOP02, POSGEN01

## Fail

FAIRWY51, FAIRWY52, FLDSTR01, FRYARE51, FSHFAC02, FSHFAC03, HRBFAC09, PILPNT02
