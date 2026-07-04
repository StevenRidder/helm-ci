# Standard Judge Batch 002

Status: batch judged; no final approvals granted.

Pass count: 22
Fail count: 28

## Fail List

- `BCNGEN65`: Redraw with four ordered horizontal bands green/white/green/white inside the BCNGEN beacon body; keep black outline/stem but do not collapse to two bands.
- `BCNGEN70`: Render three ordered horizontal bands black/yellow/black; bottom black band must be visible.
- `BCNGEN71`: Render three ordered horizontal bands yellow/black/yellow; bottom yellow band must be visible.
- `BCNGEN76`: Render three ordered horizontal bands black/red/black in the BCNGEN beacon body.
- `BCNISD21`: Redraw as the isolated-danger beacon symbol: two aligned circular danger marks/topmarks, matching S-101/OpenCPN, not a striped generic beacon.
- `BCNLAT15`: Remove green band; render red lateral beacon body with the S-101/OpenCPN black pivot/detail cue if needed.
- `BCNLAT16`: Remove red band; render green lateral beacon body with the S-101/OpenCPN cue.
- `BCNLAT21`: Remove green band and use the compact minor lateral red beacon/stake geometry from S-101/OpenCPN.
- `BCNLAT22`: Remove red band and use compact minor lateral green beacon/stake geometry from S-101/OpenCPN.
- `BCNLAT23`: Render only the ordered red/green lateral cue indicated by the OpenCPN reference and lookup; remove black/blue bands.
- `BCNLAT50`: Redraw as a plain black river stake/pole beacon; remove blue fill and keep stake proportions.
- `BCNLTC01`: Draw the lattice beacon/tower structure in black using thin OpenBridge-style strokes; remove blue band.
- `BCNSAW13`: Redraw from S-101/AquaMap safe-water reference: preserve the safe-water topmark/body cue and correct red/white semantics.
- `BCNSAW21`: Redraw minor safe-water beacon from S-101/OpenCPN, preserving the safe-water cue and not using a solid black general body.
- `BCNSPP13`: Remove black lower band; render yellow special-purpose beacon with the compact S-101/OpenCPN body.
- `BCNSPP21`: Remove black band and use minor yellow special-purpose beacon geometry.
- `BCNSTK02`: Remove blue band; redraw as the black minor stake/pole beacon shown by S-101/OpenCPN.
- `BCNSTK03`: Remove blue band and draw plain black stake/pole geometry.
- `BCNSTK77`: Correct the ordered bands to match the source structure, green-leading with all required alternating green/white bands.
- `BCNSTK79`: Render three ordered horizontal stake bands red/green/red.
- `BCNSTK80`: Render three ordered horizontal stake bands green/red/green.
- `BCNTOW01`: Draw tower/lattice body in black; remove blue band and avoid generic wedge body.
- `BCNTOW63`: Render the full alternating white/red/white/red tower band pattern; do not collapse to two bands.
- `BCNTOW66`: Render the repeated white/green/white/green tower banding visible in OpenCPN, or verify and encode the exact stripe count from the bitmap crop.
- `BCNTOW70`: Render three ordered tower bands black/yellow/black.
- `BCNTOW71`: Render the complete yellow/black/yellow band sequence in the tower body.
- `BCNTOW74`: Render three ordered tower bands red/green/red.
- `BCNTOW76`: Render three ordered tower bands black/red/black.

## Top Repair Themes

- multi-band beacon/tower/stake rows collapsed to two bands
- lateral red/green candidates invented the opposite lateral colour
- isolated-danger and safe-water rows used generic beacon bodies instead of known topmark/family cues
- tower/lattice rows sometimes lost the tower/lattice body family
- metadata labels occasionally conflict with structured S-57 conditions; renderer should follow structure and visual refs

## Pass List

- `BCNGEN68`: Band order and family are recognizable against OpenCPN-only reference.
- `BCNGEN69`: Band order and family are recognizable against OpenCPN-only reference.
- `BCNGEN79`: OpenCPN visual is tiny, but S-57 condition COLOUR11 and the candidate agree on single-colour special mark.
- `BCNGEN80`: The table label says orange, but the S-57 structure and OpenCPN ref support black; judge follows the structured source.
- `BCNSPR62`: Single-colour spar family is recognizable.
- `BCNSTK05`: Colour and stake family are recognizable.
- `BCNSTK08`: Colour and stake family are recognizable.
- `BCNSTK60`: Colour and stake family are recognizable.
- `BCNSTK61`: Colour and stake family are recognizable.
- `BCNSTK62`: Colour and stake family are recognizable.
- `BCNSTK78`: The main red/white order matches OpenCPN.
- `BCNSTK81`: Structured conditions and OpenCPN render agree with green/white.
- `BCNSTK82`: Colour order and stake family match OpenCPN.
- `BCNSTK83`: Colour order and stake family match the OpenCPN cue.
- `BCNTOW05`: Colour and tower/beacon family are recognizable.
- `BCNTOW60`: Colour and tower/beacon family are recognizable.
- `BCNTOW61`: Colour and tower/beacon family are recognizable.
- `BCNTOW62`: Colour and tower/beacon family are recognizable.
- `BCNTOW64`: Main colour order is correct.
- `BCNTOW65`: Main colour order is correct.
- `BCNTOW68`: Colour family and order are recognizable.
- `BCNTOW69`: Colour family and order are recognizable.
