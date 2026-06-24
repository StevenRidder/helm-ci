// helm_tiles.cpp — S-52 chart-tile HTTP server (Phase 2, second engine half).
//
// Loads a NOAA ENC headless via the PROVEN chart-render path (see chart_spike.cpp)
// and serves http://127.0.0.1:8082/chart/{z}/{x}/{y}.png — per-tile S-52 renders —
// for a MapLibre raster source. Real OpenCPN S-52 charts under the live nav.
//
// Reuses chart_spike's init + render verbatim; adds: ix::HttpServer, slippy-tile
// ViewPort math, PNG-to-memory. macOS note: wx bitmap/DC rendering runs on the
// MAIN thread (CoreGraphics), so HTTP worker threads hand each tile to the main
// thread via a job queue and wait for the PNG.

#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cstring>
#include <cctype>
#include <deque>
#include <mutex>
#include <condition_variable>
#include <string>
#include <thread>
#include <chrono>

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

#include "ixwebsocket/IXHttpServer.h"
#include "ixwebsocket/IXHttp.h"

extern s52plib* ps52plib;
extern wxString g_csv_locn;
extern wxString g_SENCPrefix;
extern wxString g_SData_Locn;
void EnsureHeadlessGlobals();

// GetpSharedDataLocation() is provided by the chart-render library (chart_stubs.cpp).

static const wxString kDataDir = wxT("/tmp/opencpn/data/");
static const wxString kS57Data = wxT("/tmp/opencpn/data/s57data/");
static const wxString kPLibRLE = wxT("/tmp/opencpn/data/s57data/S52RAZDS.RLE");
static const wxString kSencDir = wxT("/tmp/ocpn_senc/");

static s57chart* g_chart = nullptr;
static Extent    g_ext;
static std::string g_blank;          // transparent TS×TS PNG for no-coverage tiles
static std::string g_etag;           // immutable cache validator: cell + scheme + native scale
static const int TS = 256;           // tile size px

// case-insensitive header lookup (ixwebsocket preserves the sender's casing)
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

// ---- main-thread render job queue (CoreGraphics is main-thread) -------------
// Outcomes are kept DISTINCT (fail-and-fix-early): a render failure must NEVER
// be masked as an empty/transparent tile that the navigator reads as open water.
enum class TileStatus { Ok, NoCoverage, BadRequest, RenderFailed };
struct Job { int z; long x, y; std::string result;
             TileStatus status = TileStatus::RenderFailed;
             bool done = false; std::mutex m; std::condition_variable cv; };
static std::deque<Job*> g_jobs;
static std::mutex g_jobs_m;
static std::condition_variable g_jobs_cv;

// ---- slippy-tile (Web Mercator) helpers ------------------------------------
static double tile_lon(double x, int z) { return x / std::pow(2.0, z) * 360.0 - 180.0; }
static double tile_lat(double y, int z) {
  double n = M_PI * (1.0 - 2.0 * y / std::pow(2.0, z));
  return std::atan(std::sinh(n)) * 180.0 / M_PI;
}

