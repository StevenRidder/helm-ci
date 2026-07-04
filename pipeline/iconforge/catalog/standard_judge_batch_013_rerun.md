# Standard Judge Batch 013 Rerun

- Project: `vulkan`
- Task: `FORGE-18`
- Agent: `codex/FORGE-18-visual-rerun-batch13-local`
- Selection: `repaired_pending_judge_rerun` from `catalog/owned_repair_batch13.json`
- Counts: 29 judged, 9 pass, 20 fail, 0 final-approved

| Symbol | Pass | Confidence | Observed | Required change | Safety reason codes |
|---|---:|---:|---|---|---|
| `BOYSPH01` | `true` | 0.90 | Spherical buoy with red upper and black lower horizontal body, black outline, and stem; invented blue/grey is gone. | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| `BOYSPH65` | `true` | 0.92 | Spherical buoy with vertical red/white split, black outline, and stem. | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| `BOYSPH66` | `true` | 0.90 | Spherical buoy with horizontal red-green-red bands and black outline/stem. | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| `BOYSPH70` | `true` | 0.90 | Spherical buoy with black-yellow-black horizontal cardinal sequence and black outline/stem. | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| `BOYSPH71` | `true` | 0.90 | Spherical buoy with yellow-black-yellow horizontal cardinal sequence and black outline/stem. | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| `BOYSPP11` | `true` | 0.84 | Simplified yellow pillar special-purpose buoy cue with black outline and stem; generic black lower body is removed. | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| `BOYSPP15` | `true` | 0.85 | Simplified yellow conical/triangular special-purpose TSS starboard cue with black outline and stem. | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| `BOYSPP25` | `true` | 0.84 | Simplified yellow can/cylindrical special-purpose TSS port cue with black outline and stem. | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| `BOYSPR01` | `false` | 0.86 | White/black spar body is present, but a long grey horizontal separator stroke protrudes far outside the narrow spar silhouette. | Clip or remove the horizontal separator stroke so it does not extend outside the spar silhouette; preserve the white-over-black body. | visual_artifact, unclipped_separator_strokes, reference_mismatch |
| `BOYSPR70` | `false` | 0.88 | Black-yellow-black spar sequence is present, but two long grey separator strokes protrude outside the narrow spar body. | Clip or remove the separator strokes outside the spar silhouette; preserve black-yellow-black band order. | visual_artifact, unclipped_separator_strokes, reference_mismatch |
| `BOYSPR71` | `false` | 0.88 | Yellow-black-yellow spar sequence is present, but two long grey separator strokes protrude outside the narrow spar body. | Clip or remove the separator strokes outside the spar silhouette; preserve yellow-black-yellow band order. | visual_artifact, unclipped_separator_strokes, reference_mismatch |
| `BOYSPR72` | `false` | 0.88 | Black-red-black spar sequence is present, but two long grey separator strokes protrude outside the narrow spar body. | Clip or remove the separator strokes outside the spar silhouette; preserve black-red-black band order. | visual_artifact, unclipped_separator_strokes, reference_mismatch |
| `BOYSUP01` | `false` | 0.86 | Red/black rounded capsule buoy; it does not match the OpenCPN/S-101 super-buoy platform/trapezoid with ring cue. | Redraw as the super-buoy platform/trapezoid/ring reference silhouette while preserving red/black load-bearing colours. | wrong_shape, unsafe_buoy_family_confusion, reference_mismatch |
| `BOYSUP02` | `false` | 0.86 | Solid black rounded capsule buoy; it does not match the black super-buoy platform/trapezoid reference silhouette. | Redraw BOYSUP02 as the black super-buoy platform/trapezoid reference silhouette. | wrong_shape, unsafe_buoy_family_confusion, reference_mismatch |
| `BOYSUP03` | `false` | 0.88 | Red/black rounded capsule with a small cap/top stem; it misses the LANBY star/asterisk top cue and platform-shaped super-buoy body. | Redraw with the super-buoy platform silhouette and the LANBY star/asterisk topmark cue; preserve red/black colour semantics. | wrong_shape, missing_topmark, reference_mismatch |
| `BOYSUP65` | `false` | 0.86 | Vertical red/white striping is fixed, but the body remains a rounded capsule rather than the super-buoy platform/trapezoid witness. | Redraw on the super-buoy platform/trapezoid reference body while preserving vertical red/white order. | wrong_shape, reference_mismatch |
| `BRIDGE01` | `false` | 0.82 | Magenta circular ring is present, but the candidate adds a black crosshair/target center instead of the S-101/OpenCPN opening-bridge ring/diagonal cue. | Remove the invented black crosshair/target detail and redraw the opening-bridge ring to match the S-101/OpenCPN witness. | invented_detail, wrong_shape, reference_mismatch |
| `BRTHNO01` | `false` | 0.91 | Black outlined circle containing literal “No” text. | Redraw as the magenta berth-number circular reference cue and remove the invented text. | invented_text, wrong_colour_family, reference_mismatch |
| `BUAARE02` | `false` | 0.89 | White square frame with multiple brown building blocks and a diagonal slash. | Redraw as the built-up-area brown filled area/dot reference cue; remove the square frame and block-cluster/slash treatment. | wrong_shape, wrong_scale, reference_mismatch |
| `BUIREL01` | `false` | 0.88 | Black filled church/building silhouette with cross. | Redraw to the brown Christian cross/church schematic reference cue rather than a filled building silhouette. | wrong_shape, wrong_colour_family, reference_mismatch |
| `BUIREL04` | `false` | 0.88 | Black domed building silhouette with white columns. | Redraw to the brown non-Christian religious-building schematic reference cue. | wrong_shape, wrong_colour_family, reference_mismatch |
| `BUIREL05` | `false` | 0.88 | Black mosque/minaret building silhouette. | Redraw to the mosque/minaret crescent/reference cue and avoid the generic filled building silhouette. | wrong_shape, reference_mismatch |
| `BUIREL13` | `false` | 0.86 | Black filled church/building silhouette with cross. | Redraw to the conspicuous Christian cross/church reference cue while preserving black conspicuous colour. | wrong_shape, reference_mismatch |
| `BUIREL14` | `false` | 0.86 | Black domed building silhouette with white columns. | Redraw to the conspicuous non-Christian schematic reference cue while preserving black conspicuous colour. | wrong_shape, reference_mismatch |
| `BUIREL15` | `false` | 0.87 | Black mosque/minaret building silhouette. | Redraw to the conspicuous mosque/minaret crescent/reference cue while preserving black conspicuous colour. | wrong_shape, reference_mismatch |
| `BUISGL01` | `false` | 0.87 | Brown house pictogram with roof and black door. | Redraw as the compact brown square/building reference silhouette; remove roof/door pictogram detail. | wrong_shape, invented_detail, reference_mismatch |
| `BUISGL11` | `false` | 0.87 | Black house pictogram with roof and white door. | Redraw as the compact black square/building reference silhouette; remove roof/door pictogram detail. | wrong_shape, invented_detail, reference_mismatch |
| `BUNSTA01` | `true` | 0.86 | Black diesel/fuel-pump cue with white display and hose. | No repair required for this visual rerun; keep pending final approval QA and do not mark final-approved. |  |
| `BUNSTA02` | `false` | 0.90 | Black water-drop pictogram with a white wave mark. | Redraw to the water bunker-station bucket/tap reference silhouette; remove the generic droplet pictogram. | wrong_shape, invented_generic_icon, reference_mismatch |

No rows are final-approved by this rerun.
