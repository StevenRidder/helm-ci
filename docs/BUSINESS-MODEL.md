# Helm — Business Model: Software, Cloud & the Helm Appliance

**Copy the Home Assistant playbook, not the chartplotter playbook: free/source-available software as
the on-ramp, a cloud subscription as the engine, and an optional turnkey hardware appliance
as the convenience — with the recurring revenue in the cloud, not the box.**

> Status: Strategy draft v0.3 · 2026-06-26 · Owner: Steve Ridder
> Companion to [COMPETITIVE.md](COMPETITIVE.md), [VISION.md](VISION.md), and
> [LEGAL.md](LEGAL.md). Explores selling Helm unbundled (BYO) and bundled (a Mac mini +
> sunlight-readable marine touchscreen appliance), à la Home Assistant Green/Yellow + Nabu
> Casa Cloud.
>
> **v0.2 changelog (2026-06-26):** added §7 market size & revenue model, §8 competitive
> position & niche, §9 go-to-market, and §10 the layer marketplace & third-party rev-share
> (a second revenue line on top of the cloud subscription). §1–§6 (the appliance/cloud
> tiers) unchanged.
>
> **v0.3 changelog (2026-06-26):** added §11 "Beyond the niche" — renderer licensing, the
> S-100 storefront, and the **AI advisory layer** (incl. the offshore-energy lane and the
> "advisory, not certified ECDIS" guardrail). Former §11 "Open questions" → §12.
>
> **Honesty note:** much of Helm's premium value (the copilot, routing interpretation,
> briefings, diff-narration) is **LLM-derived** — see [WEATHER-ROUTING.md §7](WEATHER-ROUTING.md).
> That cloud-side AI inference is a primary thing the **Helm Cloud** subscription funds, and
> the guardrails there apply unchanged.

---

## 1. The Home Assistant model, translated

Home Assistant's structure is three layers — and the revenue is **not** the hardware:

| Home Assistant | What it really is | Helm equivalent |
|---|---|---|
| **HA OS (free image)** | The on-ramp; runs on anything | **Helm software, free/source-available** — the OpenCPN-refugee wedge, BYO Mac + screen |
| **Green / Yellow appliances** | Turnkey "it just works," sold near cost | **The Helm appliance** — Mac mini + sunlight-readable touchscreen, pre-configured |
| **Nabu Casa Cloud (~$6.50/mo)** | The real revenue engine + funds dev | **Helm Cloud** — chart tiling/hosting, GRIB weather, route/fleet sync, **AI copilot inference**, community backend |

**Key insight: Nabu Casa is where HA makes money, not the hardware.** Green/Yellow are sold
at thin margins as a convenience on-ramp; the subscription funds everything and aligns
incentives — you pay for convenience, not because you're locked in. Helm should copy *that*
structure.

The happy part: the architecture is **already shaped for it.** The on-demand tiler
([CHART-PIPELINE.md](CHART-PIPELINE.md)), the weather pipeline, the community/places backend
([integrations/noforeignland.md](integrations/noforeignland.md)), and the cloud-side copilot
([VISION.md](VISION.md) §8) **are** the Helm Cloud product. The Nabu Casa layer is half-built.

---

## 2. The three commercial tiers

```
┌─ Helm Free / Open ─────────────────────────────────────────────┐
│  BYO Mac + screen. Charts, fused weather layers, nav, AIS,     │
│  Smart Board, offline. The OpenCPN-refugee on-ramp.            │
└────────────────────────────────────────────────────────────────┘
        +
┌─ Helm Cloud (subscription — the revenue engine) ───────────────┐
│  Hosted chart tiling · GRIB delivery · route/fleet sync ·      │
│  AI copilot inference [LLM] · community backend · remote watch │
│  Works regardless of hardware. This is the Nabu Casa analog.   │
└────────────────────────────────────────────────────────────────┘
        +
┌─ Helm Appliance (hardware — convenience, near-cost) ───────────┐
│  Mac mini + sunlight-readable marine touchscreen, pre-built,   │
│  power-conditioned, mounted. The Green/Yellow analog.          │
└────────────────────────────────────────────────────────────────┘
```

**Lead with the first two. The box is the destination, not the start.**

---

