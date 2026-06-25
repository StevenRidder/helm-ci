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
#include <atomic>
#include <algorithm>

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
#include "model/ais_decoder.h"
#include "model/ais_target_data.h"
#include "model/ais_state_vars.h"
#include "model/select.h"
#include "model/base_platform.h"
#include "model/navobj_db.h"
#include <sqlite3.h>
#include "pugixml.hpp"
#include "rapidjson/document.h"
#include <iterator>

#include "ixwebsocket/IXHttpServer.h"
#include "ixwebsocket/IXHttp.h"
#include "ixwebsocket/IXWebSocket.h"
#include "ixwebsocket/IXConnectionState.h"

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <fcntl.h>
#include <poll.h>
#include <cerrno>
#include <sys/stat.h>
#include <sys/time.h>
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
static const int TS = 256;

// CHART-8: true engine-side S-52 colour palette (Day/Dusk/Night), NOT a raster reskin. Rendering is
// serialized on the main thread (the job loop), so we switch the global s52plib + chart colour scheme
// per tile and pay the switch cost only when the requested palette actually changes.
static std::string g_cell_name;                               // components of the per-palette ETag
static int g_native_scale = 0;
static ColorScheme g_color_scheme = GLOBAL_COLOR_SCHEME_DAY;  // currently-applied scheme
static const char* palette_name(ColorScheme s) {
  return s == GLOBAL_COLOR_SCHEME_DUSK ? "dusk" : (s == GLOBAL_COLOR_SCHEME_NIGHT ? "night" : "day");
}
static ColorScheme palette_from_query(const std::string& uri) {   // ?p=day|dusk|night (default day)
  const auto q = uri.find("p=");
  if (q != std::string::npos) {
    const std::string v = uri.substr(q + 2);
    if (v.rfind("dusk", 0) == 0)  return GLOBAL_COLOR_SCHEME_DUSK;
    if (v.rfind("night", 0) == 0) return GLOBAL_COLOR_SCHEME_NIGHT;
  }
  return GLOBAL_COLOR_SCHEME_DAY;
}
static void apply_palette(ColorScheme scheme) {               // main-thread only (called from render_tile)
  if (scheme == g_color_scheme) return;
  ps52plib->SetPLIBColorScheme(scheme, ChartCtx(false, 0));
  g_chart->SetColorScheme(scheme);
  g_color_scheme = scheme;
}

