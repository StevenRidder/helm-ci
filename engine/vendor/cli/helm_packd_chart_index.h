#pragma once

// Chart-root discovery and change detection for helm-packd. This header is
// included inside helm_packd.cpp's anonymous namespace so it can share the
// daemon's small path/JSON helpers without exposing a second public API.

std::vector<std::string> registered_chart_roots(const std::string& base) {
  const std::string configured_file = get_env("HELM_CHART_ROOTS_FILE");
  const std::string config_dir = expand_user(get_env("HELM_CONFIG", "~/.helm/config"));
  const std::string roots_file = expand_user(configured_file.empty()
    ? dirname_join(config_dir, "chart-roots.json") : configured_file);
  struct stat registry_st {};
  if (stat_file(roots_file, registry_st)) {
    auto registry = load_json_document(roots_file);
    if (!registry || !registry->IsObject() || !registry->HasMember("schema") ||
        !(*registry)["schema"].IsString() ||
        std::string((*registry)["schema"].GetString()) != "helm.chart_intake.roots.v1" ||
        !registry->HasMember("roots") || !(*registry)["roots"].IsArray()) {
      std::fprintf(stderr, "FATAL: chart roots registry is not helm.chart_intake.roots.v1\n");
      std::exit(2);
    }
    std::vector<std::string> roots;
    for (const auto& row : (*registry)["roots"].GetArray()) {
      if (!row.IsObject() || !row.HasMember("path") || !row["path"].IsString()) continue;
      const std::string path = expand_user(row["path"].GetString());
      if (!path.empty() && std::find(roots.begin(), roots.end(), path) == roots.end()) roots.push_back(path);
    }
    return roots.empty() ? std::vector<std::string>{base} : roots;
  }
  if (!configured_file.empty()) {
    std::fprintf(stderr, "FATAL: HELM_CHART_ROOTS_FILE does not exist: %s\n", roots_file.c_str());
    std::exit(2);
  }

  const std::string raw = get_env("HELM_CHART_ROOTS");
  if (raw.empty()) return {base};

  std::vector<std::string> roots;
  if (raw.front() == '[') {
    rapidjson::Document doc;
    doc.Parse(raw.c_str());
    if (doc.HasParseError() || !doc.IsArray()) {
      std::fprintf(stderr, "FATAL: HELM_CHART_ROOTS must be a JSON array of paths\n");
      std::exit(2);
    }
    for (const auto& value : doc.GetArray()) {
      if (value.IsString() && *value.GetString()) roots.push_back(expand_user(value.GetString()));
    }
  } else {
    std::size_t start = 0;
    while (start <= raw.size()) {
      const std::size_t colon = raw.find(':', start);
      const std::size_t end = colon == std::string::npos ? raw.size() : colon;
      if (end > start) roots.push_back(expand_user(raw.substr(start, end - start)));
      if (colon == std::string::npos) break;
      start = colon + 1;
    }
  }
  std::vector<std::string> unique;
  for (const std::string& root : roots) {
    if (!root.empty() && std::find(unique.begin(), unique.end(), root) == unique.end()) unique.push_back(root);
  }
  return unique.empty() ? std::vector<std::string>{base} : unique;
}

struct TreeFile {
  std::size_t root_index = 0;
  std::string relative;
  std::string path;
  struct stat st {};
};

void collect_tree_files(const std::string& root, const std::string& relative,
                        std::size_t root_index, bool packs_only,
                        std::vector<TreeFile>& files) {
  const std::string dir_path = relative.empty() ? root : dirname_join(root, relative);
  DIR* dir = ::opendir(dir_path.c_str());
  if (!dir) return;
  std::vector<std::string> names;
  while (dirent* ent = ::readdir(dir)) {
    const std::string name = ent->d_name;
    if (name != "." && name != "..") names.push_back(name);
  }
  ::closedir(dir);
  std::sort(names.begin(), names.end());

  for (const std::string& name : names) {
    const std::string child_relative = relative.empty() ? name : dirname_join(relative, name);
    const std::string child_path = dirname_join(root, child_relative);
    struct stat lst {};
    if (::lstat(child_path.c_str(), &lst) != 0) continue;
    if (S_ISDIR(lst.st_mode)) {
      collect_tree_files(root, child_relative, root_index, packs_only, files);
      continue;
    }
    struct stat st {};
    if (!stat_file(child_path, st)) continue;
    const std::string ext = extension_of(name);
    if (packs_only && ext != ".mbtiles" && ext != ".pmtiles") continue;
    files.push_back(TreeFile{root_index, child_relative, child_path, st});
  }
}

std::string collision_pack_id(std::string relative) {
  const std::size_t dot = relative.find_last_of('.');
  if (dot != std::string::npos) relative.resize(dot);
  std::string id;
  for (char value : relative) {
    const unsigned char c = static_cast<unsigned char>(value);
    if (value == '/') {
      id += "--";
    } else if (std::isalnum(c) || value == '.' || value == '_' || value == '-') {
      id += value;
    } else if (id.empty() || id.back() != '-') {
      id += '-';
    }
  }
  while (!id.empty() && id.front() == '-') id.erase(id.begin());
  while (!id.empty() && id.back() == '-') id.pop_back();
  return id.empty() ? "pack" : id;
}

std::vector<std::pair<std::string, std::string>> parse_pack_map(
    const std::string& base, const std::vector<std::string>& roots) {
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
      if (k2 == std::string::npos || colon == std::string::npos ||
          v1 == std::string::npos || v2 == std::string::npos) break;
      packs.emplace_back(raw.substr(k1 + 1, k2 - k1 - 1), raw.substr(v1 + 1, v2 - v1 - 1));
      pos = v2 + 1;
    }
    return packs;
  }

  std::vector<TreeFile> candidates;
  for (std::size_t i = 0; i < roots.size(); ++i) collect_tree_files(roots[i], "", i, true, candidates);
  std::sort(candidates.begin(), candidates.end(), [](const TreeFile& a, const TreeFile& b) {
    return std::tie(a.root_index, a.relative) < std::tie(b.root_index, b.relative);
  });
  std::map<std::string, int> stem_counts;
  for (const auto& candidate : candidates) ++stem_counts[basename_no_ext(candidate.relative)];

  std::set<std::string> used;
  for (const auto& candidate : candidates) {
    const std::string stem = basename_no_ext(candidate.relative);
    std::string id = stem_counts[stem] == 1 ? stem : collision_pack_id(candidate.relative);
    if (used.count(id)) id += "--r" + std::to_string(candidate.root_index + 1);
    const std::string base_id = id;
    int suffix = 2;
    while (used.count(id)) id = base_id + "--" + std::to_string(suffix++);
    used.insert(id);
    packs.emplace_back(id, candidate.path);
  }
  return packs;
}

void fingerprint_add(std::uint64_t& hash, const std::string& value) {
  constexpr std::uint64_t kFnvPrime = 1099511628211ULL;
  for (unsigned char c : value) {
    hash ^= c;
    hash *= kFnvPrime;
  }
}

std::string chart_tree_fingerprint(const std::string& base, const std::vector<std::string>& roots) {
  std::uint64_t hash = 1469598103934665603ULL;
  const std::string override = get_env("HELM_MBTILES_PACKS");
  fingerprint_add(hash, "override:" + override + "\n");
  for (std::size_t i = 0; i < roots.size(); ++i) {
    fingerprint_add(hash, "root:" + std::to_string(i) + ":" + roots[i] + "\n");
  }
  std::vector<TreeFile> files;
  if (override.empty()) {
    for (std::size_t i = 0; i < roots.size(); ++i) collect_tree_files(roots[i], "", i, false, files);
  } else {
    std::set<std::string> paths;
    for (const auto& entry : parse_pack_map(base, roots)) {
      const std::string path = pack_path(base, entry.second);
      const std::size_t dot = path.find_last_of('.');
      const std::string stem = dot == std::string::npos ? path : path.substr(0, dot);
      paths.insert(path);
      paths.insert(stem + ".metadata.json");
      paths.insert(stem + ".sidecar.json");
      paths.insert(path + ".metadata.json");
      paths.insert(path + ".sidecar.json");
    }
    for (const std::string& path : paths) {
      struct stat st {};
      if (stat_file(path, st)) files.push_back(TreeFile{0, path, path, st});
    }
  }
  std::sort(files.begin(), files.end(), [](const TreeFile& a, const TreeFile& b) {
    return std::tie(a.root_index, a.relative) < std::tie(b.root_index, b.relative);
  });
  for (const auto& file : files) {
    std::ostringstream row;
    row << file.root_index << ':' << file.relative << '\0' << file.st.st_size << '\0' << file.st.st_mtime;
#if defined(__APPLE__)
    row << '\0' << file.st.st_mtimespec.tv_nsec;
#elif defined(__linux__)
    row << '\0' << file.st.st_mtim.tv_nsec;
#endif
    row << '\n';
    fingerprint_add(hash, row.str());
  }
  std::ostringstream out;
  out << std::hex << std::setfill('0') << std::setw(16) << hash;
  return out.str();
}