## 3. Why the appliance is genuinely strong for Helm

1. **The precedent is already in our competitive doc.** [Orca](https://getorca.com/) (flagged
   in [COMPETITIVE.md](COMPETITIVE.md) as "the real threat") sells exactly this: a Core (boat
   computer) + Display + app + subscription. The bundled marine-nav-computer model is
   *proven*. So is the entire DIY "OpenCPN on a mini-PC at the helm" community — we'd be
   productizing what people already hack together.
2. **A fixed helm display is the *ideal* form factor for the Smart Board.** The
   Home-Assistant-style composable dashboard ([VISION.md](VISION.md) §5) makes the most sense
   on a mounted, always-on screen at the nav station. Bundle and vision reinforce each other.
3. **The bundle sidesteps our biggest legal headache.** On a Mac mini we ship a notarized DMG
   directly — **not** through the App Store — so the GPL-vs-App-Store "VLC problem" from
   [ARCHITECTURE.md](ARCHITECTURE.md) / [LEGAL.md](LEGAL.md) largely **evaporates** for the
   macOS/appliance product. A contained OpenCPN/GDAL component is far easier here than on iOS.
   macOS is already our strongest platform (cleanest OpenCPN/GDAL reuse); the appliance leans
   into that.
4. **MFDs are overpriced and ugly.** A Mac mini (~$599, ~7 W idle on Apple Silicon) + Helm
   out-UXes a $3,000–8,000 Garmin/B&G helm setup. The value story is real.

---

## 4. Where it gets hard (real, not fatal)

| Friction | Why it matters | Mitigation |
|---|---|---|
| **Marinization** | Mac mini isn't IP-rated, salt/vibration/humidity-hardened; MFDs are IPx7 | Sealed enclosure + vibration mount; let the **touchscreen** carry the marine-grade duty |
| **Power & boot** | Boats are 12 V DC; macOS hates ungraceful power-off; MFDs are instant-on | Clean DC-DC supply + UPS/supercap for graceful shutdown; always-on/sleep strategy |
| **Sunlight readability** | Consumer screens (~300 nits) wash out; marine needs ~1000+ nits, anti-glare, salt-tolerant touch | This is what the marine touchscreen ($400–1,500) is *for* |
| **Apple as appliance platform** | No appliance/kiosk licensing; can't pre-image/lock down like HA on Linux; OS updates outside our control | Reselling minis is fine (hardware resale); accept less kiosk polish than HA Green |
| **Hardware ops + liability** | Inventory, RMA, warranty, thin margins; a turnkey nav appliance carries more product-liability weight than BYO software | Stage it (§6); keep satellite-supplemental disclaimers prominent ([LEGAL.md](LEGAL.md)) |

The engineering gate for the appliance path is
[NATIVE-REFERENCE-HARDWARE.md](NATIVE-REFERENCE-HARDWARE.md): exact hardware
revision, DC power/UPS evidence, and OpenCPN parallel sea-trial level must be
recorded before any hardware bundle is described as reference-certified.

---

## 5. BOM & pricing sketch (illustrative, not committed)

