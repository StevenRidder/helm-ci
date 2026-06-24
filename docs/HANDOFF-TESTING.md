# Handoff — Community + Spacetime Probe (test & verify guide)

**For a local agent (or human) to check and test what was built on branch
`claude/codebase-audit-ui-vision-0xdkkk`.** Everything runs with **no keys** in stub/mock
mode; keys add real LLM prose + real weather.

> Specs this implements: [SPACETIME-PROBE.md](SPACETIME-PROBE.md) ·
> [BUILD-PLAN-COMMUNITY-LLM.md](BUILD-PLAN-COMMUNITY-LLM.md) ·
> [BRIEFINGS.md](BRIEFINGS.md) · ADRs [0005](decisions/0005-community-places-overlay.md)–[0007](decisions/0007-spacetime-probe.md).

---

## 1. What was built

A small **FastAPI backend** (`backend/`) + the community/spacetime features **baked into the
existing web prototype** (`web/`) as selectable layers.

### Backend (`backend/`)
| File | What it does |
|---|---|
| `main.py` | FastAPI app + endpoints (see §4) |
| `store.py` | source-tagged place store, owned pins/reviews, seed AIS, nearest-charted-depth (seeded near Key West) |
| `llm.py` | "where to go" recommender — **deterministic** pre-filter (draft/distance/shelter-vs-forecast-wind) + provider-pluggable `LLMClient` (OpenAI; honest stub w/o key) |
| `agents.py` | **ReAct research agents** — tools `get_weather` (Open-Meteo, full catalog), `fetch_page`, `search_web`; fills cited dossier; `narrate_context` (point) + `narrate_passage` (path) |
| `context.py` | **spacetime resolver** — fuses enabled layers at (lat, lon, t) into one source-tagged slice |
| `publisher.py` | give-back — NFL push (mock-first), OSM Notes (scaffold-first) |
| `test_smoke.py` | 22-check standalone smoke test (no network/keys) |

### Web (`web/`)
| File | Change |
|---|---|
| `style.json` | new `saved` + `whereto` sources/layers (gold pins, AI ring) |
| `community.js` | backend client w/ **graceful fallback** to local sample data |
| `index.html` | Community rail+drawer (where-to-go, give-back, **✨ Narrate a point**, **Narrate the passage**), layer toggles, the **slice card**, the **route-weather ribbon**, popups |
| `data/saved-sample.geojson`, `data/whereto-empty.geojson` | committed samples |

---

## 2. Run it

```bash
# backend
cd backend
pip install -r requirements.txt
cp .env.example .env          # optional; runs fine empty (stub/mock)
uvicorn main:app --reload --port 8090

# web (separate shell) — any static server from repo root
cd web && python3 -m http.server 8000
# open http://127.0.0.1:8000/   (the engine on :8081 + tiles :8082 are optional)
```

The web app auto-detects the backend at `http://127.0.0.1:8090` and **falls back to local
sample data** if it's down — so the chart never breaks.

---

## 3. Fast check — the smoke test (do this first)

```bash
cd backend && python3 test_smoke.py
# expect: "22/22 checks passed", exit 0
```

Covers: health, places (source-tagged), saved write/read, where-to-go ranking, the spacetime
**layer filter**, depth-at-point, AIS, NFL-locked-by-default, **passage briefing legs carry
the full weather catalog**, dossier sections, NFL/OSM give-back modes.

---

## 4. API reference + manual curl checks

```bash
B=http://127.0.0.1:8090

curl -s $B/health | jq                 # {ok, llm:"stub|openai", nfl:{mode:"mock"}, osm:{mode:"scaffold"}}
curl -s "$B/places?sources=osm,owned" | jq '.features|length'

# where to go (NE blow -> NE-sheltered first)
curl -s $B/whereto -H 'content-type: application/json' -d \
 '{"query":"safe tonight","position":{"lat":24.5,"lon":-81.8},"boat":{"draft":1.8},"forecast":{"windFromDeg":45,"windKt":25}}' | jq '.recommendations[0]'

# spacetime probe — narrate a point; layers[] filters the slice
curl -s $B/narrate -H 'content-type: application/json' -d \
 '{"lat":24.553,"lon":-81.782,"t":"2026-06-25T20:00","boat":{"draft":1.8},"layers":["weather","depth","ais","places"]}' | jq '{narration, layers: (.layers|keys)}'

# passage briefing — probe along a path
curl -s $B/briefing -H 'content-type: application/json' -d \
 '{"points":[{"lat":24.46,"lon":-81.88,"t":"2026-06-25T18:00"},{"lat":24.55,"lon":-81.78,"t":"2026-06-25T22:00"}],"layers":["weather","places"]}' | jq '{narration, legs:(.legs|length)}'

# dossier (ReAct agent) ; weather at a point ; give-back
curl -s $B/dossier -H 'content-type: application/json' -d '{"placeId":"osm-kw-garrison"}' | jq '.sections|keys'
curl -s "$B/weather?lat=24.55&lon=-81.80" | jq '.now'        # real wind/gust/rain/pressure (needs network)
curl -s $B/giveback/nfl/push -H 'content-type: application/json' -d '{"lat":24.5,"lon":-81.8}' | jq '.status'   # "sent-mock"
```

