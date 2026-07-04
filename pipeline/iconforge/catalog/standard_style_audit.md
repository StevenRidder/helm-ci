# Standard Style Audit

Audit of current canonical Helm SVG candidates against the Helm/OpenBridge navigation style contract.

- style_contract: `helm-openbridge-navigation-v1`
- candidates_audited: `824`
- style_pass: `737`
- style_review: `83`
- style_blocked: `4`

## Issue Counts

| Issue | Count |
| --- | ---: |
| `diamond_placeholder` | 4 |
| `generic_symbol` | 4 |
| `hairline_stroke` | 36 |
| `missing_round_linecap` | 16 |
| `missing_round_linejoin` | 16 |
| `missing_style_contract` | 5 |
| `oversized_stroke` | 35 |

## Non-Passing Assets

| Asset | Status | Issues | Notes |
| --- | --- | --- | --- |
| `DANGER53` | `style_blocked` | `diamond_placeholder, generic_symbol, missing_round_linecap, missing_round_linejoin, missing_style_contract` | `stroke_range=1.5-2` |
| `DGPS01DRFSTA01` | `style_blocked` | `diamond_placeholder, generic_symbol, missing_round_linecap, missing_round_linejoin, missing_style_contract` | `stroke_range=1.5-2` |
| `NEWOBJ 01` | `style_blocked` | `diamond_placeholder, generic_symbol, missing_round_linecap, missing_round_linejoin, missing_style_contract` | `stroke_range=1.5-2` |
| `NEWOBJ01` | `style_blocked` | `diamond_placeholder, generic_symbol, missing_round_linecap, missing_round_linejoin, missing_style_contract` | `stroke_range=1.5-2` |
| `BCNGEN01` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=4-7` |
| `BCNGEN03` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=4-7` |
| `BCNLTC01` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=3.7-6` |
| `BCNSTK02` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=7-7` |
| `BCNTOW01` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=4-6` |
| `BORDER01` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.6-6` |
| `BOYPIL78` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.6-2.4` |
| `BOYSPR01` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.65-2.4` |
| `BOYSPR70` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.65-2.4` |
| `BOYSPR71` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.65-2.4` |
| `BOYSPR72` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.65-2.4` |
| `CHCRDEL1` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=6-6` |
| `CHCRID01` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=4-6` |
| `CROSSX02` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.65-0.75` |
| `CURSRB01` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=5.5-5.5` |
| `DQUALA11` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.65-1` |
| `DQUALA21` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.65-1` |
| `DQUALB01` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.65-1` |
| `DQUALC01` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.65-1` |
| `DQUALD01` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.65-1` |
| `FSHFAC04` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-0.9` |
| `FSHHAV02` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-0.9` |
| `ICEARE04` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-0.9` |
| `MARSHES1` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-1` |
| `MARSYS51` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-0.9` |
| `NAVARE51` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.95-0.95` |
| `NMKINF01` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.8-6` |
| `NMKINF23` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.8-10` |
| `NMKINF24` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.8-10` |
| `NMKINF25` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.8-10` |
| `NMKINF26` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.8-10` |
| `NMKINF27` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.8-10` |
| `NMKINF28` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.8-10` |
| `NMKINF29` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.8-10` |
| `NMKPRH02` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.8-6` |
| `NMKREG10` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.8-7` |
| `NMKREG12` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.8-6` |
| `NMKREG13` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.8-8` |
| `NMKREG14` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.8-8` |
| `OBSTRN11` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=6-6` |
| `PASTRK01` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-0.9` |
| `PRDINS02` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=3-6` |
| `PRTSUR01` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-0.9` |
| `QUARRY01` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=3-6` |
| `RCKLDG01` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-0.9` |
| `RCRDEF01` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-1` |
| `RCRTCL11` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-1` |
| `RCRTCL12` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-1` |
| `RCRTCL13` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-1` |
| `RCRTCL14` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-1` |
| `RECDEF02` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-1` |
| `RECTRC09` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-1` |
| `RECTRC10` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-1` |
| `RECTRC11` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-1` |
| `RECTRC12` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-1` |
| `SCLBDY51` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.9-0.9` |
| `SMCFAC02` | `style_review` | `missing_style_contract` | `no_primary_contract_stroke, stroke_range=2.1-2.4` |
| `SNDWAV01` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.95-0.95` |
| `TIDINF51` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.75-0.9` |
| `TOPMA111` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=7-7` |
| `TOPMA113` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=5-9` |
| `TOPSHP00` | `style_review` | `missing_round_linecap, missing_round_linejoin, oversized_stroke` | `no_primary_contract_stroke, stroke_range=3-8` |
| `TOPSHP01` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `no_primary_contract_stroke, stroke_range=3-3` |
| `TOPSHP02` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `no_primary_contract_stroke, stroke_range=3-3` |
| `TOPSHP03` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `no_primary_contract_stroke, stroke_range=3-3` |
| `TOPSHP04` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `no_primary_contract_stroke, stroke_range=3-3` |
| `TOPSHP08` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `no_primary_contract_stroke, stroke_range=3-3` |
| `TOPSHP16` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `no_primary_contract_stroke, stroke_range=3-3` |
| `TOPSHP17` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `no_primary_contract_stroke, stroke_range=3-3` |
| `TOPSHP18` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `no_primary_contract_stroke, stroke_range=3-3` |
| `TOPSHP19` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `no_primary_contract_stroke, stroke_range=3-3` |
| `TOPSHP20` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `no_primary_contract_stroke, stroke_range=3-3` |
| `TOPSHP21` | `style_review` | `missing_round_linecap, missing_round_linejoin` | `no_primary_contract_stroke, stroke_range=3-3` |
| `TOPSHPI1` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=7-7` |
| `TOPSHPI2` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=7-7` |
| `TOPSHPI3` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=3.2-6` |
| `TOPSHPP2` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=3.4-5.8` |
| `UWTROC03` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=6-6` |
| `UWTROC04` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=5.4-5.4` |
| `VEGATN03` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.8-0.8` |
| `VEGATN04` | `style_review` | `hairline_stroke` | `no_primary_contract_stroke, stroke_range=0.8-0.9` |
| `WRECKS01` | `style_review` | `oversized_stroke` | `no_primary_contract_stroke, stroke_range=2.4-7` |
| `boyspp50` | `style_review` | `hairline_stroke` | `stroke_range=0.9-1.6` |
