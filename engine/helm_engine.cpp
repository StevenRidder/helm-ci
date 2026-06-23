// Helm Engine — skeleton (Phase 2).
//
// Links OpenCPN's model/ nav core (ocpn::model-src) and drives a REAL Routeman
// headless: builds the Key West route, activates it, advances own-ship, auto-advances
// waypoints, and computes BRG/DTW/XTE per fix (the model/-vs-gui/ "UpdateProgress"
// relocation). Streams the nav state as JSON over ws://127.0.0.1:8081 — the SAME shape
// web/nav-source.js (HelmNav) emits, so the UI swaps the JS sim for this socket unchanged.
//
// This is the nav half of the engine. The S-52 chart-tile HTTP server (proven separately
// in spike/opencpn-headless/chart-render) is the next increment.
#include <wx/init.h>
#include <wx/string.h>
#include "model/routeman.h"
#include "model/route.h"
#include "model/route_point.h"
#include "model/own_ship.h"
#include "model/georef.h"
#include "ixwebsocket/IXWebSocketServer.h"
#include "ixwebsocket/IXWebSocket.h"
#include <thread>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>
#include <ctime>

void* g_pi_manager = reinterpret_cast<void*>(1L);

struct WP { double lat, lon; const char* name; };
static std::vector<WP> ROUTE = {            // web/data/route.geojson — "Key West approach"
  { 24.458, -81.808, "WP1 \xC2\xB7 start" },
  { 24.485, -81.800, "WP2 \xC2\xB7 sea buoy" },
  { 24.515, -81.793, "WP3 \xC2\xB7 channel" },
  { 24.540, -81.786, "WP4 \xC2\xB7 pass" },
  { 24.557, -81.781, "WP5 \xC2\xB7 marina" }
};

// bearing + great-circle distance (NM) from own-ship (lat0,lon0) to target (lat1,lon1)
static void bd(double lat1, double lon1, double lat0, double lon0, double* brg, double* nm) {
  DistanceBearingMercator(lat1, lon1, lat0, lon0, brg, nm);
}
static std::string fmtPos(double lat, double lon) {
  auto one = [](double v, const char* p, const char* n) {
    const char* h = v >= 0 ? p : n; v = std::fabs(v);
    int d = (int)v; double m = (v - d) * 60.0;
    char b[64]; std::snprintf(b, sizeof b, "%d\xC2\xB0%.1f\xE2\x80\xB2%s", d, m, h); // d°m′H
    return std::string(b);
  };
  return one(lat, "N", "S") + " \xC2\xB7 " + one(lon, "E", "W");                      // · separator
}
static std::string fmtNM(double nm) {
  char b[32]; std::snprintf(b, sizeof b, "%.1f NM", nm); return b;
}

