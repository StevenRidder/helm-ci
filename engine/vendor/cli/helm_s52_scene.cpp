// helm_s52_scene.cpp -- OpenCPN s52plib -> neutral command stream.
//
// This is the RENDERMODEL-6 production bridge scaffold. It deliberately walks
// OpenCPN's resolved ObjRazRules after a headless render warm-up, so display
// category, SCAMIN, conditional symbology, text, soundings, and render ordering
// come from s52plib rather than a parallel GDAL-style interpretation.

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include <wx/app.h>
#include <wx/bitmap.h>
#include <wx/dcmemory.h>
#include <wx/filefn.h>
#include <wx/filename.h>
#include <wx/image.h>
#include <wx/string.h>

#include "gl_headers.h"

#include "chartbase.h"
#include "chartsymbols.h"
#include "color_types.h"
#include "mygeom.h"
#include "o_senc.h"
#include "ocpn_pixel.h"
#include "ocpn_region.h"
#include "s52plib.h"
#include "s52s57.h"
#include "s52utils.h"
#include "s57chart.h"
#include "s57registrar_mgr.h"
#include "viewport.h"

extern s52plib* ps52plib;
extern wxString g_csv_locn;
extern wxString g_SENCPrefix;
extern wxString g_SData_Locn;
void EnsureHeadlessGlobals();

