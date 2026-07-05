// RENDERMODEL-4/5 — ENC (.000 / S-57) -> vulkan.render_scene.v0 command-stream fixture.
// C++17 port of scripts/enc-to-render-fixture.py

#include "earcut.h"
#include "web_mercator.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <functional>
#include <limits>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <tuple>
#include <utility>
#include <variant>
#include <vector>

namespace {

constexpr const char* kOgrS57Options =
    "SPLIT_MULTIPOINT=ON,ADD_SOUNDG_DEPTH=ON,RETURN_PRIMITIVES=OFF,RETURN_LINKAGES=OFF,"
    "LNAM_REFS=OFF";

struct Category {
  const char* id;
  std::initializer_list<const char*> layers;
  const char* geom;  // poly | line | point
  const char* color;
  const char* ref;
  const char* ref_kind;  // pattern | line | symbol
  double hws;
};

constexpr Category kCategories[] = {
    {"depth_deep", {"DEPARE:deep"}, "poly", "#ecf5fb", "pattern.depare-deep", "pattern", 1.0},
    {"depth_mid", {"DEPARE:mid"}, "poly", "#cfe6f4", "pattern.depare-mid", "pattern", 1.0},
    {"depth_shallow", {"DEPARE:shallow"}, "poly", "#a9d3ea", "pattern.depare-shallow", "pattern", 1.0},
    {"dredged", {"DRGARE"}, "poly", "#cfe3ea", "pattern.dredged", "pattern", 1.0},
    {"land", {"LNDARE", "BUAARE"}, "poly", "#d9c7a6", "pattern.land", "pattern", 1.0},
    {"depth_contour", {"DEPCNT"}, "line", "#4a6f8a", "line.depth-contour", "line", 1.0},
    {"coastline", {"COALNE", "SLCONS"}, "line", "#5a4b30", "line.coastline", "line", 1.6},
    {"sounding", {"SOUNDG"}, "point", "#1b2a36", "sym.sounding", "symbol", 1.0},
    {"aid", {"BOYLAT", "BOYSAW", "BOYSPP", "BOYISD", "BOYCAR", "BCNLAT", "BCNSPP", "BCNCAR",
             "LIGHTS"},
     "point", "#f0a020", "sym.boyspp", "symbol", 1.0},
    {"hazard", {"UWTROC", "OBSTRN", "WRECKS", "ROCKS"}, "point", "#c8322d", "sym.hazard",
     "symbol", 1.0},
};

std::vector<std::string> base_layers() {
  std::set<std::string> layers;
  for (const Category& c : kCategories) {
    for (const char* spec : c.layers) {
      const std::string s(spec);
      layers.insert(s.substr(0, s.find(':')));
    }
  }
  return {layers.begin(), layers.end()};
}

struct Json;
using JsonArray = std::vector<Json>;
using JsonObject = std::map<std::string, Json>;

struct Json {
  using Storage = std::variant<std::nullptr_t, bool, double, std::string, JsonArray, JsonObject>;
  Storage value;

  [[nodiscard]] bool is_null() const { return std::holds_alternative<std::nullptr_t>(value); }
  [[nodiscard]] bool is_bool() const { return std::holds_alternative<bool>(value); }
  [[nodiscard]] bool is_number() const { return std::holds_alternative<double>(value); }
  [[nodiscard]] bool is_string() const { return std::holds_alternative<std::string>(value); }
  [[nodiscard]] bool is_array() const { return std::holds_alternative<JsonArray>(value); }
  [[nodiscard]] bool is_object() const { return std::holds_alternative<JsonObject>(value); }

  [[nodiscard]] const JsonObject& object() const {
    if (!is_object()) throw std::runtime_error("expected JSON object");
    return std::get<JsonObject>(value);
  }

  [[nodiscard]] const JsonArray& array() const {
    if (!is_array()) throw std::runtime_error("expected JSON array");
    return std::get<JsonArray>(value);
  }

  [[nodiscard]] const std::string& string() const {
    if (!is_string()) throw std::runtime_error("expected JSON string");
    return std::get<std::string>(value);
  }

  [[nodiscard]] double number() const {
    if (!is_number()) throw std::runtime_error("expected JSON number");
    return std::get<double>(value);
  }

  [[nodiscard]] bool boolean() const {
    if (!is_bool()) throw std::runtime_error("expected JSON bool");
    return std::get<bool>(value);
  }

  [[nodiscard]] const Json& at(std::string_view key) const {
    const auto& obj = object();
    const auto it = obj.find(std::string(key));
    if (it == obj.end()) throw std::runtime_error("missing JSON key: " + std::string(key));
    return it->second;
  }

  [[nodiscard]] const Json* get(std::string_view key) const {
    if (!is_object()) return nullptr;
    const auto it = object().find(std::string(key));
    return it == object().end() ? nullptr : &it->second;
  }
};

class JsonParser {
 public:
  explicit JsonParser(std::string text) : text_(std::move(text)) {}

  Json parse() {
    Json out = parse_value();
    skip_ws();
    if (pos_ != text_.size()) throw error("trailing data");
    return out;
  }

 private:
  [[nodiscard]] std::runtime_error error(std::string_view message) const {
    return std::runtime_error("JSON parse error at byte " + std::to_string(pos_) + ": " +
                              std::string(message));
  }

  void skip_ws() {
    while (pos_ < text_.size()) {
      const char ch = text_[pos_];
      if (ch != ' ' && ch != '\n' && ch != '\r' && ch != '\t') break;
      ++pos_;
    }
  }

  [[nodiscard]] char peek() {
    skip_ws();
    if (pos_ >= text_.size()) throw error("unexpected end of input");
    return text_[pos_];
  }

  [[nodiscard]] bool consume(char ch) {
    skip_ws();
    if (pos_ < text_.size() && text_[pos_] == ch) {
      ++pos_;
      return true;
    }
    return false;
  }

  void expect(char ch) {
    if (!consume(ch)) throw error(std::string("expected '") + ch + "'");
  }

