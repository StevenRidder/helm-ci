#include "helm_tides.h"

#include <cerrno>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "ixwebsocket/IXHttpClient.h"
#include "ixwebsocket/IXNetSystem.h"

namespace {

std::string JsonEscape(const std::string &s) {
  std::string out;
  out.reserve(s.size() + 8);
  for (unsigned char c : s) {
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if (c < 0x20) {
          char buf[8];
          std::snprintf(buf, sizeof(buf), "\\u%04x", c);
          out += buf;
        } else {
          out += static_cast<char>(c);
        }
    }
  }
  return out;
}

void PrintError(const std::string &error) {
  std::cout << "{\"ok\":false,\"error\":\"" << JsonEscape(error) << "\"}\n";
}

const char *JsonBool(bool value) {
  return value ? "true" : "false";
}

bool ParseDouble(const std::string &text, double *out) {
  errno = 0;
  char *end = nullptr;
  double value = std::strtod(text.c_str(), &end);
  if (end == text.c_str() || *end != '\0' || errno == ERANGE ||
      !std::isfinite(value)) {
    return false;
  }
  *out = value;
  return true;
}

bool ReadFile(const std::string &path, std::string *body, std::string *error) {
  std::ifstream in(path, std::ios::binary);
  if (!in.good()) {
    if (error) *error = "could not read input file: " + path;
    return false;
  }
  std::ostringstream ss;
  ss << in.rdbuf();
  *body = ss.str();
  return true;
}

void WriteCacheJson(std::ostream &out,
                    const helm::tides::OfficialPredictionCacheInfo &cache) {
  out << "{\"cache_path\":\"" << JsonEscape(cache.cache_path) << "\""
      << ",\"data_path\":\"" << JsonEscape(cache.data_path) << "\""
      << ",\"fetched_utc\":\"" << JsonEscape(cache.fetched_utc) << "\""
      << ",\"valid_start_utc\":\"" << JsonEscape(cache.valid_start_utc)
      << "\""
      << ",\"valid_end_utc\":\"" << JsonEscape(cache.valid_end_utc) << "\""
      << ",\"refresh_after_utc\":\"" << JsonEscape(cache.refresh_after_utc)
      << "\""
      << ",\"time_zone\":\"" << JsonEscape(cache.time_zone) << "\""
      << ",\"time_basis\":\"" << JsonEscape(cache.time_basis) << "\""
      << ",\"sample_count\":" << cache.sample_count
      << ",\"valid_for_time\":" << JsonBool(cache.valid_for_time)
      << ",\"refresh_due\":" << JsonBool(cache.refresh_due)
      << ",\"redistribution_cleared\":"
      << JsonBool(cache.redistribution_cleared) << "}";
}

void WriteRequestJson(std::ostream &out,
                      const helm::tides::OfficialPredictionRequest &request) {
  out << "{\"ok\":" << JsonBool(request.ok)
      << ",\"needed\":" << JsonBool(request.needed)
      << ",\"cached\":" << JsonBool(request.cached)
      << ",\"cache_refresh_due\":" << JsonBool(request.cache_refresh_due)
      << ",\"can_fetch_live\":" << JsonBool(request.can_fetch_live)
      << ",\"manual_import_required\":"
      << JsonBool(request.manual_import_required)
      << ",\"requires_api_key\":" << JsonBool(request.requires_api_key)
      << ",\"requires_subscription\":"
      << JsonBool(request.requires_subscription)
      << ",\"blocked\":" << JsonBool(request.blocked)
      << ",\"action\":\"" << JsonEscape(request.action) << "\""
      << ",\"status\":\"" << JsonEscape(request.status) << "\""
      << ",\"provider_region_id\":\""
      << JsonEscape(request.provider_region_id) << "\""
      << ",\"provider\":\"" << JsonEscape(request.provider) << "\""
      << ",\"adapter_status\":\"" << JsonEscape(request.adapter_status)
      << "\""
      << ",\"station_id\":\"" << JsonEscape(request.station_id) << "\""
      << ",\"station_name\":\"" << JsonEscape(request.station_name) << "\""
      << ",\"datum_name\":\"" << JsonEscape(request.datum_name) << "\""
      << ",\"date_utc\":\"" << JsonEscape(request.date_utc) << "\""
      << ",\"time_zone\":\"" << JsonEscape(request.time_zone) << "\""
      << ",\"source_url\":\"" << JsonEscape(request.source_url) << "\""
      << ",\"fetch_url\":\"" << JsonEscape(request.fetch_url) << "\""
      << ",\"cache_key\":\"" << JsonEscape(request.cache_key) << "\""
      << ",\"cache_path\":\"" << JsonEscape(request.cache_path) << "\""
      << ",\"data_path\":\"" << JsonEscape(request.data_path) << "\""
      << ",\"license\":\"" << JsonEscape(request.license) << "\""
      << ",\"provenance\":\"" << JsonEscape(request.provenance) << "\""
      << ",\"redistribution_status\":\""
      << JsonEscape(request.redistribution_status) << "\""
      << ",\"redistribution_cleared\":"
      << JsonBool(request.redistribution_cleared) << "}";
}

