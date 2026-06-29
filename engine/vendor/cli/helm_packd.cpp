// helm_packd.cpp -- local-only Helm pack daemon for BYO MBTiles/PMTiles packs.
//
// First OFFLINE-16 slice:
//   GET  /health                     -> daemon health + pack count
//   GET  /catalog                    -> public pack metadata, no filesystem paths
//   HEAD /catalog                    -> catalog probe headers
//   GET  /{pack}/{z}/{x}/{y}.{ext}   -> MBTiles tile_data, XYZ request -> TMS row
//   GET  /{pack}.pmtiles             -> PMTiles archive bytes with HTTP Range
//   HEAD /{pack}.pmtiles             -> PMTiles protocol probe
//
// Python pipeline/mbtiles_server.py remains the reference/oracle until the C++
// service reaches full parity. OFFLINE-17 owns /layers, /prefetch, and /bundle.

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dirent.h>
#include <fcntl.h>
#include <fstream>
#include <iomanip>
#include <map>
#include <memory>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>
#include <utility>
#include <vector>

#include <sqlite3.h>

#include "ixwebsocket/IXHttp.h"
#include "ixwebsocket/IXHttpServer.h"
#include "ixwebsocket/IXConnectionState.h"

namespace {

struct SqliteCloser {
  void operator()(sqlite3* db) const {
    if (db) sqlite3_close(db);
  }
};

struct PackRecord {
  std::string id;
  std::string title;
  std::string path;
  std::string container;
  std::string format = "png";
  std::string extension = "png";
  std::string type = "raster";
  std::string kind = "raster";
  std::string source = "local";
  std::string license = "local-user-owned";
  std::string attribution;
  std::string bounds;
  int minzoom = 0;
  int maxzoom = 17;
  std::uint64_t size_bytes = 0;
  std::uint64_t modified_epoch = 0;
  bool range = false;
  int pmtiles_version = 0;
  std::uint64_t addressed_tiles = 0;
  std::uint64_t tile_entries = 0;
  std::uint64_t tile_contents = 0;
  std::unique_ptr<sqlite3, SqliteCloser> db;
  mutable std::mutex db_mutex;
};

using Headers = ix::WebSocketHttpHeaders;

std::string get_env(const char* name, const std::string& fallback = std::string()) {
  const char* value = std::getenv(name);
  return value && *value ? std::string(value) : fallback;
}

bool starts_with(const std::string& s, const std::string& prefix) {
  return s.size() >= prefix.size() && std::equal(prefix.begin(), prefix.end(), s.begin());
}

bool ends_with(const std::string& s, const std::string& suffix) {
  return s.size() >= suffix.size() && std::equal(suffix.rbegin(), suffix.rend(), s.rbegin());
}

std::string lower(std::string s) {
  for (char& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  return s;
}

std::string dirname_join(const std::string& base, const std::string& name) {
  if (base.empty() || base == ".") return name;
  return base.back() == '/' ? base + name : base + "/" + name;
}

bool is_abs_path(const std::string& path) {
  return !path.empty() && path[0] == '/';
}

std::string expand_user(std::string path) {
  if (path == "~" || starts_with(path, "~/")) {
    const std::string home = get_env("HOME", ".");
    return home + path.substr(1);
  }
  return path;
}

std::string pack_path(const std::string& base, const std::string& filename) {
  const std::string expanded = expand_user(filename);
  if (is_abs_path(expanded)) return expanded;
  return dirname_join(base, expanded);
}

std::string basename_no_ext(const std::string& path) {
  std::string name = path;
  const std::size_t slash = name.find_last_of('/');
  if (slash != std::string::npos) name = name.substr(slash + 1);
  const std::size_t dot = name.find_last_of('.');
  if (dot != std::string::npos) name = name.substr(0, dot);
  return name;
}

std::string extension_of(const std::string& path) {
  const std::size_t dot = path.find_last_of('.');
  return dot == std::string::npos ? std::string() : lower(path.substr(dot));
}

bool stat_file(const std::string& path, struct stat& st) {
  return ::stat(path.c_str(), &st) == 0 && S_ISREG(st.st_mode);
}

std::string json_escape(const std::string& s) {
  std::ostringstream out;
  for (unsigned char c : s) {
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
          out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << static_cast<int>(c);
        } else {
          out << static_cast<char>(c);
        }
    }
  }
  return out.str();
}

