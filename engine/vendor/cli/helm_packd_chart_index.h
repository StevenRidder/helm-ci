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
