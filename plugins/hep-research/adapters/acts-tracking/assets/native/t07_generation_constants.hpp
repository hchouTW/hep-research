// How T07 events are drawn: t04-values-v4.md section 4.1, and the identities of section 3.2. Generator only: the driver does not
// reach this header (tests/adapters/test_acts_tracking.py), so a data-side recipe holds neither the bins nor the near rule.
#pragma once

#include <array>
#include <cmath>
#include <cstdint>
#include <string>

#include "t07_fixture_constants.hpp"

namespace t07 {

inline constexpr std::array<std::array<double, 2>, 4> momentum_bins_gev{{{1.5, 3.0}, {3.0, 6.0}, {6.0, 12.0}, {12.0, 24.0}}};
inline constexpr std::array<int, 3> tracks_per_event{6, 12, 36};     // Occupancy levels o1, o2, o3
inline constexpr std::array<int, 3> vertices_per_event{2, 2, 3};     // Vertices per event
inline constexpr std::array<double, 3> noise_means{100.0, 300.0, 1000.0};  // Noise hits per plane per event, Poisson mean
inline constexpr double noise_hit_efficiency = 0.98;  // Hit efficiency, noise fixture; 1.0 on the clean fixture
inline constexpr double vertex_u_half_range_mm = 0.05;   // Vertex position
inline constexpr double vertex_z_centre_mm = -100.0;
inline constexpr double vertex_z_half_range_mm = 0.2;
inline constexpr double vertex_v_half_range_mm = 30.0;
inline constexpr double resolution_unit_mm = 0.0184;     // u_v
inline constexpr std::array<double, 2> far_step_units{5.0, 25.0};   // Vertex separation, far: each step uniform [5, 25) u_v
inline constexpr std::array<double, 2> near_step_units{1.0, 5.0};   // near: each step uniform [1, 5) u_v
inline constexpr std::uint64_t near_event_modulus = 5;   // far when event_index mod 5 != 0
inline constexpr double slope_half_range = 0.15;         // Track slopes at the vertex, each view

inline constexpr int stratum_count = 12;                 // 4 momentum bins x 3 occupancy levels (section 4 and 7, Vertex bins)
inline constexpr std::uint32_t clean_fixture_id = 7001;  // section 3.2
inline constexpr std::uint32_t noise_fixture_id = 7002;
inline constexpr std::array<std::uint32_t, 8> known_blocks{1, 2, 3, 4, 5, 6, 11, 12};  // section 3.2, Block table

inline constexpr std::uint32_t no_hit_key = 0xffffffffu;

// Every hit leaves on one grid, 2^-30 mm, by one code path, so its bits cannot say how it was made (A09; D1 re-review N1). Without
// it a noise coordinate, -150 + 300 u, is a multiple of 2^-46 mm, and a track hit, crossing + smear, is not. The grid is 9.3e-10 mm,
// 2.1e7 below the hit sigma: the rounding error is at most 4.7e-10 mm, so it adds 7e-20 mm^2 to a variance of 4e-4 mm^2. It sits at
// least 14 bits above the coarsest noise resolution, 2^-44 mm, so a value's distance from a grid point is resolved for every hit
// and both kinds fill the grid alike. std::round sends a tie away from zero, which favours neither parity; round-half-even would
// mark exact ties as even. Adding 0.0 turns a -0.0 into +0.0.
inline constexpr double hit_grid_steps_per_mm = 1073741824.0;  // 2^30
inline double on_hit_grid(double coordinate_mm) { return std::round(coordinate_mm * hit_grid_steps_per_mm) / hit_grid_steps_per_mm + 0.0; }

enum class FixtureKind { clean, noise };

struct FixtureSpec {
  FixtureKind kind;
  std::uint32_t fixture_id;
  std::string generator;
  double hit_efficiency;
};

inline FixtureSpec fixture_spec(FixtureKind kind) {
  if (kind == FixtureKind::clean) {
    return {kind, clean_fixture_id, "t07-telescope-clean/1", 1.0};
  }
  return {kind, noise_fixture_id, "t07-telescope-noise/1", noise_hit_efficiency};
}

// Stratum numbering, left open by section 4.1 and chosen like T08's: 3 x momentum bin + occupancy level.
inline int momentum_bin_of(int stratum) { return stratum / 3; }
inline int occupancy_level_of(int stratum) { return stratum % 3; }

}  // namespace t07