// ---- render one tile (MAIN THREAD ONLY) -> status, PNG bytes in `out` --------
// Every failure path is surfaced with its stage; the caller turns RenderFailed
// into an HTTP 5xx + log, never a silent transparent tile.
static TileStatus render_tile(int z, long x, long y, std::string& out) {
  // boundary validation: reject malformed tile coordinates loudly
  if (z < 0 || z > 24 || x < 0 || y < 0 || x >= (1L << z) || y >= (1L << z)) {
    fprintf(stderr, "tile BAD REQUEST z%d/%ld/%ld (coords out of range)\n", z, x, y);
    return TileStatus::BadRequest;
  }
  double west = tile_lon(x, z), east = tile_lon(x + 1, z);
  double north = tile_lat(y, z), south = tile_lat(y + 1, z);
  // genuinely outside the chart cell -> legitimately empty (NOT a failure)
  if (east < g_ext.WLON || west > g_ext.ELON || north < g_ext.SLAT || south > g_ext.NLAT)
    return TileStatus::NoCoverage;

  double clat = (north + south) / 2.0, clon = (west + east) / 2.0;
  double span_m = (north - south) * 1852.0 * 60.0;
  if (span_m <= 0) {
    fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: non-positive latitude span\n", z, x, y);
    return TileStatus::RenderFailed;
  }
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
  if (!bmp.IsOk()) {
    fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: wxBitmap(%dx%d,%d) not ok\n", z, x, y, TS, TS, BPP);
    return TileStatus::RenderFailed;
  }
  wxMemoryDC dc(bmp);
  if (!dc.IsOk()) {
    fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: wxMemoryDC not ok\n", z, x, y);
    return TileStatus::RenderFailed;
  }
  OCPNRegion region(0, 0, TS, TS);
  bool ok = g_chart->RenderRegionViewOnDC(dc, vp, region);
  // single-cell render ends with pDIB->SelectIntoDC(dc): grab the selected bitmap
  wxBitmap rendered = dc.GetSelectedBitmap();
  dc.SelectObject(wxNullBitmap);
  if (!ok || !rendered.IsOk()) {
    fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: RenderRegionViewOnDC=%d bitmapOk=%d\n",
            z, x, y, ok, rendered.IsOk());
    return TileStatus::RenderFailed;
  }
  wxImage img = rendered.ConvertToImage();
  if (!img.IsOk()) {
    fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: ConvertToImage\n", z, x, y);
    return TileStatus::RenderFailed;
  }
  wxMemoryOutputStream mos;
  if (!img.SaveFile(mos, wxBITMAP_TYPE_PNG)) {
    fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: PNG encode\n", z, x, y);
    return TileStatus::RenderFailed;
  }
  out.resize(mos.GetSize());
  mos.CopyTo(&out[0], out.size());
  return TileStatus::Ok;
}

static std::string make_blank() {
  wxImage blank(TS, TS);
  blank.SetAlpha();
  std::memset(blank.GetAlpha(), 0, (size_t)TS * TS);   // fully transparent
  wxMemoryOutputStream mos;
  blank.SaveFile(mos, wxBITMAP_TYPE_PNG);
  std::string out; out.resize(mos.GetSize());
  mos.CopyTo(&out[0], out.size());
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

  // FAIL CLOSED on an invalid native scale: scale <= 1 means SCAMIN / safety-
  // contour filtering would be wrong (SENC missing DSPM:CSCL). Refuse to serve a
  // chart whose safety features we cannot trust, rather than render it silently.
  int ns = g_chart->GetNativeScale();
  if (ns <= 1) {
    printf("FATAL: chart native scale invalid (%d) -- SCAMIN/safety-contour "
           "selection would be wrong; refusing to serve this cell.\n", ns);
    return false;
  }

  g_blank = make_blank();
  if (g_blank.empty()) { printf("FATAL: transparent no-coverage tile generation failed\n"); return false; }

  // Immutable cache validator. A tile is fully determined by (cell + edition + color
  // scheme + native scale), none of which change over this server's lifetime, so tiles
  // are safely immutable. (Product target per docs/STREAMING-API.md §2.1: carry this
  // token as a URL version segment so multi-cell/edition caches never collide.)
  wxString cell = wxFileName(enc_path).GetName();   // e.g. US5FL96M
  char etag[96];
  std::snprintf(etag, sizeof etag, "\"%s.day.s%d\"", (const char*)cell.ToUTF8(), ns);
  g_etag = etag;

  printf("ENC loaded: S %.4f N %.4f W %.4f E %.4f  nativeScale=%d  blankPNG=%zuB\n",
         g_ext.SLAT, g_ext.NLAT, g_ext.WLON, g_ext.ELON, ns, g_blank.size());
  return true;
}