std::string url_decode(const std::string& s) {
  std::string out;
  out.reserve(s.size());
  for (std::size_t i = 0; i < s.size(); ++i) {
    if (s[i] == '%' && i + 2 < s.size() && std::isxdigit(static_cast<unsigned char>(s[i + 1])) &&
        std::isxdigit(static_cast<unsigned char>(s[i + 2]))) {
      const std::string hex = s.substr(i + 1, 2);
      out.push_back(static_cast<char>(std::strtol(hex.c_str(), nullptr, 16)));
      i += 2;
    } else if (s[i] == '+') {
      out.push_back(' ');
    } else {
      out.push_back(s[i]);
    }
  }
  return out;
}

std::string url_encode(const std::string& s) {
  std::ostringstream out;
  out << std::hex << std::uppercase;
  for (unsigned char c : s) {
    if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') ||
        c == '-' || c == '_' || c == '.' || c == '~') {
      out << static_cast<char>(c);
    } else {
      out << '%' << std::setw(2) << std::setfill('0') << static_cast<int>(c);
    }
  }
  return out.str();
}

std::string request_path(const std::string& uri) {
  const std::size_t q = uri.find('?');
  return q == std::string::npos ? uri : uri.substr(0, q);
}

std::string header_value(const Headers& headers, const std::string& name) {
  const std::string want = lower(name);
  for (const auto& kv : headers) {
    if (lower(kv.first) == want) return kv.second;
  }
  return std::string();
}

std::string origin_for(const ix::HttpRequestPtr& req, const std::string& bind, int port) {
  std::string proto = header_value(req->headers, "X-Forwarded-Proto");
  if (proto.empty()) proto = "http";
  const std::size_t comma = proto.find(',');
  if (comma != std::string::npos) proto = proto.substr(0, comma);
  std::string host = header_value(req->headers, "Host");
  if (host.empty()) {
    host = (bind == "0.0.0.0" || bind.empty()) ? "127.0.0.1" : bind;
    host += ":" + std::to_string(port);
  }
  return proto + "://" + host;
}

std::string content_type_for(const std::string& ext) {
  const std::string e = lower(ext);
  if (e == "png") return "image/png";
  if (e == "jpg" || e == "jpeg") return "image/jpeg";
  if (e == "webp") return "image/webp";
  if (e == "avif") return "image/avif";
  if (e == "mvt" || e == "pbf") return "application/vnd.mapbox-vector-tile";
  if (e == "pmtiles") return "application/vnd.pmtiles";
  return "application/octet-stream";
}