// ---------------------------------------------------------------------------
// INTAKE-5: chart-library HTTP surface (/chart-index, /chart-roots).
// Mirrors pipeline/chart_intake.py (helm.chart_intake.roots.v1 + index.v1,
// board decision #13): GETs are strictly read-only, mutations write the same
// chart-roots.json the CLI owns, and ids hash exactly like the Python CLI so
// HTTP- and CLI-registered roots are one registry, not two.

#include <climits>
#include <cmath>
#include <cstring>

// SHA-256 (FIPS 180-4). Root/chart ids must byte-match hashlib.sha256, so the
// FNV fingerprint above cannot be reused here.
struct IntakeSha256 {
  std::uint32_t state[8] = {0x6a09e667u, 0xbb67ae85u, 0x3c6ef372u, 0xa54ff53au,
                            0x510e527fu, 0x9b05688cu, 0x1f83d9abu, 0x5be0cd19u};
  std::uint64_t length = 0;
  unsigned char buffer[64] = {0};
  std::size_t buffered = 0;

  static std::uint32_t rotr(std::uint32_t v, unsigned n) { return (v >> n) | (v << (32 - n)); }

  void block(const unsigned char* p) {
    static const std::uint32_t k[64] = {
      0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u, 0x3956c25bu, 0x59f111f1u, 0x923f82a4u, 0xab1c5ed5u,
      0xd807aa98u, 0x12835b01u, 0x243185beu, 0x550c7dc3u, 0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u, 0xc19bf174u,
      0xe49b69c1u, 0xefbe4786u, 0x0fc19dc6u, 0x240ca1ccu, 0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau,
      0x983e5152u, 0xa831c66du, 0xb00327c8u, 0xbf597fc7u, 0xc6e00bf3u, 0xd5a79147u, 0x06ca6351u, 0x14292967u,
      0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu, 0x53380d13u, 0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u,
      0xa2bfe8a1u, 0xa81a664bu, 0xc24b8b70u, 0xc76c51a3u, 0xd192e819u, 0xd6990624u, 0xf40e3585u, 0x106aa070u,
      0x19a4c116u, 0x1e376c08u, 0x2748774cu, 0x34b0bcb5u, 0x391c0cb3u, 0x4ed8aa4au, 0x5b9cca4fu, 0x682e6ff3u,
      0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u, 0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u,
    };
    std::uint32_t w[64];
    for (int i = 0; i < 16; ++i) {
      w[i] = (std::uint32_t(p[i * 4]) << 24) | (std::uint32_t(p[i * 4 + 1]) << 16) |
             (std::uint32_t(p[i * 4 + 2]) << 8) | std::uint32_t(p[i * 4 + 3]);
    }
    for (int i = 16; i < 64; ++i) {
      const std::uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
      const std::uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
      w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    std::uint32_t a = state[0], b = state[1], c = state[2], d = state[3];
    std::uint32_t e = state[4], f = state[5], g = state[6], h = state[7];
    for (int i = 0; i < 64; ++i) {
      const std::uint32_t s1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const std::uint32_t ch = (e & f) ^ (~e & g);
      const std::uint32_t t1 = h + s1 + ch + k[i] + w[i];
      const std::uint32_t s0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const std::uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
      const std::uint32_t t2 = s0 + maj;
      h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    state[0] += a; state[1] += b; state[2] += c; state[3] += d;
    state[4] += e; state[5] += f; state[6] += g; state[7] += h;
  }

  void update(const void* data, std::size_t size) {
    const unsigned char* p = static_cast<const unsigned char*>(data);
    length += size;
    while (size > 0) {
      const std::size_t take = std::min(size, sizeof(buffer) - buffered);
      std::memcpy(buffer + buffered, p, take);
      buffered += take; p += take; size -= take;
      if (buffered == sizeof(buffer)) { block(buffer); buffered = 0; }
    }
  }

  void update(const std::string& text) { update(text.data(), text.size()); }

  std::string hex_digest() {
    const std::uint64_t bits = length * 8;
    const unsigned char pad = 0x80;
    const unsigned char zero = 0x00;
    update(&pad, 1);
    while (buffered != 56) update(&zero, 1);
    unsigned char len_bytes[8];
    for (int i = 0; i < 8; ++i) len_bytes[i] = static_cast<unsigned char>(bits >> (56 - i * 8));
    update(len_bytes, 8);
    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (std::uint32_t word : state) out << std::setw(8) << word;
    return out.str();
  }
};

std::string intake_sha256_hex(const std::string& data) {
  IntakeSha256 hasher;
  hasher.update(data);
  return hasher.hex_digest();
}

// Mirrors chart_intake.py INDEXER_VERSION — bump in lockstep so /chart-index
// stays in C++/Python parity (contract test compares indexer_version).
constexpr int kIntakeIndexerVersion = 2;

// --- small mirrors of chart_intake.py helpers ------------------------------

bool intake_is_digits(const std::string& text) {
  if (text.empty()) return false;
  for (char c : text) if (c < '0' || c > '9') return false;
  return true;
}

std::string intake_lower(std::string text) {
  for (char& c : text) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  return text;
}

std::string intake_trim(std::string text) {
  while (!text.empty() && std::isspace(static_cast<unsigned char>(text.front()))) text.erase(text.begin());
  while (!text.empty() && std::isspace(static_cast<unsigned char>(text.back()))) text.pop_back();
  return text;
}

bool intake_looks_private_path(const std::string& value) {
  const std::string text = intake_trim(value);
  const std::string lowered = intake_lower(text);
  static const char* fragments[] = {"file://", "/users/", "/home/", "/private/", "/volumes/", "/tmp/", "\\users\\"};
  if (!text.empty() && (text[0] == '/' || text.rfind("~/", 0) == 0)) return true;
  for (const char* fragment : fragments) {
    if (lowered.find(fragment) != std::string::npos) return true;
  }
  if (text.size() > 2 && (text.substr(1, 2) == ":\\" || text.substr(1, 2) == ":/")) return true;
  return false;
}

bool intake_valid_bbox(const std::vector<double>& bbox) {
  if (bbox.size() != 4) return false;
  for (double part : bbox) if (!std::isfinite(part)) return false;
  if (!(-180.0 <= bbox[0] && bbox[0] <= 180.0) || !(-90.0 <= bbox[1] && bbox[1] <= 90.0) ||
      !(-180.0 <= bbox[2] && bbox[2] <= 180.0) || !(-90.0 <= bbox[3] && bbox[3] <= 90.0)) return false;
  if (bbox[1] > bbox[3]) return false;
  return true;
}

std::vector<double> intake_bbox_from_text(const std::string& text) {
  std::vector<double> bbox;
  std::istringstream parts(text);
  std::string part;
  while (std::getline(parts, part, ',')) {
    try {
      std::size_t used = 0;
      const double value = std::stod(intake_trim(part), &used);
      bbox.push_back(value);
    } catch (...) {
      return {};
    }
  }
  return intake_valid_bbox(bbox) ? bbox : std::vector<double>{};
}

double intake_mercator_lat(long long y, int zoom) {
  const double n = std::pow(2.0, zoom);
  const double v = M_PI * (1.0 - 2.0 * static_cast<double>(y) / n);
  return std::atan(std::sinh(v)) * 180.0 / M_PI;
}

std::string intake_abspath(const std::string& path) {
  std::string expanded = expand_user(path);
  if (!expanded.empty() && expanded[0] != '/') {
    char cwd[PATH_MAX] = {0};
    if (::getcwd(cwd, sizeof(cwd) - 1)) expanded = dirname_join(cwd, expanded);
  }
  return expanded;
}

// Python _canonical(..., must_exist=False) analog: resolve symlinks when the
// path exists; otherwise fall back to the absolute (unresolved) form.
std::string intake_canonical(const std::string& path) {
  const std::string absolute = intake_abspath(path);
  char resolved[PATH_MAX] = {0};
  if (::realpath(absolute.c_str(), resolved)) return resolved;
  return absolute;
}

std::string intake_basename(const std::string& path) {
  const std::size_t slash = path.find_last_of('/');
  return slash == std::string::npos ? path : path.substr(slash + 1);
}

// Python Path.with_suffix("") analog: drop the last extension of the FINAL
// path component only.
std::string intake_strip_last_suffix(const std::string& relative) {
  const std::size_t slash = relative.find_last_of('/');
  const std::size_t dot = relative.find_last_of('.');
  if (dot == std::string::npos || (slash != std::string::npos && dot < slash)) return relative;
  return relative.substr(0, dot);
}

// stat_file() above is regular-file-only by design; root availability needs a
// directory check.
bool intake_is_dir(const std::string& path) {
  struct stat st {};
  return ::stat(path.c_str(), &st) == 0 && S_ISDIR(st.st_mode);
}

bool intake_mkdirs(const std::string& path) {
  for (std::size_t i = 1; i <= path.size(); ++i) {
    if (i == path.size() || path[i] == '/') {
      const std::string dir = path.substr(0, i);
      if (dir.empty() || dir == "/") continue;
      if (::mkdir(dir.c_str(), 0755) != 0 && errno != EEXIST) return false;
    }
  }
  struct stat st {};
  return ::stat(path.c_str(), &st) == 0 && S_ISDIR(st.st_mode);
}

std::string intake_root_id(const std::string& canonical_path) {
  return "root-" + intake_sha256_hex(canonical_path).substr(0, 16);
}

std::string intake_chart_id(const std::string& root_id, const std::string& relative) {
  std::string key = root_id;
  key.push_back('\0');
  key += relative;
  return "chart-" + intake_sha256_hex(key).substr(0, 20);
}

const char* intake_http_reason(int status) {
  switch (status) {
    case 200: return "OK";
    case 400: return "Bad Request";
    case 409: return "Conflict";
    case 422: return "Unprocessable Entity";
    default: return "Internal Server Error";
  }
}

// --- registry ---------------------------------------------------------------

struct ChartRootRow {
  std::string id;
  std::string label;
  std::string path;
  std::string added_at;
  bool is_default = false;
};

std::string chart_roots_file_path() {
  const std::string configured_file = get_env("HELM_CHART_ROOTS_FILE");
  const std::string config_dir = expand_user(get_env("HELM_CONFIG", "~/.helm/config"));
  return expand_user(configured_file.empty() ? dirname_join(config_dir, "chart-roots.json") : configured_file);
}

bool chart_roots_env_managed() {
  struct stat st {};
  return !stat_file(chart_roots_file_path(), st) && !get_env("HELM_CHART_ROOTS").empty();
}

// Loads registry rows for the intake endpoints. source is "file", "env", or
// "default". Returns false (with a named error) when a present registry file
// is invalid — surfaced as HTTP 500, mirroring the oracle's IntakeError.
bool load_chart_root_rows(const std::string& base, std::vector<ChartRootRow>& rows,
                          std::string& source, std::string& error) {
  rows.clear();
  const std::string roots_file = chart_roots_file_path();
  struct stat registry_st {};
  if (stat_file(roots_file, registry_st)) {
    source = "file";
    const std::string filename = intake_basename(roots_file);
    auto registry = load_json_document(roots_file);
    if (!registry || !registry->IsObject()) {
      error = "cannot read registry " + filename;
      return false;
    }
    if (!registry->HasMember("schema") || !(*registry)["schema"].IsString() ||
        std::string((*registry)["schema"].GetString()) != "helm.chart_intake.roots.v1" ||
        !registry->HasMember("roots") || !(*registry)["roots"].IsArray()) {
      error = "registry " + filename + " is not helm.chart_intake.roots.v1";
      return false;
    }
    std::set<std::string> ids, paths;
    for (const auto& row : (*registry)["roots"].GetArray()) {
      if (!row.IsObject() || !row.HasMember("id") || !row["id"].IsString() ||
          !row.HasMember("label") || !row["label"].IsString() ||
          !row.HasMember("path") || !row["path"].IsString() ||
          !*row["id"].GetString() || !*row["label"].GetString() || !*row["path"].GetString()) {
        error = "registry " + filename + " has a malformed root record";
        return false;
      }
      ChartRootRow entry;
      entry.id = row["id"].GetString();
      entry.label = row["label"].GetString();
      entry.path = row["path"].GetString();
      entry.is_default = row.HasMember("default") && row["default"].IsBool() && row["default"].GetBool();
      if (row.HasMember("added_at") && row["added_at"].IsString()) entry.added_at = row["added_at"].GetString();
      if (entry.id.rfind("root-", 0) != 0 || ids.count(entry.id)) {
        error = "registry " + filename + " has a duplicate or invalid root id";
        return false;
      }
      if (entry.path[0] != '/' || paths.count(entry.path)) {
        error = "registry " + filename + " has a duplicate or non-absolute root path";
        return false;
      }
      if (intake_looks_private_path(entry.label)) {
        error = "registry " + filename + " has a path-shaped public label";
        return false;
      }
      ids.insert(entry.id);
      paths.insert(entry.path);
      rows.push_back(std::move(entry));
    }
    return true;
  }

  if (!get_env("HELM_CHART_ROOTS").empty()) {
    source = "env";
    const std::string now = now_iso();
    for (const std::string& root : registered_chart_roots(base)) {
      ChartRootRow entry;
      entry.path = intake_abspath(root);
      entry.id = intake_root_id(entry.path);
      std::string trimmed = entry.path;
      while (trimmed.size() > 1 && trimmed.back() == '/') trimmed.pop_back();
      entry.label = intake_basename(trimmed);
      if (entry.label.empty()) entry.label = "Charts";
      entry.added_at = now;
      rows.push_back(std::move(entry));
    }
    return true;
  }

  source = "default";
  ChartRootRow entry;
  entry.path = intake_canonical(base);
  entry.id = intake_root_id(entry.path);
  entry.label = "Default charts";
  entry.is_default = true;
  entry.added_at = now_iso();
  rows.push_back(std::move(entry));
  return true;
}

bool chart_roots_registry_write(const std::string& roots_file, std::vector<ChartRootRow> rows,
                                std::string& error) {
  std::sort(rows.begin(), rows.end(), [](const ChartRootRow& x, const ChartRootRow& y) {
    return std::make_tuple(!x.is_default, intake_lower(x.label), x.id) <
           std::make_tuple(!y.is_default, intake_lower(y.label), y.id);
  });
  rapidjson::Document doc;
  doc.SetObject();
  JsonAllocator& a = doc.GetAllocator();
  JsonValue roots(rapidjson::kArrayType);
  for (const ChartRootRow& row : rows) {
    JsonValue item(rapidjson::kObjectType);
    add_string_allow_empty(item, "added_at", row.added_at, a);
    item.AddMember("default", row.is_default, a);
    add_string_allow_empty(item, "id", row.id, a);
    add_string_allow_empty(item, "label", row.label, a);
    add_string_allow_empty(item, "path", row.path, a);
    roots.PushBack(item, a);
  }
  doc.AddMember("roots", roots, a);
  add_string_allow_empty(doc, "schema", "helm.chart_intake.roots.v1", a);
  add_string_allow_empty(doc, "updated_at", now_iso(), a);

  rapidjson::StringBuffer out;
  rapidjson::Writer<rapidjson::StringBuffer> writer(out);
  doc.Accept(writer);

  const std::size_t slash = roots_file.find_last_of('/');
  const std::string dir = slash == std::string::npos ? "." : roots_file.substr(0, slash);
  if (!intake_mkdirs(dir)) {
    error = "cannot create registry directory";
    return false;
  }
  const std::string tmp_path = roots_file + ".tmp";
  FILE* stream = std::fopen(tmp_path.c_str(), "w");
  if (!stream) {
    error = "cannot write registry " + intake_basename(roots_file);
    return false;
  }
  const std::string body = std::string(out.GetString(), out.GetSize()) + "\n";
  const bool wrote = std::fwrite(body.data(), 1, body.size(), stream) == body.size();
  const bool flushed = std::fflush(stream) == 0 && ::fsync(::fileno(stream)) == 0;
  std::fclose(stream);
  if (!wrote || !flushed || ::chmod(tmp_path.c_str(), 0600) != 0 ||
      std::rename(tmp_path.c_str(), roots_file.c_str()) != 0) {
    ::unlink(tmp_path.c_str());
    error = "cannot write registry " + intake_basename(roots_file);
    return false;
  }
  return true;
}

// Mirrors ensure_registry for the mutation path only: registry file if present
// (validated), else CREATE it with the daemon's base as the default root.
bool chart_roots_registry_ensure(const std::string& base, std::vector<ChartRootRow>& rows,
                                 std::string& error) {
  const std::string roots_file = chart_roots_file_path();
  struct stat st {};
  if (stat_file(roots_file, st)) {
    std::string source;
    return load_chart_root_rows(base, rows, source, error);
  }
  ChartRootRow entry;
  entry.path = intake_canonical(base);
  entry.id = intake_root_id(entry.path);
  entry.label = "Default charts";
  entry.is_default = true;
  entry.added_at = now_iso();
  if (!intake_mkdirs(entry.path)) {
    error = "chart root is unavailable: " + entry.path;
    return false;
  }
  rows = {entry};
  return chart_roots_registry_write(roots_file, rows, error);
}

// --- sidecar + validators ---------------------------------------------------

struct IntakeValidation {
  std::string status;
  std::string code;
  std::string message;
  std::vector<double> bbox;
};

IntakeValidation intake_validation(const std::string& status, const std::string& code,
                                   const std::string& message, std::vector<double> bbox = {}) {
  return IntakeValidation{status, code, message, std::move(bbox)};
}

bool intake_read_prefix(const std::string& path, std::size_t length, std::string& out) {
  FILE* stream = std::fopen(path.c_str(), "rb");
  if (!stream) return false;
  out.resize(length);
  const std::size_t got = std::fread(&out[0], 1, length, stream);
  std::fclose(stream);
  out.resize(got);
  return true;
}

IntakeValidation intake_validate_mbtiles(const std::string& path, const std::vector<double>& sidecar_bbox) {
  const std::string sqlite_magic("SQLite format 3\x00", 16);
  std::string header;
  if (!intake_read_prefix(path, 16, header)) {
    return intake_validation("error", "invalid_container", "MBTiles container could not be opened");
  }
  if (header.rfind("PMTiles", 0) == 0) {
    return intake_validation("error", "contents_extension_mismatch", "file declares .mbtiles but contains PMTiles");
  }
  if (header != sqlite_magic) {
    return intake_validation("error", "contents_extension_mismatch", "file declares .mbtiles but is not SQLite");
  }
  sqlite3* raw = nullptr;
  if (sqlite3_open_v2(path.c_str(), &raw, SQLITE_OPEN_READONLY, nullptr) != SQLITE_OK || !raw) {
    if (raw) sqlite3_close(raw);
    return intake_validation("error", "invalid_container", "MBTiles container could not be opened");
  }
  std::unique_ptr<sqlite3, SqliteCloser> db(raw);
  auto table_exists = [&](const char* name) {
    sqlite3_stmt* stmt = nullptr;
    bool found = false;
    if (sqlite3_prepare_v2(db.get(), "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name = ?1",
                           -1, &stmt, nullptr) == SQLITE_OK) {
      sqlite3_bind_text(stmt, 1, name, -1, SQLITE_TRANSIENT);
      found = sqlite3_step(stmt) == SQLITE_ROW;
    }
    sqlite3_finalize(stmt);
    return found;
  };
  if (!table_exists("tiles")) {
    return intake_validation("error", "invalid_schema", "MBTiles container has no tiles table");
  }
  std::vector<double> bbox;
  if (table_exists("metadata")) {
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db.get(), "SELECT value FROM metadata WHERE name = 'bounds'", -1, &stmt, nullptr) == SQLITE_OK &&
        sqlite3_step(stmt) == SQLITE_ROW) {
      const unsigned char* text = sqlite3_column_text(stmt, 0);
      if (text) bbox = intake_bbox_from_text(reinterpret_cast<const char*>(text));
    }
    sqlite3_finalize(stmt);
  }
  if (bbox.empty()) {
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db.get(),
                           "SELECT zoom_level, MIN(tile_column), MAX(tile_column), MIN(tile_row), MAX(tile_row) "
                           "FROM tiles GROUP BY zoom_level ORDER BY zoom_level DESC LIMIT 1",
                           -1, &stmt, nullptr) == SQLITE_OK &&
        sqlite3_step(stmt) == SQLITE_ROW && sqlite3_column_type(stmt, 0) != SQLITE_NULL &&
        sqlite3_column_type(stmt, 1) != SQLITE_NULL && sqlite3_column_type(stmt, 2) != SQLITE_NULL &&
        sqlite3_column_type(stmt, 3) != SQLITE_NULL && sqlite3_column_type(stmt, 4) != SQLITE_NULL) {
      const int zoom = sqlite3_column_int(stmt, 0);
      const long long min_x = sqlite3_column_int64(stmt, 1);
      const long long max_x = sqlite3_column_int64(stmt, 2);
      const long long min_tms_y = sqlite3_column_int64(stmt, 3);
      const long long max_tms_y = sqlite3_column_int64(stmt, 4);
      const double n = std::pow(2.0, zoom);
      const long long max_xyz_y = static_cast<long long>(n) - 1 - min_tms_y;
      const long long min_xyz_y = static_cast<long long>(n) - 1 - max_tms_y;
      bbox = {
        static_cast<double>(min_x) / n * 360.0 - 180.0,
        intake_mercator_lat(max_xyz_y + 1, zoom),
        static_cast<double>(max_x + 1) / n * 360.0 - 180.0,
        intake_mercator_lat(min_xyz_y, zoom),
      };
    }
    sqlite3_finalize(stmt);
  }
  if (bbox.empty()) bbox = sidecar_bbox;
  if (bbox.empty()) {
    return intake_validation("error", "bbox_unavailable", "MBTiles coverage bbox could not be derived");
  }
  return intake_validation("valid", "ok", "MBTiles container and coverage are valid", bbox);
}

