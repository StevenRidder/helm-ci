#pragma once
// Sat-first offline bundle profile (OFFLINE-L-4): producer + validation for
// GET /bundle?profile=sat_first. Split out of helm_packd.cpp so the daemon file stays
// within the HELMC++-7 maintainability budget (scripts/helmcxx-maintainability-audit.mjs).
// Contract: docs/proposals/interfaces/region-bundle-sat-first-v1.md.
//
// NOT standalone: include from helm_packd.cpp AFTER PackRecord, Query, qfirst, lower,
// select_pack_ids, component_role, parse_bounds_array, intersect_bbox, rj_string, add_bool,
// add_string_allow_empty and the JsonValue/JsonAllocator aliases are defined.
#include <cstdint>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

// A sat-first profile violation. Carries a machine code so the /bundle handler can fail
// closed with HTTP 422 (missing_basemap, chart_not_basemap, ...).
struct SatFirstError : std::runtime_error {
  std::string code;
  SatFirstError(std::string c, const std::string& message)
      : std::runtime_error(message), code(std::move(c)) {}
};

inline bool sat_first_truthy(const std::string& value) {
  const std::string l = lower(value);
  return l == "1" || l == "true" || l == "yes" || l == "on";
}

// Producer rule: from all packs that overlap the request bbox, drop chart packs unless
// include_chart=1 — a chart raster must neither pad the size estimate nor stand in for a
// satellite basemap. Returns the CSV pack list to bundle; throws SatFirstError(missing_basemap)
// when nothing satellite-worthy remains.
inline std::string sat_first_pack_csv(
    const std::map<std::string, std::shared_ptr<PackRecord>>& packs,
    const Query& query, const Query& q) {
  const std::vector<double> reqbbox = parse_bounds_array(qfirst(query, "bbox"));
  const bool include_chart = sat_first_truthy(qfirst(q, "include_chart"));
  std::string csv;
  int kept = 0;
  for (const std::string& id : select_pack_ids(packs, q)) {
    const PackRecord& rec = *packs.at(id);
    if (!reqbbox.empty()) {
      const std::vector<double> pb = parse_bounds_array(rec.bounds);
      if (!pb.empty() && intersect_bbox(reqbbox, pb).empty()) continue;  // no overlap
    }
    if (!include_chart && component_role(rec) == "chart") continue;
    if (kept++) csv += ",";
    csv += id;
  }
  if (!kept)
    throw SatFirstError("missing_basemap", "sat-first bundle requires a satellite basemap component");
  return csv;
}

// Post-build: stamp profile=sat_first, mark the highest-resolution satellite basemap primary
// (larger maxzoom, then size_bytes, then stable id), and fail closed with 422 missing_basemap
// if the built bundle has no basemap component (e.g. explicit chart-only packs).
inline void sat_first_finalize(JsonValue& bundle, JsonAllocator& a) {
  add_string_allow_empty(bundle, "profile", "sat_first", a);
  int best = -1, best_maxzoom = -1, idx = -1;
  std::uint64_t best_size = 0;
  std::string best_id;
  for (auto& c : bundle["components"].GetArray()) {
    ++idx;
    if (rj_string(c, "role") != "basemap") continue;
    const int mz = (c.HasMember("maxzoom") && c["maxzoom"].IsInt()) ? c["maxzoom"].GetInt() : -1;
    const std::uint64_t sz = (c.HasMember("size_bytes") && c["size_bytes"].IsUint64()) ? c["size_bytes"].GetUint64() : 0;
    const std::string id = rj_string(c, "id");
    if (best < 0 || mz > best_maxzoom || (mz == best_maxzoom && sz > best_size) ||
        (mz == best_maxzoom && sz == best_size && id < best_id)) {
      best = idx; best_maxzoom = mz; best_size = sz; best_id = id;
    }
  }
  if (best < 0)
    throw SatFirstError("missing_basemap", "sat-first bundle requires a satellite basemap component");
  add_bool(bundle["components"][best], "primary", true, a);
}