// CHART-9: S-52 display category (Base/Std/All/Mariner) selects WHICH feature classes render
// (DISPLAYBASE = safety-critical only … OTHER = everything). Switched per tile on the serialized
// render thread, only when it changes. Default = the renderer's own default (captured at init) so a
// request without ?cat= is byte-identical to before.
static DisCat g_default_cat = STANDARD;          // captured from ps52plib->GetDisplayCategory() at init
static DisCat g_display_cat = STANDARD;          // currently-applied
static const char* cat_name(DisCat c) {
  return c == DISPLAYBASE ? "base" : (c == OTHER ? "all" : (c == MARINERS_STANDARD ? "mariner" : "std"));
}
static DisCat category_from_query(const std::string& uri) {   // ?cat=base|std|all|mariner (default = renderer default)
  const auto q = uri.find("cat=");
  if (q != std::string::npos) {
    const std::string v = uri.substr(q + 4);
    if (v.rfind("base", 0) == 0)    return DISPLAYBASE;
    if (v.rfind("std", 0) == 0)     return STANDARD;
    if (v.rfind("all", 0) == 0)     return OTHER;
    if (v.rfind("mariner", 0) == 0) return MARINERS_STANDARD;
  }
  return g_default_cat;
}
static void apply_category(DisCat cat) {                      // main-thread only (from render_tile)
  if (cat == g_display_cat) return;
  ps52plib->SetDisplayCategory(cat);
  g_display_cat = cat;
}

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
// CHART-10: the single main-thread job consumer runs either a tile render or an S-57 object query —
// both touch the non-thread-safe g_chart/ps52plib, so a query is marshalled through the SAME queue.
enum class JobKind { Render, Query };
struct Job { JobKind kind = JobKind::Render;
             int z = 0; long x = 0, y = 0;                       // render inputs (z reused as the query zoom hint)
             double qlat = 0, qlon = 0; int qradius_px = 5;      // query inputs
             ColorScheme palette = GLOBAL_COLOR_SCHEME_DAY; DisCat cat = STANDARD; std::string result;
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
// CHART-9: Web-Mercator display-scale denominator (OGC 0.28 mm/px, 256-px tiles) — for the overzoom check.
static double display_scale(int z, double lat) {
  return 559082264.029 * std::cos(lat * M_PI / 180.0) / std::pow(2.0, z);
}

static TileStatus render_tile(int z, long x, long y, ColorScheme palette, DisCat cat, std::string& out) {
  if (z < 0 || z > 24 || x < 0 || y < 0 || x >= (1L << z) || y >= (1L << z)) {
    fprintf(stderr, "tile BAD REQUEST z%d/%ld/%ld\n", z, x, y);
    return TileStatus::BadRequest;
  }
  double west = tile_lon(x, z), east = tile_lon(x + 1, z);
  double north = tile_lat(y, z), south = tile_lat(y + 1, z);
  if (east < g_ext.WLON || west > g_ext.ELON || north < g_ext.SLAT || south > g_ext.NLAT)
    return TileStatus::NoCoverage;
  apply_palette(palette);   // CHART-8: switch the S-52 colour scheme if the requested palette changed
  apply_category(cat);      // CHART-9: switch the S-52 display category if the requested one changed
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
  g_cell_name = std::string((const char*)wxFileName(enc_path).GetName().ToUTF8());
  g_native_scale = ns;   // CHART-8: ETag is built per-request as "<cell>.<palette>.<cat>.s<scale>"
  g_default_cat = g_display_cat = ps52plib->GetDisplayCategory();   // CHART-9: the renderer's default display category
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
  std::string scratch; TileStatus st = render_tile(z, x, y, GLOBAL_COLOR_SCHEME_DAY, g_default_cat, scratch);
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
struct WP { double lat, lon; std::string name; };
static std::vector<WP> ROUTE;                 // the ACTIVE route the sim follows — guarded by g_route_mtx
static std::string g_route_name = "Route";
static std::mutex g_route_mtx;                 // guards ROUTE + g_route_name (swapped at runtime by route.create)
static std::atomic<long> g_route_version{0};   // bumped on swap so nav_loop rebuilds the active route

// Built-in sample (inside US5FL96M) used when no HELM_ROUTE is given, so the server still
// runs out of the box. Real GPX data parsed by the same loader as a user file.
static const char* SAMPLE_GPX = R"GPX(<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Helm" xmlns="http://www.topografix.com/GPX/1/1">
  <rte>
    <name>Key West Approach</name>
    <rtept lat="24.770" lon="-81.580"><name>WP1 · start</name></rtept>
    <rtept lat="24.792" lon="-81.515"><name>WP2 · sea buoy</name></rtept>
    <rtept lat="24.812" lon="-81.448"><name>WP3 · channel</name></rtept>
    <rtept lat="24.835" lon="-81.375"><name>WP4 · pass</name></rtept>
    <rtept lat="24.856" lon="-81.302"><name>WP5 · marina</name></rtept>
  </rte>
</gpx>)GPX";

// Minimal JSON string escaper — route/waypoint/AIS names come from user data.
static std::string json_escape(const std::string& s) {
  std::string o; o.reserve(s.size() + 8);
  for (unsigned char c : s) {
    switch (c) {
      case '"': o += "\\\""; break;  case '\\': o += "\\\\"; break;
      case '\n': o += "\\n"; break;  case '\r': o += "\\r"; break;  case '\t': o += "\\t"; break;
      default: if (c < 0x20) { char b[8]; std::snprintf(b, sizeof b, "\\u%04x", c); o += b; } else o += (char)c;
    }
  }
  return o;
}

// CHART-10: S-57 object query at a tapped point. Runs ONLY from the main-thread job loop (it touches
// g_chart/ps52plib, exactly like render_tile), so it is invoked via a Job{kind=Query}, never directly
// from an HTTP worker thread. Returns a JSON array of the picked features (acronym / class / geometry /
// decoded attributes / plain-language lines), built from the structured S57 attribute walk — NOT the
// GUI HTML report (which merges LIGHTS and needs private chart members).
static const char* geo_str(GeoPrim_t t) { return t == GEO_POINT ? "point" : (t == GEO_LINE ? "line" : (t == GEO_AREA ? "area" : "")); }
static TileStatus run_query(double lat, double lon, int zhint, int radius_px,
                            ColorScheme palette, DisCat cat, std::string& out) {
  if (!g_chart) return TileStatus::BadRequest;
  if (lon < g_ext.WLON || lon > g_ext.ELON || lat < g_ext.SLAT || lat > g_ext.NLAT) { out = "[]"; return TileStatus::Ok; }
  apply_palette(palette); apply_category(cat);              // visibility parity with the tiles (main-thread only)
  double ppm;                                               // pixels/metre — from the zoom hint if given, else the cell span
  if (zhint > 0) {
    double n = std::pow(2.0, zhint);
    double yt = std::floor((1.0 - std::log(std::tan(lat * M_PI / 180.0) + 1.0 / std::cos(lat * M_PI / 180.0)) / M_PI) / 2.0 * n);
    double span_m = (tile_lat(yt, zhint) - tile_lat(yt + 1, zhint)) * 1852.0 * 60.0;
    ppm = span_m > 0 ? (double)TS / span_m : 1.0;
  } else {
    double span_m = (g_ext.NLAT - g_ext.SLAT) * 1852.0 * 60.0;
    ppm = span_m > 0 ? (double)TS / span_m : 1.0;
  }
  ViewPort vp;
  vp.clat = lat; vp.clon = lon; vp.view_scale_ppm = ppm;
  vp.pix_width = TS; vp.pix_height = TS; vp.rotation = 0; vp.skew = 0; vp.tilt = 0;
  vp.m_projection_type = PROJECTION_MERCATOR;
  vp.chart_scale = g_chart->GetNativeScale(); vp.ref_scale = vp.chart_scale;
  vp.b_quilt = false; vp.rv_rect = wxRect(0, 0, TS, TS); vp.SetBoxes(); vp.Validate();
  float sel_deg = (float)(radius_px / (vp.view_scale_ppm * 1852.0 * 60.0));
  ListOfObjRazRules* rl = g_chart->GetObjRuleListAtLatLon((float)lat, (float)lon, sel_deg, &vp, MASK_ALL);
  std::string arr = "[";
  if (rl) {
    const std::string ocPath = std::string(g_csv_locn.mb_str()) + "/s57objectclasses.csv";
    bool first = true; int emitted = 0;
    for (ListOfObjRazRules::Node* node = rl->GetLast(); node && emitted < 100; node = node->GetPrevious()) {
      ObjRazRules* cur = node->GetData(); if (!cur || !cur->obj) continue;
      S57Obj* o = cur->obj;
      if (o->Primitive_type == GEO_META || o->Primitive_type == GEO_PRIM) continue;       // not real features
      if (cur->LUP && std::strncmp(cur->LUP->OBCL, "SOUND", 5) == 0) continue;             // soundings: separate path
      std::string acr(o->FeatureName);
      const char* cd = MyCSVGetField(ocPath.c_str(), "Acronym", acr.c_str(), CC_ExactString, "ObjectClass");
      const char* cc = MyCSVGetField(ocPath.c_str(), "Acronym", acr.c_str(), CC_ExactString, "Code");
      std::string class_desc = (cd && *cd) ? cd : acr;
      int objl = (cc && *cc) ? std::atoi(cc) : -1;
      if (!first) arr += ","; first = false; ++emitted;
      arr += "{\"objl_code\":" + std::to_string(objl) + ",\"acronym\":\"" + json_escape(acr) +
             "\",\"class_desc\":\"" + json_escape(class_desc) + "\",\"geometry\":\"" + geo_str(o->Primitive_type) + "\"";
      std::string attrs = ",\"attributes\":{";
      std::string plain = ",\"plain_language\":[\"" + json_escape(class_desc + " (" + acr + ")") + "\"";
      bool af = true; char* ca = o->att_array;
      for (int i = 0; o->att_array && i < o->n_attr; ++i, ca += 6) {
        wxString an = wxString(ca, wxConvUTF8, 6); an.Trim();
        std::string ak = std::string(an.ToUTF8());
        std::string av = std::string(g_chart->GetObjectAttributeValueAsString(o, i, an).ToUTF8());
        if (!af) attrs += ","; af = false;
        attrs += "\"" + json_escape(ak) + "\":{\"decoded\":\"" + json_escape(av) + "\"}";
        plain += ",\"" + json_escape(ak + ": " + av) + "\"";
      }
      arr += attrs + "}" + plain + "]}";
    }
    rl->Clear(); delete rl;
  }
  arr += "]";
  out.swap(arr);
  return TileStatus::Ok;
}

static bool read_file(const char* path, std::string& out) {
  std::ifstream f(path, std::ios::binary);
  if (!f) return false;
  out.assign(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
  return true;
}
// Parse the first <rte> of a GPX doc into ROUTE + the route name (pugixml, namespace-tolerant).
static bool load_gpx_route(const std::string& xml, std::vector<WP>& out, std::string& routeName) {
  pugi::xml_document doc;
  if (!doc.load_buffer(xml.data(), xml.size())) { std::fprintf(stderr, "GPX parse error\n"); return false; }
  pugi::xml_node gpx = doc.child("gpx"); if (!gpx) gpx = doc.first_child();
  pugi::xml_node rte = gpx.child("rte"); if (!rte) { std::fprintf(stderr, "GPX has no <rte>\n"); return false; }
  if (pugi::xml_node nm = rte.child("name")) routeName = nm.text().get();
  out.clear();
  for (pugi::xml_node pt = rte.child("rtept"); pt; pt = pt.next_sibling("rtept")) {
    pugi::xml_attribute la = pt.attribute("lat"), lo = pt.attribute("lon");
    if (!la || !lo) continue;
    WP w; w.lat = la.as_double(); w.lon = lo.as_double();
    if (pugi::xml_node nm = pt.child("name")) w.name = nm.text().get();
    if (w.name.empty()) { char b[24]; std::snprintf(b, sizeof b, "WP%zu", out.size() + 1); w.name = b; }
    out.push_back(w);
  }
  return out.size() >= 2;
}
// Build an OpenCPN Route from waypoints (named WP1..n) — used for navobj persistence + active-nav.
static Route* build_route(const std::vector<WP>& pts, const std::string& name) {
  Route* r = new Route();
  for (auto& w : pts) r->AddPoint(new RoutePoint(w.lat, w.lon, wxT("circle"), wxString::FromUTF8(w.name.c_str())));
  r->m_RouteNameString = wxString::FromUTF8(name.c_str());
  r->UpdateSegmentDistances(6.0);
  return r;
}
// Read the most-recently-created route + its ordered points straight from navobj.db (the SAME SQLite
// schema OpenCPN's NavObj_dB writes). Read directly rather than via LoadAllRoutes() so we don't need
// pWayPointMan headless. Returns false (→ fall back to GPX) if the db/route isn't there yet.
static bool load_latest_route_from_db(std::vector<WP>& out, std::string& name) {
  if (!g_BasePlatform) return false;
  std::string dbpath = std::string(g_BasePlatform->GetPrivateDataDir().ToUTF8()) + "/navobj.db";
  sqlite3* db = nullptr;
  if (sqlite3_open_v2(dbpath.c_str(), &db, SQLITE_OPEN_READONLY, nullptr) != SQLITE_OK) { if (db) sqlite3_close(db); return false; }
  std::string guid; sqlite3_stmt* st = nullptr;
  if (sqlite3_prepare_v2(db, "SELECT guid, name FROM routes ORDER BY created_at DESC, rowid DESC LIMIT 1", -1, &st, nullptr) == SQLITE_OK) {
    if (sqlite3_step(st) == SQLITE_ROW) {
      const unsigned char* g = sqlite3_column_text(st, 0); guid = g ? reinterpret_cast<const char*>(g) : "";
      const unsigned char* nm = sqlite3_column_text(st, 1); name = nm ? reinterpret_cast<const char*>(nm) : "Route";
    }
    sqlite3_finalize(st);
  }
  if (!guid.empty()) {
    out.clear();
    const char* q = "SELECT rp.lat, rp.lon, rp.Name FROM routepoints rp "
                    "JOIN routepoints_link l ON rp.guid = l.point_guid "
                    "WHERE l.route_guid = ? ORDER BY l.point_order";
    if (sqlite3_prepare_v2(db, q, -1, &st, nullptr) == SQLITE_OK) {
      sqlite3_bind_text(st, 1, guid.c_str(), -1, SQLITE_TRANSIENT);
      while (sqlite3_step(st) == SQLITE_ROW) {
        WP w; w.lat = sqlite3_column_double(st, 0); w.lon = sqlite3_column_double(st, 1);
        const unsigned char* nm = sqlite3_column_text(st, 2); w.name = nm ? reinterpret_cast<const char*>(nm) : "";
        out.push_back(w);
      }
      sqlite3_finalize(st);
    }
  }
  sqlite3_close(db);
  return out.size() >= 2;
}
// Load a SPECIFIC saved route (by guid) + its name from navobj.db. Mirrors load_latest_route_from_db.
static bool load_route_by_guid(const std::string& guid, std::vector<WP>& out, std::string& name) {
  if (!g_BasePlatform || guid.empty()) return false;
  std::string dbpath = std::string(g_BasePlatform->GetPrivateDataDir().ToUTF8()) + "/navobj.db";
  sqlite3* db = nullptr;
  if (sqlite3_open_v2(dbpath.c_str(), &db, SQLITE_OPEN_READONLY, nullptr) != SQLITE_OK) { if (db) sqlite3_close(db); return false; }
  sqlite3_stmt* st = nullptr;
  if (sqlite3_prepare_v2(db, "SELECT name FROM routes WHERE guid = ?", -1, &st, nullptr) == SQLITE_OK) {
    sqlite3_bind_text(st, 1, guid.c_str(), -1, SQLITE_TRANSIENT);
    if (sqlite3_step(st) == SQLITE_ROW) { const unsigned char* nm = sqlite3_column_text(st, 0); name = nm ? reinterpret_cast<const char*>(nm) : "Route"; }
    sqlite3_finalize(st);
  }
  out.clear();
  const char* q = "SELECT rp.lat, rp.lon, rp.Name FROM routepoints rp "
                  "JOIN routepoints_link l ON rp.guid = l.point_guid "
                  "WHERE l.route_guid = ? ORDER BY l.point_order";
  if (sqlite3_prepare_v2(db, q, -1, &st, nullptr) == SQLITE_OK) {
    sqlite3_bind_text(st, 1, guid.c_str(), -1, SQLITE_TRANSIENT);
    while (sqlite3_step(st) == SQLITE_ROW) {
      WP w; w.lat = sqlite3_column_double(st, 0); w.lon = sqlite3_column_double(st, 1);
      const unsigned char* nm = sqlite3_column_text(st, 2); w.name = nm ? reinterpret_cast<const char*>(nm) : "";
      out.push_back(w);
    }
    sqlite3_finalize(st);
  }
  sqlite3_close(db);
  return out.size() >= 2;
}
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
struct RField { double v = 0; std::time_t t = 0; const char* src = "nmea"; };
struct RealFeed { std::mutex m; double lat = 0, lon = 0; std::time_t pos_t = 0; const char* pos_src = "nmea";
                  RField sog, cog, hdg, depth, wspd, wdir; };
static RealFeed g_real;

// AIS — OpenCPN's real AisDecoder driven headless (decode + CPA/TCPA stay in its code). We
// snapshot the decoded targets into our own set at decode time and age on our own clock.
extern Select* pSelectAIS;                 // model global (ais_decoder.cpp), seeded in OnInit
static AisDecoder* g_ais = nullptr;
static std::mutex  g_ais_mtx;
struct AisRow { int mmsi; double lat, lon, cog, sog, hdg, range, brg, cpa, tcpa;
                bool cpaValid; int cls; std::string name; std::time_t seen;
                // forwarded from OpenCPN's already-decoded AisTargetData for the rich target card
                int navStatus, shipType, rot, imo, length, beam, etaMo, etaDay, etaHr, etaMin;
                std::string callsign, destination; double draft; };
static std::string ais_trim(std::string s) {     // AIS text fields are right-padded with '@' (6-bit 0) / spaces
  size_t e = s.find_last_not_of("@ "); return e == std::string::npos ? std::string() : s.substr(0, e + 1);
}
static std::map<int, AisRow> g_ais_rows;
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
  // AIS (!AIVDM/!AIVDO) -> OpenCPN's decoder (own checksum + multipart reassembly). Routed BEFORE
  // the $-only checksum gate. Snapshot the decoded targets (range/brg/CPA/TCPA) into g_ais_rows.
  if (g_ais && line.size() >= 6 && (line.compare(0, 6, "!AIVDM") == 0 || line.compare(0, 6, "!AIVDO") == 0)) {
    std::lock_guard<std::mutex> lk(g_ais_mtx);
    g_ais->DecodeN0183(wxString::FromUTF8(line.c_str()));
    std::time_t snap = std::time(nullptr);
    for (auto& kv : g_ais->GetTargetList()) {
      auto& t = kv.second;
      g_ais_rows[t->MMSI] = { t->MMSI, t->Lat, t->Lon, t->COG, t->SOG, t->HDG, t->Range_NM, t->Brg,
        t->CPA, t->TCPA, t->bCPA_Valid, (int)t->Class, ais_trim(t->ShipName), snap,
        t->NavStatus, (int)t->ShipType, t->ROTAIS, t->IMO, t->DimA + t->DimB, t->DimC + t->DimD,
        t->ETA_Mo, t->ETA_Day, t->ETA_Hr, t->ETA_Min, ais_trim(t->CallSign), ais_trim(t->Destination), t->Draft };
    }
    return;
  }
  if (!nmea_csum_ok(line)) { std::fprintf(stderr, "NMEA rejected (bad checksum): %s\n", line.c_str()); return; }
  std::vector<std::string> f = splitc(line.substr(0, line.rfind('*')));
  if (f.empty() || f[0].size() < 6) return;
  std::string type = f[0].substr(3); std::time_t now = std::time(nullptr);
  std::lock_guard<std::mutex> lk(g_real.m);
  if (type == "RMC" && f.size() >= 9 && f[2] == "A") {
    g_real.lat = nmea_ll(f[3], f[4]); g_real.lon = nmea_ll(f[5], f[6]); g_real.pos_t = now; g_real.pos_src = "nmea";
    if (!f[7].empty()) { g_real.sog.v = std::atof(f[7].c_str()); g_real.sog.t = now; g_real.sog.src = "nmea"; }
    if (!f[8].empty()) { g_real.cog.v = std::atof(f[8].c_str()); g_real.cog.t = now; g_real.cog.src = "nmea"; }
  } else if (type == "DPT" && f.size() >= 2 && !f[1].empty()) { g_real.depth.v = std::atof(f[1].c_str()); g_real.depth.t = now; g_real.depth.src = "nmea"; }
  else if (type == "DBT" && f.size() >= 4 && !f[3].empty()) { g_real.depth.v = std::atof(f[3].c_str()); g_real.depth.t = now; g_real.depth.src = "nmea"; }
  else if (type == "MWV" && f.size() >= 6 && f[5] == "A") {
    if (!f[1].empty()) { g_real.wdir.v = std::atof(f[1].c_str()); g_real.wdir.t = now; g_real.wdir.src = "nmea"; }
    if (!f[3].empty()) { double sp = std::atof(f[3].c_str()); if (f[4] == "K") sp *= 0.539957; else if (f[4] == "M") sp *= 1.943844; g_real.wspd.v = sp; g_real.wspd.t = now; g_real.wspd.src = "nmea"; }
  } else if (type == "HDT" && f.size() >= 2 && !f[1].empty()) { g_real.hdg.v = std::atof(f[1].c_str()); g_real.hdg.t = now; g_real.hdg.src = "nmea"; }
}
// SignalK overlay — consume a SignalK server's WS delta stream as a CLIENT. Maps self-vessel
// paths onto the SAME g_real per-field override, tagged "signalk". SI units -> kn/deg/m.
static ix::WebSocket* g_sk = nullptr;
static std::string g_sk_self;
static void sk_apply(const std::string& path, const rapidjson::Value& v, std::time_t now) {
  auto set = [&](RField& f, double val) { f.v = val; f.t = now; f.src = "signalk"; };
  const double MS2KN = 1.943844, R2D = 180.0 / M_PI;
  if (path == "navigation.position" && v.IsObject() && v.HasMember("latitude") && v.HasMember("longitude") &&
      v["latitude"].IsNumber() && v["longitude"].IsNumber()) {
    g_real.lat = v["latitude"].GetDouble(); g_real.lon = v["longitude"].GetDouble();
    g_real.pos_t = now; g_real.pos_src = "signalk";
  } else if (path == "navigation.speedOverGround" && v.IsNumber()) set(g_real.sog, v.GetDouble() * MS2KN);
  else if (path == "navigation.courseOverGroundTrue" && v.IsNumber()) set(g_real.cog, v.GetDouble() * R2D);
  else if (path == "navigation.headingTrue" && v.IsNumber()) set(g_real.hdg, v.GetDouble() * R2D);
  else if (path == "environment.depth.belowTransducer" && v.IsNumber()) set(g_real.depth, v.GetDouble());
  else if (path == "environment.wind.speedApparent" && v.IsNumber()) set(g_real.wspd, v.GetDouble() * MS2KN);
  else if (path == "environment.wind.angleApparent" && v.IsNumber()) { double d = v.GetDouble() * R2D; if (d < 0) d += 360.0; set(g_real.wdir, d); }
}
static void sk_on_message(const std::string& msg) {
  rapidjson::Document d;
  if (d.Parse(msg.c_str()).HasParseError() || !d.IsObject()) return;
  if (d.HasMember("self") && d["self"].IsString()) { g_sk_self = d["self"].GetString(); return; }
  if (!d.HasMember("updates") || !d["updates"].IsArray()) return;
  if (d.HasMember("context") && d["context"].IsString()) {     // own-ship only; other vessels = AIS
    std::string ctx = d["context"].GetString();
    if (ctx != "vessels.self" && (g_sk_self.empty() || ctx != g_sk_self)) return;
  }
  std::time_t now = std::time(nullptr);
  std::lock_guard<std::mutex> lk(g_real.m);
  for (auto& u : d["updates"].GetArray()) {
    if (!u.HasMember("values") || !u["values"].IsArray()) continue;
    for (auto& val : u["values"].GetArray())
      if (val.HasMember("path") && val["path"].IsString() && val.HasMember("value"))
        sk_apply(val["path"].GetString(), val["value"], now);
  }
}
static void sk_start(std::string url) {
  if (url.find("://") == std::string::npos) url = "ws://" + url + "/signalk/v1/stream?subscribe=self";
  g_sk = new ix::WebSocket(); g_sk->setUrl(url); g_sk->setPingInterval(20); g_sk->enableAutomaticReconnection();
  g_sk->setOnMessageCallback([](const ix::WebSocketMessagePtr& m) {
    if (m->type == ix::WebSocketMessageType::Message) sk_on_message(m->str);
    else if (m->type == ix::WebSocketMessageType::Open) std::printf("SignalK: connected\n");
  });
  std::printf("SignalK input: %s (self-vessel nav overrides sim per-field)\n", url.c_str());
  g_sk->start();
}
// ===========================================================================
// Track recording (ownship breadcrumb) — the ENGINE owns the trail; thin clients
// just display it (single source of truth, native inherits it). Records the displayed
// fix when armed (default on), thinned by distance/time so an overnight swing at anchor
// stays compact. In-memory + capped here; GPX export is a later step.
// ===========================================================================
struct TrackPt { double lat, lon; std::time_t t; };
static std::mutex g_track_mtx;
static std::vector<TrackPt> g_track;            // recorded points (rolling, capped) — guard: g_track_mtx
static size_t g_track_emitted = 0;              // points already streamed (for trackAdd deltas) — g_track_mtx
static std::atomic<bool> g_track_armed{true};   // recording on by default
static const size_t kTrackCap = 3000;
static const double kTrackMinNM  = 0.002;       // ~3.7 m — OpenCPN "Medium" min-move (model/src/track.cpp SetPrecision)
static const double kTrackMinSec = 4.0;         // ...and >= this long since the last point (OpenCPN "Medium")
static std::string g_track_src;                 // source of the last recorded fix — g_track_mtx
static void track_record(double lat, double lon, const char* src) {
  if (!g_track_armed.load()) return;            // always-on by default — recording is automatic, like OpenCPN
  std::time_t now = std::time(nullptr);
  std::lock_guard<std::mutex> lk(g_track_mtx);
  std::string s = src ? src : "";
  if (!g_track.empty() && s != g_track_src) {   // source changed (e.g. demo-origin sim → real fix) — the
    g_track.clear(); g_track_emitted = 0;       // position teleports, so start a CLEAN track, don't draw across it
  }
  g_track_src = s;
  if (!g_track.empty()) {
    const TrackPt& last = g_track.back();
    double brg, nm; bd(lat, lon, last.lat, last.lon, &brg, &nm);
    // OpenCPN-style commit: BOTH enough time elapsed AND moved beyond the min delta. Distance-gated
    // (NOT speed) so the anchor SWING is captured (it's movement) while a dead-still boat adds nothing.
    if (std::difftime(now, last.t) < kTrackMinSec || nm < kTrackMinNM) return;
  }
  g_track.push_back({lat, lon, now});
  if (g_track.size() > kTrackCap) {
    size_t drop = g_track.size() - kTrackCap;
    g_track.erase(g_track.begin(), g_track.begin() + drop);
    g_track_emitted = (g_track_emitted > drop) ? (g_track_emitted - drop) : 0;
  }
}

// ===========================================================================
// Connections — runtime-configurable, persisted, multi-source live-data input.
// Each connection is an independent driver thread feeding the SAME nmea_parse →
// g_real / AisDecoder pipeline, so per-field source tags stay truthful. The engine
// does NOT pump a wxWidgets event loop, so we use plain BSD sockets with our own
// reconnect/backoff — and crucially support TCP-CLIENT (connect-out), which marine
// WiFi gateways require (Garmin Vesper Cortex :39150, PredictWind DataHub, …).
// Config is owned by the ENGINE and persisted to ~/.helm/connections.json; clients
// edit it over the nav-WS command-plane (conn.list / conn.upsert / conn.delete) and
// read live status back in the nav frame. (SignalK input stays on HELM_SIGNALK for now.)
// ===========================================================================
enum class ConnStatus { Disabled, Connecting, Connected, NoData, Error };
static const char* conn_status_str(ConnStatus s) {
  switch (s) {
    case ConnStatus::Disabled:   return "disabled";
    case ConnStatus::Connecting: return "connecting";
    case ConnStatus::Connected:  return "connected";
    case ConnStatus::NoData:     return "nodata";
    default:                     return "error";
  }
}
struct ConnConfig { std::string id, name, type, address, dataProtocol, comment; int port = 0; bool enabled = true; };
struct ConnRuntime {
  std::atomic<bool> want_stop{false};
  std::atomic<int>  status{(int)ConnStatus::Connecting};
  std::atomic<long> last_rx{0};
  std::atomic<long> sentences{0};
  std::string last_error;                          // guarded by g_conns_mtx
};
static std::mutex g_conns_mtx;
static std::map<std::string, ConnConfig> g_conns;                       // id -> config
static std::map<std::string, std::shared_ptr<ConnRuntime>> g_conn_rt;   // id -> runtime
static std::string g_owner_token;                                       // optional write gate (HELM_OWNER_TOKEN)
static long g_conn_counter = 0;

static std::string conn_dir() {
  if (const char* c = std::getenv("HELM_CONFIG")) if (*c) return c;
  const char* home = std::getenv("HOME"); std::string d = (home && *home) ? home : ".";
  return d + "/.helm";
}
static std::string conn_path() { return conn_dir() + "/connections.json"; }

// Non-blocking TCP connect-out with a bounded timeout; resolves host (IP or name) via getaddrinfo.
static int tcp_connect(const std::string& host, int port, int timeout_sec, std::string& err) {
  addrinfo hints{}; hints.ai_family = AF_UNSPEC; hints.ai_socktype = SOCK_STREAM;
  addrinfo* res = nullptr; char ports[16]; std::snprintf(ports, sizeof ports, "%d", port);
  int g = ::getaddrinfo(host.c_str(), ports, &hints, &res);
  if (g != 0 || !res) { err = std::string("resolve: ") + gai_strerror(g); return -1; }
  int fd = -1;
  for (addrinfo* p = res; p; p = p->ai_next) {
    fd = ::socket(p->ai_family, p->ai_socktype, p->ai_protocol); if (fd < 0) continue;
    int fl = ::fcntl(fd, F_GETFL, 0); ::fcntl(fd, F_SETFL, fl | O_NONBLOCK);
    int rc = ::connect(fd, p->ai_addr, p->ai_addrlen);
    if (rc == 0) { ::fcntl(fd, F_SETFL, fl); break; }
    if (errno == EINPROGRESS) {
      pollfd pfd{fd, POLLOUT, 0}; int pr = ::poll(&pfd, 1, timeout_sec * 1000);
      if (pr > 0) { int se = 0; socklen_t sl = sizeof se; ::getsockopt(fd, SOL_SOCKET, SO_ERROR, &se, &sl);
        if (se == 0) { ::fcntl(fd, F_SETFL, fl); break; } err = std::string("connect: ") + std::strerror(se); }
      else err = (pr == 0) ? "connect: timeout" : "connect: poll error";
    } else err = std::string("connect: ") + std::strerror(errno);
    ::close(fd); fd = -1;
  }
  ::freeaddrinfo(res);
  if (fd >= 0) { timeval tv{5, 0}; ::setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv); }
  else if (err.empty()) err = "connect: failed";
  return fd;
}
// TCP server: bind+listen, wait (interruptibly) for ONE client, return its fd. Re-binds per client.
static int tcp_server_accept(const std::string& host, int port, const std::shared_ptr<ConnRuntime>& rt, std::string& err) {
  int srv = ::socket(AF_INET, SOCK_STREAM, 0); if (srv < 0) { err = "socket"; return -1; }
  int yes = 1; ::setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
  sockaddr_in a{}; a.sin_family = AF_INET; a.sin_port = htons((uint16_t)port);
  a.sin_addr.s_addr = (host == "0.0.0.0" || host.empty()) ? INADDR_ANY : inet_addr(host.c_str());
  if (::bind(srv, (sockaddr*)&a, sizeof a) < 0 || ::listen(srv, 4) < 0) { err = "bind/listen :" + std::to_string(port); ::close(srv); return -1; }
  for (;;) {
    if (rt->want_stop) { ::close(srv); err = "stopped"; return -1; }
    pollfd pfd{srv, POLLIN, 0}; int pr = ::poll(&pfd, 1, 1000);
    if (pr > 0) { int c = ::accept(srv, nullptr, nullptr); ::close(srv);
      if (c < 0) { err = "accept"; return -1; }
      timeval tv{5, 0}; ::setsockopt(c, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv); return c; }
    if (pr < 0) { ::close(srv); err = "poll"; return -1; }
  }
}
static int udp_bind(const std::string& host, int port, std::string& err) {
  int fd = ::socket(AF_INET, SOCK_DGRAM, 0); if (fd < 0) { err = "socket"; return -1; }
  int yes = 1; ::setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
  sockaddr_in a{}; a.sin_family = AF_INET; a.sin_port = htons((uint16_t)port);
  a.sin_addr.s_addr = (host.empty() || host == "0.0.0.0") ? INADDR_ANY : inet_addr(host.c_str());
  if (::bind(fd, (sockaddr*)&a, sizeof a) < 0) { err = "bind :" + std::to_string(port); ::close(fd); return -1; }
  timeval tv{5, 0}; ::setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv); return fd;
}
// Read NMEA lines off a connected fd until EOF/error/stop, feeding nmea_parse and updating status.
static void conn_feed_fd(int fd, const std::shared_ptr<ConnRuntime>& rt) {
  std::string buf; char rb[2048];
  for (;;) {
    if (rt->want_stop) return;
    ssize_t n = ::recv(fd, rb, sizeof rb, 0);
    if (n > 0) {
      rt->last_rx = (long)std::time(nullptr); rt->status = (int)ConnStatus::Connected;
      buf.append(rb, (size_t)n); size_t nl;
      while ((nl = buf.find('\n')) != std::string::npos) {
        std::string line = buf.substr(0, nl); buf.erase(0, nl + 1);
        while (!line.empty() && (line.back() == '\r' || line.back() == ' ')) line.pop_back();
        if (!line.empty()) { nmea_parse(line); rt->sentences++; }
      }
      if (buf.size() > (1u << 16)) buf.clear();          // runaway guard (never a newline)
    } else if (n == 0) { return; }                       // peer closed
    else {
      if (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR) {
        if (rt->last_rx && (long)std::time(nullptr) - rt->last_rx > 10) rt->status = (int)ConnStatus::NoData;
        continue;
      }
      return;                                            // real error
    }
  }
}
// SignalK driver as a managed connection (CONN-5): a per-connection WebSocket that feeds the SAME
// sk_on_message → g_real per-field overrides as the HELM_SIGNALK path, but lifecycle-bound to the
// ConnRuntime so conn.upsert/disable/delete start+stop it, with live status in the nav frame.
// SignalK is JSON-over-WS, not line NMEA, so it does NOT use conn_feed_fd.
static void conn_feed_signalk(const ConnConfig& cfg, const std::shared_ptr<ConnRuntime>& rt) {
  std::string url = cfg.address;
  if (url.find("://") == std::string::npos) {            // bare host[:port] → SignalK stream URL
    std::string host = cfg.address;
    if (cfg.port > 0 && host.find(':') == std::string::npos) host += ":" + std::to_string(cfg.port);
    url = "ws://" + host + "/signalk/v1/stream?subscribe=self";
  }
  ix::WebSocket ws; ws.setUrl(url); ws.setPingInterval(20); ws.enableAutomaticReconnection();
  ws.setOnMessageCallback([rt](const ix::WebSocketMessagePtr& m) {
    if (m->type == ix::WebSocketMessageType::Message) {
      sk_on_message(m->str);
      rt->last_rx = (long)std::time(nullptr); rt->sentences++;
      rt->status = (int)ConnStatus::Connected;
    } else if (m->type == ix::WebSocketMessageType::Open) {
      rt->status = (int)ConnStatus::Connected;
      { std::lock_guard<std::mutex> lk(g_conns_mtx); rt->last_error.clear(); }
    } else if (m->type == ix::WebSocketMessageType::Error) {
      rt->status = (int)ConnStatus::Error;
      { std::lock_guard<std::mutex> lk(g_conns_mtx); rt->last_error = m->errorInfo.reason; }
    } else if (m->type == ix::WebSocketMessageType::Close) {
      if (!rt->want_stop) rt->status = (int)ConnStatus::NoData;
    }
  });
  ws.start();
  for (;;) {                                             // hold the thread until asked to stop
    if (rt->want_stop) break;
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
    if (rt->last_rx && (long)std::time(nullptr) - rt->last_rx > 10 &&
        rt->status == (int)ConnStatus::Connected)
      rt->status = (int)ConnStatus::NoData;              // connected but deltas stalled
  }
  ws.stop();
}
static void conn_thread(std::string id, std::shared_ptr<ConnRuntime> rt) {
  int backoff = 1;
  for (;;) {
    if (rt->want_stop) return;
    ConnConfig cfg;
    { std::lock_guard<std::mutex> lk(g_conns_mtx);
      auto it = g_conns.find(id); if (it == g_conns.end()) return;          // deleted
      cfg = it->second; if (!cfg.enabled) { rt->status = (int)ConnStatus::Disabled; return; } }
    rt->status = (int)ConnStatus::Connecting;
    if (cfg.type == "signalk") { conn_feed_signalk(cfg, rt); return; }   // SignalK WS driver — self-managed lifecycle + reconnect
    std::string err; int fd = -1;
    if (cfg.type == "tcp-client")      fd = tcp_connect(cfg.address, cfg.port, 6, err);
    else if (cfg.type == "tcp-server") fd = tcp_server_accept(cfg.address.empty() ? "127.0.0.1" : cfg.address, cfg.port, rt, err);
    else if (cfg.type == "udp")        fd = udp_bind(cfg.address, cfg.port, err);
    else { { std::lock_guard<std::mutex> lk(g_conns_mtx); rt->last_error = "unsupported type: " + cfg.type; } rt->status = (int)ConnStatus::Error; return; }
    if (fd < 0) {
      { std::lock_guard<std::mutex> lk(g_conns_mtx); rt->last_error = err; }
      rt->status = (int)ConnStatus::Error;
      for (int i = 0; i < backoff * 10 && !rt->want_stop; ++i) std::this_thread::sleep_for(std::chrono::milliseconds(100));
      backoff = std::min(backoff * 2, 15); continue;
    }
    backoff = 1; rt->status = (int)ConnStatus::Connected;
    { std::lock_guard<std::mutex> lk(g_conns_mtx); rt->last_error.clear(); }
    conn_feed_fd(fd, rt);
    ::close(fd);
    if (rt->want_stop) return;
    rt->status = (int)ConnStatus::NoData;
    for (int i = 0; i < 10 && !rt->want_stop; ++i) std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }
}
static void conn_kill_locked(const std::string& id) {                 // caller holds g_conns_mtx
  auto it = g_conn_rt.find(id);
  if (it != g_conn_rt.end()) { it->second->want_stop = true; g_conn_rt.erase(it); }
}
static void conn_spawn_locked(const std::string& id) {                 // caller holds g_conns_mtx
  auto rt = std::make_shared<ConnRuntime>(); g_conn_rt[id] = rt;
  std::thread(conn_thread, id, rt).detach();
}
static void conn_upsert(const ConnConfig& c) {
  std::lock_guard<std::mutex> lk(g_conns_mtx);
  g_conns[c.id] = c; conn_kill_locked(c.id);
  if (c.enabled) conn_spawn_locked(c.id);
}
static void conn_delete(const std::string& id) {
  std::lock_guard<std::mutex> lk(g_conns_mtx);
  conn_kill_locked(id); g_conns.erase(id);
}
static std::string conn_status_array() {
  std::string out = "["; std::lock_guard<std::mutex> lk(g_conns_mtx);
  long now = (long)std::time(nullptr); bool first = true;
  for (auto& kv : g_conns) {
    const ConnConfig& c = kv.second; auto itr = g_conn_rt.find(c.id);
    std::shared_ptr<ConnRuntime> rt = (itr != g_conn_rt.end()) ? itr->second : nullptr;
    ConnStatus st = !c.enabled ? ConnStatus::Disabled : (rt ? (ConnStatus)rt->status.load() : ConnStatus::Connecting);
    long lrx = rt ? rt->last_rx.load() : 0; long age = lrx ? now - lrx : -1;
    long sent = rt ? rt->sentences.load() : 0; std::string lerr = rt ? rt->last_error : std::string();
    out += std::string(first ? "" : ",") +
      "{\"id\":\"" + json_escape(c.id) + "\",\"name\":\"" + json_escape(c.name) +
      "\",\"type\":\"" + json_escape(c.type) + "\",\"address\":\"" + json_escape(c.address) +
      "\",\"port\":" + std::to_string(c.port) + ",\"enabled\":" + (c.enabled ? "true" : "false") +
      ",\"status\":\"" + conn_status_str(st) + "\",\"ageSec\":" + std::to_string(age) +
      ",\"sentences\":" + std::to_string(sent) + (lerr.empty() ? "" : (",\"error\":\"" + json_escape(lerr) + "\"")) + "}";
    first = false;
  }
  out += "]"; return out;
}
static std::string conn_list_msg() { return std::string("{\"t\":\"conn.list\",\"conns\":") + conn_status_array() + "}"; }
static std::string conn_ack(bool ok, const std::string& id, const std::string& err) {
  return std::string("{\"t\":\"conn.ack\",\"ok\":") + (ok ? "true" : "false") +
         ",\"id\":\"" + json_escape(id) + "\"" + (err.empty() ? "" : (",\"error\":\"" + json_escape(err) + "\"")) + "}";
}
static std::string conn_slug(const std::string& s) {
  std::string o; for (unsigned char c : s) { if (std::isalnum(c)) o += (char)std::tolower(c); else if (!o.empty() && o.back() != '-') o += '-'; }
  while (!o.empty() && o.back() == '-') o.pop_back(); if (o.size() > 24) o.resize(24); return o;
}
static bool conn_from_json(const rapidjson::Value& v, ConnConfig& c, std::string& err) {
  auto gs = [&](const char* k) -> std::string { return (v.HasMember(k) && v[k].IsString()) ? v[k].GetString() : std::string(); };
  c.id = gs("id"); c.name = gs("name"); c.type = gs("type"); c.address = gs("address");
  c.dataProtocol = gs("dataProtocol"); c.comment = gs("comment");
  if (v.HasMember("port") && v["port"].IsInt()) c.port = v["port"].GetInt();
  else if (v.HasMember("port") && v["port"].IsString()) c.port = std::atoi(v["port"].GetString());
  c.enabled = !(v.HasMember("enabled") && v["enabled"].IsBool()) || v["enabled"].GetBool();
  if (c.dataProtocol.empty()) c.dataProtocol = (c.type == "signalk") ? "signalk" : "nmea0183";
  if (c.type != "tcp-client" && c.type != "tcp-server" && c.type != "udp" && c.type != "signalk") { err = "type must be tcp-client | tcp-server | udp | signalk"; return false; }
  if (c.port < 1 || c.port > 65535) { err = "port must be 1-65535"; return false; }
  if ((c.type == "tcp-client" || c.type == "signalk") && c.address.empty()) { err = "address required for " + c.type; return false; }
  if (c.id.empty()) { std::string b = conn_slug(c.name.empty() ? c.type : c.name); if (b.empty()) b = "conn"; c.id = b + "-" + std::to_string(++g_conn_counter); }
  return true;
}
static void conn_save() {
  std::string js = "[";
  { std::lock_guard<std::mutex> lk(g_conns_mtx); bool first = true;
    for (auto& kv : g_conns) { const ConnConfig& c = kv.second;
      js += std::string(first ? "" : ",") +
        "{\"id\":\"" + json_escape(c.id) + "\",\"name\":\"" + json_escape(c.name) +
        "\",\"type\":\"" + json_escape(c.type) + "\",\"address\":\"" + json_escape(c.address) +
        "\",\"port\":" + std::to_string(c.port) + ",\"dataProtocol\":\"" + json_escape(c.dataProtocol) +
        "\",\"enabled\":" + (c.enabled ? "true" : "false") + ",\"comment\":\"" + json_escape(c.comment) + "\"}";
      first = false; } }
  js += "]";
  std::string dir = conn_dir(); ::mkdir(dir.c_str(), 0700);
  std::string path = conn_path(), tmp = path + ".tmp";
  { std::ofstream f(tmp, std::ios::binary | std::ios::trunc); if (!f) { std::fprintf(stderr, "conn_save: cannot write %s\n", tmp.c_str()); return; } f << js; }
  ::chmod(tmp.c_str(), 0600);
  if (::rename(tmp.c_str(), path.c_str()) != 0) std::fprintf(stderr, "conn_save: rename %s failed\n", path.c_str());
}
static void conn_load() {
  std::string body; if (!read_file(conn_path().c_str(), body)) return;       // none yet
  rapidjson::Document d;
  if (d.Parse(body.c_str()).HasParseError() || !d.IsArray()) { std::fprintf(stderr, "conn_load: %s corrupt — ignoring\n", conn_path().c_str()); return; }
  std::lock_guard<std::mutex> lk(g_conns_mtx);
  for (auto& e : d.GetArray()) {
    if (!e.IsObject()) continue; ConnConfig c;
    auto gs = [&](const char* k) -> std::string { return (e.HasMember(k) && e[k].IsString()) ? e[k].GetString() : std::string(); };
    c.id = gs("id"); c.name = gs("name"); c.type = gs("type"); c.address = gs("address");
    c.dataProtocol = gs("dataProtocol"); c.comment = gs("comment");
    if (e.HasMember("port") && e["port"].IsInt()) c.port = e["port"].GetInt();
    c.enabled = !(e.HasMember("enabled") && e["enabled"].IsBool()) || e["enabled"].GetBool();
    if (c.id.empty() || c.type.empty()) continue;
    g_conns[c.id] = c; if (c.enabled) conn_spawn_locked(c.id);
  }
  std::printf("connections: loaded %zu from %s\n", g_conns.size(), conn_path().c_str());
}
// Command-plane: inbound nav-WS messages from a client. (Replaces the old push-only lambda.)
static void handle_command(const std::string& msg, const std::shared_ptr<ix::WebSocket>& ws) {
  rapidjson::Document d;
  if (d.Parse(msg.c_str()).HasParseError() || !d.IsObject() || !d.HasMember("t") || !d["t"].IsString()) return;
  std::string t = d["t"].GetString();
  if (t == "hello") return;                                  // legacy nav-client handshake — ignore
  if (!g_owner_token.empty()) {
    std::string tok = (d.HasMember("token") && d["token"].IsString()) ? d["token"].GetString() : std::string();
    if (tok != g_owner_token) { ws->send(conn_ack(false, "", "unauthorized")); return; }
  }
  if (t == "conn.list") { ws->send(conn_list_msg()); return; }
  if (t == "conn.upsert" && d.HasMember("conn") && d["conn"].IsObject()) {
    ConnConfig c; std::string err;
    if (!conn_from_json(d["conn"], c, err)) { ws->send(conn_ack(false, "", err)); return; }
    conn_upsert(c); conn_save();
    std::printf("connections: upsert \"%s\" %s %s:%d (%s)\n", c.name.c_str(), c.type.c_str(), c.address.c_str(), c.port, c.enabled ? "enabled" : "disabled");
    ws->send(conn_ack(true, c.id, "")); ws->send(conn_list_msg()); return;
  }
  if (t == "conn.delete" && d.HasMember("id") && d["id"].IsString()) {
    std::string id = d["id"].GetString(); conn_delete(id); conn_save();
    std::printf("connections: delete %s\n", id.c_str());
    ws->send(conn_ack(true, id, "")); ws->send(conn_list_msg()); return;
  }
  if (t == "track.arm" && d.HasMember("on") && d["on"].IsBool()) {          // arm/pause breadcrumb recording
    g_track_armed = d["on"].GetBool();
    std::printf("track: recording %s\n", g_track_armed.load() ? "ON" : "paused");
    ws->send(std::string("{\"t\":\"track.ack\",\"armed\":") + (g_track_armed.load() ? "true" : "false") + "}"); return;
  }
  if (t == "track.clear") {                                                 // wipe the recorded trail
    { std::lock_guard<std::mutex> lk(g_track_mtx); g_track.clear(); g_track_emitted = 0; }
    std::printf("track: cleared\n");
    ws->send("{\"t\":\"track.ack\",\"cleared\":true}"); return;
  }
  if (t == "route.create" && d.HasMember("points") && d["points"].IsArray()) {   // create/replace the active route
    std::vector<WP> pts;
    for (auto& p : d["points"].GetArray())
      if (p.IsArray() && p.Size() >= 2 && p[0].IsNumber() && p[1].IsNumber())
        pts.push_back({ p[0].GetDouble(), p[1].GetDouble(), "" });               // [lat, lon]
    if (pts.size() < 2) { ws->send("{\"t\":\"route.ack\",\"ok\":false,\"error\":\"need >=2 points\"}"); return; }
    std::string name = (d.HasMember("name") && d["name"].IsString() && *d["name"].GetString()) ? d["name"].GetString() : "Route";
    for (size_t i = 0; i < pts.size(); ++i) { char b[16]; std::snprintf(b, sizeof b, "WP%zu", i + 1); pts[i].name = b; }
    Route* nr = build_route(pts, name);
    NavObj_dB::GetInstance().InsertRoute(nr);   // persist to navobj.db (route + points + links). nr then leaked (rare; see rebuild_route)
    { std::lock_guard<std::mutex> lk(g_route_mtx); ROUTE = pts; g_route_name = name; }
    g_route_version++;                          // nav_loop swaps to it on the next tick
    std::printf("route: created \"%s\" (%zu wp) — persisted to navobj.db + activated\n", name.c_str(), pts.size());
    ws->send(std::string("{\"t\":\"route.ack\",\"ok\":true,\"name\":\"") + json_escape(name) + "\"}"); return;
  }
  if (t == "route.list") {                                                    // list saved routes from navobj.db
    std::string rn; { std::lock_guard<std::mutex> lk(g_route_mtx); rn = g_route_name; }
    std::string arr = "[";
    if (g_BasePlatform) {
      std::string dbpath = std::string(g_BasePlatform->GetPrivateDataDir().ToUTF8()) + "/navobj.db";
      sqlite3* db = nullptr;
      if (sqlite3_open_v2(dbpath.c_str(), &db, SQLITE_OPEN_READONLY, nullptr) == SQLITE_OK) {
        sqlite3_stmt* st = nullptr;
        const char* q = "SELECT r.guid, r.name, COUNT(l.point_guid) FROM routes r "
                        "LEFT JOIN routepoints_link l ON r.guid = l.route_guid "
                        "GROUP BY r.guid, r.name ORDER BY r.created_at DESC, r.rowid DESC";
        if (sqlite3_prepare_v2(db, q, -1, &st, nullptr) == SQLITE_OK) {
          bool first = true;
          while (sqlite3_step(st) == SQLITE_ROW) {
            const unsigned char* g = sqlite3_column_text(st, 0);
            const unsigned char* nm = sqlite3_column_text(st, 1);
            std::string guid = g ? reinterpret_cast<const char*>(g) : "";
            std::string nme = nm ? reinterpret_cast<const char*>(nm) : "Route";
            char tail[48]; std::snprintf(tail, sizeof tail, ",\"points\":%d,\"active\":%s}",
              sqlite3_column_int(st, 2), (nme == rn) ? "true" : "false");
            arr += (first ? "" : ",");
            arr += "{\"guid\":\"" + json_escape(guid) + "\",\"name\":\"" + json_escape(nme) + "\"" + tail;
            first = false;
          }
          sqlite3_finalize(st);
        }
        sqlite3_close(db);
      }
    }
    arr += "]";
    ws->send(std::string("{\"t\":\"route.list\",\"routes\":") + arr + "}"); return;
  }
  if (t == "route.activate" && d.HasMember("guid") && d["guid"].IsString()) {  // switch the active route
    std::vector<WP> pts; std::string name = "Route";
    if (load_route_by_guid(d["guid"].GetString(), pts, name)) {
      { std::lock_guard<std::mutex> lk(g_route_mtx); ROUTE = pts; g_route_name = name; }
      g_route_version++;
      std::printf("route: activated \"%s\" (%zu wp)\n", name.c_str(), pts.size());
      ws->send(std::string("{\"t\":\"route.ack\",\"ok\":true,\"name\":\"") + json_escape(name) + "\"}");
    } else ws->send("{\"t\":\"route.ack\",\"ok\":false,\"error\":\"route not found\"}");
    return;
  }
  if (t == "route.delete" && d.HasMember("guid") && d["guid"].IsString()) {    // remove a saved route + its points
    std::string guid = d["guid"].GetString(); bool ok = false;
    if (g_BasePlatform) {
      std::string dbpath = std::string(g_BasePlatform->GetPrivateDataDir().ToUTF8()) + "/navobj.db";
      sqlite3* db = nullptr;
      if (sqlite3_open_v2(dbpath.c_str(), &db, SQLITE_OPEN_READWRITE, nullptr) == SQLITE_OK) {
        const char* stmts[] = {
          "DELETE FROM routepoints WHERE guid IN (SELECT point_guid FROM routepoints_link WHERE route_guid=?1) "
          "AND guid NOT IN (SELECT point_guid FROM routepoints_link WHERE route_guid<>?1)",  // points exclusive to this route
          "DELETE FROM routepoints_link WHERE route_guid=?1",
          "DELETE FROM routes WHERE guid=?1" };
        ok = true;
        for (const char* s : stmts) {
          sqlite3_stmt* st = nullptr;
          if (sqlite3_prepare_v2(db, s, -1, &st, nullptr) == SQLITE_OK) {
            sqlite3_bind_text(st, 1, guid.c_str(), -1, SQLITE_TRANSIENT);
            if (sqlite3_step(st) != SQLITE_DONE) ok = false;
            sqlite3_finalize(st);
          } else ok = false;
        }
        sqlite3_close(db);
      }
    }
    std::printf("route: delete %s -> %s\n", guid.c_str(), ok ? "ok" : "failed");
    ws->send(std::string("{\"t\":\"route.ack\",\"ok\":") + (ok ? "true" : "false") + ",\"deleted\":\"" + json_escape(guid) + "\"}");
    return;
  }
}
static void conn_init() {
  if (const char* tok = std::getenv("HELM_OWNER_TOKEN")) if (*tok) g_owner_token = tok;
  conn_load();
  { std::lock_guard<std::mutex> lk(g_conns_mtx);
    if (g_conns.empty()) {                                    // first run: seed the legacy local relay (and a UI template)
      ConnConfig c; c.id = "local-nmea"; c.name = "Local NMEA (relay)"; c.type = "tcp-server";
      c.address = "127.0.0.1"; c.port = kNmeaPort; c.dataProtocol = "nmea0183"; c.enabled = true;
      c.comment = "socat/multiplexer relay target";
      g_conns[c.id] = c; conn_spawn_locked(c.id);
      std::printf("connections: seeded default Local NMEA relay tcp://127.0.0.1:%d\n", kNmeaPort);
    } }
  if (!g_owner_token.empty()) std::printf("connections: writes gated by HELM_OWNER_TOKEN\n");
}