IntakeValidation intake_validate_pmtiles(const std::string& path, const std::vector<double>& sidecar_bbox) {
  const std::string sqlite_magic("SQLite format 3\x00", 16);
  std::string header;
  if (!intake_read_prefix(path, 127, header)) {
    return intake_validation("error", "invalid_container", "PMTiles container could not be opened");
  }
  if (header.rfind(sqlite_magic, 0) == 0) {
    return intake_validation("error", "contents_extension_mismatch", "file declares .pmtiles but contains SQLite");
  }
  if (header.size() < 127 || header.rfind("PMTiles", 0) != 0) {
    return intake_validation("error", "contents_extension_mismatch", "file declares .pmtiles but has no PMTiles header");
  }
  const unsigned version = static_cast<unsigned char>(header[7]);
  if (version != 3) {
    return intake_validation("error", "unsupported_container_version",
                             "PMTiles version " + std::to_string(version) + " is unsupported");
  }
  std::vector<double> bbox;
  for (const std::size_t offset : {std::size_t(102), std::size_t(106), std::size_t(110), std::size_t(114)}) {
    std::int32_t value = 0;
    std::memcpy(&value, header.data() + offset, sizeof(value));
    bbox.push_back(static_cast<double>(value) / 1e7);
  }
  if (!intake_valid_bbox(bbox)) bbox = sidecar_bbox;
  if (bbox.empty() || !intake_valid_bbox(bbox)) {
    return intake_validation("error", "bbox_unavailable", "PMTiles coverage bbox could not be derived");
  }
  return intake_validation("valid", "ok", "PMTiles v3 container and coverage are valid", bbox);
}