// ---- one-time render-path warmup (MAIN THREAD ONLY) -------------------------
// A one-time lazy init somewhere in the S-52 render path (s52plib / font / DC /
// GL state on the first RenderRegionViewOnDC) makes the VERY FIRST tile a fresh
// process renders differ byte-wise from steady state; it then converges to
// identical, deterministic output on re-request. Chart CONTENT is correct either
// way -- this is sub-pixel/encoding settling, not a data bug -- but for a nav
// tool every served tile must be the deterministic warm output. So we render one
// throwaway tile here, after the chart is loaded and BEFORE the server accepts
// connections, and discard it. The first SERVED tile is then always steady state.
//
// We target the center of the chart extent (always in-coverage, so it exercises
// the full RenderRegionViewOnDC path rather than the NoCoverage early-return),
// computed from g_ext so this self-adapts to whatever ENC was loaded.
static void warmup_render() {
  double clat = (g_ext.SLAT + g_ext.NLAT) / 2.0;
  double clon = (g_ext.WLON + g_ext.ELON) / 2.0;
  const int z = 13;
  const double n = std::pow(2.0, z);
  long x = (long)((clon + 180.0) / 360.0 * n);
  double lat_rad = clat * M_PI / 180.0;
  long y = (long)((1.0 - std::log(std::tan(lat_rad) + 1.0 / std::cos(lat_rad)) / M_PI) / 2.0 * n);

  std::string scratch;
  TileStatus st = render_tile(z, x, y, scratch);
  // The lazy init is tripped by RenderRegionViewOnDC running at all, regardless of
  // the encoded result, so any status leaves us warm. Log it for transparency; a
  // hard RenderFailed at the extent center would also mean real requests fail, but
  // that path is already surfaced as a 500 per-request -- don't mask it here.
  printf("warmup render z%d/%ld/%ld -> status=%d (%zuB, discarded); first served "
         "tile is now steady-state\n", z, x, y, (int)st, scratch.size());
}

