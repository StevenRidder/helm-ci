// RENDERMODEL-3/5 — CPU reference render of helm.render.artifact.v1 (parity with
// scripts/render-artifact-preview.py). Rasterizes artifact geometry to PNG without WebGPU.

#include "render_artifact.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>
#include <zlib.h>

namespace {

constexpr int kStride = 4;

struct Json;
using JsonArray = std::vector<Json>;
using JsonObject = std::map<std::string, Json>;

struct Json {
  using Storage = std::variant<std::nullptr_t, bool, double, std::string, JsonArray, JsonObject>;
  Storage value;

  [[nodiscard]] bool is_object() const { return std::holds_alternative<JsonObject>(value); }
  [[nodiscard]] bool is_array() const { return std::holds_alternative<JsonArray>(value); }
  [[nodiscard]] bool is_string() const { return std::holds_alternative<std::string>(value); }
  [[nodiscard]] bool is_number() const { return std::holds_alternative<double>(value); }

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

  [[nodiscard]] const Json* get(std::string_view key) const {
    if (!is_object()) return nullptr;
    const auto it = object().find(std::string(key));
    return it == object().end() ? nullptr : &it->second;
  }

  [[nodiscard]] const Json& at(std::string_view key) const {
    const Json* v = get(key);
    if (!v) throw std::runtime_error("missing JSON key: " + std::string(key));
    return *v;
  }
};

class JsonParser {
 public:
  explicit JsonParser(std::string text) : text_(std::move(text)) {}

  Json parse() {
    Json out = parse_value();
    skip_ws();
    if (pos_ != text_.size()) throw std::runtime_error("trailing JSON data");
    return out;
  }

 private:
  void skip_ws() {
    while (pos_ < text_.size() && std::isspace(static_cast<unsigned char>(text_[pos_]))) ++pos_;
  }

  Json parse_value() {
    skip_ws();
    const char ch = text_[pos_];
    if (ch == '{') return Json{parse_object()};
    if (ch == '[') return Json{parse_array()};
    if (ch == '"') return Json{parse_string()};
    if (ch == 't') return parse_literal("true", Json{true});
    if (ch == 'f') return parse_literal("false", Json{false});
    if (ch == 'n') return parse_literal("null", Json{nullptr});
    if (ch == '-' || std::isdigit(static_cast<unsigned char>(ch))) return Json{parse_number()};
    throw std::runtime_error("invalid JSON");
  }

  Json parse_literal(std::string_view lit, Json value) {
    if (text_.compare(pos_, lit.size(), lit) != 0) throw std::runtime_error("invalid literal");
    pos_ += lit.size();
    return value;
  }

  JsonObject parse_object() {
    ++pos_;
    JsonObject obj;
    skip_ws();
    if (text_[pos_] == '}') {
      ++pos_;
      return obj;
    }
    while (true) {
      skip_ws();
      std::string key = parse_string();
      skip_ws();
      if (text_[pos_] != ':') throw std::runtime_error("expected :");
      ++pos_;
      obj.emplace(std::move(key), parse_value());
      skip_ws();
      if (text_[pos_] == '}') {
        ++pos_;
        break;
      }
      if (text_[pos_] != ',') throw std::runtime_error("expected ,");
      ++pos_;
    }
    return obj;
  }

  JsonArray parse_array() {
    ++pos_;
    JsonArray arr;
    skip_ws();
    if (text_[pos_] == ']') {
      ++pos_;
      return arr;
    }
    while (true) {
      arr.push_back(parse_value());
      skip_ws();
      if (text_[pos_] == ']') {
        ++pos_;
        break;
      }
      if (text_[pos_] != ',') throw std::runtime_error("expected ,");
      ++pos_;
    }
    return arr;
  }

  std::string parse_string() {
    if (text_[pos_] != '"') throw std::runtime_error("expected string");
    ++pos_;
    std::string out;
    while (pos_ < text_.size()) {
      const char ch = text_[pos_++];
      if (ch == '"') return out;
      if (ch == '\\') {
        if (pos_ >= text_.size()) throw std::runtime_error("bad escape");
        const char esc = text_[pos_++];
        switch (esc) {
          case '"': out.push_back('"'); break;
          case '\\': out.push_back('\\'); break;
          case '/': out.push_back('/'); break;
          case 'n': out.push_back('\n'); break;
          case 'r': out.push_back('\r'); break;
          case 't': out.push_back('\t'); break;
          default: throw std::runtime_error("bad escape");
        }
      } else {
        out.push_back(ch);
      }
    }
    throw std::runtime_error("unterminated string");
  }

