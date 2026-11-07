// t07-telescope-cai/1, the fixtures of CAI-T07-1 to 4 (t04-values-v4.md section 4.1, "CAI items"; plan R37), as Freeze A amendment 1
// proposes them: .superpowers/sdd/finish-plan/amendment-1-draft.md until the user's word. Everything not written here is section 4.1's
// clean column, read from t07_fixture_constants.hpp and t07_generation_constants.hpp. Generator only: the driver does not reach this
// header, so a recipe holds neither the deformation nor its ids.
#pragma once

#include <array>
#include <cstdint>

#include "t07_generation_constants.hpp"

namespace t07 {

inline constexpr char cai_generator_name[] = "t07-telescope-cai/1";
inline constexpr std::uint32_t cai_clean_fixture_id = 7003;    // section 3.2 row, proposed
inline constexpr std::uint32_t cai_sagitta_fixture_id = 7004;  // section 3.2 row, proposed
inline constexpr std::array<std::uint32_t, 2> cai_blocks{1, 6};  // interface runs, generator check. No other block belongs to these fixtures
inline constexpr int cai_stratum_count = 4;                    // stratum = momentum bin: one track per event has no occupancy level

// The sagitta-like mode (plan R37: "sagitta-like for a planar spectrometer"): plane k's true position is its nominal one plus
// d_k along +loc0, d_k = A ((z_k - z_c)^2 - <(z - z_c)^2>), a parabola in the plane position with mean zero. Its centring takes out
// the part a track offset would absorb at once; the rest, a pure z^2 term, is what a track's curvature absorbs, which is why it is weak.
// With u'' = -k B q/p in this frame, a hit that reads u - d_k looks like q/p raised by 2 A / (k B), for both charges alike.
// The amendment fixes that rise at 5 per-track sigma(q/p): sigma(q/p) 0.00412 per GeV (section 4.1) and 0.299792458 GeV/(T m) (section 4).
inline constexpr double cai_gev_per_tesla_mm = 0.299792458e-3;
inline constexpr double cai_sigma_q_over_p_per_gev = 0.00412;
inline constexpr double cai_sagitta_bias_in_sigma = 5.0;
inline constexpr double cai_sagitta_curvature_per_mm = cai_sagitta_bias_in_sigma * cai_sigma_q_over_p_per_gev * cai_gev_per_tesla_mm * field_tesla / 2.0;

inline double cai_sagitta_displacement_mm(int plane_index) {  // plane_index 0..7
  const double centre_mm = 0.5 * (plane_count - 1) * plane_spacing_mm;
  const double mean_square_mm2 = plane_spacing_mm * plane_spacing_mm * (plane_count * plane_count - 1) / 12.0;
  const double offset_mm = plane_index * plane_spacing_mm - centre_mm;
  return cai_sagitta_curvature_per_mm * (offset_mm * offset_mm - mean_square_mm2);
}

enum class CaiFixtureKind { clean, sagitta };

struct CaiFixture {
  CaiFixtureKind kind;
  std::uint32_t fixture_id;
};

inline CaiFixture cai_fixture(CaiFixtureKind kind) { return {kind, kind == CaiFixtureKind::clean ? cai_clean_fixture_id : cai_sagitta_fixture_id}; }

}  // namespace t07
