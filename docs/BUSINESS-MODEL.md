# Helm — Business Model: Software, Cloud & the Helm Appliance

**Copy the Home Assistant playbook, not the chartplotter playbook: free/open software as
the on-ramp, a cloud subscription as the engine, and an optional turnkey hardware appliance
as the convenience — with the recurring revenue in the cloud, not the box.**

> Status: Strategy draft v0.1 · 2026-06-24 · Owner: Steve Ridder
> Companion to [COMPETITIVE.md](COMPETITIVE.md), [VISION.md](VISION.md), and
> [LEGAL.md](LEGAL.md). Explores selling Helm unbundled (BYO) and bundled (a Mac mini +
> sunlight-readable marine touchscreen appliance), à la Home Assistant Green/Yellow + Nabu
> Casa Cloud.
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
| **HA OS (free image)** | The on-ramp; runs on anything | **Helm software, free/open** — the OpenCPN-refugee wedge, BYO Mac + screen |
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

1. **Now — free/open software (BYO) + Helm Cloud subscription.** The real business, lowest
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

## 7. Open questions

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

---

*The model works. Reframe where the money is: the appliance is the convenient on-ramp at
the helm; the cloud subscription — funding the weather backend and the LLM copilot — is the
durable business; and free/open software is the wedge that brings the OpenCPN refugees in.*