namespace {

struct Options {
  std::string enc_path;
  std::string output_path;
  int width = 256;
  int height = 256;
  int z = -1;
  long x = -1;
  long y = -1;
  bool has_bbox = false;
  double bbox_west = 0.0;
  double bbox_south = 0.0;
  double bbox_east = 0.0;
  double bbox_north = 0.0;
  double scale_denom_override = 0.0;
  ColorScheme palette = GLOBAL_COLOR_SCHEME_DAY;
  std::string palette_name = "day";
  DisCat category = STANDARD;
  std::string category_name = "standard";
  LUPname symbol_style = PAPER_CHART;
  std::string symbol_style_name = "paper_chart";
  LUPname boundary_style = PLAIN_BOUNDARIES;
  std::string boundary_style_name = "plain";
  bool show_text = true;
  bool show_soundings = true;
  bool use_scamin = true;
  bool emit_culled = true;
  bool has_safety_contour_override = false;
  bool has_safety_depth_override = false;
  double safety_contour_override = 0.0;
  double safety_depth_override = 0.0;
};

struct GeoBBox {
  bool valid = false;
  double min_lat = 0.0;
  double min_lon = 0.0;
  double max_lat = 0.0;
  double max_lon = 0.0;
};

struct TargetPoint {
  double x = 0.0;
  double y = 0.0;
};

struct TriangleGeom {
  TargetPoint p0;
  TargetPoint p1;
  TargetPoint p2;
};

struct SoundingGeom {
  TargetPoint position;
  double depth = 0.0;
  std::string formatted_text;
};

struct CommandRecord {
  std::string command_id;
  std::string command_type;
  std::string render_pass;
  std::string source_object_id;
  std::string object_class;
  std::string display_category;
  int display_priority = 0;
  std::string lup_type;
  int lup_index = 0;
  int source_sequence = 0;
  int rule_sequence = 0;
  std::string rule_type;
  std::string rule_name;
  std::string instruction;
  int native_scale = 0;
  int scamin = 0;
  int super_scamin = 0;
  std::string safety_class = "standard";
  bool safety_relevant = false;
  GeoBBox bbox;
  double lon = 0.0;
  double lat = 0.0;
  double px = 0.0;
  double py = 0.0;
  std::string text;
  std::string geometry_status = "bbox_center_placeholder";
  bool geometry_truncated = false;
  std::vector<TargetPoint> polyline;
  std::vector<TriangleGeom> triangles;
  std::vector<SoundingGeom> soundings;
  int emit_sequence = 0;
};

struct DiagnosticRecord {
  std::string code = "semantic.culled";
  std::string source_object_id;
  std::string object_class;
  std::string reason;
  std::string message;
  int display_priority = 0;
  std::string lup_type;
  int scamin = 0;
  int native_scale = 0;
};

struct SceneCapture {
  std::vector<CommandRecord> commands;
  std::vector<DiagnosticRecord> diagnostics;
  std::map<std::string, int> command_type_counts;
  std::map<std::string, int> visible_class_counts;
  std::map<std::string, int> culled_class_counts;
  int visited_objects = 0;
  int visible_objects = 0;
  int culled_objects = 0;
  int cs_expanded_objects = 0;
};

static std::string home_dir() {
  const char* home = std::getenv("HOME");
  return home && *home ? home : ".";
}

static std::string runtime_path(const std::string& rel) {
  return home_dir() + "/.helm/runtime/" + rel;
}

static wxString env_or_runtime(const char* env_name, const std::string& rel) {
  if (const char* e = std::getenv(env_name)) {
    if (*e) return wxString::FromUTF8(e);
  }
  return wxString::FromUTF8(runtime_path(rel).c_str());
}

static wxString ensure_slash(wxString path) {
  if (!path.EndsWith(wxT("/"))) path += wxT("/");
  return path;
}

static std::string wx_to_utf8(const wxString& s) {
  wxCharBuffer b = s.ToUTF8();
  return b.data() ? std::string(b.data()) : std::string();
}

static std::string fixed_string(const char* s, size_t max_len) {
  if (!s) return std::string();
  size_t n = 0;
  while (n < max_len && s[n] != '\0') ++n;
  return std::string(s, n);
}

static std::string json_escape(const std::string& s) {
  std::ostringstream out;
  for (unsigned char c : s) {
    switch (c) {
      case '\\': out << "\\\\"; break;
      case '"': out << "\\\""; break;
      case '\b': out << "\\b"; break;
      case '\f': out << "\\f"; break;
      case '\n': out << "\\n"; break;
      case '\r': out << "\\r"; break;
      case '\t': out << "\\t"; break;
      default:
        if (c < 0x20) {
          out << "\\u" << std::hex << std::setw(4) << std::setfill('0')
              << static_cast<int>(c) << std::dec << std::setfill(' ');
        } else {
          out << static_cast<char>(c);
        }
    }
  }
  return out.str();
}

static std::string q(const std::string& s) { return "\"" + json_escape(s) + "\""; }

static std::string dis_cat_name(DisCat c) {
  switch (c) {
    case DISPLAYBASE: return "displaybase";
    case STANDARD: return "standard";
    case OTHER: return "other";
    case MARINERS_STANDARD: return "mariners_standard";
    default: return "unknown";
  }
}

static std::string lup_type_name(int index) {
  switch (index) {
    case 0: return "simplified";
    case 1: return "paper_chart";
    case 2: return "lines";
    case 3: return "plain_boundaries";
    case 4: return "symbolized_boundaries";
    default: return "unknown";
  }
}

static std::string rule_type_name(Rules_t type) {
  switch (type) {
    case RUL_TXT_TX: return "RUL_TXT_TX";
    case RUL_TXT_TE: return "RUL_TXT_TE";
    case RUL_SYM_PT: return "RUL_SYM_PT";
    case RUL_SIM_LN: return "RUL_SIM_LN";
    case RUL_COM_LN: return "RUL_COM_LN";
    case RUL_ARE_CO: return "RUL_ARE_CO";
    case RUL_ARE_PA: return "RUL_ARE_PA";
    case RUL_CND_SY: return "RUL_CND_SY";
    case RUL_MUL_SG: return "RUL_MUL_SG";
    case RUL_ARC_2C: return "RUL_ARC_2C";
    case RUL_NONE:
    default: return "RUL_NONE";
  }
}

static std::string command_type_for(Rules_t type) {
  switch (type) {
    case RUL_ARE_CO:
    case RUL_ARE_PA:
      return "fill_area";
    case RUL_SIM_LN:
    case RUL_COM_LN:
    case RUL_ARC_2C:
      return "stroke_line";
    case RUL_SYM_PT:
      return "place_symbol";
    case RUL_TXT_TX:
    case RUL_TXT_TE:
      return "draw_text";
    case RUL_MUL_SG:
      return "draw_sounding";
    default:
      return std::string();
  }
}

static std::string render_pass_for(Rules_t type) {
  switch (type) {
    case RUL_ARE_CO:
    case RUL_ARE_PA:
      return "area_fill";
    case RUL_SIM_LN:
    case RUL_COM_LN:
    case RUL_ARC_2C:
      return "line";
    case RUL_SYM_PT:
      return "symbol";
    case RUL_TXT_TX:
    case RUL_TXT_TE:
      return "text";
    case RUL_MUL_SG:
      return "sounding";
    default:
      return "metadata";
  }
}

static std::string rule_resource_name(const Rules* rule) {
  if (!rule || !rule->razRule) return std::string();
  const Rule* rr = rule->razRule;
  switch (rule->ruleType) {
    case RUL_SYM_PT: return fixed_string(rr->name.SYNM, sizeof(rr->name.SYNM));
    case RUL_ARE_PA: return fixed_string(rr->name.PANM, sizeof(rr->name.PANM));
    case RUL_COM_LN:
    case RUL_SIM_LN:
    case RUL_ARC_2C:
      return fixed_string(rr->name.LINM, sizeof(rr->name.LINM));
    default:
      return std::string();
  }
}

static std::string safety_class_for(const std::string& object_class) {
  if (object_class == "SOUNDG") return "sounding";
  if (object_class == "DEPARE") return "depth_area";
  if (object_class == "DEPCNT") return "depth_contour";
  if (object_class == "OBSTRN" || object_class == "WRECKS" ||
      object_class == "UWTROC") return "danger";
  if (object_class.rfind("BOY", 0) == 0 || object_class.rfind("BCN", 0) == 0)
    return "aid_to_navigation";
  return "standard";
}

static bool safety_relevant_for(const std::string& object_class) {
  const std::string safety = safety_class_for(object_class);
  return safety != "standard";
}

static double tile_lon(double x, int z) {
  return x / std::pow(2.0, z) * 360.0 - 180.0;
}

static double tile_lat(double y, int z) {
  const double n = M_PI * (1.0 - 2.0 * y / std::pow(2.0, z));
  return std::atan(std::sinh(n)) * 180.0 / M_PI;
}

static double zoom_scale(int z, double lat) {
  return 559082264.029 * std::cos(lat * M_PI / 180.0) / std::pow(2.0, z);
}

static bool parse_long_arg(const std::string& s, long* out) {
  char* end = nullptr;
  long v = std::strtol(s.c_str(), &end, 10);
  if (!end || *end) return false;
  *out = v;
  return true;
}

static bool parse_int_arg(const std::string& s, int* out) {
  long v = 0;
  if (!parse_long_arg(s, &v)) return false;
  *out = static_cast<int>(v);
  return true;
}

static bool parse_double_arg(const std::string& s, double* out) {
  char* end = nullptr;
  double v = std::strtod(s.c_str(), &end);
  if (!end || *end) return false;
  *out = v;
  return true;
}

static bool parse_bbox_arg(const std::string& s, Options* opts) {
  double w = 0.0;
  double south = 0.0;
  double e = 0.0;
  double north = 0.0;
  char tail = '\0';
  if (std::sscanf(s.c_str(), "%lf,%lf,%lf,%lf%c", &w, &south, &e, &north,
                  &tail) != 4) {
    return false;
  }
  if (!(w < e && south < north)) return false;
  opts->has_bbox = true;
  opts->bbox_west = w;
  opts->bbox_south = south;
  opts->bbox_east = e;
  opts->bbox_north = north;
  return true;
}

static bool parse_palette(const std::string& value, Options* opts) {
  if (value == "day") {
    opts->palette = GLOBAL_COLOR_SCHEME_DAY;
    opts->palette_name = "day";
    return true;
  }
  if (value == "dusk") {
    opts->palette = GLOBAL_COLOR_SCHEME_DUSK;
    opts->palette_name = "dusk";
    return true;
  }
  if (value == "night") {
    opts->palette = GLOBAL_COLOR_SCHEME_NIGHT;
    opts->palette_name = "night";
    return true;
  }
  return false;
}

static bool parse_category(const std::string& value, Options* opts) {
  if (value == "base" || value == "displaybase") {
    opts->category = DISPLAYBASE;
    opts->category_name = "displaybase";
    return true;
  }
  if (value == "std" || value == "standard") {
    opts->category = STANDARD;
    opts->category_name = "standard";
    return true;
  }
  if (value == "all" || value == "other") {
    opts->category = OTHER;
    opts->category_name = "other";
    return true;
  }
  if (value == "mariner" || value == "mariners_standard") {
    opts->category = MARINERS_STANDARD;
    opts->category_name = "mariners_standard";
    return true;
  }
  return false;
}

static void usage() {
  std::fprintf(stderr,
      "usage: helm-s52-scene <ENC.000> [--out scene.commands.json] "
      "[--z Z --x X --y Y] [--width N --height N] "
      "[--bbox west,south,east,north] [--scale-denom N] "
      "[--palette day|dusk|night] [--category base|standard|other|mariner] "
      "[--safety-contour M] [--safety-depth M] "
      "[--symbol simplified|paper] [--boundary plain|symbolized] "
      "[--no-text] [--no-soundings] [--no-scamin] [--no-culled]\n");
}

static bool parse_options(const std::vector<std::string>& args, Options* opts) {
  for (size_t i = 1; i < args.size(); ++i) {
    const std::string& a = args[i];
    auto require_value = [&](std::string* value) -> bool {
      if (i + 1 >= args.size()) {
        std::fprintf(stderr, "missing value for %s\n", a.c_str());
        return false;
      }
      *value = args[++i];
      return true;
    };
    std::string value;
    if (a == "--out") {
      if (!require_value(&opts->output_path)) return false;
    } else if (a == "--z") {
      if (!require_value(&value) || !parse_int_arg(value, &opts->z)) return false;
    } else if (a == "--x") {
      if (!require_value(&value) || !parse_long_arg(value, &opts->x)) return false;
    } else if (a == "--y") {
      if (!require_value(&value) || !parse_long_arg(value, &opts->y)) return false;
    } else if (a == "--width") {
      if (!require_value(&value) || !parse_int_arg(value, &opts->width)) return false;
    } else if (a == "--height") {
      if (!require_value(&value) || !parse_int_arg(value, &opts->height)) return false;
    } else if (a == "--bbox") {
      if (!require_value(&value) || !parse_bbox_arg(value, opts)) return false;
    } else if (a == "--scale-denom") {
      if (!require_value(&value) ||
          !parse_double_arg(value, &opts->scale_denom_override)) {
        return false;
      }
    } else if (a == "--palette") {
      if (!require_value(&value) || !parse_palette(value, opts)) return false;
    } else if (a == "--category") {
      if (!require_value(&value) || !parse_category(value, opts)) return false;
    } else if (a == "--safety-contour") {
      if (!require_value(&value) ||
          !parse_double_arg(value, &opts->safety_contour_override)) {
        return false;
      }
      opts->has_safety_contour_override = true;
    } else if (a == "--safety-depth") {
      if (!require_value(&value) ||
          !parse_double_arg(value, &opts->safety_depth_override)) {
        return false;
      }
      opts->has_safety_depth_override = true;
    } else if (a == "--symbol") {
      if (!require_value(&value)) return false;
      if (value == "simplified") {
        opts->symbol_style = SIMPLIFIED;
        opts->symbol_style_name = "simplified";
      } else if (value == "paper" || value == "paper_chart") {
        opts->symbol_style = PAPER_CHART;
        opts->symbol_style_name = "paper_chart";
      } else {
        std::fprintf(stderr, "unknown symbol style: %s\n", value.c_str());
        return false;
      }
    } else if (a == "--boundary") {
      if (!require_value(&value)) return false;
      if (value == "plain") {
        opts->boundary_style = PLAIN_BOUNDARIES;
        opts->boundary_style_name = "plain";
      } else if (value == "symbolized") {
        opts->boundary_style = SYMBOLIZED_BOUNDARIES;
        opts->boundary_style_name = "symbolized";
      } else {
        std::fprintf(stderr, "unknown boundary style: %s\n", value.c_str());
        return false;
      }
    } else if (a == "--no-text") {
      opts->show_text = false;
    } else if (a == "--no-soundings") {
      opts->show_soundings = false;
    } else if (a == "--no-scamin") {
      opts->use_scamin = false;
    } else if (a == "--no-culled") {
      opts->emit_culled = false;
    } else if (!a.empty() && a[0] == '-') {
      std::fprintf(stderr, "unknown option: %s\n", a.c_str());
      return false;
    } else if (opts->enc_path.empty()) {
      opts->enc_path = a;
    } else {
      std::fprintf(stderr, "unexpected positional arg: %s\n", a.c_str());
      return false;
    }
  }

  if (opts->enc_path.empty()) return false;
  if (opts->width <= 0 || opts->height <= 0) return false;
  if ((opts->z >= 0) != (opts->x >= 0 && opts->y >= 0)) {
    std::fprintf(stderr, "--z, --x, and --y must be supplied together\n");
    return false;
  }
  if (opts->has_bbox && opts->z >= 0) {
    std::fprintf(stderr, "--bbox and --z/--x/--y are mutually exclusive\n");
    return false;
  }
  if (opts->scale_denom_override < 0.0) return false;
  if (opts->has_safety_contour_override &&
      opts->safety_contour_override < 0.0) {
    return false;
  }
  if (opts->has_safety_depth_override && opts->safety_depth_override < 0.0) {
    return false;
  }
  return true;
}

static GeoBBox bbox_for_obj(const S57Obj* obj) {
  GeoBBox bbox;
  if (!obj) return bbox;
  if (obj->BBObj.GetValid()) {
    bbox.valid = true;
    bbox.min_lat = obj->BBObj.GetMinLat();
    bbox.min_lon = obj->BBObj.GetMinLon();
    bbox.max_lat = obj->BBObj.GetMaxLat();
    bbox.max_lon = obj->BBObj.GetMaxLon();
    return bbox;
  }
  if (std::isfinite(obj->m_lat) && std::isfinite(obj->m_lon)) {
    bbox.valid = true;
    bbox.min_lat = bbox.max_lat = obj->m_lat;
    bbox.min_lon = bbox.max_lon = obj->m_lon;
  }
  return bbox;
}

static void position_for_obj(const S57Obj* obj, const GeoBBox& bbox,
                             const ViewPort& vp, double* lon, double* lat,
                             double* px, double* py) {
  double out_lon = 0.0;
  double out_lat = 0.0;
  if (bbox.valid) {
    out_lon = (bbox.min_lon + bbox.max_lon) * 0.5;
    out_lat = (bbox.min_lat + bbox.max_lat) * 0.5;
  } else if (obj) {
    out_lon = obj->m_lon;
    out_lat = obj->m_lat;
  } else {
    out_lon = vp.clon;
    out_lat = vp.clat;
  }
  wxPoint2DDouble p = const_cast<ViewPort&>(vp).GetDoublePixFromLL(out_lat, out_lon);
  *lon = out_lon;
  *lat = out_lat;
  *px = p.m_x;
  *py = p.m_y;
}

static TargetPoint target_from_rule_xy(const ObjRazRules* rz, double north,
                                       double east, const ViewPort& vp) {
  TargetPoint out;
  if (!rz || !rz->obj || !rz->sm_transform_parms) return out;
  const S57Obj* obj = rz->obj;
  const double valx = (east * obj->x_rate) + obj->x_origin;
  const double valy = (north * obj->y_rate) + obj->y_origin;
  out.x = ((valx - rz->sm_transform_parms->easting_vp_center) *
           vp.view_scale_ppm) +
          (vp.pix_width / 2.0);
  out.y = (vp.pix_height / 2.0) -
          ((valy - rz->sm_transform_parms->northing_vp_center) *
           vp.view_scale_ppm);
  return out;
}

static TargetPoint target_from_ll(double lat, double lon, const ViewPort& vp) {
  wxPoint2DDouble p = const_cast<ViewPort&>(vp).GetDoublePixFromLL(lat, lon);
  TargetPoint out;
  out.x = p.m_x;
  out.y = p.m_y;
  return out;
}

static std::string text_for_obj_rule(const S57Obj* obj, Rules_t type) {
  if (!obj) return std::string();
  if (type == RUL_MUL_SG && obj->Primitive_type == GEO_POINT && std::isfinite(obj->z)) {
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(1) << obj->z;
    return ss.str();
  }
  if ((type == RUL_TXT_TX || type == RUL_TXT_TE) && obj->FText) {
    return wx_to_utf8(obj->FText->frmtd);
  }
  return std::string();
}

static std::string format_depth(double depth) {
  std::ostringstream ss;
  ss << std::fixed << std::setprecision(1) << depth;
  return ss.str();
}

static void populate_line_geometry(ObjRazRules* rz, const ViewPort& vp,
                                   CommandRecord* c) {
  if (!rz || !rz->obj || !rz->obj->m_ls_list || !rz->obj->m_chart_context ||
      !rz->obj->m_chart_context->vertex_buffer) {
    return;
  }
  const size_t kMaxPoints = 4096;
  unsigned char* source =
      reinterpret_cast<unsigned char*>(rz->obj->m_chart_context->vertex_buffer);
  for (line_segment_element* ls = rz->obj->m_ls_list; ls; ls = ls->next) {
    size_t vbo_offset = 0;
    size_t count = 0;
    if ((ls->ls_type == TYPE_EE) || (ls->ls_type == TYPE_EE_REV)) {
      if (!ls->pedge) continue;
      vbo_offset = ls->pedge->vbo_offset;
      count = ls->pedge->nCount;
    } else {
      if (!ls->pcs) continue;
      vbo_offset = ls->pcs->vbo_offset;
      count = 2;
    }
    float* pts = reinterpret_cast<float*>(source + vbo_offset);
    for (size_t i = 0; i < count; ++i) {
      if (c->polyline.size() >= kMaxPoints) {
        c->geometry_truncated = true;
        return;
      }
      c->polyline.push_back(target_from_rule_xy(rz, pts[(i * 2) + 1],
                                                pts[i * 2], vp));
    }
  }
  if (!c->polyline.empty()) c->geometry_status = "opencpn_line_vbo";
}

static TargetPoint area_vertex_target(ObjRazRules* rz, double raw_x,
                                      double raw_y, const ViewPort& vp) {
  return target_from_rule_xy(rz, raw_y, raw_x, vp);
}

static void add_triangle_fan(const std::vector<TargetPoint>& pts,
                             CommandRecord* c) {
  if (pts.size() < 3) return;
  for (size_t i = 1; i + 1 < pts.size(); ++i) {
    c->triangles.push_back({pts[0], pts[i], pts[i + 1]});
  }
}

static void add_triangle_strip(const std::vector<TargetPoint>& pts,
                               CommandRecord* c) {
  if (pts.size() < 3) return;
  for (size_t i = 0; i + 2 < pts.size(); ++i) {
    c->triangles.push_back({pts[i], pts[i + 1], pts[i + 2]});
  }
}

static void add_triangles(const std::vector<TargetPoint>& pts,
                          CommandRecord* c) {
  for (size_t i = 0; i + 2 < pts.size(); i += 3) {
    c->triangles.push_back({pts[i], pts[i + 1], pts[i + 2]});
  }
}

static void populate_area_geometry(ObjRazRules* rz, const ViewPort& vp,
                                   CommandRecord* c) {
  if (!rz || !rz->obj || !rz->obj->pPolyTessGeo) return;
  if (!rz->obj->pPolyTessGeo->IsOk()) rz->obj->pPolyTessGeo->BuildDeferredTess();
  PolyTriGroup* group = rz->obj->pPolyTessGeo->Get_PolyTriGroup_head();
  if (!group) return;
  const size_t kMaxTriangles = 4096;
  for (TriPrim* prim = group->tri_prim_head; prim; prim = prim->p_next) {
    std::vector<TargetPoint> pts;
    pts.reserve(static_cast<size_t>(std::max(0, prim->nVert)));
    if (group->data_type == DATA_TYPE_DOUBLE) {
      double* raw = prim->p_vertex;
      for (int i = 0; i < prim->nVert; ++i) {
        const double x = *raw++;
        const double y = *raw++;
        pts.push_back(area_vertex_target(rz, x, y, vp));
      }
    } else {
      float* raw = reinterpret_cast<float*>(prim->p_vertex);
      for (int i = 0; i < prim->nVert; ++i) {
        const double x = *raw++;
        const double y = *raw++;
        pts.push_back(area_vertex_target(rz, x, y, vp));
      }
    }
    const size_t before = c->triangles.size();
    if (prim->type == PTG_TRIANGLE_FAN) {
      add_triangle_fan(pts, c);
    } else if (prim->type == PTG_TRIANGLE_STRIP) {
      add_triangle_strip(pts, c);
    } else {
      add_triangles(pts, c);
    }
    if (c->triangles.size() >= kMaxTriangles) {
      c->triangles.resize(kMaxTriangles);
      c->geometry_truncated = true;
      break;
    }
    if (c->triangles.size() == before && !pts.empty()) break;
  }
  if (!c->triangles.empty()) c->geometry_status = "opencpn_area_triangles";
}

static void populate_sounding_geometry(ObjRazRules* rz, const ViewPort& vp,
                                       CommandRecord* c) {
  if (!rz || !rz->obj || !rz->obj->geoPtz || !rz->obj->geoPtMulti ||
      rz->obj->npt <= 0) {
    return;
  }
  const size_t kMaxSoundings = 4096;
  double* sm = rz->obj->geoPtz;
  double* ll = rz->obj->geoPtMulti;
  for (int i = 0; i < rz->obj->npt; ++i) {
    const double east = *sm++;
    const double north = *sm++;
    const double depth = *sm++;
    const double lon = *ll++;
    const double lat = *ll++;
    (void)east;
    (void)north;
    if (c->soundings.size() >= kMaxSoundings) {
      c->geometry_truncated = true;
      break;
    }
    SoundingGeom s;
    s.position = target_from_ll(lat, lon, vp);
    s.depth = depth;
    s.formatted_text = format_depth(depth);
    c->soundings.push_back(s);
  }
  if (!c->soundings.empty()) {
    c->geometry_status = "opencpn_multipoint_soundings";
    c->text = c->soundings.front().formatted_text;
    c->px = c->soundings.front().position.x;
    c->py = c->soundings.front().position.y;
  }
}

static void populate_point_geometry(ObjRazRules* rz, const ViewPort& vp,
                                    CommandRecord* c) {
  if (!rz || !rz->obj) return;
  TargetPoint p = target_from_rule_xy(rz, rz->obj->y, rz->obj->x, vp);
  c->px = p.x;
  c->py = p.y;
  c->geometry_status = "opencpn_object_point";
}

static void populate_command_geometry(ObjRazRules* rz, Rules_t type,
                                      const ViewPort& vp, CommandRecord* c) {
  switch (type) {
    case RUL_ARE_CO:
    case RUL_ARE_PA:
      populate_area_geometry(rz, vp, c);
      break;
    case RUL_SIM_LN:
    case RUL_COM_LN:
    case RUL_ARC_2C:
      populate_line_geometry(rz, vp, c);
      break;
    case RUL_MUL_SG:
      populate_sounding_geometry(rz, vp, c);
      break;
    case RUL_SYM_PT:
    case RUL_TXT_TX:
    case RUL_TXT_TE:
      populate_point_geometry(rz, vp, c);
      break;
    default:
      break;
  }
}

static std::string cull_reason(ObjRazRules* rz, const ViewPort& vp) {
  if (!ps52plib->ObjectRenderCheckPos(rz)) return "viewport";
  if (ps52plib->m_bUseSCAMIN && rz->obj && rz->LUP &&
      rz->obj->Scamin > 0 && vp.chart_scale > rz->obj->Scamin &&
      rz->LUP->DISC != DISPLAYBASE && rz->LUP->DPRI != PRIO_GROUP1) {
    return "scamin";
  }
  const DisCat obj_cat = rz->obj ? rz->obj->m_DisplayCat : rz->LUP->DISC;
  if (ps52plib->GetDisplayCategory() == DISPLAYBASE && obj_cat != DISPLAYBASE)
    return "display_category";
  if (ps52plib->GetDisplayCategory() == STANDARD &&
      obj_cat != DISPLAYBASE && obj_cat != STANDARD)
    return "display_category";
  if (!ps52plib->ObjectRenderCheckDates(rz)) return "date";
  return "display_category_or_no_show";
}

class SceneChart : public s57chart {
public:
  void CaptureScene(const ViewPort& vp, const Options& opts, SceneCapture* out) {
    std::set<const ObjRazRules*> diagnosed;
    int emit_sequence = 0;
    for (int prio = 0; prio < PRIO_NUM; ++prio) {
      const int boundary_index =
          ps52plib->m_nBoundaryStyle == SYMBOLIZED_BOUNDARIES ? 4 : 3;
      CaptureList(prio, boundary_index, vp, opts, out, &emit_sequence,
                  &diagnosed);
      CaptureList(prio, 2, vp, opts, out, &emit_sequence, &diagnosed);
      const int point_index = ps52plib->m_nSymbolStyle == SIMPLIFIED ? 0 : 1;
      CaptureList(prio, point_index, vp, opts, out, &emit_sequence,
                  &diagnosed);
    }
  }

private:
  void CaptureList(int prio, int lup_index, const ViewPort& vp,
                   const Options& opts, SceneCapture* out, int* emit_sequence,
                   std::set<const ObjRazRules*>* diagnosed) {
    ObjRazRules* cur = razRules[prio][lup_index];
    while (cur) {
      out->visited_objects++;
      cur->sm_transform_parms = &vp_transform;
      const std::string object_class =
          cur->LUP ? fixed_string(cur->LUP->OBCL, 6)
                   : (cur->obj ? fixed_string(cur->obj->FeatureName, 6)
                               : "UNKNOWN");
      const bool visible = ps52plib->ObjectRenderCheckRules(cur, true);
      if (!visible) {
        out->culled_objects++;
        out->culled_class_counts[object_class]++;
        if (opts.emit_culled && diagnosed->insert(cur).second) {
          DiagnosticRecord d;
          d.source_object_id = SourceObjectId(cur);
          d.object_class = object_class;
          d.reason = cull_reason(cur, vp);
          d.message = object_class + " culled by OpenCPN s52plib (" + d.reason + ")";
          d.display_priority = prio;
          d.lup_type = lup_type_name(lup_index);
          d.scamin = cur->obj ? cur->obj->Scamin : 0;
          d.native_scale = GetNativeScale();
          out->diagnostics.push_back(d);
        }
        cur = cur->next;
        continue;
      }

      out->visible_objects++;
      out->visible_class_counts[object_class]++;
      if (cur->obj && cur->obj->bCS_Added && cur->obj->CSrules)
        out->cs_expanded_objects++;

      CaptureRules(cur, cur->LUP ? cur->LUP->ruleList : nullptr, prio,
                   lup_index, vp, false, out, emit_sequence);
      if (cur->obj && cur->obj->CSrules) {
        CaptureRules(cur, cur->obj->CSrules, prio, lup_index, vp, true, out,
                     emit_sequence);
      }
      cur = cur->next;
    }
  }

