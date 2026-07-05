#include "viewport_scheduler_json.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <variant>
#include <vector>

namespace helm::schedule::json {
namespace {

struct Json;
using JsonArray = std::vector<Json>;
using JsonObject = std::map<std::string, Json>;

struct Json {
  enum class Type { Null, Bool, Number, String, Array, Object };
  Type type = Type::Null;
  bool bool_value = false;
  double number_value = 0;
  std::string number_text;
  std::string string_value;
  JsonArray array_value;
  JsonObject object_value;

  [[nodiscard]] bool is_null() const { return type == Type::Null; }
  [[nodiscard]] bool is_bool() const { return type == Type::Bool; }
  [[nodiscard]] bool is_number() const { return type == Type::Number; }
  [[nodiscard]] bool is_string() const { return type == Type::String; }
  [[nodiscard]] bool is_array() const { return type == Type::Array; }
  [[nodiscard]] bool is_object() const { return type == Type::Object; }

  [[nodiscard]] const JsonObject& object() const {
    if (!is_object()) throw std::runtime_error("expected JSON object");
    return object_value;
  }

  [[nodiscard]] const JsonArray& array() const {
    if (!is_array()) throw std::runtime_error("expected JSON array");
    return array_value;
  }

  [[nodiscard]] const std::string& string() const {
    if (!is_string()) throw std::runtime_error("expected JSON string");
    return string_value;
  }

  [[nodiscard]] double number() const {
    if (!is_number()) throw std::runtime_error("expected JSON number");
    return number_value;
  }

  [[nodiscard]] const Json* get(std::string_view key) const {
    if (!is_object()) return nullptr;
    const auto it = object_value.find(std::string(key));
    return it == object_value.end() ? nullptr : &it->second;
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
    if (ch == '{') return parse_object();
    if (ch == '[') return parse_array();
    if (ch == '"') return parse_string_value();
    if (ch == 't') return parse_literal("true", true);
    if (ch == 'f') return parse_literal("false", false);
    if (ch == 'n') return parse_null();
    if (ch == '-' || (ch >= '0' && ch <= '9')) return parse_number();
    throw error("unexpected value");
  }

  [[nodiscard]] Json parse_literal(std::string_view literal, bool value) {
    if (text_.compare(pos_, literal.size(), literal) != 0) throw error("invalid literal");
    pos_ += literal.size();
    Json out;
    out.type = Json::Type::Bool;
    out.bool_value = value;
    return out;
  }

  [[nodiscard]] Json parse_null() {
    if (text_.compare(pos_, 4, "null") != 0) throw error("invalid literal");
    pos_ += 4;
    return Json{};
  }

  [[nodiscard]] Json parse_object() {
    expect('{');
    Json out;
    out.type = Json::Type::Object;
    if (consume('}')) return out;
    while (true) {
      if (peek() != '"') throw error("expected object key");
      std::string key = parse_string();
      expect(':');
      out.object_value.emplace(std::move(key), parse_value());
      if (consume('}')) return out;
      expect(',');
    }
  }

  [[nodiscard]] Json parse_array() {
    expect('[');
    Json out;
    out.type = Json::Type::Array;
    if (consume(']')) return out;
    while (true) {
      out.array_value.push_back(parse_value());
      if (consume(']')) return out;
      expect(',');
    }
  }

