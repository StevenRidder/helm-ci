// helm_server.cpp — ONE-ORIGIN Helm server (nav + charts + UI on a single port).
//
// Merges the two Phase-2 halves into one process behind one ix::HttpServer, which
// auto-routes a WebSocket upgrade to the nav handler and everything else to the HTTP
// handler (see IXHttpServer.cpp: `if Upgrade==websocket -> handleUpgrade; else http`):
//
//   ws   /nav                       OpenCPN model/ nav — snapshot+delta, seq, ~1 Hz
//   GET  /chart/{z}/{x}/{y}.png      S-52 ENC tiles (immutable-cached)  [helm_tiles path]
//   GET  /health  /catalog          liveness + chart catalog
//   GET  /* (anything else)         the Helm UI, served from HELM_WEB_ROOT
//
// Because the page is served from the engine, the client resolves the SAME origin for
// nav + tiles with NO ?server= override. The server also advertises itself over Bonjour
// (_helm._tcp) so an iPad/iPhone discovers "Helm Engine" on the WiFi automatically.
//
//   HELM_BIND      bind address (default 127.0.0.1; 0.0.0.0 to serve the LAN)
//   HELM_PORT      one origin port (default 8080)
//   HELM_WEB_ROOT  static UI directory (default ./web)
//   HELM_ENC       ENC cell .000 (default /tmp/ENC_ROOT/US5FL96M/US5FL96M.000)
//
// Links ocpn::chart-render (which pulls in model-src) + ixwebsocket — the helm-tiles
// line. Bonjour uses the system dns_sd (libSystem on macOS, no extra link).

#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cstring>
#include <cctype>
#include <deque>
#include <set>
#include <map>
#include <mutex>
#include <condition_variable>
#include <string>
#include <thread>
#include <chrono>
#include <vector>
#include <ctime>
#include <fstream>
#include <sstream>

#include <wx/app.h>
#include <wx/bitmap.h>
#include <wx/dcmemory.h>
#include <wx/filename.h>
#include <wx/image.h>
#include <wx/mstream.h>
#include <wx/string.h>

#include "gl_headers.h"
#include "chartbase.h"
#include "s57chart.h"
#include "viewport.h"
#include "ocpn_region.h"
#include "ocpn_pixel.h"
#include "color_types.h"
#include "s52plib.h"
#include "chartsymbols.h"
#include "s57registrar_mgr.h"
#include "o_senc.h"

#include "model/routeman.h"
#include "model/route.h"
#include "model/route_point.h"
#include "model/own_ship.h"
#include "model/georef.h"

#include "ixwebsocket/IXHttpServer.h"
#include "ixwebsocket/IXHttp.h"
#include "ixwebsocket/IXWebSocket.h"
#include "ixwebsocket/IXConnectionState.h"

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <dns_sd.h>

// NOTE: g_pi_manager is provided by chart_stubs.cpp (inside ocpn::chart-render) — do NOT
// redefine it here, or the link fails with a duplicate symbol. (This is the api_shim-vs-
// chart_stubs overlap the README warned about; the merged binary takes the chart_stubs one.)

extern s52plib* ps52plib;
extern wxString g_csv_locn;
extern wxString g_SENCPrefix;
extern wxString g_SData_Locn;
void EnsureHeadlessGlobals();

// ===========================================================================
// Tile rendering (S-52) — from helm_tiles.cpp, unchanged behavior.
// ===========================================================================
static const wxString kDataDir = wxT("/tmp/opencpn/data/");
static const wxString kS57Data = wxT("/tmp/opencpn/data/s57data/");
static const wxString kPLibRLE = wxT("/tmp/opencpn/data/s57data/S52RAZDS.RLE");
static const wxString kSencDir = wxT("/tmp/ocpn_senc/");

static s57chart* g_chart = nullptr;
static Extent    g_ext;
static std::string g_blank;
static std::string g_etag;
static const int TS = 256;

static std::string header_ci(const ix::WebSocketHttpHeaders& h, const char* name) {
  std::string want(name);
  for (auto& c : want) c = (char)std::tolower((unsigned char)c);
  for (auto& kv : h) {
    std::string k = kv.first;
    for (auto& c : k) c = (char)std::tolower((unsigned char)c);
    if (k == want) return kv.second;
  }
  return std::string();
}

enum class TileStatus { Ok, NoCoverage, BadRequest, RenderFailed };
struct Job { int z; long x, y; std::string result;
             TileStatus status = TileStatus::RenderFailed;
             bool done = false; std::mutex m; std::condition_variable cv; };
static std::deque<Job*> g_jobs;
static std::mutex g_jobs_m;
static std::condition_variable g_jobs_cv;

