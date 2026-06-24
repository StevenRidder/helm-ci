# Helm — The Spacetime Probe

**Every layer is part of the space/time slice. Pick a point (or a path, or a region) in
space and time, and Helm fuses *all* layers there into one source-tagged slice that the AI
agent narrates.**

> Status: **Committed** ([ADR-0007](decisions/0007-spacetime-probe.md)) · spec v0.1 ·
> 2026-06-24 · Owner: Steve Ridder
> The generalization of two things we'd already written per-domain — the *weather* field
> ([WEATHER-ROUTING.md §1](WEATHER-ROUTING.md), `W(lat,lon,t)`) and the *destination* dossier
> ([BRIEFINGS.md](BRIEFINGS.md)) — into one primitive: **any** layer, **any** point in
> spacetime, fused and narrated. Realized in code by [../backend/context.py](../backend/context.py)
> (`resolve_context`) + `/context` + `/narrate`, narrated by
> [../backend/agents.py](../backend/agents.py) (`narrate_context`).
> Honesty spine: deterministic facts computed, the agent narrates; cite + date + confidence;
> respect every source wall; supplemental-not-primary; offline-aware.

---

## 1. The idea

Helm's data is not a pile of separate apps or even separate overlays — it is **one fused
field over space and time.** Weather already is (`W(lat, lon, t)`). The insight here is that
*everything else is too*: depth, places, reviews, saved pins, climate, tides, AIS, the
NFL slot — each is a **function of where and when.**

So the core query is a point in spacetime, and the core answer is a **slice**: the value of
*every* layer at that point, source-tagged, which the agent then narrates.

```
  query  = a point (lat, lon, t)   ·or·  a path P(t) (your route)   ·or·  a region (bbox, t)
                                   │
                                   ▼
            ┌──────────────  THE SLICE  ──────────────┐
            │  every layer sampled at the query,       │
            │  each tagged {value, source, freshness,  │
            │  confidence}                             │
            └───────────────────┬─────────────────────┘
                                ▼
                   ReAct narrator (agent) → plain-language briefing, cited, honest
```

This is why "tap a point, scrub a time → it narrates the weather, climate, NFL data, the
anchorage reviews, the depth" is a *single call*, not a feature per data type.

---

## 2. The rule — any layer is part of the slice

**A layer is not "done" until it can answer `sample(lat, lon, t)`.** Every layer in Helm has
**two faces**:

1. a **visual face** — how it draws on the chart (a MapLibre layer, the S-52 engine, a
   particle field); and
2. a **probe face** — a uniform contract so it can join the slice and be narrated.

```
LayerSample = {
  layer:      "wind" | "gust" | "swell" | "depth" | "places" | "reviews" | "saved"
            | "climate" | "tide" | "current" | "ais" | "nfl" | "chart" | "route" | …,
  value:      <any structured value at the point/time>,   // COMPUTED, never invented
  source:     "open" | "owned" | "rag" | "nfl" | "engine",
  sourceRef:  { title, url? },
  freshness:  ISO timestamp / "climatology" / "live",
  confidence: "low" | "fair" | "good",
  horizon?:   forecast horizon note (time layers),
  locked?:    true if gated (e.g. NFL experimental/partnership)
}

Slice = { point|path|region, samples: LayerSample[], sources[], disclaimer }
```

The same toggle that shows/hides a layer on the chart (the **selectable layers**, like
weather) doubles as **"include this layer in the slice?"** — so the user composes both what
they see *and* what gets narrated.

> **Architectural mandate (ADR-0007):** any new layer — a plugin radar feed, a tide model, a
> satellite-derived bathymetry tile, a community data source — must implement the probe
> contract. If it can be drawn, it can be sliced; if it can be sliced, it can be narrated.

---

## 3. The layers (current + planned)

Everything is a layer in the slice. Status is for the **probe face** (narration), separate
from whether it already *draws*.