void intake_collect_pairs(const JsonValue& value, std::vector<std::pair<double, double>>& pairs) {
  if (!value.IsArray()) return;
  if (value.Size() >= 2 && value[0].IsNumber() && value[1].IsNumber()) {
    pairs.emplace_back(value[0].GetDouble(), value[1].GetDouble());
    return;
  }
  for (const auto& child : value.GetArray()) intake_collect_pairs(child, pairs);
}

std::vector<double> intake_geojson_bbox(const JsonValue& doc) {
  if (doc.HasMember("bbox") && doc["bbox"].IsArray()) {
    std::vector<double> explicit_bbox;
    for (const auto& part : doc["bbox"].GetArray()) {
      if (part.IsNumber()) explicit_bbox.push_back(part.GetDouble());
    }
    if (intake_valid_bbox(explicit_bbox)) return explicit_bbox;
  }
  std::vector<const JsonValue*> geometries;
  const std::string kind = doc.HasMember("type") && doc["type"].IsString() ? doc["type"].GetString() : "";
  if (kind == "FeatureCollection") {
    if (doc.HasMember("features") && doc["features"].IsArray()) {
      for (const auto& feature : doc["features"].GetArray()) {
        if (feature.IsObject() && feature.HasMember("geometry")) geometries.push_back(&feature["geometry"]);
      }
    }
  } else if (kind == "Feature") {
    if (doc.HasMember("geometry")) geometries.push_back(&doc["geometry"]);
  } else {
    geometries.push_back(&doc);
  }
  std::vector<std::pair<double, double>> pairs;
  for (const JsonValue* geometry : geometries) {
    if (!geometry || !geometry->IsObject()) continue;
    const std::string gtype = geometry->HasMember("type") && (*geometry)["type"].IsString()
      ? (*geometry)["type"].GetString() : "";
    if (gtype == "GeometryCollection") {
      if (geometry->HasMember("geometries") && (*geometry)["geometries"].IsArray()) {
        for (const auto& child : (*geometry)["geometries"].GetArray()) {
          if (child.IsObject() && child.HasMember("coordinates")) intake_collect_pairs(child["coordinates"], pairs);
        }
      }
    } else if (geometry->HasMember("coordinates")) {
      intake_collect_pairs((*geometry)["coordinates"], pairs);
    }
  }
  double west = 0, south = 0, east = 0, north = 0;
  bool init = false;
  for (const auto& pair : pairs) {
    if (!std::isfinite(pair.first) || !std::isfinite(pair.second)) continue;
    if (!init) { west = east = pair.first; south = north = pair.second; init = true; continue; }
    west = std::min(west, pair.first); east = std::max(east, pair.first);
    south = std::min(south, pair.second); north = std::max(north, pair.second);
  }
  if (!init) return {};
  const std::vector<double> bbox = {west, south, east, north};
  return intake_valid_bbox(bbox) ? bbox : std::vector<double>{};
}

