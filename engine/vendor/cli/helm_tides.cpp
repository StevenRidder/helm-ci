#include "helm_tides.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cctype>
#include <fstream>
#include <limits>
#include <map>
#include <sstream>
#include <utility>

#include "tc_data_factory.h"
#include "tcmgr.h"

namespace helm {
namespace tides {

namespace {

constexpr double kEarthRadiusNm = 3440.065;
constexpr double kDegToRad = 3.14159265358979323846 / 180.0;

std::string Basename(const std::string &path) {
  size_t slash = path.find_last_of("/\\");
  return slash == std::string::npos ? path : path.substr(slash + 1);
}

double Clamp(double value, double lo, double hi) {
  return std::max(lo, std::min(hi, value));
}

double UnitFactorToMeters(const Station_Data *station_data) {
  if (!station_data) return 1.0;
  int unit_idx = TCDataFactory::findunit(station_data->unit);
  if (unit_idx < 0) return 1.0;
  return TCDataFactory::known_units[unit_idx].conv_factor;
}

double DistanceNm(double lat0, double lon0, double lat1, double lon1) {
  double phi0 = lat0 * kDegToRad;
  double phi1 = lat1 * kDegToRad;
  double dphi = (lat1 - lat0) * kDegToRad;
  double dlambda = (lon1 - lon0) * kDegToRad;
  double a = std::sin(dphi / 2.0) * std::sin(dphi / 2.0) +
             std::cos(phi0) * std::cos(phi1) *
                 std::sin(dlambda / 2.0) * std::sin(dlambda / 2.0);
  double c = 2.0 * std::atan2(std::sqrt(a), std::sqrt(1.0 - a));
  return kEarthRadiusNm * c;
}

time_t TimegmPortable(std::tm *tm) {
#if defined(_WIN32)
  return _mkgmtime(tm);
#else
  return timegm(tm);
#endif
}

bool ReferenceValidForTime(const OfficialTideReference &ref, std::time_t utc) {
  std::time_t start = 0;
  std::time_t end = 0;
  if (!ref.valid_start_utc.empty() &&
      ParseUtcIso8601(ref.valid_start_utc, &start) && utc < start) {
    return false;
  }
  if (!ref.valid_end_utc.empty() &&
      ParseUtcIso8601(ref.valid_end_utc, &end) && utc > end) {
    return false;
  }
  return true;
}

bool LongitudeInRange(double lon, double min_lon, double max_lon) {
  if (min_lon <= max_lon) return lon >= min_lon && lon <= max_lon;
  return lon >= min_lon || lon <= max_lon;  // bbox crosses the dateline.
}

bool RegionContainsPoint(const TideProviderRegion &region,
                         double lat,
                         double lon) {
  return lat >= region.min_lat && lat <= region.max_lat &&
         LongitudeInRange(lon, region.min_lon, region.max_lon);
}

void AddUniqueRegion(std::vector<TideProviderRegion> *regions,
                     const TideProviderRegion &region) {
  if (!regions) return;
  for (const TideProviderRegion &existing : *regions) {
    if (existing.id == region.id) return;
  }
  regions->push_back(region);
}

std::string Trim(const std::string &s) {
  size_t first = 0;
  while (first < s.size() &&
         std::isspace(static_cast<unsigned char>(s[first]))) {
    ++first;
  }
  size_t last = s.size();
  while (last > first &&
         std::isspace(static_cast<unsigned char>(s[last - 1]))) {
    --last;
  }
  return s.substr(first, last - first);
}

std::map<std::string, std::string> ReadKeyValueFile(const std::string &path) {
  std::map<std::string, std::string> values;
  std::ifstream in(path);
  std::string line;
  while (std::getline(in, line)) {
    std::string trimmed = Trim(line);
    if (trimmed.empty() || trimmed[0] == '#') continue;
    size_t eq = trimmed.find('=');
    if (eq == std::string::npos) continue;
    values[Trim(trimmed.substr(0, eq))] = Trim(trimmed.substr(eq + 1));
  }
  return values;
}

std::string ValueOr(const std::map<std::string, std::string> &values,
                    const std::string &key,
                    const std::string &fallback) {
  auto it = values.find(key);
  return it == values.end() || it->second.empty() ? fallback : it->second;
}

bool BoolValueOr(const std::map<std::string, std::string> &values,
                 const std::string &key,
                 bool fallback) {
  auto it = values.find(key);
  if (it == values.end()) return fallback;
  std::string v = it->second;
  std::transform(v.begin(), v.end(), v.begin(),
                 [](unsigned char c) { return std::tolower(c); });
  if (v == "1" || v == "true" || v == "yes") return true;
  if (v == "0" || v == "false" || v == "no") return false;
  return fallback;
}

int IntValueOr(const std::map<std::string, std::string> &values,
               const std::string &key,
               int fallback) {
  auto it = values.find(key);
  if (it == values.end()) return fallback;
  char *end = nullptr;
  long v = std::strtol(it->second.c_str(), &end, 10);
  return end && *end == '\0' ? static_cast<int>(v) : fallback;
}

std::string SanitizePathToken(const std::string &token) {
  std::string out;
  out.reserve(token.size());
  for (unsigned char c : token) {
    if (std::isalnum(c) || c == '-' || c == '_') {
      out.push_back(static_cast<char>(c));
    } else {
      out.push_back('_');
    }
  }
  return out.empty() ? "_" : out;
}

std::string JoinPath(std::string base, const std::string &child) {
  if (base.empty()) return child;
  if (base.back() != '/') base.push_back('/');
  return base + child;
}

std::string UtcDateKey(std::time_t t) {
  std::string iso = FormatUtcIso8601(t);
  return iso.size() >= 10 ? iso.substr(0, 10) : iso;
}

bool CacheValidForTime(const OfficialPredictionCacheInfo &cache,
                       std::time_t utc) {
  std::time_t start = 0;
  std::time_t end = 0;
  if (!cache.valid_start_utc.empty() &&
      ParseUtcIso8601(cache.valid_start_utc, &start) && utc < start) {
    return false;
  }
  if (!cache.valid_end_utc.empty() &&
      ParseUtcIso8601(cache.valid_end_utc, &end) && utc > end) {
    return false;
  }
  return true;
}

const TideProviderRegion *FindRegion(
    const std::vector<TideProviderRegion> &regions,
    const std::string &id) {
  for (const TideProviderRegion &region : regions) {
    if (region.id == id) return &region;
  }
  return nullptr;
}

}  // namespace

struct TideEngine::Impl {
  TCMgr manager;
  bool loaded = false;
  std::vector<TideSourceInfo> loaded_sources;
  std::vector<OfficialTideReference> official_references =
      DefaultOfficialReferences();
  std::vector<TideProviderRegion> provider_regions = DefaultProviderRegions();
  std::string official_prediction_cache_dir;
};

TideEngine::TideEngine() : impl_(new Impl()) {}
TideEngine::~TideEngine() = default;
TideEngine::TideEngine(TideEngine &&) noexcept = default;
TideEngine &TideEngine::operator=(TideEngine &&) noexcept = default;

bool TideEngine::LoadSources(const std::vector<std::string> &sources,
                             std::string *error) {
  if (sources.empty()) {
    if (error) *error = "no tide/current harmonic sources supplied";
    return false;
  }

  std::vector<std::string> mutable_sources = sources;
  TC_Error_Code code = impl_->manager.LoadDataSources(mutable_sources);
  if (code != TC_NO_ERROR) {
    if (error) {
      char buf[96];
      std::snprintf(buf, sizeof(buf), "TCMgr LoadDataSources failed: %d", code);
      *error = buf;
    }
    return false;
  }

  impl_->loaded = true;
  impl_->loaded_sources.clear();
  for (const std::string &source : sources) {
    impl_->loaded_sources.push_back(ClassifySourcePath(source));
  }
  if (impl_->manager.Get_max_IDX() < 1) {
    if (error) *error = "harmonic sources loaded, but no stations were indexed";
    return false;
  }

  return true;
}

bool TideEngine::LoadDefaultSources(const std::string &tcdata_dir,
                                    TideSourcePolicy policy,
                                    std::string *error) {
  return LoadSources(DefaultSourcePaths(tcdata_dir, policy), error);
}

void TideEngine::SetOfficialPredictionCacheDir(const std::string &cache_dir) {
  impl_->official_prediction_cache_dir = cache_dir;
}

std::string TideEngine::OfficialPredictionCacheDir() const {
  return impl_->official_prediction_cache_dir;
}

std::vector<TideSourceInfo> TideEngine::LoadedSources() const {
  return impl_->loaded_sources;
}

std::vector<OfficialTideReference> TideEngine::OfficialReferences() const {
  return impl_->official_references;
}

std::vector<TideProviderRegion> TideEngine::ProviderRegions() const {
  return impl_->provider_regions;
}

std::vector<TideProviderRegion> TideEngine::ProviderRegionsForPoint(
    double lat, double lon) const {
  std::vector<TideProviderRegion> matches;
  if (!std::isfinite(lat) || !std::isfinite(lon)) return matches;
  for (const TideProviderRegion &region : impl_->provider_regions) {
    if (RegionContainsPoint(region, lat, lon)) matches.push_back(region);
  }
  return matches;
}

TideStation TideEngine::StationAt(int index) const {
  TideStation station;
  const IDX_entry *entry = impl_->manager.GetIDX_entry(index);
  if (!entry) return station;

  station.index = index;
  station.type = entry->IDX_type;
  station.name = entry->IDX_station_name;
  station.reference_name = entry->IDX_reference_name;
  station.source = entry->source_ident;
  TideSourceInfo source_info = ClassifySourcePath(station.source);
  station.source_license = source_info.license;
  station.source_provenance = source_info.provenance;
  station.source_redistribution_status = source_info.redistribution_status;
  station.source_redistribution_cleared = source_info.redistribution_cleared;
  station.source_enabled_by_default = source_info.enabled_by_default;
  station.lat = entry->IDX_lat;
  station.lon = entry->IDX_lon;
  station.timezone_minutes = entry->IDX_time_zone;
  station.usable = entry->IDX_Useable != 0;

  const Station_Data *station_data = entry->pref_sta_data;
  if (station_data) {
    station.has_datum = true;
    station.unit = station_data->unit;
    station.units_abbrev = station_data->units_abbrv;
    station.datum_m = station_data->DATUM * UnitFactorToMeters(station_data);
  }

  return station;
}

std::vector<TideStation> TideEngine::Stations() const {
  std::vector<TideStation> stations;
  if (!impl_->loaded) return stations;

  int max_idx = impl_->manager.Get_max_IDX();
  for (int index = 1; index <= max_idx; ++index) {
    TideStation station = StationAt(index);
    if (station.index >= 0) stations.push_back(station);
  }
  return stations;
}

bool TideEngine::NearestTideStation(double lat, double lon,
                                    TideStation *out) const {
  if (!impl_->loaded || !out) return false;

  double best_nm = std::numeric_limits<double>::infinity();
  TideStation best;
  int max_idx = impl_->manager.Get_max_IDX();
  for (int index = 1; index <= max_idx; ++index) {
    TideStation station = StationAt(index);
    if (!station.is_tide() || !station.usable) continue;
    double dist_nm = DistanceNm(lat, lon, station.lat, station.lon);
    if (dist_nm < best_nm) {
      best_nm = dist_nm;
      best = std::move(station);
      best.distance_nm = dist_nm;
    }
  }

  if (best.index < 0) return false;
  *out = std::move(best);
  return true;
}

bool TideEngine::NearestOfficialReference(double lat, double lon,
                                          std::time_t utc,
                                          OfficialTideReference *out) const {
  if (!out || impl_->official_references.empty()) return false;

  double best_nm = std::numeric_limits<double>::infinity();
  OfficialTideReference best;
  for (OfficialTideReference ref : impl_->official_references) {
    double dist_nm = DistanceNm(lat, lon, ref.lat, ref.lon);
    if (dist_nm < best_nm) {
      ref.distance_nm = dist_nm;
      ref.valid_for_time = ReferenceValidForTime(ref, utc);
      best = std::move(ref);
      best_nm = dist_nm;
    }
  }

  if (best.distance_nm < 0.0) return false;
  *out = std::move(best);
  return true;
}

bool TideEngine::CachedOfficialPrediction(
    const OfficialTideReference &reference,
    std::time_t utc,
    OfficialPredictionCacheInfo *out) const {
  if (!out || impl_->official_prediction_cache_dir.empty() ||
      reference.provider_region_id.empty() || reference.station_id.empty()) {
    return false;
  }

  std::string path = impl_->official_prediction_cache_dir;
  path = JoinPath(path, SanitizePathToken(reference.provider_region_id));
  path = JoinPath(path, SanitizePathToken(reference.station_id));
  path = JoinPath(path, UtcDateKey(utc) + ".meta");
  std::ifstream probe(path);
  if (!probe.good()) return false;
  probe.close();

  std::map<std::string, std::string> kv = ReadKeyValueFile(path);
  OfficialPredictionCacheInfo cache;
  const TideProviderRegion *region =
      FindRegion(impl_->provider_regions, reference.provider_region_id);
  cache.provider_region_id =
      ValueOr(kv, "provider_region_id", reference.provider_region_id);
  cache.provider = ValueOr(kv, "provider", reference.provider);
  cache.station_id = ValueOr(kv, "station_id", reference.station_id);
  cache.station_name = ValueOr(kv, "station_name", reference.station_name);
  cache.datum_name = ValueOr(kv, "datum_name", reference.datum_name);
  cache.source_url = ValueOr(kv, "source_url", reference.source_url);
  cache.cache_path = path;
  cache.fetched_utc = ValueOr(kv, "fetched_utc", "");
  cache.issue_date = ValueOr(kv, "issue_date", reference.issue_date);
  cache.valid_start_utc =
      ValueOr(kv, "valid_start_utc", reference.valid_start_utc);
  cache.valid_end_utc = ValueOr(kv, "valid_end_utc", reference.valid_end_utc);
  cache.license = ValueOr(kv, "license", region ? region->license : "");
  cache.provenance =
      ValueOr(kv, "provenance", region ? region->provenance : "");
  cache.redistribution_status = ValueOr(
      kv, "redistribution_status",
      region ? region->redistribution_status : "unknown");
  cache.cache_status =
      ValueOr(kv, "cache_status", "official predictions cached for query day");
  cache.sample_count = IntValueOr(kv, "sample_count", 0);
  cache.official = BoolValueOr(kv, "official", reference.official);
  cache.redistribution_cleared = BoolValueOr(
      kv, "redistribution_cleared",
      region ? region->redistribution_cleared : false);
  cache.valid_for_time = CacheValidForTime(cache, utc);

  if (cache.provider_region_id != reference.provider_region_id ||
      cache.station_id != reference.station_id || !cache.valid_for_time) {
    return false;
  }

  cache.ok = true;
  *out = std::move(cache);
  return true;
}

TideConfidence TideEngine::AssessConfidence(double lat, double lon,
                                            std::time_t utc,
                                            const TideStation &station) const {
  TideConfidence c;
  c.harmonic_station_distance_nm = station.distance_nm;
  c.basis = "nearest-station harmonic prediction with official reference metadata";
  c.score = 0.35;

  if (station.has_datum) {
    c.score += 0.10;
    c.factors.push_back("harmonic station exposes datum");
  } else {
    c.factors.push_back("harmonic station has no datum metadata");
    c.score -= 0.10;
  }

  if (station.source_redistribution_cleared) {
    c.score += 0.05;
    c.factors.push_back("harmonic source is redistributable by default");
  } else {
    c.score -= 0.10;
    c.factors.push_back("harmonic source is explicit opt-in/commercial-review");
  }

  if (station.distance_nm >= 0.0) {
    if (station.distance_nm <= 5.0) {
      c.score += 0.15;
      c.factors.push_back("harmonic station is within 5 nm");
    } else if (station.distance_nm <= 25.0) {
      c.score += 0.07;
      c.factors.push_back("harmonic station is within 25 nm");
    } else if (station.distance_nm <= 60.0) {
      c.factors.push_back("harmonic station is remote but within 60 nm");
    } else {
      c.score -= 0.15;
      c.factors.push_back("harmonic station is more than 60 nm away");
    }
  } else {
    c.factors.push_back("prediction was by station id; query distance unknown");
  }

  OfficialTideReference official;
  if (NearestOfficialReference(lat, lon, utc, &official)) {
    c.has_official_reference = true;
    c.official_reference = official;
    c.official_station_distance_nm = official.distance_nm;
    c.official_reference_valid_for_time = official.valid_for_time;
    c.live_observation_available = false;

    if (official.valid_for_time) {
      c.score += 0.25;
      c.factors.push_back("nearest official tide reference is valid for query time");
    } else {
      c.score -= 0.15;
      c.factors.push_back("nearest official tide reference is outside its validity window");
    }

    if (official.distance_nm <= 5.0) {
      c.score += 0.15;
      c.factors.push_back("official reference station is within 5 nm");
    } else if (official.distance_nm <= 25.0) {
      c.score += 0.07;
      c.factors.push_back("official reference station is within 25 nm");
    } else if (official.distance_nm <= 60.0) {
      c.factors.push_back("official reference station is remote but within 60 nm");
    } else {
      c.score -= 0.20;
      c.factors.push_back("official reference station is more than 60 nm away");
    }

    if (!official.observed_url.empty()) {
      c.factors.push_back("official/partner observed-water feed exists but residual is not yet applied");
    }
  } else {
    c.factors.push_back("no official/government station reference matched this area");
  }

  c.score = Clamp(c.score, 0.0, 1.0);
  if (!c.has_official_reference) c.score = std::min(c.score, 0.45);
  if (!c.official_reference_valid_for_time && c.has_official_reference)
    c.score = std::min(c.score, 0.50);
  if (!station.source_redistribution_cleared)
    c.score = std::min(c.score, 0.75);

  if (c.score >= 0.80) {
    c.tier = "high";
  } else if (c.score >= 0.55) {
    c.tier = "medium";
  } else if (c.score >= 0.35) {
    c.tier = "low";
  } else {
    c.tier = "very_low";
  }

  if (c.tier == "high") {
    c.summary = "official station/datum metadata is close and current";
  } else if (c.tier == "medium") {
    c.summary = "usable tide estimate; verify locally before pass/bar decisions";
  } else {
    c.summary = "remote or incomplete tide basis; visual verification required";
  }
  return c;
}

TidePrediction TideEngine::Predict(int station_index, std::time_t utc) const {
  TidePrediction prediction;
  prediction.time_utc = utc;
  if (!impl_->loaded) {
    prediction.error = "tide engine has not loaded harmonic sources";
    return prediction;
  }

  float value_m = 0.0f;
  float direction = 0.0f;
  bool ok = impl_->manager.GetTideOrCurrentMeters(
      utc, station_index, value_m, direction);
  if (!ok) {
    prediction.error = "OpenCPN TCMgr could not predict the requested station";
    prediction.station = StationAt(station_index);
    return prediction;
  }

  prediction.ok = true;
  prediction.value_m = value_m;
  prediction.station = StationAt(station_index);
  prediction.station.distance_nm = 0.0;
  prediction.is_current = prediction.station.is_current();
  if (prediction.is_current && direction >= 0.0f && direction <= 360.0f) {
    prediction.direction_deg = direction;
    prediction.has_direction = true;
  }
  prediction.confidence = AssessConfidence(prediction.station.lat,
                                           prediction.station.lon, utc,
                                           prediction.station);
  return prediction;
}

TidePrediction TideEngine::PredictNearest(double lat, double lon,
                                          std::time_t utc) const {
  TideStation nearest;
  if (!NearestTideStation(lat, lon, &nearest)) {
    TidePrediction prediction;
    prediction.time_utc = utc;
    prediction.error = "no usable tide station found in loaded sources";
    return prediction;
  }

  TidePrediction prediction = Predict(nearest.index, utc);
  prediction.station.distance_nm = nearest.distance_nm;
  prediction.confidence = AssessConfidence(lat, lon, utc, prediction.station);
  return prediction;
}

TideEvent TideEngine::NextHighLowEvent(int station_index,
                                       std::time_t after_utc) const {
  TideEvent event;
  event.search_start_utc = after_utc;
  if (!impl_->loaded) {
    event.error = "tide engine has not loaded harmonic sources";
    return event;
  }

  TideStation station = StationAt(station_index);
  event.station = station;
  if (!station.is_tide()) {
    event.error = "high/low events are only available for tide stations";
    return event;
  }

  std::time_t event_time = after_utc;
  int kind = impl_->manager.GetNextBigEvent(&event_time, station_index);
  if (kind != 1 && kind != 2) {
    event.error = "OpenCPN TCMgr could not find the next high/low event";
    return event;
  }

  float source_value = 0.0f;
  float direction = 0.0f;
  if (impl_->manager.GetTideOrCurrent(event_time, station_index, source_value,
                                      direction)) {
    float refined_source_value = 0.0f;
    std::time_t refined_time = event_time;
    impl_->manager.GetHightOrLowTide(event_time, 600, 60, source_value,
                                     kind == 2, station_index,
                                     refined_source_value, refined_time);
    if (refined_time > 0) event_time = refined_time;
  }

  float value_m = 0.0f;
  if (!impl_->manager.GetTideOrCurrentMeters(event_time, station_index, value_m,
                                             direction)) {
    event.error = "OpenCPN TCMgr could not predict the event water level";
    return event;
  }

  event.ok = true;
  event.kind = kind == 1 ? "low_water" : "high_water";
  event.event_utc = event_time;
  event.value_m = value_m;
  return event;
}

TideEvent TideEngine::NextHighLowEventNearest(double lat, double lon,
                                              std::time_t after_utc) const {
  TideStation nearest;
  if (!NearestTideStation(lat, lon, &nearest)) {
    TideEvent event;
    event.search_start_utc = after_utc;
    event.error = "no usable tide station found in loaded sources";
    return event;
  }

  TideEvent event = NextHighLowEvent(nearest.index, after_utc);
  event.station.distance_nm = nearest.distance_nm;
  return event;
}

TideSourceResolution TideEngine::ResolveSources(
    const std::vector<TideResolvePoint> &points,
    std::time_t fallback_utc,
    double corridor_nm) const {
  TideSourceResolution resolution;
  resolution.generated_utc = std::time(nullptr);
  resolution.corridor_nm = corridor_nm > 0.0 ? corridor_nm : 25.0;
  resolution.loaded_sources = LoadedSources();
  if (!impl_->loaded) {
    resolution.error = "tide engine has not loaded harmonic sources";
    return resolution;
  }
  if (points.empty()) {
    resolution.error = "no GPS, route, viewport, or explicit tide-resolve points supplied";
    return resolution;
  }

  const double ready_radius_nm = std::max(60.0, resolution.corridor_nm);
  resolution.ok = true;
  resolution.offline_ready = true;
  resolution.official_coverage_ready = true;
  resolution.min_confidence_score = 1.0;

  for (const TideResolvePoint &point : points) {
    TideResolvedPoint out;
    out.point = point;
    std::time_t utc = point.eta_utc != 0 ? point.eta_utc : fallback_utc;
    if (utc == 0) utc = resolution.generated_utc;

    if (!std::isfinite(point.lat) || !std::isfinite(point.lon) ||
        point.lat < -90.0 || point.lat > 90.0 ||
        point.lon < -180.0 || point.lon > 180.0) {
      out.warnings.push_back("invalid coordinate; no tide source resolved");
      out.confidence.tier = "very_low";
      out.confidence.summary = "invalid coordinate";
      resolution.offline_ready = false;
      resolution.official_coverage_ready = false;
      resolution.needs_attention = true;
      resolution.min_confidence_score = 0.0;
      resolution.points.push_back(out);
      continue;
    }

    out.provider_regions = ProviderRegionsForPoint(point.lat, point.lon);
    out.provider_catalog_available = !out.provider_regions.empty();
    for (const TideProviderRegion &region : out.provider_regions) {
      AddUniqueRegion(&resolution.provider_regions, region);
      if (region.official && !region.predictions_available) {
        out.warnings.push_back("matched official provider catalog, but no tide predictions are advertised");
      }
      if (region.requires_subscription) {
        out.warnings.push_back(
            "matched official provider requires subscription/licensed adapter before caching");
      } else if (region.requires_api_key) {
        out.warnings.push_back(
            "matched official provider requires API credentials before caching");
      } else if (region.adapter_status != "api-ready") {
        out.warnings.push_back(
            "matched official provider needs a format-specific adapter before caching");
      }
      if (!region.redistribution_cleared) {
        out.warnings.push_back(
            "matched official provider has redistribution/license review pending");
      }
    }
    if (out.provider_regions.empty()) {
      out.warnings.push_back(
          "no official/provider region catalog entry covers this point");
    }

    TideStation station;
    if (NearestTideStation(point.lat, point.lon, &station)) {
      out.has_harmonic_station = true;
      out.harmonic_station = station;
      out.harmonic_offline_available = true;
      out.confidence = AssessConfidence(point.lat, point.lon, utc, station);
      out.cache_status = "local harmonic fallback available";
      if (out.provider_catalog_available)
        out.cache_status += "; official provider catalog selected";

      if (!station.source_redistribution_cleared) {
        out.warnings.push_back(
            "nearest harmonic source is local/opt-in and needs license review");
      }
      if (station.distance_nm > ready_radius_nm) {
        out.offline_ready = false;
        out.warnings.push_back(
            "nearest harmonic tide station is outside the offline-ready radius");
      } else if (out.confidence.score < 0.35) {
        out.offline_ready = false;
        out.warnings.push_back("harmonic fallback confidence is very low");
      } else {
        out.offline_ready = true;
      }
      if (station.distance_nm > resolution.max_harmonic_station_distance_nm)
        resolution.max_harmonic_station_distance_nm = station.distance_nm;
    } else {
      out.cache_status = "no local harmonic fallback";
      if (out.provider_catalog_available)
        out.cache_status += "; official provider catalog selected";
      out.warnings.push_back("no usable local harmonic tide station found");
      out.confidence.tier = "very_low";
      out.confidence.summary = "no local harmonic tide station";
      out.confidence.score = 0.0;
      out.offline_ready = false;
    }

    OfficialTideReference official;
    if (NearestOfficialReference(point.lat, point.lon, utc, &official)) {
      out.has_official_reference = true;
      out.official_reference = official;
      out.official_metadata_available = true;
      out.observed_feed_available = official.observed_water_level_available;
      OfficialPredictionCacheInfo cache;
      if (CachedOfficialPrediction(official, utc, &cache)) {
        out.official_prediction_cached = true;
        out.official_prediction_cache = cache;
        if (!out.cache_status.empty()) out.cache_status += "; ";
        out.cache_status += cache.cache_status;
        if (official.distance_nm <= ready_radius_nm) out.offline_ready = true;
      }
      if (!official.valid_for_time) {
        out.warnings.push_back(
            "nearest official tide reference is outside its validity window");
      }
      if (official.distance_nm > ready_radius_nm) {
        out.warnings.push_back(
            "nearest official tide reference is outside the offline-ready radius");
      }
      if (official.distance_nm > resolution.max_official_station_distance_nm)
        resolution.max_official_station_distance_nm = official.distance_nm;
    } else {
      out.warnings.push_back("no official/government tide reference matched");
    }

    if (out.provider_catalog_available && !out.has_official_reference) {
      out.warnings.push_back(
          "official region provider is known, but no cached station/calendar reference is available yet");
    }

    if (!out.has_official_reference || !out.official_reference.valid_for_time ||
        out.official_reference.distance_nm > ready_radius_nm) {
      resolution.official_coverage_ready = false;
    }
    if (!out.offline_ready) resolution.offline_ready = false;
    if (!out.warnings.empty() || out.confidence.score < 0.55)
      resolution.needs_attention = true;
    resolution.min_confidence_score =
        std::min(resolution.min_confidence_score, out.confidence.score);

    resolution.points.push_back(out);
  }

  if (resolution.points.empty()) {
    resolution.ok = false;
    resolution.error = "no tide-source coverage points could be evaluated";
    resolution.offline_ready = false;
    resolution.official_coverage_ready = false;
    resolution.min_confidence_score = 0.0;
    return resolution;
  }

  if (resolution.min_confidence_score >= 0.80) {
    resolution.confidence_tier = "high";
  } else if (resolution.min_confidence_score >= 0.55) {
    resolution.confidence_tier = "medium";
  } else if (resolution.min_confidence_score >= 0.35) {
    resolution.confidence_tier = "low";
  } else {
    resolution.confidence_tier = "very_low";
  }

  if (resolution.offline_ready) {
    resolution.cache_summary =
        "local harmonic tide fallback is cached for every requested point";
  } else {
    resolution.cache_summary =
        "one or more requested points need source download, closer station data, or local observations before relying offline";
    resolution.warnings.push_back(
        "route/area is not fully offline-ready for tide guidance");
  }

  if (resolution.official_coverage_ready) {
    resolution.summary =
        "official tide reference metadata and local harmonic fallback cover the requested route/area";
  } else if (resolution.offline_ready) {
    resolution.summary =
        "local harmonic fallback is available, but official coverage is incomplete or remote";
  } else {
    resolution.summary =
        "tide source coverage is incomplete; verify visually and cache better regional data";
  }

  return resolution;
}

TideSourceInfo ClassifySourcePath(const std::string &path) {
  TideSourceInfo info;
  info.path = path;
  info.basename = Basename(path);

  if (info.basename == "harmonics-dwf-20210110-free.tcd") {
    info.license = "Harmonics/public-domain";
    info.provenance = "XTide dwf free harmonic subset packaged by OpenCPN";
    info.redistribution_status = "redistributable";
    info.redistribution_cleared = true;
    info.enabled_by_default = true;
  } else if (info.basename == "ticon-europe-global.tcd") {
    info.license = "CC-BY-SA-4.0";
    info.provenance = "DGFI-TUM TICON Europe data packaged by OpenCPN";
    info.redistribution_status = "attribution-sharealike-commercial-review";
  } else if (info.basename == "HARMONICS_NO_US.IDX" ||
             info.basename == "HARMONICS_NO_US") {
    info.license = "XTide/OpenCPN legacy harmonics";
    info.provenance = "OpenCPN legacy ASCII harmonic source";
    info.redistribution_status = "unverified-commercial-review";
  } else {
    info.license = "unknown";
    info.provenance = "local harmonic source";
    info.redistribution_status = "unverified";
  }

  return info;
}

std::vector<TideSourceInfo> DefaultSourceCatalog(const std::string &tcdata_dir) {
  std::string base = tcdata_dir;
  if (!base.empty() && base.back() != '/') base.push_back('/');
  return {
      ClassifySourcePath(base + "harmonics-dwf-20210110-free.tcd"),
      ClassifySourcePath(base + "HARMONICS_NO_US.IDX"),
      ClassifySourcePath(base + "ticon-europe-global.tcd"),
  };
}

std::vector<TideProviderRegion> DefaultProviderRegions() {
  TideProviderRegion noaa;
  noaa.id = "noaa-coops-us";
  noaa.provider = "NOAA CO-OPS";
  noaa.authority = "NOAA Center for Operational Oceanographic Products and Services";
  noaa.product = "CO-OPS metadata, datums, predictions, water levels, currents";
  noaa.region_name = "United States coastal waters, territories, and Great Lakes";
  noaa.country = "United States";
  noaa.source_url = "https://tidesandcurrents.noaa.gov/";
  noaa.metadata_url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/";
  noaa.prediction_url_template =
      "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
      "?station={station}&product=predictions&datum={datum}&time_zone=gmt"
      "&units=metric&format=json";
  noaa.observed_url_template =
      "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
      "?station={station}&product=water_level&datum={datum}&time_zone=gmt"
      "&units=metric&format=json";
  noaa.datum_name = "station datum, commonly MLLW for predictions";
  noaa.license = "US government public data";
  noaa.provenance = "NOAA CO-OPS Data API and Metadata API";
  noaa.redistribution_status = "redistributable-public-domain";
  noaa.cache_policy =
      "cache station metadata/datums by station; cache predictions by station/day; "
      "refresh observed water levels only when online";
  noaa.update_cadence =
      "metadata on demand; predictions by request window; observed water levels near-real-time";
  noaa.adapter_status = "api-ready";
  noaa.intended_use = "official-station";
  noaa.notes =
      "No spatial interpolation; resolver must pick a station and expose distance/datum.";
  noaa.min_lat = 13.0;
  noaa.max_lat = 72.0;
  noaa.min_lon = -180.0;
  noaa.max_lon = -64.0;
  noaa.official = true;
  noaa.predictions_available = true;
  noaa.observations_available = true;
  noaa.currents_available = true;
  noaa.redistribution_cleared = true;
  noaa.enabled_by_default = true;

  TideProviderRegion fiji;
  fiji.id = "fiji-met-cosppac";
  fiji.provider = "Fiji Meteorological Service / COSPPac";
  fiji.authority = "Fiji Meteorological Service";
  fiji.product = "annual tide prediction calendars and COSPPac observed water levels";
  fiji.region_name = "Fiji";
  fiji.country = "Fiji";
  fiji.source_url =
      "https://www.met.gov.fj/climate-services/suva-tide-prediction/";
  fiji.metadata_url = "https://www.met.gov.fj/climate-services/";
  fiji.prediction_url_template =
      "https://www.met.gov.fj/climate-services/{station}-tide-prediction/";
  fiji.observed_url_template = "https://www.bom.gov.au/cosppac/rtdd/";
  fiji.datum_name = "Tide Prediction Datum";
  fiji.license = "public web calendar; redistribution review required";
  fiji.provenance =
      "Fiji Meteorological Service tide prediction pages and COSPPac RTDD";
  fiji.redistribution_status = "official-publication-license-review";
  fiji.cache_policy =
      "cache annual station calendars after parser verifies issue date and station";
  fiji.update_cadence = "annual prediction calendar; observed feed when available";
  fiji.adapter_status = "manual-calendar";
  fiji.intended_use = "official-station";
  fiji.notes =
      "Catalog match is not enough for pass advice; station/calendar parser must cache the departure window.";
  fiji.min_lat = -22.0;
  fiji.max_lat = -15.0;
  fiji.min_lon = 172.0;
  fiji.max_lon = -176.0;
  fiji.official = true;
  fiji.predictions_available = true;
  fiji.observations_available = true;
  fiji.redistribution_cleared = false;
  fiji.enabled_by_default = true;

  TideProviderRegion shom;
  shom.id = "shom-spm-refmar-fr-polynesia";
  shom.provider = "SHOM / REFMAR";
  shom.authority = "Service hydrographique et oceanographique de la Marine";
  shom.product =
      "official tide predictions, sea-level observations, and station metadata";
  shom.region_name = "French Polynesia";
  shom.country = "France / French Polynesia";
  shom.source_url = "https://refmar.shom.fr/";
  shom.metadata_url = "https://data.shom.fr/";
  shom.prediction_url_template =
      "https://services.data.shom.fr/{key}/spm/prediction/maree";
  shom.observed_url_template = "https://refmar.shom.fr/";
  shom.datum_name = "SHOM station datum";
  shom.license = "SHOM public/service terms; subscription key required for prediction service";
  shom.provenance = "SHOM/REFMAR public portals and SHOM data services";
  shom.redistribution_status = "subscription-required-license-review";
  shom.cache_policy =
      "cache itinerary prediction windows only with a configured SHOM key and retained source terms";
  shom.update_cadence =
      "predictions by request window; observed stations as published by REFMAR";
  shom.adapter_status = "subscription-api";
  shom.intended_use = "official-station-or-point";
  shom.notes =
      "This is the Tuamotu/French Polynesia official-source hook; do not treat Copernicus/Open-Meteo as equivalent.";
  shom.min_lat = -28.0;
  shom.max_lat = -5.0;
  shom.min_lon = -155.0;
  shom.max_lon = -134.0;
  shom.official = true;
  shom.predictions_available = true;
  shom.observations_available = true;
  shom.requires_subscription = true;
  shom.redistribution_cleared = false;
  shom.enabled_by_default = false;

  return {noaa, fiji, shom};
}

std::vector<OfficialTideReference> DefaultOfficialReferences() {
  OfficialTideReference suva;
  suva.provider_region_id = "fiji-met-cosppac";
  suva.provider = "Fiji Meteorological Service / COSPPac";
  suva.product = "Suva 2026 tide prediction calendar";
  suva.station_id = "FJ-SUVA-WHARF";
  suva.station_name = "Suva Wharf";
  suva.country = "Fiji";
  suva.source_url =
      "https://www.met.gov.fj/climate-services/suva-tide-prediction/";
  suva.observed_url = "https://www.bom.gov.au/cosppac/rtdd/q1c7o0hj48yu/";
  suva.datum_name = "Tide Prediction Datum";
  suva.issue_date = "2026-04-08";
  suva.valid_start_utc = "2026-01-01T00:00:00Z";
  suva.valid_end_utc = "2026-12-31T23:59:59Z";
  suva.interpolation_method =
      "nearest official station; no spatial interpolation";
  suva.lat = -18.1330;
  suva.lon = 178.4280;
  suva.official = true;
  suva.prediction_calendar = true;
  suva.observed_water_level_available = true;

  OfficialTideReference honolulu;
  honolulu.provider_region_id = "noaa-coops-us";
  honolulu.provider = "NOAA CO-OPS";
  honolulu.product = "CO-OPS station metadata, datums, water levels, predictions";
  honolulu.station_id = "1612340";
  honolulu.station_name = "Honolulu, Honolulu Harbor";
  honolulu.country = "United States";
  honolulu.source_url =
      "https://tidesandcurrents.noaa.gov/stationhome.html?id=1612340";
  honolulu.observed_url =
      "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
      "?station=1612340&product=water_level&datum=MLLW&time_zone=gmt"
      "&units=metric&format=json";
  honolulu.datum_name = "MLLW";
  honolulu.interpolation_method =
      "NOAA station datum; no spatial interpolation";
  honolulu.lat = 21.3067;
  honolulu.lon = -157.8670;
  honolulu.official = true;
  honolulu.prediction_calendar = false;
  honolulu.observed_water_level_available = true;

  return {suva, honolulu};
}

std::vector<std::string> DefaultSourcePaths(const std::string &tcdata_dir,
                                           TideSourcePolicy policy) {
  std::vector<std::string> paths;
  for (const TideSourceInfo &source : DefaultSourceCatalog(tcdata_dir)) {
    if (policy == TideSourcePolicy::kAllLocal || source.enabled_by_default) {
      paths.push_back(source.path);
    }
  }
  return paths;
}

bool ParseUtcIso8601(const std::string &text, std::time_t *out) {
  if (!out) return false;

  std::tm tm {};
  int year = 0;
  int month = 0;
  int day = 0;
  int hour = 0;
  int minute = 0;
  int second = 0;
  if (std::sscanf(text.c_str(), "%d-%d-%dT%d:%d:%dZ", &year, &month, &day,
                  &hour, &minute, &second) != 6 &&
      std::sscanf(text.c_str(), "%d-%d-%dT%d:%d:%d", &year, &month, &day,
                  &hour, &minute, &second) != 6) {
    return false;
  }

  tm.tm_year = year - 1900;
  tm.tm_mon = month - 1;
  tm.tm_mday = day;
  tm.tm_hour = hour;
  tm.tm_min = minute;
  tm.tm_sec = second;
  tm.tm_isdst = 0;
  *out = TimegmPortable(&tm);
  return *out != static_cast<std::time_t>(-1);
}

std::string FormatUtcIso8601(std::time_t t) {
  std::tm tm {};
#if defined(_WIN32)
  gmtime_s(&tm, &t);
#else
  gmtime_r(&t, &tm);
#endif
  char buf[32];
  std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &tm);
  return buf;
}

}  // namespace tides
}  // namespace helm
