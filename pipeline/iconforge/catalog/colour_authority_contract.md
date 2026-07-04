# Colour Authority Contract

DB-side contract separating feature colour predicates from generated visual colour recipes.

- schema: `helm.iconforge.colour_authority_contract.v1`
- rows: `824`
- runtime_blocker_rows: `0`

## Status Counts

| Status | Count |
| --- | ---: |
| `aligned` | 220 |
| `feature_colour_dropped` | 129 |
| `feature_empty_visual_defined` | 120 |
| `feature_visual_order_difference` | 106 |
| `not_colour_bearing` | 141 |
| `visual_colour_extra` | 108 |

## Policy

- Feature colours remain the S-57/S-52 semantic predicates.
- Visual colours are read from the selected generated Helm SVG/recipe.
- S-101 witness images are not colour-authoritative by default.
- Unresolved or missing colour authority fails closed.

## Feature/Visual Colour Deltas

| Asset | Status | Feature colours | Visual colours | Missing feature colours | Extra visual colours | Authority |
| --- | --- | --- | --- | --- | --- | --- |
| `ADDMRK01` | `feature_colour_dropped` | white, black | white | black | none | `generated_visual_recipe` |
| `ADDMRK02` | `feature_colour_dropped` | white, black | white | black | none | `generated_visual_recipe` |
| `ADDMRK05` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `BCNGEN01` | `feature_colour_dropped` | black | blue | black | blue | `generated_visual_recipe` |
| `BCNGEN03` | `feature_colour_dropped` | black | blue, magenta | black | blue, magenta | `generated_visual_recipe` |
| `BCNLAT15` | `feature_colour_dropped` | red, green, red | white, red | green | white | `generated_visual_recipe` |
| `BCNLAT16` | `feature_colour_dropped` | green, red, green | white, green | red | white | `generated_visual_recipe` |
| `BCNLAT21` | `feature_colour_dropped` | red, green, red | white, red | green | white | `generated_visual_recipe` |
| `BCNLAT22` | `feature_colour_dropped` | green, red, green | white, green | red | white | `generated_visual_recipe` |
| `BCNLAT23` | `feature_colour_dropped` | red, green, black | white, red, green | black | white | `generated_visual_recipe` |
| `BCNLTC01` | `feature_colour_dropped` | black | white | black | white | `generated_visual_recipe` |
| `BOYBAR01` | `feature_colour_dropped` | red, black | white, black, black, white | red | white | `generated_visual_recipe` |
| `BOYINB01` | `feature_colour_dropped` | black | white, white | black | white | `generated_visual_recipe` |
| `BOYMOR01` | `feature_colour_dropped` | black | white | black | white | `generated_visual_recipe` |
| `BOYMOR03` | `feature_colour_dropped` | green, black | white | green, black | white | `generated_visual_recipe` |
| `BUNSTA02` | `feature_colour_dropped` | black | white | black | white | `generated_visual_recipe` |
| `FERYRT02` | `feature_colour_dropped` | black | grey, grey, grey | black | grey | `generated_visual_recipe` |
| `HRBFAC10` | `feature_colour_dropped` | black | grey | black | grey | `generated_visual_recipe` |
| `HRBFAC11` | `feature_colour_dropped` | black | grey | black | grey | `generated_visual_recipe` |
| `HRBFAC12` | `feature_colour_dropped` | black | grey | black | grey | `generated_visual_recipe` |
| `HRBFAC13` | `feature_colour_dropped` | black | grey | black | grey | `generated_visual_recipe` |
| `HRBFAC16` | `feature_colour_dropped` | black | grey | black | grey | `generated_visual_recipe` |
| `HRBFAC17` | `feature_colour_dropped` | black | grey | black | grey | `generated_visual_recipe` |
| `HRBFAC18` | `feature_colour_dropped` | black | grey | black | grey | `generated_visual_recipe` |
| `LOWACC41` | `feature_colour_dropped` | black | grey | black | grey | `generated_visual_recipe` |
| `MARSHES1` | `feature_colour_dropped` | brown | yellow, yellow, yellow, yellow, yellow, yellow, yellow, yellow, yellow | brown | yellow | `generated_visual_recipe` |
| `MORFAC03` | `feature_colour_dropped` | black | brown | black | brown | `generated_visual_recipe` |
| `MSTCON14` | `feature_colour_dropped` | black | white | black | white | `generated_visual_recipe` |
| `NMKINF01` | `feature_colour_dropped` | green, white, black | green | white, black | none | `generated_visual_recipe` |
| `NMKINF02` | `feature_colour_dropped` | white, black | blue, white | black | blue | `generated_visual_recipe` |
| `NMKINF03` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF04` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF05` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF06` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF19` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF20` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF21` | `feature_colour_dropped` | white, black | blue, white, white | black | blue | `generated_visual_recipe` |
| `NMKINF22` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF23` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF24` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF25` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF26` | `feature_colour_dropped` | white | blue | white | blue | `generated_visual_recipe` |
| `NMKINF27` | `feature_colour_dropped` | white | blue | white | blue | `generated_visual_recipe` |
| `NMKINF28` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF29` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF38` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF40` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF43` | `feature_colour_dropped` | white, black | blue, white | black | blue | `generated_visual_recipe` |
| `NMKINF44` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF45` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF46` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF47` | `feature_colour_dropped` | white, black | blue, white | black | blue | `generated_visual_recipe` |
| `NMKINF48` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF49` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF50` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKINF53` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKPRH02` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NMKPRH06` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NMKPRH07` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NMKPRH08` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NMKPRH10` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NMKPRH11` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NMKPRH12` | `feature_colour_dropped` | red, white, black | red, white | black | none | `generated_visual_recipe` |
| `NMKPRH13` | `feature_colour_dropped` | red, white, black | white, red | black | none | `generated_visual_recipe` |
| `NMKPRH14` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NMKRCD01` | `feature_colour_dropped` | black | yellow | black | yellow | `generated_visual_recipe` |
| `NMKRCD02` | `feature_colour_dropped` | black | yellow, yellow | black | yellow | `generated_visual_recipe` |
| `NMKRCD03` | `feature_colour_dropped` | green, white, black | green, white | black | none | `generated_visual_recipe` |
| `NMKRCD04` | `feature_colour_dropped` | green, white, black | green, white | black | none | `generated_visual_recipe` |
| `NMKRCD05` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKRCD06` | `feature_colour_dropped` | white, black | blue | white, black | blue | `generated_visual_recipe` |
| `NMKREG01` | `feature_colour_dropped` | red, white, black | red, white | black | none | `generated_visual_recipe` |
| `NMKREG02` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NMKREG03` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NMKREG10` | `feature_colour_dropped` | red, white, black | red, white | black | none | `generated_visual_recipe` |
| `NMKREG11` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NMKREG12` | `feature_colour_dropped` | red, white, black | red, white | black | none | `generated_visual_recipe` |
| `NMKREG13` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NMKREG14` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NMKREG15` | `feature_colour_dropped` | red, white, black | red, white | black | none | `generated_visual_recipe` |
| `NMKREG16` | `feature_colour_dropped` | red, white, black | red, white | black | none | `generated_visual_recipe` |
| `NMKREG17` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NMKREG19` | `feature_colour_dropped` | red, white, black | red, white | black | none | `generated_visual_recipe` |
| `NMKREG20` | `feature_colour_dropped` | red, white, black | red, white | black | none | `generated_visual_recipe` |
| `NOTMRK01` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `NOTMRK02` | `feature_colour_dropped` | red, white, black | red, white | black | none | `generated_visual_recipe` |
| `NOTMRK03` | `feature_colour_dropped` | black | blue | black | blue | `generated_visual_recipe` |
| `OBSTRN01` | `feature_colour_dropped` | black | blue | black | blue | `generated_visual_recipe` |
| `PIER0001` | `feature_colour_dropped` | black | blue, blue | black | blue | `generated_visual_recipe` |
| `PILBOP02` | `feature_colour_dropped` | black | magenta, magenta | black | magenta | `generated_visual_recipe` |
| `RASCAN11` | `feature_colour_dropped` | black | white | black | white | `generated_visual_recipe` |
| `SISTAT02` | `feature_colour_dropped` | white | black | white | black | `generated_visual_recipe` |
| `SSENTR01` | `feature_colour_dropped` | black | white, white | black | white | `generated_visual_recipe` |
| `SSWARS01` | `feature_colour_dropped` | black | white | black | white | `generated_visual_recipe` |
| `TERMNL01` | `feature_colour_dropped` | black | white | black | white | `generated_visual_recipe` |
| `TERMNL03` | `feature_colour_dropped` | red, black | white, red, green, yellow, red | black | white, green, yellow | `generated_visual_recipe` |
| `TERMNL09` | `feature_colour_dropped` | red, black | red | black | none | `generated_visual_recipe` |
| `TOPMA107` | `feature_colour_dropped` | white, red | white | red | none | `generated_visual_recipe` |
| `TOPMA109` | `feature_colour_dropped` | white, green | white | green | none | `generated_visual_recipe` |
| `TOPSHP00` | `feature_colour_dropped` | white, white, red | white | red | none | `generated_visual_recipe` |
| `TOPSHP33` | `feature_colour_dropped` | green, red, green | white, white | green, red | white | `generated_visual_recipe` |
| `TOPSHQ06` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ07` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ08` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ15` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ16` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ17` | `feature_colour_dropped` | white, black | white | black | none | `generated_visual_recipe` |
| `TOPSHQ18` | `feature_colour_dropped` | red, white, black | red, red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ19` | `feature_colour_dropped` | red, green, white, black | red | green, white, black | none | `generated_visual_recipe` |
| `TOPSHQ20` | `feature_colour_dropped` | white, black | white | black | none | `generated_visual_recipe` |
| `TOPSHQ21` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ22` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ23` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ24` | `feature_colour_dropped` | green, white, black | green | white, black | none | `generated_visual_recipe` |
| `TOPSHQ25` | `feature_colour_dropped` | green, white, black | green | white, black | none | `generated_visual_recipe` |
| `TOPSHQ26` | `feature_colour_dropped` | red, white, black | red, white | black | none | `generated_visual_recipe` |
| `TOPSHQ27` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ28` | `feature_colour_dropped` | red, white, black | red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ29` | `feature_colour_dropped` | red, white, black | red, red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ30` | `feature_colour_dropped` | red, white, black | red, red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ31` | `feature_colour_dropped` | red, white, black | red, red | white, black | none | `generated_visual_recipe` |
| `TOPSHQ32` | `feature_colour_dropped` | red, white, black | red, red | white, black | none | `generated_visual_recipe` |
| `TOWERS55` | `feature_colour_dropped` | yellow, black | yellow, white | black | white | `generated_visual_recipe` |
| `TOWERS74` | `feature_colour_dropped` | white, orange | yellow, white | orange | yellow | `generated_visual_recipe` |
| `VTCLMK01` | `feature_colour_dropped` | black | white | black | white | `generated_visual_recipe` |
| `WIMCON11` | `feature_colour_dropped` | black | white | black | white | `generated_visual_recipe` |
| `WNDMIL12` | `feature_colour_dropped` | black | white | black | white | `generated_visual_recipe` |
| `WTLVGG02` | `feature_colour_dropped` | black | white | black | white | `generated_visual_recipe` |
| `ZZZZZZ01` | `feature_colour_dropped` | red, green, white, black | yellow, red | green, white, black | yellow | `generated_visual_recipe` |
| `BCNGEN64` | `feature_visual_order_difference` | red, white, red, white | white, red, white, red, white | none | none | `generated_visual_recipe` |
| `BCNGEN65` | `feature_visual_order_difference` | green, white, green, white | white, green, white, green, white | none | none | `generated_visual_recipe` |
| `BCNGEN68` | `feature_visual_order_difference` | black, yellow | yellow, black | none | none | `generated_visual_recipe` |
| `BCNGEN69` | `feature_visual_order_difference` | yellow, black | black, yellow | none | none | `generated_visual_recipe` |
| `BCNISD21` | `feature_visual_order_difference` | red | red, red | none | none | `generated_visual_recipe` |
| `BCNSTK77` | `feature_visual_order_difference` | white, green, white | white, green, white, green, white | none | none | `generated_visual_recipe` |
| `BCNTOW05` | `feature_visual_order_difference` | white | white, white | none | none | `generated_visual_recipe` |
| `BCNTOW63` | `feature_visual_order_difference` | white, red | white, red, white, red, white | none | none | `generated_visual_recipe` |
| `BCNTOW64` | `feature_visual_order_difference` | red, white | red, white, white | none | none | `generated_visual_recipe` |
| `BCNTOW65` | `feature_visual_order_difference` | green, white | green, white, white | none | none | `generated_visual_recipe` |
| `BCNTOW66` | `feature_visual_order_difference` | white, green | white, green, white, green, white | none | none | `generated_visual_recipe` |
| `BCNTOW85` | `feature_visual_order_difference` | green, white | green, white, white | none | none | `generated_visual_recipe` |
| `BCNTOW86` | `feature_visual_order_difference` | white, black | white, black, white | none | none | `generated_visual_recipe` |
| `BCNTOW87` | `feature_visual_order_difference` | black, white, black | black, white, black, white | none | none | `generated_visual_recipe` |
| `BCNTOW88` | `feature_visual_order_difference` | black, white | black, white, white | none | none | `generated_visual_recipe` |
| `BCNTOW91` | `feature_visual_order_difference` | white | white, white | none | none | `generated_visual_recipe` |
| `BOYCON81` | `feature_visual_order_difference` | blue, red, white, blue | blue, red, white, blue, blue | none | none | `generated_visual_recipe` |
| `BOYISD12` | `feature_visual_order_difference` | red | red, red | none | none | `generated_visual_recipe` |
| `BOYPIL78` | `feature_visual_order_difference` | red, white | red, white, red, white, white, red, white, red, red, white, red, white, white, red, white, red, red, white, red, white | none | none | `generated_visual_recipe` |
| `BOYSPR04` | `feature_visual_order_difference` | white, orange | white, white, orange | none | none | `generated_visual_recipe` |
| `BOYSPR05` | `feature_visual_order_difference` | white | white, white | none | none | `generated_visual_recipe` |
| `BOYSPR65` | `feature_visual_order_difference` | white, red | white, white, red | none | none | `generated_visual_recipe` |
| `BUIREL13` | `feature_visual_order_difference` | black | black, black, black | none | none | `generated_visual_recipe` |
| `BUIREL14` | `feature_visual_order_difference` | black | black, black | none | none | `generated_visual_recipe` |
| `BUIREL15` | `feature_visual_order_difference` | black | black, black, black, black | none | none | `generated_visual_recipe` |
| `BUNSTA01` | `feature_visual_order_difference` | white, black | black, white | none | none | `generated_visual_recipe` |
| `BUNSTA03` | `feature_visual_order_difference` | black | black, black, black | none | none | `generated_visual_recipe` |
| `CAIRNS11` | `feature_visual_order_difference` | black | black, black, black, black | none | none | `generated_visual_recipe` |
| `CHIMNY11` | `feature_visual_order_difference` | black | black, black, black | none | none | `generated_visual_recipe` |
| `CROSSX02` | `feature_visual_order_difference` | brown | brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown, brown | none | none | `generated_visual_recipe` |
| `DANGER51` | `feature_visual_order_difference` | black | black, black, black, black, black, black, black, black | none | none | `generated_visual_recipe` |
| `DANGER52` | `feature_visual_order_difference` | black | black, black, black, black, black, black, black, black, black | none | none | `generated_visual_recipe` |
| `DIRBOYB1` | `feature_visual_order_difference` | red, green | green, red | none | none | `generated_visual_recipe` |
| `DISMAR06` | `feature_visual_order_difference` | black | black, black | none | none | `generated_visual_recipe` |
| `DOMES011` | `feature_visual_order_difference` | black | black, black | none | none | `generated_visual_recipe` |
| `DSHAER11` | `feature_visual_order_difference` | black | black, black | none | none | `generated_visual_recipe` |
| `FLASTK11` | `feature_visual_order_difference` | black | black, black, black | none | none | `generated_visual_recipe` |
| `FRYARE52` | `feature_visual_order_difference` | black | black, black, black, black | none | none | `generated_visual_recipe` |
| `MONUMT12` | `feature_visual_order_difference` | black | black, black, black | none | none | `generated_visual_recipe` |
| `MORFAC04` | `feature_visual_order_difference` | black | black, black, black | none | none | `generated_visual_recipe` |
| `NOTBRD11` | `feature_visual_order_difference` | black | black, black | none | none | `generated_visual_recipe` |
| `OBSTRN03` | `feature_visual_order_difference` | black | black, black | none | none | `generated_visual_recipe` |
| `PRDINS02` | `feature_visual_order_difference` | brown | brown, brown | none | none | `generated_visual_recipe` |
| `PRICKE03` | `feature_visual_order_difference` | black | black, black, black | none | none | `generated_visual_recipe` |
| `PRICKE04` | `feature_visual_order_difference` | black | black, black, black | none | none | `generated_visual_recipe` |
| `RFNERY11` | `feature_visual_order_difference` | black | black, black, black | none | none | `generated_visual_recipe` |
| `TERMNL02` | `feature_visual_order_difference` | black | black, black, black | none | none | `generated_visual_recipe` |
| `TERMNL10` | `feature_visual_order_difference` | black | black, black, black | none | none | `generated_visual_recipe` |
| `TERMNL11` | `feature_visual_order_difference` | black | black, black | none | none | `generated_visual_recipe` |
| `TNKFRM11` | `feature_visual_order_difference` | black | black, black, black, black | none | none | `generated_visual_recipe` |
| `TOPMAR87` | `feature_visual_order_difference` | black | black, black | none | none | `generated_visual_recipe` |
| `TOPMAR88` | `feature_visual_order_difference` | black | black, black | none | none | `generated_visual_recipe` |
| `TOPSHP16` | `feature_visual_order_difference` | red, white | red, white, red | none | none | `generated_visual_recipe` |
| `TOPSHP17` | `feature_visual_order_difference` | orange, black, orange | orange, black, orange, black | none | none | `generated_visual_recipe` |
| `TOPSHP19` | `feature_visual_order_difference` | red, yellow | red, yellow, red | none | none | `generated_visual_recipe` |
| `TOPSHP25` | `feature_visual_order_difference` | white, orange | white, orange, orange | none | none | `generated_visual_recipe` |
| `TOPSHP31` | `feature_visual_order_difference` | orange, white | orange, white, white | none | none | `generated_visual_recipe` |
| `TOPSHP38` | `feature_visual_order_difference` | orange, white | orange, white, white, orange | none | none | `generated_visual_recipe` |
| `TOPSHP40` | `feature_visual_order_difference` | white, black | white, black, white | none | none | `generated_visual_recipe` |
| `TOPSHP47` | `feature_visual_order_difference` | red, red | red | none | none | `generated_visual_recipe` |
| `TOPSHP48` | `feature_visual_order_difference` | green, green | green | none | none | `generated_visual_recipe` |
| `TOPSHP64` | `feature_visual_order_difference` | white, green, white | white, green, white, green | none | none | `generated_visual_recipe` |
| `TOPSHP70` | `feature_visual_order_difference` | yellow, yellow | yellow | none | none | `generated_visual_recipe` |
| `TOPSHP72` | `feature_visual_order_difference` | white, red, white | white, red, white, red | none | none | `generated_visual_recipe` |
| `TOPSHP73` | `feature_visual_order_difference` | white, black, white | white, black, white, black, black | none | none | `generated_visual_recipe` |
| `TOPSHP81` | `feature_visual_order_difference` | orange, black | orange, black, black | none | none | `generated_visual_recipe` |
| `TOPSHP83` | `feature_visual_order_difference` | white, black | white, black, white, black | none | none | `generated_visual_recipe` |
| `TOPSHPD5` | `feature_visual_order_difference` | red, white, black | red, white, black, white | none | none | `generated_visual_recipe` |
| `TOPSHPS1` | `feature_visual_order_difference` | white, red, white | red, white, red | none | none | `generated_visual_recipe` |
| `TOPSHPT8` | `feature_visual_order_difference` | white, black, white | white, black, white, black | none | none | `generated_visual_recipe` |
| `TOPSHPU1` | `feature_visual_order_difference` | green, green | green | none | none | `generated_visual_recipe` |
| `TOWERS05` | `feature_visual_order_difference` | white | white, white | none | none | `generated_visual_recipe` |
| `TOWERS48` | `feature_visual_order_difference` | white, green | white, green, white | none | none | `generated_visual_recipe` |
| `TOWERS49` | `feature_visual_order_difference` | black, white | black, white, white | none | none | `generated_visual_recipe` |
| `TOWERS50` | `feature_visual_order_difference` | white, red | white, red, white | none | none | `generated_visual_recipe` |
| `TOWERS51` | `feature_visual_order_difference` | white, black, white | white, black, white, white | none | none | `generated_visual_recipe` |
| `TOWERS52` | `feature_visual_order_difference` | white, red | white, red, white | none | none | `generated_visual_recipe` |
| `TOWERS53` | `feature_visual_order_difference` | red, white | red, white, white | none | none | `generated_visual_recipe` |
| `TOWERS54` | `feature_visual_order_difference` | orange, white | white, orange, white | none | none | `generated_visual_recipe` |
| `TOWERS56` | `feature_visual_order_difference` | orange, white | orange, white, orange, white, white, orange, white, orange, orange, white, orange, white, white, orange, white, orange, orange, white, orange, white, white | none | none | `generated_visual_recipe` |
| `TOWERS58` | `feature_visual_order_difference` | white, brown | white, brown, white | none | none | `generated_visual_recipe` |
| `TOWERS66` | `feature_visual_order_difference` | white, grey, white | white, grey, white, white | none | none | `generated_visual_recipe` |
| `TOWERS67` | `feature_visual_order_difference` | white, yellow, white | white, yellow, white, white | none | none | `generated_visual_recipe` |
| `TOWERS72` | `feature_visual_order_difference` | white, red, white | white, red, white, white | none | none | `generated_visual_recipe` |
| `TOWERS76` | `feature_visual_order_difference` | white, blue | white, blue, white | none | none | `generated_visual_recipe` |
| `TOWERS77` | `feature_visual_order_difference` | white, green | white, green, white | none | none | `generated_visual_recipe` |
| `TOWERS78` | `feature_visual_order_difference` | white, red | white, red, white | none | none | `generated_visual_recipe` |
| `TOWERS79` | `feature_visual_order_difference` | white, black | white, black, white | none | none | `generated_visual_recipe` |
| `TOWERS81` | `feature_visual_order_difference` | green, white, black | green, white, black, white | none | none | `generated_visual_recipe` |
| `TOWERS83` | `feature_visual_order_difference` | black, white | black, white, white | none | none | `generated_visual_recipe` |
| `TOWERS85` | `feature_visual_order_difference` | red, white, red, white | red, white, red, white, white | none | none | `generated_visual_recipe` |
| `TOWERS87` | `feature_visual_order_difference` | white, grey | white, grey, white | none | none | `generated_visual_recipe` |
| `TOWERS88` | `feature_visual_order_difference` | white, black | white, black, white | none | none | `generated_visual_recipe` |
| `TOWERS91` | `feature_visual_order_difference` | grey, white | grey, white, white | none | none | `generated_visual_recipe` |
| `TOWERS92` | `feature_visual_order_difference` | black, white, black | black, white, black, white | none | none | `generated_visual_recipe` |
| `TOWERS93` | `feature_visual_order_difference` | black, white, grey | black, white, grey, white | none | none | `generated_visual_recipe` |
| `TOWERS94` | `feature_visual_order_difference` | black, white | black, white, white, white | none | none | `generated_visual_recipe` |
| `TOWERS95` | `feature_visual_order_difference` | white, red | white, red, white | none | none | `generated_visual_recipe` |
| `TOWERS96` | `feature_visual_order_difference` | white, black | white, black, white | none | none | `generated_visual_recipe` |
| `TOWERS97` | `feature_visual_order_difference` | white, black | white, black, black, white | none | none | `generated_visual_recipe` |
| `TOWERS98` | `feature_visual_order_difference` | red, white | red, white, red, white, white, red, white, red, red, white, red, white, white, red, white, red, red, white, red, white, white | none | none | `generated_visual_recipe` |
| `TOWERS99` | `feature_visual_order_difference` | black, white | black, white, black, white, white, black, white, black, black, white, black, white, white, black, white, black, black, white, black, white, white | none | none | `generated_visual_recipe` |
| `UWTROC04` | `feature_visual_order_difference` | black | black, black | none | none | `generated_visual_recipe` |
| `WNDFRM61` | `feature_visual_order_difference` | black | black, black, black | none | none | `generated_visual_recipe` |
| `WRECKS04` | `feature_visual_order_difference` | black | black, black | none | none | `generated_visual_recipe` |
| `boyspp50` | `feature_visual_order_difference` | yellow | yellow, yellow | none | none | `generated_visual_recipe` |
| `BCNGEN70` | `visual_colour_extra` | black, yellow, black | white, black, yellow, black | none | white | `generated_visual_recipe` |
| `BCNGEN71` | `visual_colour_extra` | yellow, black, yellow | white, yellow, black, yellow | none | white | `generated_visual_recipe` |
| `BCNGEN76` | `visual_colour_extra` | black, red, black | white, black, red, black | none | white | `generated_visual_recipe` |
| `BCNLAT50` | `visual_colour_extra` | black | white, black | none | white | `generated_visual_recipe` |
| `BCNSAW13` | `visual_colour_extra` | black | black, blue | none | blue | `generated_visual_recipe` |
| `BCNSAW21` | `visual_colour_extra` | black | black, blue | none | blue | `generated_visual_recipe` |
| `BCNSTK03` | `visual_colour_extra` | black | white, black | none | white | `generated_visual_recipe` |
| `BCNSTK79` | `visual_colour_extra` | red, green, red | white, red, green, red | none | white | `generated_visual_recipe` |
| `BCNSTK80` | `visual_colour_extra` | green, red, green | white, green, red, green | none | white | `generated_visual_recipe` |
| `BCNTOW01` | `visual_colour_extra` | black | black, white | none | white | `generated_visual_recipe` |
| `BCNTOW60` | `visual_colour_extra` | red | red, white | none | white | `generated_visual_recipe` |
| `BCNTOW61` | `visual_colour_extra` | green | green, white | none | white | `generated_visual_recipe` |
| `BCNTOW62` | `visual_colour_extra` | yellow | yellow, white | none | white | `generated_visual_recipe` |
| `BCNTOW68` | `visual_colour_extra` | black, yellow | black, yellow, white | none | white | `generated_visual_recipe` |
| `BCNTOW69` | `visual_colour_extra` | yellow, black | yellow, black, white | none | white | `generated_visual_recipe` |
| `BCNTOW70` | `visual_colour_extra` | black, yellow, black | black, yellow, black, white | none | white | `generated_visual_recipe` |
| `BCNTOW71` | `visual_colour_extra` | yellow, black, yellow | yellow, black, yellow, white | none | white | `generated_visual_recipe` |
| `BCNTOW74` | `visual_colour_extra` | red, green, red | red, green, red, white | none | white | `generated_visual_recipe` |
| `BCNTOW76` | `visual_colour_extra` | black, red, black | black, red, black, white | none | white | `generated_visual_recipe` |
| `BCNTOW89` | `visual_colour_extra` | black | black, white | none | white | `generated_visual_recipe` |
| `BCNTOW90` | `visual_colour_extra` | brown | brown, white | none | white | `generated_visual_recipe` |
| `BORDER01` | `visual_colour_extra` | red | red, white | none | white | `generated_visual_recipe` |
| `BOYBAR60` | `visual_colour_extra` | red | red, black, black, white | none | black, white | `generated_visual_recipe` |
| `BOYBAR61` | `visual_colour_extra` | green | green, black, black, white | none | black, white | `generated_visual_recipe` |
| `BOYBAR62` | `visual_colour_extra` | yellow | yellow, black, black, white | none | black, white | `generated_visual_recipe` |
| `BOYCAN01` | `visual_colour_extra` | black | white, black, white | none | white | `generated_visual_recipe` |
| `BOYCAN60` | `visual_colour_extra` | red | red, black, white | none | black, white | `generated_visual_recipe` |
| `BOYCAN61` | `visual_colour_extra` | green | green, black, white | none | black, white | `generated_visual_recipe` |
| `BOYCAN62` | `visual_colour_extra` | green, black | green, black, black, white | none | white | `generated_visual_recipe` |
| `BOYCAN63` | `visual_colour_extra` | yellow | yellow, black, white | none | black, white | `generated_visual_recipe` |
| `BOYCAN64` | `visual_colour_extra` | black | black, black, white | none | white | `generated_visual_recipe` |
| `BOYCAN65` | `visual_colour_extra` | white | white, black, white | none | black | `generated_visual_recipe` |
| `BOYCAN68` | `visual_colour_extra` | black, yellow | black, yellow, black, white | none | white | `generated_visual_recipe` |
| `BOYCAN69` | `visual_colour_extra` | yellow, black | yellow, black, black, white | none | white | `generated_visual_recipe` |
| `BOYCAN70` | `visual_colour_extra` | black, yellow, black | black, yellow, black, black, white | none | white | `generated_visual_recipe` |
| `BOYCAN71` | `visual_colour_extra` | yellow, black, yellow | yellow, black, yellow, black, white | none | white | `generated_visual_recipe` |
| `BOYCAN72` | `visual_colour_extra` | red, green, red | red, green, red, black, white | none | black, white | `generated_visual_recipe` |
| `BOYCAN73` | `visual_colour_extra` | green, red, green | green, red, green, black, white | none | black, white | `generated_visual_recipe` |
| `BOYCAN74` | `visual_colour_extra` | red, white, red, white, red | red, white, red, white, red, black, white | none | black | `generated_visual_recipe` |
| `BOYCAN75` | `visual_colour_extra` | red, green | red, green, black, white | none | black, white | `generated_visual_recipe` |
| `BOYCAN76` | `visual_colour_extra` | black, red, black | black, red, black, black, white | none | white | `generated_visual_recipe` |
| `BOYCAN77` | `visual_colour_extra` | white, orange | white, orange, black, white | none | black | `generated_visual_recipe` |
| `BOYCAN78` | `visual_colour_extra` | white, orange, white | white, orange, white, black, white | none | black | `generated_visual_recipe` |
| `BOYCAN79` | `visual_colour_extra` | orange | orange, black, white | none | black, white | `generated_visual_recipe` |
| `BOYCAN80` | `visual_colour_extra` | red, white | red, white, black, white | none | black | `generated_visual_recipe` |
| `BOYCAN81` | `visual_colour_extra` | orange, white | orange, white, black, white | none | black | `generated_visual_recipe` |
| `BOYCAN82` | `visual_colour_extra` | red, white, red, white, red | red, white, red, white, red, black, white | none | black | `generated_visual_recipe` |
| `BOYCAN83` | `visual_colour_extra` | red, white, red, white | red, white, red, white, black, white | none | black | `generated_visual_recipe` |
| `BOYSAW12` | `visual_colour_extra` | red | red, white | none | white | `generated_visual_recipe` |
| `BOYSPR02` | `visual_colour_extra` | green | white, green | none | white | `generated_visual_recipe` |
| `BOYSPR03` | `visual_colour_extra` | red | white, red | none | white | `generated_visual_recipe` |
| `BOYSPR60` | `visual_colour_extra` | red | white, red | none | white | `generated_visual_recipe` |
| `BOYSPR61` | `visual_colour_extra` | green | white, green | none | white | `generated_visual_recipe` |
| `BOYSPR62` | `visual_colour_extra` | yellow | white, yellow | none | white | `generated_visual_recipe` |
| `BOYSPR68` | `visual_colour_extra` | black, yellow | white, black, yellow | none | white | `generated_visual_recipe` |
| `BOYSPR69` | `visual_colour_extra` | yellow, black | white, yellow, black | none | white | `generated_visual_recipe` |
| `CGUSTA02` | `visual_colour_extra` | white | white, magenta, magenta | none | magenta | `generated_visual_recipe` |
| `HGWTMK01` | `visual_colour_extra` | black | white, black | none | white | `generated_visual_recipe` |
| `HRBFAC14` | `visual_colour_extra` | black | grey, black | none | grey | `generated_visual_recipe` |
| `HRBFAC15` | `visual_colour_extra` | black | grey, black | none | grey | `generated_visual_recipe` |
| `LITFLT01` | `visual_colour_extra` | black | black, white | none | white | `generated_visual_recipe` |
| `LITFLT10` | `visual_colour_extra` | red, white | white, red, red, yellow | none | yellow | `generated_visual_recipe` |
| `LITFLT61` | `visual_colour_extra` | green | green, yellow | none | yellow | `generated_visual_recipe` |
| `LITVES01` | `visual_colour_extra` | black | black, white | none | white | `generated_visual_recipe` |
| `LITVES60` | `visual_colour_extra` | red | red, yellow | none | yellow | `generated_visual_recipe` |
| `LITVES61` | `visual_colour_extra` | green | green, yellow | none | yellow | `generated_visual_recipe` |
| `SSLOCK01` | `visual_colour_extra` | black | white, black, black | none | white | `generated_visual_recipe` |
| `TERMNL07` | `visual_colour_extra` | black | white, black | none | white | `generated_visual_recipe` |
| `TERMNL12` | `visual_colour_extra` | black | white, black | none | white | `generated_visual_recipe` |
| `TOPMA113` | `visual_colour_extra` | yellow | black, yellow | none | black | `generated_visual_recipe` |
| `TOPSHP09` | `visual_colour_extra` | red, red, green | red, red, green, black | none | black | `generated_visual_recipe` |
| `TOPSHP15` | `visual_colour_extra` | red, red, yellow | red, red, yellow, black | none | black | `generated_visual_recipe` |
| `TOPSHP30` | `visual_colour_extra` | green, green, yellow | green, white, yellow | none | white | `generated_visual_recipe` |
| `TOPSHP37` | `visual_colour_extra` | black, black | black, white, black | none | white | `generated_visual_recipe` |
| `TOPSHP41` | `visual_colour_extra` | orange, orange | orange, white, orange | none | white | `generated_visual_recipe` |
| `TOPSHP43` | `visual_colour_extra` | green, red, green | green, red, green, white, green | none | white | `generated_visual_recipe` |
| `TOPSHP44` | `visual_colour_extra` | yellow, yellow | yellow, white, yellow | none | white | `generated_visual_recipe` |
| `TOPSHP89` | `visual_colour_extra` | red, white, red | red, white, red, black | none | black | `generated_visual_recipe` |
| `TOPSHPD1` | `visual_colour_extra` | orange | orange, white | none | white | `generated_visual_recipe` |
| `TOPSHPD2` | `visual_colour_extra` | green, green | green, white | none | white | `generated_visual_recipe` |
| `TOPSHPD3` | `visual_colour_extra` | red | red, white | none | white | `generated_visual_recipe` |
| `TOPSHPP2` | `visual_colour_extra` | yellow | black, yellow | none | black | `generated_visual_recipe` |
| `TOWERS03` | `visual_colour_extra` | black | black, white | none | white | `generated_visual_recipe` |
| `TOWERS12` | `visual_colour_extra` | black | black, white | none | white | `generated_visual_recipe` |
| `TOWERS15` | `visual_colour_extra` | black | black, white | none | white | `generated_visual_recipe` |
| `TOWERS57` | `visual_colour_extra` | black, red | black, red, white | none | white | `generated_visual_recipe` |
| `TOWERS59` | `visual_colour_extra` | brown | brown, white | none | white | `generated_visual_recipe` |
| `TOWERS60` | `visual_colour_extra` | red | red, white | none | white | `generated_visual_recipe` |
| `TOWERS61` | `visual_colour_extra` | green | green, white | none | white | `generated_visual_recipe` |
| `TOWERS62` | `visual_colour_extra` | yellow | yellow, white | none | white | `generated_visual_recipe` |
| `TOWERS63` | `visual_colour_extra` | black | black, white | none | white | `generated_visual_recipe` |
| `TOWERS64` | `visual_colour_extra` | orange | orange, white | none | white | `generated_visual_recipe` |
| `TOWERS65` | `visual_colour_extra` | grey | grey, white | none | white | `generated_visual_recipe` |
| `TOWERS68` | `visual_colour_extra` | black, yellow | black, yellow, white | none | white | `generated_visual_recipe` |
| `TOWERS69` | `visual_colour_extra` | yellow, black | yellow, black, white | none | white | `generated_visual_recipe` |
| `TOWERS70` | `visual_colour_extra` | black, yellow, black | black, yellow, black, white | none | white | `generated_visual_recipe` |
| `TOWERS71` | `visual_colour_extra` | yellow, black, yellow | yellow, black, yellow, white | none | white | `generated_visual_recipe` |
| `TOWERS73` | `visual_colour_extra` | black, red, black | black, red, black, white | none | white | `generated_visual_recipe` |
| `TOWERS75` | `visual_colour_extra` | black, orange | black, orange, white | none | white | `generated_visual_recipe` |
| `TOWERS80` | `visual_colour_extra` | black, red, black | black, red, black, white | none | white | `generated_visual_recipe` |
| `TOWERS82` | `visual_colour_extra` | red, grey | red, grey, white | none | white | `generated_visual_recipe` |
| `TOWERS84` | `visual_colour_extra` | black, grey | black, grey, white | none | white | `generated_visual_recipe` |
| `TOWERS86` | `visual_colour_extra` | grey | grey, white | none | white | `generated_visual_recipe` |
| `TOWERS89` | `visual_colour_extra` | green, grey | grey, green, grey, green, white | none | white | `generated_visual_recipe` |
| `TOWERS90` | `visual_colour_extra` | grey, red | red, grey, red, grey, white | none | white | `generated_visual_recipe` |
| `UWTROC03` | `visual_colour_extra` | black | blue, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black | none | blue | `generated_visual_recipe` |
| `WRECKS05` | `visual_colour_extra` | black | blue, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black, black | none | blue | `generated_visual_recipe` |
| `WTLVGG01` | `visual_colour_extra` | black | white, black | none | white | `generated_visual_recipe` |
