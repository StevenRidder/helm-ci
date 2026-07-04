# Standard judge batch 021 rerun

- Project: `vulkan`
- Task: `FORGE-18`
- Agent: `codex/FORGE-18-visual-rerun-batch21-local`
- Source batch: `pipeline/iconforge/catalog/owned_repair_batch21.json`
- Selection: `helm_candidate.candidate_status == repaired_pending_judge_rerun` from batch21 only
- Chart 1 gate: hard; no row is final-approved, automated passes are `pass-pending-human` only

- Judged: 24
- Pass-pending-human: 3
- Fail: 21
- Final approved: 0

| Symbol | Verdict | Confidence | Observed | Required change | Reason codes |
|---|---:|---:|---|---|---|
| BRIDGE01 | fail | 0.88 | Candidate remains a magenta double ring with a diagonal slash through the centre. | Remove the diagonal slash and any centre clutter; render BRIDGE01 as the clean magenta concentric opening-bridge ring. | invented_detail, wrong_internal_detail, reference_mismatch |
| BUNSTA02 | fail | 0.86 | Candidate is a cylindrical tank/barrel with a blue horizontal band. | Redraw as the water bunker-station bucket/service witness; remove the cylindrical barrel body. | wrong_shape, wrong_symbol_semantics, reference_mismatch |
| BUNSTA03 | pass-pending-human | 0.82 | Candidate is a black outlined isometric cube/box with visible face divisions. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| CRANES01 | fail | 0.90 | Candidate is a single boom crane with a small hanging load. | Redraw CRANES01 as the gantry/quay crane silhouette with vertical support legs and top beam; do not use a generic single-boom crane. | wrong_crane_type, wrong_shape, reference_mismatch |
| CURDEF01 | fail | 0.84 | Candidate has orange up/down arrows with question marks. | Preserve the central current arrow and question marks but move to the reference grey/slate colour family and closer arrow barb proportions. | wrong_colour_family, reference_mismatch |
| DISMAR03 | fail | 0.90 | Candidate is a black post/box with DM text. | Resolve DISMAR03 against the intended strongest reference, then redraw to that witness instead of the black DM post. | conflicting_reference_witness, wrong_shape, reference_mismatch |
| DISMAR04 | fail | 0.90 | Candidate is a black target/crosshair with DP text. | Resolve DISMAR04 against the intended strongest reference, then redraw to that witness instead of the black DP target. | conflicting_reference_witness, wrong_shape, reference_mismatch |
| DWRTPT51 | fail | 0.86 | Candidate shows magenta DW text with an added dashed underline. | Remove the dashed underline and keep the DW text cue aligned to the reference proportions/colour. | invented_detail, wrong_line_pattern, reference_mismatch |
| ESSARE01 | fail | 0.88 | Candidate shows ESSA text with an added dashed underline. | Remove the dashed underline and resolve whether the row should use ESSA text or the boundary-line witness; do not combine invented text underline detail. | invented_detail, conflicting_reference_witness, reference_mismatch |
| FAIRWY51 | fail | 0.84 | Candidate is a solid black one-way up arrow. | Redraw as the outlined one-way fairway arrow with hollow body/head and reference stroke colour. | wrong_fill_style, wrong_shape, reference_mismatch |
| FAIRWY52 | fail | 0.84 | Candidate is a solid black two-way up/down arrow. | Redraw as the outlined two-way fairway arrow with hollow body/head and reference stroke colour. | wrong_fill_style, wrong_shape, reference_mismatch |
| FLDSTR01 | fail | 0.86 | Candidate is orange with a vertical shaft, arrowhead, and multiple horizontal crossbars. | Redraw FLDSTR01 to the reference flood-stream arrow geometry and colour family; remove extra stacked crossbars. | wrong_internal_detail, wrong_colour_family, reference_mismatch |
| FLGSTF01 | fail | 0.82 | Candidate has a waving flag and a circular ring at the base. | Replace the circular base with the reference flagstaff base/foot structure and square flag proportions. | wrong_base_detail, wrong_shape, reference_mismatch |
| FLTHAZ02 | fail | 0.93 | Candidate is a magenta circle with an asterisk/star. | Redraw as the FLTHAZ02 circled X and lower hazard contour; remove the asterisk/star symbol. | wrong_symbol_class, wrong_internal_detail, reference_mismatch |
| FOGSIG01 | fail | 0.92 | Candidate is a small arch/bell-like curve with a dash under it. | Redraw as three fog-signal sound arcs; remove the arch-with-dash/bell placeholder. | wrong_shape, wrong_symbol_semantics, reference_mismatch |
| FORSTC01 | fail | 0.82 | Candidate is a brown square fort outline with two battlements on top. | Remove battlements and render the plain fortified-structure square outline matching the witness. | invented_detail, wrong_shape, reference_mismatch |
| FORSTC11 | fail | 0.82 | Candidate is a black square fort outline with two battlements on top. | Remove battlements and render the conspicuous fortified-structure as the bold plain square outline. | invented_detail, wrong_shape, reference_mismatch |
| FOULGND1 | pass-pending-human | 0.86 | Candidate is a black hash/grid foul-ground mark with the same general crossed-line structure as the witnesses. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| FRYARE51 | fail | 0.90 | Candidate shows a ferry/boat icon over curved wake lines. | Redraw as the ferry-area dashed-line witness with the ferry outline on the line; remove wake arcs. | missing_route_line, wrong_line_pattern, reference_mismatch |
| FRYARE52 | fail | 0.90 | Candidate shows a ferry/boat icon with dashed wake-like marks. | Redraw as the cable-ferry horizontal line witness with ferry outline; remove wake arcs and extra clustered dashes. | wrong_line_pattern, wrong_shape, reference_mismatch |
| FSHFAC02 | fail | 0.92 | Candidate is a gold slanted grid or fence panel. | Redraw fishing stakes as the rectangular stake panel with one diagonal stake/line; remove lattice/grid cells. | wrong_pattern, wrong_shape, reference_mismatch |
| FSHFAC03 | fail | 0.84 | Candidate is a compact gold square picket/grid. | Stretch/redraw to the horizontal fishing-stakes pattern: baseline with several vertical posts, not a square grid. | wrong_aspect_ratio, wrong_pattern, reference_mismatch |
| FSHGRD01 | pass-pending-human | 0.84 | Candidate is a fish outline with internal dot/detail and tail, matching the fishing-ground witness silhouette closely enough for automated rerun. | No repair required for this automated visual rerun; keep pending human/chart parity approval and do not mark final-approved. |  |
| FSHHAV01 | fail | 0.90 | Candidate is a fish inside a dashed rectangular enclosure. | Replace the dashed rectangle with the dotted oval fish-haven enclosure while preserving the fish silhouette. | wrong_enclosure_shape, wrong_line_pattern, reference_mismatch |

## Pass-pending-human

BUNSTA03, FOULGND1, FSHGRD01

## Fail

BRIDGE01, BUNSTA02, CRANES01, CURDEF01, DISMAR03, DISMAR04, DWRTPT51, ESSARE01, FAIRWY51, FAIRWY52, FLDSTR01, FLGSTF01, FLTHAZ02, FOGSIG01, FORSTC01, FORSTC11, FRYARE51, FRYARE52, FSHFAC02, FSHFAC03, FSHHAV01
