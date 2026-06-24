# Helm backend (prototype)

The small FastAPI service the static web app + C++ engine don't provide: the **place store**,
**owned pins/reviews**, the **"where to go" recommender**, **ReAct research agents** that fill
the dossier cards, and the **give-back publishers** (NFL push + OSM Notes). Source-agnostic,
offline-first, NFL-slot-open. Spec: [../docs/BUILD-PLAN-COMMUNITY-LLM.md](../docs/BUILD-PLAN-COMMUNITY-LLM.md).

## Run

Requires **Python 3.9+** (verified on 3.9.6 — the macOS system `python3` — and 3.13).

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env          # optional — works with no keys (stub/mock mode)
uvicorn main:app --reload --port 8090
```

The web prototype (`web/community.js`) auto-detects `http://127.0.0.1:8090` and **falls back to
local sample data when it's not running** — so the chart never breaks.

## Modes (graceful by design)

| Without keys (now) | With keys (you add later) |
|---|---|
| `where to go` + dossier run a **deterministic stub** (honest reasons from real weather + seed sources) | set `OPENAI_API_KEY` → real **ReAct agent** + LLM ranking/explanation |
| NFL push runs **mock** (`sent-mock`, proves queue/flush) | set `NFL_BOAT_KEY` + `NFL_PUSH_ENABLED=true` → live push |
| OSM Notes **scaffold** (`would-create`) | set `OSM_NOTES_ENABLED=true` → live Notes |
| `search_web` returns **curated real cruiser sources** | set `SEARCH_PROVIDER` (Tavily/Bing/SerpAPI) → full live search |

**Secrets:** all via `.env` / env vars, **never committed** (see `.gitignore`); the NFL key
stays device-local.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | mode report (llm provider, nfl/osm mode) |
| GET | `/places?sources=osm,owned` | source-tagged places (GeoJSON) |
| GET | `/saved` · POST `/saved` | owned saved pins (the cross-device bookmarks) |
| POST | `/reviews` | add an owned review |
| POST | `/whereto` | recommender: deterministic pre-filter + LLM rank/explain + map highlight |
| POST | `/dossier` | **ReAct agent** fills the destination dossier (cited) |
| GET | `/weather?lat=&lon=` | real forecast at a point (Open-Meteo) — the agent's weather tool |
| POST | `/giveback/nfl/push` | push own position to NFL (mock-first) |
| POST | `/giveback/osm-note` | OSM Note give-back (scaffold-first) |

## The ReAct agents ([agents.py](agents.py))

A reason→act→observe tool-calling loop that **researches instead of hallucinating**. Tools:
`get_weather` (real Open-Meteo), `search_web` (pluggable; curated sources until a provider is
set), `fetch_page` (real fetch + extract). The agent may only summarize what tools return,
**cites every claim with a source + date**, and marks gaps "verify locally". Fills the dossier
sections (formalities · anchorage · services · community · climate) + arrival weather.