IntakeValidation intake_validate_geojson(const std::string& path, const std::vector<double>& sidecar_bbox) {
  auto doc = load_json_document(path);
  if (!doc) {
    return intake_validation("error", "contents_extension_mismatch", "file declares .geojson but is not valid JSON");
  }
  static const std::set<std::string> allowed = {
    "FeatureCollection", "Feature", "Point", "MultiPoint", "LineString", "MultiLineString",
    "Polygon", "MultiPolygon", "GeometryCollection",
  };
  const std::string kind = doc->IsObject() && doc->HasMember("type") && (*doc)["type"].IsString()
    ? (*doc)["type"].GetString() : "";
  if (!doc->IsObject() || !allowed.count(kind)) {
    return intake_validation("error", "contents_extension_mismatch", "file declares .geojson but has no GeoJSON type");
  }
  if (kind == "FeatureCollection" && (!doc->HasMember("features") || !(*doc)["features"].IsArray())) {
    return intake_validation("error", "invalid_schema", "GeoJSON FeatureCollection has no features array");
  }
  std::vector<double> bbox = intake_geojson_bbox(*doc);
  if (bbox.empty()) bbox = sidecar_bbox;
  if (bbox.empty()) {
    return intake_validation("error", "bbox_unavailable", "GeoJSON coverage bbox could not be derived");
  }
  return intake_validation("valid", "ok", "GeoJSON schema and coverage are valid", bbox);
}

// helm-packd has no S-57 driver (that is helm-server territory), so this is
// the exact analog of the oracle's driver-unavailable branch: leader sanity +
// sidecar coverage, never a fabricated bbox. Codes match the oracle; only the
// message wording names helm-packd instead of pyogrio.
IntakeValidation intake_validate_s57(const std::string& path, const std::vector<double>& sidecar_bbox) {
  const std::string sqlite_magic("SQLite format 3\x00", 16);
  std::string header;
  if (!intake_read_prefix(path, 24, header)) {
    return intake_validation("error", "invalid_container", "S-57 cell could not be opened");
  }
  if (header.rfind(sqlite_magic, 0) == 0 || header.rfind("PMTiles", 0) == 0 ||
      (!header.empty() && header[0] == '{')) {
    return intake_validation("error", "contents_extension_mismatch", "file declares .000 but contains another container type");
  }
  const bool leader_ok = header.size() == 24 && intake_is_digits(header.substr(0, 5)) &&
                         intake_is_digits(header.substr(12, 5));
  if (!leader_ok) {
    return intake_validation("error", "contents_extension_mismatch", "file declares .000 but has no ISO 8211 leader");
  }
  if (!sidecar_bbox.empty()) {
    return intake_validation("warning", "s57_driver_unavailable",
                             "S-57 leader is valid; coverage came from metadata because helm-packd has no S-57 driver",
                             sidecar_bbox);
  }
  return intake_validation("error", "bbox_validation_unavailable",
                           "S-57 leader is valid but helm-packd has no S-57 driver for required bbox validation");
}

IntakeValidation intake_validate_chart(const std::string& path, const std::string& extension,
                                       const std::vector<double>& sidecar_bbox) {
  if (extension == ".mbtiles") return intake_validate_mbtiles(path, sidecar_bbox);
  if (extension == ".pmtiles") return intake_validate_pmtiles(path, sidecar_bbox);
  if (extension == ".geojson") return intake_validate_geojson(path, sidecar_bbox);
  return intake_validate_s57(path, sidecar_bbox);
}

struct IntakeSidecar {
  bool present = false;
  bool invalid = false;
  std::string name;
  std::vector<double> bbox;
  std::unique_ptr<rapidjson::Document> public_metadata;  // includes sidecar_name
  std::vector<std::pair<std::string, std::string>> warnings;  // code, message
};

IntakeSidecar intake_load_sidecar(const std::string& path) {
  IntakeSidecar result;
  const std::string candidate = intake_strip_last_suffix(path) + ".metadata.json";
  struct stat st {};
  if (!stat_file(candidate, st) || !S_ISREG(st.st_mode)) return result;
  result.present = true;
  result.name = intake_basename(candidate);
  auto raw = load_json_document(candidate);
  if (!raw) {
    result.invalid = true;
    result.warnings.emplace_back("invalid_sidecar", "metadata sidecar is not valid JSON");
    return result;
  }
  if (!raw->IsObject()) {
    result.invalid = true;
    result.warnings.emplace_back("invalid_sidecar", "metadata sidecar must be a JSON object");
    return result;
  }
  result.public_metadata = std::make_unique<rapidjson::Document>();
  result.public_metadata->SetObject();
  rapidjson::Document& pub = *result.public_metadata;
  JsonAllocator& pa = pub.GetAllocator();
  auto is_scalar = [](const JsonValue& v) { return v.IsString() || v.IsBool() || v.IsNumber(); };
  auto scalar_is_private = [](const JsonValue& v) {
    return v.IsString() && intake_looks_private_path(v.GetString());
  };
  for (const char* key : {"id", "label", "title", "license", "attribution"}) {
    if (!raw->HasMember(key)) continue;
    const JsonValue& value = (*raw)[key];
    if (is_scalar(value) && !scalar_is_private(value)) {
      JsonValue copied;
      copied.CopyFrom(value, pa);
      pub.AddMember(JsonValue(key, pa), copied, pa);
    } else if (!value.IsNull() && scalar_is_private(value)) {
      result.warnings.emplace_back("private_sidecar_value_omitted",
                                   std::string("private path omitted from sidecar field ") + key);
    }
  }
  if (raw->HasMember("source")) {
    const JsonValue& source = (*raw)["source"];
    if (source.IsString() && !intake_looks_private_path(source.GetString())) {
      JsonValue copied;
      copied.CopyFrom(source, pa);
      pub.AddMember("source", copied, pa);
    } else if (source.IsObject()) {
      JsonValue safe(rapidjson::kObjectType);
      for (const char* key : {"id", "label", "license"}) {
        if (source.HasMember(key) && is_scalar(source[key]) && !scalar_is_private(source[key])) {
          JsonValue copied;
          copied.CopyFrom(source[key], pa);
          safe.AddMember(JsonValue(key, pa), copied, pa);
        }
      }
      if (safe.MemberCount() > 0) pub.AddMember("source", safe, pa);
    } else if (source.IsString()) {
      result.warnings.emplace_back("private_sidecar_value_omitted", "private path omitted from sidecar field source");
    }
  }
  for (const char* key : {"bounds", "bbox"}) {
    if (!raw->HasMember(key)) continue;
    const JsonValue& value = (*raw)[key];
    std::vector<double> bbox;
    if (value.IsArray()) {
      for (const auto& part : value.GetArray()) if (part.IsNumber()) bbox.push_back(part.GetDouble());
      if (!intake_valid_bbox(bbox)) bbox.clear();
    } else if (value.IsString()) {
      bbox = intake_bbox_from_text(value.GetString());
    }
    if (!bbox.empty()) { result.bbox = bbox; break; }
  }
  if (!result.bbox.empty()) {
    JsonValue arr(rapidjson::kArrayType);
    for (double part : result.bbox) arr.PushBack(part, pa);
    pub.AddMember("bbox", arr, pa);
  }
  add_string_allow_empty(pub, "sidecar_name", result.name, pa);
  return result;
}

