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
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <ctime>
#include <mutex>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

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
static std::string fmtDur(double hours) {              // time-to-go as a human duration
  if (!(hours >= 0)) hours = 0;
  long mins = (long)std::lround(hours * 60.0);
  char b[24];
  if (mins < 60)            std::snprintf(b, sizeof b, "%ldm", mins);
  else if (mins < 24 * 60)  std::snprintf(b, sizeof b, "%ldh %02ldm", mins / 60, mins % 60);
  else                      std::snprintf(b, sizeof b, "%ldd %ldh", mins / 1440, (mins % 1440) / 60);
  return b;
}

// ---------------------------------------------------------------------------
// Real-data overlay — NMEA 0183 over TCP (port 10110, the standard boat feed).
//
// The sim is only scaffolding. Any real sentence overrides the matching field
// and stamps its source; a field with no fresh real sentence falls back to sim
// — but the per-field source flag ALWAYS tells the truth, so a simulated value
// is never reported as real. Corrupt (bad-checksum) sentences are rejected, not
// trusted. To take the boat off sim later, stop emitting the sim fallbacks.
// (Production should route this through OpenCPN's NavMsgBus / model-comms for
// full sentence coverage; this minimal listener proves the override path.)
// ---------------------------------------------------------------------------
static const int kNmeaPort = 10110;
static const double kStaleSec = 5.0;

struct RField { double v = 0; std::time_t t = 0; };     // t == 0 => never received
struct RealFeed {
  std::mutex m;
  double lat = 0, lon = 0; std::time_t pos_t = 0;
  RField sog, cog, hdg, depth, wspd, wdir;
};
static RealFeed g_real;
static bool fresh(std::time_t t) {
  return t != 0 && std::difftime(std::time(nullptr), t) <= kStaleSec;
}