| Item | Cost |
|---|---|
| Mac mini (Apple Silicon, base) | ~$599 |
| Sunlight-readable marine touchscreen (10–15", IP65) | ~$400–1,500 |
| DC-DC power + UPS/supercap + enclosure + mount + cabling | ~$200–400 |
| **Appliance BOM** | **~$1,200–2,500** |
| **Sell price** | **~$2,000–3,500** — still undercutting a comparable Garmin/B&G helm install ($3,000–8,000+) |
| **Helm Cloud** | subscription (the Nabu Casa engine), ~consumer-SaaS monthly — works with or without the box |

The margin philosophy mirrors HA: **box near cost, money in the cloud.**

---

## 6. Recommended sequencing — don't lead with a box

1. **Now — free/source-available software (BYO) + Helm Cloud subscription.** The real business, lowest
   risk. Validate that people pay for the cloud layer (weather, sync, copilot, community)
   regardless of hardware.
2. **Next — a "certified build" / reference hardware list.** "Here's the exact Mac mini +
   screen + power + enclosure, here's the install guide." Zero inventory risk; learn the
   integration without owning the ops.
3. **Then — the full bundled appliance**, once demand and support capacity exist. The
   Green/Yellow moment.

**Unbundled is the right *start*, bundled is the right *destination*, and Helm Cloud is the
engine under both.**

---

## 7. Market size & the revenue model

**Don't believe the big number.** ~30M+ recreational boaters worldwide and a ~$6B/yr
new-sailboat market are real but largely irrelevant — ~99% buy a Garmin at the helm or tap
Navionics and never touch a BYO/hackable chartplotter. Our serviceable market is the overlap
of *cruising sailors* ∩ *technical / DIY / OpenCPN-comfortable*:

| Funnel stage | Order of magnitude |
|---|---|
| Recreational boaters worldwide | ~30M+ |
| Sailing cruisers | ~1M |
| Tech-savvy "OpenCPN-refugee" niche (our SAM) | ~50,000–150,000 |
| Realistic paying customers (1–5% capture, multi-year) | hundreds → low thousands |

OpenCPN has no published user count; community consensus is *tens of thousands* of active
users, "thousands" using it as primary nav — that's the core of the SAM.

**Comparables (the reality check):**

- **savvy navvy** — our closest analog (subscription sailing nav). ~1.6–3M downloads →
  ~15k+ paying subs at ~£100/yr → ~£1.5M ARR (~$2.6M revenue), ~25 staff, on ~$4.6M raised
  across 4+ crowdfunding rounds. Download→paid conversion ≈ **1%**.
- **Orca** — free app, "hundreds of thousands" of users, monetizes hardware (Core/Display) +
  Orca Plus €49 / Smart €149; backed by Atomico. (The recreational Orca, *not* the unrelated
  "Orca AI" autonomous-shipping company.)
- **Navionics** (Garmin) — mass market, ~$80/yr; the chart-data moat. Not our fight.

**Revenue scenarios** (gross ARR = paying subs × price; net ≈ subtract ~$18/user/yr cloud +
LLM COGS):

| Paying subs | @ $100/yr | What it is |
|---|---|---|
| ~100 | ~$10k | pocket money / hobby |
| ~500 | ~$50k | solid side income (realistic 2–3 yr solo target) |
| ~1,000 | ~$100k | full-time, one person |
| ~5,000 | ~$500k | small company |
| ~15,000 | ~$1.5M | savvy-navvy territory — needs a team + funding |

Price anchor: **~$49–100/yr**, near Orca Plus (€49) and below savvy navvy (£99). Above
~$150/yr the "OpenCPN is free" perception bites.

**Honest framing:** what's *most built* (the fused, offline, no-lock-in chartplotter) is the
**free on-ramp**; what *justifies the subscription* (cloud sync, AI copilot, weather routing,
remote alerts) is the **least built**. The product is real; the business is the gap between
them. That gap — not the engine — is the work.

## 8. Competitive position & the niche

We don't beat Orca / savvy navvy on their axis — we play a different one: **fused +
open/power-user**, the quadrant nobody occupies. The only open kin (OpenCPN) is dated,
desktop-only, not fused; everyone polished (Navionics, Orca, savvy navvy) is closed.

**Niche, one line:** *the off-grid / world-cruiser / OpenCPN-refugee who wants OpenCPN's power
and no chart-subscription lock-in — but fused, modern, and offline-first.*

- **Where we win:** a real S-52 ENC engine (not an app's simplified vector charts), genuine
  fusion on one screen, depth-on-satellite reef piloting, true BYO/offline, honesty primitives
  (source-tagging, advise-don't-act). The gray, liability-heavy features a VC-backed firm
  won't ship — our moat *and* our ceiling.
- **Where we're behind today:** no native / App-Store app, no weather routing, no
  tides/currents, no auto-routing, AI copilot mostly aspirational, no cloud product yet,
  thinner chart-data coverage than Navionics, no distribution / brand / support org.

## 9. Go-to-market — copy what worked, use our unfair channel

How the funded players actually got clients: a **free top-of-funnel**, **real capital + a
team** (CMO, BD), and the 2020–21 boat boom. Two distinct playbooks:

- **savvy navvy:** crowdfunding-as-marketing (4+ rounds, 2,000+ investor-evangelists), founder
  marina-walks, RYA/RNLI credibility, and a killer one-liner ("Google Maps for boats").
- **Orca:** design + hardware-as-distribution (retail shelves, press reviews, OEM deals
  putting it on new boats at the factory), free app as land-grab.

**Our unfair channel they don't have:** the existing **OpenCPN community** — tens of thousands
of warm, technical, pain-aware, lock-in-averse boaters concentrated on forums (Cruisers Forum,
etc.). savvy navvy had to *find* such people one marina at a time; ours are already in one
room. [posts/cruisersforum-opencpn-update.md](posts/cruisersforum-opencpn-update.md) is that
wedge.

**Copy directly:** (1) keep the free on-ramp ungated; (2) community-as-owners — open-source +
crowdfunding fits us *better* than it fit them (the Home Assistant / HACS pattern).
**One gap to close:** we have no "Google Maps for boats" one-liner yet — and that sentence is
cheaper than any ad budget.

## 10. The layer marketplace & third-party rev-share

**Thesis:** open Helm's layer system so third parties' data (weather, places, routing, regional
charts) plugs in as **subscribable layers**, and take a cut. This converts our core weakness
(can't out-feature funded teams) into a strength — providers and community build the features
we'd never have time to, and the ecosystem becomes the moat (à la Home Assistant / HACS).

**Why the architecture is already ready.** A "layer" has a defined shape: `SHELL` panel/layer
registration + per-domain `style.json` fragments (done), the `sample()` probe contract
(`AI-5` / `AI-17`), the value-encoded tile contract (`cog.js`, `WX-10`), and a per-domain
FastAPI backend (`BACKEND-1`). `NATIVE-14` literally names a "plugin SDK / layer probe
contract." And **per-field source-tagging (`ENGINE-7`) doubles as the metering/payout ledger**
— every datum is already attributed, which is exactly what honest per-provider rev-share needs.

**Strategic tailwind — the pros are converging on this model.** The professional standard
S-100 (IMO-enabled from 2026) reframes the chart as a *layered data canvas*: an S-101 base ENC
plus plug-in product specs (S-102 high-res bathymetry, S-104 water levels, S-111 surface
currents, S-124 nav warnings, S-129 under-keel clearance). That is the same architecture as
our marketplace. **Design the layer contract to mirror/ingest S-100 product specs**, so
"a vendor publishes a layer" and "ingest the official S-104 layer" travel the same pipe — and
we become the first *consumer* chartplotter surfacing S-100 layers to cruisers.

**Competitive read (the S-100 "dual-fuel" canvas).** This widens the moat along our existing
axis *without* moving us toward the closed/commercial corner. The recreational players
(Navionics/Orca/savvy navvy) have no reason to consume official S-100 — their value is their
*own* data — and OpenCPN is slow on it, so adopting S-100 makes Helm the only *recreational*
client speaking the pro chart language (S-57 past / S-52 present / S-101 future). It also lowers
marketplace integration cost: a vendor publishes a *standard* S-102/S-104 product instead of a
Helm-specific adapter, easing some tier-2 rev-share answers. **Guardrail — data model YES,
commercial ECDIS NO:** adopt the S-100 data model + ingestion for the cruiser/bridge use case
(real-time, on-the-boat, offline); do **not** drift into a type-approved/SOLAS ECDIS or a
fleet-route-optimization "office" product (Furuno/Wärtsilä/NAVTOR territory — regulated,
liability-heavy, a different buyer). The standard's commercial origin will pull that way;
resisting it is the positioning. Near-term scope stays the **Hybrid Bridge**: free NOAA
S-57/S-52 base + free S-100 overlays where they exist + BYO — not a bet on global S-101 coverage.
See [LABS.md](LABS.md) (`LABS-5`).

**Two integration models:**

- **Provider-built** — they build to our SDK (they bear the cost). Best for the long tail and
  the OpenCPN-plugin community.
- **Helm-built, rev-shared** — *we* write the adapter and the data owner gets paid on
  subscriptions (they bear ~zero cost/risk). This is just our existing first-party-adapter
  pattern (Open-Meteo today is exactly this) plus a meter. Lower friction; the right model for
  anchor providers.

**Who actually says yes — segment, because money only moves one tier early:**

| Provider tier | Examples | Build to Helm? | Why |
|---|---|---|---|
| **Eager yes** | regional GRIB shops, tide-data vendors, cruising-guide authors, niche routers | Yes, fast | Found money, no strategic conflict, low "worth-a-contract" threshold |
| **Yes, at scale** | Windy, PredictWind | Eventually | Have resale terms, but our cut must clear a *big* firm's attention bar; they'll guard against cannibalizing direct subs |
| **Structural no** | Garmin/Navionics, Orca, ActiveCaptain, SeaPeople | No, at any price | Competitor channel/brand, or walled/unlicensable data |

**Frictions to respect:** (a) a provider only nets *more* on net-new users → big names price to
avoid undercutting their direct subs; (b) in the Helm-built model *we* carry build +
maintenance, so at low subs our cut won't cover it — **demand-gate adapters, don't build on
spec**; (c) willingness ≠ rights — upstream licenses (ECMWF, hydrographic offices) may bar
resale ([LEGAL.md](LEGAL.md), walls table in [COMPETITIVE.md](COMPETITIVE.md)).

**The unbuilt money-rail** (the gap between "architecture-ready" and "marketplace-real"):
Cloud billing + entitlements + payout (`NATIVE-11`, `CONTRACT-15`) and three-tier packaging /
plugin SDK (`NATIVE-14`) — all **Not Started**. We can build the adapter today; we can't meter
and pay for it yet.

**Sequencing:** first-party layers (some wrapping third-party data) → free community SDK
(HACS-style, riding the OpenCPN dev crowd) → paid marketplace at scale. **Design for rev-share
now; build the store after there are users.**

---

## 11. Beyond the niche — renderer licensing, the S-100 storefront & the AI advisory layer

> The niche model (§7–§8) is the **lifestyle outcome**: hundreds of cruiser subscribers, a
> defensible corner. This section is the **company outcome** — the paths past the
> consumer-paying-base ceiling. All ride the *same* tech core (the S-100 renderer + the AI
> copilot + the fusion engine + the honesty primitives); what changes is the buyer and the
> go-to-market. **Rule of the section: don't try to *be* a certified ECDIS — be the AI
> charting/advisory + data layer (and the engine) that rides *alongside* one.**

### 11.1 The one line that's closed — and why it's not a coding problem

The **type-approved, primary-navigation ECDIS for SOLAS vessels** is genuinely closed to a small,
fast-moving team. Three gates, none of which good engineering solves:

1. **Type approval is a product gate, not a quality gate** — certified against `MSC.232(82)` +
   `IEC 61174`, tested by a class society (DNV/BV/ClassNK), flag-state accepted: ~six-to-seven
   figures, 12–24 months, *per product*, re-triggered on material change. That cadence is the
   opposite of a web app's.
2. **Liability is categorical** — a certified ECDIS in the chain on a grounding ($100M hull, a
   spill, deaths) puts the maker in the lawsuit. Incumbents carry the insurance, legal teams, and
   case law. (Even Exxon operates its high-consequence regulated work behind a balance sheet +
   compliance apparatus — the moat is the apparatus, not the brains.)
3. **Distribution is a service moat** — fitted at the shipyard, sold through class-approved 24/7
   global service networks with guaranteed ENC-update delivery. Years of infrastructure.

Stay out of *that* layer. It is one slice, not the whole commercial market.

### 11.2 The layers that are open (and where the edge is)

| Layer | Open? | Why / the edge |
|---|---|---|
| Certified primary-nav ECDIS (SOLAS) | No | type-approval cadence + categorical liability + service moat |
| Non-SOLAS commercial (workboats, fishing, tugs, OSVs, survey, sub-threshold ferries, yachts) | Yes | not required to run type-approved ECDIS; legal as a planning/awareness aid |
| **AI decision-support / advisory** (voyage optimization, AI lookout, predictive UKC, anomaly/risk narration, fleet analytics) | **Yes — the frontier** | rides *alongside* the certified ECDIS → no type approval; incumbents are weak at modern AI/UX |
| **Offshore-energy marine** (OSVs, DP support, met-ocean, survey/ROV) | **Yes — the unfair-advantage lane** | high-value, relationship-gated, safety-critical-AI-friendly; founder has offshore-energy access + credibility |
| Component / white-label engine licensing | Yes | let a type-approved partner carry the cert; we supply the renderer/AI |

### 11.3 The revenue lines (which scale past the consumer base)

| Revenue line | Who pays | Ceiling | Gated on |
|---|---|---|---|
| Consumer sub (Helm Cloud) | cruisers, prosumers | lifestyle (hundreds–few-thousand subs) | exists |
| **Marketplace take-rate / S-100 storefront** | users buy layers; we keep a cut | grows with the *supply* side, not just users | billing rail (`NATIVE-11`, `CONTRACT-15`) + supplier BD |
| **Engine / renderer licensing (B2B/OEM)** | non-SOLAS commercial + app/HW makers | not capped by consumer conversion | **clean-room relicensing (`CHART-13`, `ENGINE-11`)** |
| **AI advisory (seats / SaaS)** | non-SOLAS commercial + offshore-energy ops | enterprise ARPU, few-big-deals | advise-don't-act framing (`AI-13`) + BD |
| Appliance hardware | cruisers, yachts | near-cost | exists |
| Opt-in crowd data (CSB) | hydro offices, researchers | modest, opt-in | consent + aggregation |

### 11.4 The AI advisory layer — the actual frontier (and our best fit)

The companies attacking commercial shipping with capital today (Nautilus Labs, Bearing.ai,
Windward, Orca AI, Sea Machines, Awake.AI) are **not** building certified ECDIS — they build the
AI / analytics / situational-awareness layer that sits *next to* it. That layer needs **zero type
approval** because it's advisory, and it's exactly where the certified incumbents are bad.

What we'd ship there is mostly *already specced* in Helm + Labs:

- **Predictive under-keel clearance** (`LABS-2`) → bar/channel transit timing for workboats,
  dredgers, OSVs.
- **AI lookout / sensor-fusion collision risk** (`LABS-3`) → the Orca-AI / SEA.AI lane.
- **Watchkeeper risk narration + departure/voyage advisory** (`AI-11`) → fuel/route/weather
  optimization, the Nautilus/Bearing lane.
- **Met-ocean fusion + S-102/S-104 dynamic layers** → the situational-awareness picture.
- **Fleet analytics + anomaly detection** (net-new) over the same source-tagged stream.

Why we can enter it: **advise-don't-act (`AI-13`) + explicit "supplementary, not primary
navigation" labeling is the legal spine** that keeps us out of the primary-nav liability chain.
The honesty primitives built for *cruiser* trust are precisely what make the *commercial* advisory
market enterable. Why *this founder* specifically: safety-critical-AI experience in a regulated
high-consequence industry (oil & gas) + offshore-energy access is an edge most marine-app founders
can't touch. **Point the AI layer at offshore-energy marine first.**

### 11.5 The honest gates

- **Engine licensing is closed until `CHART-13`.** Today's renderer is OpenCPN/GPL-derived; you
  cannot cleanly commercial-license GPL-derived code. The clean-room rebuild on permissive
  GDAL/OGR/PROJ (`CHART-13`, gated on IP counsel) is the unlock — a real cost, not free upside.
- **Advisory still carries liability** — just not certification. If the AI says "safe to transit"
  and a vessel grounds, you're still in the conversation. `AI-13` + supplementary labeling are
  load-bearing legally; any commercial/offshore product needs counsel sign-off.
- **These are different companies.** Consumer self-serve vs BD-heavy enterprise (few big deals,
  long cycles, support/SLA contracts). The storefront needs supplier agreements with hydro
  offices/VARs; the advisory line needs enterprise sales. A deliberate fork, not a free extension.
- **Still not a certified ECDIS** (§11.1). First-class renderer ≠ type approval.

### 11.6 Verdict — the fork

Same tech core, two destinies. The **consumer cruiser app** is the lifestyle outcome *and* the
proving ground (it boat-tests the engine and the AI cheaply). The **engine + the S-100 storefront
+ the AI advisory layer (aimed at offshore-energy)** is the company outcome — the part not capped
by consumer conversion, and the part where the founder's background is the edge. Build the wedge
now; keep the renderer relicensable (`CHART-13`) and the AI advisory honest (`AI-13`) so the
bigger doors stay open; choose the fork deliberately once the wedge has proven the core.

**Decision (2026-06-26, pre-MVP): keep both paths open.** Too early to pick — no MVP yet means no
real demand signal to choose on, and the option value is cheap because the path-preserving moves
*are* principles we already hold:

- keep the renderer **relicensable** — honor the `ENGINE-11` GPL boundary, don't deepen
  OpenCPN/GPL entanglement (this keeps `CHART-13` / engine licensing possible later);
- keep the AI **advise-don't-act + supplementary-labeled** (`AI-13`) — the legal spine for a
  trustworthy consumer app *and* any future commercial advisory product;
- keep everything **source-tagged** (`ENGINE-7`) — honesty for consumers *and* the marketplace's
  metering/payout ledger;
- keep the **layer contract clean / S-100-shaped** (informed by `LABS-5`);
- sign **no exclusive** data/distribution deals and no commercial-foreclosing license (the
  `NATIVE-12` BSL→Apache posture already guards this).

The only thing we explicitly do NOT do pre-MVP is spend on *either* go-to-market — no
certification, no enterprise BD, no consumer-marketing push. **Revisit the fork when the MVP is
boat-proven AND a real pull signal appears** — an inbound engine-licensing/OEM ask, hydro-office /
VAR storefront interest, or an offshore-energy pilot (Steve's network) — whichever comes first.

---

## 12. Open questions

- **Cloud subscription scope & price** — what's in free vs. paid? (Likely: offline core
  free; hosted tiling/GRIB/sync/copilot/community/remote-watch paid.)
- **LLM inference cost** — the copilot is a real per-user cloud cost; it must be priced into
  the subscription, with an on-device fallback offshore ([WEATHER-ROUTING.md §7](WEATHER-ROUTING.md)).
- **Liability of a sold nav appliance** vs. BYO software — needs counsel before the box ships.
- **Apple's posture** on resold/embedded Mac minis as a productized appliance at scale.
- **Support ops** — a hardware business is inventory + RMA + warranty; heavy for a small
  team. The certified-build step (§6.2) defers this.
- **Which gray sources ship** in a *sold* product vs. a personal build ([LEGAL.md](LEGAL.md),
  [COMPETITIVE.md](COMPETITIVE.md)) — the bundle's out-of-box wow is tamer than Steve's
  personal build because BYO/personal-use toggles bind a distributed product.
- **Marketplace cut & layer pricing** — what % does Helm keep, and are layers priced
  per-layer or bundled into Cloud tiers? (§10)
- **The scale threshold** — at what subscriber count does a tier-2 provider's (e.g. Windy)
  annual rev-share stop being a rounding error and flip them to "yes"? Model this against §7.
- **Anchor providers** — which 2–3 tier-1 providers do we approach first to seed the store?
- **Third-party-layer safety review** — a bad layer on a nav-safety screen is *our* liability;
  what's the review/cert gate (the enforceable probe-contract bar, `AI-17`) before a layer ships?
- **S-100 ingestion** — do we build the layer contract to natively consume S-100 product specs
  (S-102/104/111/124/129) from 2026, making official layers and marketplace layers one pipe? (§10)
- **The strategic fork** — *decided 2026-06-26 (pre-MVP): keep both paths open; defer the choice
  (§11.6).* Live sub-question: what's the earliest trigger that should force it — and who do we say
  no to in the meantime to avoid foreclosing a path?
- **Advisory liability** — is advise-don't-act + "supplementary, not primary navigation" framing
  (`AI-13`) sufficient to stay out of the primary-nav liability chain for a *commercial/offshore*
  advisory product? Needs counsel. (§11)
- **Clean-room relicensing trigger** — what demand signal justifies funding `CHART-13` (the gate
  that opens engine licensing)? (§11)

---

*The model works. Reframe where the money is: the appliance is the convenient on-ramp at
the helm; the cloud subscription — funding the weather backend and the LLM copilot — is the
durable business; the layer marketplace is the second revenue line and the ecosystem moat;
and free/source-available software is the wedge that brings the OpenCPN refugees in. The niche is small
but defensible — a lifestyle/side-business at hundreds of subscribers, a real company only at
savvy-navvy scale (team + capital). Build for the former; leave the door open to the latter.*
