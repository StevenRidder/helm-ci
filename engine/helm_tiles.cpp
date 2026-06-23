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

static wxString s_shared_data = wxT("/tmp/opencpn/data/");
extern "C" wxString* GetpSharedDataLocation() { return &s_shared_data; }

static const wxString kDataDir = wxT("/tmp/opencpn/data/");
static const wxString kS57Data = wxT("/tmp/opencpn/data/s57data/");
static const wxString kPLibRLE = wxT("/tmp/opencpn/data/s57data/S52RAZDS.RLE");
static const wxString kSencDir = wxT("/tmp/ocpn_senc/");

static s57chart* g_chart = nullptr;
static Extent    g_ext;
static std::string g_blank;          // transparent TS×TS PNG for no-coverage tiles
static const int TS = 256;           // tile size px

// ---- main-thread render job queue (CoreGraphics is main-thread) -------------
struct Job { int z; long x, y; std::string result; bool done = false;
             std::mutex m; std::condition_variable cv; };
static std::deque<Job*> g_jobs;
static std::mutex g_jobs_m;
static std::condition_variable g_jobs_cv;

// ---- slippy-tile (Web Mercator) helpers ------------------------------------
static double tile_lon(double x, int z) { return x / std::pow(2.0, z) * 360.0 - 180.0; }
static double tile_lat(double y, int z) {
  double n = M_PI * (1.0 - 2.0 * y / std::pow(2.0, z));
  return std::atan(std::sinh(n)) * 180.0 / M_PI;
}

// ---- render one tile -> PNG bytes (MAIN THREAD ONLY). "" => fail ------------
static std::string render_tile(int z, long x, long y) {
  double west = tile_lon(x, z), east = tile_lon(x + 1, z);
  double north = tile_lat(y, z), south = tile_lat(y + 1, z);
  // cull tiles that don't touch the cell -> caller serves a transparent tile
  if (east < g_ext.WLON || west > g_ext.ELON || north < g_ext.SLAT || south > g_ext.NLAT)
    return std::string();
  double clat = (north + south) / 2.0, clon = (west + east) / 2.0;
  double span_m = (north - south) * 1852.0 * 60.0;
  if (span_m <= 0) return std::string();
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
  if (!bmp.IsOk()) return std::string();
  wxMemoryDC dc(bmp);
  if (!dc.IsOk()) return std::string();
  OCPNRegion region(0, 0, TS, TS);
  bool ok = g_chart->RenderRegionViewOnDC(dc, vp, region);
  // single-cell render ends with pDIB->SelectIntoDC(dc): grab the selected bitmap
  wxBitmap rendered = dc.GetSelectedBitmap();
  dc.SelectObject(wxNullBitmap);
  if (!ok || !rendered.IsOk()) return std::string();
  wxImage img = rendered.ConvertToImage();
  if (!img.IsOk()) return std::string();
  wxMemoryOutputStream mos;
  if (!img.SaveFile(mos, wxBITMAP_TYPE_PNG)) return std::string();
  std::string out; out.resize(mos.GetSize());
  mos.CopyTo(&out[0], out.size());
  return out;
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
  g_blank = make_blank();
  printf("ENC loaded: S %.4f N %.4f W %.4f E %.4f  nativeScale=%d  blankPNG=%zuB\n",
         g_ext.SLAT, g_ext.NLAT, g_ext.WLON, g_ext.ELON, g_chart->GetNativeScale(), g_blank.size());
  return true;
}

class TileApp : public wxApp {
public:
  ix::HttpServer* server = nullptr;
  bool OnInit() override {
    SetAppName(wxT("opencpn"));
    wxString enc = (argc >= 2) ? wxString(argv[1]) : wxString(wxT("/tmp/ENC_ROOT/US5FL96M/US5FL96M.000"));
    if (!init_chart(enc)) return false;

    server = new ix::HttpServer(8082, "127.0.0.1");
    server->setOnConnectionCallback(
      [](ix::HttpRequestPtr req, std::shared_ptr<ix::ConnectionState>) -> ix::HttpResponsePtr {
        ix::WebSocketHttpHeaders h;
        h["Access-Control-Allow-Origin"] = "*";
        h["Cache-Control"] = "no-cache";
        int z; long x, y;
        if (std::sscanf(req->uri.c_str(), "/chart/%d/%ld/%ld.png", &z, &x, &y) == 3) {
          // hand the render to the main thread (CoreGraphics) and wait
          Job job; job.z = z; job.x = x; job.y = y;
          { std::lock_guard<std::mutex> lk(g_jobs_m); g_jobs.push_back(&job); }
          g_jobs_cv.notify_one();
          { std::unique_lock<std::mutex> lk(job.m); job.cv.wait(lk, [&]{ return job.done; }); }
          h["Content-Type"] = "image/png";
          const std::string& body = job.result.empty() ? g_blank : job.result;
          return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h, body);
        }
        if (req->uri == "/" || req->uri == "/health") {
          h["Content-Type"] = "text/plain";
          return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h,
            std::string("helm-tiles: S-52 ENC tile server. GET /chart/{z}/{x}/{y}.png\n"));
        }
        return std::make_shared<ix::HttpResponse>(404, "Not Found", ix::HttpErrorCode::Ok, h, std::string());
      });
    if (!server->listenAndStart()) { printf("HTTP listen on 8082 FAILED\n"); return false; }
    printf("S-52 tile server: http://127.0.0.1:8082/chart/{z}/{x}/{y}.png  (cell US5FL96M)\n");
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
    j->result = render_tile(j->z, j->x, j->y);
    { std::lock_guard<std::mutex> lk(j->m); j->done = true; }
    j->cv.notify_one();
  }
  wxEntryCleanup();
  return 0;
}
