# Helm — Vision & UX Study

**What Helm could and should be: the world-class, AI-native client for the water.**

> Status: Vision draft v0.1 · 2026-06-24 · Owner: Steve Ridder
> Companion to [PRD.md](../PRD.md) (what we're building) and [COMPETITIVE.md](COMPETITIVE.md)
> (the field). This document is the *north star* — the product Helm grows into once the
> tracer bullet proves the magic. It is deliberately ambitious. Every claim is tagged
> **[ship]** (do it), **[earn]** (gated on partnership/scale/legal), or **[honesty]**
> (a constraint we must never paper over).

---

## 0. TL;DR — the one-paragraph vision

Helm today is a *fused chart* — satellite + S-52 ENC + the full weather catalog + live
nav + AIS on one offline screen. That is already something no competitor ships. But "one
fused screen" is the **floor**, not the ceiling. The world-class version of Helm is three
products braided into one: **(1) the calmest, most legible chartplotter on any Apple
device** — Apple-Maps-grade polish over OpenCPN-grade power; **(2) a "Smart Board" — a
Home-Assistant-style, fully user-composable boat dashboard** that turns NMEA/SignalK into
glanceable, alarmable, automatable instruments; and **(3) an AI-native copilot** that
answers "is it safe to leave at dawn?", drafts the passage, watches the anchor, and
narrates risk in plain language — wrapped in a **community layer** (places, tracks,
fleet, reviews) that borrows the best of NoForeignLand, ActiveCaptain, and Sea People
without their walls. Helm should feel less like OpenCPN and more like *if Apple, Windy,
and a very good first mate built a chartplotter together.*

---

## 1. Where Helm is today — an honest audit

The codebase is a **pre-alpha tracer bullet plus a serious headless engine**. It is
further along than "pre-alpha" implies on the things that are hard, and barely started on
the things that are merely laborious (UI surface area, persistence, native apps).

### 1.1 What actually works (proven in code)

| Domain | Reality | Where |
|---|---|---|
| **Fused chart canvas** | MapLibre style composites satellite + NOAA raster + S-52 ENC + depth + route + AIS + places, with Day/Dusk/Night reskin | `web/style.json`, `web/index.html` |
| **Real headless nav** | OpenCPN's actual `Routeman` driven headless: route activation, waypoint advance, BRG/DTW/XTE per fix, streamed over WebSocket ~1 Hz | `engine/vendor/cli/helm_engine.cpp` |
| **Live data ingestion** | NMEA 0183 over TCP:10110 (RMC/DPT/DBT/MWV/HDT), SignalK WebSocket client, real `AisDecoder` with CPA/TCPA — all per-field source-tagged | `helm_engine.cpp` |
| **Live S-52 tiles** | Real NOAA S-57 cell rendered headless to PNG tiles over HTTP:8082, composited under live nav | `engine/vendor/cli/helm_tiles.cpp` |
| **Weather, Windy-class** | Animated WebGL wind particles (7k, 60fps), scalar heatmaps (wind/gust/rain/temp/cloud/pressure/CAPE/waves/swell/SST/current), RainViewer radar, pressure isobars, forecast time-scrubber | `web/wind-layer.js`, `field-layer.js`, `radar.js`, `isolines.js` |
| **On-demand pipeline** | bbox → mbtiles tiler; Open-Meteo multi-layer weather; OSM/Overpass places; GDAL S-57 depth extraction | `pipeline/*.py`, `extract_depth.sh` |
| **Honesty primitives** | Nav-source badge (LIVE / SIM / ENGINE·SIM POS / ENGINE LOST) never fakes a dropped feed; per-field source tooltips | `web/index.html`, `nav-source.js` |
| **Canonical design system** | Pixel-perfect glass UI across macOS/iPad/iPhone, with real S-52 conventions, Day/Dusk/Night | `docs/mockups/*.html` |

This is a **strong foundation**: the two genuinely hard bets — reusing OpenCPN's nav core
headless, and rendering real S-52 — are *de-risked*. The honesty discipline (never badge a
simulated position as truth) is already baked in and must be preserved as a core value.

### 1.2 What's missing today (the gap)

The web app is a **read-only demo**. Everything that makes a chartplotter a *tool you
operate* is absent:

- **No persistence** — settings, layer state, units, theme all reset on reload.
- **No route/mark/track creation or editing** — routes load only from a GPX file at
  engine start; you cannot tap the chart to drop a waypoint, drag a leg, or save a track.
- **No alarms** — AIS vessels are *colored* by CPA but nothing *alerts*; no guard zone,
  no anchor watch, no depth/XTE/arrival alarm, no MOB, no SART handling.
- **No native apps** — iOS/iPadOS/macOS SwiftUI shells don't exist yet; the "client" is
  a browser page.
- **No Smart Board** — instruments are a fixed bottom bar; nothing is composable,
  resizable, or user-arranged.
- **No community/social layer** — places render but there's no detail card, no reviews,
  no pins, no fleet, no track sharing.
- **No AI anything** — no copilot, no natural-language search, no command palette
  (the ⌘K is a painted affordance), no smart routing, no anomaly detection.
- **No weather routing** — own isochrone router and polars are documented, not built.
- **No tides/currents prediction, no plugin SDK, no chart-download UX, no onboarding.**

The rest of this document is about turning that gap into a **world-class** product, not
just a feature-complete one.

---

## 2. The thesis — five surfaces, one helm

Today the app is "a chart with panels." The world-class Helm is **five coherent surfaces**
sharing one canvas, one design language, and one brain:

```
                         ┌──────────────────────────────┐
                         │      THE HELM COPILOT  🧠      │  ← AI-native layer, threads through all
                         │  natural language · routing   │
                         │  watchkeeping · narration     │
                         └───────────────┬──────────────┘
            ┌───────────────┬────────────┼────────────┬───────────────┐
            ▼               ▼            ▼             ▼               ▼
       ┌─────────┐   ┌────────────┐ ┌─────────┐ ┌────────────┐ ┌────────────┐
       │  CHART  │   │ SMART BOARD│ │ WEATHER │ │ COMMUNITY  │ │  VOYAGE    │
       │ the nav │   │ your boat  │ │ & router│ │ places ·   │ │ planning · │
       │ canvas  │   │ dashboard  │ │         │ │ fleet ·    │ │ logbook ·  │
       │         │   │ (HA-style) │ │         │ │ reviews    │ │ checklists │
       └─────────┘   └────────────┘ └─────────┘ └────────────┘ └────────────┘
            └───────────────┴────────────┬────────────┴───────────────┘
                              one shared offline-first core
```

Each surface is detailed below with **what world-class means**, **what to borrow from
whom**, and **the concrete backlog**.

---

## 3. Design system & UX principles

Helm already has a strong visual identity (calm glass chrome, recede-don't-shout, S-52
chart truth, Day/Dusk/Night as a first-class control). The world-class bar adds:

### 3.1 Principles (the non-negotiables)

1. **Chart-first, full-bleed.** Chrome is a guest on the chart. Panels are glass that
   dims and recedes underway; the map is always the hero. *(Borrow: Apple Maps, Orca.)*
2. **Legible at arm's length, in spray, with one wet hand.** Tabular numerals, big touch
   targets (≥44pt underway, scaling up at speed), high-contrast night mode that protects
   dark adaptation (true red-on-black, not "dimmed day"). *(Borrow: Garmin helm displays,
   aviation EFBs like ForeFlight.)*
3. **Calm by default, loud only when it matters.** The UI whispers; alarms shout. A CPA
   breach, a depth alarm, a drag — these earn motion, color, sound, haptics. Nothing else
   does. *(Borrow: ForeFlight's hazard alerting restraint.)*
4. **Honesty is a feature, not a disclaimer.** The source badge, the "satellite is
   supplemental" watermark, the "imported — not live" label on PredictWind data: these
   are *trust infrastructure*. Never hide provenance. **[honesty]**
5. **Glanceable hierarchy.** At a glance: where am I, where am I going, what's the danger.
   One tap deeper: the numbers. Two taps: the controls. *(Borrow: Apple Watch complications.)*
6. **Same product everywhere, native everywhere.** A macOS power surface and a one-handed
   iPhone underway view are the *same app's* dialects, not different apps. *(Borrow: how
   Things / Fantastical scale one model across Apple platforms.)*
7. **Composability over configuration.** Don't bury power in Settings; let users *build*
   their view (the Smart Board thesis). *(Borrow: Home Assistant, iOS widgets.)*

### 3.2 The design tokens (formalize what the mockups already imply)

- **Palette:** glass `rgba(13,19,27,.74)`, accent `#5bc0ff`, route-magenta `#d6219a`,
  PredictWind-mint `#54f0ad`, ok-mint, warn-amber, danger-red. Three full chart schemes
  (Day/Dusk/Night) that reskin *both* raster basemap and vector symbology.
- **Type:** SF Pro, tabular numerals everywhere a number can change.
- **Iconography:** Tabler/SF Symbols, single-weight line icons.
- **Motion:** 120ms for chrome; particle/weather animation is the only persistent motion;
  alarms get a distinct, attention-grabbing motion vocabulary reserved for them.
- **Materials:** consistent `blur(22px)` glass, hairline `.5px` borders, deep soft shadows.

**[ship]** Extract these into a single design-token file (`web/tokens.css` → later a Swift
`HelmTheme`) so every surface and platform stays pixel-consistent.

---

## 4. Surface 1 — The Chart (the nav canvas)

The chart is mostly *there*. World-class is the difference between "renders correctly" and
"feels like the best map app you've ever used, that happens to be a chartplotter."

### 4.1 What world-class adds

- **Direct manipulation routing.** Tap to drop a waypoint; long-press a leg to insert;
  drag a waypoint and watch BRG/DTG/ETA recompute live; rubber-band a whole route. Snap to
  buoys/marks. Edit, reverse, split, save, name. *This is the single biggest functional
  gap.* **[ship]** *(Borrow: Savvy Navvy's "draw a line" simplicity + Aqua Map precision.)*
- **Smart auto-routing with honesty.** "Route me to Marina" → a depth-aware, hazard-aware
  suggested route the user *confirms leg by leg*, with every assumption shown (draft,
  safety contour, what it avoided). Never a black box. **[ship]** *(Borrow: Savvy Navvy /
  Navionics Dock-to-dock — but show your work.)*
- **Heading-up / course-up / north-up** with a buttery rotation, look-ahead offset at
  speed (own-ship sits low, more chart ahead), and auto-zoom-to-speed. *(Borrow: car nav,
  Orca.)*
- **The "radar overlay" of context:** range rings, EBL/VRM (electronic bearing line /
  variable range marker), a tactical CPA vector cone for AIS targets, a predicted-position
  "where will I be in 6 min" ghost. *(Borrow: real radar/MFD helm units.)*
- **Object query that's a *card*, not a popup.** Tap a buoy → a rich card: full S-57
  attributes in plain language ("Red can buoy '4', flashing red 4s, marks port side of
  channel"), not a raw attribute dump. Tap a depth → contour context. **[ship]**
- **Quilting & chart-group UX** that's invisible when it works and explicit when you want
  control (which cell, which scale, why this chart). **[earn]** (needs S-52 engine, Phase 2)
- **Measure / route-preview tools** always a thumb away: distance+bearing ruler, "what's
  my ETA there at current SOG", clearance/air-draft checks.
- **Track recording** with breadcrumb, auto-log, and "retrace my track home" — critical
  for fog/night reef exits. **[ship]**

### 4.2 The two-renderer reality **[honesty]**

MapLibre cannot render S-52; the dedicated S-52 engine composites on top (already proven
in `helm_tiles.cpp`). The UX must make the seam invisible: one set of controls, one theme
switch driving both renderers, no flicker on pan/zoom. This is load-bearing, not a nicety.

---

## 5. Surface 2 — The Smart Board (the "starboard")

**This is the feature you described as "starboard like what I have with Home Assistant"
— and it's a genuine differentiator no marine app does well.**

Every chartplotter has "instruments." They are all *fixed*: a vendor decides you get
SOG/COG/Depth/Wind in this order, this size, forever. Home Assistant proved the opposite
model wins: **the user composes their own dashboard from widgets, and it adapts to
context.** Helm should bring that to the helm.

### 5.1 The concept

A **Smart Board** is a user-composable grid of **tiles** ("instruments + cards +
automations") that you build like a Home Assistant Lovelace dashboard or the iOS widget
gallery — but tuned for the water and driven by your live NMEA/SignalK data.

```
┌─ SMART BOARD: "Underway" ────────────────────────────────────────┐
│  ┌────────┐ ┌────────┐ ┌──────────────┐ ┌───────────────────────┐ │
│  │  SOG   │ │  TWS   │ │ WIND ROSE    │ │  NEXT WAYPOINT         │ │
│  │  6.2kn │ │ 14 kt  │ │   (gauge)    │ │  R"4" · 0.3NM · 11:42  │ │
│  └────────┘ └────────┘ └──────────────┘ └───────────────────────┘ │
│  ┌──────────────────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐  │
│  │ DEPTH + history spark │ │  VMG   │ │  BATT  │ │ TANK levels  │  │
│  │  8.4m  ▁▂▃▅▇          │ │  5.1kn │ │ 12.6V  │ │ ▓▓▓░ fuel    │  │
│  └──────────────────────┘ └────────┘ └────────┘ └──────────────┘  │
└──────────────────────────────────────────────────────────────────┘
   [ Underway ]  [ At Anchor ]  [ Racing ]  [ Engine ]  [ + ]   ← boards
```

### 5.2 What makes it world-class

- **User-composable, drag-to-build.** Pick from a tile gallery, drag onto a grid, resize,
  reorder. Save multiple boards. *(Borrow: Home Assistant Lovelace, iOS widget editor,
  Garmin's customizable data pages — but make it actually pleasant.)*
- **Context-switching boards.** Boards auto-activate by *mode*: "Underway" while sailing,
  "At Anchor" when anchored (anchor-watch front and center), "Engine/Motoring", "Racing"
  (start-line timer, lay lines, polars, target boatspeed), "Night" (red, minimal),
  "Docking". *(Borrow: Apple Watch "Smart Stack", car drive modes.)*
- **Any SignalK path is a tile.** Because the engine already speaks SignalK, *anything* on
  the boat's network can become a tile: tank levels, battery banks, bilge, engine RPM/temp,
  fridge temp, AC, autopilot state. This is where Helm becomes a **boat cockpit, not just a
  chartplotter.** **[ship]** *(Borrow: Home Assistant's "everything is an entity.")*
- **Tiles carry history + spark + trend.** A depth tile shows the last N minutes; battery
  shows discharge curve; wind shows a rose with gust/lull range. *(Borrow: WeatherKit /
  Health app sparklines.)*
- **Tiles can alarm.** Any numeric tile can carry thresholds → notification + haptic +
  sound. Depth < 3m, battery < 11.8V, wind > 25kt, anchor drag > 30m. **[ship]**
- **Automations (the Home Assistant magic).** "When wind > 30kt AND I'm at anchor, alert
  me and start logging." "When depth < safety contour, flash the chart." "At sunset, switch
  to Night board." A simple, safe trigger→condition→action rule builder. **[earn]**
- **Glance surfaces everywhere.** The same tiles power the iPhone glance card, the Apple
  Watch complications, the macOS menu-bar/Today widget, CarPlay/lock-screen. Build once,
  glance everywhere. **[ship]**

### 5.3 Why this is strategic

Orca and Savvy Navvy own "modern nav." **Nobody owns "modern boat dashboard."** The Smart
Board is the wedge that makes Helm the app you keep open *at anchor and at the dock*, not
just underway — which is where engagement, retention, and the community layer live.

---

## 6. Surface 3 — Weather & Routing

The weather *rendering* is already best-in-class for a prototype. World-class is about
**decision support**, not just pretty layers.

- **The forecast scrubber becomes a story.** Scrub time and the *whole picture* moves —
  wind, your route's exposure, ETA at each waypoint under that forecast, the swell you'll
  punch into on leg 3. Weather and route are *coupled*, not parallel. **[ship]**
- **"Weather along my route" ribbon.** A timeline strip: for the planned passage, show
  wind/gust/sea-state/rain at each hour *at the boat's projected position* — the single
  most useful passage-planning view, and almost nobody does it well. **[ship]**
  *(Borrow: PredictWind's departure planner + Windy's route forecast, fused on the chart.)*
- **Own isochrone router + polars.** The documented Phase-2 router: GRIB + boat polars →
  optimal route, with a polar editor and "what-if" departure-time comparison. Show
  confidence, show the assumptions. **[earn]** *(Borrow: qtVlm, PredictWind — open it up.)*
- **Departure advisor (AI-assisted, see §8).** "Best window to leave for X in the next 5
  days" with plain-language reasoning. **[earn]**
- **PredictWind / GRIB import**, labeled honestly as imported and device-local. **[honesty]**
- **Multi-model honesty.** When we show GFS vs ECMWF vs local, *say which* and show
  spread/agreement — disagreement between models is itself decision-relevant. **[honesty]**

---

## 7. Surface 4 — Community & Social

You named the inspirations: **Sea People, NoForeignLand, ActiveCaptain**. The honest
reality (documented in [integrations/noforeignland.md](integrations/noforeignland.md)) is
that these are **walled** — no read APIs. So the strategy is: **build the open substrate,
own the contributed data, and interoperate where sanctioned.**

### 7.1 The Places layer → rich community

- **Open-data base** (OSM/Overpass + OpenSeaMap), cached offline alongside charts —
  already fetched by `fetch_places.py`. **[ship]**
- **Rich detail cards** (not the current bare popup): photos, depth/holding, shelter by
  wind direction, services, reviews, "navigate here", "last updated". *(Borrow:
  ActiveCaptain anchorage cards + Navily — the gold standard for anchorage detail.)* **[ship]**
- **Helm-owned pins & reviews** stored in *our* backend → over time this becomes Helm's
  community moat (the one dataset no one can wall off from us because we own it). **[earn]**
- **Anchorage intelligence:** crowdsourced + computed shelter analysis ("good in NE-SE,
  exposed to SW swell"), holding reports, "boats here now" count. *(Borrow: Navily,
  ActiveCaptain.)* **[earn]**

### 7.2 Fleet & social (the Sea People / NFL layer)

- **NFL push** (sanctioned): your boat appears for friends on NoForeignLand via your own
  key. **[ship]**
- **Helm fleet:** opt-in position sharing with *your* people — buddy boats, your family
  ashore watching your passage, a flotilla. Live track, ETA, "arrived safe" auto-ping.
  *(Borrow: Sea People's social presence + Find My's calm sharing model.)* **[earn]**
- **Voyage sharing:** a beautiful, shareable passage recap (track + stats + photos +
  weather you sailed through) — the Strava-for-sailing artifact that drives organic
  growth. *(Borrow: Strava, Sea People.)* **[earn]**
- **Logbook → social, gently.** Auto-logged passages become shareable stories; reviews
  you write enrich the community places layer. The social loop is a *byproduct* of using
  the tool, not a separate chore. **[earn]**

**[honesty]** Privacy is paramount on a *location* app: sharing is opt-in, scoped, and
revocable; "share with everyone" and "share with my 3 buddy boats" are very different
defaults. Off by default. Never sell or expose location.

---

## 8. Surface 5 — The AI-native copilot 🧠

This is the layer that makes Helm "**AI-native**," not "an app with a chatbot bolted on."
The copilot threads through every other surface. Modern Claude models (the engine already
has a sophisticated headless data backbone to feed them) make this genuinely buildable.

### 8.1 The principle

**The copilot is a first mate, not an autopilot.** It *advises, drafts, watches, and
explains* — the human always confirms anything that affects safety or the boat. Every AI
output shows its reasoning and its sources. **[honesty]**

### 8.2 What it does (in rough order of value)

1. **Natural-language command & search (the real ⌘K).** "Take me to the fuel dock in
   Papeete." "Show me wind for tomorrow afternoon." "Where's the nearest all-weather
   anchorage with good holding?" "Hide everything except depth and AIS." The command
   palette becomes a *conversational* control surface over the whole app. **[ship — start here]**
2. **Passage briefing.** "Brief me on the run to Moorea." → a plain-language summary:
   distance, ETA, the weather window, the hazards on the route, tidal gates, where it gets
   uncomfortable, what to watch. Generated from the *fused* data Helm already has. **[earn]**
3. **Departure advisor.** "Should I leave at dawn or wait for Thursday?" with model-backed
   reasoning and the tradeoffs spelled out. **[earn]**
4. **The watchkeeper.** Underway and at anchor, the copilot watches the same streams the
   Smart Board does and *narrates risk*: "A vessel crossing will pass 0.3 NM ahead in 8
   minutes." "Wind has backed 20° and built to 28kt — your anchor scope is now marginal."
   Plain language on top of the deterministic CPA/alarm math (which stays the source of
   truth). **[earn]**
5. **Explain-this.** Tap any chart object, weather pattern, or alarm → "what does this
   mean and what should I do?" — turning S-57 jargon and meteorology into seamanship.
   *(This is huge for newer sailors and a genuine safety win.)* **[ship]**
6. **Smart logbook.** Auto-narrated passage log ("Departed 06:14, motored out of the
   lagoon, sailed close-hauled in 12-16kt..."), drafted from the track + instrument data,
   editable by the human. **[earn]**
7. **Maintenance & checklists.** "Pre-departure checklist for an offshore passage," boat-
   specific over time. **[earn]**

### 8.3 Architecture notes **[honesty]**

- **Deterministic core, AI narration on top.** CPA/TCPA, XTE, anchor drag, depth alarms
  are *computed* (they already are, in `helm_engine.cpp`) — the AI explains them, it never
  *replaces* the math. A hallucinated CPA would be a safety failure.
- **On-device where possible, offline-aware always.** Offshore = no signal. The copilot
  degrades gracefully: full power dockside on wifi, a smaller on-device model + cached
  briefings offshore. Be explicit about which mode you're in.
- **Cite sources, show confidence.** Every briefing names its GRIB model, its chart cell,
  its data age. Never present a guess as a fact.
- **Default to latest Claude models** for the cloud-side reasoning; the rich, already-
  structured nav/weather/AIS state is an ideal tool-use substrate.

---

## 9. Platform matrix — native everywhere

The "client" is not one screen; it's a family. World-class means each Apple surface gets
the *right dialect* of the same product.

| Platform | The role | Killer surface |
|---|---|---|
| **macOS** | Planning & power. Multi-window, menus, drag-drop GPX/GRIB/mbtiles, serial NMEA, the big chart table. | Voyage planning, route building, the full Smart Board editor. **[ship]** |
| **iPadOS** | *The helm tablet.* Touch-first, floating rail, big instrument tiles, mounted at the nav station. | Underway chart + Smart Board, split-view chart/weather. **[ship]** |
| **iPhone** | One-handed underway + always-in-pocket. Glance card, route bottom-sheet, layers FAB. | Quick glance, anchor watch in your bunk, "arrived safe" ping. **[ship]** |
| **Apple Watch** | The wrist glance. Anchor-watch alarm that *wakes you*, MOB, key instruments as complications. | Anchor drag alarm on your wrist at 3am — a genuine safety feature. **[earn]** |
| **CarPlay / lock screen / widgets** | Glance without opening the app. Next waypoint, ETA, wind, depth, anchor status as Live Activity / widget. | Dynamic Island "Route to Marina · 0.3 NM." **[earn]** |
| **Vision Pro (someday)** | Spatial chart table, heads-up AIS. Speculative — note it, don't chase it. **[earn]** |

**[honesty]** iOS has no serial/USB — connectivity is SignalK / NMEA-over-TCP-UDP / BLE /
internal GPS; autopilot output over the network. Serial only on macOS. This is real and
shapes the iOS connectivity UX (it's network-discovery-first).

---

## 10. Information architecture & navigation

A single coherent model across platforms:

- **The map is home.** Everything else is a layer, a sheet, or a board *over* the map.
- **Left rail (mac/iPad) / tab bar (iPhone):** Chart · Routes/Voyage · Weather · Smart
  Board · Community · (More). The current rail (chart/layers/weather/routes/ais/places/
  download/settings) is close — promote **Smart Board** and **Community** to first-class,
  demote download into Charts management.
- **Command palette (⌘K / long-press)** is the universal accelerator *and* the copilot
  entry — the same box does fuzzy "go to" and natural language.
- **Sheets, not modal mazes.** Bottom sheets on iPhone, inspectors on iPad/mac, all
  draggable, all dismissible to the chart. (The draggable route inspector already models
  this.)
- **Underway mode is a global state, not a screen.** When moving, chrome recedes, fonts
  grow, the active board surfaces, alarms arm. Tapping wakes the controls; idle hides them.

---

## 11. Onboarding & first-run

Currently: none. World-class onboarding earns trust fast and proves the magic in 60
seconds:

1. **"Show me the fusion" hero.** Drop the user on a gorgeous fused scene (their location
   if available) — satellite + depth + live wind — before any signup. The wow *is* the
   pitch.
2. **Connect your boat (optional, skippable).** Auto-discover SignalK/NMEA on the local
   network; or "just use my phone's GPS." Honest about what's connected.
3. **Build your first board** from a template ("Sailing", "Power", "At anchor").
4. **Download your home waters** for offline (lasso → mbtiles), so the first time they
   lose signal, it just works.
5. **Set the boat profile** (draft, air-draft, polars later) — feeds safety contours and
   routing.

*(Borrow: the calm, progressive onboarding of Apple's own apps; skip the 12-screen tour.)*

---

## 12. Competitive teardown — what to steal from whom

| Source | Steal this | Don't |
|---|---|---|
| **Apple Maps / car nav** | Look-ahead camera, calm rerouting, glance hierarchy, polish | Their lack of marine data |
| **Orca** | Modern hybrid satellite charts, sail routing UX, hardware-grade feel | The hardware lock-in |
| **Savvy Navvy** | "Draw a line" routing simplicity, weather-aware passage planning | The chart-subscription model |
| **Navionics / Navily / ActiveCaptain** | Anchorage detail cards, community reviews, dock-to-dock | Their walls; their dated UX (ActiveCaptain) |
| **Windy** | The layer catalog, the particle aesthetic, route forecast | Online-only, logo-mandatory, no compositing **[honesty]** |
| **PredictWind** | Departure planner, route weather, polars | Closed ecosystem (no API — import only) **[honesty]** |
| **ForeFlight (aviation EFB)** | Alarm restraint, briefing UX, "I trust this in an emergency" gravitas | n/a |
| **Home Assistant** | The composable dashboard, "everything is an entity", automations | Its configuration complexity — make ours *pleasant* |
| **Sea People / NoForeignLand** | Fleet presence, voyage sharing, the cruiser community loop | Their walled data — build open + owned **[honesty]** |
| **Strava** | Shareable activity recap as a growth engine | Over-gamification |
| **Apple Watch** | Complications, Smart Stack, glance-first | n/a |

---

## 13. Safety, trust & honesty (the things we must never break)

These are the spine of the brand. They are already present in the code as *values* — keep
them as the product scales:

1. **Never fake a feed.** The LIVE/SIM/LOST badge logic is sacred. A dropped real feed is
   an *alarm*, never a silent fallback to plausible fiction. **[honesty]**
2. **Satellite is supplemental.** Permanent "cross-reference official charts" treatment on
   imagery and depth-on-satellite. Conservative SDB shading. **[honesty]**
3. **AI advises, the human commands.** No AI action touches safety without confirmation;
   every AI claim is sourced and dated. **[honesty]**
4. **Deterministic safety math.** CPA/TCPA, anchor drag, depth, XTE alarms are computed
   and tested, never AI-guessed. **[honesty]**
5. **Provenance everywhere.** Imported PredictWind data labeled and device-local; weather
   model named; chart cell/scale shown; data age visible. **[honesty]**
6. **Privacy by default.** Location sharing is opt-in, scoped, revocable, never sold.
7. **Offline-first is a safety feature.** The places people sail have no signal; *every*
   surface degrades gracefully and says so.

---

## 14. Prioritized backlog — turning vision into sprints

Sequenced so each phase ships something *usable* and each builds on the proven core.

### Phase A — Make the demo a tool (operate the chart)
- [ ] **Persistence layer** (settings, layer state, theme, units, boards) — unblocks all.
- [ ] **Route/mark/track creation & editing** on the chart (tap, drag, insert, save, name).
- [ ] **Track recording** + "retrace home".
- [ ] **Real alarms:** AIS CPA/TCPA guard zone, depth, XTE, arrival, anchor watch, MOB.
- [ ] **Rich object-query cards** (plain-language S-57).
- [ ] **Settings that exist:** NMEA/SignalK source config, boat profile, units, alarms.

### Phase B — The Smart Board
- [ ] Tile model + drag-to-build grid + tile gallery.
- [ ] Core instrument tiles (SOG/COG/wind/depth/VMG/heading/position/next-WP) with sparks.
- [ ] Any-SignalK-path tile (tanks/battery/engine/bilge).
- [ ] Per-tile thresholds → alarms; context-switching boards (Underway/Anchor/Racing/Night).
- [ ] Glance surfaces: iPhone glance card, Watch complications, widgets/Live Activity.

### Phase C — Native apps + polish
- [ ] SwiftUI/MapLibre shells (macOS → iPad → iPhone), shared C++ core wired in.
- [ ] Heading-up / look-ahead / auto-zoom-to-speed, underway mode, night-vision night theme.
- [ ] Onboarding flow + offline-region download UX.
- [ ] Command palette (fuzzy "go to" first).

### Phase D — Weather decision support + routing
- [ ] Route-coupled forecast scrubber + "weather along my route" ribbon.
- [ ] Own isochrone router + polar editor; departure-time comparison.
- [ ] Tides/currents harmonics.

### Phase E — Community
- [ ] Rich places cards + Helm-owned pins/reviews backend.
- [ ] NFL push; Helm fleet (scoped position sharing); voyage-recap sharing.
- [ ] Anchorage intelligence (shelter/holding).

### Phase F — AI-native copilot
- [ ] Conversational command palette (natural-language control + search). *(Start in A/C.)*
- [ ] Explain-this on chart objects/weather/alarms.
- [ ] Passage briefing + departure advisor (cloud, sourced).
- [ ] Watchkeeper narration over the deterministic alarm core.
- [ ] Smart logbook.

*(Phases A–C are the "make it a real, world-class chartplotter" core. D–F are the
"why Helm wins forever" differentiators. They can overlap; the conversational palette in F
can start as early as A because it's mostly a thin layer over existing commands.)*

---

## 15. North-star metrics

What "world-class" looks like in numbers:

- **The acid test (from the PRD):** Steve plans and sails a real passage on Helm alone —
  no Windy, no PredictWind, no chart app. *Extend it:* and never opens the boat's vendor
  MFD app either, because the Smart Board is better.
- **Time-to-wow < 60s** from first launch (the fused hero scene).
- **Days-open-per-week > underway-days** — proof the Smart Board + community make Helm the
  app you keep open at anchor and at the dock, not just sailing.
- **Zero "silent wrong" incidents** — the honesty primitives never let a stale/fake
  reading masquerade as truth. This number must stay at zero.
- **Anchor-watch alarms that actually wake people** (Watch/phone) — the feature people
  *tell their friends about.*
- **Community contribution rate** — % of users who drop a pin / review / share a voyage:
  the leading indicator of the owned-data moat.

---

## 16. Open questions

- **Smart Board automation depth:** how far toward Home Assistant's rule engine before it
  becomes a configuration burden? (Lean: curated triggers, not a scripting language.)
- **Copilot offline model:** what's the smallest on-device model that gives useful
  briefings with no signal, and how do we set expectations at the boundary?
- **Community backend cost & moderation:** owned pins/reviews mean we own moderation, spam,
  and liability for user-contributed nav info. Scope carefully.
- **Fleet-sharing privacy model:** the defaults here are a trust make-or-break.
- **Where AI narration ends and regulated nav advice begins** — keep the copilot firmly in
  "first mate who explains," never "the authority you blame."
- **Watch/Live-Activity background-execution limits** vs. anchor-watch reliability — the
  alarm must fire even when iOS wants to sleep the app.

---

*This is a living document. It describes the mountain, not the next step. The next step is
still the tracer bullet: one fused screen that feels worth using. Everything above is what
that screen grows into once it proves itself.*