void PrintRequestPlan(const helm::tides::OfficialPredictionRequest &request,
                      bool executed,
                      bool dry_run,
                      const std::string &execution_status,
                      const helm::tides::OfficialPredictionCacheInfo *cache) {
  std::cout << "{\"ok\":" << JsonBool(request.ok)
            << ",\"mode\":\"request-plan\""
            << ",\"executed\":" << JsonBool(executed)
            << ",\"dry_run\":" << JsonBool(dry_run)
            << ",\"blocked\":" << JsonBool(request.blocked)
            << ",\"execution_status\":\""
            << JsonEscape(execution_status) << "\""
            << ",\"request\":";
  WriteRequestJson(std::cout, request);
  if (cache) {
    std::cout << ",\"cache\":";
    WriteCacheJson(std::cout, *cache);
  }
  std::cout << "}\n";
}

bool ParseDay(const std::string &date_or_time, std::time_t *utc) {
  if (date_or_time.size() == 10) {
    return helm::tides::ParseUtcIso8601(date_or_time + "T00:00:00Z", utc);
  }
  return helm::tides::ParseUtcIso8601(date_or_time, utc);
}

helm::tides::TideProviderRegion ProviderRegion(const std::string &id) {
  for (const helm::tides::TideProviderRegion &region :
       helm::tides::DefaultProviderRegions()) {
    if (region.id == id) return region;
  }
  return helm::tides::TideProviderRegion();
}

helm::tides::OfficialTideReference FindReference(
    const std::string &provider_region_id,
    const std::string &station_id,
    const std::string &station_name,
    const std::string &datum_name) {
  for (helm::tides::OfficialTideReference ref :
       helm::tides::DefaultOfficialReferences()) {
    if (ref.provider_region_id == provider_region_id &&
        ref.station_id == station_id) {
      if (!station_name.empty()) ref.station_name = station_name;
      if (!datum_name.empty()) ref.datum_name = datum_name;
      return ref;
    }
  }

  helm::tides::TideProviderRegion region = ProviderRegion(provider_region_id);
  helm::tides::OfficialTideReference ref;
  ref.provider_region_id = provider_region_id;
  ref.provider = region.provider;
  ref.product = region.product;
  ref.station_id = station_id;
  ref.station_name = station_name.empty() ? station_id : station_name;
  ref.country = region.country;
  ref.datum_name = datum_name.empty() ? "MLLW" : datum_name;
  ref.interpolation_method = "official station; no spatial interpolation";
  ref.official = region.official;
  ref.prediction_calendar = false;
  ref.observed_water_level_available = region.observations_available;
  return ref;
}

