# Standard Repair Batch 48 / Owned Repair Batch 56

Targeted owned redraws for the 17 failures from `standard_judge_batch_054_rerun`.

- failed_repaired: `17`
- visual_parity: `repaired_pending_judge_rerun`

| Asset | Required change | Safety reason codes |
| --- | --- | --- |
| `BOYCON78` | Redraw with vertical red/white striping on the conical/nun body; the current after SVG stacks red over white horizontally. | `wrong_colour_pattern`, `wrong_stripe_orientation`, `reference_mismatch` |
| `BOYCON79` | Redraw as the BCNSHP1 stake/perch beacon family with red/green body; the current after SVG is a conical buoy substitution. | `wrong_shape`, `wrong_reference_family`, `unsafe_buoy_beacon_confusion` |
| `BOYISD12` | Restore the isolated-danger simplified reference cue with paired red marks; the current candidate is a single white spherical buoy. | `wrong_colour_family`, `wrong_symbol_family`, `missing_required_marks`, `reference_mismatch` |
| `BOYMOR01` | Restore the black mooring buoy/facility witness shape; the current candidate is a white barrel/body and drops the black mooring cue. | `wrong_colour_family`, `wrong_reference_family`, `reference_mismatch` |
| `BOYMOR03` | Restore the can mooring buoy green/black colour cue; the current candidate is a plain white can body. | `wrong_colour_family`, `missing_required_colour`, `reference_mismatch` |
| `BOYMOR11` | Restore the black mooring facility/buoy symbol family; the current candidate is a white barrel/body with no black mooring cue. | `wrong_colour_family`, `wrong_reference_family`, `reference_mismatch` |
| `BOYPIL01` | Restore the black pillar buoy body recorded by the source spine; the current candidate is white. | `wrong_colour_family`, `missing_required_colour`, `reference_mismatch` |
| `BOYPIL73` | Redraw with vertical red/white stripes on the pillar body; the current candidate stacks red over white horizontally. | `wrong_colour_pattern`, `wrong_stripe_orientation`, `reference_mismatch` |
| `BOYSAW12` | Restore the safe-water simplified red reference cue; the current candidate is a single white spherical buoy. | `wrong_colour_family`, `wrong_symbol_family`, `reference_mismatch` |
| `BOYSPH01` | Restore the red/black spherical buoy colour pair; the current candidate is a plain white sphere. | `wrong_colour_family`, `missing_required_colour`, `reference_mismatch` |
| `BOYSPH65` | Redraw with vertical red/white striping on the spherical buoy; the current candidate stacks red over white horizontally. | `wrong_colour_pattern`, `wrong_stripe_orientation`, `reference_mismatch` |
| `BOYSPP11` | Restore the yellow special-purpose pillar cue from the OpenCPN/S-101/AquaMap witnesses; the current candidate is white. | `wrong_colour_family`, `missing_special_purpose_yellow`, `reference_mismatch` |
| `BOYSPP15` | Restore the yellow special-purpose conical/nun cue; the current candidate is white. | `wrong_colour_family`, `missing_special_purpose_yellow`, `reference_mismatch` |
| `BOYSPP25` | Redraw as a yellow can/cylindrical special-purpose TSS port cue; the current candidate is a white pillar body. | `wrong_shape`, `wrong_colour_family`, `missing_special_purpose_yellow`, `reference_mismatch` |
| `BOYSUP01` | Restore red/black load-bearing colours on the low super-buoy body; the current candidate is a white platform/body. | `wrong_colour_family`, `missing_required_colour`, `reference_mismatch` |
| `BOYSUP03` | Restore the LANBY/super-buoy reference family with red/black body and star/asterisk topmark; the current candidate is a white platform without the LANBY topmark. | `wrong_colour_family`, `missing_topmark`, `reference_mismatch` |
| `BOYSUP65` | Redraw with vertical red/white stripes on the super-buoy body; the current candidate uses horizontal red-over-white bands. | `wrong_colour_pattern`, `wrong_stripe_orientation`, `reference_mismatch` |

Rows remain pending judge rerun; none are final-approved.