  [[nodiscard]] Json parse_string_value() {
    Json out;
    out.type = Json::Type::String;
    out.string_value = parse_string();
    return out;
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

  [[nodiscard]] Json parse_number() {
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
    Json out;
    out.type = Json::Type::Number;
    out.number_text = text_.substr(start, pos_ - start);
    out.number_value = std::stod(out.number_text);
    return out;
  }

  std::string text_;
  std::size_t pos_ = 0;
};

void append_json_string(const std::string& value, std::string& out) {
  out.push_back('"');
  for (const unsigned char c : value) {
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\b': out += "\\b"; break;
      case '\f': out += "\\f"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default: out.push_back(static_cast<char>(c));
    }
  }
  out.push_back('"');
}

void append_canonical(const Json& value, std::string& out) {
  switch (value.type) {
    case Json::Type::Null:
      out += "null";
      break;
    case Json::Type::Bool:
      out += value.bool_value ? "true" : "false";
      break;
    case Json::Type::Number:
      out += value.number_text;
      break;
    case Json::Type::String:
      append_json_string(value.string_value, out);
      break;
    case Json::Type::Array:
      out.push_back('[');
      for (std::size_t i = 0; i < value.array_value.size(); ++i) {
        if (i) out.push_back(',');
        append_canonical(value.array_value[i], out);
      }
      out.push_back(']');
      break;
    case Json::Type::Object:
      out.push_back('{');
      for (auto it = value.object_value.begin(); it != value.object_value.end(); ++it) {
        if (it != value.object_value.begin()) out.push_back(',');
        append_json_string(it->first, out);
        out.push_back(':');
        append_canonical(it->second, out);
      }
      out.push_back('}');
      break;
  }
}

class Sha256 {
 public:
  Sha256() : bit_len_(0), buffer_len_(0) {
    h_[0] = 0x6a09e667u;
    h_[1] = 0xbb67ae85u;
    h_[2] = 0x3c6ef372u;
    h_[3] = 0xa54ff53au;
    h_[4] = 0x510e527fu;
    h_[5] = 0x9b05688cu;
    h_[6] = 0x1f83d9abu;
    h_[7] = 0x5be0cd19u;
  }

  void update(const unsigned char* data, std::size_t len) {
    bit_len_ += static_cast<std::uint64_t>(len) * 8u;
    for (std::size_t i = 0; i < len; ++i) {
      buffer_[buffer_len_++] = data[i];
      if (buffer_len_ == 64) {
        transform(buffer_);
        buffer_len_ = 0;
      }
    }
  }

  std::string hex_digest() {
    const std::uint64_t input_bits = bit_len_;
    buffer_[buffer_len_++] = 0x80u;
    if (buffer_len_ > 56) {
      while (buffer_len_ < 64) buffer_[buffer_len_++] = 0;
      transform(buffer_);
      buffer_len_ = 0;
    }
    while (buffer_len_ < 56) buffer_[buffer_len_++] = 0;
    for (int i = 7; i >= 0; --i) {
      buffer_[buffer_len_++] = static_cast<unsigned char>((input_bits >> (i * 8)) & 0xffu);
    }
    transform(buffer_);

    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (std::size_t i = 0; i < 8; ++i) out << std::setw(8) << h_[i];
    return out.str();
  }

 private:
  static std::uint32_t rotr(std::uint32_t v, std::uint32_t n) {
    return (v >> n) | (v << (32 - n));
  }

  static std::uint32_t ch(std::uint32_t x, std::uint32_t y, std::uint32_t z) {
    return (x & y) ^ (~x & z);
  }

  static std::uint32_t maj(std::uint32_t x, std::uint32_t y, std::uint32_t z) {
    return (x & y) ^ (x & z) ^ (y & z);
  }

  static std::uint32_t big0(std::uint32_t x) {
    return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22);
  }

  static std::uint32_t big1(std::uint32_t x) {
    return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25);
  }

  static std::uint32_t small0(std::uint32_t x) {
    return rotr(x, 7) ^ rotr(x, 18) ^ (x >> 3);
  }

  static std::uint32_t small1(std::uint32_t x) {
    return rotr(x, 17) ^ rotr(x, 19) ^ (x >> 10);
  }

