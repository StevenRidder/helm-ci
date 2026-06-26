#include "helm_tides.h"

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
         "--date YYYY-MM-DD --cache-dir DIR --input-calendar FILE\n";
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
            << ",\"cache\":{\"cache_path\":\""
            << JsonEscape(cache.cache_path) << "\""
            << ",\"data_path\":\"" << JsonEscape(cache.data_path) << "\""
            << ",\"fetched_utc\":\"" << JsonEscape(cache.fetched_utc)
            << "\""
            << ",\"valid_start_utc\":\""
            << JsonEscape(cache.valid_start_utc) << "\""
            << ",\"valid_end_utc\":\"" << JsonEscape(cache.valid_end_utc)
            << "\""
            << ",\"refresh_after_utc\":\""
            << JsonEscape(cache.refresh_after_utc) << "\""
            << ",\"time_zone\":\"" << JsonEscape(cache.time_zone) << "\""
            << ",\"time_basis\":\"" << JsonEscape(cache.time_basis) << "\""
            << ",\"sample_count\":" << cache.sample_count
            << ",\"valid_for_time\":"
            << (cache.valid_for_time ? "true" : "false")
            << ",\"refresh_due\":"
            << (cache.refresh_due ? "true" : "false")
            << ",\"redistribution_cleared\":"
            << (cache.redistribution_cleared ? "true" : "false")
            << "}}\n";
  return 0;
}
