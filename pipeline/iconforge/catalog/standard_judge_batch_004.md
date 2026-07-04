# standard_judge_batch_004

Result: **30 pass, 20 fail, 0 final-approved**

## Fail List
- **BCNTOW90** — Candidate renders black tower, but OpenCPN/S-52 reference and COLOUR8 indicate a yellow/brown tower body. Required: Re-render as beacon tower with the BCNTOW90 yellow/brown body color, not black, preserving compact tower silhouette and black outline.
- **BLKADJ01** — Candidate is a black diamond with a white dot; reference is a square brightness/contrast control swatch. Required: Replace diamond with square control swatch: black outer square/frame with dark inner square as in S-52/S-101 BLKADJ01.
- **BORDER01** — Candidate is a magenta diamond/circle marker; reference is a thin diagonal red/white border symbol. Required: Replace with a thin diagonal red/white bordered line/strip matching BORDER01; no diamond, circle, or point-marker body.
- **BOYBAR01** — Candidate is a colored barrel with red/blue bands; reference is black paper-chart barrel outline/generic barrel. Required: Re-render as generic black/paper-chart barrel buoy silhouette/outline. Remove invented red/blue bands.
- **BOYCAN01** — Candidate is an upright filled black can; reference is a small paper-chart can outline/shape. Required: Use the BOYCAN01 paper-chart can shape/outline, not a filled full-chart upright can.
- **BOYCAN62** — Candidate invents green/blue bands for a generic can buoy; reference is uncolored/generic can. Required: Render generic can with neutral/black outline and no invented green/blue color bands.
- **BOYCAN72** — Candidate has red over green only; metadata/reference require lateral r-g-r three-band can. Required: Render three horizontal bands red/green/red in correct order on can body.
- **BOYCAN73** — Candidate has green over red only; metadata/reference require lateral g-r-g three-band can. Required: Render three horizontal bands green/red/green in correct order on can body.
- **BOYCAN74** — Candidate has red over white only; metadata/reference require lateral r-w-r three-band can. Required: Render three horizontal bands red/white/red in correct order on can body.
- **BOYCAN76** — Candidate shows black over red but lacks the lower black band for isolated danger b-r-b. Required: Render isolated-danger can as black/red/black with all three bands visible.
- **BOYCAN77** — Candidate has white over orange only; reference/metadata indicate white/orange/white pattern. Required: Render white/orange/white three-band can; do not collapse to two bands.
- **BOYCAN78** — Candidate has white over orange only; reference/metadata indicate white/orange/white pattern. Required: Render white/orange/white three-band can; do not collapse to two bands.
- **BOYCAN79** — Candidate does not closely match the available reference packet. Required: Repair against OpenCPN/S-52 spine and available S-101/AquaMap examples, then rerun judge.
- **BOYCAN81** — Candidate has orange/white only for white/orange pattern and misses the full repeated band cue. Required: Render the white/orange/white lateral can pattern indicated by S-52 metadata/reference.
- **BOYCAN82** — Candidate has red/white only; metadata/reference require red/white/red lateral can. Required: Render three horizontal bands red/white/red in correct order.
- **BOYCAN83** — Candidate has red/white only; metadata/reference require red/white/red lateral can. Required: Render three horizontal bands red/white/red in correct order.
- **BOYCON01** — Candidate invents red and blue fill bands on a generic/paper-chart conical buoy. Required: Render generic BOYCON01 conical buoy as the S-52/S-101 paper/full-chart reference shape without invented red/blue bands.
- **BOYCON63** — Candidate shows black/red but lacks lower black band for isolated-danger black-red-black conical buoy. Required: Render conical buoy with black/red/black three-band sequence.
- **BOYCON66** — Candidate has red over green only; metadata/reference require lateral r-g-r conical buoy. Required: Render three horizontal bands red/green/red in correct order on conical body.
- **BOYCON67** — Candidate has green over red only; metadata/reference require lateral g-r-g conical buoy. Required: Render three horizontal bands green/red/green in correct order on conical body.

## Top Repair Themes
- missing third band in repeated color patterns such as r-g-r, g-r-g, r-w-r, w-o-w, and b-r-b
- invented colors or bands on generic/paper-chart buoy symbols
- wrong utility/border symbol family for BLKADJ01 and BORDER01
- one BCNTOW color mismatch: BCNTOW90 renders black instead of yellow/brown

## Notes
Judged from normalized source table packet, OpenCPN rendered refs, local AquaMap refs where mapped, S-57/S-52 metadata, and Helm candidate PNG/SVG. No verdict is final-approved.