  void transform(const unsigned char block[64]) {
    static const std::uint32_t k[64] = {
        0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u, 0x3956c25bu, 0x59f111f1u,
        0x923f82a4u, 0xab1c5ed5u, 0xd807aa98u, 0x12835b01u, 0x243185beu, 0x550c7dc3u,
        0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u, 0xc19bf174u, 0xe49b69c1u, 0xefbe4786u,
        0x0fc19dc6u, 0x240ca1ccu, 0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau,
        0x983e5152u, 0xa831c66du, 0xb00327c8u, 0xbf597fc7u, 0xc6e00bf3u, 0xd5a79147u,
        0x06ca6351u, 0x14292967u, 0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu, 0x53380d13u,
        0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u, 0xa2bfe8a1u, 0xa81a664bu,
        0xc24b8b70u, 0xc76c51a3u, 0xd192e819u, 0xd6990624u, 0xf40e3585u, 0x106aa070u,
        0x19a4c116u, 0x1e376c08u, 0x2748774cu, 0x34b0bcb5u, 0x391c0cb3u, 0x4ed8aa4au,
        0x5b9cca4fu, 0x682e6ff3u, 0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u,
        0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u};

    std::uint32_t w[64];
    for (std::size_t i = 0; i < 16; ++i) {
      w[i] = (static_cast<std::uint32_t>(block[i * 4]) << 24) |
             (static_cast<std::uint32_t>(block[i * 4 + 1]) << 16) |
             (static_cast<std::uint32_t>(block[i * 4 + 2]) << 8) |
             static_cast<std::uint32_t>(block[i * 4 + 3]);
    }
    for (std::size_t i = 16; i < 64; ++i) {
      w[i] = small1(w[i - 2]) + w[i - 7] + small0(w[i - 15]) + w[i - 16];
    }

    std::uint32_t a = h_[0], b = h_[1], c = h_[2], d = h_[3];
    std::uint32_t e = h_[4], f = h_[5], g = h_[6], h = h_[7];
    for (std::size_t i = 0; i < 64; ++i) {
      const std::uint32_t t1 = h + big1(e) + ch(e, f, g) + k[i] + w[i];
      const std::uint32_t t2 = big0(a) + maj(a, b, c);
      h = g;
      g = f;
      f = e;
      e = d + t1;
      d = c;
      c = b;
      b = a;
      a = t1 + t2;
    }
    h_[0] += a;
    h_[1] += b;
    h_[2] += c;
    h_[3] += d;
    h_[4] += e;
    h_[5] += f;
    h_[6] += g;
    h_[7] += h;
  }

  std::uint32_t h_[8];
  std::uint64_t bit_len_;
  unsigned char buffer_[64];
  std::size_t buffer_len_;
};

[[nodiscard]] std::string sha256_bytes(const std::string& bytes) {
  Sha256 sha;
  sha.update(reinterpret_cast<const unsigned char*>(bytes.data()), bytes.size());
  return sha.hex_digest();
}

[[nodiscard]] std::string string_or(const Json* value, const std::string& fallback = {}) {
  return value && value->is_string() ? value->string() : fallback;
}

[[nodiscard]] bool bool_or(const Json* value, bool fallback) {
  return value && value->is_bool() ? value->bool_value : fallback;
}

[[nodiscard]] double number_or(const Json* value, double fallback) {
  return value && value->is_number() ? value->number() : fallback;
}

[[nodiscard]] std::uint32_t uint_or(const Json* value, std::uint32_t fallback) {
  return value && value->is_number() ? static_cast<std::uint32_t>(value->number()) : fallback;
}

[[nodiscard]] std::uint64_t u64_or(const Json* value, std::uint64_t fallback) {
  return value && value->is_number() ? static_cast<std::uint64_t>(value->number()) : fallback;
}

[[nodiscard]] TileCoord parse_tile(const Json& value) {
  const JsonObject& obj = value.object();
  TileCoord tile;
  if (const auto it = obj.find("z"); it != obj.end()) tile.z = uint_or(&it->second, 0);
  if (const auto it = obj.find("x"); it != obj.end()) tile.x = uint_or(&it->second, 0);
  if (const auto it = obj.find("y"); it != obj.end()) tile.y = uint_or(&it->second, 0);
  return tile;
}

