#pragma once
// mapbox/earcut.hpp wrapper (ISC) — parity with scripts/_earcut.py triangulate_rings().

#include "mapbox_earcut.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <utility>
#include <vector>

namespace helm::earcut {

struct Point {
  double x = 0;
  double y = 0;
};

using Ring = std::vector<Point>;
using Triangle = std::array<Point, 3>;

inline Ring clean_ring(Ring ring) {
  if (ring.size() >= 2 && ring.front().x == ring.back().x && ring.front().y == ring.back().y) {
    ring.pop_back();
  }
  return ring;
}

inline std::vector<Triangle> triangulate_rings(const Ring& exterior,
                                               const std::vector<Ring>& holes = {}) {
  std::vector<Triangle> out;
  const Ring ext = clean_ring(exterior);
  if (ext.size() < 3) return out;

  using PolyPoint = std::array<double, 2>;
  std::vector<std::vector<PolyPoint>> poly;
  poly.emplace_back();
  for (const Point& p : ext) poly.back().push_back({p.x, p.y});
  for (Ring hole : holes) {
    hole = clean_ring(std::move(hole));
    if (hole.size() < 3) continue;
    poly.emplace_back();
    for (const Point& p : hole) poly.back().push_back({p.x, p.y});
  }

  const std::vector<std::uint32_t> idx = mapbox::earcut<std::uint32_t>(poly);
  std::vector<Point> flat;
  flat.reserve(ext.size());
  for (const auto& ring : poly) {
    for (const auto& p : ring) flat.push_back({p[0], p[1]});
  }
  for (std::size_t k = 0; k + 2 < idx.size(); k += 3) {
    const Point a = flat[idx[k]];
    const Point b = flat[idx[k + 1]];
    const Point c = flat[idx[k + 2]];
    const double cross = (b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y);
    if (std::abs(cross) < 1.0) continue;
    out.push_back({a, b, c});
  }
  return out;
}

}  // namespace helm::earcut
