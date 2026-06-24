# Build Plan — Give-back, "Where to Go" LLM, NFL Reciprocity

**Pre-implementation spec. Flesh this out fully before wiring it into the live prototype.**

> Status: Plan draft v0.1 · 2026-06-24 · Owner: Steve Ridder
> Turns three agreed directions into a buildable plan:
> 1. **Give-back** — NFL push + opt-in OSM/OpenSeaMap contribution (sanctioned, ship now).
> 2. **"Where to go" LLM** — on open + owned + RAG, source-agnostic, NFL-shaped slot left open.
> 3. **NFL reciprocity** — open a non-commercial read-access conversation (we have a real offer).
>
> Companions: [integrations/noforeignland.md](integrations/noforeignland.md),
> [BRIEFINGS.md](BRIEFINGS.md), [WEATHER-ROUTING.md](WEATHER-ROUTING.md),
> [decisions/0005-community-places-overlay.md](decisions/0005-community-places-overlay.md).
> Honesty spine throughout: deterministic facts computed, LLM narrates; cite/date/link;
> respect every source wall; owned > scraped; offline-aware. **[LLM]** = LLM-derived.

---

## 0. The shared prerequisite — a small Helm backend

All three need a place to live that the static web prototype + the C++ engine don't provide
today. Stand up a **lightweight Helm service** (the seed of "Helm Cloud" from
[BUSINESS-MODEL.md](BUSINESS-MODEL.md)) — for the prototype, a single local service
(FastAPI or Node), offline-first, that owns:

| Capability | Used by | Notes |
|---|---|---|
| **Place store** (source-tagged GeoJSON + attrs) | Where-to-go, Places overlay | ingest OSM/OpenSeaMap/owned; NFL slot |
| **Owned pins/reviews** (CRUD) | Give-back, Where-to-go, Saved places | our data, the moat |
| **Recommendation service** | Where-to-go | deterministic pre-filter + [LLM] rank |
| **RAG index** | Where-to-go, Briefings | Noonsite/blogs/forums + owned reviews, cited |
| **Contribution queue** | Give-back | outbound to NFL (push) + OSM (notes/edits) |
| **NFL push proxy** | Give-back | holds nothing but the user's own key, device-local |

Design rule: **the engine stays the source of truth for live nav** (position, AIS, routes);
the backend handles community + LLM + outbound. They meet over the existing WebSocket/HTTP.

---

## 1. Workstream A — Give-back (sanctioned, ship first)

### A1 · NFL push (your track → NoForeignLand)

**Goal:** your boat appears for friends on NFL, using your own NFL boat API key. Direction is
strictly Helm → NFL.

- **Mechanism:** replicate the **[signalk-to-nfl](https://github.com/amirlanesman/signalk-to-nfl)**
  POST (study that plugin for the exact endpoint + payload; treat as the reference impl).
  Abstract it behind a `PositionPublisher` provider interface so NFL is one of several
  targets (NFL, [future] YB, generic webhook).
- **Source of position:** the engine already computes own-ship position and streams it
  ([engine/vendor/cli/helm_engine.cpp](../engine/vendor/cli/helm_engine.cpp), WS :8081). The
  publisher consumes that feed — no new positioning code.
- **Cadence + offline:** post on NFL's expected interval (e.g. every N min underway, slower at
  anchor); **queue while offline, flush on reconnect** (same discipline as the briefing
  ingestion). Never blocks nav.
- **Privacy / honesty:** opt-in; key stored **device-local only**; pause/stop anytime;
  optional precision reduction ("share approximate position"); show last-sent time + status.
- **Settings UI:** the "Share my track to NoForeignLand" tile (wireframed in
  [mockups/nfl-giveback-experimental.html](mockups/nfl-giveback-experimental.html)) — toggle +
  paste-key + cadence + privacy.
- **Code touchpoints:** new `pipeline/` or backend `publisher` service consuming WS :8081;
  settings panel in `web/`.

### A2 · OSM / OpenSeaMap contribution (give back to the open commons)

**Goal:** a user's anchorage corrections / new POIs flow back to the open map everyone uses.
**Tier it by risk** — the open map is a shared resource; sloppy writes are vandalism.