  double parse_number() {
    const std::size_t start = pos_;
    if (text_[pos_] == '-') ++pos_;
    while (pos_ < text_.size() && std::isdigit(static_cast<unsigned char>(text_[pos_]))) ++pos_;
    if (pos_ < text_.size() && text_[pos_] == '.') {
      ++pos_;
      while (pos_ < text_.size() && std::isdigit(static_cast<unsigned char>(text_[pos_]))) ++pos_;
    }
    return std::stod(text_.substr(start, pos_ - start));
  }

  std::string text_;
  std::size_t pos_ = 0;
};

[[nodiscard]] std::string read_file(const std::filesystem::path& path) {
  std::ifstream in(path);
  if (!in) throw std::runtime_error("cannot read " + path.string());
  std::ostringstream out;
  out << in.rdbuf();
  return out.str();
}

struct Rgb {
  std::uint8_t r = 0;
  std::uint8_t g = 0;
  std::uint8_t b = 0;
};

[[nodiscard]] Rgb hex_rgb(std::string h) {
  if (!h.empty() && h[0] == '#') h.erase(h.begin());
  if (h.size() == 3) {
    std::string expanded;
    for (char c : h) {
      expanded.push_back(c);
      expanded.push_back(c);
    }
    h = std::move(expanded);
  }
  return Rgb{static_cast<std::uint8_t>(std::stoi(h.substr(0, 2), nullptr, 16)),
             static_cast<std::uint8_t>(std::stoi(h.substr(2, 2), nullptr, 16)),
             static_cast<std::uint8_t>(std::stoi(h.substr(4, 2), nullptr, 16))};
}

[[nodiscard]] double merc_x(double lon) { return lon / 360.0 + 0.5; }

[[nodiscard]] double merc_y(double lat) {
  const double s = std::max(-0.9999, std::min(0.9999, std::sin(lat * 3.14159265358979323846 / 180.0)));
  return 0.5 - std::log((1.0 + s) / (1.0 - s)) / (4.0 * 3.14159265358979323846);
}

class Canvas {
 public:
  Canvas(int w, int h, Rgb bg) : w_(w), h_(h), buf_(static_cast<std::size_t>(w * h * 3), 0) {
    for (std::size_t i = 0; i < buf_.size(); i += 3) {
      buf_[i] = bg.r;
      buf_[i + 1] = bg.g;
      buf_[i + 2] = bg.b;
    }
  }

  void blend(int x, int y, Rgb rgb, double a) {
    if (x < 0 || y < 0 || x >= w_ || y >= h_) return;
    const std::size_t i = static_cast<std::size_t>((y * w_ + x) * 3);
    const double ia = 1.0 - a;
    buf_[i] = static_cast<std::uint8_t>(buf_[i] * ia + rgb.r * a);
    buf_[i + 1] = static_cast<std::uint8_t>(buf_[i + 1] * ia + rgb.g * a);
    buf_[i + 2] = static_cast<std::uint8_t>(buf_[i + 2] * ia + rgb.b * a);
  }

  void fill_tri(std::array<std::pair<double, double>, 3> tri, Rgb rgb, double a) {
    const auto [p0, p1, p2] = tri;
    const int minx = std::max(0, static_cast<int>(std::floor(std::min({p0.first, p1.first, p2.first}))));
    const int maxx = std::min(w_ - 1, static_cast<int>(std::ceil(std::max({p0.first, p1.first, p2.first}))));
    const int miny = std::max(0, static_cast<int>(std::floor(std::min({p0.second, p1.second, p2.second}))));
    const int maxy = std::min(h_ - 1, static_cast<int>(std::ceil(std::max({p0.second, p1.second, p2.second}))));
    const double x0 = p0.first, y0 = p0.second;
    const double x1 = p1.first, y1 = p1.second;
    const double x2 = p2.first, y2 = p2.second;
    const double d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2);
    if (std::abs(d) < 1e-12) return;
    for (int y = miny; y <= maxy; ++y) {
      for (int x = minx; x <= maxx; ++x) {
        const double px = x + 0.5;
        const double py = y + 0.5;
        const double l0 = ((y1 - y2) * (px - x2) + (x2 - x1) * (py - y2)) / d;
        const double l1 = ((y2 - y0) * (px - x2) + (x0 - x2) * (py - y2)) / d;
        const double l2 = 1.0 - l0 - l1;
        if (l0 >= -0.001 && l1 >= -0.001 && l2 >= -0.001) blend(x, y, rgb, a);
      }
    }
  }