bool FetchLive(const std::string &url, std::string *body, std::string *error) {
  ix::HttpClient client;
  auto args = client.createRequest(url);
  args->connectTimeout = 20;
  args->transferTimeout = 30;
  args->followRedirects = true;
  args->maxRedirects = 3;
  args->compress = true;
  args->extraHeaders["Accept"] = "application/json";
  args->extraHeaders["User-Agent"] = "Helm Tides/0.1";

  ix::HttpResponsePtr response = client.get(url, args);
  if (!response) {
    if (error) *error = "NOAA fetch returned no response";
    return false;
  }
  if (response->errorCode != ix::HttpErrorCode::Ok) {
    if (error) {
      *error = "NOAA fetch failed: " + response->errorMsg;
    }
    return false;
  }
  if (response->statusCode != 200) {
    if (error) {
      *error = "NOAA fetch HTTP status " + std::to_string(response->statusCode);
    }
    return false;
  }
  *body = response->body;
  return true;
}

void PrintUsage() {
  std::cerr
      << "usage: helm-tides-fetch --provider noaa-coops-us --station ID "
         "--date YYYY-MM-DD --cache-dir DIR [--datum MLLW] "
         "[--station-name NAME] (--input-json FILE | --live)\n"
         "       helm-tides-fetch --provider fiji-met-cosppac --station ID "
         "--date YYYY-MM-DD --cache-dir DIR --input-calendar FILE\n"
         "       helm-tides-fetch --resolve-lat LAT --resolve-lon LON "
         "--date YYYY-MM-DD --cache-dir DIR "
         "[--ready-radius-nm NM] [--execute-request] "
         "[--input-json FILE | --input-calendar FILE | --live]\n";
}

}  // namespace