  void CaptureRules(ObjRazRules* rz, Rules* rules, int prio, int lup_index,
                    const ViewPort& vp, bool cs_expanded, SceneCapture* out,
                    int* emit_sequence) {
    for (Rules* rule = rules; rule; rule = rule->next) {
      if (rule->ruleType == RUL_CND_SY || rule->ruleType == RUL_NONE) continue;
      const std::string command_type = command_type_for(rule->ruleType);
      if (command_type.empty()) continue;

      CommandRecord c;
      c.command_type = command_type;
      c.render_pass = render_pass_for(rule->ruleType);
      c.source_object_id = SourceObjectId(rz);
      c.object_class = rz->LUP ? fixed_string(rz->LUP->OBCL, 6)
                               : fixed_string(rz->obj->FeatureName, 6);
      c.display_category =
          rz->obj ? dis_cat_name(rz->obj->m_DisplayCat)
                  : (rz->LUP ? dis_cat_name(rz->LUP->DISC) : "unknown");
      c.display_priority = prio;
      c.lup_type = lup_type_name(lup_index);
      c.lup_index = lup_index;
      c.source_sequence = rz->LUP ? rz->LUP->nSequence : 0;
      c.rule_sequence = rule->n_sequence;
      c.rule_type = rule_type_name(rule->ruleType);
      c.rule_name = rule_resource_name(rule);
      c.instruction = rule->INSTstr ? std::string(rule->INSTstr) : std::string();
      c.native_scale = GetNativeScale();
      c.scamin = rz->obj ? rz->obj->Scamin : 0;
      c.super_scamin = rz->obj ? rz->obj->SuperScamin : 0;
      c.safety_class = safety_class_for(c.object_class);
      c.safety_relevant = safety_relevant_for(c.object_class);
      c.bbox = bbox_for_obj(rz->obj);
      position_for_obj(rz->obj, c.bbox, vp, &c.lon, &c.lat, &c.px, &c.py);
      c.text = text_for_obj_rule(rz->obj, rule->ruleType);
      populate_command_geometry(rz, rule->ruleType, vp, &c);
      c.emit_sequence = ++(*emit_sequence);
      std::ostringstream id;
      id << "cmd." << c.object_class << "." << c.emit_sequence;
      if (cs_expanded) id << ".cs";
      c.command_id = id.str();
      out->command_type_counts[c.command_type]++;
      out->commands.push_back(c);
    }
  }

