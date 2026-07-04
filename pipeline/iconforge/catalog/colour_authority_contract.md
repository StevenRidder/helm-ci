# Colour Authority Contract

DB-side contract separating feature colour predicates from generated visual colour recipes.

- schema: `helm.iconforge.colour_authority_contract.v1`
- rows: `824`
- runtime_blocker_rows: `380`

## Status Counts

| Status | Count |
| --- | ---: |
| `aligned` | 183 |
| `feature_colour_dropped` | 129 |
| `feature_empty_visual_defined` | 261 |
| `feature_visual_order_difference` | 106 |
| `pattern_orientation_conflict` | 37 |
| `visual_colour_extra` | 108 |

## Policy

- Feature colours remain the S-57/S-52 semantic predicates.
- Visual colours are read from the selected generated Helm SVG/recipe.
- S-101 witness images are not colour-authoritative by default.
- Unresolved or missing colour authority fails closed.

## Feature/Visual Colour Deltas

| Asset | Status | Feature colours | Visual colours | Missing feature colours | Extra visual colours | Authority |
| --- | --- | --- | --- | --- | --- | --- |
| `ADDMRK01` | `feature_colour_dropped` | white, black | white | black | none | `manual_review_required` |
| `ADDMRK02` | `feature_colour_dropped` | white, black | white | black | none | `manual_review_required` |
| `ADDMRK05` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `BCNGEN01` | `feature_colour_dropped` | black | blue | black | blue | `manual_review_required` |
| `BCNGEN03` | `feature_colour_dropped` | black | blue, magenta | black | blue, magenta | `manual_review_required` |
| `BCNLAT15` | `feature_colour_dropped` | red, green, red | white, red | green | white | `manual_review_required` |
| `BCNLAT16` | `feature_colour_dropped` | green, red, green | white, green | red | white | `manual_review_required` |
| `BCNLAT21` | `feature_colour_dropped` | red, green, red | white, red | green | white | `manual_review_required` |
| `BCNLAT22` | `feature_colour_dropped` | green, red, green | white, green | red | white | `manual_review_required` |
| `BCNLAT23` | `feature_colour_dropped` | red, green, black | white, red, green | black | white | `manual_review_required` |
| `BCNLTC01` | `feature_colour_dropped` | black | white | black | white | `manual_review_required` |
| `BOYBAR01` | `feature_colour_dropped` | red, black | white, black, black, white | red | white | `manual_review_required` |
| `BOYINB01` | `feature_colour_dropped` | black | white, white | black | white | `manual_review_required` |
| `BOYMOR01` | `feature_colour_dropped` | black | white | black | white | `manual_review_required` |
| `BOYMOR03` | `feature_colour_dropped` | green, black | white | green, black | white | `manual_review_required` |
| `BUNSTA02` | `feature_colour_dropped` | black | white | black | white | `manual_review_required` |
| `FERYRT02` | `feature_colour_dropped` | black | grey, grey, grey | black | grey | `manual_review_required` |
| `HRBFAC10` | `feature_colour_dropped` | black | grey | black | grey | `manual_review_required` |
| `HRBFAC11` | `feature_colour_dropped` | black | grey | black | grey | `manual_review_required` |
| `HRBFAC12` | `feature_colour_dropped` | black | grey | black | grey | `manual_review_required` |
| `HRBFAC13` | `feature_colour_dropped` | black | grey | black | grey | `manual_review_required` |
| `HRBFAC16` | `feature_colour_dropped` | black | grey | black | grey | `manual_review_required` |
| `HRBFAC17` | `feature_colour_dropped` | black | grey | black | grey | `manual_review_required` |
| `HRBFAC18` | `feature_colour_dropped` | black | grey | black | grey | `manual_review_required` |
| `LOWACC41` | `feature_colour_dropped` | black | grey | black | grey | `manual_review_required` |
| `MARSHES1` | `feature_colour_dropped` | brown | yellow, yellow, yellow, yellow, yellow, yellow, yellow, yellow, yellow | brown | yellow | `manual_review_required` |
| `MORFAC03` | `feature_colour_dropped` | black | brown | black | brown | `manual_review_required` |
| `MSTCON14` | `feature_colour_dropped` | black | white | black | white | `manual_review_required` |
| `NMKINF01` | `feature_colour_dropped` | green, white, black | green | white, black | none | `manual_review_required` |
| `NMKINF02` | `feature_colour_dropped` | white, black | blue, white | black | blue | `manual_review_required` |
| `NMKINF03` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF04` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF05` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF06` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF19` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF20` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF21` | `feature_colour_dropped` | white, black | blue, white, white | black | blue | `manual_review_required` |
| `NMKINF22` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF23` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF24` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF25` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF26` | `feature_colour_dropped` | white | blue | white | blue | `manual_review_required` |
| `NMKINF27` | `feature_colour_dropped` | white | blue | white | blue | `manual_review_required` |
| `NMKINF28` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF29` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF38` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF40` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF43` | `feature_colour_dropped` | white, black | blue, white | black | blue | `manual_review_required` |
| `NMKINF44` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF45` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF46` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF47` | `feature_colour_dropped` | white, black | blue, white | black | blue | `manual_review_required` |
| `NMKINF48` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF49` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF50` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKINF53` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKPRH02` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NMKPRH06` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NMKPRH07` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NMKPRH08` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NMKPRH10` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NMKPRH11` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NMKPRH12` | `feature_colour_dropped` | red, white, black | red, white | black | none | `manual_review_required` |
| `NMKPRH13` | `feature_colour_dropped` | red, white, black | white, red | black | none | `manual_review_required` |
| `NMKPRH14` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NMKRCD01` | `feature_colour_dropped` | black | yellow | black | yellow | `manual_review_required` |
| `NMKRCD02` | `feature_colour_dropped` | black | yellow, yellow | black | yellow | `manual_review_required` |
| `NMKRCD03` | `feature_colour_dropped` | green, white, black | green, white | black | none | `manual_review_required` |
| `NMKRCD04` | `feature_colour_dropped` | green, white, black | green, white | black | none | `manual_review_required` |
| `NMKRCD05` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKRCD06` | `feature_colour_dropped` | white, black | blue | white, black | blue | `manual_review_required` |
| `NMKREG01` | `feature_colour_dropped` | red, white, black | red, white | black | none | `manual_review_required` |
| `NMKREG02` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NMKREG03` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NMKREG10` | `feature_colour_dropped` | red, white, black | red, white | black | none | `manual_review_required` |
| `NMKREG11` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NMKREG12` | `feature_colour_dropped` | red, white, black | red, white | black | none | `manual_review_required` |
| `NMKREG13` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NMKREG14` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NMKREG15` | `feature_colour_dropped` | red, white, black | red, white | black | none | `manual_review_required` |
| `NMKREG16` | `feature_colour_dropped` | red, white, black | red, white | black | none | `manual_review_required` |
| `NMKREG17` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NMKREG19` | `feature_colour_dropped` | red, white, black | red, white | black | none | `manual_review_required` |
| `NMKREG20` | `feature_colour_dropped` | red, white, black | red, white | black | none | `manual_review_required` |
| `NOTMRK01` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `NOTMRK02` | `feature_colour_dropped` | red, white, black | red, white | black | none | `manual_review_required` |
| `NOTMRK03` | `feature_colour_dropped` | black | blue | black | blue | `manual_review_required` |
| `OBSTRN01` | `feature_colour_dropped` | black | blue | black | blue | `manual_review_required` |
| `PIER0001` | `feature_colour_dropped` | black | blue, blue | black | blue | `manual_review_required` |
| `PILBOP02` | `feature_colour_dropped` | black | magenta, magenta | black | magenta | `manual_review_required` |
| `RASCAN11` | `feature_colour_dropped` | black | white | black | white | `manual_review_required` |
| `SISTAT02` | `feature_colour_dropped` | white | black | white | black | `manual_review_required` |
| `SSENTR01` | `feature_colour_dropped` | black | white, white | black | white | `manual_review_required` |
| `SSWARS01` | `feature_colour_dropped` | black | white | black | white | `manual_review_required` |
| `TERMNL01` | `feature_colour_dropped` | black | white | black | white | `manual_review_required` |
| `TERMNL03` | `feature_colour_dropped` | red, black | white, red, green, yellow, red | black | white, green, yellow | `manual_review_required` |
| `TERMNL09` | `feature_colour_dropped` | red, black | red | black | none | `manual_review_required` |
| `TOPMA107` | `feature_colour_dropped` | white, red | white | red | none | `manual_review_required` |
| `TOPMA109` | `feature_colour_dropped` | white, green | white | green | none | `manual_review_required` |
| `TOPSHP00` | `feature_colour_dropped` | white, white, red | white | red | none | `manual_review_required` |
| `TOPSHP33` | `feature_colour_dropped` | green, red, green | white, white | green, red | white | `manual_review_required` |
| `TOPSHQ06` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `TOPSHQ07` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `TOPSHQ08` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `TOPSHQ15` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `TOPSHQ16` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `TOPSHQ17` | `feature_colour_dropped` | white, black | white | black | none | `manual_review_required` |
| `TOPSHQ18` | `feature_colour_dropped` | red, white, black | red, red | white, black | none | `manual_review_required` |
| `TOPSHQ19` | `feature_colour_dropped` | red, green, white, black | red | green, white, black | none | `manual_review_required` |
| `TOPSHQ20` | `feature_colour_dropped` | white, black | white | black | none | `manual_review_required` |
| `TOPSHQ21` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `TOPSHQ22` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `TOPSHQ23` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `TOPSHQ24` | `feature_colour_dropped` | green, white, black | green | white, black | none | `manual_review_required` |
| `TOPSHQ25` | `feature_colour_dropped` | green, white, black | green | white, black | none | `manual_review_required` |
| `TOPSHQ26` | `feature_colour_dropped` | red, white, black | red, white | black | none | `manual_review_required` |
| `TOPSHQ27` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `TOPSHQ28` | `feature_colour_dropped` | red, white, black | red | white, black | none | `manual_review_required` |
| `TOPSHQ29` | `feature_colour_dropped` | red, white, black | red, red | white, black | none | `manual_review_required` |
| `TOPSHQ30` | `feature_colour_dropped` | red, white, black | red, red | white, black | none | `manual_review_required` |
| `TOPSHQ31` | `feature_colour_dropped` | red, white, black | red, red | white, black | none | `manual_review_required` |
| `TOPSHQ32` | `feature_colour_dropped` | red, white, black | red, red | white, black | none | `manual_review_required` |
| `TOWERS55` | `feature_colour_dropped` | yellow, black | yellow, white | black | white | `manual_review_required` |
| `TOWERS74` | `feature_colour_dropped` | white, orange | yellow, white | orange | yellow | `manual_review_required` |
| `VTCLMK01` | `feature_colour_dropped` | black | white | black | white | `manual_review_required` |
| `WIMCON11` | `feature_colour_dropped` | black | white | black | white | `manual_review_required` |
| `WNDMIL12` | `feature_colour_dropped` | black | white | black | white | `manual_review_required` |
| `WTLVGG02` | `feature_colour_dropped` | black | white | black | white | `manual_review_required` |
| `ZZZZZZ01` | `feature_colour_dropped` | red, green, white, black | yellow, red | green, white, black | yellow | `manual_review_required` |
| `BCNGEN64` | `feature_visual_order_difference` | red, white, red, white | white, red, white, red, white | none | none | `manual_review_required` |
| `BCNGEN65` | `feature_visual_order_difference` | green, white, green, white | white, green, white, green, white | none | none | `manual_review_required` |
| `BCNGEN68` | `feature_visual_order_difference` | black, yellow | yellow, black | none | none | `manual_review_required` |
| `BCNGEN69` | `feature_visual_order_difference` | yellow, black | black, yellow | none | none | `manual_review_required` |
| `BCNISD21` | `feature_visual_order_difference` | red | red, red | none | none | `manual_review_required` |
| `BCNSTK77` | `feature_visual_order_difference` | white, green, white | white, green, white, green, white | none | none | `manual_review_required` |
| `BCNTOW05` | `feature_visual_order_difference` | white | white, white | none | none | `manual_review_required` |
| `BCNTOW63` | `feature_visual_order_difference` | white, red | white, red, white, red, white | none | none | `manual_review_required` |
| `BCNTOW64` | `feature_visual_order_difference` | red, white | red, white, white | none | none | `manual_review_required` |
| `BCNTOW65` | `feature_visual_order_difference` | green, white | green, white, white | none | none | `manual_review_required` |
| `BCNTOW66` | `feature_visual_order_difference` | white, green | white, green, white, green, white | none | none | `manual_review_required` |
| `BCNTOW85` | `feature_visual_order_difference` | green, white | green, white, white | none | none | `manual_review_required` |
| `BCNTOW86` | `feature_visual_order_difference` | white, black | white, black, white | none | none | `manual_review_required` |
| `BCNTOW87` | `feature_visual_order_difference` | black, white, black | black, white, black, white | none | none | `manual_review_required` |
| `BCNTOW88` | `feature_visual_order_difference` | black, white | black, white, white | none | none | `manual_review_required` |
| `BCNTOW91` | `feature_visual_order_difference` | white | white, white | none | none | `manual_review_required` |
| `BOYCON81` | `feature_visual_order_difference` | blue, red, white, blue | blue, red, white, blue, blue | none | none | `manual_review_required` |
| `BOYISD12` | `feature_visual_order_difference` | red | red, red | none | none | `manual_review_required` |
| `BOYPIL78` | `feature_visual_order_difference` | red, white | red, white, red, white, white, red, white, red, red, white, red, white, white, red, white, red, red, white, red, white | none | none | `manual_review_required` |
| `BOYSPR04` | `feature_visual_order_difference` | white, orange | white, white, orange | none | none | `manual_review_required` |
| `BOYSPR05` | `feature_visual_order_difference` | white | white, white | none | none | `manual_review_required` |
| `BOYSPR65` | `feature_visual_order_difference` | white, red | white, white, red | none | none | `manual_review_required` |
| `BUIREL13` | `feature_visual_order_difference` | black | black, black, black | none | none | `manual_review_required` |
| `BUIREL14` | `feature_visual_order_difference` | black | black, black | none | none | `manual_review_required` |
| `BUIREL15` | `feature_visual_order_difference` | black | black, black, black, black | none | none | `manual_review_required` |
| `BUNSTA01` | `feature_visual_order_difference` | white, black | black, white | none | none | `manual_review_required` |
| `BUNSTA03` | `feature_visual_order_difference` | black | black, black, black | none | none | `manual_review_required` |
| `CAIRNS11` | `feature_visual_order_difference` | black | black, black, black, black | none | none | `manual_review_required` |
| `CHIMNY11` | `feature_visual_order_difference` | black | black, black, black | none | none | `manual_review_required` |
| `CROSSX02` | `feature_visual_order_difference` | brown | brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown | none | none | `manual_review_required` |
| `DANGER51` | `feature_visual_order_difference` | black | black, black, black, black, black, black, black, black | none | none | `manual_review_required` |
| `DANGER52` | `feature_visual_order_difference` | black | black, black, black, black, black, black, black, black, black | none | none | `manual_review_required` |
| `DIRBOYB1` | `feature_visual_order_difference` | red, green | green, red | none | none | `manual_review_required` |
| `DISMAR06` | `feature_visual_order_difference` | black | black, black | none | none | `manual_review_required` |
| `DOMES011` | `feature_visual_order_difference` | black | black, black | none | none | `manual_review_required` |
| `DSHAER11` | `feature_visual_order_difference` | black | black, black | none | none | `manual_review_required` |
| `FLASTK11` | `feature_visual_order_difference` | black | black, black, black | none | none | `manual_review_required` |
| `FRYARE52` | `feature_visual_order_difference` | black | black, black, black, black | none | none | `manual_review_required` |
| `MONUMT12` | `feature_visual_order_difference` | black | black, black, black | none | none | `manual_review_required` |
| `MORFAC04` | `feature_visual_order_difference` | black | black, black, black | none | none | `manual_review_required` |
| `NOTBRD11` | `feature_visual_order_difference` | black | black, black | none | none | `manual_review_required` |
| `OBSTRN03` | `feature_visual_order_difference` | black | black, black | none | none | `manual_review_required` |
| `PRDINS02` | `feature_visual_order_difference` | brown | brown, brown | none | none | `manual_review_required` |
| `PRICKE03` | `feature_visual_order_difference` | black | black, black, black | none | none | `manual_review_required` |
| `PRICKE04` | `feature_visual_order_difference` | black | black, black, black | none | none | `manual_review_required` |
| `RFNERY11` | `feature_visual_order_difference` | black | black, black, black | none | none | `manual_review_required` |
| `TERMNL02` | `feature_visual_order_difference` | black | black, black, black | none | none | `manual_review_required` |
| `TERMNL10` | `feature_visual_order_difference` | black | black, black, black | none | none | `manual_review_required` |
| `TERMNL11` | `feature_visual_order_difference` | black | black, black | none | none | `manual_review_required` |
| `TNKFRM11` | `feature_visual_order_difference` | black | black, black, black, black | none | none | `manual_review_required` |
| `TOPMAR87` | `feature_visual_order_difference` | black | black, black | none | none | `manual_review_required` |
| `TOPMAR88` | `feature_visual_order_difference` | black | black, black | none | none | `manual_review_required` |
| `TOPSHP16` | `feature_visual_order_difference` | red, white | red, white, red | none | none | `manual_review_required` |
| `TOPSHP17` | `feature_visual_order_difference` | orange, black, orange | orange, black, orange, black | none | none | `manual_review_required` |
| `TOPSHP19` | `feature_visual_order_difference` | red, yellow | red, yellow, red | none | none | `manual_review_required` |
| `TOPSHP25` | `feature_visual_order_difference` | white, orange | white, orange, orange | none | none | `manual_review_required` |
| `TOPSHP31` | `feature_visual_order_difference` | orange, white | orange, white, white | none | none | `manual_review_required` |
| `TOPSHP38` | `feature_visual_order_difference` | orange, white | orange, white, white, orange | none | none | `manual_review_required` |
| `TOPSHP40` | `feature_visual_order_difference` | white, black | white, black, white | none | none | `manual_review_required` |
| `TOPSHP47` | `feature_visual_order_difference` | red, red | red | none | none | `manual_review_required` |
| `TOPSHP48` | `feature_visual_order_difference` | green, green | green | none | none | `manual_review_required` |
| `TOPSHP64` | `feature_visual_order_difference` | white, green, white | white, green, white, green | none | none | `manual_review_required` |
| `TOPSHP70` | `feature_visual_order_difference` | yellow, yellow | yellow | none | none | `manual_review_required` |
| `TOPSHP72` | `feature_visual_order_difference` | white, red, white | white, red, white, red | none | none | `manual_review_required` |
| `TOPSHP73` | `feature_visual_order_difference` | white, black, white | white, black, white, black, black | none | none | `manual_review_required` |
| `TOPSHP81` | `feature_visual_order_difference` | orange, black | orange, black, black | none | none | `manual_review_required` |
| `TOPSHP83` | `feature_visual_order_difference` | white, black | white, black, white, black | none | none | `manual_review_required` |
| `TOPSHPD5` | `feature_visual_order_difference` | red, white, black | red, white, black, white | none | none | `manual_review_required` |
| `TOPSHPS1` | `feature_visual_order_difference` | white, red, white | red, white, red | none | none | `manual_review_required` |
| `TOPSHPT8` | `feature_visual_order_difference` | white, black, white | white, black, white, black | none | none | `manual_review_required` |
| `TOPSHPU1` | `feature_visual_order_difference` | green, green | green | none | none | `manual_review_required` |
| `TOWERS05` | `feature_visual_order_difference` | white | white, white | none | none | `manual_review_required` |
| `TOWERS48` | `feature_visual_order_difference` | white, green | white, green, white | none | none | `manual_review_required` |
| `TOWERS49` | `feature_visual_order_difference` | black, white | black, white, white | none | none | `manual_review_required` |
| `TOWERS50` | `feature_visual_order_difference` | white, red | white, red, white | none | none | `manual_review_required` |
| `TOWERS51` | `feature_visual_order_difference` | white, black, white | white, black, white, white | none | none | `manual_review_required` |
| `TOWERS52` | `feature_visual_order_difference` | white, red | white, red, white | none | none | `manual_review_required` |
| `TOWERS53` | `feature_visual_order_difference` | red, white | red, white, white | none | none | `manual_review_required` |
| `TOWERS54` | `feature_visual_order_difference` | orange, white | white, orange, white | none | none | `manual_review_required` |
| `TOWERS56` | `feature_visual_order_difference` | orange, white | orange, white, orange, white, white, orange, white, orange, orange, white, orange, white, white, orange, white, orange, orange, white, orange, white, white | none | none | `manual_review_required` |
| `TOWERS58` | `feature_visual_order_difference` | white, brown | white, brown, white | none | none | `manual_review_required` |
| `TOWERS66` | `feature_visual_order_difference` | white, grey, white | white, grey, white, white | none | none | `manual_review_required` |
| `TOWERS67` | `feature_visual_order_difference` | white, yellow, white | white, yellow, white, white | none | none | `manual_review_required` |
| `TOWERS72` | `feature_visual_order_difference` | white, red, white | white, red, white, white | none | none | `manual_review_required` |
| `TOWERS76` | `feature_visual_order_difference` | white, blue | white, blue, white | none | none | `manual_review_required` |
| `TOWERS77` | `feature_visual_order_difference` | white, green | white, green, white | none | none | `manual_review_required` |
| `TOWERS78` | `feature_visual_order_difference` | white, red | white, red, white | none | none | `manual_review_required` |
| `TOWERS79` | `feature_visual_order_difference` | white, black | white, black, white | none | none | `manual_review_required` |
| `TOWERS81` | `feature_visual_order_difference` | green, white, black | green, white, black, white | none | none | `manual_review_required` |
| `TOWERS83` | `feature_visual_order_difference` | black, white | black, white, white | none | none | `manual_review_required` |
| `TOWERS85` | `feature_visual_order_difference` | red, white, red, white | red, white, red, white, white | none | none | `manual_review_required` |
| `TOWERS87` | `feature_visual_order_difference` | white, grey | white, grey, white | none | none | `manual_review_required` |
| `TOWERS88` | `feature_visual_order_difference` | white, black | white, black, white | none | none | `manual_review_required` |
| `TOWERS91` | `feature_visual_order_difference` | grey, white | grey, white, white | none | none | `manual_review_required` |
| `TOWERS92` | `feature_visual_order_difference` | black, white, black | black, white, black, white | none | none | `manual_review_required` |
| `TOWERS93` | `feature_visual_order_difference` | black, white, grey | black, white, grey, white | none | none | `manual_review_required` |
| `TOWERS94` | `feature_visual_order_difference` | black, white | black, white, white, white | none | none | `manual_review_required` |
| `TOWERS95` | `feature_visual_order_difference` | white, red | white, red, white | none | none | `manual_review_required` |
| `TOWERS96` | `feature_visual_order_difference` | white, black | white, black, white | none | none | `manual_review_required` |
| `TOWERS97` | `feature_visual_order_difference` | white, black | white, black, black, white | none | none | `manual_review_required` |
| `TOWERS98` | `feature_visual_order_difference` | red, white | red, white, red, white, white, red, white, red, red, white, red, white, white, red, white, red, red, white, red, white, white | none | none | `manual_review_required` |
| `TOWERS99` | `feature_visual_order_difference` | black, white | black, white, black, white, white, black, white, black, black, white, black, white, white, black, white, black, black, white, black, white, white | none | none | `manual_review_required` |
| `UWTROC04` | `feature_visual_order_difference` | black | black, black | none | none | `manual_review_required` |
| `WNDFRM61` | `feature_visual_order_difference` | black | black, black, black | none | none | `manual_review_required` |
| `WRECKS04` | `feature_visual_order_difference` | black | black, black | none | none | `manual_review_required` |
| `boyspp50` | `feature_visual_order_difference` | yellow | yellow, yellow | none | none | `manual_review_required` |
| `BCNCON81` | `pattern_orientation_conflict` | blue, red, white, blue | blue, red, white, blue | none | none | `manual_review_required` |
| `TOPSHP05` | `pattern_orientation_conflict` | orange, black | orange, black | none | none | `manual_review_required` |
| `TOPSHP13` | `pattern_orientation_conflict` | orange, black | orange, black | none | none | `manual_review_required` |
| `TOPSHP51` | `pattern_orientation_conflict` | white, black, white | white, black, white | none | none | `manual_review_required` |
| `TOPSHP58` | `pattern_orientation_conflict` | red, white | red, white | none | none | `manual_review_required` |
| `TOPSHP61` | `pattern_orientation_conflict` | orange, white | orange, white | none | none | `manual_review_required` |
| `TOPSHP62` | `pattern_orientation_conflict` | white, orange | white, orange | none | none | `manual_review_required` |
| `TOPSHP65` | `pattern_orientation_conflict` | white, red | white, red | none | none | `manual_review_required` |
| `TOPSHP74` | `pattern_orientation_conflict` | red, white, white, red | red, white, white, red | none | none | `manual_review_required` |
| `TOPSHP76` | `pattern_orientation_conflict` | white, white, red, white | white, white, red, white | none | none | `manual_review_required` |
| `TOPSHP77` | `pattern_orientation_conflict` | white, white, black, white | white, white, black, white | none | none | `manual_review_required` |
| `TOPSHP78` | `pattern_orientation_conflict` | white, white, yellow, white | white, white, yellow, white | none | none | `manual_review_required` |
| `TOPSHP84` | `pattern_orientation_conflict` | orange, white | orange, white | none | none | `manual_review_required` |
| `TOPSHP85` | `pattern_orientation_conflict` | red, white | red, white | none | none | `manual_review_required` |
| `TOPSHP87` | `pattern_orientation_conflict` | white, red | white, red | none | none | `manual_review_required` |
| `TOPSHP88` | `pattern_orientation_conflict` | red, white | red, white | none | none | `manual_review_required` |
| `TOPSHP90` | `pattern_orientation_conflict` | red, white, red | red, white, red | none | none | `manual_review_required` |
| `TOPSHP91` | `pattern_orientation_conflict` | red, white | red, white | none | none | `manual_review_required` |
| `TOPSHP92` | `pattern_orientation_conflict` | white, red | white, red | none | none | `manual_review_required` |
| `TOPSHP93` | `pattern_orientation_conflict` | white, green | white, green | none | none | `manual_review_required` |
| `TOPSHP94` | `pattern_orientation_conflict` | white, red, white | white, red, white | none | none | `manual_review_required` |
| `TOPSHP96` | `pattern_orientation_conflict` | red, white, red, yellow | red, white, red, yellow | none | none | `manual_review_required` |
| `TOPSHP97` | `pattern_orientation_conflict` | yellow, black, yellow | yellow, black, yellow | none | none | `manual_review_required` |
| `TOPSHP98` | `pattern_orientation_conflict` | red, black | red, black | none | none | `manual_review_required` |
| `TOPSHP99` | `pattern_orientation_conflict` | white, black | white, black | none | none | `manual_review_required` |
| `TOPSHPA0` | `pattern_orientation_conflict` | red, black, red | red, black, red | none | none | `manual_review_required` |
| `TOPSHPA1` | `pattern_orientation_conflict` | black, white, black | black, white, black | none | none | `manual_review_required` |
| `TOPSHPA2` | `pattern_orientation_conflict` | red, green | red, green | none | none | `manual_review_required` |
| `TOPSHPA3` | `pattern_orientation_conflict` | red, green, red | red, green, red | none | none | `manual_review_required` |
| `TOPSHPA5` | `pattern_orientation_conflict` | white, black, white | white, black, white | none | none | `manual_review_required` |
| `TOPSHPA7` | `pattern_orientation_conflict` | green, red, green | green, red, green | none | none | `manual_review_required` |
| `TOPSHPA8` | `pattern_orientation_conflict` | green, black | green, black | none | none | `manual_review_required` |
| `TOPSHPA9` | `pattern_orientation_conflict` | white, red | white, red | none | none | `manual_review_required` |
| `TOPSHPB0` | `pattern_orientation_conflict` | red, white | red, white | none | none | `manual_review_required` |
| `TOPSHPI3` | `pattern_orientation_conflict` | white, red | white, red | none | none | `manual_review_required` |
| `TOPSHPT2` | `pattern_orientation_conflict` | red, white | red, white | none | none | `manual_review_required` |
| `TOPSHPU2` | `pattern_orientation_conflict` | white, red | white, red | none | none | `manual_review_required` |
| `BCNGEN70` | `visual_colour_extra` | black, yellow, black | white, black, yellow, black | none | white | `manual_review_required` |
| `BCNGEN71` | `visual_colour_extra` | yellow, black, yellow | white, yellow, black, yellow | none | white | `manual_review_required` |
| `BCNGEN76` | `visual_colour_extra` | black, red, black | white, black, red, black | none | white | `manual_review_required` |
| `BCNLAT50` | `visual_colour_extra` | black | white, black | none | white | `manual_review_required` |
| `BCNSAW13` | `visual_colour_extra` | black | black, blue | none | blue | `manual_review_required` |
| `BCNSAW21` | `visual_colour_extra` | black | black, blue | none | blue | `manual_review_required` |
| `BCNSTK03` | `visual_colour_extra` | black | white, black | none | white | `manual_review_required` |
| `BCNSTK79` | `visual_colour_extra` | red, green, red | white, red, green, red | none | white | `manual_review_required` |
| `BCNSTK80` | `visual_colour_extra` | green, red, green | white, green, red, green | none | white | `manual_review_required` |
| `BCNTOW01` | `visual_colour_extra` | black | black, white | none | white | `manual_review_required` |
| `BCNTOW60` | `visual_colour_extra` | red | red, white | none | white | `manual_review_required` |
| `BCNTOW61` | `visual_colour_extra` | green | green, white | none | white | `manual_review_required` |
| `BCNTOW62` | `visual_colour_extra` | yellow | yellow, white | none | white | `manual_review_required` |
| `BCNTOW68` | `visual_colour_extra` | black, yellow | black, yellow, white | none | white | `manual_review_required` |
| `BCNTOW69` | `visual_colour_extra` | yellow, black | yellow, black, white | none | white | `manual_review_required` |
| `BCNTOW70` | `visual_colour_extra` | black, yellow, black | black, yellow, black, white | none | white | `manual_review_required` |
| `BCNTOW71` | `visual_colour_extra` | yellow, black, yellow | yellow, black, yellow, white | none | white | `manual_review_required` |
| `BCNTOW74` | `visual_colour_extra` | red, green, red | red, green, red, white | none | white | `manual_review_required` |
| `BCNTOW76` | `visual_colour_extra` | black, red, black | black, red, black, white | none | white | `manual_review_required` |
| `BCNTOW89` | `visual_colour_extra` | black | black, white | none | white | `manual_review_required` |
| `BCNTOW90` | `visual_colour_extra` | brown | brown, white | none | white | `manual_review_required` |
| `BORDER01` | `visual_colour_extra` | red | red, white | none | white | `manual_review_required` |
| `BOYBAR60` | `visual_colour_extra` | red | red, black, black, white | none | black, white | `manual_review_required` |
| `BOYBAR61` | `visual_colour_extra` | green | green, black, black, white | none | black, white | `manual_review_required` |
| `BOYBAR62` | `visual_colour_extra` | yellow | yellow, black, black, white | none | black, white | `manual_review_required` |
| `BOYCAN01` | `visual_colour_extra` | black | white, black, white | none | white | `manual_review_required` |
| `BOYCAN60` | `visual_colour_extra` | red | red, black, white | none | black, white | `manual_review_required` |
| `BOYCAN61` | `visual_colour_extra` | green | green, black, white | none | black, white | `manual_review_required` |
| `BOYCAN62` | `visual_colour_extra` | green, black | green, black, black, white | none | white | `manual_review_required` |
| `BOYCAN63` | `visual_colour_extra` | yellow | yellow, black, white | none | black, white | `manual_review_required` |
| `BOYCAN64` | `visual_colour_extra` | black | black, black, white | none | white | `manual_review_required` |
| `BOYCAN65` | `visual_colour_extra` | white | white, black, white | none | black | `manual_review_required` |
| `BOYCAN68` | `visual_colour_extra` | black, yellow | black, yellow, black, white | none | white | `manual_review_required` |
| `BOYCAN69` | `visual_colour_extra` | yellow, black | yellow, black, black, white | none | white | `manual_review_required` |
| `BOYCAN70` | `visual_colour_extra` | black, yellow, black | black, yellow, black, black, white | none | white | `manual_review_required` |
| `BOYCAN71` | `visual_colour_extra` | yellow, black, yellow | yellow, black, yellow, black, white | none | white | `manual_review_required` |
| `BOYCAN72` | `visual_colour_extra` | red, green, red | red, green, red, black, white | none | black, white | `manual_review_required` |
| `BOYCAN73` | `visual_colour_extra` | green, red, green | green, red, green, black, white | none | black, white | `manual_review_required` |
| `BOYCAN74` | `visual_colour_extra` | red, white, red, white, red | red, white, red, white, red, black, white | none | black | `manual_review_required` |
| `BOYCAN75` | `visual_colour_extra` | red, green | red, green, black, white | none | black, white | `manual_review_required` |
| `BOYCAN76` | `visual_colour_extra` | black, red, black | black, red, black, black, white | none | white | `manual_review_required` |
| `BOYCAN77` | `visual_colour_extra` | white, orange | white, orange, black, white | none | black | `manual_review_required` |
| `BOYCAN78` | `visual_colour_extra` | white, orange, white | white, orange, white, black, white | none | black | `manual_review_required` |
| `BOYCAN79` | `visual_colour_extra` | orange | orange, black, white | none | black, white | `manual_review_required` |
| `BOYCAN80` | `visual_colour_extra` | red, white | red, white, black, white | none | black | `manual_review_required` |
| `BOYCAN81` | `visual_colour_extra` | orange, white | orange, white, black, white | none | black | `manual_review_required` |
| `BOYCAN82` | `visual_colour_extra` | red, white, red, white, red | red, white, red, white, red, black, white | none | black | `manual_review_required` |
| `BOYCAN83` | `visual_colour_extra` | red, white, red, white | red, white, red, white, black, white | none | black | `manual_review_required` |
| `BOYSAW12` | `visual_colour_extra` | red | red, white | none | white | `manual_review_required` |
| `BOYSPR02` | `visual_colour_extra` | green | white, green | none | white | `manual_review_required` |
| `BOYSPR03` | `visual_colour_extra` | red | white, red | none | white | `manual_review_required` |
| `BOYSPR60` | `visual_colour_extra` | red | white, red | none | white | `manual_review_required` |
| `BOYSPR61` | `visual_colour_extra` | green | white, green | none | white | `manual_review_required` |
| `BOYSPR62` | `visual_colour_extra` | yellow | white, yellow | none | white | `manual_review_required` |
| `BOYSPR68` | `visual_colour_extra` | black, yellow | white, black, yellow | none | white | `manual_review_required` |
| `BOYSPR69` | `visual_colour_extra` | yellow, black | white, yellow, black | none | white | `manual_review_required` |
| `CGUSTA02` | `visual_colour_extra` | white | white, magenta, magenta | none | magenta | `manual_review_required` |
| `HGWTMK01` | `visual_colour_extra` | black | white, black | none | white | `manual_review_required` |
| `HRBFAC14` | `visual_colour_extra` | black | grey, black | none | grey | `manual_review_required` |
| `HRBFAC15` | `visual_colour_extra` | black | grey, black | none | grey | `manual_review_required` |
| `LITFLT01` | `visual_colour_extra` | black | black, white | none | white | `manual_review_required` |
| `LITFLT10` | `visual_colour_extra` | red, white | white, red, red, yellow | none | yellow | `manual_review_required` |
| `LITFLT61` | `visual_colour_extra` | green | green, yellow | none | yellow | `manual_review_required` |
| `LITVES01` | `visual_colour_extra` | black | black, white | none | white | `manual_review_required` |
| `LITVES60` | `visual_colour_extra` | red | red, yellow | none | yellow | `manual_review_required` |
| `LITVES61` | `visual_colour_extra` | green | green, yellow | none | yellow | `manual_review_required` |
| `SSLOCK01` | `visual_colour_extra` | black | white, black, black | none | white | `manual_review_required` |
| `TERMNL07` | `visual_colour_extra` | black | white, black | none | white | `manual_review_required` |
| `TERMNL12` | `visual_colour_extra` | black | white, black | none | white | `manual_review_required` |
| `TOPMA113` | `visual_colour_extra` | yellow | black, yellow | none | black | `manual_review_required` |
| `TOPSHP09` | `visual_colour_extra` | red, red, green | red, red, green, black | none | black | `manual_review_required` |
| `TOPSHP15` | `visual_colour_extra` | red, red, yellow | red, red, yellow, black | none | black | `manual_review_required` |
| `TOPSHP30` | `visual_colour_extra` | green, green, yellow | green, white, yellow | none | white | `manual_review_required` |
| `TOPSHP37` | `visual_colour_extra` | black, black | black, white, black | none | white | `manual_review_required` |
| `TOPSHP41` | `visual_colour_extra` | orange, orange | orange, white, orange | none | white | `manual_review_required` |
| `TOPSHP43` | `visual_colour_extra` | green, red, green | green, red, green, white, green | none | white | `manual_review_required` |
| `TOPSHP44` | `visual_colour_extra` | yellow, yellow | yellow, white, yellow | none | white | `manual_review_required` |
| `TOPSHP89` | `visual_colour_extra` | red, white, red | red, white, red, black | none | black | `manual_review_required` |
| `TOPSHPD1` | `visual_colour_extra` | orange | orange, white | none | white | `manual_review_required` |
| `TOPSHPD2` | `visual_colour_extra` | green, green | green, white | none | white | `manual_review_required` |
| `TOPSHPD3` | `visual_colour_extra` | red | red, white | none | white | `manual_review_required` |
| `TOPSHPP2` | `visual_colour_extra` | yellow | black, yellow | none | black | `manual_review_required` |
| `TOWERS03` | `visual_colour_extra` | black | black, white | none | white | `manual_review_required` |
| `TOWERS12` | `visual_colour_extra` | black | black, white | none | white | `manual_review_required` |
| `TOWERS15` | `visual_colour_extra` | black | black, white | none | white | `manual_review_required` |
| `TOWERS57` | `visual_colour_extra` | black, red | black, red, white | none | white | `manual_review_required` |
| `TOWERS59` | `visual_colour_extra` | brown | brown, white | none | white | `manual_review_required` |
| `TOWERS60` | `visual_colour_extra` | red | red, white | none | white | `manual_review_required` |
| `TOWERS61` | `visual_colour_extra` | green | green, white | none | white | `manual_review_required` |
| `TOWERS62` | `visual_colour_extra` | yellow | yellow, white | none | white | `manual_review_required` |
| `TOWERS63` | `visual_colour_extra` | black | black, white | none | white | `manual_review_required` |
| `TOWERS64` | `visual_colour_extra` | orange | orange, white | none | white | `manual_review_required` |
| `TOWERS65` | `visual_colour_extra` | grey | grey, white | none | white | `manual_review_required` |
| `TOWERS68` | `visual_colour_extra` | black, yellow | black, yellow, white | none | white | `manual_review_required` |
| `TOWERS69` | `visual_colour_extra` | yellow, black | yellow, black, white | none | white | `manual_review_required` |
| `TOWERS70` | `visual_colour_extra` | black, yellow, black | black, yellow, black, white | none | white | `manual_review_required` |
| `TOWERS71` | `visual_colour_extra` | yellow, black, yellow | yellow, black, yellow, white | none | white | `manual_review_required` |
| `TOWERS73` | `visual_colour_extra` | black, red, black | black, red, black, white | none | white | `manual_review_required` |
| `TOWERS75` | `visual_colour_extra` | black, orange | black, orange, white | none | white | `manual_review_required` |
| `TOWERS80` | `visual_colour_extra` | black, red, black | black, red, black, white | none | white | `manual_review_required` |
| `TOWERS82` | `visual_colour_extra` | red, grey | red, grey, white | none | white | `manual_review_required` |
| `TOWERS84` | `visual_colour_extra` | black, grey | black, grey, white | none | white | `manual_review_required` |
| `TOWERS86` | `visual_colour_extra` | grey | grey, white | none | white | `manual_review_required` |
| `TOWERS89` | `visual_colour_extra` | green, grey | grey, green, grey, green, white | none | white | `manual_review_required` |
| `TOWERS90` | `visual_colour_extra` | grey, red | red, grey, red, grey, white | none | white | `manual_review_required` |
| `UWTROC03` | `visual_colour_extra` | black | blue, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black | none | blue | `manual_review_required` |
| `WRECKS05` | `visual_colour_extra` | black | blue, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black | none | blue | `manual_review_required` |
| `WTLVGG01` | `visual_colour_extra` | black | white, black | none | white | `manual_review_required` |