// --- recursive walk (Python os.walk parity: files of a directory first, then
// sorted subdirs; symlinked dirs skipped with a named warning; symlinked files
// indexed only when they resolve inside the root) -----------------------------

struct IntakeTreeState {
  std::vector<std::pair<std::string, struct stat>> candidates;  // relative -> stat
  std::map<std::string, std::vector<int>> updates;              // stem -> update numbers
  std::vector<std::pair<std::string, std::string>> warnings;    // code, relative_path
  IntakeSha256* fingerprint = nullptr;
};

bool intake_recognized_ext(const std::string& ext) {
  return ext == ".mbtiles" || ext == ".pmtiles" || ext == ".000" || ext == ".geojson";
}

bool intake_numeric_suffix(const std::string& ext) {
  return ext.size() == 4 && ext[0] == '.' && intake_is_digits(ext.substr(1));
}

void intake_walk(const std::string& root, const std::string& relative, IntakeTreeState& state) {
  const std::string dir_path = relative.empty() ? root : dirname_join(root, relative);
  DIR* dir = ::opendir(dir_path.c_str());
  if (!dir) return;
  std::vector<std::string> names;
  while (dirent* ent = ::readdir(dir)) {
    const std::string name = ent->d_name;
    if (name != "." && name != "..") names.push_back(name);
  }
  ::closedir(dir);
  std::sort(names.begin(), names.end());

  std::vector<std::string> subdirs;
  std::vector<std::string> symlink_dirs;
  for (const std::string& name : names) {
    const std::string child_relative = relative.empty() ? name : relative + "/" + name;
    const std::string child_path = dirname_join(root, child_relative);
    struct stat lst {};
    if (::lstat(child_path.c_str(), &lst) != 0) continue;
    if (S_ISDIR(lst.st_mode)) {
      subdirs.push_back(child_relative);
      continue;
    }
    if (S_ISLNK(lst.st_mode)) {
      struct stat target {};
      if (::stat(child_path.c_str(), &target) == 0 && S_ISDIR(target.st_mode)) {
        state.warnings.emplace_back("symlink_directory_ignored", child_relative);
        continue;
      }
    }
    const std::string ext = intake_lower(extension_of(name));
    const std::string lowered_name = intake_lower(name);
    const bool is_sidecar = lowered_name.size() >= 14 &&
      lowered_name.substr(lowered_name.size() - 14) == ".metadata.json";
    const bool interesting = intake_recognized_ext(ext) || intake_numeric_suffix(ext) || is_sidecar;
    if (S_ISLNK(lst.st_mode)) {
      if (!interesting) continue;
      char resolved[PATH_MAX] = {0};
      char root_resolved[PATH_MAX] = {0};
      if (!::realpath(child_path.c_str(), resolved) || !::realpath(root.c_str(), root_resolved) ||
          std::string(resolved).rfind(std::string(root_resolved) + "/", 0) != 0) {
        state.warnings.emplace_back("external_symlink_file_ignored", child_relative);
        continue;
      }
      struct stat target {};
      if (::stat(resolved, &target) != 0 || !S_ISREG(target.st_mode)) continue;
    }
    struct stat st {};
    if (!stat_file(child_path, st) || !S_ISREG(st.st_mode)) continue;
    if (interesting && state.fingerprint) {
      std::ostringstream row;
      row << child_relative << '\0' << st.st_size << '\0';
#if defined(__APPLE__)
      row << (static_cast<long long>(st.st_mtimespec.tv_sec) * 1000000000LL + st.st_mtimespec.tv_nsec);
#elif defined(__linux__)
      row << (static_cast<long long>(st.st_mtim.tv_sec) * 1000000000LL + st.st_mtim.tv_nsec);
#else
      row << (static_cast<long long>(st.st_mtime) * 1000000000LL);
#endif
      row << '\n';
      state.fingerprint->update(row.str());
    }
    if (intake_numeric_suffix(ext) && ext != ".000") {
      state.updates[intake_strip_last_suffix(child_relative)].push_back(std::stoi(ext.substr(1)));
    } else if (intake_recognized_ext(ext)) {
      state.candidates.emplace_back(child_relative, st);
    }
  }

  for (const std::string& subdir : subdirs) {
    intake_walk(root, subdir, state);
  }
}

// --- /chart-index -----------------------------------------------------------

void intake_add_bbox(JsonValue& item, const char* key, const std::vector<double>& bbox, JsonAllocator& a) {
  if (bbox.empty()) return;
  JsonValue arr(rapidjson::kArrayType);
  for (double part : bbox) arr.PushBack(part, a);
  item.AddMember(JsonValue(key, a), arr, a);
}

std::string intake_chart_type_for(const std::string& ext) {
  if (ext == ".mbtiles" || ext == ".pmtiles") return "tile_pack";
  if (ext == ".000") return "enc";
  return "overlay";
}

std::string intake_serialize(const rapidjson::Document& doc) {
  rapidjson::StringBuffer out;
  rapidjson::Writer<rapidjson::StringBuffer> writer(out);
  doc.Accept(writer);
  return std::string(out.GetString(), out.GetSize());
}

std::string chart_roots_error_json(const std::string& code, const std::string& message) {
  rapidjson::Document doc;
  doc.SetObject();
  JsonAllocator& a = doc.GetAllocator();
  add_string_allow_empty(doc, "error", code, a);
  add_string_allow_empty(doc, "message", message, a);
  return intake_serialize(doc);
}

