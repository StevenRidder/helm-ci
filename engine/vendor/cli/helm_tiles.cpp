// helm_tiles.cpp — S-52 chart-tile HTTP server (Phase 2, second engine half).
//
// Loads a whole FOLDER of NOAA ENC cells headless via the PROVEN chart-render path
// (see chart_spike.cpp) and serves http://127.0.0.1:8082/chart/{z}/{x}/{y}.png — per-tile
// S-52 renders — for a MapLibre raster source. Multi-cell: for each tile it picks the
// zoom-appropriate covering cell (the tile-layer analogue of OpenCPN's quilt reference-chart
// selection, without the GUI/viewport coupling). Real OpenCPN S-52 charts under the live nav.
//
// Reuses chart_spike's init + render verbatim; adds: ix::HttpServer, slippy-tile
// ViewPort math, PNG-to-memory. macOS note: wx bitmap/DC rendering runs on the
// MAIN thread (CoreGraphics), so HTTP worker threads hand each tile to the main
// thread via a job queue and wait for the PNG.

#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cstring>
#include <deque>
#include <mutex>
#include <condition_variable>
#include <string>
#include <vector>
#include <algorithm>
#include <thread>
#include <chrono>

#include <wx/app.h>
#include <wx/bitmap.h>
#include <wx/dcmemory.h>
#include <wx/dir.h>
#include <wx/filefn.h>
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

// One loaded ENC cell. The tiler is multi-cell: it loads a whole folder of cells (a region's
// worth, across usage bands / scales) and picks the best one per tile by zoom — the tile-layer
// analogue of OpenCPN's quilt reference-chart selection, minus the GUI/viewport coupling.
struct Cell { s57chart* chart; Extent ext; int scale; std::string path; };
static std::vector<Cell> g_cells;    // all loaded cells, sorted most-detailed (smallest scale) first
static std::string g_blank;          // transparent TS×TS PNG for no-coverage tiles
static const int TS = 256;           // tile size px

// Immutable-cache stamp for ETags (CHART-14). A tile's bytes are a pure function of the loaded
// cell set + scale selection + palette, so we fold those into one stable hash at startup; the
// per-tile ETag is then "<stamp>.<z>.<x>.<y>". Same granularity as helm-server's cell.palette.scale
// ETag, but per-tile-unique — so a 304 revalidation is correct AND can skip the S-52 render.
static std::string g_charts_version;

// S-52 no-data (NODTA) colour, captured from the active colour table at init. Pixels matching it
// are made transparent so cells composite over each other AND over satellite (depth-on-satellite).
static unsigned char g_nodtaR = 0, g_nodtaG = 0, g_nodtaB = 0;
static bool g_nodtaOk = false;

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

// ---- per-tile cell selection (the quilt's reference-chart pick) -------------
// Web-Mercator scale denominator at this zoom (OGC 0.28 mm/px, 256-px tiles). This is the
// "paper scale" the tile is shown at, so we can pick the cell whose native scale matches.
static double zoom_scale(int z, double lat) {
  return 559082264.029 * std::cos(lat * M_PI / 180.0) / std::pow(2.0, z);
}
static bool extent_hits(const Extent& e, double w, double s, double ee, double n) {
  return !(ee < e.WLON || w > e.ELON || n < e.SLAT || s > e.NLAT);
}
static const double SCALE_WIN = 3.0;   // composite cells within 3× of the tile's display scale
static const size_t MAX_LAYERS = 4;    // …and at most this many per tile (the finest kept)

// Rank the cells to composite for a tile: those covering it whose native scale is within SCALE_WIN
// of the zoom's display scale (so we never draw a harbour chart at ocean zoom or vice-versa),
// sorted COARSEST-first so finer cells draw on top. Falls back to the single nearest-scale covering
// cell so we never blank water some chart covers. `out` left empty => no coverage.
static void rank_cells(double w, double s, double e, double n, int z, std::vector<Cell*>& out) {
  out.clear();
  const double ideal = zoom_scale(z, (n + s) / 2.0);
  std::vector<Cell*> cov;
  for (auto& c : g_cells) if (extent_hits(c.ext, w, s, e, n)) cov.push_back(&c);
  if (cov.empty()) return;
  for (Cell* c : cov) { double r = c->scale / ideal; if (r < 1.0) r = 1.0 / r; if (r <= SCALE_WIN) out.push_back(c); }
  if (out.empty()) {                                   // nothing in-band: keep the single nearest
    Cell* best = nullptr; double err = 1e18;
    for (Cell* c : cov) { double er = std::fabs(std::log((double)c->scale) - std::log(ideal)); if (er < err) { err = er; best = c; } }
    out.push_back(best);
  }
  std::sort(out.begin(), out.end(), [](Cell* a, Cell* b) { return a->scale > b->scale; });   // coarse -> fine
  if (out.size() > MAX_LAYERS) out.erase(out.begin(), out.end() - MAX_LAYERS);                // keep finest
}

