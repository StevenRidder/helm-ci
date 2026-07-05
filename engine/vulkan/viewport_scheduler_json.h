#pragma once

#include "viewport_scheduler.h"

#include <string>

namespace helm::schedule::json {

[[nodiscard]] ScheduleRequest ParseScheduleRequest(const std::string& text);
[[nodiscard]] ScheduleResponse ParseScheduleResponse(const std::string& text);
[[nodiscard]] std::string ScheduleResponseToJson(const ScheduleResponse& response);
[[nodiscard]] std::string CanonicalJson(const std::string& text);
[[nodiscard]] std::string Sha256Json(const std::string& json_text);

}  // namespace helm::schedule::json
