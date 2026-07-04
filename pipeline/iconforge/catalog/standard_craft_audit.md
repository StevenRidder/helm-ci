# Standard Craft Audit

Rendered quality/readability audit for current Helm SVG candidates.

- candidates_audited: `824`
- craft_pass: `714`
- craft_review: `106`
- craft_blocked: `4`

## Issue Counts

| Issue | Count |
| --- | ---: |
| `off_center_art` | 1 |
| `placeholder_shape` | 4 |
| `style_blocked_upstream` | 4 |
| `tiny_render_too_small` | 97 |
| `too_many_path_commands` | 8 |

## Non-Passing Assets

| Asset | Status | Issues | Tiny BBox | Center Offset | Elements |
| --- | --- | --- | ---: | ---: | ---: |
| `DANGER53` | `craft_blocked` | `placeholder_shape, style_blocked_upstream` | 15.9x15.9 | 0.0 | 2 |
| `DGPS01DRFSTA01` | `craft_blocked` | `placeholder_shape, style_blocked_upstream` | 15.9x15.9 | 0.0 | 2 |
| `NEWOBJ 01` | `craft_blocked` | `placeholder_shape, style_blocked_upstream` | 15.9x15.9 | 0.0 | 2 |
| `NEWOBJ01` | `craft_blocked` | `placeholder_shape, style_blocked_upstream` | 15.9x15.9 | 0.0 | 2 |
| `ADDMRK05` | `craft_review` | `tiny_render_too_small` | 14.4x4.5 | 0.0 | 1 |
| `ARPONE01` | `craft_review` | `tiny_render_too_small` | 6.0x0.75 | 0.016 | 1 |
| `ARPSIX01` | `craft_review` | `tiny_render_too_small` | 13.5x0.9 | 0.0 | 1 |
| `BCNGEN05` | `craft_review` | `tiny_render_too_small` | 3.9x16.95 | 0.041 | 2 |
| `BCNGEN60` | `craft_review` | `tiny_render_too_small` | 3.9x16.95 | 0.041 | 2 |
| `BCNGEN61` | `craft_review` | `tiny_render_too_small` | 3.9x16.95 | 0.041 | 2 |
| `BCNGEN65` | `craft_review` | `tiny_render_too_small` | 4.5x16.95 | 0.041 | 7 |
| `BCNGEN70` | `craft_review` | `tiny_render_too_small` | 4.5x16.95 | 0.041 | 6 |
| `BCNGEN71` | `craft_review` | `tiny_render_too_small` | 4.5x16.95 | 0.041 | 6 |
| `BCNGEN76` | `craft_review` | `tiny_render_too_small` | 4.5x16.95 | 0.041 | 6 |
| `BCNLAT15` | `craft_review` | `tiny_render_too_small` | 4.5x16.95 | 0.041 | 4 |
| `BCNLAT16` | `craft_review` | `tiny_render_too_small` | 4.5x16.95 | 0.041 | 4 |
| `BCNLAT21` | `craft_review` | `tiny_render_too_small` | 3.0x17.4 | 0.031 | 4 |
| `BCNLAT22` | `craft_review` | `tiny_render_too_small` | 3.0x17.4 | 0.031 | 4 |
| `BCNLAT23` | `craft_review` | `tiny_render_too_small` | 4.5x16.95 | 0.041 | 5 |
| `BCNLAT50` | `craft_review` | `tiny_render_too_small` | 3.0x17.4 | 0.031 | 4 |
| `BCNSAW21` | `craft_review` | `tiny_render_too_small` | 4.5x17.4 | 0.0 | 2 |
| `BCNSPP21` | `craft_review` | `tiny_render_too_small` | 4.95x17.4 | 0.009 | 2 |
| `BCNSPR62` | `craft_review` | `tiny_render_too_small` | 4.5x15.0 | 0.031 | 2 |
| `BCNSTK03` | `craft_review` | `tiny_render_too_small` | 3.0x17.4 | 0.031 | 4 |
| `BCNSTK77` | `craft_review` | `tiny_render_too_small` | 3.0x17.4 | 0.031 | 7 |
| `BCNSTK79` | `craft_review` | `tiny_render_too_small` | 3.0x17.4 | 0.031 | 6 |
| `BCNSTK80` | `craft_review` | `tiny_render_too_small` | 3.0x17.4 | 0.031 | 6 |
| `BOYISD12` | `craft_review` | `tiny_render_too_small` | 3.3x7.35 | 0.009 | 2 |
| `BOYMOR11` | `craft_review` | `tiny_render_too_small` | 8.4x2.25 | 0.078 | 2 |
| `BOYPIL78` | `craft_review` | `too_many_path_commands` | 10.5x18.75 | 0.078 | 30 |
| `BOYSAW12` | `craft_review` | `tiny_render_too_small` | 4.5x4.5 | 0.0 | 2 |
| `BOYSPP11` | `craft_review` | `tiny_render_too_small` | 4.5x4.5 | 0.0 | 2 |
| `CBLSUB06` | `craft_review` | `tiny_render_too_small` | 14.7x2.25 | 0.041 | 1 |
| `CROSSX02` | `craft_review` | `too_many_path_commands` | 5.85x5.85 | 0.013 | 64 |
| `DASH` | `craft_review` | `tiny_render_too_small` | 17.4x0.9 | 0.0 | 1 |
| `DISMAR03` | `craft_review` | `tiny_render_too_small` | 6.75x2.7 | 0.007 | 1 |
| `DISMAR04` | `craft_review` | `tiny_render_too_small` | 4.65x2.55 | 0.01 | 1 |
| `DOTT` | `craft_review` | `tiny_render_too_small` | 16.2x0.9 | 0.025 | 1 |
| `DQUALA11` | `craft_review` | `too_many_path_commands` | 9.9x9.75 | 0.016 | 21 |
| `DQUALA21` | `craft_review` | `too_many_path_commands` | 9.9x10.5 | 0.031 | 22 |
| `DQUALB01` | `craft_review` | `too_many_path_commands` | 9.9x9.75 | 0.016 | 21 |
| `DQUALC01` | `craft_review` | `tiny_render_too_small` | 10.5x4.2 | 0.006 | 13 |
| `DQUALD01` | `craft_review` | `tiny_render_too_small` | 10.5x4.2 | 0.006 | 9 |
| `DQUALU01` | `craft_review` | `tiny_render_too_small` | 10.5x4.2 | 0.006 | 2 |
| `DWLDEF01` | `craft_review` | `tiny_render_too_small` | 16.95x3.45 | 0.074 | 5 |
| `DWRTCL05` | `craft_review` | `tiny_render_too_small` | 16.95x3.45 | 0.074 | 6 |
| `DWRTCL06` | `craft_review` | `tiny_render_too_small` | 16.95x3.45 | 0.074 | 6 |
| `DWRTCL07` | `craft_review` | `tiny_render_too_small` | 16.65x3.45 | 0.08 | 4 |
| `DWRTCL08` | `craft_review` | `tiny_render_too_small` | 16.65x3.45 | 0.08 | 4 |
| `ERBLNA01` | `craft_review` | `tiny_render_too_small` | 15.0x0.9 | 0.0 | 1 |
| `ERBLNB01` | `craft_review` | `tiny_render_too_small` | 14.25x0.9 | 0.016 | 1 |
| `EVENTS02` | `craft_review` | `tiny_render_too_small` | 4.5x4.5 | 0.0 | 2 |
| `FERYRT01` | `craft_review` | `tiny_render_too_small` | 14.7x2.25 | 0.017 | 3 |
| `FERYRT02` | `craft_review` | `tiny_render_too_small` | 14.7x3.15 | 0.017 | 3 |
| `FRYARE51` | `craft_review` | `tiny_render_too_small` | 16.2x3.9 | 0.101 | 2 |
| `FSHFAC04` | `craft_review` | `tiny_render_too_small` | 9.45x4.2 | 0.048 | 4 |
| `FSHHAV02` | `craft_review` | `tiny_render_too_small` | 10.95x4.05 | 0.055 | 1 |
| `HECMTR01` | `craft_review` | `tiny_render_too_small` | 3.0x3.0 | 0.0 | 1 |
| `HECMTR02` | `craft_review` | `tiny_render_too_small` | 3.9x3.9 | 0.0 | 1 |
| `HULKES01` | `craft_review` | `tiny_render_too_small` | 7.2x3.0 | 0.025 | 1 |
| `LITFLT01` | `craft_review` | `off_center_art` | 17.4x10.5 | 0.188 | 4 |
| `LNDARE01` | `craft_review` | `tiny_render_too_small` | 1.8x1.8 | 0.0 | 1 |
| `LOCMAG01` | `craft_review` | `tiny_render_too_small` | 3.75x9.9 | 0.016 | 2 |
| `LOCMAG51` | `craft_review` | `tiny_render_too_small` | 3.75x9.9 | 0.016 | 2 |
| `MAGVAR01` | `craft_review` | `tiny_render_too_small` | 3.0x9.15 | 0.016 | 2 |
| `MAGVAR51` | `craft_review` | `tiny_render_too_small` | 3.0x9.15 | 0.016 | 2 |
| `MARSHES1` | `craft_review` | `tiny_render_too_small` | 9.0x4.5 | 0.031 | 9 |
| `MARSYS51` | `craft_review` | `tiny_render_too_small` | 12.9x2.85 | 0.028 | 3 |
| `NAVARE51` | `craft_review` | `tiny_render_too_small` | 11.4x4.5 | 0.031 | 2 |
| `NODATA03` | `craft_review` | `tiny_render_too_small` | 11.4x0.75 | 0.016 | 1 |
| `OSPONE02` | `craft_review` | `tiny_render_too_small` | 3.9x0.9 | 0.0 | 1 |
| `OSPSIX02` | `craft_review` | `tiny_render_too_small` | 5.4x0.9 | 0.0 | 1 |
| `OVERSC01` | `craft_review` | `tiny_render_too_small` | 0.9x10.5 | 0.0 | 1 |
| `PIPARE51` | `craft_review` | `tiny_render_too_small` | 13.65x1.65 | 0.022 | 1 |
| `PIPARE61` | `craft_review` | `tiny_render_too_small` | 13.65x1.65 | 0.022 | 1 |
| `PIPSOL06` | `craft_review` | `tiny_render_too_small` | 13.95x4.65 | 0.018 | 3 |
| `PLNPOS02` | `craft_review` | `tiny_render_too_small` | 6.0x0.9 | 0.0 | 1 |
| `PRTSUR01` | `craft_review` | `tiny_render_too_small` | 11.4x0.75 | 0.016 | 1 |
| `RCRDEF01` | `craft_review` | `tiny_render_too_small` | 15.3x3.15 | 0.083 | 5 |
| `RCRTCL11` | `craft_review` | `tiny_render_too_small` | 15.3x3.15 | 0.083 | 6 |
| `RCRTCL12` | `craft_review` | `tiny_render_too_small` | 15.3x3.15 | 0.083 | 4 |
| `RCRTCL13` | `craft_review` | `tiny_render_too_small` | 15.3x3.15 | 0.083 | 6 |
| `RCRTCL14` | `craft_review` | `tiny_render_too_small` | 15.3x3.15 | 0.083 | 4 |
| `RECDEF02` | `craft_review` | `tiny_render_too_small` | 12.15x3.15 | 0.022 | 4 |
| `RECTRC09` | `craft_review` | `tiny_render_too_small` | 12.15x3.15 | 0.022 | 5 |
| `RECTRC10` | `craft_review` | `tiny_render_too_small` | 12.15x3.15 | 0.022 | 5 |
| `RECTRC11` | `craft_review` | `tiny_render_too_small` | 12.15x3.15 | 0.022 | 3 |
| `RECTRC12` | `craft_review` | `tiny_render_too_small` | 12.15x3.15 | 0.022 | 3 |
| `SCALEB10` | `craft_review` | `tiny_render_too_small` | 0.9x15.9 | 0.031 | 6 |
| `SCALEB11` | `craft_review` | `tiny_render_too_small` | 0.9x15.9 | 0.031 | 6 |
| `SCLBDY51` | `craft_review` | `tiny_render_too_small` | 12.15x3.9 | 0.016 | 2 |
| `SILBUI01` | `craft_review` | `tiny_render_too_small` | 4.5x4.5 | 0.0 | 1 |
| `SILBUI11` | `craft_review` | `tiny_render_too_small` | 4.5x4.5 | 0.0 | 1 |
| `SNDWAV01` | `craft_review` | `tiny_render_too_small` | 12.3x1.65 | 0.024 | 1 |
| `SNDWAV02` | `craft_review` | `tiny_render_too_small` | 18.75x4.95 | 0.027 | 1 |
| `SOLD` | `craft_review` | `tiny_render_too_small` | 17.4x0.9 | 0.0 | 1 |
| `TIDINF51` | `craft_review` | `tiny_render_too_small` | 12.9x2.7 | 0.025 | 4 |
| `TOPMA114` | `craft_review` | `tiny_render_too_small` | 4.5x6.9 | 0.0 | 1 |
| `TOPMAR91` | `craft_review` | `tiny_render_too_small` | 4.5x6.0 | 0.0 | 1 |
| `TOPMAR92` | `craft_review` | `tiny_render_too_small` | 4.5x6.0 | 0.0 | 1 |
| `TOWERS56` | `craft_review` | `too_many_path_commands` | 15.0x18.3 | 0.05 | 21 |
| `TOWERS98` | `craft_review` | `too_many_path_commands` | 15.0x18.3 | 0.05 | 21 |
| `TOWERS99` | `craft_review` | `too_many_path_commands` | 15.0x18.3 | 0.05 | 21 |
| `TREPNT05` | `craft_review` | `tiny_render_too_small` | 7.5x3.9 | 0.044 | 3 |
| `UNITFTH1` | `craft_review` | `tiny_render_too_small` | 4.8x7.05 | 0.094 | 1 |
| `VECWTR01` | `craft_review` | `tiny_render_too_small` | 7.5x4.95 | 0.022 | 1 |
| `VECWTR21` | `craft_review` | `tiny_render_too_small` | 7.5x4.95 | 0.022 | 1 |
| `VTCLMK01` | `craft_review` | `tiny_render_too_small` | 3.0x9.0 | 0.0 | 3 |
| `WATTUR02` | `craft_review` | `tiny_render_too_small` | 15.9x2.55 | 0.056 | 1 |
| `WTLVGG02` | `craft_review` | `tiny_render_too_small` | 3.45x9.9 | 0.009 | 2 |