static double tile_lon(double x, int z) { return x / std::pow(2.0, z) * 360.0 - 180.0; }
static double tile_lat(double y, int z) {
  double n = M_PI * (1.0 - 2.0 * y / std::pow(2.0, z));
  return std::atan(std::sinh(n)) * 180.0 / M_PI;
}

static TileStatus render_tile(int z, long x, long y, std::string& out) {
  if (z < 0 || z > 24 || x < 0 || y < 0 || x >= (1L << z) || y >= (1L << z)) {
    fprintf(stderr, "tile BAD REQUEST z%d/%ld/%ld\n", z, x, y);
    return TileStatus::BadRequest;
  }
  double west = tile_lon(x, z), east = tile_lon(x + 1, z);
  double north = tile_lat(y, z), south = tile_lat(y + 1, z);
  if (east < g_ext.WLON || west > g_ext.ELON || north < g_ext.SLAT || south > g_ext.NLAT)
    return TileStatus::NoCoverage;
  double clat = (north + south) / 2.0, clon = (west + east) / 2.0;
  double span_m = (north - south) * 1852.0 * 60.0;
  if (span_m <= 0) { fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: span\n", z, x, y); return TileStatus::RenderFailed; }
  double ppm = (double)TS / span_m;
  ViewPort vp;
  vp.clat = clat; vp.clon = clon; vp.view_scale_ppm = ppm;
  vp.pix_width = TS; vp.pix_height = TS;
  vp.rotation = 0; vp.skew = 0; vp.tilt = 0;
  vp.m_projection_type = PROJECTION_MERCATOR;
  vp.chart_scale = g_chart->GetNativeScale();
  vp.ref_scale = vp.chart_scale;
  vp.b_quilt = false;
  vp.rv_rect = wxRect(0, 0, TS, TS);
  vp.SetBoxes(); vp.Validate();
  wxBitmap bmp(TS, TS, BPP);
  if (!bmp.IsOk()) { fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: bmp\n", z, x, y); return TileStatus::RenderFailed; }
  wxMemoryDC dc(bmp);
  if (!dc.IsOk()) { fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: dc\n", z, x, y); return TileStatus::RenderFailed; }
  OCPNRegion region(0, 0, TS, TS);
  bool ok = g_chart->RenderRegionViewOnDC(dc, vp, region);
  wxBitmap rendered = dc.GetSelectedBitmap();
  dc.SelectObject(wxNullBitmap);
  if (!ok || !rendered.IsOk()) { fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: render\n", z, x, y); return TileStatus::RenderFailed; }
  wxImage img = rendered.ConvertToImage();
  if (!img.IsOk()) { fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: img\n", z, x, y); return TileStatus::RenderFailed; }
  wxMemoryOutputStream mos;
  if (!img.SaveFile(mos, wxBITMAP_TYPE_PNG)) { fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: png\n", z, x, y); return TileStatus::RenderFailed; }
  out.resize(mos.GetSize());
  mos.CopyTo(&out[0], out.size());
  return TileStatus::Ok;
}

static std::string make_blank() {
  wxImage blank(TS, TS); blank.SetAlpha();
  std::memset(blank.GetAlpha(), 0, (size_t)TS * TS);
  wxMemoryOutputStream mos; blank.SaveFile(mos, wxBITMAP_TYPE_PNG);
  std::string out; out.resize(mos.GetSize()); mos.CopyTo(&out[0], out.size());
  return out;
}

static bool init_chart(const wxString& enc_path) {
  setvbuf(stdout, nullptr, _IONBF, 0);
  wxImage::AddHandler(new wxPNGHandler);
  EnsureHeadlessGlobals();
  ::wxFileName::Mkdir(kSencDir, 0755, wxPATH_MKDIR_FULL);
  g_SENCPrefix = kSencDir; g_csv_locn = kS57Data; g_SData_Locn = kDataDir;
  ps52plib = new s52plib(kPLibRLE, false);
  if (!ps52plib || !ps52plib->m_bOK) { printf("s52plib load FAILED\n"); return false; }
  ps52plib->SetPLIBColorScheme(GLOBAL_COLOR_SCHEME_DAY, ChartCtx(false, 0));
  m_pRegistrarMan = new s57RegistrarMgr(kS57Data, stderr);
  g_chart = new s57chart();
  g_chart->DisableBackgroundSENC();
  if (g_chart->Init(enc_path, FULL_INIT) != INIT_OK) { printf("chart Init FAILED\n"); return false; }
  g_chart->SetColorScheme(GLOBAL_COLOR_SCHEME_DAY);
  if (!g_chart->GetChartExtent(&g_ext)) { printf("GetChartExtent FAILED\n"); return false; }
  int ns = g_chart->GetNativeScale();
  if (ns <= 1) { printf("FATAL: chart native scale invalid (%d)\n", ns); return false; }
  g_blank = make_blank();
  if (g_blank.empty()) { printf("FATAL: blank tile gen failed\n"); return false; }
  wxString cell = wxFileName(enc_path).GetName();
  char etag[96]; std::snprintf(etag, sizeof etag, "\"%s.day.s%d\"", (const char*)cell.ToUTF8(), ns);
  g_etag = etag;
  printf("ENC loaded: S %.4f N %.4f W %.4f E %.4f  nativeScale=%d\n",
         g_ext.SLAT, g_ext.NLAT, g_ext.WLON, g_ext.ELON, ns);
  return true;
}

static void warmup_render() {
  double clat = (g_ext.SLAT + g_ext.NLAT) / 2.0, clon = (g_ext.WLON + g_ext.ELON) / 2.0;
  const int z = 13; const double n = std::pow(2.0, z);
  long x = (long)((clon + 180.0) / 360.0 * n);
  double lr = clat * M_PI / 180.0;
  long y = (long)((1.0 - std::log(std::tan(lr) + 1.0 / std::cos(lr)) / M_PI) / 2.0 * n);
  std::string scratch; TileStatus st = render_tile(z, x, y, scratch);
  printf("warmup render z%d/%ld/%ld -> status=%d (%zuB)\n", z, x, y, (int)st, scratch.size());
}

// ===========================================================================
// Static UI serving — the page is served from the engine, so the client's
// resolved origin == the engine. (No ?server= override needed.)
// ===========================================================================
static std::string g_webroot;
static const char* mime_for(const std::string& path) {
  auto ends = [&](const char* s){ size_t n=strlen(s); return path.size()>=n && path.compare(path.size()-n,n,s)==0; };
  if (ends(".html")) return "text/html; charset=utf-8";
  if (ends(".js"))   return "application/javascript";
  if (ends(".mjs"))  return "application/javascript";
  if (ends(".json")) return "application/json";
  if (ends(".geojson")) return "application/json";
  if (ends(".css"))  return "text/css";
  if (ends(".png"))  return "image/png";
  if (ends(".svg"))  return "image/svg+xml";
  if (ends(".ico"))  return "image/x-icon";
  return "text/plain; charset=utf-8";
}
// returns false if the path escapes the root or the file is missing
static bool serve_static(const std::string& uri, std::string& body, std::string& mime) {
  std::string p = uri;
  size_t q = p.find('?'); if (q != std::string::npos) p = p.substr(0, q);
  if (p == "/" || p.empty()) p = "/index.html";
  if (p.find("..") != std::string::npos) return false;           // no path traversal
  std::string full = g_webroot + p;
  std::ifstream f(full, std::ios::binary);
  if (!f) return false;
  std::ostringstream ss; ss << f.rdbuf();
  body = ss.str(); mime = mime_for(p);
  return true;
}

// ===========================================================================
// Nav (model/ Routeman) — from helm_engine.cpp. Runs on its own thread and
// pushes snapshot/delta to the WS clients of the shared ix::HttpServer.
// ===========================================================================
struct WP { double lat, lon; const char* name; };
static std::vector<WP> ROUTE = {
  { 24.458, -81.808, "WP1 \xC2\xB7 start" },
  { 24.485, -81.800, "WP2 \xC2\xB7 sea buoy" },
  { 24.515, -81.793, "WP3 \xC2\xB7 channel" },
  { 24.540, -81.786, "WP4 \xC2\xB7 pass" },
  { 24.557, -81.781, "WP5 \xC2\xB7 marina" }
};
static void bd(double lat1, double lon1, double lat0, double lon0, double* brg, double* nm) {
  DistanceBearingMercator(lat1, lon1, lat0, lon0, brg, nm);
}
static std::string fmtPos(double lat, double lon) {
  auto one = [](double v, const char* p, const char* n) {
    const char* h = v >= 0 ? p : n; v = std::fabs(v);
    int d = (int)v; double m = (v - d) * 60.0;
    char b[64]; std::snprintf(b, sizeof b, "%d\xC2\xB0%.1f\xE2\x80\xB2%s", d, m, h);
    return std::string(b);
  };
  return one(lat, "N", "S") + " \xC2\xB7 " + one(lon, "E", "W");
}
static std::string fmtNM(double nm) { char b[32]; std::snprintf(b, sizeof b, "%.1f NM", nm); return b; }
static std::string fmtDur(double hours) {
  if (!(hours >= 0)) hours = 0;
  long mins = (long)std::lround(hours * 60.0); char b[24];
  if (mins < 60) std::snprintf(b, sizeof b, "%ldm", mins);
  else if (mins < 24 * 60) std::snprintf(b, sizeof b, "%ldh %02ldm", mins / 60, mins % 60);
  else std::snprintf(b, sizeof b, "%ldd %ldh", mins / 1440, (mins % 1440) / 60);
  return b;
}

// NMEA 0183 over TCP (real data overrides the sim per-field; source flags stay truthful)
static const int kNmeaPort = 10110;
static const double kStaleSec = 5.0;
struct RField { double v = 0; std::time_t t = 0; };
struct RealFeed { std::mutex m; double lat = 0, lon = 0; std::time_t pos_t = 0;
                  RField sog, cog, hdg, depth, wspd, wdir; };
static RealFeed g_real;
static bool fresh(std::time_t t) { return t != 0 && std::difftime(std::time(nullptr), t) <= kStaleSec; }
static std::vector<std::string> splitc(const std::string& s) {
  std::vector<std::string> out; std::string cur;
  for (char c : s) { if (c == ',') { out.push_back(cur); cur.clear(); } else cur += c; }
  out.push_back(cur); return out;
}
static bool nmea_csum_ok(const std::string& s) {
  if (s.size() < 4 || s[0] != '$') return false;
  size_t star = s.rfind('*');
  if (star == std::string::npos || star + 2 >= s.size()) return false;
  unsigned char cs = 0; for (size_t i = 1; i < star; ++i) cs ^= (unsigned char)s[i];
  return cs == (unsigned char)std::strtoul(s.substr(star + 1, 2).c_str(), nullptr, 16);
}
static double nmea_ll(const std::string& v, const std::string& hemi) {
  if (v.empty()) return 0;
  double raw = std::atof(v.c_str()); int deg = (int)(raw / 100); double mn = raw - deg * 100;
  double dec = deg + mn / 60.0; if (hemi == "S" || hemi == "W") dec = -dec; return dec;
}
static void nmea_parse(const std::string& line) {
  if (!nmea_csum_ok(line)) { std::fprintf(stderr, "NMEA rejected (bad checksum): %s\n", line.c_str()); return; }
  std::vector<std::string> f = splitc(line.substr(0, line.rfind('*')));
  if (f.empty() || f[0].size() < 6) return;
  std::string type = f[0].substr(3); std::time_t now = std::time(nullptr);
  std::lock_guard<std::mutex> lk(g_real.m);
  if (type == "RMC" && f.size() >= 9 && f[2] == "A") {
    g_real.lat = nmea_ll(f[3], f[4]); g_real.lon = nmea_ll(f[5], f[6]); g_real.pos_t = now;
    if (!f[7].empty()) { g_real.sog.v = std::atof(f[7].c_str()); g_real.sog.t = now; }
    if (!f[8].empty()) { g_real.cog.v = std::atof(f[8].c_str()); g_real.cog.t = now; }
  } else if (type == "DPT" && f.size() >= 2 && !f[1].empty()) { g_real.depth.v = std::atof(f[1].c_str()); g_real.depth.t = now; }
  else if (type == "DBT" && f.size() >= 4 && !f[3].empty()) { g_real.depth.v = std::atof(f[3].c_str()); g_real.depth.t = now; }
  else if (type == "MWV" && f.size() >= 6 && f[5] == "A") {
    if (!f[1].empty()) { g_real.wdir.v = std::atof(f[1].c_str()); g_real.wdir.t = now; }
    if (!f[3].empty()) { double sp = std::atof(f[3].c_str()); if (f[4] == "K") sp *= 0.539957; else if (f[4] == "M") sp *= 1.943844; g_real.wspd.v = sp; g_real.wspd.t = now; }
  } else if (type == "HDT" && f.size() >= 2 && !f[1].empty()) { g_real.hdg.v = std::atof(f[1].c_str()); g_real.hdg.t = now; }
}
static void nmea_listener() {
  int srv = ::socket(AF_INET, SOCK_STREAM, 0);
  if (srv < 0) { std::fprintf(stderr, "NMEA: socket() failed\n"); return; }
  int yes = 1; ::setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
  sockaddr_in a{}; a.sin_family = AF_INET; a.sin_port = htons(kNmeaPort); a.sin_addr.s_addr = inet_addr("127.0.0.1");
  if (::bind(srv, (sockaddr*)&a, sizeof a) < 0 || ::listen(srv, 4) < 0) {
    std::fprintf(stderr, "NMEA: bind/listen on %d failed\n", kNmeaPort); ::close(srv); return;
  }
  std::printf("NMEA 0183 input: tcp://127.0.0.1:%d (real data overrides sim per-field)\n", kNmeaPort);
  std::string buf;
  for (;;) {
    int c = ::accept(srv, nullptr, nullptr); if (c < 0) continue;
    buf.clear(); char rb[1024];
    for (;;) {
      ssize_t n = ::recv(c, rb, sizeof rb, 0); if (n <= 0) break;
      buf.append(rb, (size_t)n); size_t nl;
      while ((nl = buf.find('\n')) != std::string::npos) {
        std::string line = buf.substr(0, nl); buf.erase(0, nl + 1);
        while (!line.empty() && (line.back() == '\r' || line.back() == ' ')) line.pop_back();
        if (!line.empty()) nmea_parse(line);
      }
    }
    ::close(c);
  }
}

static long g_seq = 0;
static std::set<ix::WebSocket*> g_seen;   // clients already given a snapshot baseline (nav thread only)

static void nav_loop(ix::HttpServer* server) {
  Route* r = new Route();
  for (auto& w : ROUTE) r->AddPoint(new RoutePoint(w.lat, w.lon, wxT("circle"), wxString::FromUTF8(w.name)));
  r->UpdateSegmentDistances(6.0);
  g_pRouteMan = new Routeman(RoutePropDlgCtx(), RoutemanDlgCtx());
  gLat = ROUTE[0].lat; gLon = ROUTE[0].lon;
  g_pRouteMan->ActivateRoute(r);
  g_pRouteMan->ActivateNextPoint(r, false);
  std::printf("route activated: %d waypoints; Routeman live (no GUI).\n", r->GetnPoints());

  std::vector<double> legLen; double total = 0, b, d;
  for (size_t i = 0; i + 1 < ROUTE.size(); ++i) { bd(ROUTE[i + 1].lat, ROUTE[i + 1].lon, ROUTE[i].lat, ROUTE[i].lon, &b, &d); legLen.push_back(d); total += d; }

  double along = 0; size_t lastLeg = 0;
  for (long tick = 0;; ++tick) {
    double sim_sog = 5.6 + std::sin(tick / 9.0) * 0.9;
    along += sim_sog / 3600.0;
    if (along >= total) { along = 0; lastLeg = 0; g_pRouteMan->ActivateRoute(r); g_pRouteMan->ActivateNextPoint(r, false); }
    size_t li = 0; double acc = 0;
    while (li + 1 < legLen.size() && acc + legLen[li] < along) { acc += legLen[li]; ++li; }
    double f = legLen[li] ? (along - acc) / legLen[li] : 0;
    const WP& A = ROUTE[li]; const WP& B = ROUTE[li + 1];
    while (lastLeg < li) { g_pRouteMan->ActivateNextPoint(r, false); ++lastLeg; }
    double sim_lat = A.lat + (B.lat - A.lat) * f, sim_lon = A.lon + (B.lon - A.lon) * f;
    double legBrg, segNM; bd(B.lat, B.lon, A.lat, A.lon, &legBrg, &segNM);
    int sim_cog = (int)std::lround(legBrg);
    int sim_hdg = ((int)std::lround(legBrg) + (int)std::lround(std::sin(tick / 7.0) * 4) + 360) % 360;
    double sim_wspd = 14 + std::sin(tick / 11.0) * 3;
    int sim_wdir = ((int)std::lround(95 + std::sin(tick / 13.0) * 10) + 360) % 360;
    double sim_depth = 6 + (1 - f) * 8 + std::sin(tick / 5.0) * 0.6;

    double sog, depth, wspd; int cog, hdg, wdir;
    const char *src_pos, *src_sog, *src_cog, *src_hdg, *src_depth, *src_wind;
    { std::lock_guard<std::mutex> lk(g_real.m);
      if (fresh(g_real.pos_t)) { gLat = g_real.lat; gLon = g_real.lon; src_pos = "nmea"; } else { gLat = sim_lat; gLon = sim_lon; src_pos = "simulated"; }
      if (fresh(g_real.sog.t)) { sog = g_real.sog.v; src_sog = "nmea"; } else { sog = sim_sog; src_sog = "simulated"; }
      if (fresh(g_real.cog.t)) { cog = (int)std::lround(g_real.cog.v); src_cog = "nmea"; } else { cog = sim_cog; src_cog = "simulated"; }
      if (fresh(g_real.hdg.t)) { hdg = (int)std::lround(g_real.hdg.v); src_hdg = "nmea"; } else { hdg = sim_hdg; src_hdg = "simulated"; }
      if (fresh(g_real.depth.t)) { depth = g_real.depth.v; src_depth = "nmea"; } else { depth = sim_depth; src_depth = "simulated"; }
      if (fresh(g_real.wspd.t)) { wspd = g_real.wspd.v; src_wind = "nmea"; } else { wspd = sim_wspd; src_wind = "simulated"; }
      wdir = fresh(g_real.wdir.t) ? (int)std::lround(g_real.wdir.v) : sim_wdir;
    }
    RoutePoint* act = g_pRouteMan->GetpActivePoint();
    double brgW = 0, dtw = 0; if (act) bd(act->GetLatitude(), act->GetLongitude(), gLat, gLon, &brgW, &dtw);
    double dtg = dtw; for (size_t k = li + 1; k < legLen.size(); ++k) dtg += legLen[k];
    double brgAP, dAP; bd(gLat, gLon, A.lat, A.lon, &brgAP, &dAP);
    double xteNM = std::fabs(std::asin(std::sin(dAP / 3440.065) * std::sin((brgAP - legBrg) * M_PI / 180.0)) * 3440.065);
    double hoursToGo = dtg / std::max(0.1, sog);
    std::time_t now = std::time(nullptr); std::time_t etaT = now + (std::time_t)(hoursToGo * 3600.0);
    char etabuf[40]; std::strftime(etabuf, sizeof etabuf, "%I:%M %p \xC2\xB7 %a %d %b", std::localtime(&etaT));
    std::string ttg = fmtDur(hoursToGo);
    double vmg = sog * std::cos((brgW - cog) * M_PI / 180.0);
    std::string actName = act ? std::string(act->GetName().ToUTF8()) : "—";
    std::string nextShort = actName.substr(0, actName.find(" \xC2\xB7 "));
    std::string legs = "[";
    for (size_t k = li + 1; k < ROUTE.size() && k <= li + 2; ++k) {
      const WP& from = (k == li + 1) ? WP{gLat, gLon, ""} : ROUTE[k - 1];
      double lb, ld; bd(ROUTE[k].lat, ROUTE[k].lon, from.lat, from.lon, &lb, &ld);
      char lbuf[160];
      std::snprintf(lbuf, sizeof lbuf, "%s{\"name\":\"%s\",\"brg\":\"%ld\xC2\xB0\",\"active\":%s}",
                    k == li + 1 ? "" : ",", ROUTE[k].name, std::lround(lb), k == li + 1 ? "true" : "false");
      legs += lbuf;
    }
    legs += "]";

    long seq = ++g_seq; double ts = (double)now; bool keyframe = (tick % 10 == 0);
    char snap[1700];
    int snlen = std::snprintf(snap, sizeof snap,
      "{\"t\":\"snapshot\",\"seq\":%ld,\"ts\":%.3f,\"type\":\"nav\",\"posSource\":\"%s\","
      "\"sources\":{\"pos\":\"%s\",\"sog\":\"%s\",\"cog\":\"%s\",\"hdg\":\"%s\",\"depth\":\"%s\",\"wind\":\"%s\"},"
      "\"pos\":{\"lat\":%.5f,\"lon\":%.5f},\"posStr\":\"%s\","
      "\"sog\":%.1f,\"cog\":%d,\"hdg\":%d,\"depth\":%.1f,"
      "\"wind\":{\"spd\":%.0f,\"dir\":%d,\"range\":\"%ld\xE2\x80\x93%ld kt\"},"
      "\"active\":{\"name\":\"Route to Marina\",\"eta\":\"%s\",\"ttg\":\"%s\",\"vmg\":\"%.1f kn\","
      "\"dtg\":\"%s\",\"xte\":\"%d m\",\"legs\":%s,\"nextWp\":\"%s \xC2\xB7 %s\"}}",
      seq, ts, src_pos, src_pos, src_sog, src_cog, src_hdg, src_depth, src_wind,
      gLat, gLon, fmtPos(gLat, gLon).c_str(), sog, cog, hdg, depth,
      wspd, wdir, std::lround(wspd - 4), std::lround(wspd + 8),
      etabuf, ttg.c_str(), vmg, fmtNM(dtg).c_str(), (int)std::lround(xteNM * 1852),
      legs.c_str(), nextShort.c_str(), fmtNM(dtw).c_str());

    std::string frame; bool truncated = (snlen < 0 || (size_t)snlen >= sizeof snap);
    if (keyframe) { frame = snap; }
    else {
      char dlt[1100];
      int dlen = std::snprintf(dlt, sizeof dlt,
        "{\"t\":\"delta\",\"seq\":%ld,\"ts\":%.3f,\"posSource\":\"%s\","
        "\"sources\":{\"pos\":\"%s\",\"sog\":\"%s\",\"cog\":\"%s\",\"hdg\":\"%s\",\"depth\":\"%s\",\"wind\":\"%s\"},"
        "\"pos\":{\"lat\":%.5f,\"lon\":%.5f},\"posStr\":\"%s\","
        "\"sog\":%.1f,\"cog\":%d,\"hdg\":%d,\"depth\":%.1f,"
        "\"active\":{\"dtg\":\"%s\",\"xte\":\"%d m\",\"eta\":\"%s\",\"ttg\":\"%s\",\"vmg\":\"%.1f kn\",\"nextWp\":\"%s \xC2\xB7 %s\"}}",
        seq, ts, src_pos, src_pos, src_sog, src_cog, src_hdg, src_depth, src_wind,
        gLat, gLon, fmtPos(gLat, gLon).c_str(), sog, cog, hdg, depth,
        fmtNM(dtg).c_str(), (int)std::lround(xteNM * 1852), etabuf, ttg.c_str(), vmg, nextShort.c_str(), fmtNM(dtw).c_str());
      truncated = truncated || dlen < 0 || (size_t)dlen >= sizeof dlt;
      frame = dlt;
      if (tick % 5 == 0) {
        char wbuf[160];
        int wlen = std::snprintf(wbuf, sizeof wbuf, "\"wind\":{\"spd\":%.0f,\"dir\":%d,\"range\":\"%ld\xE2\x80\x93%ld kt\"},",
          wspd, wdir, std::lround(wspd - 4), std::lround(wspd + 8));
        truncated = truncated || wlen < 0 || (size_t)wlen >= sizeof wbuf;
        frame.insert(frame.find("\"active\""), wbuf);
      }
    }
    if (truncated) { std::fprintf(stderr, "ERROR: nav frame seq %ld truncated; NOT sending.\n", seq); std::this_thread::sleep_for(std::chrono::seconds(1)); continue; }

    auto clients = server->getClients();
    std::set<ix::WebSocket*> live;
    for (auto& c : clients) live.insert(c.get());
    for (auto& c : clients) c->send(g_seen.count(c.get()) ? frame : snap);
    g_seen.swap(live);
    if (tick % 10 == 0)
      std::printf("  [%ld] seq %ld %-5s %s [%s]  SOG %.1f  DTG %s  -> %s  (clients: %zu)\n",
                  tick, seq, keyframe ? "snap" : "delta", fmtPos(gLat, gLon).c_str(), src_pos, sog,
                  fmtNM(dtg).c_str(), nextShort.c_str(), clients.size());
    std::this_thread::sleep_for(std::chrono::seconds(1));
  }
}

// ===========================================================================
// Bonjour (_helm._tcp) — system dns_sd; lets an iPad discover "Helm Engine".
// ===========================================================================
static void bonjour_advertise(int port) {
  static DNSServiceRef ref = nullptr;
  DNSServiceErrorType err = DNSServiceRegister(
    &ref, 0, 0, "Helm Engine", "_helm._tcp", nullptr, nullptr, htons((uint16_t)port),
    0, nullptr, nullptr, nullptr);
  if (err != kDNSServiceErr_NoError) { std::fprintf(stderr, "Bonjour: register failed (%d) — discovery off\n", err); return; }
  std::printf("Bonjour: advertising _helm._tcp on %d as \"Helm Engine\"\n", port);
  std::thread([] { for (;;) { if (DNSServiceProcessResult(ref) != kDNSServiceErr_NoError) break; } }).detach();
}

// ===========================================================================
// One ix::HttpServer; HTTP callback routes tiles/health/catalog/static, WS
// callback handles /nav. Tiles render on the MAIN thread (CoreGraphics).
// ===========================================================================
class ServerApp : public wxApp {
public:
  ix::HttpServer* server = nullptr;
  bool OnInit() override {
    SetAppName(wxT("opencpn"));
    const char* enc = std::getenv("HELM_ENC");
    wxString encPath = enc && *enc ? wxString::FromUTF8(enc) : wxT("/tmp/ENC_ROOT/US5FL96M/US5FL96M.000");
    if (!init_chart(encPath)) return false;
    if (!std::getenv("HELM_TILES_NO_WARMUP")) warmup_render();

    const char* webroot = std::getenv("HELM_WEB_ROOT");
    g_webroot = webroot && *webroot ? webroot : "web";

    const char* bindHost = std::getenv("HELM_BIND"); if (!bindHost || !*bindHost) bindHost = "127.0.0.1";
    int port = 8080;
    if (const char* p = std::getenv("HELM_PORT")) {
      char* end = nullptr; long v = std::strtol(p, &end, 10);
      if (end == p || *end != '\0' || v < 1 || v > 65535) { printf("FATAL: HELM_PORT=\"%s\" invalid (1-65535)\n", p); return false; }
      port = (int)v;
    }

    server = new ix::HttpServer(port, bindHost);

    // WS side (/nav): set on the WebSocketServer base (HttpServer::handleUpgrade uses it).
    server->WebSocketServer::setOnConnectionCallback(
      [](std::weak_ptr<ix::WebSocket> wptr, std::shared_ptr<ix::ConnectionState> cs) {
        if (auto ws = wptr.lock())
          ws->setOnMessageCallback([](const ix::WebSocketMessagePtr&) {}); // push-only; baseline sent by nav_loop
        std::printf("nav client connected: %s\n", cs->getId().c_str()); std::fflush(stdout);
      });

    // HTTP side: tiles, health, catalog, then the static UI.
    server->setOnConnectionCallback(
      [](ix::HttpRequestPtr req, std::shared_ptr<ix::ConnectionState>) -> ix::HttpResponsePtr {
        ix::WebSocketHttpHeaders h; h["Access-Control-Allow-Origin"] = "*";
        int z; long x, y;
        if (std::sscanf(req->uri.c_str(), "/chart/%d/%ld/%ld.png", &z, &x, &y) == 3) {
          h["Cache-Control"] = "public, max-age=31536000, immutable"; h["ETag"] = g_etag;
          if (header_ci(req->headers, "If-None-Match") == g_etag)
            return std::make_shared<ix::HttpResponse>(304, "Not Modified", ix::HttpErrorCode::Ok, h, std::string());
          Job job; job.z = z; job.x = x; job.y = y;
          { std::lock_guard<std::mutex> lk(g_jobs_m); g_jobs.push_back(&job); }
          g_jobs_cv.notify_one();
          { std::unique_lock<std::mutex> lk(job.m); job.cv.wait(lk, [&]{ return job.done; }); }
          switch (job.status) {
            case TileStatus::Ok: h["Content-Type"] = "image/png";
              return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h, job.result);
            case TileStatus::NoCoverage: h["Content-Type"] = "image/png";
              return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h, g_blank);
            case TileStatus::BadRequest: h["Content-Type"] = "text/plain"; h["Cache-Control"] = "no-store"; h.erase("ETag");
              return std::make_shared<ix::HttpResponse>(400, "Bad Request", ix::HttpErrorCode::Ok, h, std::string("invalid tile coordinates\n"));
            default: h["Content-Type"] = "text/plain"; h["Cache-Control"] = "no-store"; h.erase("ETag");
              return std::make_shared<ix::HttpResponse>(500, "Render Failed", ix::HttpErrorCode::Ok, h, std::string("S-52 tile render failed; see server log\n"));
          }
        }
        if (req->uri == "/health") { h["Content-Type"] = "application/json";
          return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h, std::string("{\"status\":\"ok\",\"engine\":\"helm-server\"}")); }
        if (req->uri == "/catalog") { h["Content-Type"] = "application/json";
          return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h,
            std::string("{\"cells\":[{\"id\":\"US5FL96M\",\"name\":\"Key West\"}]}")); }
        // static UI (the page is served from the engine → same origin → no ?server=)
        std::string body, mime;
        if (serve_static(req->uri, body, mime)) { h["Content-Type"] = mime;
          return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h, body); }
        h["Content-Type"] = "text/plain";
        return std::make_shared<ix::HttpResponse>(404, "Not Found", ix::HttpErrorCode::Ok, h, std::string("not found\n"));
      });

    if (!server->listenAndStart()) { printf("listen on %s:%d FAILED\n", bindHost, port); return false; }
    printf("Helm one-origin server: http://%s:%d/  (UI + /chart S-52 tiles + ws /nav)\n", bindHost, port);
    if (std::strcmp(bindHost, "127.0.0.1") != 0)
      printf("  serving the LAN — iPad/iPhone: open http://<this-host>:%d/  (no ?server= needed)\n", port);

    std::thread(nav_loop, server).detach();
    std::thread(nmea_listener).detach();
    bonjour_advertise(port);
    return false;  // no wx event loop; main() runs the render job loop
  }
};
wxIMPLEMENT_APP_NO_MAIN(ServerApp);

int main(int argc, char** argv) {
  wxEntryStart(argc, argv);
  wxTheApp->CallOnInit();
  ServerApp* app = static_cast<ServerApp*>(wxTheApp);
  if (!app->server) { printf("startup failed\n"); wxEntryCleanup(); return 1; }
  for (;;) {
    Job* j = nullptr;
    { std::unique_lock<std::mutex> lk(g_jobs_m); g_jobs_cv.wait(lk, [] { return !g_jobs.empty(); });
      j = g_jobs.front(); g_jobs.pop_front(); }
    j->status = render_tile(j->z, j->x, j->y, j->result);
    { std::lock_guard<std::mutex> lk(j->m); j->done = true; } j->cv.notify_one();
  }
  wxEntryCleanup();
  return 0;
}