  [[nodiscard]] Json parse_value() {
    const char ch = peek();
    if (ch == '{') return Json{parse_object()};
    if (ch == '[') return Json{parse_array()};
    if (ch == '"') return Json{parse_string()};
    if (ch == 't') return parse_literal("true", Json{true});
    if (ch == 'f') return parse_literal("false", Json{false});
    if (ch == 'n') return parse_literal("null", Json{nullptr});
    if (ch == '-' || (ch >= '0' && ch <= '9')) return Json{parse_number()};
    throw error("unexpected value");
  }

  [[nodiscard]] Json parse_literal(std::string_view literal, Json value) {
    if (text_.compare(pos_, literal.size(), literal) != 0) throw error("invalid literal");
    pos_ += literal.size();
    return value;
  }

  [[nodiscard]] JsonObject parse_object() {
    expect('{');
    JsonObject obj;
    if (consume('}')) return obj;
    while (true) {
      if (peek() != '"') throw error("expected object key");
      std::string key = parse_string();
      expect(':');
      obj.emplace(std::move(key), parse_value());
      if (consume('}')) return obj;
      expect(',');
    }
  }

  [[nodiscard]] JsonArray parse_array() {
    expect('[');
    JsonArray arr;
    if (consume(']')) return arr;
    while (true) {
      arr.push_back(parse_value());
      if (consume(']')) return arr;
      expect(',');
    }
  }

  [[nodiscard]] std::string parse_string() {
    expect('"');
    std::string out;
    while (pos_ < text_.size()) {
      const unsigned char ch = static_cast<unsigned char>(text_[pos_++]);
      if (ch == '"') return out;
      if (ch != '\\') {
        if (ch < 0x20) throw error("control character in string");
        out.push_back(static_cast<char>(ch));
        continue;
      }
      if (pos_ >= text_.size()) throw error("bad escape");
      const char esc = text_[pos_++];
      switch (esc) {
        case '"': out.push_back('"'); break;
        case '\\': out.push_back('\\'); break;
        case '/': out.push_back('/'); break;
        case 'b': out.push_back('\b'); break;
        case 'f': out.push_back('\f'); break;
        case 'n': out.push_back('\n'); break;
        case 'r': out.push_back('\r'); break;
        case 't': out.push_back('\t'); break;
        case 'u': {
          if (pos_ + 4 > text_.size()) throw error("bad unicode escape");
          const int code = std::stoi(text_.substr(pos_, 4), nullptr, 16);
          pos_ += 4;
          if (code < 0x80) {
            out.push_back(static_cast<char>(code));
          } else {
            out.push_back('?');
          }
          break;
        }
        default: throw error("bad escape");
      }
    }
    throw error("unterminated string");
  }

  [[nodiscard]] double parse_number() {
    const std::size_t start = pos_;
    if (text_[pos_] == '-') ++pos_;
    while (pos_ < text_.size() && std::isdigit(static_cast<unsigned char>(text_[pos_]))) ++pos_;
    if (pos_ < text_.size() && text_[pos_] == '.') {
      ++pos_;
      while (pos_ < text_.size() && std::isdigit(static_cast<unsigned char>(text_[pos_]))) ++pos_;
    }
    if (pos_ < text_.size() && (text_[pos_] == 'e' || text_[pos_] == 'E')) {
      ++pos_;
      if (pos_ < text_.size() && (text_[pos_] == '+' || text_[pos_] == '-')) ++pos_;
      while (pos_ < text_.size() && std::isdigit(static_cast<unsigned char>(text_[pos_]))) ++pos_;
    }
    return std::stod(text_.substr(start, pos_ - start));
  }