static std::vector<std::string> splitc(const std::string& s) {
  std::vector<std::string> out; std::string cur;
  for (char c : s) { if (c == ',') { out.push_back(cur); cur.clear(); } else cur += c; }
  out.push_back(cur); return out;
}
static bool nmea_csum_ok(const std::string& s) {           // reject corrupt sentences
  if (s.size() < 4 || s[0] != '$') return false;
  size_t star = s.rfind('*');
  if (star == std::string::npos || star + 2 >= s.size()) return false;
  unsigned char cs = 0; for (size_t i = 1; i < star; ++i) cs ^= (unsigned char)s[i];
  return cs == (unsigned char)std::strtoul(s.substr(star + 1, 2).c_str(), nullptr, 16);
}
static double nmea_ll(const std::string& v, const std::string& hemi) {  // ddmm.mmm -> deg
  if (v.empty()) return 0;
  double raw = std::atof(v.c_str());
  int deg = (int)(raw / 100); double min = raw - deg * 100;
  double dec = deg + min / 60.0;
  if (hemi == "S" || hemi == "W") dec = -dec;
  return dec;
}
static void nmea_parse(const std::string& line) {
  if (!nmea_csum_ok(line)) {
    std::fprintf(stderr, "NMEA rejected (bad checksum): %s\n", line.c_str());
    return;
  }
  std::vector<std::string> f = splitc(line.substr(0, line.rfind('*')));
  if (f.empty() || f[0].size() < 6) return;
  std::string type = f[0].substr(3);                       // drop "$tt" talker id
  std::time_t now = std::time(nullptr);
  std::lock_guard<std::mutex> lk(g_real.m);
  if (type == "RMC" && f.size() >= 9 && f[2] == "A") {     // valid GPS fix: pos + sog + cog
    g_real.lat = nmea_ll(f[3], f[4]); g_real.lon = nmea_ll(f[5], f[6]); g_real.pos_t = now;
    if (!f[7].empty()) { g_real.sog.v = std::atof(f[7].c_str()); g_real.sog.t = now; }
    if (!f[8].empty()) { g_real.cog.v = std::atof(f[8].c_str()); g_real.cog.t = now; }
  } else if (type == "DPT" && f.size() >= 2 && !f[1].empty()) {       // depth, metres
    g_real.depth.v = std::atof(f[1].c_str()); g_real.depth.t = now;
  } else if (type == "DBT" && f.size() >= 4 && !f[3].empty()) {       // depth below transducer (m in f[3])
    g_real.depth.v = std::atof(f[3].c_str()); g_real.depth.t = now;
  } else if (type == "MWV" && f.size() >= 6 && f[5] == "A") {         // wind angle + speed
    if (!f[1].empty()) { g_real.wdir.v = std::atof(f[1].c_str()); g_real.wdir.t = now; }
    if (!f[3].empty()) {
      double sp = std::atof(f[3].c_str());
      if (f[4] == "K") sp *= 0.539957;        // km/h -> kn
      else if (f[4] == "M") sp *= 1.943844;   // m/s  -> kn
      g_real.wspd.v = sp; g_real.wspd.t = now;
    }
  } else if (type == "HDT" && f.size() >= 2 && !f[1].empty()) {       // true heading
    g_real.hdg.v = std::atof(f[1].c_str()); g_real.hdg.t = now;
  }
}
static void nmea_listener() {
  int srv = ::socket(AF_INET, SOCK_STREAM, 0);
  if (srv < 0) { std::fprintf(stderr, "NMEA: socket() failed; real-data override disabled\n"); return; }
  int yes = 1; ::setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
  sockaddr_in a{}; a.sin_family = AF_INET; a.sin_port = htons(kNmeaPort);
  a.sin_addr.s_addr = inet_addr("127.0.0.1");
  if (::bind(srv, (sockaddr*)&a, sizeof a) < 0 || ::listen(srv, 4) < 0) {
    std::fprintf(stderr, "NMEA: bind/listen on %d failed; real-data override disabled\n", kNmeaPort);
    ::close(srv); return;
  }
  std::printf("NMEA 0183 input: tcp://127.0.0.1:%d  (real data overrides sim per-field)\n", kNmeaPort);
  std::fflush(stdout);
  std::string buf;
  for (;;) {
    int c = ::accept(srv, nullptr, nullptr);
    if (c < 0) continue;
    buf.clear(); char rb[1024];
    for (;;) {
      ssize_t n = ::recv(c, rb, sizeof rb, 0);
      if (n <= 0) break;
      buf.append(rb, (size_t)n);
      size_t nl;
      while ((nl = buf.find('\n')) != std::string::npos) {
        std::string line = buf.substr(0, nl); buf.erase(0, nl + 1);
        while (!line.empty() && (line.back() == '\r' || line.back() == ' ')) line.pop_back();
        if (!line.empty()) nmea_parse(line);
      }
    }
    ::close(c);
  }
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

  std::thread(nmea_listener).detach();   // real NMEA (port 10110) overrides the sim per-field

  double along = 0; size_t lastLeg = 0;
  for (long tick = 0;; ++tick) {
    double sim_sog = 5.6 + std::sin(tick / 9.0) * 0.9;    // gentle 4.7-6.5 kn (scaffolding)
    along += sim_sog / 3600.0;                            // sim own-ship advances along the route
    if (along >= total) { along = 0; lastLeg = 0;                  // loop the demo
      g_pRouteMan->ActivateRoute(r); g_pRouteMan->ActivateNextPoint(r, false); }

    size_t li = 0; double acc = 0;
    while (li + 1 < legLen.size() && acc + legLen[li] < along) { acc += legLen[li]; ++li; }
    double f = legLen[li] ? (along - acc) / legLen[li] : 0;
    const WP& A = ROUTE[li]; const WP& B = ROUTE[li + 1];
    while (lastLeg < li) { g_pRouteMan->ActivateNextPoint(r, false); ++lastLeg; }

    // ---- sim values (fallback scaffolding only) ----
    double sim_lat = A.lat + (B.lat - A.lat) * f;
    double sim_lon = A.lon + (B.lon - A.lon) * f;
    double legBrg, segNM; bd(B.lat, B.lon, A.lat, A.lon, &legBrg, &segNM);   // leg bearing (route geometry)
    int    sim_cog = (int)std::lround(legBrg);
    int    sim_hdg = ((int)std::lround(legBrg) + (int)std::lround(std::sin(tick / 7.0) * 4) + 360) % 360;
    double sim_wspd = 14 + std::sin(tick / 11.0) * 3;
    int    sim_wdir = ((int)std::lround(95 + std::sin(tick / 13.0) * 10) + 360) % 360;
    double sim_depth = 6 + (1 - f) * 8 + std::sin(tick / 5.0) * 0.6;

    // ---- merge: fresh real NMEA overrides sim; EACH field reports its true source ----
    double sog, depth, wspd; int cog, hdg, wdir;
    const char *src_pos, *src_sog, *src_cog, *src_hdg, *src_depth, *src_wind;
    { std::lock_guard<std::mutex> lk(g_real.m);
      if (fresh(g_real.pos_t)) { gLat = g_real.lat; gLon = g_real.lon; src_pos = "nmea"; }
      else                     { gLat = sim_lat;    gLon = sim_lon;    src_pos = "simulated"; }
      if (fresh(g_real.sog.t))   { sog = g_real.sog.v;                   src_sog = "nmea"; }   else { sog = sim_sog;     src_sog = "simulated"; }
      if (fresh(g_real.cog.t))   { cog = (int)std::lround(g_real.cog.v); src_cog = "nmea"; }   else { cog = sim_cog;     src_cog = "simulated"; }
      if (fresh(g_real.hdg.t))   { hdg = (int)std::lround(g_real.hdg.v); src_hdg = "nmea"; }   else { hdg = sim_hdg;     src_hdg = "simulated"; }
      if (fresh(g_real.depth.t)) { depth = g_real.depth.v;              src_depth = "nmea"; }  else { depth = sim_depth; src_depth = "simulated"; }
      if (fresh(g_real.wspd.t))  { wspd = g_real.wspd.v;                src_wind = "nmea"; }   else { wspd = sim_wspd;   src_wind = "simulated"; }
      wdir = fresh(g_real.wdir.t) ? (int)std::lround(g_real.wdir.v) : sim_wdir;
    }

    // BRG/DTW to the model's active waypoint, computed from the (real-or-sim) position
    RoutePoint* act = g_pRouteMan->GetpActivePoint();
    double brgW = 0, dtw = 0;
    if (act) bd(act->GetLatitude(), act->GetLongitude(), gLat, gLon, &brgW, &dtw);
    double dtg = dtw; for (size_t k = li + 1; k < legLen.size(); ++k) dtg += legLen[k];

    // cross-track off the A->B leg
    double brgAP, dAP; bd(gLat, gLon, A.lat, A.lon, &brgAP, &dAP);
    double xteNM = std::fabs(std::asin(std::sin(dAP / 3440.065) *
                   std::sin((brgAP - legBrg) * M_PI / 180.0)) * 3440.065);

    double hoursToGo = dtg / std::max(0.1, sog);
    std::time_t now = std::time(nullptr);
    std::time_t etaT = now + (std::time_t)(hoursToGo * 3600.0);
    char etabuf[40]; std::strftime(etabuf, sizeof etabuf, "%I:%M %p \xC2\xB7 %a %d %b", std::localtime(&etaT));
    std::string ttg = fmtDur(hoursToGo);
    double vmg = sog * std::cos((brgW - cog) * M_PI / 180.0);   // velocity made good toward the active WP

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

    // Per-field `sources` carry the truth: "nmea" where a fresh real sentence
    // overrode the value, "simulated" where the demo scaffolding is still showing.
    char json[1500];
    std::snprintf(json, sizeof json,
      "{\"type\":\"nav\",\"posSource\":\"%s\","
      "\"sources\":{\"pos\":\"%s\",\"sog\":\"%s\",\"cog\":\"%s\",\"hdg\":\"%s\",\"depth\":\"%s\",\"wind\":\"%s\"},"
      "\"pos\":{\"lat\":%.5f,\"lon\":%.5f},\"posStr\":\"%s\","
      "\"sog\":%.1f,\"cog\":%d,\"hdg\":%d,\"depth\":%.1f,"
      "\"wind\":{\"spd\":%.0f,\"dir\":%d,\"range\":\"%ld\xE2\x80\x93%ld kt\"},"
      "\"active\":{\"name\":\"Route to Marina\",\"eta\":\"%s\",\"ttg\":\"%s\",\"vmg\":\"%.1f kn\","
      "\"dtg\":\"%s\",\"xte\":\"%d m\","
      "\"legs\":%s,\"nextWp\":\"%s \xC2\xB7 %s\"}}",
      src_pos,
      src_pos, src_sog, src_cog, src_hdg, src_depth, src_wind,
      gLat, gLon, fmtPos(gLat, gLon).c_str(),
      sog, cog, hdg, depth,
      wspd, wdir, std::lround(wspd - 4), std::lround(wspd + 8),
      etabuf, ttg.c_str(), vmg, fmtNM(dtg).c_str(), (int)std::lround(xteNM * 1852),
      legs.c_str(), nextShort.c_str(), fmtNM(dtw).c_str());

    for (auto& c : server.getClients()) c->send(json);
    if (tick % 10 == 0)
      std::printf("  [%ld] %s [%s]  SOG %.1f  COG %d  DTG %s  -> %s  (clients: %zu)\n",
                  tick, fmtPos(gLat, gLon).c_str(), src_pos, sog, cog,
                  fmtNM(dtg).c_str(), nextShort.c_str(), server.getClients().size());

    std::this_thread::sleep_for(std::chrono::seconds(1));
  }
  return 0;
}