| Layer | Source tier | Probe status |
|---|---|---|
| Wind / gust / swell / wave / rain / pressure / current / SST / CAPE | open (GRIB/Open-Meteo) | **live** via `get_weather` (wind/gust/wave); rest to extend |
| Climate / tropical-cyclone | open (NOAA/COGOW/NHC/JTWC) | **stub** → real climatology tier ([WEATHER-ROUTING §5](WEATHER-ROUTING.md)) |
| Depth / chart (S-52) | open (NOAA ENC) | pointer now ("see chart"); **TODO** depth-at-point from the engine |
| Tides & currents | open (harmonics) | **TODO** |
| Places (marinas/anchorages/fuel/services) | open (OSM/OpenSeaMap) | **live** via the place store |
| Reviews | owned + rag | **live** (owned) + cited RAG |
| Saved places (your pins) | owned | **live** |
| AIS targets | engine | **TODO** (CPA/TCPA already computed in the engine) |
| Route / route-weather | engine + weather | **TODO** (couple `W(P(t),t)`) |
| Satellite imagery | open (Sentinel-2) / BYO | visual only; supplemental |
| **NoForeignLand** | walled | **locked** slot — experimental/partnership only ([ADR-0005](decisions/0005-community-places-overlay.md)) |

---

## 4. Query modes (one primitive, several shapes)

- **Point** — tap the chart → slice at `(lat, lon, now)` → narrate "what's here, now."
- **Point + time** — tap + scrub the timeline → slice at `(lat, lon, t)` → "what it'll be like
  here, then."
- **Path `P(t)`** — your route → a *sequence* of slices along the worldline → the passage
  briefing ([WEATHER-ROUTING §2](WEATHER-ROUTING.md)) and the route-weather ribbon.
- **Destination** — a place + your ETA → the slice that fills the dossier ([BRIEFINGS.md](BRIEFINGS.md)).
- **Region** — a bbox + time → "what's notable in this area" (where-to-go candidates).

All four are the **same** resolve→narrate pipeline at different geometries. The destination
dossier and the passage briefing are not separate engines — they are the spacetime probe
applied to a place and to a path.

---

## 5. The narrator

The ReAct agent ([agents.py](../backend/agents.py) `narrate_context`) turns a slice into
2–4 plain sentences:

> *"At 24.55°N 81.80°W, Thu 20:00: wind ~22 kt from the NE gusting 28, seas ~1.4 m. Nearest:
> Garrison Bight (0.7 NM) — 'held well in a 25 kt norther' (SV Halcyon). Late dry season, low
> cyclone risk. NoForeignLand data: locked (experimental). Cross-reference the S-52 chart for
> depth. Verify on official charts."*

**Honesty is structural, not cosmetic:**
- The agent may only narrate the **values the layers returned** — never invent a fee, depth,
  holding, or forecast; gaps are "verify locally."
- Each clause traces to a `source` + `freshness`; time layers carry a **horizon/confidence**.
- **Walled layers stay locked** (NFL) and are *named as locked*, never silently dropped or
  faked.
- Satellite/SDB layers are **supplemental** — the narration says so.
- Deterministic core, agent on top: the numbers are computed; the agent sequences and speaks
  them.

---

## 6. Mapping to code (today)

| Concept | Code |
|---|---|
| Slice resolver | [`backend/context.py`](../backend/context.py) `resolve_context(lat, lon, t, …)` |
| Narrator | [`backend/agents.py`](../backend/agents.py) `ResearchAgent.narrate_context` |
| Endpoints | `POST /context` (the fused slice) · `POST /narrate` (the narration) |
| Weather probe | `agents.get_weather` (Open-Meteo, live) |
| Places/reviews/saved probe | `backend/store.py` |
| Selectable layers (visual + slice filter) | `web/style.json` + `web/community.js` toggles |
| NFL locked slot | `context.py` (`nfl_enabled` flag, off by default) |

---

## 7. Build order to "any layer, fully"

1. **Wire the probe into the chart** — tap a point (+ scrub time) → `/narrate` → a slice card.
2. **Promote more weather fields** into `get_weather` (swell/rain/pressure/current/SST/CAPE).
3. **Depth-at-point** from the engine + **tides/currents** harmonics into the slice.
4. **AIS + route-weather** layers join the slice (engine already computes CPA/TCPA).
5. **Real climatology/tropical tier** replaces the climate stub.
6. **Plugin layer contract** — third-party layers implement `sample()` and become narratable.
7. **NFL** unlocks the slot via experimental flag (personal) or partnership.

---

*One field over space and time; every layer a function of where and when; one probe that
slices them all; one narrator that speaks the slice — honestly, with sources. That is the
spine the whole product hangs on.*