  void write_png(const std::filesystem::path& path) const {
    std::vector<unsigned char> raw;
    raw.reserve(static_cast<std::size_t>((w_ * h_ * 3) + h_));
    for (int y = 0; y < h_; ++y) {
      raw.push_back(0);
      const std::size_t off = static_cast<std::size_t>(y * w_ * 3);
      raw.insert(raw.end(), buf_.begin() + off, buf_.begin() + off + static_cast<std::size_t>(w_ * 3));
    }
    uLongf comp_len = compressBound(static_cast<uLong>(raw.size()));
    std::vector<unsigned char> comp(comp_len);
    if (compress2(comp.data(), &comp_len, raw.data(), static_cast<uLong>(raw.size()), 9) != Z_OK) {
      throw std::runtime_error("zlib compress failed");
    }
    comp.resize(comp_len);

    auto crc32 = [](const unsigned char* data, std::size_t len) -> std::uint32_t {
      return static_cast<std::uint32_t>(::crc32(0, data, static_cast<uInt>(len)));
    };
    auto write_chunk = [&](std::ofstream& out, const char* tag, const std::vector<unsigned char>& data) {
      const std::uint32_t len = static_cast<std::uint32_t>(data.size());
      out.put(static_cast<char>((len >> 24) & 0xff));
      out.put(static_cast<char>((len >> 16) & 0xff));
      out.put(static_cast<char>((len >> 8) & 0xff));
      out.put(static_cast<char>(len & 0xff));
      out.write(tag, 4);
      if (!data.empty()) out.write(reinterpret_cast<const char*>(data.data()), static_cast<std::streamsize>(data.size()));
      std::vector<unsigned char> crc_input(4 + data.size());
      std::memcpy(crc_input.data(), tag, 4);
      if (!data.empty()) std::memcpy(crc_input.data() + 4, data.data(), data.size());
      const std::uint32_t c = crc32(crc_input.data(), crc_input.size());
      out.put(static_cast<char>((c >> 24) & 0xff));
      out.put(static_cast<char>((c >> 16) & 0xff));
      out.put(static_cast<char>((c >> 8) & 0xff));
      out.put(static_cast<char>(c & 0xff));
    };

    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("cannot write " + path.string());
    out.write("\x89PNG\r\n\x1a\n", 8);
    const std::uint32_t w = static_cast<std::uint32_t>(w_);
    const std::uint32_t h = static_cast<std::uint32_t>(h_);
    std::vector<unsigned char> ihdr(13);
    ihdr[0] = static_cast<unsigned char>((w >> 24) & 0xff);
    ihdr[1] = static_cast<unsigned char>((w >> 16) & 0xff);
    ihdr[2] = static_cast<unsigned char>((w >> 8) & 0xff);
    ihdr[3] = static_cast<unsigned char>(w & 0xff);
    ihdr[4] = static_cast<unsigned char>((h >> 24) & 0xff);
    ihdr[5] = static_cast<unsigned char>((h >> 16) & 0xff);
    ihdr[6] = static_cast<unsigned char>((h >> 8) & 0xff);
    ihdr[7] = static_cast<unsigned char>(h & 0xff);
    ihdr[8] = 8;
    ihdr[9] = 2;
    write_chunk(out, "IHDR", ihdr);
    write_chunk(out, "IDAT", comp);
    write_chunk(out, "IEND", {});
  }

  [[nodiscard]] int width() const { return w_; }
  [[nodiscard]] int height() const { return h_; }

 private:
  int w_;
  int h_;
  std::vector<std::uint8_t> buf_;
};

