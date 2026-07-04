# Standard Repair Batch 50 / Owned Repair Batch 58

Targeted nested/bordered square-board redraws for the TOPSHP failures from `standard_judge_batch_057_rerun`.

- failed_repaired: `11`
- visual_parity: `repaired_pending_judge_rerun`

| Asset | Required change | Pattern |
| --- | --- | --- |
| `TOPSHP25` | Redraw COLPAT6 as the compact square-board reference pattern: white field with orange nested/center block, not a 4x4 checkerboard. | `nested` `white,orange` |
| `TOPSHP29` | Redraw COLPAT6 as the compact square-board reference pattern: red field with nested green/red center geometry, not a 4x4 checkerboard. | `nested` `red,green,red` |
| `TOPSHP30` | Redraw COLPAT6 as the compact square-board reference pattern: green field with nested white/yellow center geometry, not a 4x4 checkerboard. | `nested` `green,white,yellow` |
| `TOPSHP31` | Redraw COLPAT6 as the compact square-board reference pattern: orange field with nested white center geometry, not a 4x4 checkerboard. | `nested` `orange,white` |
| `TOPSHP33` | Do not promote without an exact OpenCPN/source render for this TOPSHP33 COLPAT6 row; the current 4x4 checkerboard is inconsistent with the neighboring COLPAT6 reference family. | `nested` `green,red,green` |
| `TOPSHP37` | Restore the COLPAT6 black/white nested-square reference cue; the current all-black checker cells collapse to a solid black board and lose the inner white pattern. | `nested` `black,white,black` |
| `TOPSHP38` | Redraw the squared/checkered reference as the compact 2x2 orange/white quadrant layout; the current 4x4 checkerboard overstates the pattern and does not match the reference crop. | `quadrant` `orange,white` |
| `TOPSHP40` | Restore the COLPAT6 white/black nested-square reference cue; the current 4x4 checkerboard does not match the OpenCPN reference pattern. | `nested` `white,black,white` |
| `TOPSHP41` | Restore the horizontal orange/white band cue shown by the reference render; the current candidate is effectively solid orange and drops the white bands. | `horizontal` `orange,white,orange` |
| `TOPSHP43` | Restore the compound COLPAT6+horizontal reference cue with green/red plus nested white/green structure; the current simple green/red/green bands are too shallow. | `compound` `green,red,green` |
| `TOPSHP44` | Restore the COLPAT6 yellow/white nested-square reference cue; the current yellow-only board loses the reference pattern. | `nested` `yellow,white,yellow` |

Rows remain pending judge rerun; none are final-approved.