class TileApp : public wxApp {
public:
  ix::HttpServer* server = nullptr;
  bool OnInit() override {
    SetAppName(wxT("opencpn"));
    wxString enc = (argc >= 2) ? wxString(argv[1]) : wxString(wxT("/tmp/ENC_ROOT/US5FL96M/US5FL96M.000"));
    if (!init_chart(enc)) return false;

    // Settle the first-render lazy init BEFORE we accept connections, so the first
    // SERVED tile is deterministic steady-state output (see warmup_render).
    if (!getenv("HELM_TILES_NO_WARMUP")) warmup_render();   // TEMP control toggle

    // Bind configurable so the SAME server feeds localhost (dev) or the boat LAN (iPad/
    // iPhone): HELM_BIND (default 127.0.0.1; 0.0.0.0 to expose) + HELM_TILE_PORT.
    const char* bindHost = std::getenv("HELM_BIND");
    if (!bindHost || !*bindHost) bindHost = "127.0.0.1";
    int tilePort = 8082;
    if (const char* p = std::getenv("HELM_TILE_PORT")) {   // invalid input fails loud — never silently default
      char* end = nullptr; long v = std::strtol(p, &end, 10);
      if (end == p || *end != '\0' || v < 1 || v > 65535) {
        printf("FATAL: HELM_TILE_PORT=\"%s\" is not a valid port (1-65535); refusing to fall back to a default.\n", p);
        return false;
      }
      tilePort = (int)v;
    }

    server = new ix::HttpServer(tilePort, bindHost);
    server->setOnConnectionCallback(
      [](ix::HttpRequestPtr req, std::shared_ptr<ix::ConnectionState>) -> ix::HttpResponsePtr {
        ix::WebSocketHttpHeaders h;
        h["Access-Control-Allow-Origin"] = "*";
        int z; long x, y;
        if (std::sscanf(req->uri.c_str(), "/chart/%d/%ld/%ld.png", &z, &x, &y) == 3) {
          // S-52 tiles are immutable for this cell/scheme — cache hard (huge win when a Pi
          // feeds several iPads) and honor revalidation cheaply without re-rendering.
          h["Cache-Control"] = "public, max-age=31536000, immutable";
          h["ETag"] = g_etag;
          if (header_ci(req->headers, "If-None-Match") == g_etag)
            return std::make_shared<ix::HttpResponse>(304, "Not Modified", ix::HttpErrorCode::Ok, h, std::string());
          // hand the render to the main thread (CoreGraphics) and wait
          Job job; job.z = z; job.x = x; job.y = y;
          { std::lock_guard<std::mutex> lk(g_jobs_m); g_jobs.push_back(&job); }
          g_jobs_cv.notify_one();
          { std::unique_lock<std::mutex> lk(job.m); job.cv.wait(lk, [&]{ return job.done; }); }
          switch (job.status) {
            case TileStatus::Ok:
              h["Content-Type"] = "image/png";
              return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h, job.result);
            case TileStatus::NoCoverage:           // legitimately no chart here -> transparent
              h["Content-Type"] = "image/png";
              return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h, g_blank);
            case TileStatus::BadRequest:
              h["Content-Type"] = "text/plain";
              h["Cache-Control"] = "no-store"; h.erase("ETag");   // never cache an error as if it were the tile
              return std::make_shared<ix::HttpResponse>(400, "Bad Request", ix::HttpErrorCode::Ok, h,
                std::string("invalid tile coordinates\n"));
            case TileStatus::RenderFailed:
            default:                               // surface it; do NOT mask a broken render as open water
              h["Content-Type"] = "text/plain";
              h["Cache-Control"] = "no-store"; h.erase("ETag");   // a 500 must not be cached forever
              return std::make_shared<ix::HttpResponse>(500, "Render Failed", ix::HttpErrorCode::Ok, h,
                std::string("S-52 tile render failed; see server log\n"));
          }
        }
        if (req->uri == "/" || req->uri == "/health") {
          h["Content-Type"] = "text/plain";
          return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h,
            std::string("helm-tiles: S-52 ENC tile server. GET /chart/{z}/{x}/{y}.png\n"));
        }
        return std::make_shared<ix::HttpResponse>(404, "Not Found", ix::HttpErrorCode::Ok, h, std::string());
      });
    if (!server->listenAndStart()) { printf("HTTP listen on %s:%d FAILED\n", bindHost, tilePort); return false; }
    printf("S-52 tile server: http://%s:%d/chart/{z}/{x}/{y}.png  (immutable, ETag %s)\n", bindHost, tilePort, g_etag.c_str());
    if (std::strcmp(bindHost, "127.0.0.1") != 0)
      printf("  serving the LAN — an iPad/iPhone on the same WiFi can load charts from http://<this-host>:%d/\n", tilePort);
    return false;  // no wx event loop; main() runs the render job loop
  }
};
wxIMPLEMENT_APP_NO_MAIN(TileApp);

int main(int argc, char** argv) {
  wxEntryStart(argc, argv);
  wxTheApp->CallOnInit();
  TileApp* app = static_cast<TileApp*>(wxTheApp);
  if (!app->server) { printf("startup failed\n"); wxEntryCleanup(); return 1; }

  // main-thread render loop: pull jobs queued by HTTP worker threads, render, signal.
  for (;;) {
    Job* j = nullptr;
    { std::unique_lock<std::mutex> lk(g_jobs_m);
      g_jobs_cv.wait(lk, [] { return !g_jobs.empty(); });
      j = g_jobs.front(); g_jobs.pop_front(); }
    j->status = render_tile(j->z, j->x, j->y, j->result);
    { std::lock_guard<std::mutex> lk(j->m); j->done = true; }
    j->cv.notify_one();
  }
  wxEntryCleanup();
  return 0;
}
