#pragma once
// LAYER-6: create + self-document the user overlay drop folder ({user_data_root}/layers) at
// helm-packd startup, so a fresh boat serves user GeoJSON overlays with no manual setup. Mirrors
// pipeline/user_layers.py (which only runs in the retired Python oracle); split into a header to
// keep helm_packd.cpp under the HELMC++-7 line budget. Contract: docs/USER-LAYERS.md.
//
// NOT standalone: include from helm_packd.cpp AFTER user_data_root() and expand_user() are defined.
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <dirent.h>
#include <fstream>
#include <string>
#include <sys/stat.h>

inline const char* hul_readme() {
  return
    "<!-- helm-user-layers-readme v1 -->\n"
    "# Helm user overlay layers - drop folder\n\n"
    "Drop GeoJSON files here and they appear as overlays on the Helm chart.\n\n"
    "1. Copy a `.geojson` (a FeatureCollection) into this folder.\n"
    "2. In Helm, press Cmd-K and run \"Reload user overlay layers\" (or reload the page).\n"
    "3. Your features draw in the overlay band (above the chart, below weather/AIS).\n\n"
    "Optional: a `<name>.metadata.json` sidecar overrides id / title / tier / source / inspection.\n"
    "Supported geometry: Point/MultiPoint (circles), LineString/MultiLineString (lines),\n"
    "Polygon/MultiPolygon (filled + outline). Sidecar metadata is PUBLIC - secret/path keys are\n"
    "stripped and never published. See docs/USER-LAYERS.md for the full format and security notes.\n\n"
    "`example-harbor-notes.geojson` here is a working example you can copy or delete.\n";
}

inline const char* hul_sample_geojson() {
  return
    "{\n"
    "  \"type\": \"FeatureCollection\",\n"
    "  \"features\": [\n"
    "    { \"type\": \"Feature\",\n"
    "      \"geometry\": { \"type\": \"Point\", \"coordinates\": [178.4419, -18.1416] },\n"
    "      \"properties\": { \"name\": \"Example anchorage\",\n"
    "        \"note\": \"Delete example-harbor-notes.* once you add your own layers.\" } }\n"
    "  ]\n"
    "}\n";
}

inline const char* hul_sample_sidecar() {
  return
    "{\n"
    "  \"id\": \"example-harbor-notes\",\n"
    "  \"title\": \"Example harbor notes\",\n"
    "  \"tier\": \"overlay\",\n"
    "  \"source\": { \"label\": \"example\", \"license\": \"sample-delete-me\" },\n"
    "  \"inspection\": { \"mode\": \"feature-properties\" }\n"
    "}\n";
}

inline bool hul_is_dir(const std::string& path) {
  struct stat st;
  return ::stat(path.c_str(), &st) == 0 && S_ISDIR(st.st_mode);
}

inline bool hul_is_file(const std::string& path) {
  struct stat st;
  return ::stat(path.c_str(), &st) == 0 && S_ISREG(st.st_mode);
}

inline bool hul_write_file(const std::string& path, const char* content) {
  std::ofstream out(path, std::ios::binary | std::ios::trunc);
  if (!out) return false;
  out << content;
  return static_cast<bool>(out);
}

// mkdir -p: create path and any missing parents.
inline bool hul_mkdirs(const std::string& path) {
  for (std::size_t i = 1; i <= path.size(); ++i) {
    if (i == path.size() || path[i] == '/') {
      const std::string dir = path.substr(0, i);
      if (dir.empty() || dir == "/") continue;
      if (::mkdir(dir.c_str(), 0755) != 0 && errno != EEXIST) return false;
    }
  }
  return hul_is_dir(path);
}

inline bool hul_dir_has_geojson(const std::string& dir) {
  DIR* d = ::opendir(dir.c_str());
  if (!d) return false;
  bool found = false;
  while (dirent* ent = ::readdir(d)) {
    const std::string name = ent->d_name;
    if (name.empty() || name[0] == '.') continue;
    if (name.size() >= 8 && name.substr(name.size() - 8) == ".geojson") { found = true; break; }
  }
  ::closedir(d);
  return found;
}

// Create + self-document {user_data_root}/layers at startup. Idempotent; never clobbers a user's
// *.geojson / *.metadata.json. Uses helm-packd's own user_data_root() so the created folder is
// exactly the one /layer-manifest scans. Failures log to stderr and are non-fatal (fail-fix-early).
inline void ensure_user_layers_dir() {
  const std::string layers = user_data_root() + "/layers";
  const bool created = !hul_is_dir(layers);
  if (!hul_mkdirs(layers)) {
    std::fprintf(stderr, "helm-packd: could not create user layers folder %s: %s\n",
                 layers.c_str(), std::strerror(errno));
    return;
  }
  // The README is Helm-owned: (re)write it when missing or stale so the contract stays current.
  const std::string readme = layers + "/README.md";
  bool readme_current = false;
  {
    std::ifstream in(readme);
    if (in) {
      std::string head;
      std::getline(in, head);
      readme_current = head.find("helm-user-layers-readme v1") != std::string::npos;
    }
  }
  if (!readme_current) hul_write_file(readme, hul_readme());
  // Seed the working example only for a brand-new folder with no user geojson yet.
  bool seeded = false;
  if (created && !hul_dir_has_geojson(layers)) {
    hul_write_file(layers + "/example-harbor-notes.geojson", hul_sample_geojson());
    hul_write_file(layers + "/example-harbor-notes.metadata.json", hul_sample_sidecar());
    seeded = true;
  }
  std::printf("helm-packd: user layers %s%s%s\n", layers.c_str(),
              created ? " (created)" : "", seeded ? " +sample" : "");
}