int main(int argc, char **argv) {
  std::string provider_region_id = "noaa-coops-us";
  std::string station_id;
  std::string station_name;
  std::string datum_name = "MLLW";
  std::string day_text;
  std::string cache_dir;
  std::string input_json;
  std::string input_calendar;
  std::string source_url;
  std::string fetched_utc;
  int interval_minutes = 60;
  bool live = false;
  bool execute_request = false;
  double resolve_lat = 0.0;
  double resolve_lon = 0.0;
  double ready_radius_nm = 60.0;
  bool has_resolve_lat = false;
  bool has_resolve_lon = false;

  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    if ((arg == "--provider" || arg == "--provider-region") && i + 1 < argc) {
      provider_region_id = argv[++i];
    } else if (arg == "--station" && i + 1 < argc) {
      station_id = argv[++i];
    } else if (arg == "--station-name" && i + 1 < argc) {
      station_name = argv[++i];
    } else if (arg == "--datum" && i + 1 < argc) {
      datum_name = argv[++i];
    } else if ((arg == "--date" || arg == "--time") && i + 1 < argc) {
      day_text = argv[++i];
    } else if (arg == "--cache-dir" && i + 1 < argc) {
      cache_dir = argv[++i];
    } else if (arg == "--input-json" && i + 1 < argc) {
      input_json = argv[++i];
    } else if (arg == "--input-calendar" && i + 1 < argc) {
      input_calendar = argv[++i];
    } else if (arg == "--source-url" && i + 1 < argc) {
      source_url = argv[++i];
    } else if (arg == "--fetched-utc" && i + 1 < argc) {
      fetched_utc = argv[++i];
    } else if (arg == "--interval-minutes" && i + 1 < argc) {
      interval_minutes = std::atoi(argv[++i]);
    } else if (arg == "--resolve-lat" && i + 1 < argc) {
      if (!ParseDouble(argv[++i], &resolve_lat)) {
        PrintError("bad --resolve-lat");
        return 2;
      }
      has_resolve_lat = true;
    } else if (arg == "--resolve-lon" && i + 1 < argc) {
      if (!ParseDouble(argv[++i], &resolve_lon)) {
        PrintError("bad --resolve-lon");
        return 2;
      }
      has_resolve_lon = true;
    } else if (arg == "--ready-radius-nm" && i + 1 < argc) {
      if (!ParseDouble(argv[++i], &ready_radius_nm)) {
        PrintError("bad --ready-radius-nm");
        return 2;
      }
    } else if (arg == "--execute-request") {
      execute_request = true;
    } else if (arg == "--dry-run") {
      execute_request = false;
    } else if (arg == "--live") {
      live = true;
    } else if (arg == "--help" || arg == "-h") {
      PrintUsage();
      return 0;
    } else {
      PrintUsage();
      PrintError("unknown or incomplete argument: " + arg);
      return 2;
    }
  }

  if (cache_dir.empty()) {
    if (const char *env = std::getenv("HELM_TIDES_CACHE_DIR")) cache_dir = env;
  }
  const bool resolve_mode = has_resolve_lat || has_resolve_lon;
  if (resolve_mode) {
    if (!has_resolve_lat || !has_resolve_lon) {
      PrintError("--resolve-lat and --resolve-lon must be supplied together");
      return 2;
    }
    if (day_text.empty()) {
      PrintError("--date YYYY-MM-DD or --time UTC_ISO is required");
      return 2;
    }
    if (cache_dir.empty()) {
      PrintError("--cache-dir or HELM_TIDES_CACHE_DIR is required");
      return 2;
    }

    std::time_t day_utc = 0;
    if (!ParseDay(day_text, &day_utc)) {
      PrintError("bad date/time; use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ");
      return 2;
    }

    helm::tides::TideEngine engine;
    engine.SetOfficialPredictionCacheDir(cache_dir);
    helm::tides::OfficialPredictionRequest request =
        engine.PlanOfficialPredictionRequest(resolve_lat, resolve_lon, day_utc,
                                             ready_radius_nm);

    const bool source_supplied =
        live || !input_json.empty() || !input_calendar.empty();
    const bool should_execute = execute_request || source_supplied;
    if (!request.ok) {
      PrintRequestPlan(request, false, !should_execute, request.status,
                       nullptr);
      return 1;
    }
    if (request.blocked) {
      PrintRequestPlan(request, false, !should_execute, request.status,
                       nullptr);
      return 0;
    }
    if (request.cached && !request.cache_refresh_due) {
      PrintRequestPlan(request, false, !should_execute,
                       "cache already satisfies request", nullptr);
      return 0;
    }
    if (!should_execute) {
      PrintRequestPlan(request, false, true,
                       "dry-run: request was planned but not executed",
                       nullptr);
      return 0;
    }

    if (request.provider_region_id == "noaa-coops-us") {
      if (input_json.empty() && !live) {
        PrintError("NOAA request execution needs --input-json FILE or --live");
        return 2;
      }
      if (!input_calendar.empty()) {
        PrintError("NOAA request execution does not use --input-calendar");
        return 2;
      }
    } else if (request.provider_region_id == "fiji-met-cosppac") {
      if (input_calendar.empty()) {
        PrintError("Fiji request execution needs --input-calendar FILE");
        return 2;
      }
      if (!input_json.empty() || live) {
        PrintError("Fiji request execution does not use --input-json or --live");
        return 2;
      }
    } else {
      PrintRequestPlan(request, false, false,
                       "provider request execution is not implemented",
                       nullptr);
      return 0;
    }

    helm::tides::OfficialTideReference reference =
        FindReference(request.provider_region_id, request.station_id,
                      request.station_name, request.datum_name);
    if (request.provider_region_id == "fiji-met-cosppac" &&
        reference.datum_name == "MLLW") {
      reference.datum_name = "Tide Prediction Datum";
    }

    if (source_url.empty()) {
      source_url = request.provider_region_id == "noaa-coops-us"
                       ? request.fetch_url
                       : request.source_url;
    }

    std::string body;
    std::string error;
    if (!input_json.empty() || !input_calendar.empty()) {
      const std::string input_path =
          !input_json.empty() ? input_json : input_calendar;
      if (!ReadFile(input_path, &body, &error)) {
        PrintError(error);
        return 1;
      }
    } else {
      ix::initNetSystem();
      bool ok = FetchLive(source_url, &body, &error);
      ix::uninitNetSystem();
      if (!ok) {
        PrintError(error);
        return 1;
      }
    }

    helm::tides::OfficialPredictionCacheInfo cache;
    bool wrote_cache = false;
    if (request.provider_region_id == "noaa-coops-us") {
      wrote_cache = helm::tides::WriteNoaaCoopsPredictionCache(
          reference, cache_dir, day_utc, body, source_url, fetched_utc, &cache,
          &error);
    } else {
      wrote_cache = helm::tides::WriteFijiMetCalendarCache(
          reference, cache_dir, day_utc, body, source_url, fetched_utc, &cache,
          &error);
    }
    if (!wrote_cache) {
      PrintError(error);
      return 1;
    }

    PrintRequestPlan(request, true, false, "cache populated", &cache);
    return 0;
  }

  if (station_id.empty()) {
    PrintError("--station is required");
    return 2;
  }
  if (day_text.empty()) {
    PrintError("--date YYYY-MM-DD or --time UTC_ISO is required");
    return 2;
  }
  if (cache_dir.empty()) {
    PrintError("--cache-dir or HELM_TIDES_CACHE_DIR is required");
    return 2;
  }
  if (provider_region_id == "noaa-coops-us" &&
      (input_json.empty() == !live || !input_calendar.empty())) {
    PrintError("NOAA uses exactly one of --input-json FILE or --live");
    return 2;
  }
  if (provider_region_id == "fiji-met-cosppac" &&
      (input_calendar.empty() || !input_json.empty() || live)) {
    PrintError("Fiji Met/COSPPac uses --input-calendar FILE only");
    return 2;
  }
  if (provider_region_id != "noaa-coops-us" &&
      provider_region_id != "fiji-met-cosppac") {
    PrintError("provider fetch is not implemented: " + provider_region_id);
    return 2;
  }

  std::time_t day_utc = 0;
  if (!ParseDay(day_text, &day_utc)) {
    PrintError("bad date/time; use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ");
    return 2;
  }

  helm::tides::OfficialTideReference reference =
      FindReference(provider_region_id, station_id, station_name, datum_name);
  if (provider_region_id == "fiji-met-cosppac" && datum_name == "MLLW") {
    reference.datum_name = "Tide Prediction Datum";
  }

  std::string generated_url;
  if (provider_region_id == "noaa-coops-us") {
    generated_url = helm::tides::NoaaCoopsPredictionUrl(reference, day_utc,
                                                        interval_minutes);
    if (source_url.empty()) source_url = generated_url;
  } else if (source_url.empty()) {
    source_url = reference.source_url;
  }

  std::string body;
  std::string error;
  bool used_live = false;
  if (!input_json.empty() || !input_calendar.empty()) {
    std::string input_path =
        !input_json.empty() ? input_json : input_calendar;
    if (!ReadFile(input_path, &body, &error)) {
      PrintError(error);
      return 1;
    }
  } else {
    ix::initNetSystem();
    used_live = true;
    bool ok = FetchLive(source_url, &body, &error);
    ix::uninitNetSystem();
    if (!ok) {
      PrintError(error);
      return 1;
    }
  }

  helm::tides::OfficialPredictionCacheInfo cache;
  bool wrote_cache = false;
  if (provider_region_id == "noaa-coops-us") {
    wrote_cache = helm::tides::WriteNoaaCoopsPredictionCache(
        reference, cache_dir, day_utc, body, source_url, fetched_utc, &cache,
        &error);
  } else {
    wrote_cache = helm::tides::WriteFijiMetCalendarCache(
        reference, cache_dir, day_utc, body, source_url, fetched_utc, &cache,
        &error);
  }
  if (!wrote_cache) {
    PrintError(error);
    return 1;
  }

  std::cout << "{\"ok\":true"
            << ",\"provider_region_id\":\""
            << JsonEscape(reference.provider_region_id) << "\""
            << ",\"provider\":\"" << JsonEscape(reference.provider) << "\""
            << ",\"station_id\":\"" << JsonEscape(reference.station_id)
            << "\""
            << ",\"station_name\":\"" << JsonEscape(reference.station_name)
            << "\""
            << ",\"datum_name\":\"" << JsonEscape(reference.datum_name)
            << "\""
            << ",\"mode\":\""
            << (used_live ? "live" :
                         (!input_calendar.empty() ? "calendar" : "fixture"))
            << "\""
            << ",\"source_url\":\"" << JsonEscape(source_url) << "\""
            << ",\"cache\":";
  WriteCacheJson(std::cout, cache);
  std::cout << "}\n";
  return 0;
}
