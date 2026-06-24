"""
Helm backend — the spacetime context resolver (the "mash").

This is the keystone: given a point in SPACE and TIME (lat, lon, t), fan out across every
data layer and return ONE unified, source-tagged context object — weather valid at t,
climate, nearby places + reviews, owned saved pins, the NFL slot, chart/depth pointers, AIS.
The ReAct narrator (agents.ResearchAgent.narrate_context) then speaks it in plain language
with citations.

So "tap a point, scrub a time → it narrates the weather, climate, community, etc." becomes a
single call. Every layer is tagged with its source and the NFL layer is explicitly locked
unless experimental/partnership — honesty preserved end to end.
"""
import store
from agents import get_weather


def _valid_at(weather, t):
    """Pick the forecast hour nearest the requested ISO time t from the weather tool's series."""
    series = weather.get("next") or []
    if not t or not series:
        return weather.get("now"), None
    # series 't' are ISO strings (same TZ from Open-Meteo): first hour at/after t, else the
    # last available hour (clamped). We return that hour's REAL time so the slice card shows
    # when the forecast is actually valid — never the requested time dressed up as a forecast.
    chosen = next((h for h in series if h.get("t") and h["t"] >= t), series[-1])
    return chosen, chosen.get("t")


def resolve_context(lat, lon, t=None, boat=None, radius_nm=15, nfl_enabled=False, layers=None):
    """Fuse the enabled layers at (lat, lon, t) into one source-tagged slice.
    `layers` (list of keys) filters which layers participate — the selectable layer toggles
    drive the slice (ADR-0007). None = all layers."""
    want = set(layers) if layers else None
    def on(key):
        return want is None or key in want

    L, sources = {}, []

    if on("weather"):
        weather = get_weather(lat, lon)                 # real (Open-Meteo) at runtime
        wx_at, wx_time = _valid_at(weather, t)
        L["weather"] = {"validAt": wx_time, "atTime": wx_at, "now": weather.get("now"),
                        "sea": weather.get("sea"), "sst": weather.get("sst"),
                        "current": weather.get("current"), "series": weather.get("next"),
                        "horizon": "good ~0-7d; beyond is climatology",
                        "error": weather.get("windError") or weather.get("seaError")}
        sources.append({"title": "Open-Meteo", "url": "https://open-meteo.com", "kind": "open"})
    else:
        wx_time = None

    if on("places") or on("saved"):
        nearby, saved_near = [], []
        for p in store.all_places():
            d = store.haversine_nm(lat, lon, p["lat"], p["lon"])
            if d <= radius_nm:
                entry = {"id": p["id"], "name": p["name"], "source": p["source"], "kind": p["kind"],
                         "distanceNm": round(d, 1),
                         "reviews": [{"text": r["text"], "author": r["author"], "url": r.get("url")}
                                     for r in store.reviews_for(p["id"])[:2]]}
                if p["source"] == "owned":
                    saved_near.append(entry)
                nearby.append(entry)
        nearby.sort(key=lambda x: x["distanceNm"])
        if on("places"):
            L["places"] = nearby[:6]
            for p in nearby[:6]:
                sources.append({"title": p["name"], "kind": p["source"]})
                for r in p["reviews"]:
                    if r.get("url"):
                        sources.append({"title": r["author"], "url": r["url"], "kind": "rag"})
        if on("saved"):
            L["saved"] = saved_near

    if on("climate"):
        L["climate"] = {"note": "Seasonal & cyclone context (climatology tier — stub).",
                        "source": {"title": "NOAA climatology / pilot charts", "url": "https://www.noaa.gov", "kind": "open"}}
        sources.append(L["climate"]["source"])

    if on("nfl"):
        L["nfl"] = ({"available": False, "locked": True,
                     "reason": "NoForeignLand read is experimental / partnership-gated"}
                    if not nfl_enabled else
                    {"available": True, "locked": False, "note": "NFL enrichment active"})

    if on("depth"):
        nd = store.nearest_charted_depth(lat, lon)
        L["depth"] = {"nearestChartedM": round(nd[1], 1) if nd else None,
                      "nearFeature": nd[2] if nd else None,
                      "note": "Charted-depth proxy; read exact soundings on the S-52 chart.",
                      "source": {"title": "NOAA ENC (S-52)", "kind": "open"}}

    if on("ais"):
        targets = store.ais_near(lat, lon)
        L["ais"] = {"count": len(targets), "targets": targets, "source": "sample",
                    "note": "sample AIS — the engine provides real decode + CPA/TCPA"}

    if on("chart"):
        L["chart"] = {"note": "Cross-reference the S-52 chart for depth, contours and hazards here.",
                      "source": {"title": "NOAA ENC (S-52)", "kind": "open"}}

    return {
        "point": {"lat": lat, "lon": lon, "t": t, "weatherValidAt": wx_time},
        "layers": L,
        "boat": boat,
        "enabledLayers": sorted(L.keys()),
        "sources": sources,
        "disclaimer": "Fused from layered, cited sources. Supplemental — verify on official charts.",
    }

