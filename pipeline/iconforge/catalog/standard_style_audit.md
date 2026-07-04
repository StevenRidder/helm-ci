# Standard Style Audit

Audit of current canonical Helm SVG candidates against the Helm/OpenBridge navigation style contract.

- style_contract: `helm-openbridge-navigation-v1`
- candidates_audited: `824`
- style_pass: `738`
- style_review: `82`
- style_blocked: `4`
- satellite_contact_sheet: `catalog/proofs/style_contract_satellite_contact_sheet.svg`
- contact_sheet_samples: `32`

## Issue Counts

| Issue | Count |
| --- | ---: |
| `diamond_placeholder` | 4 |
| `generic_symbol` | 4 |
| `hairline_stroke` | 36 |
| `missing_round_linecap` | 16 |
| `missing_round_linejoin` | 16 |
| `missing_style_contract` | 5 |
| `oversized_stroke` | 34 |

## Non-Passing Assets

| Asset | Status | Issues | Notes |
| --- | --- | --- | --- |
| `DANGER53` | `style_blocked` | `diamond_placeholder, generic_symbol, missing_round_linecap, missing_round_linejoin, missing_style_contract` | `graphic_elements=2, stroke_range=1.5-2, viewbox=0,0,64,64` |
| `DGPS01DRFSTA01` | `style_blocked` | `diamond_placeholder, generic_symbol, missing_round_linecap, missing_round_linejoin, missing_style_contract` | `graphic_elements=2, stroke_range=1.5-2, viewbox=0,0,64,64` |
| `NEWOBJ 01` | `style_blocked` | `diamond_placeholder, generic_symbol, missing_round_linecap, missing_round_linejoin, missing_style_contract` | `graphic_elements=2, stroke_range=1.5-2, viewbox=0,0,64,64` |
| `NEWOBJ01` | `style_blocked` | `diamond_placeholder, generic_symbol, missing_round_linecap, missing_round_linejoin, missing_style_contract` | `graphic_elements=2, stroke_range=1.5-2, viewbox=0,0,64,64` |
| `BCNGEN01` | `style_review` | `oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=4-7, viewbox=0,0,64,64` |
| `BCNGEN03` | `style_review` | `oversized_stroke` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=4-7, viewbox=0,0,64,64` |
| `BCNLTC01` | `style_review` | `oversized_stroke` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=3.7-6, viewbox=0,0,64,64` |
| `BCNSTK02` | `style_review` | `oversized_stroke` | `graphic_elements=1, no_primary_contract_stroke, stroke_range=7-7, viewbox=0,0,64,64` |
| `BORDER01` | `style_review` | `oversized_stroke` | `graphic_elements=2, no_primary_contract_stroke, stroke_range=2.6-6, viewbox=0,0,64,64` |
| `BOYPIL78` | `style_review` | `hairline_stroke` | `graphic_elements=30, no_primary_contract_stroke, stroke_range=0.6-2.4, viewbox=0,0,64,64` |
| `BOYSPR01` | `style_review` | `hairline_stroke` | `graphic_elements=6, no_primary_contract_stroke, stroke_range=0.65-2.4, viewbox=0,0,64,64` |
| `BOYSPR70` | `style_review` | `hairline_stroke` | `graphic_elements=8, no_primary_contract_stroke, stroke_range=0.65-2.4, viewbox=0,0,64,64` |
| `BOYSPR71` | `style_review` | `hairline_stroke` | `graphic_elements=8, no_primary_contract_stroke, stroke_range=0.65-2.4, viewbox=0,0,64,64` |
| `BOYSPR72` | `style_review` | `hairline_stroke` | `graphic_elements=8, no_primary_contract_stroke, stroke_range=0.65-2.4, viewbox=0,0,64,64` |
| `CHCRDEL1` | `style_review` | `oversized_stroke` | `graphic_elements=1, no_primary_contract_stroke, stroke_range=6-6, viewbox=0,0,64,64` |
| `CHCRID01` | `style_review` | `oversized_stroke` | `graphic_elements=2, no_primary_contract_stroke, stroke_range=4-6, viewbox=0,0,64,64` |
| `CROSSX02` | `style_review` | `hairline_stroke` | `graphic_elements=64, no_primary_contract_stroke, stroke_range=0.65-0.75, viewbox=0,0,64,64` |
| `CURSRB01` | `style_review` | `oversized_stroke` | `graphic_elements=1, no_primary_contract_stroke, stroke_range=5.5-5.5, viewbox=0,0,64,64` |
| `DQUALA11` | `style_review` | `hairline_stroke` | `graphic_elements=21, no_primary_contract_stroke, stroke_range=0.65-1, viewbox=0,0,64,64` |
| `DQUALA21` | `style_review` | `hairline_stroke` | `graphic_elements=22, no_primary_contract_stroke, stroke_range=0.65-1, viewbox=0,0,64,64` |
| `DQUALB01` | `style_review` | `hairline_stroke` | `graphic_elements=21, no_primary_contract_stroke, stroke_range=0.65-1, viewbox=0,0,64,64` |
| `DQUALC01` | `style_review` | `hairline_stroke` | `graphic_elements=13, no_primary_contract_stroke, stroke_range=0.65-1, viewbox=0,0,64,64` |
| `DQUALD01` | `style_review` | `hairline_stroke` | `graphic_elements=9, no_primary_contract_stroke, stroke_range=0.65-1, viewbox=0,0,64,64` |
| `FSHFAC04` | `style_review` | `hairline_stroke` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=0.9-0.9, viewbox=0,0,64,64` |
| `FSHHAV02` | `style_review` | `hairline_stroke` | `graphic_elements=1, no_primary_contract_stroke, stroke_range=0.9-0.9, viewbox=0,0,64,64` |
| `ICEARE04` | `style_review` | `hairline_stroke` | `graphic_elements=5, no_primary_contract_stroke, stroke_range=0.9-0.9, viewbox=0,0,64,64` |
| `MARSHES1` | `style_review` | `hairline_stroke` | `graphic_elements=9, no_primary_contract_stroke, stroke_range=0.9-1, viewbox=0,0,64,64` |
| `MARSYS51` | `style_review` | `hairline_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=0.9-0.9, viewbox=0,0,64,64` |
| `NAVARE51` | `style_review` | `hairline_stroke` | `graphic_elements=2, no_primary_contract_stroke, stroke_range=0.95-0.95, viewbox=0,0,64,64` |
| `NMKINF01` | `style_review` | `oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=2.8-6, viewbox=0,0,64,64` |
| `NMKINF23` | `style_review` | `oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=2.8-10, viewbox=0,0,64,64` |
| `NMKINF24` | `style_review` | `oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=2.8-10, viewbox=0,0,64,64` |
| `NMKINF25` | `style_review` | `oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=2.8-10, viewbox=0,0,64,64` |
| `NMKINF26` | `style_review` | `oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=2.8-10, viewbox=0,0,64,64` |
| `NMKINF27` | `style_review` | `oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=2.8-10, viewbox=0,0,64,64` |
| `NMKINF28` | `style_review` | `oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=2.8-10, viewbox=0,0,64,64` |
| `NMKINF29` | `style_review` | `oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=2.8-10, viewbox=0,0,64,64` |
| `NMKPRH02` | `style_review` | `oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=2.8-6, viewbox=0,0,64,64` |
| `NMKREG10` | `style_review` | `oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=2.8-7, viewbox=0,0,64,64` |
| `NMKREG12` | `style_review` | `oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=2.8-6, viewbox=0,0,64,64` |
| `NMKREG13` | `style_review` | `oversized_stroke` | `graphic_elements=5, no_primary_contract_stroke, stroke_range=2.8-8, viewbox=0,0,64,64` |
| `NMKREG14` | `style_review` | `oversized_stroke` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=2.8-8, viewbox=0,0,64,64` |
| `OBSTRN11` | `style_review` | `oversized_stroke` | `graphic_elements=1, no_primary_contract_stroke, stroke_range=6-6, viewbox=0,0,64,64` |
| `PASTRK01` | `style_review` | `hairline_stroke` | `graphic_elements=2, no_primary_contract_stroke, stroke_range=0.9-0.9, viewbox=0,0,64,64` |
| `PRDINS02` | `style_review` | `oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=3-6, viewbox=0,0,64,64` |
| `PRTSUR01` | `style_review` | `hairline_stroke` | `graphic_elements=1, no_primary_contract_stroke, stroke_range=0.9-0.9, viewbox=0,0,64,64` |
| `QUARRY01` | `style_review` | `oversized_stroke` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=3-6, viewbox=0,0,64,64` |
| `RCKLDG01` | `style_review` | `hairline_stroke` | `graphic_elements=5, no_primary_contract_stroke, stroke_range=0.9-0.9, viewbox=0,0,64,64` |
| `RCRDEF01` | `style_review` | `hairline_stroke` | `graphic_elements=5, no_primary_contract_stroke, stroke_range=0.9-1, viewbox=0,0,64,64` |
| `RCRTCL11` | `style_review` | `hairline_stroke` | `graphic_elements=6, no_primary_contract_stroke, stroke_range=0.9-1, viewbox=0,0,64,64` |
| `RCRTCL12` | `style_review` | `hairline_stroke` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=0.9-1, viewbox=0,0,64,64` |
| `RCRTCL13` | `style_review` | `hairline_stroke` | `graphic_elements=6, no_primary_contract_stroke, stroke_range=0.9-1, viewbox=0,0,64,64` |
| `RCRTCL14` | `style_review` | `hairline_stroke` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=0.9-1, viewbox=0,0,64,64` |
| `RECDEF02` | `style_review` | `hairline_stroke` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=0.9-1, viewbox=0,0,64,64` |
| `RECTRC09` | `style_review` | `hairline_stroke` | `graphic_elements=5, no_primary_contract_stroke, stroke_range=0.9-1, viewbox=0,0,64,64` |
| `RECTRC10` | `style_review` | `hairline_stroke` | `graphic_elements=5, no_primary_contract_stroke, stroke_range=0.9-1, viewbox=0,0,64,64` |
| `RECTRC11` | `style_review` | `hairline_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=0.9-1, viewbox=0,0,64,64` |
| `RECTRC12` | `style_review` | `hairline_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=0.9-1, viewbox=0,0,64,64` |
| `SCLBDY51` | `style_review` | `hairline_stroke` | `graphic_elements=2, no_primary_contract_stroke, stroke_range=0.9-0.9, viewbox=0,0,64,64` |
| `SMCFAC02` | `style_review` | `missing_style_contract` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=2.1-2.4, viewbox=0,0,64,64` |
| `SNDWAV01` | `style_review` | `hairline_stroke` | `graphic_elements=1, no_primary_contract_stroke, stroke_range=0.95-0.95, viewbox=0,0,64,64` |
| `TIDINF51` | `style_review` | `hairline_stroke` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=0.75-0.9, viewbox=0,0,64,64` |
| `TOPMA111` | `style_review` | `oversized_stroke` | `graphic_elements=1, no_primary_contract_stroke, stroke_range=7-7, viewbox=0,0,64,64` |
| `TOPMA113` | `style_review` | `oversized_stroke` | `graphic_elements=2, no_primary_contract_stroke, stroke_range=5-9, viewbox=0,0,64,64` |
| `TOPSHP00` | `style_review` | `missing_round_linecap, missing_round_linejoin, oversized_stroke` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=3-8, viewbox=0,0,64,64` |
| `TOPSHP01` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=3-3, viewbox=0,0,64,64` |
| `TOPSHP02` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=3-3, viewbox=0,0,64,64` |
| `TOPSHP03` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=3-3, viewbox=0,0,64,64` |
| `TOPSHP04` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=3-3, viewbox=0,0,64,64` |
| `TOPSHP08` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `graphic_elements=6, no_primary_contract_stroke, stroke_range=3-3, viewbox=0,0,64,64` |
| `TOPSHP16` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=3-3, viewbox=0,0,64,64` |
| `TOPSHP17` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `graphic_elements=6, no_primary_contract_stroke, stroke_range=3-3, viewbox=0,0,64,64` |
| `TOPSHP18` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=3-3, viewbox=0,0,64,64` |
| `TOPSHP19` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=3-3, viewbox=0,0,64,64` |
| `TOPSHP20` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `graphic_elements=3, no_primary_contract_stroke, stroke_range=3-3, viewbox=0,0,64,64` |
| `TOPSHP21` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `graphic_elements=1, no_primary_contract_stroke, stroke_range=3-3, viewbox=0,0,64,64` |
| `TOPSHPI1` | `style_review` | `oversized_stroke` | `graphic_elements=1, no_primary_contract_stroke, stroke_range=7-7, viewbox=0,0,64,64` |
| `TOPSHPI2` | `style_review` | `oversized_stroke` | `graphic_elements=1, no_primary_contract_stroke, stroke_range=7-7, viewbox=0,0,64,64` |
| `TOPSHPI3` | `style_review` | `oversized_stroke` | `graphic_elements=2, no_primary_contract_stroke, stroke_range=3.2-6, viewbox=0,0,64,64` |
| `TOPSHPP2` | `style_review` | `oversized_stroke` | `graphic_elements=2, no_primary_contract_stroke, stroke_range=3.4-5.8, viewbox=0,0,64,64` |
| `UWTROC03` | `style_review` | `oversized_stroke` | `graphic_elements=22, no_primary_contract_stroke, stroke_range=6-6, viewbox=0,0,64,64` |
| `UWTROC04` | `style_review` | `oversized_stroke` | `graphic_elements=2, no_primary_contract_stroke, stroke_range=5.4-5.4, viewbox=0,0,64,64` |
| `VEGATN03` | `style_review` | `hairline_stroke` | `graphic_elements=5, no_primary_contract_stroke, stroke_range=0.8-0.8, viewbox=0,0,64,64` |
| `VEGATN04` | `style_review` | `hairline_stroke` | `graphic_elements=2, no_primary_contract_stroke, stroke_range=0.8-0.9, viewbox=0,0,64,64` |
| `WRECKS01` | `style_review` | `oversized_stroke` | `graphic_elements=4, no_primary_contract_stroke, stroke_range=2.4-7, viewbox=0,0,64,64` |
| `boyspp50` | `style_review` | `hairline_stroke` | `graphic_elements=4, stroke_range=0.9-1.6, viewbox=0,0,64,64` |
