# Helm — Weather, Routing & the Spacetime Engine

**Sample the weather along your *future track*, not at a fixed clock time. Make every
forecast update magic-in-the-background. Make ocean routing easy enough that you stop
juggling eight apps — and honest enough to tell you when to still call a human.**

> Status: Spec draft v0.1 · 2026-06-24 · Owner: Steve Ridder
> Companion to [VISION.md](VISION.md) (§6 Weather, §8 Copilot) and [WEATHER.md](WEATHER.md)
> (the own-GRIB rendering stack). Born from a real 18-day Maupiti→Fiji passage and the
> misery of constantly re-downloading GRIB, opening tabs, and re-deriving the route by hand.
>
> **Honesty note up front:** a large share of the "magic" in this document is **LLM-derived**
> — briefings, the diff narration, departure advice, routing interpretation. Those parts are
> tagged **[LLM]** and governed by the guardrails in §7. The numbers underneath them
> (position, ETA, isochrones, CPA, wind/sea values) are **deterministic** and computed, never
> generated. The LLM *explains and sequences*; it never *invents* a forecast or a fix.

---

## 1. The core idea — spacetime coupling

Every weather app shows the field at a **fixed wall-clock time** and makes the human do the
projection: "the front arrives Thursday 14:00 — where will *I* be Thursday 14:00?" That
mental projection, repeated across wind/gust/swell/rain and re-done after every GRIB
download, *is* the work that exhausts passage-makers.

Reframe it. Your boat is a **worldline** — position as a function of time, `P(t)`. Weather
is a **4-D field** — `W(lat, lon, t)`. The single useful operation is to **sample the field
along the worldline**:

```
                  weather you will actually experience  =  W( P(t), t )
```

Other apps give you `W(·, t_fixed)` and leave `P(t)` in your head. Helm computes both and
joins them. That join is the whole feature.

### Why this is close at hand (not a new subsystem)

All three ingredients already exist in the repo:

| Ingredient | Already in | What it gives us |
|---|---|---|
| Forecast time index | `web/index.html` scrubber + `forecast.json` (`times[]`, per-frame `field-*-t{n}.json`) | `W(·, t)` for each hour |
| Boat position along route + ETA | `engine/.../helm_engine.cpp` (real OpenCPN `Routeman`: BRG/DTW/XTE per fix) | `P(t)` from route + speed model |
| Per-time weather layers | `field-layer.js`, `wind-layer.js` | renderable `W` at any frame |

The feature is **binding the scrubber to the boat and the boat to the scrubber** — not
building a new engine.

---

## 2. Three interactions, one model

### 2.1 Scrub the boat forward
Drag the time handle and **both** move: a ghost own-ship slides along the route at the
polar/SOG-predicted speed, and the weather layer snaps to the *valid* time at each step. The
instrument tiles (and the Smart Board) show TWS / TWA / gust / sea-state **the boat will
feel at that moment**, not the current conditions. You fast-forward your passage and watch
the weather you're sailing into.

