#pragma once
// Web Mercator slippy-tile helpers (parity with chart-viewport-scheduler.js / _webmerc.py).

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <tuple>
#include <utility>
#include <vector>

namespace helm::webmerc {

inline constexpr double kLatLimit = 85.05112878;

inline double clamp_lat(double lat) {
  return std::max(-kLatLimit, std::min(kLatLimit, lat));
}

inline double clamp_lon(double lon) {
  return std::max(-180.0, std::min(180.0, lon));
}

inline std::pair<int, int> deg2num(double lon, double lat, int z) {
  lat = clamp_lat(lat);
  const int n = 1 << z;
  int x = static_cast<int>(std::floor((lon + 180.0) / 360.0 * n));
  const double lat_rad = lat * 3.14159265358979323846 / 180.0;
  int y = static_cast<int>(
      std::floor((1.0 - std::asinh(std::tan(lat_rad)) / 3.14159265358979323846) / 2.0 * n));
  x = std::max(0, std::min(n - 1, x));
  y = std::max(0, std::min(n - 1, y));
  return {x, y};
}

struct Bbox {
  double west = 0;
  double south = 0;
  double east = 0;
  double north = 0;
};

inline Bbox num2bbox(int z, int x, int y) {
  const double n = static_cast<double>(1 << z);
  Bbox out;
  out.west = x / n * 360.0 - 180.0;
  out.east = (x + 1) / n * 360.0 - 180.0;
  out.north = std::atan(std::sinh(3.14159265358979323846 * (1.0 - 2.0 * y / n))) *
              180.0 / 3.14159265358979323846;
  out.south = std::atan(std::sinh(3.14159265358979323846 * (1.0 - 2.0 * (y + 1) / n))) *
              180.0 / 3.14159265358979323846;
  return out;
}

struct TileCoord {
  int z = 0;
  int x = 0;
  int y = 0;
};

inline std::vector<TileCoord> tiles_covering_bbox(double west, double south, double east,
                                                  double north, int z_min, int z_max) {
  std::vector<TileCoord> out;
  for (int z = z_min; z <= z_max; ++z) {
    const auto [x0, y_north] = deg2num(west, north, z);
    const auto [x1, y_south] = deg2num(east, south, z);
    const int xa = std::min(x0, x1);
    const int xb = std::max(x0, x1);
    const int ya = std::min(y_north, y_south);
    const int yb = std::max(y_north, y_south);
    for (int x = xa; x <= xb; ++x) {
      for (int y = ya; y <= yb; ++y) {
        const Bbox tb = num2bbox(z, x, y);
        if (tb.east <= west || tb.west >= east || tb.north <= south || tb.south >= north) {
          continue;
        }
        out.push_back(TileCoord{z, x, y});
      }
    }
  }
  return out;
}

}  // namespace helm::webmerc
