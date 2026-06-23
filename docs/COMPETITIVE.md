# Competitive landscape & market position

> Honest read: the market is crowded and *consolidating* toward modern all-in-one apps.
> Don't fight on charts (Garmin/Navionics own that moat). Win on **fusion + the
> cruiser-hacker features incumbents legally won't build.**

## The field (2026)

| App | Price/yr | Strength | Helm's edge over it |
|---|---|---|---|
| [Navionics Boating](https://www.wavveboating.com/blog/navionics-vs-aqua-map-comparison-guide/) (Garmin) | ~$80 (regional €50–100) | The chart-data moat; coverage; auto-routing | Weather fusion, offline-everything, no chart-subscription lock-in |
| [Aqua Map](https://www.wavveboating.com/blog/navionics-vs-aqua-map-comparison-guide/) | $15–25 | Cheap; inland; depth shading; fishing | Modern UX, real weather, satellite, cross-platform |
| [Savvy Navvy](https://www.wavveboating.com/blog/savvy-navvy-cost-pricing-guide/) | $99–169 | Modern auto-routing ("Google Maps for boats"); wind/tide/current | Satellite + depth-on-sat, on-demand charts, full Windy-class layers, BYO |
| [Argo](https://www.wavveboating.com/blog/argo-boating-app-pricing-cost-guide/) | ~$40 | Social + NOAA ENC offline (US); hazard pins | Global coverage, weather depth, fusion |
| **[Orca](https://getorca.com/)** | €49–149 (+ hardware) | **The real threat** — modern, *satellite hybrid charts*, sail routing, AIS, collision; hardware ecosystem | Multi-source chart download, full GRIB weather catalog, OpenCPN-grade power, true BYO |
| [OpenCPN](https://opencpn.org) | free | Power users, plugins, BYO/ChartLocker | **Who Helm is *for*** — dated UX, desktop-only, no iOS, no fusion |
| [Windy](https://www.windy.com) / [PredictWind](https://www.predictwind.com) | freemium / sub | Best-in-class weather / routing | Composited onto the chart, offline, in one app |

## The wedge

No product puts **charts + satellite + the full weather stack + routing + AIS + instruments
on one screen.** The closest (Orca, Savvy Navvy) are well-funded and moving fast — but they
*can't* ship Helm's most differentiated features:

- ChartLocker-style **multi-source on-demand chart download** (satellite/Navionics/Google/Bing),
- **depth-on-satellite** reef piloting,
- **true BYO / offline-everything** with no chart-subscription lock-in.

Those are exactly the **legally-gray, liability-heavy** features a VC-backed company won't
build. That's simultaneously Helm's moat (incumbents won't) and its ceiling (you inherit the
ToS/liability if you sell it).

## Verdict

- **Build it** — you'll use it daily, and the fused screen genuinely doesn't exist.
- **Sell it** to the **off-grid / world-cruiser / OpenCPN-refugee** niche as freemium, priced
  near Orca Plus (~€49/yr), leaning on *fusion + offline + no-lock-in + power-user capability*.
- **Don't** position as a mass-market Navionics/Orca competitor — the chart moat and liability
  make that a losing fight.
- **Catch** (see [LEGAL.md](LEGAL.md)): the paid build likely ships the gray sources as
  BYO/personal-use toggles, so its out-of-box wow is tamer than your personal build.

## Data-source walls (who you can and can't pull from)

| Source | Wall | Path |
|---|---|---|
| OpenStreetMap / Overpass | open | Pull freely (ODbL attribution) — primary places layer |
| OpenSeaMap | open | Pull (ODbL) — seamarks/harbours |
| NoForeignLand | semi-walled | **Push** official; **pull** = partnership or personal-only ([integration scope](integrations/noforeignland.md)) |
| SeaPeople | walled | No public API — not integrable |
| ActiveCaptain (Garmin) | walled | Partnership only |
| Navionics | walled | Paid SDK, online-only ([LEGAL.md](LEGAL.md)) |