std::string chart_index_json(const std::string& base, int& http_status) {
  std::vector<ChartRootRow> rows;
  std::string source, error;
  if (!load_chart_root_rows(base, rows, source, error)) {
    http_status = 500;
    return chart_roots_error_json("chart_index_unavailable", error);
  }
  http_status = 200;

  rapidjson::Document doc;
  doc.SetObject();
  JsonAllocator& a = doc.GetAllocator();

  IntakeSha256 fingerprint;
  // Must track chart_intake.py INDEXER_VERSION (INTAKE-7 bumped it 1->2). helm-packd
  // has no S-57 depth pipeline, so the capability half stays "pyogrio:unavailable";
  // the depth pass is a Python rescan-only augmentation the read-only GET never runs.
  fingerprint.update("chart-intake:" + std::to_string(kIntakeIndexerVersion) + ":pyogrio:unavailable\n");

  JsonValue roots_json(rapidjson::kArrayType);
  JsonValue charts_json(rapidjson::kArrayType);
  JsonValue scan_warnings(rapidjson::kArrayType);
  int chart_count = 0, invalid_count = 0, warning_count = 0, scan_warning_count = 0;

  for (const ChartRootRow& row : rows) {
    JsonValue root_json(rapidjson::kObjectType);
    add_string_allow_empty(root_json, "id", row.id, a);
    add_string_allow_empty(root_json, "label", row.label, a);
    root_json.AddMember("default", row.is_default, a);

    {
      // Registry metadata is part of the fingerprint exactly like the oracle:
      // json.dumps({id,label,default}, sort_keys=True, separators=(",", ":")).
      std::ostringstream row_json;
      row_json << "{\"default\":" << (row.is_default ? "true" : "false")
               << ",\"id\":\"" << row.id << "\",\"label\":\"";
      for (char c : row.label) {
        if (c == '"' || c == '\\') row_json << '\\';
        row_json << c;
      }
      row_json << "\"}";
      fingerprint.update(row_json.str());
      fingerprint.update("\n");
    }

    const bool available = intake_is_dir(row.path);
    if (!available) {
      add_string_allow_empty(root_json, "status", "unavailable", a);
      add_string_allow_empty(root_json, "reason", "registered_root_missing", a);
      root_json.AddMember("chart_count", 0, a);
      root_json.AddMember("group_count", 0, a);
      roots_json.PushBack(root_json, a);
      fingerprint.update("missing\n");
      JsonValue warning(rapidjson::kObjectType);
      add_string_allow_empty(warning, "code", "registered_root_missing", a);
      add_string_allow_empty(warning, "root_id", row.id, a);
      add_string_allow_empty(warning, "message", "a registered chart root is unavailable", a);
      scan_warnings.PushBack(warning, a);
      ++scan_warning_count;
      continue;
    }
    add_string_allow_empty(root_json, "status", "available", a);

    IntakeTreeState state;
    state.fingerprint = &fingerprint;
    intake_walk(row.path, "", state);

    for (const auto& warning : state.warnings) {
      JsonValue entry(rapidjson::kObjectType);
      add_string_allow_empty(entry, "code", warning.first, a);
      add_string_allow_empty(entry, "root_id", row.id, a);
      add_string_allow_empty(entry, "relative_path", warning.second, a);
      add_string_allow_empty(entry, "message",
        warning.first == "symlink_directory_ignored"
          ? "symlinked directories are not scanned"
          : "symlinked chart or metadata outside the registered root is not indexed", a);
      scan_warnings.PushBack(entry, a);
      ++scan_warning_count;
    }

    std::set<std::string> base_stems;
    for (const auto& candidate : state.candidates) {
      if (intake_lower(extension_of(candidate.first)) == ".000") {
        base_stems.insert(intake_strip_last_suffix(candidate.first));
      }
    }
    for (const auto& update : state.updates) {
      if (!base_stems.count(update.first)) {
        JsonValue entry(rapidjson::kObjectType);
        add_string_allow_empty(entry, "code", "orphan_enc_update", a);
        add_string_allow_empty(entry, "root_id", row.id, a);
        add_string_allow_empty(entry, "relative_path", update.first, a);
        add_string_allow_empty(entry, "message", "S-57 update has no matching .000 base cell", a);
        scan_warnings.PushBack(entry, a);
        ++scan_warning_count;
      }
    }

    std::sort(state.candidates.begin(), state.candidates.end(),
              [](const std::pair<std::string, struct stat>& x, const std::pair<std::string, struct stat>& y) {
                return intake_lower(x.first) < intake_lower(y.first);
              });

    int root_chart_count = 0;
    std::set<std::string> groups;
    for (const auto& candidate : state.candidates) {
      const std::string& relative = candidate.first;
      const struct stat& entry_st = candidate.second;
      const std::string ext = intake_lower(extension_of(relative));
      const std::string path = dirname_join(row.path, relative);
      const IntakeSidecar sidecar = intake_load_sidecar(path);
      IntakeValidation validation = intake_validate_chart(path, ext, sidecar.bbox);
      if (sidecar.invalid) {
        validation = intake_validation("error", "invalid_sidecar", "chart metadata sidecar is invalid", validation.bbox);
      }
      const std::size_t slash = relative.find('/');
      const std::string group = slash == std::string::npos ? "." : relative.substr(0, slash);

      JsonValue item(rapidjson::kObjectType);
      add_string_allow_empty(item, "id", intake_chart_id(row.id, relative), a);
      add_string_allow_empty(item, "root_id", row.id, a);
      add_string_allow_empty(item, "relative_path", relative, a);
      add_string_allow_empty(item, "filename", intake_basename(relative), a);
      add_string_allow_empty(item, "group", group, a);
      add_string_allow_empty(item, "chart_type", intake_chart_type_for(ext), a);
      add_string_allow_empty(item, "extension", ext, a);
      item.AddMember("size_bytes", static_cast<std::int64_t>(entry_st.st_size), a);
      add_string_allow_empty(item, "modified_at", iso_from_epoch(static_cast<std::uint64_t>(entry_st.st_mtime)), a);

      JsonValue validation_json(rapidjson::kObjectType);
      add_string_allow_empty(validation_json, "status", validation.status, a);
      add_string_allow_empty(validation_json, "code", validation.code, a);
      add_string_allow_empty(validation_json, "message", validation.message, a);
      item.AddMember("validation", validation_json, a);

      JsonValue warnings_json(rapidjson::kArrayType);
      for (const auto& warning : sidecar.warnings) {
        JsonValue entry(rapidjson::kObjectType);
        add_string_allow_empty(entry, "code", warning.first, a);
        add_string_allow_empty(entry, "message", warning.second, a);
        warnings_json.PushBack(entry, a);
      }
      const bool has_sidecar_warnings = warnings_json.Size() > 0;
      item.AddMember("warnings", warnings_json, a);

      intake_add_bbox(item, "bbox", validation.bbox, a);
      if (!sidecar.invalid && sidecar.public_metadata && sidecar.public_metadata->MemberCount() > 0) {
        JsonValue metadata;
        metadata.CopyFrom(*sidecar.public_metadata, a);
        item.AddMember("metadata", metadata, a);
      }
      if (sidecar.present) add_string_allow_empty(item, "sidecar", sidecar.name, a);
      if (ext == ".000") {
        const auto updates_it = state.updates.find(intake_strip_last_suffix(relative));
        const int update_count = updates_it == state.updates.end() ? 0 : static_cast<int>(updates_it->second.size());
        item.AddMember("update_count", update_count, a);
        if (update_count > 0) {
          item.AddMember("latest_update",
                         *std::max_element(updates_it->second.begin(), updates_it->second.end()), a);
        }
      }

      if (validation.status == "error") ++invalid_count;
      if (validation.status == "warning" || has_sidecar_warnings) ++warning_count;
      groups.insert(group);
      ++root_chart_count;
      ++chart_count;
      charts_json.PushBack(item, a);
    }

    root_json.AddMember("chart_count", root_chart_count, a);
    root_json.AddMember("group_count", static_cast<int>(groups.size()), a);
    roots_json.PushBack(root_json, a);
  }

  warning_count += scan_warning_count;
  add_string_allow_empty(doc, "schema", "helm.chart_intake.index.v1", a);
  doc.AddMember("indexer_version", kIntakeIndexerVersion, a);
  {
    JsonValue classes(rapidjson::kArrayType);
    const struct ClassSpec { const char* type; const char* consumer; const char* exts[2]; int n; } specs[] = {
      {"tile_pack", "helm-packd", {".mbtiles", ".pmtiles"}, 2},
      {"enc", "helm-server", {".000", nullptr}, 1},
      {"overlay", "layer-manifest", {".geojson", nullptr}, 1},
    };
    for (const ClassSpec& spec : specs) {
      JsonValue entry(rapidjson::kObjectType);
      add_string_allow_empty(entry, "chart_type", spec.type, a);
      JsonValue exts(rapidjson::kArrayType);
      for (int i = 0; i < spec.n; ++i) exts.PushBack(JsonValue(spec.exts[i], a), a);
      entry.AddMember("extensions", exts, a);
      add_string_allow_empty(entry, "consumer", spec.consumer, a);
      classes.PushBack(entry, a);
    }
    doc.AddMember("chart_classes", classes, a);
  }
  add_string_allow_empty(doc, "generated_at", now_iso(), a);
  add_string_allow_empty(doc, "fingerprint", "sha256:" + fingerprint.hex_digest(), a);
  add_string_allow_empty(doc, "status", invalid_count ? "error" : (warning_count ? "warning" : "ok"), a);
  doc.AddMember("chart_count", chart_count, a);
  doc.AddMember("invalid_count", invalid_count, a);
  doc.AddMember("warning_count", warning_count, a);
  doc.AddMember("roots", roots_json, a);
  doc.AddMember("charts", charts_json, a);
  doc.AddMember("warnings", scan_warnings, a);
  return intake_serialize(doc);
}