[[nodiscard]] Rgb style_fallback(std::string_view style_key) {
  static const std::map<std::string, std::string, std::less<>> kFallback = {
      {"fill_area", "#b9d7e8"},       {"stroke_line", "#4a6f8a"}, {"place_symbol", "#f5d76e"},
      {"draw_text", "#28323c"},       {"draw_sounding", "#28323c"}, {"draw_raster_sheet", "#787882"},
  };
  const auto it = kFallback.find(style_key);
  return hex_rgb(it == kFallback.end() ? "#c0c0c8" : it->second);
}

}  // namespace

int main(int argc, char** argv) {
  try {
    std::string artifact_path;
    std::string out_path;
    std::string scene_path;
    int width = 1400;
    std::string bg = "#08151d";
    for (int i = 1; i < argc; ++i) {
      const std::string arg = argv[i];
      if (arg == "--scene" && i + 1 < argc) {
        scene_path = argv[++i];
      } else if (arg == "--width" && i + 1 < argc) {
        width = std::stoi(argv[++i]);
      } else if (arg == "--bg" && i + 1 < argc) {
        bg = argv[++i];
      } else if (artifact_path.empty()) {
        artifact_path = arg;
      } else if (out_path.empty()) {
        out_path = arg;
      } else {
        std::cerr << "usage: render-artifact-preview ARTIFACT.json OUT.png [--scene scene.commands.json] "
                     "[--width 1400] [--bg \"#08151d\"]\n";
        return 2;
      }
    }
    if (artifact_path.empty() || out_path.empty()) {
      std::cerr << "usage: render-artifact-preview ARTIFACT.json OUT.png [--scene scene.commands.json] "
                   "[--width 1400] [--bg \"#08151d\"]\n";
      return 2;
    }

    const Json art = JsonParser(read_file(artifact_path)).parse();
    const Json& vp = art.at("viewport");
    const Json& bbox = vp.at("geographic_bbox");
    const double west = bbox.at("west").number();
    const double east = bbox.at("east").number();
    const double south = bbox.at("south").number();
    const double north = bbox.at("north").number();
    const JsonArray& pixel_size = vp.at("pixel_size").array();
    const double pw = pixel_size[0].number();
    const double ph = pixel_size[1].number();

    std::map<std::string, Rgb> cmd_color;
    std::map<std::string, double> cmd_alpha;
    if (!scene_path.empty()) {
      const Json scene = JsonParser(read_file(scene_path)).parse();
      for (const Json& grp : scene.at("command_groups").array()) {
        for (const Json& cmd : grp.at("commands").array()) {
          const Json* cid = cmd.get("command_id");
          const Json* fill = cmd.get("fill");
          if (!cid || !cid->is_string() || !fill || !fill->is_object()) continue;
          const Json* color = fill->get("color");
          if (!color || !color->is_string()) continue;
          cmd_color[cid->string()] = hex_rgb(color->string());
          const Json* opacity = cmd.get("opacity");
          cmd_alpha[cid->string()] = opacity && opacity->is_number() ? opacity->number() : 1.0;
        }
      }
    }

    const JsonArray& mats = art.get("material_table") ? art.at("material_table").array() : JsonArray{};

    auto batch_color = [&](const Json& batch) -> std::pair<Rgb, double> {
      std::string pid;
      if (const Json* pids = batch.get("primitive_ids"); pids && pids->is_array() && !pids->array().empty()) {
        if (pids->array()[0].is_string()) pid = pids->array()[0].string();
      }
      if (!pid.empty()) {
        const auto cit = cmd_color.find(pid);
        if (cit != cmd_color.end()) {
          const auto ait = cmd_alpha.find(pid);
          return {cit->second, ait == cmd_alpha.end() ? 1.0 : ait->second};
        }
      }
      const int mi = batch.get("material_index") ? static_cast<int>(batch.at("material_index").number()) : 0;
      std::string sk;
      if (mi >= 0 && static_cast<std::size_t>(mi) < mats.size() && mats[static_cast<std::size_t>(mi)].is_object()) {
        if (const Json* v = mats[static_cast<std::size_t>(mi)].get("style_key"); v && v->is_string()) {
          sk = v->string();
        }
      }
      return {style_fallback(sk), 0.9};
    };

    const auto to_merc = [&](double px, double py) {
      const double lon = west + px * (east - west) / std::max(1.0, pw);
      const double lat = north - py * (north - south) / std::max(1.0, ph);
      return std::pair<double, double>{merc_x(lon), merc_y(lat)};
    };

    const double mx_w = merc_x(west);
    const double mx_e = merc_x(east);
    const double my_n = merc_y(north);
    const double my_s = merc_y(south);
    const int W = width;
    const int H = std::max(1, static_cast<int>(std::round(W * (my_s - my_n) / (mx_e - mx_w))));

    const auto to_screen = [&](double px, double py) {
      const auto [mx, my] = to_merc(px, py);
      const double sx = (mx - mx_w) / (mx_e - mx_w) * W;
      const double sy = (my - my_n) / (my_s - my_n) * H;
      return std::pair<double, double>{sx, sy};
    };

    const Json& verts_json = art.at("geometry").at("vertices_f32");
    const Json& inds_json = art.at("geometry").at("indices_u32");
    std::vector<float> verts;
    for (const Json& v : verts_json.array()) verts.push_back(static_cast<float>(v.number()));
    std::vector<std::uint32_t> inds;
    for (const Json& v : inds_json.array()) inds.push_back(static_cast<std::uint32_t>(v.number()));

    JsonArray batches = art.get("draw_batches") ? art.at("draw_batches").array() : JsonArray{};
    std::sort(batches.begin(), batches.end(), [](const Json& a, const Json& b) {
      const double ao = a.get("order_bucket") ? a.at("order_bucket").number() : 0;
      const double bo = b.get("order_bucket") ? b.at("order_bucket").number() : 0;
      return ao < bo;
    });

    Canvas canvas(W, H, hex_rgb(bg));
    const auto vxy = [&](std::uint32_t vi) {
      return std::pair<double, double>{verts[vi * kStride], verts[vi * kStride + 1]};
    };

    int n_tri = 0;
    for (const Json& batch : batches) {
      const auto [rgb, a] = batch_color(batch);
      const std::string topo = batch.get("topology") && batch.at("topology").is_string()
                                   ? batch.at("topology").string()
                                   : std::string{};
      const std::uint32_t fi = static_cast<std::uint32_t>(batch.at("first_index").number());
      const std::uint32_t ic = static_cast<std::uint32_t>(batch.at("index_count").number());
      if (topo == "triangles") {
        for (std::uint32_t k = fi; k + 2 < fi + ic; k += 3) {
          canvas.fill_tri({to_screen(vxy(inds[k]).first, vxy(inds[k]).second),
                           to_screen(vxy(inds[k + 1]).first, vxy(inds[k + 1]).second),
                           to_screen(vxy(inds[k + 2]).first, vxy(inds[k + 2]).second)},
                          rgb, a);
          ++n_tri;
        }
      } else if (topo == "line_list") {
        for (std::uint32_t k = fi; k + 1 < fi + ic; k += 2) {
          const auto s0 = to_screen(vxy(inds[k]).first, vxy(inds[k]).second);
          const auto s1 = to_screen(vxy(inds[k + 1]).first, vxy(inds[k + 1]).second);
          const int steps = std::max(1, static_cast<int>(std::hypot(s1.first - s0.first, s1.second - s0.second)));
          for (int t = 0; t <= steps; ++t) {
            const int x = static_cast<int>(s0.first + (s1.first - s0.first) * t / steps);
            const int y = static_cast<int>(s0.second + (s1.second - s0.second) * t / steps);
            for (int dx = -1; dx <= 1; ++dx) {
              for (int dy = -1; dy <= 1; ++dy) canvas.blend(x + dx, y + dy, rgb, a);
            }
          }
        }
      } else if (topo == "points") {
        for (std::uint32_t k = fi; k < fi + ic; ++k) {
          const auto [sx, sy] = to_screen(vxy(inds[k]).first, vxy(inds[k]).second);
          const int xi = static_cast<int>(sx);
          const int yi = static_cast<int>(sy);
          for (int dx = -2; dx <= 2; ++dx) {
            for (int dy = -2; dy <= 2; ++dy) canvas.blend(xi + dx, yi + dy, rgb, a);
          }
        }
      }
    }

    canvas.write_png(out_path);
    std::cout << out_path << "  " << canvas.width() << "x" << canvas.height()
              << "  batches=" << batches.size() << " triangles=" << n_tri << "\n";
    return 0;
  } catch (const std::exception& ex) {
    std::cerr << "render-artifact-preview failed: " << ex.what() << "\n";
    return 1;
  }
}
