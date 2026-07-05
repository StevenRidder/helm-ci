#include "viewport_scheduler.h"
#include "viewport_scheduler_json.h"

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {

[[nodiscard]] std::string read_file(const std::string& path) {
  std::ifstream in(path);
  if (!in) throw std::runtime_error("cannot read " + path);
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

[[nodiscard]] std::string join_path(const std::string& dir, const std::string& name) {
  if (dir.empty() || dir.back() == '/') return dir + name;
  return dir + "/" + name;
}

[[nodiscard]] std::string manifest_string_field(const std::string& text, const std::string& key) {
  const std::string needle = "\"" + key + "\"";
  const std::size_t key_pos = text.find(needle);
  if (key_pos == std::string::npos) {
    throw std::runtime_error("manifest missing key: " + key);
  }
  const std::size_t colon = text.find(':', key_pos + needle.size());
  if (colon == std::string::npos) throw std::runtime_error("manifest malformed key: " + key);
  const std::size_t quote = text.find('"', colon + 1);
  if (quote == std::string::npos) throw std::runtime_error("manifest malformed value: " + key);
  const std::size_t end = text.find('"', quote + 1);
  if (end == std::string::npos) throw std::runtime_error("manifest malformed value: " + key);
  return text.substr(quote + 1, end - quote - 1);
}

void usage(const char* argv0) {
  std::cerr << "usage: " << argv0 << " <fixture-dir> [--print-hashes]\n";
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    usage(argv[0]);
    return 2;
  }

  const std::string fixture_dir = argv[1];
  bool print_hashes = false;
  for (int i = 2; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == "--print-hashes") {
      print_hashes = true;
    } else {
      usage(argv[0]);
      return 2;
    }
  }

  try {
    const std::string request_text = read_file(join_path(fixture_dir, "request.json"));
    const std::string response_text = read_file(join_path(fixture_dir, "response.json"));
    const std::string manifest_text = read_file(join_path(fixture_dir, "manifest.json"));

    const std::string source_epoch = manifest_string_field(manifest_text, "source_epoch");
    const std::string expected_request_hash =
        manifest_string_field(manifest_text, "request_json_sha256");
    const std::string expected_response_hash =
        manifest_string_field(manifest_text, "response_json_sha256");

    const helm::schedule::ScheduleRequest request =
        helm::schedule::json::ParseScheduleRequest(request_text);
    const helm::schedule::ScheduleResponse actual =
        helm::schedule::BuildScheduleResponse(request, source_epoch);
    const helm::schedule::ScheduleResponse expected =
        helm::schedule::json::ParseScheduleResponse(response_text);

    if (!helm::schedule::ScheduleResponseEqual(actual, expected)) {
      std::cerr << "fixture mismatch: " << fixture_dir << "\n";
      return 1;
    }

    const std::string request_hash = helm::schedule::json::Sha256Json(request_text);
    const std::string response_hash = helm::schedule::json::Sha256Json(response_text);
    if (request_hash != expected_request_hash || response_hash != expected_response_hash) {
      std::cerr << "hash mismatch: request=" << request_hash << " expected=" << expected_request_hash
                << "; response=" << response_hash << " expected=" << expected_response_hash << "\n";
      return 1;
    }

    if (print_hashes) {
      std::cout << "request_json_sha256=" << request_hash << "\n";
      std::cout << "response_json_sha256=" << response_hash << "\n";
    }

    std::cout << "ok entries=" << actual.totals.entries << " visible=" << actual.totals.visible
              << " overscan=" << actual.totals.overscan << "\n";
    return 0;
  } catch (const std::exception& ex) {
    std::cerr << "viewport-scheduler-fixture-check failed: " << ex.what() << "\n";
    return 1;
  }
}