- **Tier 1 (ship first — low risk): OSM Notes.** Drop a **Note** at a location ("anchorage
  here, good holding in sand, 7 m") via the OSM Notes API. Notes are suggestions a human OSM
  editor acts on — **no edit privileges, no vandalism risk, no schema burden.** This is the
  safe, immediate give-back.
- **Tier 2 (later — reviewed): real node edits.** Create/edit OSM nodes (e.g.
  `leisure=marina`, `seamark:type=anchorage`, `waterway=fuel`) via **OAuth2 + changesets**,
  through a **review queue** (not silent auto-push). Correct tagging, sensible changeset
  comments, rate limits, and an anti-abuse gate. OpenSeaMap = OSM with `seamark:*` tags, so
  this covers both.
- **Attribution / license:** ODbL — attribute, share-alike; don't hammer endpoints; cache.
- **Data model:** a `Contribution` record (below) tracks intent → submitted → accepted.
- **Settings UI:** "Contribute to OpenSeaMap / OSM" tile (opt-in, Tier 1 by default).
- **Honesty:** make clear what gets published and where; opt-in; show what was contributed.

---

## 2. Workstream B — "Where to Go" recommender (open + owned + RAG, NFL slot open)

### Pipeline

```
  query ("safe spot for tonight near here")
        │
        ▼
  ┌─────────────────────┐   boat profile (draft, air-draft)   forecast (spacetime, §WEATHER-ROUTING)
  │  Candidate store     │◄── position / region ──┐                 │
  │  source-tagged:      │                        │                 │
  │  OSM · OpenSeaMap ·   │                        ▼                 ▼
  │  owned pins/reviews · │      ┌────────────────────────────────────────┐
  │  [NFL slot]          │─────►│ Deterministic pre-filter (COMPUTED)      │
  └─────────────────────┘      │  draft vs charted depth · distance/ETA ·  │
                               │  shelter vs forecast wind dir · season    │
                               └───────────────────┬──────────────────────┘
                                                   ▼
                            ┌──────────────────────────────────────────┐
                            │  RAG retrieve (owned reviews + cited web) │
                            └───────────────────┬──────────────────────┘
                                                ▼
                            ┌──────────────────────────────────────────┐
                            │  [LLM] rank + explain why + confidence    │
                            │  cite every source · "verify locally"     │
                            └───────────────────┬──────────────────────┘
                                                ▼
                                  ranked recommendations (card UI)
```

### Components

- **Candidate store.** Unify sources into one schema with a `source` tag. Seed from the
  existing [pipeline/fetch_places.py](../pipeline/fetch_places.py) (OSM/Overpass) + add
  OpenSeaMap seamarks + owned pins/reviews. **NFL is just another `source` value** — present
  only via experimental/partnership, otherwise absent (locked-enrichment UI).
- **Context.** Boat profile (draft, air-draft, comfort limits), current position, and the
  **forecast at arrival** from the spacetime engine ([WEATHER-ROUTING.md](WEATHER-ROUTING.md))
  — so "safe for tonight" means safe *in the wind that's coming*.
- **Deterministic pre-filter (COMPUTED, not LLM):** draft vs charted depth; distance/ETA;
  **shelter geometry vs forecast wind direction** (anchorage opening/fetch); cyclone-season
  check. Produces a scored shortlist + the hard facts.
- **RAG layer:** retrieve text for shortlisted places — owned reviews first, then **cited**
  Noonsite/blogs/forums. Embed + store, or fetch-on-demand; always attribute + link.
- **[LLM] rank + explain:** given query + shortlist + facts + retrieved text, return a ranked
  list with **plain-language "why," citations, and confidence.** Tool-use over the structured
  store; **default to the latest Claude models.** The LLM never invents a depth/holding/review
  — unknowns are "verify locally."
- **Output schema** (drives the card UI already wireframed): `{place, rank, reasons[],
  sources[], confidence, computedFacts{distance,eta,draftOk,shelter}, nflLocked?}`.
- **Source-agnostic + NFL slot:** ranking + prompt don't special-case NFL; when NFL records
  exist they add candidates/reviews tagged `nfl` and labelled in the UI; when absent, the card
  shows the **locked enrichment** affordance — never silently omits.
- **Offline / online:** full model + live RAG dockside; **precomputed/cached recommendations
  per region + smaller on-device model offshore**, explicit about which mode and data age.

### Prototype scope (first cut)

Open + owned candidates, the deterministic pre-filter, a **shallow RAG** (owned reviews + a
handful of cited pages), the [LLM] rank/explain, and the **Where-to-go card** UI from
[mockups/nfl-giveback-experimental.html](mockups/nfl-giveback-experimental.html). NFL slot
stubbed/locked. This proves the loop end-to-end without the wall.

---

## 3. Workstream C — NFL reciprocity (the conversation)

- **The offer (what we give):** opted-in active-cruiser **tracks** already flowing to NFL
  (Workstream A1), plus the option to mirror **owned contributions**, full **attribution**,
  and real users on the water — i.e. we *feed* their community, we don't just take.
- **The ask:** **non-commercial read access** to render NFL places (and optionally boats)
  in-app, attributed and cached — to enrich (not power) "Where to go."
- **Framing:** match their non-commercial, fundraise-to-stay-free ethos; respect that the
  crowdsourced DB is their moat; open to terms; happy to start non-commercial/personal.
- **Prep before sending:** have the give-back **live as proof**, a one-paragraph Helm
  explainer, and a clear "here's exactly what we'd display and how we'd attribute."
- **Draft note:** [integrations/nfl-outreach-draft.md](integrations/nfl-outreach-draft.md).
- **Fallbacks:** if declined or no reply, the product is unaffected (open + owned + RAG); the
  personal-experimental pull remains for Steve's own build only.

---

## 4. Consolidated data models (prototype-level)

```
Place        { id, source: 'osm'|'openseamap'|'owned'|'nfl', kind, name, lat, lon,
               attrs{depth?, holding?, shelterDirs?, services[]}, updatedAt }
Review       { id, placeId, source, author, boat?, text, ratings{holding?}, url?, createdAt }
SavedPlace   { id, placeId|point, title, category, note, sourceUrl?, status, collectionId,
               device, createdAt }          // from BRIEFINGS §3c
BoatProfile  { draft, airDraft, lengthOverall, comfortWindMax, comfortSeaMax }
Recommendation { placeId, rank, reasons[], sources[], confidence,
                 computed{distanceNm, etaIso, draftOk, shelterScore}, nflLocked }
Contribution { id, target:'nfl'|'osm-note'|'osm-edit', payload, status:'queued'|'sent'|'accepted',
               createdAt }                   // outbound give-back
```

---

## 5. Sequencing into the live prototype

1. **Backend skeleton** (§0) — place store + owned pins/reviews CRUD + WS bridge to the engine.
2. **A1 NFL push** — `PositionPublisher` consuming WS :8081 → NFL (start **mocked**, then real
   key). Settings tile.
3. **Place store ingest** — extend `fetch_places.py` (OpenSeaMap + normalize) into the store.
4. **B prototype** — deterministic pre-filter + shallow RAG + [LLM] card; NFL slot locked.
5. **A2 OSM Notes** (Tier 1) give-back.
6. **C** — send the NFL reciprocity note (once A1 is live as proof).
7. *Later:* A2 Tier-2 OSM edits; NFL read behind Experimental flag; offline model.

---

## 6. Open decisions (resolve before building — see chat)

| # | Decision | Recommendation |
|---|---|---|
| D1 | Where-to-go LLM in the prototype: real Claude API via backend, or local stub first? | **Real API via the small backend** — it's the whole point; stub only the NFL slot. |
| D2 | OSM contribution depth first: Notes, full node edits, or owned-queue only? | **OSM Notes (Tier 1)** — low-risk, immediate, real give-back. |
| D3 | NFL push in prototype: real posts with your key, or mock then real? | **Mock first**, switch to your real key once the publisher is proven. |
| D4 | Backend stack for the prototype | **Python (FastAPI)** — matches `pipeline/` + easy Claude SDK; or Node if preferred. |

---

*Build order favors the sanctioned, high-trust pieces first (give-back), proves the LLM loop
on data we own, and keeps NFL as an enrichment the reciprocity conversation can unlock — so
nothing here is blocked on anyone else's permission.*
