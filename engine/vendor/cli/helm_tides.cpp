#include "helm_tides.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <limits>
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

}  // namespace

struct TideEngine::Impl {
  TCMgr manager;
  bool loaded = false;
  std::vector<TideSourceInfo> loaded_sources;
  std::vector<OfficialTideReference> official_references =
      DefaultOfficialReferences();
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

std::vector<TideSourceInfo> TideEngine::LoadedSources() const {
  return impl_->loaded_sources;
}

std::vector<OfficialTideReference> TideEngine::OfficialReferences() const {
  return impl_->official_references;
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

std::vector<OfficialTideReference> DefaultOfficialReferences() {
  OfficialTideReference suva;
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