static long g_seq = 0;
static std::set<ix::WebSocket*> g_seen;   // clients already given a snapshot baseline (nav thread only)

static void nav_loop(ix::HttpServer* server) {
  g_pRouteMan = new Routeman(RoutePropDlgCtx(), RoutemanDlgCtx());
  // Active route: a saved route from navobj.db (survives restart) wins; else HELM_ROUTE GPX; else the
  // built-in sample. Populates the shared ROUTE/g_route_name that route.create can swap live.
  { std::vector<WP> saved; std::string sname;
    if (load_latest_route_from_db(saved, sname)) {
      std::lock_guard<std::mutex> lk(g_route_mtx); ROUTE = saved; g_route_name = sname;
      std::printf("route source: navobj.db \"%s\" (%zu wp)\n", sname.c_str(), saved.size());
    } else {
      const char* rp = std::getenv("HELM_ROUTE"); std::string gpx;
      if (rp && *rp) { if (!read_file(rp, gpx)) { std::fprintf(stderr, "FATAL: cannot read GPX route '%s'\n", rp); std::exit(3); } std::printf("route source: %s\n", rp); }
      else { gpx = SAMPLE_GPX; std::printf("route source: built-in sample (no saved route; override: HELM_ROUTE=<route.gpx>)\n"); }
      std::vector<WP> g; std::string gn;
      if (!load_gpx_route(gpx, g, gn)) { std::fprintf(stderr, "FATAL: GPX route unusable (need <rte> with >=2 <rtept>)\n"); std::exit(4); }
      std::lock_guard<std::mutex> lk(g_route_mtx); ROUTE = g; g_route_name = gn;
    } }

  // Local working snapshot of the active route + its Route object, rebuilt whenever it's swapped.
  std::vector<WP> route; std::string rname; Route* r = nullptr;
  std::vector<double> legLen; double total = 0;
  double along = 0; size_t lastLeg = 0; long seenVer = -1;
  auto rebuild_route = [&]() {
    { std::lock_guard<std::mutex> lk(g_route_mtx); route = ROUTE; rname = g_route_name; }
    r = build_route(route, rname);   // prior r intentionally leaked (rare swap; deleting while Routeman-active is unsafe)
    gLat = route[0].lat; gLon = route[0].lon;
    g_pRouteMan->ActivateRoute(r); g_pRouteMan->ActivateNextPoint(r, false);
    legLen.clear(); total = 0; double b, d;
    for (size_t i = 0; i + 1 < route.size(); ++i) { bd(route[i + 1].lat, route[i + 1].lon, route[i].lat, route[i].lon, &b, &d); legLen.push_back(d); total += d; }
    along = 0; lastLeg = 0;
    std::printf("route activated: \"%s\" %zu waypoints; Routeman live (no GUI).\n", rname.c_str(), route.size());
  };

  for (long tick = 0;; ++tick) {
    long ver = g_route_version.load();
    if (ver != seenVer) { seenVer = ver; rebuild_route(); }
    double sim_sog = 5.6 + std::sin(tick / 9.0) * 0.9;
    along += sim_sog / 3600.0;
    if (along >= total) { along = 0; lastLeg = 0; g_pRouteMan->ActivateRoute(r); g_pRouteMan->ActivateNextPoint(r, false); }
    size_t li = 0; double acc = 0;
    while (li + 1 < legLen.size() && acc + legLen[li] < along) { acc += legLen[li]; ++li; }
    double f = legLen[li] ? (along - acc) / legLen[li] : 0;
    const WP& A = route[li]; const WP& B = route[li + 1];
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
      if (fresh(g_real.pos_t)) { gLat = g_real.lat; gLon = g_real.lon; src_pos = g_real.pos_src; } else { gLat = sim_lat; gLon = sim_lon; src_pos = "simulated"; }
      if (fresh(g_real.sog.t)) { sog = g_real.sog.v; src_sog = g_real.sog.src; } else { sog = sim_sog; src_sog = "simulated"; }
      if (fresh(g_real.cog.t)) { cog = (int)std::lround(g_real.cog.v); src_cog = g_real.cog.src; } else { cog = sim_cog; src_cog = "simulated"; }
      if (fresh(g_real.hdg.t)) { hdg = (int)std::lround(g_real.hdg.v); src_hdg = g_real.hdg.src; } else { hdg = sim_hdg; src_hdg = "simulated"; }
      if (fresh(g_real.depth.t)) { depth = g_real.depth.v; src_depth = g_real.depth.src; } else { depth = sim_depth; src_depth = "simulated"; }
      if (fresh(g_real.wspd.t)) { wspd = g_real.wspd.v; src_wind = g_real.wspd.src; } else { wspd = sim_wspd; src_wind = "simulated"; }
      wdir = fresh(g_real.wdir.t) ? (int)std::lround(g_real.wdir.v) : sim_wdir;
    }
    gCog = (double)cog; gSog = sog;   // own-ship course/speed -> OpenCPN's UpdateOneCPA (gLat/gLon set above)
    track_record(gLat, gLon, src_pos);  // ownship breadcrumb trail (auto; resets on source change so sim→real doesn't draw across the ocean)
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
    for (size_t k = li + 1; k < route.size() && k <= li + 2; ++k) {
      const WP& from = (k == li + 1) ? WP{gLat, gLon, ""} : route[k - 1];
      double lb, ld; bd(route[k].lat, route[k].lon, from.lat, from.lon, &lb, &ld);
      char lbuf[160];
      std::snprintf(lbuf, sizeof lbuf, "%s{\"name\":\"%s\",\"brg\":\"%ld\xC2\xB0\",\"active\":%s}",
                    k == li + 1 ? "" : ",", json_escape(route[k].name).c_str(), std::lround(lb), k == li + 1 ? "true" : "false");
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
      "\"active\":{\"name\":\"%s\",\"eta\":\"%s\",\"ttg\":\"%s\",\"vmg\":\"%.1f kn\","
      "\"dtg\":\"%s\",\"xte\":\"%d m\",\"legs\":%s,\"nextWp\":\"%s \xC2\xB7 %s\"}}",
      seq, ts, src_pos, src_pos, src_sog, src_cog, src_hdg, src_depth, src_wind,
      gLat, gLon, fmtPos(gLat, gLon).c_str(), sog, cog, hdg, depth,
      wspd, wdir, std::lround(wspd - 4), std::lround(wspd + 8),
      json_escape(g_route_name).c_str(),
      etabuf, ttg.c_str(), vmg, fmtNM(dtg).c_str(), (int)std::lround(xteNM * 1852),
      legs.c_str(), json_escape(nextShort).c_str(), fmtNM(dtw).c_str());

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
        fmtNM(dtg).c_str(), (int)std::lround(xteNM * 1852), etabuf, ttg.c_str(), vmg, json_escape(nextShort).c_str(), fmtNM(dtw).c_str());
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

    // AIS targets (OpenCPN-computed range/brg/CPA/TCPA) — spliced into the DYNAMIC frame strings
    // (not the fixed snprintf buffers) so a busy harbor can't truncate the nav frame.
    std::string aisArr = "[";
    { std::lock_guard<std::mutex> lk(g_ais_mtx);
      std::time_t aisNow = std::time(nullptr); bool first = true;
      for (auto it = g_ais_rows.begin(); it != g_ais_rows.end(); ) {
        AisRow& t = it->second; long age = (long)(aisNow - t.seen);
        if (age > 600) { it = g_ais_rows.erase(it); continue; }
        if ((t.lat == 0.0 && t.lon == 0.0) || t.lat < -90 || t.lat > 90) { ++it; continue; }  // no real position yet (static-only target) — don't emit a ghost at (0,0)
        char eta[16] = "";                            // MM-DD HH:MM when the voyage ETA is set
        if (t.etaMo >= 1 && t.etaMo <= 12 && t.etaDay >= 1 && t.etaDay <= 31)
          std::snprintf(eta, sizeof eta, "%02d-%02d %02d:%02d", t.etaMo, t.etaDay, t.etaHr, t.etaMin);
        char rotj[16] = "null";                       // AIS ROT units -> deg/min; -128/128 = not available
        if (t.rot != -128 && t.rot != 128) {
          double a = std::fabs((double)t.rot) / 4.733, dm = (t.rot < 0 ? -1.0 : 1.0) * a * a;
          if (dm > 720) dm = 720; if (dm < -720) dm = -720;
          std::snprintf(rotj, sizeof rotj, "%.0f", dm);
        }
        char tb[800];
        std::snprintf(tb, sizeof tb,
          "%s{\"mmsi\":%d,\"lat\":%.5f,\"lon\":%.5f,\"cog\":%.0f,\"sog\":%.1f,\"hdg\":%.0f,"
          "\"range\":%.2f,\"brg\":%.0f,\"cpa\":%.2f,\"tcpa\":%.1f,\"cpaValid\":%s,"
          "\"class\":%d,\"name\":\"%s\",\"ageSec\":%ld,"
          "\"navStatus\":%d,\"shipType\":%d,\"callsign\":\"%s\",\"destination\":\"%s\","
          "\"eta\":\"%s\",\"length\":%d,\"beam\":%d,\"draught\":%.1f,\"rot\":%s,\"imo\":%d}",
          first ? "" : ",", t.mmsi, t.lat, t.lon, t.cog, t.sog, t.hdg,
          t.range, t.brg, t.cpa, t.tcpa, t.cpaValid ? "true" : "false",
          t.cls, json_escape(t.name).c_str(), age,
          t.navStatus, t.shipType, json_escape(t.callsign).c_str(), json_escape(t.destination).c_str(),
          eta, t.length, t.beam, t.draft, rotj, t.imo);
        aisArr += tb; first = false; ++it;
      }
    }
    aisArr += "]";
    std::string connsArr = conn_status_array();   // live per-connection status, streamed to clients
    // Track (ownship breadcrumb): full trail into snapshots (new/reloaded clients get the whole line),
    // only the newly-added points into deltas (tiny). g_track_emitted advances once per tick.
    std::string trackFull = "[", trackAdd = "[";
    std::string armedJson = g_track_armed.load() ? "true" : "false";
    { std::lock_guard<std::mutex> lk(g_track_mtx);
      for (size_t i = 0; i < g_track.size(); ++i) { char tb[48]; std::snprintf(tb, sizeof tb, "%s[%.5f,%.5f]", i ? "," : "", g_track[i].lat, g_track[i].lon); trackFull += tb; }
      size_t from = std::min(g_track_emitted, g_track.size());
      for (size_t i = from; i < g_track.size(); ++i) { char tb[48]; std::snprintf(tb, sizeof tb, "%s[%.5f,%.5f]", (i == from) ? "" : ",", g_track[i].lat, g_track[i].lon); trackAdd += tb; }
      g_track_emitted = g_track.size();
    }
    trackFull += "]"; trackAdd += "]";
    // Active route geometry (full line + active-leg index) so the client redraws the line on change.
    // Routes are small (a handful of waypoints), so it rides every frame — coords are [lon,lat].
    std::string routeArr = "[";
    for (size_t i = 0; i < route.size(); ++i) { char rb[40]; std::snprintf(rb, sizeof rb, "%s[%.5f,%.5f]", i ? "," : "", route[i].lon, route[i].lat); routeArr += rb; }
    routeArr += "]";
    std::string routeJson = "{\"coords\":" + routeArr + ",\"activeLeg\":" + std::to_string((long)li) + ",\"name\":\"" + json_escape(rname) + "\"}";
    std::string snapOut(snap);
    if (!snapOut.empty()) {                                                // top-level, before final }
      snapOut.insert(snapOut.size() - 1, ",\"ais\":" + aisArr);
      snapOut.insert(snapOut.size() - 1, ",\"conns\":" + connsArr);
      snapOut.insert(snapOut.size() - 1, ",\"track\":" + trackFull + ",\"trackArmed\":" + armedJson);
      snapOut.insert(snapOut.size() - 1, ",\"route\":" + routeJson);
    }
    if (keyframe) frame = snapOut;
    else if (!frame.empty()) {
      frame.insert(frame.size() - 1, ",\"ais\":" + aisArr);
      frame.insert(frame.size() - 1, ",\"conns\":" + connsArr);
      frame.insert(frame.size() - 1, ",\"trackAdd\":" + trackAdd + ",\"trackArmed\":" + armedJson);
      frame.insert(frame.size() - 1, ",\"route\":" + routeJson);
    }

    auto clients = server->getClients();
    std::set<ix::WebSocket*> live;
    for (auto& c : clients) live.insert(c.get());
    for (auto& c : clients) c->send(g_seen.count(c.get()) ? frame : snapOut);
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
        if (auto ws = wptr.lock()) {
          std::weak_ptr<ix::WebSocket> wk = ws;                  // capture weak to avoid a ref cycle
          ws->setOnMessageCallback([wk](const ix::WebSocketMessagePtr& m) {
            if (m->type == ix::WebSocketMessageType::Message)    // command-plane: conn.list/upsert/delete
              if (auto s = wk.lock()) handle_command(m->str, s);
          });
        }
        std::printf("nav client connected: %s\n", cs->getId().c_str()); std::fflush(stdout);
      });

    // HTTP side: tiles, health, catalog, then the static UI.
    server->setOnConnectionCallback(
      [](ix::HttpRequestPtr req, std::shared_ptr<ix::ConnectionState>) -> ix::HttpResponsePtr {
        ix::WebSocketHttpHeaders h; h["Access-Control-Allow-Origin"] = "*";
        int z; long x, y;
        if (std::sscanf(req->uri.c_str(), "/chart/%d/%ld/%ld.png", &z, &x, &y) == 3) {
          const ColorScheme pal = palette_from_query(req->uri);   // CHART-8: ?p=day|dusk|night
          const DisCat cat = category_from_query(req->uri);       // CHART-9: ?cat=base|std|all|mariner
          char et[128]; std::snprintf(et, sizeof et, "\"%s.%s.%s.s%d\"", g_cell_name.c_str(), palette_name(pal), cat_name(cat), g_native_scale);
          const std::string etag(et);
          h["Cache-Control"] = "public, max-age=31536000, immutable"; h["ETag"] = etag;
          if (header_ci(req->headers, "If-None-Match") == etag)
            return std::make_shared<ix::HttpResponse>(304, "Not Modified", ix::HttpErrorCode::Ok, h, std::string());
          Job job; job.z = z; job.x = x; job.y = y; job.palette = pal; job.cat = cat;
          { std::lock_guard<std::mutex> lk(g_jobs_m); g_jobs.push_back(&job); }
          g_jobs_cv.notify_one();
          { std::unique_lock<std::mutex> lk(job.m); job.cv.wait(lk, [&]{ return job.done; }); }
          switch (job.status) {
            case TileStatus::Ok: h["Content-Type"] = "image/png";
              // CHART-9: overzoom warning — viewing finer than the cell's survey scale (SCAMIN hides detail).
              { double ds = display_scale(z, tile_lat(y + 0.5, z));
                if (g_native_scale > 0 && ds > 0 && (double)g_native_scale / ds >= 2.0) {
                  char oz[32]; std::snprintf(oz, sizeof oz, "%.1fx", (double)g_native_scale / ds);
                  h["X-Helm-Overzoom"] = oz; } }
              return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h, job.result);
            case TileStatus::NoCoverage: h["Content-Type"] = "image/png";
              return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h, g_blank);
            case TileStatus::BadRequest: h["Content-Type"] = "text/plain"; h["Cache-Control"] = "no-store"; h.erase("ETag");
              return std::make_shared<ix::HttpResponse>(400, "Bad Request", ix::HttpErrorCode::Ok, h, std::string("invalid tile coordinates\n"));
            default: h["Content-Type"] = "text/plain"; h["Cache-Control"] = "no-store"; h.erase("ETag");
              return std::make_shared<ix::HttpResponse>(500, "Render Failed", ix::HttpErrorCode::Ok, h, std::string("S-52 tile render failed; see server log\n"));
          }
        }
        if (req->uri.rfind("/query", 0) == 0) {   // CHART-10: GET /query?lat=&lon=[&z=][&radius=][&p=][&cat=] (worker thread: parse + marshal ONLY)
          const std::string& u = req->uri;
          auto getd = [&](const char* k, double& v) -> bool {   // key must follow '?' or '&' — no substring collisions
            const std::string key = k;
            for (size_t p = u.find(key); p != std::string::npos; p = u.find(key, p + 1))
              if (p > 0 && (u[p - 1] == '?' || u[p - 1] == '&'))
                return std::sscanf(u.c_str() + p + key.size(), "%lf", &v) == 1;
            return false;
          };
          double qlat, qlon, tmp;
          h["Cache-Control"] = "no-store";   // dynamic, unlike the immutable tiles
          if (!getd("lat=", qlat) || !getd("lon=", qlon)) { h["Content-Type"] = "text/plain";
            return std::make_shared<ix::HttpResponse>(400, "Bad Request", ix::HttpErrorCode::Ok, h, std::string("bad query params (need lat,lon)\n")); }
          Job job; job.kind = JobKind::Query; job.qlat = qlat; job.qlon = qlon;
          if (getd("z=", tmp)) job.z = (int)tmp;
          if (getd("radius=", tmp)) job.qradius_px = (int)tmp;
          job.palette = palette_from_query(u); job.cat = category_from_query(u);
          { std::lock_guard<std::mutex> lk(g_jobs_m); g_jobs.push_back(&job); }   // marshal onto the main thread, like /chart
          g_jobs_cv.notify_one();
          { std::unique_lock<std::mutex> lk(job.m); job.cv.wait(lk, [&]{ return job.done; }); }
          if (job.status == TileStatus::Ok) { h["Content-Type"] = "application/json";
            return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h, job.result); }
          h["Content-Type"] = "text/plain";
          return std::make_shared<ix::HttpResponse>(job.status == TileStatus::BadRequest ? 400 : 500,
            job.status == TileStatus::BadRequest ? "Bad Request" : "Query Failed", ix::HttpErrorCode::Ok, h,
            std::string(job.status == TileStatus::BadRequest ? "no chart loaded\n" : "S-57 query failed; see server log\n"));
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

    // --- AIS: stand up OpenCPN's real AisDecoder headless (decode + CPA/TCPA stay in its code) ---
    g_CPAMax_NM = 20.0; g_CPAWarn_NM = 2.0; g_TCPA_Max = 30.0;
    g_ShowMoored_Kts = 0.2; g_AISShowTracks_Mins = 20.0;
    g_bMarkLost = false; g_MarkLost_Mins = 10.0; g_bRemoveLost = false; g_RemoveLost_Mins = 20.0;
    g_bInlandEcdis = false; g_benableAISNameCache = false;
    bGPSValid = true; gCog = 0; gSog = 0;
    if (!g_BasePlatform) g_BasePlatform = new BasePlatform();   // Select reads GetSelectRadiusPix() from it
    pSelectAIS = new Select();
    g_ais = new AisDecoder(AisDecoderCallbacks());
    std::printf("AIS: OpenCPN AisDecoder live — !AIVDM from any connection feeds CPA/TCPA\n");
    if (const char* sk = std::getenv("HELM_SIGNALK")) if (*sk) sk_start(sk);   // opt-in SignalK overlay

    std::thread(nav_loop, server).detach();
    conn_init();   // load/seed persisted connections; each enabled one runs its own driver thread
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
    if (j->kind == JobKind::Query) j->status = run_query(j->qlat, j->qlon, j->z, j->qradius_px, j->palette, j->cat, j->result);
    else                           j->status = render_tile(j->z, j->x, j->y, j->palette, j->cat, j->result);
    { std::lock_guard<std::mutex> lk(j->m); j->done = true; } j->cv.notify_one();
  }
  wxEntryCleanup();
  return 0;
}