// Render one cell into a TS×TS image for `base`'s viewport, with NODTA (no-data) made transparent
// so cells composite cleanly over each other and over satellite. Returns false on render failure.
static bool render_cell_to_image(Cell* cell, const ViewPort& base, wxImage& out) {
  ViewPort vp = base;
  vp.chart_scale = cell->chart->GetNativeScale();      // per-cell scale -> correct SCAMIN/safety pick
  vp.ref_scale = vp.chart_scale;
  vp.SetBoxes(); vp.Validate();

  wxBitmap bmp(TS, TS, BPP);
  if (!bmp.IsOk()) return false;
  wxMemoryDC dc(bmp);
  if (!dc.IsOk()) return false;
  OCPNRegion region(0, 0, TS, TS);
  bool ok = cell->chart->RenderRegionViewOnDC(dc, vp, region);
  wxBitmap rendered = dc.GetSelectedBitmap();          // single-cell render ends with SelectIntoDC
  dc.SelectObject(wxNullBitmap);
  if (!ok || !rendered.IsOk()) return false;
  out = rendered.ConvertToImage();
  if (!out.IsOk()) return false;

  if (!out.HasAlpha()) out.InitAlpha();
  unsigned char* a = out.GetAlpha();
  const unsigned char* d = out.GetData();
  const int N = TS * TS;
  if (g_nodtaOk && a && d)
    for (int i = 0; i < N; ++i)
      a[i] = (d[3 * i] == g_nodtaR && d[3 * i + 1] == g_nodtaG && d[3 * i + 2] == g_nodtaB) ? 0 : 255;
  else if (a)
    for (int i = 0; i < N; ++i) a[i] = 255;            // NODTA unknown -> stay opaque (old behaviour)
  return true;
}