  std::string text_;
  std::size_t pos_ = 0;
};

[[nodiscard]] std::string number_to_string(double value) {
  if (value == 0.0) value = 0.0;
  std::ostringstream out;
  out << std::setprecision(15) << value;
  return out.str();
}

void indent(std::ostream& out, int depth) {
  for (int i = 0; i < depth; ++i) out << "  ";
}

void write_string(std::ostream& out, const std::string& value) {
  out << '"';
  for (const unsigned char c : value) {
    switch (c) {
      case '"': out << "\\\""; break;
      case '\\': out << "\\\\"; break;
      case '\b': out << "\\b"; break;
      case '\f': out << "\\f"; break;
      case '\n': out << "\\n"; break;
      case '\r': out << "\\r"; break;
      case '\t': out << "\\t"; break;
      default:
        if (c < 0x20) {
          out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << static_cast<int>(c)
              << std::dec << std::setfill(' ');
        } else {
          out << static_cast<char>(c);
        }
    }
  }
  out << '"';
}

void write_key(std::ostream& out, int depth, const std::string& key) {
  indent(out, depth);
  write_string(out, key);
  out << ": ";
}

void write_number(std::ostream& out, double value) { out << number_to_string(value); }

void write_null(std::ostream& out) { out << "null"; }

void write_json(std::ostream& out, const Json& value, int depth);

void write_json_array(std::ostream& out, const JsonArray& arr, int depth) {
  out << "[";
  if (!arr.empty()) out << "\n";
  for (std::size_t i = 0; i < arr.size(); ++i) {
    indent(out, depth + 1);
    write_json(out, arr[i], depth + 1);
    out << (i + 1 < arr.size() ? ",\n" : "\n");
  }
  if (!arr.empty()) indent(out, depth);
  out << "]";
}

void write_json_object(std::ostream& out, const JsonObject& obj, int depth) {
  out << "{";
  if (!obj.empty()) out << "\n";
  std::size_t i = 0;
  for (const auto& [key, val] : obj) {
    write_key(out, depth + 1, key);
    write_json(out, val, depth + 1);
    out << (++i < obj.size() ? ",\n" : "\n");
  }
  if (!obj.empty()) indent(out, depth);
  out << "}";
}

void write_json(std::ostream& out, const Json& value, int depth) {
  if (value.is_null()) {
    write_null(out);
  } else if (value.is_bool()) {
    out << (value.boolean() ? "true" : "false");
  } else if (value.is_number()) {
    write_number(out, value.number());
  } else if (value.is_string()) {
    write_string(out, value.string());
  } else if (value.is_array()) {
    write_json_array(out, value.array(), depth);
  } else if (value.is_object()) {
    write_json_object(out, value.object(), depth);
  }
}

[[nodiscard]] std::string read_file(const std::filesystem::path& path) {
  std::ifstream in(path);
  if (!in) throw std::runtime_error("cannot read " + path.string());
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

void write_file(const std::filesystem::path& path, const std::string& content) {
  std::ofstream out(path);
  if (!out) throw std::runtime_error("cannot write " + path.string());
  out << content;
  if (!content.empty() && content.back() != '\n') out << '\n';
}

[[nodiscard]] std::string shell_quote(const std::string& s) {
  std::string out = "'";
  for (const char c : s) {
    if (c == '\'') {
      out += "'\\''";
    } else {
      out += c;
    }
  }
  out += "'";
  return out;
}

[[nodiscard]] bool command_exists(const char* cmd) {
  const std::string probe = std::string("command -v ") + cmd + " >/dev/null 2>&1";
  return std::system(probe.c_str()) == 0;
}

[[nodiscard]] bool run_ogr2ogr(const std::filesystem::path& enc, const std::string& layer,
                               const std::filesystem::path& out_geojson) {
#if defined(_WIN32)
  _putenv_s("OGR_S57_OPTIONS", kOgrS57Options);
#else
  setenv("OGR_S57_OPTIONS", kOgrS57Options, 1);
#endif
  const std::string cmd = "ogr2ogr -f GeoJSON -t_srs EPSG:4326 " + shell_quote(out_geojson.string()) +
                          " " + shell_quote(enc.string()) + " " + layer + " 2>/dev/null";
  if (std::system(cmd.c_str()) != 0) return false;
  return std::filesystem::exists(out_geojson) && std::filesystem::file_size(out_geojson) > 0;
}

using LonLat = std::pair<double, double>;
using PixelPt = std::pair<double, double>;
using IntPt = std::pair<int, int>;
using Ring = std::vector<IntPt>;

[[nodiscard]] std::optional<LonLat> coord_lonlat(const Json& coord) {
  if (!coord.is_array() || coord.array().size() < 2) return std::nullopt;
  return LonLat{coord.array()[0].number(), coord.array()[1].number()};
}

void for_each_polygon(const Json& geom,
                      const std::function<void(const JsonArray&, const std::vector<JsonArray>&)>& fn) {
  if (!geom.is_object()) return;
  const Json* type = geom.get("type");
  const Json* coords = geom.get("coordinates");
  if (!type || !coords || !coords->is_array()) return;
  const std::string& t = type->string();
  if (t == "Polygon") {
    if (!coords->array().empty()) {
      std::vector<JsonArray> holes;
      for (std::size_t i = 1; i < coords->array().size(); ++i) holes.push_back(coords->array()[i].array());
      fn(coords->array()[0].array(), holes);
    }
  } else if (t == "MultiPolygon") {
    for (const Json& poly : coords->array()) {
      if (poly.array().empty()) continue;
      std::vector<JsonArray> holes;
      for (std::size_t i = 1; i < poly.array().size(); ++i) holes.push_back(poly.array()[i].array());
      fn(poly.array()[0].array(), holes);
    }
  }
}

void for_each_line(const Json& geom, const std::function<void(const JsonArray&)>& fn) {
  if (!geom.is_object()) return;
  const Json* type = geom.get("type");
  const Json* coords = geom.get("coordinates");
  if (!type || !coords || !coords->is_array()) return;
  const std::string& t = type->string();
  if (t == "LineString") {
    fn(coords->array());
  } else if (t == "MultiLineString") {
    for (const Json& line : coords->array()) fn(line.array());
  } else if (t == "Polygon") {
    for (const Json& ring : coords->array()) fn(ring.array());
  } else if (t == "MultiPolygon") {
    for (const Json& poly : coords->array()) {
      for (const Json& ring : poly.array()) fn(ring.array());
    }
  }
}

void for_each_point(const Json& geom, const std::function<void(const Json&)>& fn) {
  if (!geom.is_object()) return;
  const Json* type = geom.get("type");
  const Json* coords = geom.get("coordinates");
  if (!type || !coords) return;
  const std::string& t = type->string();
  if (t == "Point") {
    fn(*coords);
  } else if (t == "MultiPoint") {
    for (const Json& p : coords->array()) fn(p);
  }
}

[[nodiscard]] int ri(double v) { return static_cast<int>(std::lround(v)); }

[[nodiscard]] std::optional<Ring> seg_quad(double x0, double y0, double x1, double y1, double half_px) {
  const double dx = x1 - x0;
  const double dy = y1 - y0;
  const double n = std::hypot(dx, dy);
  if (n < 1e-9) return std::nullopt;
  const double nx = -dy / n * half_px;
  const double ny = dx / n * half_px;
  return Ring{{ri(x0 + nx), ri(y0 + ny)},
              {ri(x1 + nx), ri(y1 + ny)},
              {ri(x1 - nx), ri(y1 - ny)},
              {ri(x0 - nx), ri(y0 - ny)},
              {ri(x0 + nx), ri(y0 + ny)}};
}

[[nodiscard]] Ring dot_square(double x, double y, double half_px) {
  const int xi = ri(x);
  const int yi = ri(y);
  const int h = std::max(1, ri(half_px));
  return Ring{{xi - h, yi - h}, {xi + h, yi - h}, {xi + h, yi + h}, {xi - h, yi + h},
              {xi - h, yi - h}};
}

[[nodiscard]] std::optional<Ring> tri_ring(const helm::earcut::Triangle& tri) {
  Ring ring{{ri(tri[0].x), ri(tri[0].y)},
            {ri(tri[1].x), ri(tri[1].y)},
            {ri(tri[2].x), ri(tri[2].y)}};
  const int ax = ring[0].first, ay = ring[0].second;
  const int bx = ring[1].first, by = ring[1].second;
  const int cx = ring[2].first, cy = ring[2].second;
  if (std::abs((bx - ax) * (cy - ay) - (cx - ax) * (by - ay)) < 1) return std::nullopt;
  return ring;
}

[[nodiscard]] std::vector<PixelPt> simplify(const std::vector<PixelPt>& pts, double tol) {
  if (tol <= 0 || pts.size() < 3) return pts;
  std::vector<bool> keep(pts.size(), false);
  keep.front() = keep.back() = true;
  std::vector<std::pair<std::size_t, std::size_t>> stack{{0, pts.size() - 1}};
  while (!stack.empty()) {
    const auto [a, b] = stack.back();
    stack.pop_back();
    if (b <= a + 1) continue;
    const double ax = pts[a].first, ay = pts[a].second;
    const double bx = pts[b].first, by = pts[b].second;
    const double dx = bx - ax, dy = by - ay;
    const double seglen = std::hypot(dx, dy);
    double dmax = -1.0;
    std::size_t idx = 0;
    for (std::size_t i = a + 1; i < b; ++i) {
      const double px = pts[i].first, py = pts[i].second;
      const double d = seglen < 1e-9 ? std::hypot(px - ax, py - ay)
                                     : std::abs(dy * px - dx * py + bx * ay - by * ax) / seglen;
      if (d > dmax) {
        dmax = d;
        idx = i;
      }
    }
    if (dmax > tol && idx > 0) {
      keep[idx] = true;
      stack.emplace_back(a, idx);
      stack.emplace_back(idx, b);
    }
  }
  std::vector<PixelPt> out;
  for (std::size_t i = 0; i < pts.size(); ++i) {
    if (keep[i]) out.push_back(pts[i]);
  }
  return out;
}

[[nodiscard]] std::string depare_band(const JsonObject& props, double safety_contour) {
  double v = 0.0;
  const auto it = props.find("DRVAL1");
  if (it != props.end() && it->second.is_number()) v = it->second.number();
  if (v < safety_contour * 0.5) return "shallow";
  if (v < safety_contour * 2.0) return "mid";
  return "deep";
}

struct LayerTarget {
  std::string cid;
  std::optional<std::string> band;
  std::string kind;
  double hws;
};

[[nodiscard]] std::map<std::string, std::vector<LayerTarget>> build_layer_targets() {
  std::map<std::string, std::vector<LayerTarget>> out;
  for (const Category& c : kCategories) {
    for (const char* spec : c.layers) {
      const std::string s(spec);
      const std::size_t colon = s.find(':');
      const std::string base = s.substr(0, colon);
      std::optional<std::string> band;
      if (colon != std::string::npos) band = s.substr(colon + 1);
      out[base].push_back({c.id, band, c.geom, c.hws});
    }
  }
  return out;
}

[[nodiscard]] Json ring_to_json(const Ring& ring) {
  JsonArray arr;
  for (const IntPt& p : ring) {
    arr.push_back(Json{JsonArray{Json{static_cast<double>(p.first)}, Json{static_cast<double>(p.second)}}});
  }
  return Json{arr};
}

[[nodiscard]] Json rings_to_json(const std::vector<Ring>& rings) {
  JsonArray arr;
  for (const Ring& ring : rings) arr.push_back(ring_to_json(ring));
  return Json{arr};
}

struct Options {
  std::filesystem::path enc;
  std::filesystem::path out_dir;
  std::string cell_id;
  int pixel_size = 2048;
  std::string palette = "day";
  std::string display_category = "standard";
  double safety_depth = 10.0;
  double safety_contour = 10.0;
  double half_width_px = 1.4;
  double point_size_px = 2.6;
  double simplify_px = 1.0;
  int reference_zoom = 13;
  std::optional<int> tile_z;
  std::optional<int> tile_x;
  std::optional<int> tile_y;
  std::optional<std::string> bbox;
};

[[nodiscard]] Options parse_args(int argc, char** argv) {
  Options opt;
  if (argc < 3) throw std::runtime_error("usage");
  opt.enc = argv[1];
  opt.out_dir = argv[2];
  for (int i = 3; i < argc; ++i) {
    const std::string arg = argv[i];
    auto need = [&](const char* flag) -> std::string {
      if (i + 1 >= argc) throw std::runtime_error(std::string(flag) + " requires a value");
      return argv[++i];
    };
    if (arg == "--cell-id") {
      opt.cell_id = need("--cell-id");
    } else if (arg == "--pixel-size") {
      opt.pixel_size = std::stoi(need("--pixel-size"));
    } else if (arg == "--palette") {
      opt.palette = need("--palette");
    } else if (arg == "--display-category") {
      opt.display_category = need("--display-category");
    } else if (arg == "--safety-depth") {
      opt.safety_depth = std::stod(need("--safety-depth"));
    } else if (arg == "--safety-contour") {
      opt.safety_contour = std::stod(need("--safety-contour"));
    } else if (arg == "--half-width-px") {
      opt.half_width_px = std::stod(need("--half-width-px"));
    } else if (arg == "--point-size-px") {
      opt.point_size_px = std::stod(need("--point-size-px"));
    } else if (arg == "--simplify-px") {
      opt.simplify_px = std::stod(need("--simplify-px"));
    } else if (arg == "--reference-zoom") {
      opt.reference_zoom = std::stoi(need("--reference-zoom"));
    } else if (arg == "--tile-z") {
      opt.tile_z = std::stoi(need("--tile-z"));
    } else if (arg == "--tile-x") {
      opt.tile_x = std::stoi(need("--tile-x"));
    } else if (arg == "--tile-y") {
      opt.tile_y = std::stoi(need("--tile-y"));
    } else if (arg == "--bbox") {
      opt.bbox = need("--bbox");
    } else {
      throw std::runtime_error("unknown arg: " + arg);
    }
  }
  return opt;
}

void acc_bbox(double lon, double lat, double& west, double& south, double& east, double& north) {
  west = std::min(west, lon);
  east = std::max(east, lon);
  south = std::min(south, lat);
  north = std::max(north, lat);
}

[[nodiscard]] bool feature_intersects_tile(const Json& geom, double west, double south, double east,
                                           double north) {
  double fw = std::numeric_limits<double>::infinity();
  double fe = -std::numeric_limits<double>::infinity();
  double fs = std::numeric_limits<double>::infinity();
  double fn = -std::numeric_limits<double>::infinity();
  bool any = false;
  for_each_line(geom, [&](const JsonArray& line) {
    for (const Json& p : line) {
      if (auto ll = coord_lonlat(p)) {
        acc_bbox(ll->first, ll->second, fw, fs, fe, fn);
        any = true;
      }
    }
  });
  for_each_point(geom, [&](const Json& p) {
    if (auto ll = coord_lonlat(p)) {
      acc_bbox(ll->first, ll->second, fw, fs, fe, fn);
      any = true;
    }
  });
  if (!any) return false;
  return !(fe < west || fw > east || fn < south || fs > north);
}

}  // namespace

int main(int argc, char** argv) {
  try {
    Options opt = parse_args(argc, argv);
    opt.enc = std::filesystem::absolute(opt.enc);
    if (!std::filesystem::exists(opt.enc)) {
      std::cerr << "ENC not found: " << opt.enc << "\n";
      return 2;
    }
    if (!command_exists("ogr2ogr")) {
      std::cerr << "ogr2ogr (GDAL) not found on PATH — install GDAL first\n";
      return 3;
    }

    if (opt.cell_id.empty()) {
      opt.cell_id = opt.enc.stem().string();
    }
    opt.out_dir = std::filesystem::absolute(opt.out_dir);
    std::filesystem::create_directories(opt.out_dir);

    const std::filesystem::path tmp =
        std::filesystem::temp_directory_path() / ("enc-extract-" + opt.cell_id);
    std::filesystem::create_directories(tmp);

    std::map<std::string, JsonArray> layer_features;
    for (const std::string& layer : base_layers()) {
      const std::filesystem::path gj = tmp / (layer + ".geojson");
      if (!run_ogr2ogr(opt.enc, layer, gj)) continue;
      const Json root = JsonParser(read_file(gj)).parse();
      const Json* feats = root.get("features");
      if (!feats || !feats->is_array() || feats->array().empty()) continue;
      layer_features[layer] = feats->array();
      std::cerr << "  " << layer << ": " << feats->array().size() << " features\n";
    }
    if (layer_features.empty()) {
      std::cerr << "No usable layers extracted from ENC\n";
      std::filesystem::remove_all(tmp);
      return 4;
    }

    std::optional<int> tile_z = opt.tile_z;
    std::optional<int> tile_x = opt.tile_x;
    std::optional<int> tile_y = opt.tile_y;
    double west = 0, south = 0, east = 0, north = 0;

    if (tile_z.has_value()) {
      if (!tile_x.has_value() || !tile_y.has_value()) {
        std::cerr << "--tile-z requires --tile-x and --tile-y\n";
        return 2;
      }
      const helm::webmerc::Bbox bb = helm::webmerc::num2bbox(*tile_z, *tile_x, *tile_y);
      west = bb.west;
      south = bb.south;
      east = bb.east;
      north = bb.north;
    } else if (opt.bbox.has_value()) {
      std::istringstream ss(*opt.bbox);
      char comma;
      ss >> west >> comma >> south >> comma >> east >> comma >> north;
    } else {
      west = std::numeric_limits<double>::infinity();
      south = std::numeric_limits<double>::infinity();
      east = -std::numeric_limits<double>::infinity();
      north = -std::numeric_limits<double>::infinity();
      for (const auto& [layer, feats] : layer_features) {
        (void)layer;
        for (const Json& ft : feats) {
          const Json* geom = ft.get("geometry");
          if (!geom) continue;
          for_each_line(*geom, [&](const JsonArray& line) {
            for (const Json& p : line) {
              if (auto ll = coord_lonlat(p)) acc_bbox(ll->first, ll->second, west, south, east, north);
            }
          });
          for_each_point(*geom, [&](const Json& p) {
            if (auto ll = coord_lonlat(p)) acc_bbox(ll->first, ll->second, west, south, east, north);
          });
        }
      }
      const double dlon = (east - west) * 0.02;
      const double dlat = (north - south) * 0.02;
      west -= dlon ? dlon : 0.001;
      east += dlon ? dlon : 0.001;
      south -= dlat ? dlat : 0.001;
      north += dlat ? dlat : 0.001;
    }

    if (!(east > west && north > south)) {
      std::cerr << "Degenerate bbox\n";
      std::filesystem::remove_all(tmp);
      return 5;
    }

    const int pw = opt.pixel_size;
    const int ph = pw;
    double simplify_px = opt.simplify_px;
    if (tile_z.has_value() && opt.simplify_px > 0) {
      simplify_px = opt.simplify_px * std::pow(2.0, opt.reference_zoom - *tile_z);
    }

    const auto project = [&](double lon, double lat) -> PixelPt {
      return {(lon - west) / (east - west) * pw, (north - lat) / (north - south) * ph};
    };

    const double hw_px = opt.half_width_px;
    const double pt_px = opt.point_size_px;
    std::map<std::string, std::vector<Ring>> cat_rings;
    std::map<std::string, int> cat_counts;
    for (const Category& c : kCategories) {
      cat_rings[c.id] = {};
      cat_counts[c.id] = 0;
    }

    const auto layer_targets = build_layer_targets();

    for (const auto& [layer, feats] : layer_features) {
      const auto targets_it = layer_targets.find(layer);
      if (targets_it == layer_targets.end()) continue;
      for (const Json& ft : feats) {
        const Json* geom = ft.get("geometry");
        if (!geom) continue;
        if (tile_z.has_value() &&
            !feature_intersects_tile(*geom, west, south, east, north)) {
          continue;
        }
        const JsonObject* props = nullptr;
        if (const Json* p = ft.get("properties"); p && p->is_object()) props = &p->object();
        const std::string band = (layer == "DEPARE" && props) ? depare_band(*props, opt.safety_contour)
                                                              : std::string{};

        for (const LayerTarget& target : targets_it->second) {
          if (target.band.has_value() && *target.band != band) continue;
          bool added = false;
          if (target.kind == "poly") {
            for_each_polygon(*geom, [&](const JsonArray& exterior, const std::vector<JsonArray>& holes) {
              std::vector<PixelPt> ext_pts;
              for (const Json& p : exterior) {
                if (auto ll = coord_lonlat(p)) ext_pts.push_back(project(ll->first, ll->second));
              }
              ext_pts = simplify(ext_pts, simplify_px);
              if (ext_pts.size() < 3) return;
              helm::earcut::Ring ext;
              for (const PixelPt& p : ext_pts) ext.push_back({p.first, p.second});
              std::vector<helm::earcut::Ring> hs;
              for (const JsonArray& hole : holes) {
                std::vector<PixelPt> hp;
                for (const Json& p : hole) {
                  if (auto ll = coord_lonlat(p)) hp.push_back(project(ll->first, ll->second));
                }
                hp = simplify(hp, simplify_px);
                if (hp.size() < 3) continue;
                helm::earcut::Ring hr;
                for (const PixelPt& p : hp) hr.push_back({p.first, p.second});
                hs.push_back(std::move(hr));
              }
              for (const helm::earcut::Triangle& tri : helm::earcut::triangulate_rings(ext, hs)) {
                if (auto ring = tri_ring(tri)) {
                  cat_rings[target.cid].push_back(*ring);
                  added = true;
                }
              }
            });
          } else if (target.kind == "line") {
            for_each_line(*geom, [&](const JsonArray& line) {
              std::vector<PixelPt> pts;
              for (const Json& p : line) {
                if (auto ll = coord_lonlat(p)) pts.push_back(project(ll->first, ll->second));
              }
              pts = simplify(pts, simplify_px);
              for (std::size_t i = 0; i + 1 < pts.size(); ++i) {
                if (auto q = seg_quad(pts[i].first, pts[i].second, pts[i + 1].first, pts[i + 1].second,
                                      hw_px * target.hws)) {
                  cat_rings[target.cid].push_back(*q);
                  added = true;
                }
              }
            });
          } else if (target.kind == "point") {
            for_each_point(*geom, [&](const Json& p) {
              if (auto ll = coord_lonlat(p)) {
                const PixelPt xy = project(ll->first, ll->second);
                cat_rings[target.cid].push_back(dot_square(xy.first, xy.second, pt_px));
                added = true;
              }
            });
          }
          if (added) ++cat_counts[target.cid];
        }
      }
    }

    const std::string scene_id = opt.cell_id + "-" + opt.palette + "-" + opt.display_category;
    const double center_lon = (west + east) / 2.0;
    const double center_lat = (south + north) / 2.0;

    int z = 0, tx = 0, ty = 0;
    if (tile_z.has_value()) {
      z = *tile_z;
      tx = *tile_x;
      ty = *tile_y;
    } else {
      z = opt.reference_zoom;
      const int n_tiles = 1 << z;
      tx = static_cast<int>((center_lon + 180.0) / 360.0 * n_tiles);
      const double lat_rad = center_lat * 3.14159265358979323846 / 180.0;
      ty = static_cast<int>((1.0 - std::asinh(std::tan(lat_rad)) / 3.14159265358979323846) / 2.0 *
                            n_tiles);
    }

    JsonArray command_groups;
    JsonArray provenance_table;
    JsonArray source_objects;
    int priority = 0;

    for (const Category& c : kCategories) {
      const std::vector<Ring>& rings = cat_rings[c.id];
      if (rings.empty()) continue;
      const std::string prov_id = "prov." + std::string(c.id);
      JsonObject cmd;
      cmd["type"] = Json{"fill_area"};
      cmd["command_id"] = Json{"cmd.area." + std::string(c.id)};
      cmd["rings"] = rings_to_json(rings);
      cmd["coordinate_space"] = Json{"target"};
      JsonObject fill;
      fill["palette_ref"] = Json{"palette." + opt.palette};
      fill["color"] = Json{std::string(c.color)};
      cmd["fill"] = Json{fill};
      cmd["symbol_ref"] = Json{c.ref_kind == std::string("symbol") ? Json{std::string(c.ref)} : Json{nullptr}};
      cmd["line_style_ref"] =
          Json{c.ref_kind == std::string("line") ? Json{std::string(c.ref)} : Json{nullptr}};
      cmd["pattern_ref"] =
          Json{c.ref_kind == std::string("pattern") ? Json{std::string(c.ref)} : Json{nullptr}};
      cmd["opacity"] = Json{1.0};
      cmd["clip_ref"] = Json{nullptr};
      cmd["provenance_refs"] = Json{JsonArray{Json{prov_id}}};

      JsonObject group;
      group["group_id"] = Json{"s52-" + std::string(c.id)};
      group["chart_priority"] = Json{static_cast<double>(priority)};
      group["s52_layer"] = Json{"area"};
      group["quilt_rank"] = Json{static_cast<double>(priority)};
      group["commands"] = Json{JsonArray{Json{cmd}}};
      command_groups.push_back(Json{group});

      JsonObject prov;
      prov["provenance_id"] = Json{prov_id};
      prov["source_chart_id"] = Json{opt.cell_id};
      provenance_table.push_back(Json{prov});

      std::string geom_type = "point";
      if (std::string(c.geom) == "poly") geom_type = "polygon";
      else if (std::string(c.geom) == "line") geom_type = "line";
      const std::string layer0 = [&]() {
        std::string s(c.layers.begin()[0]);
        const std::size_t colon = s.find(':');
        return colon == std::string::npos ? s : s.substr(0, colon);
      }();
      JsonObject so;
      so["source_object_id"] = Json{std::string(c.id) + "-GROUP"};
      so["source_object_class"] = Json{layer0};
      so["geometry_type"] = Json{geom_type};
      so["feature_count"] = Json{static_cast<double>(cat_counts[c.id])};
      so["convex_ring_count"] = Json{static_cast<double>(rings.size())};
      source_objects.push_back(Json{so});

      ++priority;
    }

    if (command_groups.empty()) {
      std::cerr << "No drawable geometry produced\n";
      std::filesystem::remove_all(tmp);
      return 6;
    }

    JsonObject resource_table;
    JsonArray symbols, line_styles, area_patterns;
    for (const Category& c : kCategories) {
      if (std::string(c.ref_kind) == "symbol") {
        JsonObject r;
        r["resource_id"] = Json{std::string(c.ref)};
        r["source"] = Json{"s52-atlas"};
        symbols.push_back(Json{r});
      } else if (std::string(c.ref_kind) == "line") {
        JsonObject r;
        r["resource_id"] = Json{std::string(c.ref)};
        r["source"] = Json{"s52-atlas"};
        line_styles.push_back(Json{r});
      } else if (std::string(c.ref_kind) == "pattern") {
        JsonObject r;
        r["resource_id"] = Json{std::string(c.ref)};
        r["source"] = Json{"s52-atlas"};
        area_patterns.push_back(Json{r});
      }
    }
    resource_table["symbols"] = Json{symbols};
    resource_table["line_styles"] = Json{line_styles};
    resource_table["area_patterns"] = Json{area_patterns};
    JsonObject font;
    font["resource_id"] = Json{"font.chart-label"};
    font["family"] = Json{"chart-sans"};
    font["size_px"] = Json{11.0};
    resource_table["fonts"] = Json{JsonArray{Json{font}}};
    resource_table["raster_textures"] = Json{JsonArray{}};
    resource_table["geometry_buffers"] = Json{JsonArray{}};
    JsonObject palette_res;
    palette_res["resource_id"] = Json{"palette." + opt.palette};
    palette_res["name"] = Json{opt.palette};
    resource_table["palettes"] = Json{JsonArray{Json{palette_res}}};

    JsonObject render_view;
    render_view["projection"] = Json{"web_mercator_tile"};
    JsonObject geo_bbox;
    geo_bbox["west"] = Json{west};
    geo_bbox["south"] = Json{south};
    geo_bbox["east"] = Json{east};
    geo_bbox["north"] = Json{north};
    render_view["geographic_bbox"] = Json{geo_bbox};
    JsonObject center;
    center["lon"] = Json{center_lon};
    center["lat"] = Json{center_lat};
    render_view["center"] = Json{center};
    render_view["scale_denom"] = Json{20000.0};
    render_view["rotation_deg"] = Json{0.0};
    render_view["pixel_size"] = Json{JsonArray{Json{static_cast<double>(pw)}, Json{static_cast<double>(ph)}}};
    render_view["device_pixel_ratio"] = Json{1.0};
    render_view["overzoom"] = Json{false};
    render_view["overscan_px"] = Json{0.0};

    JsonObject display_state;
    display_state["palette"] = Json{opt.palette};
    display_state["display_category"] = Json{opt.display_category};
    display_state["safety_depth_m"] = Json{opt.safety_depth};
    display_state["shallow_contour_m"] = Json{opt.safety_contour * 0.5};
    display_state["safety_contour_m"] = Json{opt.safety_contour};
    display_state["deep_contour_m"] = Json{opt.safety_contour * 2.0};
    display_state["show_text"] = Json{true};
    display_state["show_soundings"] = Json{true};
    display_state["show_lights"] = Json{true};
    display_state["simplified_symbols"] = Json{false};
    display_state["two_shade_depth"] = Json{false};
    display_state["language"] = Json{"en"};
    display_state["units"] = Json{"metric"};

    JsonObject scene;
    scene["schema_version"] = Json{"vulkan.render_scene.v0"};
    scene["scene_id"] = Json{scene_id};
    scene["source_epoch"] = Json{opt.cell_id + "@enc"};
    scene["render_view"] = Json{render_view};
    scene["display_state"] = Json{display_state};
    scene["resource_table"] = Json{resource_table};
    scene["command_groups"] = Json{command_groups};
    scene["provenance_table"] = Json{provenance_table};
    JsonObject diag;
    diag["severity"] = Json{"info"};
    diag["code"] = Json{"capture.real_enc"};
    diag["message"] = Json{"Real NOAA ENC cell " + opt.cell_id +
                         " captured via GDAL/OGR S-57 with earcut area fills (RENDERMODEL-4)."};
    diag["provenance_refs"] = Json{JsonArray{}};
    diag["suggested_action"] = Json{""};
    scene["diagnostics"] = Json{JsonArray{Json{diag}}};

    JsonObject source;
    source["fixture_id"] = Json{opt.cell_id};
    source["source_epoch"] = Json{opt.cell_id + "@enc"};
    source["source_type"] = Json{"enc_s57"};
    JsonObject chart;
    chart["source_chart_id"] = Json{opt.cell_id};
    chart["source_chart_edition"] = Json{"1"};
    chart["source_update"] = Json{"0"};
    chart["native_scale"] = Json{20000.0};
    JsonObject bounds;
    bounds["west"] = Json{west};
    bounds["south"] = Json{south};
    bounds["east"] = Json{east};
    bounds["north"] = Json{north};
    chart["bounds"] = Json{bounds};
    chart["objects"] = Json{source_objects};
    source["charts"] = Json{JsonArray{Json{chart}}};

    JsonArray prov_doc_table;
    for (const Json& p : provenance_table) {
      const std::string prov_id = p.at("provenance_id").string();
      const std::string cid = prov_id.substr(5);
      const Category* cat = nullptr;
      for (const Category& c : kCategories) {
        if (c.id == cid) {
          cat = &c;
          break;
        }
      }
      std::string layer0 = cat ? std::string(*cat->layers.begin()) : cid;
      const std::size_t colon = layer0.find(':');
      if (colon != std::string::npos) layer0 = layer0.substr(0, colon);
      JsonObject row;
      row["provenance_id"] = Json{prov_id};
      row["source_chart_id"] = Json{opt.cell_id};
      row["source_chart_edition"] = Json{"1"};
      row["source_update"] = Json{"0"};
      std::string obj_id = prov_id.substr(5);
      std::transform(obj_id.begin(), obj_id.end(), obj_id.begin(),
                     [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
      row["source_object_id"] = Json{obj_id + "-GROUP"};
      row["source_object_class"] = Json{layer0};
      row["source_geometry_hash"] = Json{"enc-ogr-" + prov_id.substr(5)};
      row["conversion_stage"] = Json{"enc-ogr-capture"};
      row["transform_chain"] =
          Json{JsonArray{Json{"wgs84"}, Json{"web-mercator"}, Json{"target-pixels"}}};
      row["quilt_decision_id"] = Json{"quilt." + opt.cell_id + ".primary"};
      row["target_bounds"] =
          Json{JsonArray{Json{0.0}, Json{0.0}, Json{static_cast<double>(pw)}, Json{static_cast<double>(ph)}}};
      row["warnings"] = Json{JsonArray{}};
      prov_doc_table.push_back(Json{row});
    }
    JsonObject provenance_doc;
    provenance_doc["fixture_id"] = Json{opt.cell_id};
    provenance_doc["schema_version"] = Json{"vulkan.provenance.v0"};
    provenance_doc["provenance_table"] = Json{prov_doc_table};

    JsonObject manifest;
    manifest["fixture_id"] = Json{opt.cell_id};
    manifest["title"] = Json{"Real NOAA ENC " + opt.cell_id +
                             " filled-polygon command-stream capture (RENDERMODEL-4)"};
    manifest["schema_version"] = Json{"vulkan.render_scene.v0"};
    manifest["scene_id"] = Json{scene_id};
    manifest["source_file"] = Json{"source.json"};
    manifest["scene_file"] = Json{"scene.commands.json"};
    manifest["provenance_file"] = Json{"provenance.json"};
    manifest["render_model_file"] = Json{"render-model.json"};
    manifest["render_model_binary_file"] = Json{"render-model.bin"};
    manifest["render_artifact_file"] = Json{"render-artifact.json"};
    manifest["render_artifact_binary_file"] = Json{"render-artifact.bin"};
    JsonObject license;
    license["type"] = Json{"noaa-enc-public-domain"};
    license["redistribution"] = Json{"us-government-work"};
    license["notes"] = Json{"Geometry derived from NOAA ENC " + opt.cell_id +
                            " (US public domain) via GDAL/OGR S-57."};
    manifest["license"] = Json{license};
    JsonObject capture;
    capture["name"] = Json{opt.palette + "-" + opt.display_category + "-z" + std::to_string(z)};
    capture["palette"] = Json{opt.palette};
    capture["display_category"] = Json{opt.display_category};
    capture["safety_depth_m"] = Json{opt.safety_depth};
    capture["projection"] = Json{"web_mercator_tile"};
    JsonObject tile_obj;
    tile_obj["z"] = Json{static_cast<double>(z)};
    tile_obj["x"] = Json{static_cast<double>(tx)};
    tile_obj["y"] = Json{static_cast<double>(ty)};
    capture["tile"] = Json{tile_obj};
    capture["pixel_size"] =
        Json{JsonArray{Json{static_cast<double>(pw)}, Json{static_cast<double>(ph)}}};
    manifest["capture_matrix"] = Json{JsonArray{Json{capture}}};
    manifest["required_command_types"] = Json{JsonArray{Json{"fill_area"}}};

    auto dump = [&](const char* name, const Json& obj) {
      std::ostringstream ss;
      write_json(ss, obj, 0);
      ss << '\n';
      write_file(opt.out_dir / name, ss.str());
    };

    dump("scene.commands.json", Json{scene});
    dump("source.json", Json{source});
    dump("provenance.json", Json{provenance_doc});
    dump("manifest.json", Json{manifest});

    std::filesystem::remove_all(tmp);

    int total_rings = 0;
    for (const auto& [cid, rings] : cat_rings) {
      (void)cid;
      total_rings += static_cast<int>(rings.size());
    }
    std::cerr << "cell=" << opt.cell_id << " bbox=(" << std::fixed << std::setprecision(5) << west
              << "," << south << "," << east << "," << north << ") pixel_size=(" << pw << "x" << ph
              << ") categories=" << command_groups.size() << " convex_rings=" << total_rings << "\n";
    for (const Category& c : kCategories) {
      if (cat_counts[c.id]) {
        std::cerr << "    " << std::setw(15) << std::left << c.id << " features=" << std::setw(5)
                  << cat_counts[c.id] << " rings=" << std::setw(6) << cat_rings[c.id].size() << "\n";
      }
    }
    std::cout << opt.out_dir << "\n";
    return 0;
  } catch (const std::runtime_error& e) {
    if (std::string(e.what()) == "usage") {
      std::cerr
          << "usage: enc-to-render-fixture ENC OUT_DIR [--cell-id ID] [--pixel-size 2048] "
             "[--palette day] [--display-category standard] [--safety-depth 10] "
             "[--safety-contour 10] [--half-width-px 1.4] [--point-size-px 2.6] "
             "[--simplify-px 1.0] [--reference-zoom 13] [--tile-z Z --tile-x X --tile-y Y] "
             "[--bbox W,S,E,N]\n";
      return 2;
    }
    std::cerr << e.what() << "\n";
    return 2;
  }
}