### 2.2 Click anywhere on the route — the "Virtual Buoy" move
*(Conceptual ancestor: [Buoyweather](https://www.buoyweather.com/)'s "Virtual Buoys" — a
point forecast anywhere offshore, on demand.)* Tap a leg or any point on the route → Helm
computes the ETA there from the speed model → shows the forecast valid **then, right there**:

> **WP5 · arrive Thu 14:00 · 28 kt SW, gusts 34 · 3.1 m swell @ 11 s · on the nose.**

That one line is what people currently assemble across eight tabs.

### 2.3 The route-weather ribbon
A horizontal strip under the chart: for the whole passage, wind / gust / sea-state / rain at
each hour **at the boat's projected position**. The single most useful passage view — the
thing PredictWind's departure planner does well and almost nobody else does. It turns an
18-day passage into something readable in ten seconds. Scrubbing, the ribbon, and the chart
ghost are all the same `W(P(t), t)` shown three ways.

**[LLM]** A one-tap "read me the passage" turns the ribbon into a spoken/written narrative:
*"You'll motor out of the lagoon into light SE, build to 18–22 kt by Tuesday night, then a
front Thursday afternoon gives you 30 kt on the nose for ~12 hours before it eases."*

---

## 3. The real pain — "every download changes where I'd go"

The data churn is inherent (GFS/ECMWF update 2–4×/day; each run shifts the optimum). The
*misery* is human: re-download, re-open, re-derive, every time. The fix is a UX discipline,
not a model:

1. **Background, always.** Helm ingests new GRIB automatically whenever it has a pipe — wifi
   at anchor, a sat link offshore — re-runs the router, and updates silently. No "download"
   ceremony, no managing files. The Maupiti→Fiji workflow (download → open tons of pages →
   figure it out) collapses to *nothing the user does*.
2. **Diff, don't dump. [LLM]** Never hand the user 40 MB and a blank stare. Surface **what
   changed and whether it matters to *their* decision**:
   > *New ECMWF run: the Thursday squash zone shifted ~120 NM north — your current route now
   > clips 35 kt. Suggested reroute saves ~6 h of beating. [view] [apply] [ignore]*

   Most updates change nothing material → stay silent. The one that matters earns the
   notification. The LLM writes the sentence; the **isochrone delta underneath it is
   computed.**
3. **Ensemble = honesty about confidence.** Run GFS *and* ECMWF (both free). Agreement →
   high confidence; divergence → the divergence *is* the decision. Show spread, never pretend
   one model is truth. (Same "never fake a feed" ethic as the nav-source badge.) **[honesty]**

---

## 4. Routing made easy — democratizing MetBob

PredictWind feels easy and people *still* hire MetBob / Commanders' Weather to cross the
Pacific. Not for raw data — for **interpretation, timing judgment, and reassurance on
tropical systems.** That is precisely the gap an AI-native layer fills, *without
overclaiming.*

- **Deterministic core:** isochrone router on free GRIB + boat polars (Phase 2 in
  [ROADMAP.md](ROADMAP.md)). Produces the route, the isochrones, the ETA. **Computed.**
- **Departure-window optimizer:** *"best 5-day window to leave for Fiji"* with the tradeoffs
  spelled out, not a wall of GRIB. **[LLM]** narration over **computed** candidate routes.
- **Continuous re-route underway:** the "always in the background" — recompute on each new
  run, surface only material change (§3).
- **The copilot talks like a router. [LLM]**
  > *"Models agree on the front Thursday. I'd leave Wednesday 02:00 to cross ahead of it; the
  > alternative is Saturday — calmer but ~18 h slower. Worth a human router's eyes: tropical
  > activity is building NE of Fiji."*

  It makes the 90% case trivial **and tells you honestly when you're in the 10% where you
  should still call MetBob.** That "knows its limits" posture is the trustworthy position and
  the right brand. **[honesty]**

---

## 5. The horizon problem — why an 18-day passage needs climatology, not just GRIB

The honest constraint the "weather buoy climate updates" instinct is reaching for:
**deterministic forecast skill falls off a cliff after ~7–10 days.** On an 18-day passage
the back half is *not* knowable from today's GRIB — it must be **climatology + updated en
route.** So Helm needs a second weather tier *above* the point forecast:

| Tier | Horizon | Source (open) | Use |
|---|---|---|---|
| **Deterministic forecast** | 0–10 days | GFS, ECMWF, GFS-Wave, RTOFS | the route you sail now |
| **Tropical-cyclone tracking** | live | NHC / JTWC public advisories | active storm tracks + forecast cones as a first-class **hazard layer with alarms** |
| **Climatology** | seasonal | NOAA / COGOW / pilot-chart data | historical wind roses, current climatology, **cyclone probability by month** for the route |
| **Seasonal / long-range outlook [LLM]** | weeks | climatology × current-season anomaly | plan the *passage window*, not the next 48 h |

The tropical layer is a **safety feature** for Pacific/ocean passages, not a nicety. The
climatology tier is what makes Helm trustworthy for *crossings specifically* — and it's a
clean differentiator, because the consumer apps are tuned for the deterministic window, not
the 18-day reality.

**[honesty]** Always show the **forecast horizon and confidence**. Day-15 "wind" is
climatology dressed as a number; label it as such. Never let a low-skill long-range value
wear the same clothes as a 24-hour forecast.

---

## 6. Data sources (all open / ownable)

- **Deterministic:** GFS, GFS-Wave, RTOFS, ECMWF open data — already the plan in
  [WEATHER.md](WEATHER.md) / [WEATHER-DATA.md](WEATHER-DATA.md); fetched today via
  `pipeline/fetch_weather.py` (Open-Meteo) and renderable offline.
- **Tropical:** NHC (Atlantic/E-Pacific) and JTWC (W-Pacific/Indian) public advisories +
  forecast cones.
- **Climatology:** NOAA climatology, COGOW ocean-wind climatology, digitized pilot-chart
  data. Cache alongside the region's chart mbtiles so it's available offline like everything
  else.
- **PredictWind / imported GRIB:** user-initiated import, labeled honestly as imported,
  device-local, excluded from any sync. **[honesty]**

---

## 7. What's LLM-derived — and the guardrails

Per the project's standing ethic, this section is explicit so it can never be quietly
violated. **Default to the latest Claude models** for cloud-side reasoning; the already-
structured nav/weather/AIS state is an ideal tool-use substrate.

**LLM-derived (advisory, narrated, sequenced):**
- Passage briefings and the spoken route-weather narrative (§2.3).
- The "what changed and does it matter" diff notifications (§3.2).
- Departure-window advice and routing interpretation (§4).
- Seasonal/long-range outlook synthesis (§5).
- "Explain this" on any weather pattern, chart object, or alarm.

**Never LLM-derived (computed, deterministic, testable):**
- Position `P(t)`, ETA, isochrones, XTE, VMG — from the nav core.
- CPA/TCPA and collision math — from the engine's `AisDecoder`.
- The actual wind/gust/swell/pressure values — from GRIB interpolation.
- Anchor drag, depth, threshold alarms — from sensor data + rules.

**The guardrails (non-negotiable):**
1. **Deterministic core, LLM narration on top.** A hallucinated CPA or fabricated wind speed
   is a safety failure. The LLM may *describe* the computed number; it may not *produce* it.
2. **Cite sources, show confidence, show data age.** Every briefing names its model (GFS vs
   ECMWF), its forecast horizon, and how old the data is. **[honesty]**
3. **Advise, don't act.** No LLM output changes a route, arms/disarms an alarm, or commands
   the autopilot without explicit human confirmation. First mate, not autopilot.
4. **Offline-aware, and says so.** Full reasoning dockside on wifi; a smaller on-device model
   + cached briefings offshore. Always explicit about which mode it's in — the back half of
   an ocean passage is exactly when there's no signal.
5. **Knows its limits.** When uncertainty is high or tropical activity is in play, the
   correct LLM output is "get a human router's eyes on this," not false confidence.

---

## 8. Build order

1. **Bind the scrubber to the boat** (§2.1) + **clickable route-point forecast** (§2.2) —
   pure wiring of existing pieces; ship in the web prototype first.
2. **Route-weather ribbon** (§2.3) — the highest-value view.
3. **Background ingestion + diff notifications** (§3) — backend + the [LLM] diff narrator.
4. **Isochrone router + polars + departure optimizer** (§4) — Phase-2 deterministic core,
   then the [LLM] interpretation layer.
5. **Tropical + climatology tiers** (§5) — open data layers + horizon/confidence honesty.
6. **Full copilot integration** — briefings, narration, "explain this," tied to
   [VISION.md](VISION.md) §8.

---

*This attacks the exact pain of a real passage: stop downloading, stop juggling tabs, stop
re-deriving by hand. The forecast follows the boat; the updates arrive as decisions, not
data; and the routing is easy where it can be and honest where it can't.*