// Composite `top` over `acc` (both TS×TS, alpha 0/255): where top is opaque, it wins.
static void composite_over(wxImage& acc, const wxImage& top) {
  unsigned char* ad = acc.GetData(); unsigned char* aa = acc.GetAlpha();
  const unsigned char* td = top.GetData(); const unsigned char* ta = top.GetAlpha();
  if (!ad || !aa || !td || !ta) return;
  const int N = TS * TS;
  for (int i = 0; i < N; ++i)
    if (ta[i]) { ad[3 * i] = td[3 * i]; ad[3 * i + 1] = td[3 * i + 1]; ad[3 * i + 2] = td[3 * i + 2]; aa[i] = 255; }
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
  // rank the zoom-appropriate cells covering this tile; none -> legitimately empty (NOT a failure)
  std::vector<Cell*> layers;
  rank_cells(west, south, east, north, z, layers);
  if (layers.empty()) return TileStatus::NoCoverage;

  double clat = (north + south) / 2.0, clon = (west + east) / 2.0;
  double span_m = (north - south) * 1852.0 * 60.0;
  if (span_m <= 0) {
    fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: non-positive latitude span\n", z, x, y);
    return TileStatus::RenderFailed;
  }
  double ppm = (double)TS / span_m;

  ViewPort base;
  base.clat = clat; base.clon = clon; base.view_scale_ppm = ppm;
  base.pix_width = TS; base.pix_height = TS;
  base.rotation = 0; base.skew = 0; base.tilt = 0;
  base.m_projection_type = PROJECTION_MERCATOR;
  base.chart_scale = layers.back()->chart->GetNativeScale();   // nominal; each cell overrides per-render
  base.ref_scale = base.chart_scale;
  base.b_quilt = false;
  base.rv_rect = wxRect(0, 0, TS, TS);
  base.SetBoxes(); base.Validate();

  // Composite coarse -> fine, NODTA transparent: finer cells land on top within their coverage,
  // coarser fills the rest. One tile, fully quilted across cells, no seams, no holes.
  wxImage acc; bool any = false; int failed = 0;
  for (Cell* c : layers) {
    wxImage img;
    if (!render_cell_to_image(c, base, img)) { ++failed; continue; }
    if (!any) { acc = img; any = true; }
    else composite_over(acc, img);
  }
  if (!any) {
    fprintf(stderr, "tile RENDER FAIL z%d/%ld/%ld: all %zu layer(s) failed\n", z, x, y, layers.size());
    return TileStatus::RenderFailed;
  }
  if (failed)
    fprintf(stderr, "tile z%d/%ld/%ld: %d of %zu layer(s) failed; served the rest\n", z, x, y, failed, layers.size());

  wxMemoryOutputStream mos;
  if (!acc.SaveFile(mos, wxBITMAP_TYPE_PNG)) {
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

// Load one ENC cell into g_cells. Returns false (and skips, never aborts) for an unusable cell:
// a region folder will contain cells of varying quality and we keep serving the good ones.
static bool load_one_cell(const wxString& path) {
  const char* p = (const char*)path.ToUTF8();
  s57chart* ch = new s57chart();
  ch->DisableBackgroundSENC();
  if (ch->Init(path, FULL_INIT) != INIT_OK) { fprintf(stderr, "  skip (Init failed): %s\n", p); delete ch; return false; }
  ch->SetColorScheme(GLOBAL_COLOR_SCHEME_DAY);
  Extent ext;
  if (!ch->GetChartExtent(&ext)) { fprintf(stderr, "  skip (no extent): %s\n", p); delete ch; return false; }
  // FAIL CLOSED per cell on an invalid native scale: scale <= 1 means SCAMIN / safety-contour
  // selection would be wrong (SENC missing DSPM:CSCL). Skip it rather than serve it silently.
  int ns = ch->GetNativeScale();
  if (ns <= 1) { fprintf(stderr, "  skip (bad native scale %d): %s\n", ns, p); delete ch; return false; }
  g_cells.push_back({ ch, ext, ns, std::string(p) });
  return true;
}

// Load every ENC cell under `root` (a folder of *.000, recursively) — or a single *.000 file.
static bool init_charts(const wxString& root) {
  setvbuf(stdout, nullptr, _IONBF, 0);
  wxImage::AddHandler(new wxPNGHandler);
  EnsureHeadlessGlobals();
  ::wxFileName::Mkdir(kSencDir, 0755, wxPATH_MKDIR_FULL);
  g_SENCPrefix = kSencDir; g_csv_locn = kS57Data; g_SData_Locn = kDataDir;

  ps52plib = new s52plib(kPLibRLE, false);
  if (!ps52plib || !ps52plib->m_bOK) { printf("s52plib load FAILED\n"); return false; }
  ps52plib->SetPLIBColorScheme(GLOBAL_COLOR_SCHEME_DAY, ChartCtx(false, 0));

  // Capture the no-data colour so render_cell_to_image can key it to transparent.
  if (S52color* nd = ps52plib->getColor("NODTA")) {
    g_nodtaR = nd->R; g_nodtaG = nd->G; g_nodtaB = nd->B; g_nodtaOk = true;
    printf("NODTA no-data colour = rgb(%d,%d,%d) -> transparent (composite over satellite)\n",
           g_nodtaR, g_nodtaG, g_nodtaB);
  } else {
    printf("WARN: NODTA colour unavailable; no-data areas will stay opaque grey\n");
  }

  m_pRegistrarMan = new s57RegistrarMgr(kS57Data, stderr);

  wxArrayString files;
  if (wxDirExists(root))        wxDir::GetAllFiles(root, &files, wxT("*.000"), wxDIR_FILES | wxDIR_DIRS);
  else if (wxFileExists(root))  files.Add(root);
  if (files.IsEmpty()) { printf("FATAL: no ENC (*.000) cells under '%s'\n", (const char*)root.ToUTF8()); return false; }

  printf("scanning %zu ENC file(s) under '%s' …\n", (size_t)files.GetCount(), (const char*)root.ToUTF8());
  for (size_t i = 0; i < files.GetCount(); ++i) load_one_cell(files[i]);
  if (g_cells.empty()) { printf("FATAL: no usable ENC cells loaded\n"); return false; }

  // most-detailed (smallest native scale) first — tidy, and a deterministic tie-break base
  std::sort(g_cells.begin(), g_cells.end(), [](const Cell& a, const Cell& b) { return a.scale < b.scale; });

  g_blank = make_blank();
  if (g_blank.empty()) { printf("FATAL: transparent no-coverage tile generation failed\n"); return false; }

  printf("loaded %zu ENC cell(s); native scales 1:%d (finest) .. 1:%d (coarsest)\n",
         g_cells.size(), g_cells.front().scale, g_cells.back().scale);
  return true;
}

// Fold the loaded cell set (path + native scale) and palette into a stable 64-bit stamp (FNV-1a).
// Changes iff the chart inputs that determine a tile's bytes change, so it's a sound immutable-cache key.
static std::string charts_version_stamp() {
  unsigned long long hsh = 1469598103934665603ULL;            // FNV-1a 64-bit offset basis
  auto fold = [&](const std::string& s) {
    for (unsigned char c : s) { hsh ^= c; hsh *= 1099511628211ULL; }
  };
  fold("day|");                                               // palette (helm-tiles renders Day)
  for (const Cell& c : g_cells) { fold(c.path); fold("@"); fold(std::to_string(c.scale)); fold(";"); }
  char buf[17]; std::snprintf(buf, sizeof buf, "%016llx", hsh);
  return std::string(buf);
}

class TileApp : public wxApp {
public:
  ix::HttpServer* server = nullptr;
  bool OnInit() override {
    SetAppName(wxT("opencpn"));
    // arg or $HELM_ENC_ROOT: a folder of ENC cells (multi-cell quilt) or a single .000 file.
    wxString root;
    if (argc >= 2) root = wxString(argv[1]);
    else if (const wxChar* env = wxGetenv(wxT("HELM_ENC_ROOT"))) root = wxString(env);
    else root = wxString(wxT("/tmp/ENC_ROOT"));
    if (!init_charts(root)) return false;
    g_charts_version = charts_version_stamp();   // CHART-14: stamp the loaded chart set for immutable ETags

    server = new ix::HttpServer(8082, "127.0.0.1");
    server->setOnConnectionCallback(
      [](ix::HttpRequestPtr req, std::shared_ptr<ix::ConnectionState>) -> ix::HttpResponsePtr {
        ix::WebSocketHttpHeaders h;
        h["Access-Control-Allow-Origin"] = "*";
        h["Cache-Control"] = "no-cache";          // default for /, /health, 404, and error bodies
        int z; long x, y;
        if (std::sscanf(req->uri.c_str(), "/chart/%d/%ld/%ld.png", &z, &x, &y) == 3) {
          // Immutable per-tile ETag (CHART-14): a tile's bytes don't change unless g_charts_version
          // does, so a matching revalidation gets 304 WITHOUT rendering, and the browser may cache for
          // a year. Mirrors helm-server's immutable ETag+304 (which standalone helm-tiles lacked).
          char et[80]; std::snprintf(et, sizeof et, "\"%s.%d.%ld.%ld\"", g_charts_version.c_str(), z, x, y);
          const std::string etag(et);
          const auto inm = req->headers.find("If-None-Match");   // ix headers compare case-insensitively
          if (inm != req->headers.end() && inm->second == etag) {
            h["Cache-Control"] = "public, max-age=31536000, immutable"; h["ETag"] = etag;
            return std::make_shared<ix::HttpResponse>(304, "Not Modified", ix::HttpErrorCode::Ok, h, std::string());
          }
          // hand the render to the main thread (CoreGraphics) and wait
          Job job; job.z = z; job.x = x; job.y = y;
          { std::lock_guard<std::mutex> lk(g_jobs_m); g_jobs.push_back(&job); }
          g_jobs_cv.notify_one();
          { std::unique_lock<std::mutex> lk(job.m); job.cv.wait(lk, [&]{ return job.done; }); }
          switch (job.status) {
            case TileStatus::Ok:
              h["Content-Type"] = "image/png";
              h["Cache-Control"] = "public, max-age=31536000, immutable"; h["ETag"] = etag;
              return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h, job.result);
            case TileStatus::NoCoverage:           // legitimately no chart here -> transparent (still immutable)
              h["Content-Type"] = "image/png";
              h["Cache-Control"] = "public, max-age=31536000, immutable"; h["ETag"] = etag;
              return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h, g_blank);
            case TileStatus::BadRequest:
              h["Content-Type"] = "text/plain"; h["Cache-Control"] = "no-store";   // never cache an error
              return std::make_shared<ix::HttpResponse>(400, "Bad Request", ix::HttpErrorCode::Ok, h,
                std::string("invalid tile coordinates\n"));
            case TileStatus::RenderFailed:
            default:                               // surface it; do NOT mask a broken render as open water
              h["Content-Type"] = "text/plain"; h["Cache-Control"] = "no-store";
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
    if (!server->listenAndStart()) { printf("HTTP listen on 8082 FAILED\n"); return false; }
    printf("S-52 tile server: http://127.0.0.1:8082/chart/{z}/{x}/{y}.png  (%zu cells, zoom-quilted)\n",
           g_cells.size());
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
