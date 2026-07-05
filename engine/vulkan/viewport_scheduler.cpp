#include "viewport_scheduler.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <tuple>
#include <utility>

namespace helm::schedule {
namespace {

inline constexpr double kWebMercatorLatLimit = 85.05112878;
inline constexpr int kDefaultTileSizePx = 256;

double clamp_lat(double lat) {
  return std::max(-kWebMercatorLatLimit, std::min(kWebMercatorLatLimit, lat));
}

double clamp_lon(double lon) {
  return std::max(-180.0, std::min(180.0, lon));
}

std::pair<int, int> deg2num(double lon, double lat, int z) {
  lat = clamp_lat(lat);
  const int n = 1 << z;
  int x = static_cast<int>((lon + 180.0) / 360.0 * n);
  const double lat_rad = lat * 3.14159265358979323846 / 180.0;
  int y = static_cast<int>((1.0 - std::asinh(std::tan(lat_rad)) / 3.14159265358979323846) / 2.0 * n);
  x = std::max(0, std::min(n - 1, x));
  y = std::max(0, std::min(n - 1, y));
  return {x, y};
}

std::array<double, 4> num2bbox(int z, int x, int y) {
  const double n = static_cast<double>(1 << z);
  const double west = x / n * 360.0 - 180.0;
  const double east = (x + 1) / n * 360.0 - 180.0;
  const double north = std::atan(std::sinh(3.14159265358979323846 * (1.0 - 2.0 * y / n))) *
                       180.0 / 3.14159265358979323846;
  const double south = std::atan(std::sinh(3.14159265358979323846 * (1.0 - 2.0 * (y + 1) / n))) *
                       180.0 / 3.14159265358979323846;
  return {west, south, east, north};
}

std::string normalize_cache_key(const std::map<std::string, std::string>& parts) {
  std::ostringstream out;
  bool first = true;
  for (const auto& [key, value] : parts) {
    if (!first) out << ';';
    first = false;
    out << key << '=' << value;
  }
  return out.str();
}

std::string build_cache_key(const RendererIdentity& renderer, const std::string& source_epoch,
                            const TileCoord& tile, const std::string& display_fingerprint,
                            int overscan_px) {
  std::map<std::string, std::string> parts;
  parts["display_fp"] = display_fingerprint;
  parts["overscan"] = std::to_string(overscan_px);
  parts["renderer"] = renderer.backend.empty() ? "vulkan" : renderer.backend;
  parts["scene_schema"] =
      renderer.scene_schema.empty() ? "helm.render.model.v1" : renderer.scene_schema;
  parts["source_epoch"] = source_epoch;
  parts["x"] = std::to_string(tile.x);
  parts["y"] = std::to_string(tile.y);
  parts["z"] = std::to_string(tile.z);
  if (!renderer.renderer_sha.empty()) {
    parts["renderer_sha"] = renderer.renderer_sha;
  }
  return normalize_cache_key(parts);
}

std::string build_cache_epoch(const std::string& source_epoch, const ScheduleRequest& request) {
  const std::string scene_schema = request.renderer.scene_schema.empty()
                                       ? "helm.render.model.v1"
                                       : request.renderer.scene_schema;
  return source_epoch + ":" + scene_schema + ":" + request.display_fingerprint;
}

TileCoord anchor_tile(const VisibleViewport& visible) {
  if (visible.anchor_tile.has_value()) {
    return *visible.anchor_tile;
  }
  if (visible.z == 0) {
    throw ScheduleError("visible requires anchor_tile or center+z");
  }
  const auto [x, y] = deg2num(visible.center.lon, visible.center.lat, static_cast<int>(visible.z));
  return TileCoord{visible.z, static_cast<std::uint32_t>(x), static_cast<std::uint32_t>(y)};
}

std::set<TileCoord> visible_tiles(const VisibleViewport& visible) {
  const int z = static_cast<int>(visible.z);
  if (visible.viewport_width_px == 0 || visible.viewport_height_px == 0) {
    throw ScheduleError("visible.viewport_px must be [width, height]");
  }
  const int width_px = static_cast<int>(visible.viewport_width_px);
  const int height_px = static_cast<int>(visible.viewport_height_px);
  const double dpr = visible.device_pixel_ratio > 0 ? visible.device_pixel_ratio : 1.0;
  const TileCoord anchor = anchor_tile(visible);
  const auto bbox = num2bbox(static_cast<int>(anchor.z), static_cast<int>(anchor.x),
                             static_cast<int>(anchor.y));
  const double west = bbox[0];
  const double south = bbox[1];
  const double east = bbox[2];
  const double north = bbox[3];
  const double tile_w = (east - west) / kDefaultTileSizePx;
  const double tile_h = (north - south) / kDefaultTileSizePx;
  const double half_w_deg = (width_px * dpr * tile_w) / 2.0;
  const double half_h_deg = (height_px * dpr * tile_h) / 2.0;
  double lon = visible.has_center ? visible.center.lon : (west + east) / 2.0;
  double lat = visible.has_center ? visible.center.lat : (south + north) / 2.0;
  const double view_west = clamp_lon(lon - half_w_deg);
  const double view_south = clamp_lat(lat - half_h_deg);
  const double view_east = clamp_lon(lon + half_w_deg);
  const double view_north = clamp_lat(lat + half_h_deg);

  const auto [x0, y0] = deg2num(view_west, view_north, z);
  const auto [x1, y1] = deg2num(view_east, view_south, z);
  std::set<TileCoord> tiles;
  for (int x = std::min(x0, x1); x <= std::max(x0, x1); ++x) {
    for (int y = std::min(y0, y1); y <= std::max(y0, y1); ++y) {
      tiles.insert(TileCoord{static_cast<std::uint32_t>(z), static_cast<std::uint32_t>(x),
                             static_cast<std::uint32_t>(y)});
    }
  }
  if (tiles.empty()) {
    tiles.insert(anchor);
  }
  return tiles;
}

std::set<TileCoord> ring_tiles(const TileCoord& anchor, int ring) {
  const int z = static_cast<int>(anchor.z);
  const int x0 = static_cast<int>(anchor.x);
  const int y0 = static_cast<int>(anchor.y);
  const int n = 1 << z;
  std::set<TileCoord> out;
  for (int dx = -ring; dx <= ring; ++dx) {
    for (int dy = -ring; dy <= ring; ++dy) {
      if (dx == 0 && dy == 0) continue;
      const int x = (x0 + dx) % n;
      const int y = std::max(0, std::min(n - 1, y0 + dy));
      out.insert(TileCoord{anchor.z, static_cast<std::uint32_t>(x), static_cast<std::uint32_t>(y)});
    }
  }
  return out;
}

std::vector<std::pair<TileCoord, double>> adjacent_zoom_tiles(const TileCoord& anchor,
                                                               const ZoomPolicy& zoom_policy) {
  std::vector<std::pair<TileCoord, double>> out;
  const int z = static_cast<int>(anchor.z);
  const int x = static_cast<int>(anchor.x);
  const int y = static_cast<int>(anchor.y);
  for (int delta : zoom_policy.adjacent_offsets) {
    const int target_z = z + delta;
    if (target_z < 0) continue;
    if (delta < 0 && zoom_policy.include_parent) {
      out.push_back({TileCoord{static_cast<std::uint32_t>(target_z),
                                static_cast<std::uint32_t>(x / 2),
                                static_cast<std::uint32_t>(y / 2)},
                     0.5});
    }
    if (delta > 0 && zoom_policy.include_children) {
      const int base_x = x * 2;
      const int base_y = y * 2;
      for (int dx = 0; dx <= 1; ++dx) {
        for (int dy = 0; dy <= 1; ++dy) {
          out.push_back({TileCoord{static_cast<std::uint32_t>(target_z),
                                    static_cast<std::uint32_t>(base_x + dx),
                                    static_cast<std::uint32_t>(base_y + dy)},
                         0.25});
        }
      }
    }
  }
  return out;
}

StalePolicy role_stale_policy(EntryRole role, ScheduleIntent intent) {
  if (role == EntryRole::Visible) return StalePolicy::Strict;
  if (role == EntryRole::Overscan) {
    return intent == ScheduleIntent::Revalidate ? StalePolicy::Strict
                                                : StalePolicy::StaleWhileRevalidate;
  }
  return StalePolicy::StaleOk;
}

int priority_for_role(EntryRole role) {
  switch (role) {
    case EntryRole::Visible: return 0;
    case EntryRole::Overscan: return 10;
    case EntryRole::Neighbor: return 20;
    case EntryRole::ZoomAdjacent: return 30;
    case EntryRole::Prefetch: return 40;
  }
  return 50;
}

std::string entry_id(const TileCoord& tile, EntryRole role) {
  std::ostringstream out;
  out << "tile.z" << tile.z << ".x" << tile.x << ".y" << tile.y << "."
      << EntryRoleName(role);
  return out.str();
}

}  // namespace

ScheduleResponse BuildScheduleResponse(const ScheduleRequest& request,
                                       const std::string& source_epoch_in) {
  if (request.schema_version != kScheduleRequestSchema) {
    throw ScheduleError(std::string("schema must be ") + kScheduleRequestSchema);
  }
  std::string epoch = source_epoch_in.empty() ? request.source_epoch_hint : source_epoch_in;
  if (epoch.empty()) {
    throw ScheduleError("source_epoch is required");
  }

  const TileCoord anchor = anchor_tile(request.visible);
  std::set<TileCoord> visible_set = visible_tiles(request.visible);

  std::set<TileCoord> overscan_set;
  for (int ring = 1; ring <= static_cast<int>(request.overscan.margin_tiles); ++ring) {
    const auto ring_set = ring_tiles(anchor, ring);
    overscan_set.insert(ring_set.begin(), ring_set.end());
  }
  for (auto it = overscan_set.begin(); it != overscan_set.end();) {
    if (visible_set.count(*it)) {
      it = overscan_set.erase(it);
    } else {
      ++it;
    }
  }

  std::set<TileCoord> neighbor_set;
  const int margin_tiles = static_cast<int>(request.overscan.margin_tiles);
  const int ring_count = static_cast<int>(request.neighbor_policy.ring_count);
  if (ring_count > margin_tiles) {
    for (int ring = margin_tiles + 1; ring <= ring_count; ++ring) {
      const auto ring_set = ring_tiles(anchor, ring);
      neighbor_set.insert(ring_set.begin(), ring_set.end());
    }
  }
  for (auto it = neighbor_set.begin(); it != neighbor_set.end();) {
    if (visible_set.count(*it) || overscan_set.count(*it)) {
      it = neighbor_set.erase(it);
    } else {
      ++it;
    }
  }

  ScheduleResponse response;
  response.schema_version = kScheduleResponseSchema;
  response.request_id = request.request_id;
  response.source_epoch = epoch;
  response.cache_epoch = build_cache_epoch(epoch, request);

  const int margin_px = static_cast<int>(request.overscan.margin_px);

  auto add_entry = [&](const TileCoord& tile, EntryRole role, double blend_weight) {
    ScheduleEntry entry;
    entry.entry_id = entry_id(tile, role);
    entry.kind = EntryKind::Tile;
    entry.role = role;
    entry.priority = priority_for_role(role);
    entry.tile = tile;
    entry.overscan_px = static_cast<std::uint32_t>(margin_px);
    entry.cache_key = build_cache_key(request.renderer, epoch, tile, request.display_fingerprint,
                                      margin_px);
    entry.stale_policy = role_stale_policy(role, request.intent);
    entry.blend_weight = blend_weight;
    response.entries.push_back(std::move(entry));
  };

  for (const TileCoord& tile : visible_set) {
    add_entry(tile, EntryRole::Visible, 1.0);
  }
  for (const TileCoord& tile : overscan_set) {
    add_entry(tile, EntryRole::Overscan, 1.0);
  }
  for (const TileCoord& tile : neighbor_set) {
    add_entry(tile, EntryRole::Neighbor, 1.0);
  }
  for (const auto& [tile, blend] : adjacent_zoom_tiles(anchor, request.zoom_policy)) {
    add_entry(tile, EntryRole::ZoomAdjacent, blend);
  }

  std::sort(response.entries.begin(), response.entries.end(), EntryLess);

  response.totals.entries = static_cast<std::uint32_t>(response.entries.size());
  response.totals.visible = 0;
  response.totals.overscan = 0;
  response.totals.neighbor = 0;
  response.totals.zoom_adjacent = 0;
  for (const ScheduleEntry& entry : response.entries) {
    switch (entry.role) {
      case EntryRole::Visible: ++response.totals.visible; break;
      case EntryRole::Overscan: ++response.totals.overscan; break;
      case EntryRole::Neighbor: ++response.totals.neighbor; break;
      case EntryRole::ZoomAdjacent: ++response.totals.zoom_adjacent; break;
      default: break;
    }
  }
  return response;
}

bool ScheduleResponseEqual(const ScheduleResponse& lhs, const ScheduleResponse& rhs) {
  if (lhs.schema_version != rhs.schema_version || lhs.request_id != rhs.request_id ||
      lhs.source_epoch != rhs.source_epoch || lhs.cache_epoch != rhs.cache_epoch ||
      lhs.entries.size() != rhs.entries.size()) {
    return false;
  }
  for (std::size_t i = 0; i < lhs.entries.size(); ++i) {
    const ScheduleEntry& a = lhs.entries[i];
    const ScheduleEntry& b = rhs.entries[i];
    if (a.entry_id != b.entry_id || a.kind != b.kind || a.role != b.role ||
        a.priority != b.priority || a.tile != b.tile || a.overscan_px != b.overscan_px ||
        a.cache_key != b.cache_key || a.stale_policy != b.stale_policy ||
        a.blend_weight != b.blend_weight) {
      return false;
    }
  }
  return lhs.totals.entries == rhs.totals.entries && lhs.totals.visible == rhs.totals.visible &&
         lhs.totals.overscan == rhs.totals.overscan &&
         lhs.totals.neighbor == rhs.totals.neighbor &&
         lhs.totals.zoom_adjacent == rhs.totals.zoom_adjacent;
}

}  // namespace helm::schedule