[[nodiscard]] ScheduleIntent parse_intent(const std::string& value) {
  if (value == "prefetch") return ScheduleIntent::Prefetch;
  if (value == "revalidate") return ScheduleIntent::Revalidate;
  return ScheduleIntent::Visible;
}

[[nodiscard]] EntryRole parse_role(const std::string& value) {
  if (value == "overscan") return EntryRole::Overscan;
  if (value == "neighbor") return EntryRole::Neighbor;
  if (value == "zoom_adjacent") return EntryRole::ZoomAdjacent;
  if (value == "prefetch") return EntryRole::Prefetch;
  return EntryRole::Visible;
}

[[nodiscard]] EntryKind parse_kind(const std::string& value) {
  if (value == "artifact_packet") return EntryKind::ArtifactPacket;
  if (value == "render_model") return EntryKind::RenderModel;
  return EntryKind::Tile;
}

[[nodiscard]] StalePolicy parse_stale_policy(const std::string& value) {
  if (value == "stale_while_revalidate") return StalePolicy::StaleWhileRevalidate;
  if (value == "stale_ok") return StalePolicy::StaleOk;
  return StalePolicy::Strict;
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

[[nodiscard]] std::string number_to_string(double value) {
  if (value == 0.0) value = 0.0;
  if (std::floor(value) == value && std::abs(value) < 9.007199254740992e15) {
    return std::to_string(static_cast<long long>(value));
  }
  std::ostringstream out;
  out << std::setprecision(15) << value;
  return out.str();
}

void write_number(std::ostream& out, double value) { out << number_to_string(value); }

}  // namespace

std::string CanonicalJson(const std::string& text) {
  std::string out;
  append_canonical(JsonParser(text).parse(), out);
  return out;
}

std::string Sha256Json(const std::string& json_text) {
  return sha256_bytes(CanonicalJson(json_text));
}

ScheduleRequest ParseScheduleRequest(const std::string& text) {
  const Json root = JsonParser(text).parse();
  if (!root.is_object()) throw ScheduleError("request must be a JSON object");

  ScheduleRequest request;
  if (const Json* schema = root.get("schema"); schema && schema->is_string()) {
    request.schema_version = schema->string();
  }
  request.request_id = string_or(root.get("request_id"));
  request.intent = parse_intent(string_or(root.get("intent"), "visible"));

  if (const Json* visible = root.get("visible"); visible && visible->is_object()) {
    request.visible.projection = string_or(visible->get("projection"), "web_mercator_tile");
    request.visible.z = uint_or(visible->get("z"), 0);
    if (const Json* center = visible->get("center"); center && center->is_object()) {
      const Json* lon = center->get("lon");
      const Json* lat = center->get("lat");
      if (lon && lon->is_number() && lat && lat->is_number()) {
        request.visible.center.lon = lon->number();
        request.visible.center.lat = lat->number();
        request.visible.has_center = true;
      }
    }
    if (const Json* anchor = visible->get("anchor_tile"); anchor && anchor->is_object()) {
      request.visible.anchor_tile = parse_tile(*anchor);
    }
    if (const Json* viewport = visible->get("viewport_px"); viewport && viewport->is_array()) {
      const JsonArray& px = viewport->array();
      if (px.size() >= 2) {
        request.visible.viewport_width_px = uint_or(&px[0], 0);
        request.visible.viewport_height_px = uint_or(&px[1], 0);
      }
    }
    request.visible.device_pixel_ratio = number_or(visible->get("device_pixel_ratio"), 1);
    request.visible.rotation_deg = number_or(visible->get("rotation_deg"), 0);
  }

  if (const Json* overscan = root.get("overscan"); overscan && overscan->is_object()) {
    request.overscan.margin_px = uint_or(overscan->get("margin_px"), 16);
    request.overscan.margin_tiles = uint_or(overscan->get("margin_tiles"), 1);
  }

  if (const Json* neighbor = root.get("neighbor_policy"); neighbor && neighbor->is_object()) {
    request.neighbor_policy.cardinal = bool_or(neighbor->get("cardinal"), true);
    request.neighbor_policy.diagonal = bool_or(neighbor->get("diagonal"), true);
    request.neighbor_policy.ring_count = uint_or(neighbor->get("ring_count"), 1);
  }

  if (const Json* zoom = root.get("zoom_policy"); zoom && zoom->is_object()) {
    request.zoom_policy.include_children = bool_or(zoom->get("include_children"), true);
    request.zoom_policy.include_parent = bool_or(zoom->get("include_parent"), true);
    if (const Json* offsets = zoom->get("adjacent_offsets"); offsets && offsets->is_array()) {
      for (const Json& item : offsets->array()) {
        if (!item.is_number()) throw ScheduleError("zoom_policy.adjacent_offsets must contain integers");
        request.zoom_policy.adjacent_offsets.push_back(static_cast<int>(item.number()));
      }
    }
  }

  request.display_fingerprint = string_or(root.get("display_fingerprint"));
  request.source_epoch_hint = string_or(root.get("source_epoch_hint"));
  request.client_epoch = u64_or(root.get("client_epoch"), 0);

  if (const Json* renderer = root.get("renderer"); renderer && renderer->is_object()) {
    request.renderer.backend = string_or(renderer->get("backend"), "vulkan");
    request.renderer.scene_schema = string_or(renderer->get("scene_schema"), "helm.render.model.v1");
    request.renderer.renderer_sha = string_or(renderer->get("renderer_sha"));
  }

  return request;
}

