// RENDERMODEL-5 — build a multi-zoom WebGPU artifact pyramid for a real ENC cell.
// C++17 port of scripts/render-artifact-pyramid.py

#include "web_mercator.h"

#include <algorithm>
#include <cctype>
#include <cstdlib>
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
#include <utility>
#include <variant>
#include <vector>

namespace {

struct Json;
using JsonArray = std::vector<Json>;
using JsonObject = std::map<std::string, Json>;

struct Json {
  using Storage = std::variant<std::nullptr_t, double, std::string, JsonArray, JsonObject>;
  Storage value;

  [[nodiscard]] bool is_null() const { return std::holds_alternative<std::nullptr_t>(value); }
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
    if (ch == 't') return parse_literal("true", Json{nullptr});
    if (ch == 'f') return parse_literal("false", Json{nullptr});
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
        case 'u': pos_ += 4; out.push_back('?'); break;
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
      case '\n': out << "\\n"; break;
      case '\r': out << "\\r"; break;
      case '\t': out << "\\t"; break;
      default: out << static_cast<char>(c);
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

struct IndexEntry {
  int z = 0;
  int x = 0;
  int y = 0;
  double west = 0;
  double south = 0;
  double east = 0;
  double north = 0;
  std::string fixture_relpath;
  std::string artifact_url;
  std::string artifact_id;
  int vertex_count = 0;
  int index_count = 0;
  std::string packet_sha256;
};

struct Options {
  std::filesystem::path enc;
  std::filesystem::path out_dir;
  std::filesystem::path root;
  std::string cell_id;
  double west = 0;
  double south = 0;
  double east = 0;
  double north = 0;
  int z_min = 11;
  int z_max = 15;
  int pixel_size = 2048;
  int reference_zoom = 13;
  double simplify_px = 1.0;
  bool skip_compile = false;
  int max_tiles = 0;
  bool append = false;
  std::vector<int> nodata_z;
};

[[nodiscard]] std::string shell_quote(const std::string& s) {
  std::string out = "'";
  for (const char c : s) {
    if (c == '\'') out += "'\\''";
    else out += c;
  }
  out += "'";
  return out;
}

[[nodiscard]] std::filesystem::path discover_root(int argc, char** argv) {
  if (const char* env = std::getenv("HELM_ROOT")) return env;
  if (argc > 0) {
    std::filesystem::path exe = std::filesystem::absolute(argv[0]);
    if (exe.filename() == "render-artifact-pyramid" || exe.parent_path().filename() == "scripts") {
      return exe.parent_path().parent_path();
    }
  }
  throw std::runtime_error("cannot discover HELM root — set HELM_ROOT");
}

[[nodiscard]] std::string read_file(const std::filesystem::path& path) {
  std::ifstream in(path);
  if (!in) throw std::runtime_error("cannot read " + path.string());
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

void write_file(const std::filesystem::path& path, const std::string& content) {
  std::filesystem::create_directories(path.parent_path());
  std::ofstream out(path);
  if (!out) throw std::runtime_error("cannot write " + path.string());
  out << content;
  if (!content.empty() && content.back() != '\n') out << '\n';
}

void run_cmd(const std::string& cmd, const std::filesystem::path& cwd) {
  std::cerr << "+ " << cmd << "\n";
  const std::string full = "cd " + shell_quote(cwd.string()) + " && " + cmd;
  if (std::system(full.c_str()) != 0) throw std::runtime_error("command failed: " + cmd);
}

[[nodiscard]] IndexEntry artifact_stats(const std::filesystem::path& path) {
  IndexEntry e;
  const Json art = JsonParser(read_file(path)).parse();
  if (const Json* id = art.get("artifact_id"); id && id->is_string()) e.artifact_id = id->string();
  if (const Json* geo = art.get("geometry"); geo && geo->is_object()) {
    if (const Json* verts = geo->get("vertices_f32"); verts && verts->is_array()) {
      e.vertex_count = static_cast<int>(verts->array().size() / 4);
    }
    if (const Json* idx = geo->get("indices_u32"); idx && idx->is_array()) {
      e.index_count = static_cast<int>(idx->array().size());
    }
  }
  if (const Json* checksums = art.get("checksums"); checksums && checksums->is_object()) {
    if (const Json* sha = checksums->get("packet_sha256"); sha && sha->is_string()) {
      e.packet_sha256 = sha->string();
    }
  }
  return e;
}

[[nodiscard]] std::string tile_key(int z, int x, int y) {
  return std::to_string(z) + "/" + std::to_string(x) + "/" + std::to_string(y);
}

[[nodiscard]] std::vector<IndexEntry> load_existing_entries(const std::filesystem::path& index_path) {
  std::vector<IndexEntry> out;
  if (!std::filesystem::exists(index_path)) return out;
  const Json root = JsonParser(read_file(index_path)).parse();
  const Json* entries = root.get("entries");
  if (!entries || !entries->is_array()) return out;
  for (const Json& e : entries->array()) {
    if (!e.is_object()) continue;
    IndexEntry row;
    if (const Json* tile = e.get("tile"); tile && tile->is_object()) {
      row.z = static_cast<int>(tile->at("z").number());
      row.x = static_cast<int>(tile->at("x").number());
      row.y = static_cast<int>(tile->at("y").number());
    }
    if (const Json* bb = e.get("geographic_bbox"); bb && bb->is_object()) {
      row.west = bb->at("west").number();
      row.south = bb->at("south").number();
      row.east = bb->at("east").number();
      row.north = bb->at("north").number();
    }
    if (const Json* v = e.get("fixture_relpath"); v && v->is_string()) row.fixture_relpath = v->string();
    if (const Json* v = e.get("artifact_url"); v && v->is_string()) row.artifact_url = v->string();
    if (const Json* v = e.get("artifact_id"); v && v->is_string()) row.artifact_id = v->string();
    if (const Json* v = e.get("vertex_count"); v && v->is_number()) row.vertex_count = static_cast<int>(v->number());
    if (const Json* v = e.get("index_count"); v && v->is_number()) row.index_count = static_cast<int>(v->number());
    if (const Json* v = e.get("packet_sha256"); v && v->is_string()) row.packet_sha256 = v->string();
    out.push_back(std::move(row));
  }
  return out;
}

void write_index(const Options& opt, const std::vector<IndexEntry>& entries,
                 const std::vector<int>& nodata_z_levels, const std::filesystem::path& index_path,
                 const std::filesystem::path& web_index_path) {
  std::ostringstream out;
  out << "{\n";
  write_key(out, 1, "schema_version");
  write_string(out, "helm.render.artifact_index.v1");
  out << ",\n";
  write_key(out, 1, "cell_id");
  write_string(out, opt.cell_id);
  out << ",\n";
  write_key(out, 1, "source_epoch");
  write_string(out, opt.cell_id + "@enc");
  out << ",\n";
  write_key(out, 1, "cell_bbox");
  out << "{\n";
  write_key(out, 2, "west");
  write_number(out, opt.west);
  out << ",\n";
  write_key(out, 2, "south");
  write_number(out, opt.south);
  out << ",\n";
  write_key(out, 2, "east");
  write_number(out, opt.east);
  out << ",\n";
  write_key(out, 2, "north");
  write_number(out, opt.north);
  out << "\n";
  indent(out, 1);
  out << "},\n";
  write_key(out, 1, "z_range");
  const int z_lo = entries.empty() ? opt.z_min : entries.front().z;
  const int z_hi = entries.empty() ? opt.z_max : entries.back().z;
  out << "[" << z_lo << ", " << z_hi << "],\n";
  write_key(out, 1, "pixel_size");
  out << "[" << opt.pixel_size << ", " << opt.pixel_size << "],\n";
  write_key(out, 1, "reference_zoom");
  out << opt.reference_zoom << ",\n";
  if (!nodata_z_levels.empty()) {
    write_key(out, 1, "nodata_z_levels");
    out << "[";
    for (std::size_t i = 0; i < nodata_z_levels.size(); ++i) {
      if (i) out << ", ";
      out << nodata_z_levels[i];
    }
    out << "],\n";
  }
  write_key(out, 1, "tile_count");
  out << entries.size() << ",\n";
  write_key(out, 1, "entries");
  out << "[\n";
  for (std::size_t i = 0; i < entries.size(); ++i) {
    const IndexEntry& e = entries[i];
    indent(out, 2);
    out << "{\n";
    write_key(out, 3, "tile");
    out << "{\n";
    write_key(out, 4, "z");
    out << e.z << ",\n";
    write_key(out, 4, "x");
    out << e.x << ",\n";
    write_key(out, 4, "y");
    out << e.y << "\n";
    indent(out, 3);
    out << "},\n";
    write_key(out, 3, "geographic_bbox");
    out << "{\n";
    write_key(out, 4, "west");
    write_number(out, e.west);
    out << ",\n";
    write_key(out, 4, "south");
    write_number(out, e.south);
    out << ",\n";
    write_key(out, 4, "east");
    write_number(out, e.east);
    out << ",\n";
    write_key(out, 4, "north");
    write_number(out, e.north);
    out << "\n";
    indent(out, 3);
    out << "},\n";
    write_key(out, 3, "fixture_relpath");
    write_string(out, e.fixture_relpath);
    out << ",\n";
    write_key(out, 3, "artifact_url");
    write_string(out, e.artifact_url);
    out << ",\n";
    write_key(out, 3, "artifact_id");
    write_string(out, e.artifact_id);
    out << ",\n";
    write_key(out, 3, "vertex_count");
    out << e.vertex_count << ",\n";
    write_key(out, 3, "index_count");
    out << e.index_count << ",\n";
    write_key(out, 3, "packet_sha256");
    write_string(out, e.packet_sha256);
    out << "\n";
    indent(out, 2);
    out << "}" << (i + 1 < entries.size() ? ",\n" : "\n");
  }
  indent(out, 1);
  out << "]\n";
  out << "}\n";
  const std::string json = out.str();
  write_file(index_path, json);
  write_file(web_index_path, json);
}

[[nodiscard]] Options parse_args(int argc, char** argv) {
  Options opt;
  if (argc < 3) throw std::runtime_error("usage");
  opt.root = discover_root(argc, argv);
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
    } else if (arg == "--cell-bbox") {
      const std::string bb = need("--cell-bbox");
      std::istringstream ss(bb);
      char comma;
      ss >> opt.west >> comma >> opt.south >> comma >> opt.east >> comma >> opt.north;
    } else if (arg == "--z-min") {
      opt.z_min = std::stoi(need("--z-min"));
    } else if (arg == "--z-max") {
      opt.z_max = std::stoi(need("--z-max"));
    } else if (arg == "--pixel-size") {
      opt.pixel_size = std::stoi(need("--pixel-size"));
    } else if (arg == "--reference-zoom") {
      opt.reference_zoom = std::stoi(need("--reference-zoom"));
    } else if (arg == "--simplify-px") {
      opt.simplify_px = std::stod(need("--simplify-px"));
    } else if (arg == "--skip-compile") {
      opt.skip_compile = true;
    } else if (arg == "--max-tiles") {
      opt.max_tiles = std::stoi(need("--max-tiles"));
    } else if (arg == "--append") {
      opt.append = true;
    } else if (arg == "--nodata-z") {
      const std::string val = need("--nodata-z");
      std::istringstream ss(val);
      std::string part;
      while (std::getline(ss, part, ',')) {
        if (!part.empty()) opt.nodata_z.push_back(std::stoi(part));
      }
    } else {
      throw std::runtime_error("unknown arg: " + arg);
    }
  }
  if (opt.cell_id.empty()) throw std::runtime_error("--cell-id is required");
  return opt;
}

[[nodiscard]] std::string lower_ascii(std::string s) {
  for (char& c : s) {
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
  }
  return s;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    Options opt = parse_args(argc, argv);
    opt.enc = std::filesystem::absolute(opt.enc);
    opt.out_dir = std::filesystem::absolute(opt.out_dir);

    std::vector<helm::webmerc::TileCoord> tiles =
        helm::webmerc::tiles_covering_bbox(opt.west, opt.south, opt.east, opt.north, opt.z_min,
                                           opt.z_max);
    if (opt.max_tiles > 0 && static_cast<int>(tiles.size()) > opt.max_tiles) {
      tiles.resize(static_cast<std::size_t>(opt.max_tiles));
    }
    if (tiles.empty()) {
      std::cerr << "No tiles in range\n";
      return 2;
    }

    const std::filesystem::path pyramid_root = opt.out_dir / "pyramid";
    const std::filesystem::path tiles_root = pyramid_root / "tiles";
    const std::filesystem::path index_path = pyramid_root / "index.json";
    const std::filesystem::path web_index =
        opt.root / "web" / "data" / ("render-artifact-index-" + lower_ascii(opt.cell_id) + ".json");

    std::map<std::string, IndexEntry> entry_map;
    if (opt.append) {
      for (IndexEntry e : load_existing_entries(index_path)) {
        entry_map[tile_key(e.z, e.x, e.y)] = std::move(e);
      }
    }

    const std::filesystem::path enc_script = opt.root / "scripts" / "enc-to-render-fixture";
    const std::filesystem::path model_script = opt.root / "scripts" / "render-model-fixture-export";
    const std::filesystem::path compile_script = opt.root / "scripts" / "render-artifact-compile";
    const std::string cell_lower = lower_ascii(opt.cell_id);

    for (const helm::webmerc::TileCoord& tile : tiles) {
      const std::string key = tile_key(tile.z, tile.x, tile.y);
      if (opt.append && entry_map.count(key)) {
        std::cerr << "  skip z" << tile.z << "/" << tile.x << "/" << tile.y << " (already indexed)\n";
        continue;
      }

      const std::filesystem::path tile_dir =
          tiles_root / std::to_string(tile.z) / std::to_string(tile.x) / std::to_string(tile.y);
      std::filesystem::create_directories(tile_dir);

      const helm::webmerc::Bbox bb = helm::webmerc::num2bbox(tile.z, tile.x, tile.y);

      run_cmd(enc_script.string() + " " + shell_quote(opt.enc.string()) + " " +
                  shell_quote(tile_dir.string()) + " --cell-id " + shell_quote(opt.cell_id) +
                  " --pixel-size " + std::to_string(opt.pixel_size) + " --reference-zoom " +
                  std::to_string(opt.reference_zoom) + " --simplify-px " +
                  number_to_string(opt.simplify_px) + " --tile-z " + std::to_string(tile.z) +
                  " --tile-x " + std::to_string(tile.x) + " --tile-y " + std::to_string(tile.y),
              opt.root);

      if (!opt.skip_compile) {
        run_cmd(model_script.string() + " " + shell_quote(tile_dir.string()) + " --print-hashes",
                opt.root);
        run_cmd(compile_script.string() + " " + shell_quote(tile_dir.string()) + " --print-hashes",
                opt.root);
      }

      const std::filesystem::path art_path = tile_dir / "render-artifact.json";
      IndexEntry entry;
      entry.z = tile.z;
      entry.x = tile.x;
      entry.y = tile.y;
      entry.west = bb.west;
      entry.south = bb.south;
      entry.east = bb.east;
      entry.north = bb.north;
      entry.fixture_relpath = "pyramid/tiles/" + std::to_string(tile.z) + "/" +
                              std::to_string(tile.x) + "/" + std::to_string(tile.y) +
                              "/render-artifact.json";
      entry.artifact_url = "data/artifacts/" + cell_lower + "/z" + std::to_string(tile.z) + "/x" +
                           std::to_string(tile.x) + "/y" + std::to_string(tile.y) + ".json";

      if (std::filesystem::exists(art_path)) {
        const IndexEntry stats = artifact_stats(art_path);
        entry.artifact_id = stats.artifact_id;
        entry.vertex_count = stats.vertex_count;
        entry.index_count = stats.index_count;
        entry.packet_sha256 = stats.packet_sha256;

        const std::filesystem::path web_path = opt.root / "web" / entry.artifact_url;
        std::filesystem::create_directories(web_path.parent_path());
        std::filesystem::copy_file(art_path, web_path, std::filesystem::copy_options::overwrite_existing);
      }

      entry_map[key] = std::move(entry);
      std::cerr << "  z" << tile.z << "/" << tile.x << "/" << tile.y
                << " verts=" << entry_map[key].vertex_count << "\n";
    }

    std::vector<IndexEntry> entries;
    entries.reserve(entry_map.size());
    for (auto& [k, e] : entry_map) {
      (void)k;
      entries.push_back(std::move(e));
    }
    std::sort(entries.begin(), entries.end(), [](const IndexEntry& a, const IndexEntry& b) {
      if (a.z != b.z) return a.z < b.z;
      if (a.x != b.x) return a.x < b.x;
      return a.y < b.y;
    });

    std::vector<int> nodata_z_levels = opt.nodata_z;
    if (std::filesystem::exists(index_path)) {
      const Json existing = JsonParser(read_file(index_path)).parse();
      if (const Json* nodata = existing.get("nodata_z_levels"); nodata && nodata->is_array()) {
        for (const Json& z : nodata->array()) {
          if (z.is_number()) nodata_z_levels.push_back(static_cast<int>(z.number()));
        }
      }
    }
    std::sort(nodata_z_levels.begin(), nodata_z_levels.end());
    nodata_z_levels.erase(std::unique(nodata_z_levels.begin(), nodata_z_levels.end()),
                          nodata_z_levels.end());

    write_index(opt, entries, nodata_z_levels, index_path, web_index);

    std::cerr << "pyramid: " << entries.size() << " tiles -> " << index_path << "\n";
    std::cout << web_index << "\n";
    return 0;
  } catch (const std::runtime_error& e) {
    if (std::string(e.what()) == "usage") {
      std::cerr << "usage: render-artifact-pyramid ENC OUT_DIR --cell-id ID --cell-bbox W,S,E,N "
                   "[--z-min 11] [--z-max 15] [--nodata-z 16] [--append] [--skip-compile] "
                   "[--max-tiles N] [--pixel-size 2048] [--reference-zoom 13] [--simplify-px 1.0]\n";
      return 2;
    }
    std::cerr << "FAIL render-artifact-pyramid: " << e.what() << "\n";
    return 1;
  }
}