void base_headers(Headers& h) {
  h["Access-Control-Allow-Origin"] = "*";
  h["Access-Control-Allow-Headers"] = "Range, Content-Type";
  h["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS";
  h["Access-Control-Expose-Headers"] = "Accept-Ranges, Content-Length, Content-Range, ETag";
  h["Cache-Control"] = "no-cache";
}

ix::HttpResponsePtr response(int status, const std::string& reason, Headers h, std::string body) {
  h["Content-Length"] = std::to_string(body.size());
  return std::make_shared<ix::HttpResponse>(status, reason, ix::HttpErrorCode::Ok, h, body);
}

ix::HttpResponsePtr empty_response(int status, const std::string& reason, Headers h) {
  return response(status, reason, std::move(h), std::string());
}

int safe_int(const std::string& value, int fallback) {
  if (value.empty()) return fallback;
  char* end = nullptr;
  long parsed = std::strtol(value.c_str(), &end, 10);
  return end && *end == '\0' ? static_cast<int>(parsed) : fallback;
}

std::string sqlite_text(sqlite3_stmt* stmt, int col) {
  const unsigned char* text = sqlite3_column_text(stmt, col);
  return text ? reinterpret_cast<const char*>(text) : std::string();
}

std::map<std::string, std::string> read_mbtiles_metadata(sqlite3* db) {
  std::map<std::string, std::string> metadata;
  sqlite3_stmt* stmt = nullptr;
  if (sqlite3_prepare_v2(db, "SELECT name, value FROM metadata", -1, &stmt, nullptr) != SQLITE_OK) {
    return metadata;
  }
  while (sqlite3_step(stmt) == SQLITE_ROW) {
    metadata[sqlite_text(stmt, 0)] = sqlite_text(stmt, 1);
  }
  sqlite3_finalize(stmt);
  return metadata;
}

std::uint64_t u64_le(const unsigned char* p) {
  std::uint64_t v = 0;
  for (int i = 7; i >= 0; --i) v = (v << 8) | p[i];
  return v;
}

std::int32_t i32_le(const unsigned char* p) {
  std::uint32_t v = 0;
  for (int i = 3; i >= 0; --i) v = (v << 8) | p[i];
  return static_cast<std::int32_t>(v);
}

std::string bounds_string_from_pmtiles_header(const unsigned char* header) {
  const double west = i32_le(header + 102) / 10000000.0;
  const double south = i32_le(header + 106) / 10000000.0;
  const double east = i32_le(header + 110) / 10000000.0;
  const double north = i32_le(header + 114) / 10000000.0;
  std::ostringstream out;
  out << std::setprecision(8) << west << "," << south << "," << east << "," << north;
  return out.str();
}

std::string pmtiles_format(int tile_type) {
  switch (tile_type) {
    case 1: return "mvt";
    case 2: return "png";
    case 3: return "jpg";
    case 4: return "webp";
    case 5: return "avif";
    default: return "bin";
  }
}

std::string kind_for(const std::string& id, const std::string& title, const std::string& fmt, const std::string& type) {
  const std::string text = lower(id + " " + title + " " + fmt);
  if (text.find("sat") != std::string::npos || text.find("sentinel") != std::string::npos ||
      text.find("imagery") != std::string::npos || text.find("photo") != std::string::npos) {
    return "satellite";
  }
  if (text.find("chart") != std::string::npos || text.find("navionics") != std::string::npos ||
      text.find("noaa") != std::string::npos || text.find("enc") != std::string::npos) {
    return "chart";
  }
  return type == "vector" ? "vector" : "raster";
}

std::vector<std::pair<std::string, std::string>> parse_pack_map(const std::string& base) {
  std::vector<std::pair<std::string, std::string>> packs;
  const std::string raw = get_env("HELM_MBTILES_PACKS");
  if (!raw.empty()) {
    std::size_t pos = 0;
    while (true) {
      const std::size_t k1 = raw.find('"', pos);
      if (k1 == std::string::npos) break;
      const std::size_t k2 = raw.find('"', k1 + 1);
      const std::size_t colon = raw.find(':', k2 == std::string::npos ? k1 : k2);
      const std::size_t v1 = raw.find('"', colon == std::string::npos ? k1 : colon);
      const std::size_t v2 = raw.find('"', v1 == std::string::npos ? k1 : v1 + 1);
      if (k2 == std::string::npos || colon == std::string::npos || v1 == std::string::npos || v2 == std::string::npos) break;
      packs.emplace_back(raw.substr(k1 + 1, k2 - k1 - 1), raw.substr(v1 + 1, v2 - v1 - 1));
      pos = v2 + 1;
    }
    return packs;
  }

  DIR* dir = ::opendir(base.c_str());
  if (!dir) return packs;
  while (dirent* ent = ::readdir(dir)) {
    const std::string filename = ent->d_name;
    const std::string ext = extension_of(filename);
    if (ext == ".mbtiles" || ext == ".pmtiles") {
      packs.emplace_back(basename_no_ext(filename), filename);
    }
  }
  ::closedir(dir);
  std::sort(packs.begin(), packs.end());
  return packs;
}

bool open_mbtiles_pack(const std::string& id, const std::string& path, const struct stat& st, PackRecord& rec, std::string& error) {
  sqlite3* raw = nullptr;
  const std::string uri = "file:" + path + "?mode=ro&immutable=1";
  if (sqlite3_open_v2(uri.c_str(), &raw, SQLITE_OPEN_READONLY | SQLITE_OPEN_URI, nullptr) != SQLITE_OK) {
    error = raw ? sqlite3_errmsg(raw) : "sqlite open failed";
    if (raw) sqlite3_close(raw);
    return false;
  }
  rec.db.reset(raw);
  const auto metadata = read_mbtiles_metadata(rec.db.get());
  auto get = [&](const char* key) -> std::string {
    const auto it = metadata.find(key);
    return it == metadata.end() ? std::string() : it->second;
  };

  rec.id = id;
  rec.path = path;
  rec.container = "mbtiles";
  rec.title = get("name").empty() ? id : get("name");
  rec.format = lower(get("format").empty() ? "png" : get("format"));
  if (rec.format == "jpeg") rec.format = "jpg";
  rec.extension = rec.format == "jpg" ? "jpg" : rec.format;
  rec.type = (rec.format == "pbf" || rec.format == "mvt") ? "vector" : "raster";
  rec.kind = get("kind").empty() ? kind_for(rec.id, rec.title, rec.format, rec.type) : get("kind");
  rec.source = get("source").empty() ? "local" : get("source");
  rec.license = get("license").empty() ? "local-user-owned" : get("license");
  rec.attribution = get("attribution");
  rec.bounds = get("bounds");
  rec.minzoom = safe_int(get("minzoom"), 0);
  rec.maxzoom = safe_int(get("maxzoom"), 17);
  rec.size_bytes = static_cast<std::uint64_t>(st.st_size);
  rec.modified_epoch = static_cast<std::uint64_t>(st.st_mtime);
  return true;
}

bool open_pmtiles_pack(const std::string& id, const std::string& path, const struct stat& st, PackRecord& rec, std::string& error) {
  std::ifstream in(path, std::ios::binary);
  if (!in) {
    error = "cannot open file";
    return false;
  }
  unsigned char header[127] = {0};
  in.read(reinterpret_cast<char*>(header), sizeof(header));
  if (in.gcount() != static_cast<std::streamsize>(sizeof(header)) || std::memcmp(header, "PMTiles", 7) != 0) {
    error = "not a PMTiles v3 archive";
    return false;
  }

  rec.id = id;
  rec.path = path;
  rec.container = "pmtiles";
  rec.range = true;
  rec.pmtiles_version = header[7];
  rec.addressed_tiles = u64_le(header + 72);
  rec.tile_entries = u64_le(header + 80);
  rec.tile_contents = u64_le(header + 88);
  rec.format = pmtiles_format(header[99]);
  rec.extension = rec.format == "jpg" ? "jpg" : rec.format;
  rec.type = rec.format == "mvt" ? "vector" : "raster";
  rec.title = id;
  rec.kind = kind_for(rec.id, rec.title, rec.format, rec.type);
  rec.bounds = bounds_string_from_pmtiles_header(header);
  rec.minzoom = header[100];
  rec.maxzoom = header[101];
  rec.size_bytes = static_cast<std::uint64_t>(st.st_size);
  rec.modified_epoch = static_cast<std::uint64_t>(st.st_mtime);
  return true;
}

std::map<std::string, std::shared_ptr<PackRecord>> build_pack_index(const std::string& base) {
  std::map<std::string, std::shared_ptr<PackRecord>> records;
  for (const auto& entry : parse_pack_map(base)) {
    const std::string id = entry.first;
    const std::string path = pack_path(base, entry.second);
    struct stat st {};
    if (!stat_file(path, st)) {
      std::fprintf(stderr, "warning: pack %s not found at %s\n", id.c_str(), path.c_str());
      continue;
    }
    const std::string ext = extension_of(path);
    auto rec = std::make_shared<PackRecord>();
    std::string error;
    const bool ok = ext == ".mbtiles"
      ? open_mbtiles_pack(id, path, st, *rec, error)
      : (ext == ".pmtiles" ? open_pmtiles_pack(id, path, st, *rec, error) : false);
    if (ok) {
      records[id] = rec;
    } else {
      std::fprintf(stderr, "warning: cannot open pack %s: %s\n", id.c_str(), error.c_str());
    }
  }
  return records;
}

std::string catalog_json(const std::map<std::string, std::shared_ptr<PackRecord>>& packs,
                         const std::string& origin) {
  std::ostringstream out;
  out << "{";
  bool first = true;
  for (const auto& kv : packs) {
    const PackRecord& rec = *kv.second;
    if (!first) out << ",";
    first = false;
    const std::string quoted_id = url_encode(rec.id);
    out << "\"" << json_escape(rec.id) << "\":{";
    out << "\"id\":\"" << json_escape(rec.id) << "\",";
    out << "\"name\":\"" << json_escape(rec.id) << "\",";
    out << "\"title\":\"" << json_escape(rec.title) << "\",";
    out << "\"container\":\"" << rec.container << "\",";
    out << "\"format\":\"" << rec.format << "\",";
    out << "\"extension\":\"" << rec.extension << "\",";
    out << "\"type\":\"" << rec.type << "\",";
    out << "\"kind\":\"" << rec.kind << "\",";
    out << "\"source\":\"" << json_escape(rec.source) << "\",";
    out << "\"license\":\"" << json_escape(rec.license) << "\",";
    out << "\"size_bytes\":" << rec.size_bytes << ",";
    out << "\"modified_epoch\":" << rec.modified_epoch << ",";
    out << "\"minzoom\":" << rec.minzoom << ",";
    out << "\"maxzoom\":" << rec.maxzoom;
    if (!rec.bounds.empty()) out << ",\"bounds\":\"" << json_escape(rec.bounds) << "\"";
    if (!rec.attribution.empty()) out << ",\"attribution\":\"" << json_escape(rec.attribution) << "\"";
    if (rec.container == "mbtiles") {
      const std::string url = origin + "/" + quoted_id + "/{z}/{x}/{y}." + rec.extension;
      out << ",\"tile_url\":\"" << json_escape(url) << "\",";
      out << "\"url\":\"" << json_escape(url) << "\"";
    } else {
      const std::string url = origin + "/" + quoted_id + ".pmtiles";
      out << ",\"range\":true,";
      out << "\"pmtiles_version\":" << rec.pmtiles_version << ",";
      out << "\"addressed_tiles\":" << rec.addressed_tiles << ",";
      out << "\"tile_entries\":" << rec.tile_entries << ",";
      out << "\"tile_contents\":" << rec.tile_contents << ",";
      out << "\"pmtiles_url\":\"" << json_escape(url) << "\",";
      out << "\"protocol_url\":\"pmtiles://" << json_escape(url) << "\",";
      out << "\"url\":\"" << json_escape(url) << "\"";
    }
    out << "}";
  }
  out << "}";
  return out.str();
}

bool parse_uint(const std::string& text, std::uint64_t& value) {
  if (text.empty()) return false;
  char* end = nullptr;
  errno = 0;
  unsigned long long parsed = std::strtoull(text.c_str(), &end, 10);
  if (errno || !end || *end != '\0') return false;
  value = static_cast<std::uint64_t>(parsed);
  return true;
}

struct ByteRange {
  bool partial = false;
  std::uint64_t start = 0;
  std::uint64_t end = 0;
};

bool parse_range(const std::string& value, std::uint64_t size, ByteRange& out, std::string& content_range) {
  if (value.empty()) {
    out.partial = false;
    out.start = 0;
    out.end = size ? size - 1 : 0;
    return true;
  }
  if (!starts_with(value, "bytes=")) return false;
  const std::string spec = value.substr(6);
  const std::size_t dash = spec.find('-');
  if (dash == std::string::npos) return false;
  const std::string a = spec.substr(0, dash);
  const std::string b = spec.substr(dash + 1);
  if (a.empty() && b.empty()) return false;
  std::uint64_t start = 0;
  std::uint64_t end = size ? size - 1 : 0;
  if (a.empty()) {
    std::uint64_t suffix = 0;
    if (!parse_uint(b, suffix) || suffix == 0) return false;
    start = suffix >= size ? 0 : size - suffix;
  } else {
    if (!parse_uint(a, start)) return false;
    if (!b.empty() && !parse_uint(b, end)) return false;
  }
  if (size == 0 || start >= size || start > end) {
    content_range = "bytes */" + std::to_string(size);
    return false;
  }
  end = std::min(end, size - 1);
  out.partial = true;
  out.start = start;
  out.end = end;
  return true;
}

std::string read_file_slice(const std::string& path, std::uint64_t start, std::uint64_t length) {
  std::ifstream in(path, std::ios::binary);
  if (!in) return std::string();
  in.seekg(static_cast<std::streamoff>(start));
  std::string body;
  body.resize(static_cast<std::size_t>(length));
  in.read(&body[0], static_cast<std::streamsize>(length));
  body.resize(static_cast<std::size_t>(in.gcount()));
  return body;
}

std::string etag_for(const PackRecord& rec) {
  std::ostringstream out;
  out << "\"" << std::hex << rec.modified_epoch << "-" << rec.size_bytes << "\"";
  return out.str();
}

ix::HttpResponsePtr serve_pmtiles(const PackRecord& rec, const ix::HttpRequestPtr& req, bool head_only) {
  Headers h;
  base_headers(h);
  h["Content-Type"] = content_type_for("pmtiles");
  h["Accept-Ranges"] = "bytes";
  h["Cache-Control"] = "public, max-age=86400";
  h["ETag"] = etag_for(rec);

  ByteRange range;
  std::string content_range;
  if (!parse_range(header_value(req->headers, "Range"), rec.size_bytes, range, content_range)) {
    if (!content_range.empty()) h["Content-Range"] = content_range;
    return empty_response(416, "Range Not Satisfiable", std::move(h));
  }

  const std::uint64_t length = rec.size_bytes == 0 ? 0 : range.end - range.start + 1;
  if (range.partial) {
    h["Content-Range"] = "bytes " + std::to_string(range.start) + "-" + std::to_string(range.end) +
      "/" + std::to_string(rec.size_bytes);
  }
  if (head_only) {
    h["Content-Length"] = std::to_string(length);
    return std::make_shared<ix::HttpResponse>(range.partial ? 206 : 200,
      range.partial ? "Partial Content" : "OK", ix::HttpErrorCode::Ok, h, std::string());
  }
  return response(range.partial ? 206 : 200, range.partial ? "Partial Content" : "OK", std::move(h),
                  read_file_slice(rec.path, range.start, length));
}

ix::HttpResponsePtr serve_mbtiles(const PackRecord& rec, const std::vector<std::string>& parts) {
  Headers h;
  base_headers(h);
  if (parts.size() != 4 || !rec.db) return empty_response(404, "Not Found", std::move(h));

  std::uint64_t z = 0;
  std::uint64_t x = 0;
  std::string y_ext = parts[3];
  const std::size_t dot = y_ext.find('.');
  if (dot == std::string::npos) return empty_response(404, "Not Found", std::move(h));
  std::uint64_t y = 0;
  if (!parse_uint(parts[1], z) || !parse_uint(parts[2], x) || !parse_uint(y_ext.substr(0, dot), y) || z > 30) {
    return empty_response(404, "Not Found", std::move(h));
  }
  const std::uint64_t limit = 1ULL << z;
  if (x >= limit || y >= limit) return empty_response(404, "Not Found", std::move(h));
  const std::uint64_t tms_y = limit - 1 - y;

  std::string tile;
  {
    std::lock_guard<std::mutex> lock(rec.db_mutex);
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(rec.db.get(),
          "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
          -1, &stmt, nullptr) != SQLITE_OK) {
      return empty_response(500, "SQLite Error", std::move(h));
    }
    sqlite3_bind_int64(stmt, 1, static_cast<sqlite3_int64>(z));
    sqlite3_bind_int64(stmt, 2, static_cast<sqlite3_int64>(x));
    sqlite3_bind_int64(stmt, 3, static_cast<sqlite3_int64>(tms_y));
    if (sqlite3_step(stmt) == SQLITE_ROW) {
      const void* blob = sqlite3_column_blob(stmt, 0);
      const int bytes = sqlite3_column_bytes(stmt, 0);
      if (blob && bytes > 0) tile.assign(static_cast<const char*>(blob), static_cast<std::size_t>(bytes));
    }
    sqlite3_finalize(stmt);
  }
  if (tile.empty()) return empty_response(204, "No Content", std::move(h));

  h["Content-Type"] = content_type_for(rec.extension);
  h["Cache-Control"] = "public, max-age=86400";
  return response(200, "OK", std::move(h), std::move(tile));
}