int main(int, char**) {
  wxInitializer init;
  if (!init) { std::printf("wx init failed\n"); return 1; }
  std::printf("== Helm Engine (skeleton): OpenCPN model/ nav core -> WebSocket ==\n");

  // --- real model/ route + route manager, headless ---
  Route* r = new Route();
  for (auto& w : ROUTE)
    r->AddPoint(new RoutePoint(w.lat, w.lon, wxT("circle"), wxString::FromUTF8(w.name)));
  r->UpdateSegmentDistances(6.0);
  g_pRouteMan = new Routeman(RoutePropDlgCtx(), RoutemanDlgCtx());
  gLat = ROUTE[0].lat; gLon = ROUTE[0].lon;
  g_pRouteMan->ActivateRoute(r);
  g_pRouteMan->ActivateNextPoint(r, false);  // own-ship starts at WP1 → target the first destination
  std::printf("route activated: %d waypoints; Routeman live (no GUI).\n", r->GetnPoints());

  // precompute leg lengths (NM) for the own-ship sim
  std::vector<double> legLen; double total = 0, b, d;
  for (size_t i = 0; i + 1 < ROUTE.size(); ++i) {
    bd(ROUTE[i + 1].lat, ROUTE[i + 1].lon, ROUTE[i].lat, ROUTE[i].lon, &b, &d);
    legLen.push_back(d); total += d;
  }

  // --- WebSocket server: push nav state to all clients ---
  ix::WebSocketServer server(8081, "127.0.0.1");
  server.setOnConnectionCallback(
    [](std::weak_ptr<ix::WebSocket> wptr, std::shared_ptr<ix::ConnectionState> cs) {
      if (auto ws = wptr.lock())
        ws->setOnMessageCallback([](const ix::WebSocketMessagePtr&) {}); // push-only; ignore inbound
      std::printf("client connected: %s\n", cs->getId().c_str());
      std::fflush(stdout);
    });
  if (!server.listenAndStart()) { std::printf("WS listen on 8081 FAILED\n"); return 2; }
  std::printf("nav-state WebSocket: ws://127.0.0.1:8081  (streaming 1 Hz)\n");

  double along = 0; size_t lastLeg = 0;
  for (long tick = 0;; ++tick) {
    double sog = 5.6 + std::sin(tick / 9.0) * 0.9;        // gentle 4.7-6.5 kn
    along += sog / 3600.0;                                // NM per second
    if (along >= total) { along = 0; lastLeg = 0;                  // loop the demo
      g_pRouteMan->ActivateRoute(r); g_pRouteMan->ActivateNextPoint(r, false); }

    size_t li = 0; double acc = 0;
    while (li + 1 < legLen.size() && acc + legLen[li] < along) { acc += legLen[li]; ++li; }
    double f = legLen[li] ? (along - acc) / legLen[li] : 0;
    const WP& A = ROUTE[li]; const WP& B = ROUTE[li + 1];
    gLat = A.lat + (B.lat - A.lat) * f;                   // own-ship position
    gLon = A.lon + (B.lon - A.lon) * f;

    // keep the model's active waypoint in sync (real auto-advance)
    while (lastLeg < li) { g_pRouteMan->ActivateNextPoint(r, false); ++lastLeg; }

    double cog, segNM; bd(B.lat, B.lon, A.lat, A.lon, &cog, &segNM);
    int hdg = ((int)std::lround(cog) + (int)std::lround(std::sin(tick / 7.0) * 4) + 360) % 360;

    // BRG/DTW to the model's active waypoint (the relocated per-fix nav math)
    RoutePoint* act = g_pRouteMan->GetpActivePoint();
    double brgW = 0, dtw = 0;
    if (act) bd(act->GetLatitude(), act->GetLongitude(), gLat, gLon, &brgW, &dtw);
    double dtg = dtw; for (size_t k = li + 1; k < legLen.size(); ++k) dtg += legLen[k];

    // cross-track off the A->B leg
    double brgAP, dAP; bd(gLat, gLon, A.lat, A.lon, &brgAP, &dAP);
    double xteNM = std::fabs(std::asin(std::sin(dAP / 3440.065) *
                   std::sin((brgAP - cog) * M_PI / 180.0)) * 3440.065);

    std::time_t now = std::time(nullptr);
    std::time_t etaT = now + (std::time_t)((dtg / std::max(0.1, sog)) * 3600.0);
    char etabuf[16]; std::strftime(etabuf, sizeof etabuf, "%I:%M %p", std::localtime(&etaT));

    double windSpd = 14 + std::sin(tick / 11.0) * 3;
    int windDir = ((int)std::lround(95 + std::sin(tick / 13.0) * 10) + 360) % 360;
    double depth = 6 + (1 - f) * 8 + std::sin(tick / 5.0) * 0.6;

    std::string actName = act ? std::string(act->GetName().ToUTF8()) : "—";
    std::string nextShort = actName.substr(0, actName.find(" \xC2\xB7 "));

    // legs: active waypoint then the one after
    std::string legs = "[";
    for (size_t k = li + 1; k < ROUTE.size() && k <= li + 2; ++k) {
      const WP& from = (k == li + 1) ? WP{gLat, gLon, ""} : ROUTE[k - 1];
      double lb, ld; bd(ROUTE[k].lat, ROUTE[k].lon, from.lat, from.lon, &lb, &ld);
      char lbuf[160];
      std::snprintf(lbuf, sizeof lbuf, "%s{\"name\":\"%s\",\"brg\":\"%ld\xC2\xB0\",\"active\":%s}",
                    k == li + 1 ? "" : ",", ROUTE[k].name, std::lround(lb),
                    k == li + 1 ? "true" : "false");
      legs += lbuf;
    }
    legs += "]";

    char json[1200];
    std::snprintf(json, sizeof json,
      "{\"type\":\"nav\",\"pos\":{\"lat\":%.5f,\"lon\":%.5f},\"posStr\":\"%s\","
      "\"sog\":%.1f,\"cog\":%ld,\"hdg\":%d,\"depth\":%.1f,"
      "\"wind\":{\"spd\":%.0f,\"dir\":%d,\"range\":\"%ld\xE2\x80\x93%ld kt\"},"
      "\"active\":{\"name\":\"Route to Marina\",\"eta\":\"%s\",\"dtg\":\"%s\",\"xte\":\"%d m\","
      "\"legs\":%s,\"nextWp\":\"%s \xC2\xB7 %s\"}}",
      gLat, gLon, fmtPos(gLat, gLon).c_str(),
      sog, std::lround(cog), hdg, depth,
      windSpd, windDir, std::lround(windSpd - 4), std::lround(windSpd + 8),
      etabuf, fmtNM(dtg).c_str(), (int)std::lround(xteNM * 1852),
      legs.c_str(), nextShort.c_str(), fmtNM(dtw).c_str());

    for (auto& c : server.getClients()) c->send(json);
    if (tick % 10 == 0)
      std::printf("  [%ld] %s  SOG %.1f  COG %ld  DTG %s  -> %s  (clients: %zu)\n",
                  tick, fmtPos(gLat, gLon).c_str(), sog, std::lround(cog),
                  fmtNM(dtg).c_str(), nextShort.c_str(), server.getClients().size());

    std::this_thread::sleep_for(std::chrono::seconds(1));
  }
  return 0;
}