ScheduleResponse ParseScheduleResponse(const std::string& text) {
  const Json root = JsonParser(text).parse();
  if (!root.is_object()) throw ScheduleError("response must be a JSON object");

  ScheduleResponse response;
  if (const Json* schema = root.get("schema"); schema && schema->is_string()) {
    response.schema_version = schema->string();
  }
  response.request_id = string_or(root.get("request_id"));
  response.source_epoch = string_or(root.get("source_epoch"));
  response.cache_epoch = string_or(root.get("cache_epoch"));

  if (const Json* entries = root.get("entries"); entries && entries->is_array()) {
    for (const Json& item : entries->array()) {
      if (!item.is_object()) continue;
      ScheduleEntry entry;
      entry.entry_id = string_or(item.get("entry_id"));
      entry.kind = parse_kind(string_or(item.get("kind"), "tile"));
      entry.role = parse_role(string_or(item.get("role"), "visible"));
      entry.priority = static_cast<std::int32_t>(number_or(item.get("priority"), 0));
      if (const Json* tile = item.get("tile"); tile && tile->is_object()) {
        entry.tile = parse_tile(*tile);
      }
      entry.overscan_px = uint_or(item.get("overscan_px"), 0);
      entry.cache_key = string_or(item.get("cache_key"));
      entry.stale_policy = parse_stale_policy(string_or(item.get("stale_policy"), "strict"));
      entry.blend_weight = number_or(item.get("blend_weight"), 1);
      response.entries.push_back(std::move(entry));
    }
  }

  if (const Json* totals = root.get("totals"); totals && totals->is_object()) {
    response.totals.entries = uint_or(totals->get("entries"), 0);
    response.totals.visible = uint_or(totals->get("visible"), 0);
    response.totals.overscan = uint_or(totals->get("overscan"), 0);
    response.totals.neighbor = uint_or(totals->get("neighbor"), 0);
    response.totals.zoom_adjacent = uint_or(totals->get("zoom_adjacent"), 0);
  }

  if (const Json* diagnostics = root.get("diagnostics"); diagnostics && diagnostics->is_array()) {
    for (const Json& item : diagnostics->array()) {
      if (!item.is_object()) continue;
      ScheduleDiagnostic diag;
      diag.severity = string_or(item.get("severity"));
      diag.code = string_or(item.get("code"));
      diag.message = string_or(item.get("message"));
      response.diagnostics.push_back(std::move(diag));
    }
  }

  return response;
}