std::vector<std::string> split_path(const std::string& path) {
  std::vector<std::string> parts;
  std::size_t start = 0;
  while (start < path.size()) {
    while (start < path.size() && path[start] == '/') ++start;
    if (start >= path.size()) break;
    const std::size_t slash = path.find('/', start);
    const std::size_t end = slash == std::string::npos ? path.size() : slash;
    parts.push_back(url_decode(path.substr(start, end - start)));
    start = end;
  }
  return parts;
}

class PackDaemon {
public:
  PackDaemon(std::string bind, int port, std::map<std::string, std::shared_ptr<PackRecord>> packs)
      : bind_(std::move(bind)), port_(port), packs_(std::move(packs)), server_(port_, bind_) {}

  bool start() {
    server_.setOnConnectionCallback(
      [this](ix::HttpRequestPtr req, std::shared_ptr<ix::ConnectionState>) -> ix::HttpResponsePtr {
        return this->handle(req);
      });
    return server_.listenAndStart();
  }

private:
  ix::HttpResponsePtr handle(const ix::HttpRequestPtr& req) const {
    Headers h;
    base_headers(h);
    const std::string path = request_path(req->uri);
    const bool is_head = req->method == "HEAD";

    if (req->method == "OPTIONS") return empty_response(204, "No Content", std::move(h));

    if (path == "/" || path == "/health") {
      h["Content-Type"] = "application/json";
      h["Cache-Control"] = "no-store";
      std::ostringstream body;
      body << "{\"status\":\"ok\",\"engine\":\"helm-packd\",\"packs\":" << packs_.size() << "}";
      return response(200, "OK", std::move(h), is_head ? std::string() : body.str());
    }

    if (path == "/catalog") {
      h["Content-Type"] = "application/json";
      const std::string body = catalog_json(packs_, origin_for(req, bind_, port_));
      if (is_head) {
        h["Content-Length"] = std::to_string(body.size());
        return std::make_shared<ix::HttpResponse>(200, "OK", ix::HttpErrorCode::Ok, h, std::string());
      }
      return response(200, "OK", std::move(h), body);
    }

    if (ends_with(path, ".pmtiles")) {
      const std::string id = url_decode(path.substr(1, path.size() - 1 - 8));
      const auto it = packs_.find(id);
      if (it == packs_.end() || it->second->container != "pmtiles") return empty_response(404, "Not Found", std::move(h));
      return serve_pmtiles(*it->second, req, is_head);
    }

    if (req->method != "GET") return empty_response(405, "Method Not Allowed", std::move(h));

    const std::vector<std::string> parts = split_path(path);
    if (parts.empty()) return empty_response(404, "Not Found", std::move(h));
    const auto it = packs_.find(parts[0]);
    if (it == packs_.end() || it->second->container != "mbtiles") return empty_response(404, "Not Found", std::move(h));
    return serve_mbtiles(*it->second, parts);
  }

  std::string bind_;
  int port_;
  std::map<std::string, std::shared_ptr<PackRecord>> packs_;
  ix::HttpServer server_;
};

}  // namespace

int main(int argc, char** argv) {
  const int port = argc > 1 ? std::atoi(argv[1]) : 8091;
  const std::string bind = get_env("HELM_BIND", "0.0.0.0");
  const std::string base = expand_user(get_env("HELM_MBTILES_DIR", "web/data"));
  auto packs = build_pack_index(base);
  if (packs.empty()) {
    std::fprintf(stderr, "FATAL: no .mbtiles or .pmtiles packs found under %s\n", base.c_str());
    std::fprintf(stderr, "Set HELM_MBTILES_DIR or HELM_MBTILES_PACKS to point at local packs.\n");
    return 1;
  }

  PackDaemon daemon(bind, port, std::move(packs));
  if (!daemon.start()) {
    std::fprintf(stderr, "helm-packd listen on %s:%d FAILED\n", bind.c_str(), port);
    return 2;
  }
  std::printf("helm-packd local pack server: http://%s:%d/  (packs from %s)\n", bind.c_str(), port, base.c_str());
  for (;;) std::this_thread::sleep_for(std::chrono::hours(24));
  return 0;
}