  std::string SourceObjectId(ObjRazRules* rz) const {
    const std::string klass =
        rz && rz->LUP ? fixed_string(rz->LUP->OBCL, 6)
                      : (rz && rz->obj ? fixed_string(rz->obj->FeatureName, 6)
                                       : "UNKNOWN");
    const int index = rz && rz->obj ? rz->obj->Index : 0;
    std::ostringstream out;
    out << klass << "-" << index;
    return out.str();
  }
};

static ViewPort make_viewport(SceneChart* chart, const Options& opts,
                              Extent* chart_extent) {
  Extent ext;
  chart->GetChartExtent(&ext);
  if (chart_extent) *chart_extent = ext;

  double north = ext.NLAT;
  double south = ext.SLAT;
  double west = ext.WLON;
  double east = ext.ELON;
  double clat = (north + south) / 2.0;
  double clon = (west + east) / 2.0;
  double chart_scale = chart->GetNativeScale();
  double ppm = 0.0;

  if (opts.has_bbox) {
    west = opts.bbox_west;
    east = opts.bbox_east;
    south = opts.bbox_south;
    north = opts.bbox_north;
    clat = (north + south) / 2.0;
    clon = (west + east) / 2.0;
  } else if (opts.z >= 0) {
    west = tile_lon(opts.x, opts.z);
    east = tile_lon(opts.x + 1, opts.z);
    north = tile_lat(opts.y, opts.z);
    south = tile_lat(opts.y + 1, opts.z);
    clat = (north + south) / 2.0;
    clon = (west + east) / 2.0;
    chart_scale = zoom_scale(opts.z, clat);
  }
  if (opts.scale_denom_override > 0.0) chart_scale = opts.scale_denom_override;

  double span_m = (north - south) * 1852.0 * 60.0;
  if (span_m <= 0.0) span_m = 1000.0;
  ppm = static_cast<double>(opts.height) / span_m;

  ViewPort vp;
  vp.clat = clat;
  vp.clon = clon;
  vp.view_scale_ppm = ppm;
  vp.pix_width = opts.width;
  vp.pix_height = opts.height;
  vp.rotation = 0.0;
  vp.skew = 0.0;
  vp.tilt = 0.0;
  vp.m_projection_type = PROJECTION_MERCATOR;
  vp.chart_scale = chart_scale;
  vp.ref_scale = chart_scale;
  vp.b_quilt = false;
  vp.rv_rect = wxRect(0, 0, opts.width, opts.height);
  vp.SetBoxes();
  vp.Validate();
  return vp;
}

static void write_bbox(std::ostream& os, const GeoBBox& bbox) {
  if (!bbox.valid) {
    os << "null";
    return;
  }
  os << "{\"west\":" << bbox.min_lon << ",\"south\":" << bbox.min_lat
     << ",\"east\":" << bbox.max_lon << ",\"north\":" << bbox.max_lat << "}";
}

static void write_target_point(std::ostream& os, const TargetPoint& p) {
  os << "[" << p.x << "," << p.y << "]";
}

static void write_polyline(std::ostream& os, const std::vector<TargetPoint>& pts) {
  os << "[";
  for (size_t i = 0; i < pts.size(); ++i) {
    if (i) os << ",";
    write_target_point(os, pts[i]);
  }
  os << "]";
}

static void write_triangles(std::ostream& os,
                            const std::vector<TriangleGeom>& triangles) {
  os << "[";
  for (size_t i = 0; i < triangles.size(); ++i) {
    if (i) os << ",";
    os << "[";
    write_target_point(os, triangles[i].p0);
    os << ",";
    write_target_point(os, triangles[i].p1);
    os << ",";
    write_target_point(os, triangles[i].p2);
    os << "]";
  }
  os << "]";
}

static void write_soundings(std::ostream& os,
                            const std::vector<SoundingGeom>& soundings) {
  os << "[";
  for (size_t i = 0; i < soundings.size(); ++i) {
    if (i) os << ",";
    os << "{\"position\":";
    write_target_point(os, soundings[i].position);
    os << ",\"depth\":" << soundings[i].depth;
    os << ",\"formatted_text\":" << q(soundings[i].formatted_text);
    os << "}";
  }
  os << "]";
}

static void write_string_int_map(std::ostream& os,
                                 const std::map<std::string, int>& counts) {
  os << "{";
  bool first = true;
  for (const auto& kv : counts) {
    if (!first) os << ",";
    first = false;
    os << q(kv.first) << ":" << kv.second;
  }
  os << "}";
}

static void write_command(std::ostream& os, const CommandRecord& c,
                          const Options& opts) {
  os << "{";
  os << "\"type\":" << q(c.command_type);
  os << ",\"command_id\":" << q(c.command_id);
  os << ",\"coordinate_space\":\"target\"";
  os << ",\"geometry_status\":" << q(c.geometry_status);
  os << ",\"geometry_truncated\":" << (c.geometry_truncated ? "true" : "false");
  if (c.command_type == "fill_area") {
    os << ",\"rings\":[]";
    os << ",\"triangles\":";
    write_triangles(os, c.triangles);
  } else if (c.command_type == "stroke_line") {
    os << ",\"polyline\":";
    write_polyline(os, c.polyline);
  } else if (c.command_type == "place_symbol") {
    os << ",\"symbol_ref\":" << q(c.rule_name.empty() ? "opencpn.symbol" : "s52." + c.rule_name);
    os << ",\"position\":[" << c.px << "," << c.py << "]";
  } else if (c.command_type == "draw_text") {
    os << ",\"text\":" << q(c.text.empty() ? c.instruction : c.text);
    os << ",\"position\":[" << c.px << "," << c.py << "]";
  } else if (c.command_type == "draw_sounding") {
    os << ",\"formatted_text\":" << q(c.text);
    os << ",\"position\":[" << c.px << "," << c.py << "]";
    os << ",\"soundings\":";
    write_soundings(os, c.soundings);
  }
  os << ",\"geographic_bbox\":";
  write_bbox(os, c.bbox);
  os << ",\"s52_rule\":{";
  os << "\"rule_type\":" << q(c.rule_type);
  os << ",\"rule_name\":" << q(c.rule_name);
  os << ",\"instruction\":" << q(c.instruction);
  os << ",\"rule_sequence\":" << c.rule_sequence;
  os << "}";
  os << ",\"s52_semantics\":{";
  os << "\"presentation_authority\":\"opencpn.s52plib\"";
  os << ",\"source_object_id\":" << q(c.source_object_id);
  os << ",\"object_class\":" << q(c.object_class);
  os << ",\"display_category\":" << q(c.display_category);
  os << ",\"display_priority\":" << c.display_priority;
  os << ",\"lup_type\":" << q(c.lup_type);
  os << ",\"render_pass\":" << q(c.render_pass);
  os << ",\"source_sequence\":" << c.source_sequence;
  os << ",\"rule_sequence\":" << c.rule_sequence;
  os << ",\"native_scale\":" << c.native_scale;
  if (c.scamin > 0) os << ",\"scamin_max_scale\":" << c.scamin;
  if (c.super_scamin > 0) os << ",\"super_scamin_max_scale\":" << c.super_scamin;
  os << ",\"use_scamin\":" << (opts.use_scamin ? "true" : "false");
  os << ",\"use_super_scamin\":" << (ps52plib->m_bUseSUPER_SCAMIN ? "true" : "false");
  os << ",\"safety_class\":" << q(c.safety_class);
  os << ",\"safety_relevant\":" << (c.safety_relevant ? "true" : "false");
  os << ",\"visible\":true";
  os << ",\"order_key\":[1,1," << c.display_priority << "," << c.lup_index
     << "," << c.emit_sequence << "]";
  os << "}";
  os << ",\"provenance_refs\":[" << q("prov." + c.source_object_id) << "]";
  os << "}";
}

static void write_scene_json(std::ostream& os, const Options& opts,
                             SceneChart& chart, ViewPort& vp,
                             const Extent& ext, const SceneCapture& capture) {
  os << std::setprecision(10);
  os << "{\n";
  os << "  \"schema_version\":\"vulkan.render_scene.v0\",\n";
  os << "  \"scene_id\":\"opencpn-s52plib-neutral\",\n";
  os << "  \"source_epoch\":\"opencpn.s52plib.headless\",\n";
  os << "  \"chart_source\":{";
  os << "\"enc_path\":" << q(opts.enc_path);
  os << ",\"cell_id\":" << q(wx_to_utf8(wxFileName(wxString::FromUTF8(opts.enc_path.c_str())).GetName()));
  os << ",\"native_scale\":" << chart.GetNativeScale();
  os << ",\"extent\":{\"west\":" << ext.WLON << ",\"south\":" << ext.SLAT
     << ",\"east\":" << ext.ELON << ",\"north\":" << ext.NLAT << "}";
  os << "},\n";
  os << "  \"render_view\":{";
  os << "\"projection\":\"web_mercator_tile\"";
  os << ",\"center\":{\"lon\":" << vp.clon << ",\"lat\":" << vp.clat << "}";
  os << ",\"scale_denom\":" << vp.chart_scale;
  os << ",\"rotation_deg\":0";
  os << ",\"pixel_size\":[" << opts.width << "," << opts.height << "]";
  os << ",\"device_pixel_ratio\":1";
  os << ",\"geographic_bbox\":{\"west\":" << vp.GetBBox().GetMinLon()
     << ",\"south\":" << vp.GetBBox().GetMinLat()
     << ",\"east\":" << vp.GetBBox().GetMaxLon()
     << ",\"north\":" << vp.GetBBox().GetMaxLat() << "}";
  if (opts.z >= 0) {
    os << ",\"tile\":{\"z\":" << opts.z << ",\"x\":" << opts.x
       << ",\"y\":" << opts.y << "}";
  }
  if (opts.has_bbox) {
    os << ",\"viewport_mode\":\"fixed_bbox\"";
  }
  if (opts.scale_denom_override > 0.0) {
    os << ",\"scale_override\":true";
  }
  os << "},\n";
  os << "  \"display_state\":{";
  os << "\"palette\":" << q(opts.palette_name);
  os << ",\"display_category\":" << q(opts.category_name);
  os << ",\"show_text\":" << (opts.show_text ? "true" : "false");
  os << ",\"show_soundings\":" << (opts.show_soundings ? "true" : "false");
  os << ",\"symbol_style\":" << q(opts.symbol_style_name);
  os << ",\"boundary_style\":" << q(opts.boundary_style_name);
  os << ",\"safety_contour\":" << S52_getMarinerParam(S52_MAR_SAFETY_CONTOUR);
  os << ",\"safety_depth\":" << S52_getMarinerParam(S52_MAR_SAFETY_DEPTH);
  os << ",\"use_scamin\":" << (opts.use_scamin ? "true" : "false");
  os << ",\"use_super_scamin\":" << (ps52plib->m_bUseSUPER_SCAMIN ? "true" : "false");
  os << "},\n";
  os << "  \"command_groups\":[{\"group_id\":\"opencpn-s52plib\","
     << "\"chart_priority\":1,\"s52_layer\":\"s52plib-resolved\","
     << "\"quilt_rank\":1,\"commands\":[";
  for (size_t i = 0; i < capture.commands.size(); ++i) {
    if (i) os << ",";
    write_command(os, capture.commands[i], opts);
  }
  os << "]}],\n";
  os << "  \"diagnostics\":[";
  for (size_t i = 0; i < capture.diagnostics.size(); ++i) {
    const DiagnosticRecord& d = capture.diagnostics[i];
    if (i) os << ",";
    os << "{";
    os << "\"code\":" << q(d.code);
    os << ",\"message\":" << q(d.message);
    os << ",\"reason\":" << q(d.reason);
    os << ",\"s52_semantics\":{";
    os << "\"presentation_authority\":\"opencpn.s52plib\"";
    os << ",\"source_object_id\":" << q(d.source_object_id);
    os << ",\"object_class\":" << q(d.object_class);
    os << ",\"display_priority\":" << d.display_priority;
    os << ",\"lup_type\":" << q(d.lup_type);
    os << ",\"native_scale\":" << d.native_scale;
    if (d.scamin > 0) os << ",\"scamin_max_scale\":" << d.scamin;
    os << ",\"visible\":false";
    os << "}";
    os << ",\"provenance_refs\":[" << q("prov." + d.source_object_id) << "]";
    os << "}";
  }
  os << "],\n";
  os << "  \"statistics\":{";
  os << "\"visited_objects\":" << capture.visited_objects;
  os << ",\"visible_objects\":" << capture.visible_objects;
  os << ",\"culled_objects\":" << capture.culled_objects;
  os << ",\"cs_expanded_objects\":" << capture.cs_expanded_objects;
  os << ",\"commands\":" << capture.commands.size();
  os << ",\"command_type_counts\":";
  write_string_int_map(os, capture.command_type_counts);
  os << ",\"visible_class_counts\":";
  write_string_int_map(os, capture.visible_class_counts);
  os << ",\"culled_class_counts\":";
  write_string_int_map(os, capture.culled_class_counts);
  os << "}\n";
  os << "}\n";
}

static bool init_runtime() {
  wxImage::AddHandler(new wxPNGHandler);
  EnsureHeadlessGlobals();

  wxString s57 = ensure_slash(env_or_runtime("HELM_S57_DATA", "s57data"));
  wxString senc = ensure_slash(env_or_runtime("HELM_SENC_DIR", "senc"));
  wxString data_dir = s57;
  if (data_dir.EndsWith(wxT("/"))) data_dir.RemoveLast();
  data_dir = data_dir.BeforeLast('/') + wxT("/");

  ::wxFileName::Mkdir(senc, 0755, wxPATH_MKDIR_FULL);
  g_SENCPrefix = senc;
  g_csv_locn = s57;
  g_SData_Locn = data_dir;

  wxString rle = s57 + wxT("S52RAZDS.RLE");
  ps52plib = new s52plib(rle, false);
  if (!ps52plib || !ps52plib->m_bOK) {
    std::fprintf(stderr, "s52plib load failed: %s\n", (const char*)rle.ToUTF8());
    return false;
  }
  m_pRegistrarMan = new s57RegistrarMgr(s57, stderr);
  return true;
}

static int run_capture(const Options& opts) {
  if (!init_runtime()) return 2;

  ps52plib->SetPLIBColorScheme(opts.palette, ChartCtx(false, 0));
  ps52plib->SetDisplayCategory(opts.category);
  ps52plib->m_nSymbolStyle = opts.symbol_style;
  ps52plib->m_nBoundaryStyle = opts.boundary_style;
  ps52plib->SetShowS57Text(opts.show_text);
  ps52plib->SetShowSoundings(opts.show_soundings);
  ps52plib->m_bUseSCAMIN = opts.use_scamin;
  if (opts.has_safety_contour_override) {
    S52_setMarinerParam(S52_MAR_SAFETY_CONTOUR, opts.safety_contour_override);
    if (!opts.has_safety_depth_override)
      S52_setMarinerParam(S52_MAR_SAFETY_DEPTH,
                          opts.safety_contour_override);
  }
  if (opts.has_safety_depth_override)
    S52_setMarinerParam(S52_MAR_SAFETY_DEPTH, opts.safety_depth_override);

  SceneChart chart;
  chart.DisableBackgroundSENC();
  InitReturn init = chart.Init(wxString::FromUTF8(opts.enc_path.c_str()), FULL_INIT);
  if (init != INIT_OK) {
    std::fprintf(stderr, "chart Init failed for %s: %d\n", opts.enc_path.c_str(),
                 static_cast<int>(init));
    return 3;
  }
  chart.SetColorScheme(opts.palette);

  Extent extent;
  ViewPort vp = make_viewport(&chart, opts, &extent);

  wxBitmap bmp(opts.width, opts.height, BPP);
  if (!bmp.IsOk()) {
    std::fprintf(stderr, "wxBitmap(%d,%d,%d) failed\n", opts.width, opts.height, BPP);
    return 4;
  }
  wxMemoryDC dc(bmp);
  if (!dc.IsOk()) {
    std::fprintf(stderr, "wxMemoryDC failed\n");
    return 4;
  }
  OCPNRegion region(0, 0, opts.width, opts.height);
  bool rendered = chart.RenderRegionViewOnDCNoText(dc, vp, region);
  dc.SelectObject(wxNullBitmap);
  if (!rendered) {
    std::fprintf(stderr,
                 "warning: RenderRegionViewOnDCNoText returned false; emitting rule audit anyway\n");
  }

  SceneCapture capture;
  chart.CaptureScene(vp, opts, &capture);

  if (opts.output_path.empty() || opts.output_path == "-") {
    write_scene_json(std::cout, opts, chart, vp, extent, capture);
  } else {
    std::ofstream out(opts.output_path);
    if (!out) {
      std::fprintf(stderr, "cannot write %s\n", opts.output_path.c_str());
      return 5;
    }
    write_scene_json(out, opts, chart, vp, extent, capture);
  }
  std::fprintf(stderr,
               "helm-s52-scene: visited=%d visible=%d culled=%d commands=%zu cs=%d\n",
               capture.visited_objects, capture.visible_objects,
               capture.culled_objects, capture.commands.size(),
               capture.cs_expanded_objects);
  return 0;
}

class S52SceneApp : public wxApp {
public:
  int rc = 0;
  bool OnInit() override {
    SetAppName(wxT("opencpn"));
    std::vector<std::string> args;
    for (int i = 0; i < argc; ++i) args.push_back(wx_to_utf8(wxString(argv[i])));
    Options opts;
    if (!parse_options(args, &opts)) {
      usage();
      rc = 1;
      return false;
    }
    rc = run_capture(opts);
    return false;
  }
  int OnExit() override { return rc; }
};

}  // namespace

wxIMPLEMENT_APP_NO_MAIN(S52SceneApp);

int main(int argc, char** argv) {
  wxEntryStart(argc, argv);
  wxTheApp->CallOnInit();
  int rc = static_cast<S52SceneApp*>(wxTheApp)->rc;
  wxEntryCleanup();
  return rc;
}
