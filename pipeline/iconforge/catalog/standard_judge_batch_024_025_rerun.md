# Standard Judge Batch 024/025 Rerun

Scope: older repaired icon batches 24 and 25 only, limited to rows whose current `helm_candidate.candidate_status` is still `repaired_pending_judge_rerun` in `pipeline/iconforge/catalog/standard_source_table.json`.

Superseded/excluded because the current source table points to later batch26 pass-pending candidates: `MORFAC03`, `MORFAC04`, `MSTCON04`, `MSTCON14`, `POSGEN04`.

## Result

- Judged: 19
- Pass: 13
- Fail: 6
- Final-approved: 0

## Failed Symbols

| Symbol | Confidence | Required change |
| --- | ---: | --- |
| `HULKES01` | 0.86 | Redraw HULKES01 as the compact brown hulk silhouette from OpenCPN/S-52: low horizontal hull body, no upright leaf outline, no tree-like internal ribs. |
| `LNDARE01` | 0.93 | Redraw LNDARE01 as a small point/dot marker matching the reference; remove the outer ring and bullseye treatment. |
| `LOCMAG01` | 0.96 | Redraw LOCMAG01 as the reference magenta wedge/line glyph; remove the A-shaped triangle, crossbar, and baseline. |
| `LOCMAG51` | 0.96 | Redraw LOCMAG51 as the reference magenta magnetic-anomaly line/area wedge/line glyph; remove the A-shaped body and baseline. |
| `MAGVAR01` | 0.88 | Redraw MAGVAR01 as the compact filled magenta wedge with short vertical reference line matching OpenCPN; avoid a generic flag-on-pole silhouette. |
| `MAGVAR51` | 0.88 | Redraw MAGVAR51 as the compact magenta wedge/vertical-line line-or-area glyph from the reference; remove the flagpole/base icon treatment. |

## Passed Pending Human Final Approval

`BUIREL01`, `BUIREL13`, `GATCON03`, `GATCON04`, `INFORM01`, `ITZARE51`, `LOWACC01`, `MARCUL02`, `MONUMT02`, `MONUMT12`, `NORTHAR1`, `POSGEN03`, `PRCARE51`.

No SVGs or catalogs were edited by this judge pass.