// --- /chart-roots -----------------------------------------------------------

std::string chart_roots_get_json(const std::string& base, int& http_status) {
  std::vector<ChartRootRow> rows;
  std::string source, error;
  if (!load_chart_root_rows(base, rows, source, error)) {
    http_status = 500;
    return chart_roots_error_json("chart_roots_unavailable", error);
  }
  http_status = 200;
  rapidjson::Document doc;
  doc.SetObject();
  JsonAllocator& a = doc.GetAllocator();
  add_string_allow_empty(doc, "schema", "helm.chart_intake.roots.v1", a);
  JsonValue roots(rapidjson::kArrayType);
  for (const ChartRootRow& row : rows) {
    JsonValue item(rapidjson::kObjectType);
    add_string_allow_empty(item, "id", row.id, a);
    add_string_allow_empty(item, "label", row.label, a);
    item.AddMember("default", row.is_default, a);
    if (!row.added_at.empty()) add_string_allow_empty(item, "added_at", row.added_at, a);
    const bool available = intake_is_dir(row.path);
    add_string_allow_empty(item, "status", available ? "available" : "unavailable", a);
    roots.PushBack(item, a);
  }
  doc.AddMember("roots", roots, a);
  add_string_allow_empty(doc, "source", source, a);
  return intake_serialize(doc);
}

// POST /chart-roots and /chart-roots/remove. On success returns "" and fills
// result_doc's "root"/"removed" + "changed"; the caller rescans packs and
// finishes the response with chart_roots_success_json.
std::string chart_roots_mutate_json(const std::string& base, const std::string& body,
                                    bool remove, int& http_status, rapidjson::Document& result_doc) {
  http_status = 200;
  if (chart_roots_env_managed()) {
    http_status = 409;
    return chart_roots_error_json("chart_roots_env_managed",
      "chart roots come from HELM_CHART_ROOTS; unset it (or create chart-roots.json) to manage roots over HTTP");
  }
  rapidjson::Document request;
  request.Parse(body.c_str());
  if (request.HasParseError() || !request.IsObject()) {
    http_status = 400;
    return chart_roots_error_json("bad_chart_root_request", "body must be a JSON object");
  }

  std::vector<ChartRootRow> rows;
  std::string error;
  if (!chart_roots_registry_ensure(base, rows, error)) {
    http_status = 422;
    return chart_roots_error_json("chart_root_rejected", error);
  }
  const std::string roots_file = chart_roots_file_path();
  JsonAllocator& a = result_doc.GetAllocator();

  if (remove) {
    std::string ref;
    if (request.HasMember("id") && request["id"].IsString()) ref = request["id"].GetString();
    else if (request.HasMember("path") && request["path"].IsString()) ref = request["path"].GetString();
    ref = intake_trim(ref);
    if (ref.empty()) {
      http_status = 400;
      return chart_roots_error_json("bad_chart_root_request", "body must include \"id\" or \"path\"");
    }
    const std::string ref_canonical = ref.rfind("root-", 0) == 0 ? std::string() : intake_canonical(ref);
    for (std::size_t i = 0; i < rows.size(); ++i) {
      const bool matches = rows[i].id == ref ||
        (!ref_canonical.empty() && intake_canonical(rows[i].path) == ref_canonical);
      if (!matches) continue;
      if (rows[i].is_default) {
        http_status = 422;
        return chart_roots_error_json("chart_root_rejected", "the default chart root cannot be unregistered");
      }
      const ChartRootRow removed_row = rows[i];
      rows.erase(rows.begin() + static_cast<std::ptrdiff_t>(i));
      if (!chart_roots_registry_write(roots_file, rows, error)) {
        http_status = 422;
        return chart_roots_error_json("chart_root_rejected", error);
      }
      JsonValue removed_json(rapidjson::kObjectType);
      add_string_allow_empty(removed_json, "id", removed_row.id, a);
      add_string_allow_empty(removed_json, "label", removed_row.label, a);
      result_doc.AddMember("removed", removed_json, a);
      return std::string();
    }
    http_status = 422;
    return chart_roots_error_json("chart_root_rejected", "unknown chart root: " + ref);
  }

  std::string path;
  if (request.HasMember("path") && request["path"].IsString()) path = request["path"].GetString();
  path = intake_trim(path);
  if (path.empty()) {
    http_status = 400;
    return chart_roots_error_json("bad_chart_root_request", "body must include a non-empty \"path\"");
  }
  if (request.HasMember("label") && !request["label"].IsString() && !request["label"].IsNull()) {
    http_status = 400;
    return chart_roots_error_json("bad_chart_root_request", "\"label\" must be a string");
  }

  const std::string expanded = intake_abspath(path);
  char resolved[PATH_MAX] = {0};
  if (!::realpath(expanded.c_str(), resolved)) {
    http_status = 422;
    return chart_roots_error_json("chart_root_rejected", "chart root is unavailable: " + expanded);
  }
  struct stat dir_st {};
  if (::stat(resolved, &dir_st) != 0 || !S_ISDIR(dir_st.st_mode)) {
    http_status = 422;
    return chart_roots_error_json("chart_root_rejected", "chart root is not a directory: " + path);
  }
  const std::string canonical = resolved;
  const bool label_given = request.HasMember("label") && request["label"].IsString();
  std::string label = intake_trim(label_given ? request["label"].GetString() : intake_basename(canonical));
  if (label.empty() && !label_given) label = "Charts";
  if (label.empty()) {
    http_status = 422;
    return chart_roots_error_json("chart_root_rejected", "chart root label cannot be empty");
  }
  if (intake_looks_private_path(label)) {
    http_status = 422;
    return chart_roots_error_json("chart_root_rejected", "chart root label must not contain a private filesystem path");
  }

  bool changed = false;
  std::size_t result_index = rows.size();
  for (std::size_t i = 0; i < rows.size(); ++i) {
    if (intake_canonical(rows[i].path) != canonical) continue;
    if (label_given && rows[i].label != label) {
      rows[i].label = label;
      if (!chart_roots_registry_write(roots_file, rows, error)) {
        http_status = 422;
        return chart_roots_error_json("chart_root_rejected", error);
      }
      changed = true;
    }
    result_index = i;
    break;
  }
  if (result_index == rows.size()) {
    ChartRootRow entry;
    entry.id = intake_root_id(canonical);
    entry.label = label;
    entry.path = canonical;
    entry.added_at = now_iso();
    rows.push_back(entry);
    if (!chart_roots_registry_write(roots_file, rows, error)) {
      http_status = 422;
      return chart_roots_error_json("chart_root_rejected", error);
    }
    changed = true;
    result_index = rows.size() - 1;
  }

  const ChartRootRow& result_row = rows[result_index];
  JsonValue root_json(rapidjson::kObjectType);
  add_string_allow_empty(root_json, "id", result_row.id, a);
  add_string_allow_empty(root_json, "label", result_row.label, a);
  root_json.AddMember("default", result_row.is_default, a);
  if (!result_row.added_at.empty()) add_string_allow_empty(root_json, "added_at", result_row.added_at, a);
  const bool available = intake_is_dir(result_row.path);
  add_string_allow_empty(root_json, "status", available ? "available" : "unavailable", a);
  result_doc.AddMember("root", root_json, a);
  result_doc.AddMember("changed", changed, a);
  return std::string();
}

// Final success body for POST /chart-roots(+/remove) once the caller has
// rescanned: mirrors the oracle's response shape exactly.
std::string chart_roots_success_json(rapidjson::Document& result_doc, std::size_t packs,
                                     const std::string& fingerprint) {
  JsonAllocator& a = result_doc.GetAllocator();
  add_string_allow_empty(result_doc, "schema", "helm.chart_intake.roots.v1", a);
  add_string_allow_empty(result_doc, "status", "ok", a);
  result_doc.AddMember("packs", static_cast<std::uint64_t>(packs), a);
  add_string_allow_empty(result_doc, "fingerprint", fingerprint, a);
  return intake_serialize(result_doc);
}