---

## 5. Manual UI checks (web)

1. Open the **Community** icon (rail, between Places and Settings). Status line shows
   *"Helm backend connected"* (green) or *offline* (amber, sample data).
2. **Layers drawer:** toggle **Saved places** (gold pins) and **Where to go** on/off.
3. **Where to go → "Suggest for tonight":** results list appears; click one → map flies to it;
   a gold ring + rank highlights it on the chart.
4. **✨ Narrate a point:** click it (chart arms, dashed outline), then tap the chart → a
   **slice card** appears: narration + per-layer chips (wind/sea/rain/pressure/current/depth/
   AIS/places/climate/🔒 NFL locked/chart) + sources + "verify on official charts".
   - Scrub the **weather timeline** first → tap again → narration reflects the new time.
   - Uncheck **Places** (or weather "Off") in Layers → tap again → that layer drops from the
     card and the narration (**toggles drive the slice**, ADR-0007).
5. **Narrate the passage:** the **route-weather ribbon** appears under the chart — one column
   per leg with a colour-ramped wind bar, rotated wind arrow, time, sea state, narration above.
6. **Give back:** toggle "Share my track → NoForeignLand" → status shows `sent-mock`; toggle
   "Contribute to OpenSeaMap" → `would-create`.

---

## 6. Going fully live (add keys) — what should change

| Add to `backend/.env` | Effect | How to verify |
|---|---|---|
| `OPENAI_API_KEY=…` (+ `OPENAI_MODEL`) | `/health` `llm:"openai"`; narration/dossier become real prose via a ReAct tool-calling loop | re-run curl `/narrate`, `/dossier`; text is generated, not templated |
| open network (your Mac) | `get_weather` returns real values; ribbon bars + arrival weather fill | `curl "$B/weather?lat=24.55&lon=-81.8"` → `.now.windKt` is a number |
| `NFL_BOAT_KEY=…` + `NFL_PUSH_ENABLED=true` | NFL push goes live (TODO: confirm endpoint from signalk-to-nfl) | `/health` `nfl.mode:"live"` |
| `OSM_NOTES_ENABLED=true` | OSM Notes posts for real | `/giveback/osm-note` → `queued` |
| `SEARCH_PROVIDER=…` | full live web search in the agent | dossier sources broaden |

---

## 7. Known limitations / what to scrutinize (honest)

- **Weather couldn't be verified in the build sandbox** — its egress proxy returns a policy
  **403** for `open-meteo.com`, so `get_weather` errored there and the agent honestly said
  "weather unavailable". **On a normal network it should work** (same API the existing
  `pipeline/fetch_weather.py` uses). **Please verify** `/weather` returns real numbers locally.
- **The full web app wasn't visually rendered in the sandbox** — the MapLibre/Tabler CDNs
  (`unpkg`/`jsdelivr`) are also proxy-blocked there. JS was **syntax-validated** (`node --check`)
  and standalone card/ribbon previews were rendered, but **please load `web/index.html` in a
  real browser** and run the §5 checks.
- **Depth-at-point and AIS are proxies/samples, labeled as such.** Depth = nearest charted
  feature's depth (not a true point sounding); AIS = seed targets (no real decode/CPA). The
  **engine** (`engine/…/helm_engine.cpp`, `helm_tiles.cpp`) already computes real depth/AIS —
  wiring those into the slice is the next step (see SPACETIME-PROBE §7).
- **Climate tier is a stub**; real climatology/tropical data is TODO (WEATHER-ROUTING §5).
- **Stub mode is deterministic by design** — narration is templated until a key is added; this
  is intended, not a bug.
- No secrets are committed: `.env` and runtime `data/owned.json` are gitignored.

---

## 8. Suggested local-agent test plan

1. `cd backend && pip install -r requirements.txt && python3 test_smoke.py` → expect 22/22.
2. Start `uvicorn` + a static server; run the §4 curl checks; confirm shapes match.
3. Add `OPENAI_API_KEY`; re-run `/narrate` + `/dossier`; confirm `provider:"openai"` and that
   the prose is grounded only in the returned data (no invented depths/fees) — **flag any
   hallucination** as a regression against the honesty rules (BRIEFINGS §6, WEATHER-ROUTING §7).
4. Verify `/weather` returns real numbers on your network.
5. Load `web/index.html`; run the §5 UI checks; confirm the layer-toggle→slice behavior.
6. Report: anything red, any hallucinated value, any layer that draws but doesn't narrate.