std::string ScheduleResponseToJson(const ScheduleResponse& response) {
  std::ostringstream out;
  out << "{\n";
  write_key(out, 1, "schema");
  write_string(out, response.schema_version);
  out << ",\n";
  write_key(out, 1, "request_id");
  write_string(out, response.request_id);
  out << ",\n";
  write_key(out, 1, "source_epoch");
  write_string(out, response.source_epoch);
  out << ",\n";
  write_key(out, 1, "cache_epoch");
  write_string(out, response.cache_epoch);
  out << ",\n";
  write_key(out, 1, "entries");
  out << "[\n";
  for (std::size_t i = 0; i < response.entries.size(); ++i) {
    const ScheduleEntry& entry = response.entries[i];
    indent(out, 2);
    out << "{\n";
    write_key(out, 3, "entry_id");
    write_string(out, entry.entry_id);
    out << ",\n";
    write_key(out, 3, "kind");
    write_string(out, entry.kind == EntryKind::Tile ? "tile"
                                                    : entry.kind == EntryKind::ArtifactPacket
                                                          ? "artifact_packet"
                                                          : "render_model");
    out << ",\n";
    write_key(out, 3, "role");
    write_string(out, EntryRoleName(entry.role));
    out << ",\n";
    write_key(out, 3, "priority");
    write_number(out, entry.priority);
    out << ",\n";
    write_key(out, 3, "tile");
    out << "{\n";
    write_key(out, 4, "z");
    write_number(out, entry.tile.z);
    out << ",\n";
    write_key(out, 4, "x");
    write_number(out, entry.tile.x);
    out << ",\n";
    write_key(out, 4, "y");
    write_number(out, entry.tile.y);
    out << "\n";
    indent(out, 3);
    out << "},\n";
    write_key(out, 3, "overscan_px");
    write_number(out, entry.overscan_px);
    out << ",\n";
    write_key(out, 3, "cache_key");
    write_string(out, entry.cache_key);
    out << ",\n";
    write_key(out, 3, "stale_policy");
    write_string(out, StalePolicyName(entry.stale_policy));
    out << ",\n";
    write_key(out, 3, "blend_weight");
    write_number(out, entry.blend_weight);
    out << "\n";
    indent(out, 2);
    out << "}";
    if (i + 1 < response.entries.size()) out << ",";
    out << "\n";
  }
  indent(out, 1);
  out << "],\n";
  write_key(out, 1, "totals");
  out << "{\n";
  write_key(out, 2, "entries");
  write_number(out, response.totals.entries);
  out << ",\n";
  write_key(out, 2, "visible");
  write_number(out, response.totals.visible);
  out << ",\n";
  write_key(out, 2, "overscan");
  write_number(out, response.totals.overscan);
  out << ",\n";
  write_key(out, 2, "neighbor");
  write_number(out, response.totals.neighbor);
  out << ",\n";
  write_key(out, 2, "zoom_adjacent");
  write_number(out, response.totals.zoom_adjacent);
  out << "\n";
  indent(out, 1);
  out << "},\n";
  write_key(out, 1, "diagnostics");
  out << "[";
  for (std::size_t i = 0; i < response.diagnostics.size(); ++i) {
    if (i) out << ", ";
    const ScheduleDiagnostic& diag = response.diagnostics[i];
    out << "{\n";
    write_key(out, 2, "severity");
    write_string(out, diag.severity);
    out << ",\n";
    write_key(out, 2, "code");
    write_string(out, diag.code);
    out << ",\n";
    write_key(out, 2, "message");
    write_string(out, diag.message);
    out << "\n";
    indent(out, 1);
    out << "}";
  }
  out << "]\n";
  out << "}\n";
  return out.str();
}

}  // namespace helm::schedule::json
