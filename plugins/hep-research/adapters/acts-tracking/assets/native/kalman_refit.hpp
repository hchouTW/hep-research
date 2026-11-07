// Refit of a known hit set with the ACTS Kalman fitter (recipe reco.track.acts-kf-refit/1, t04-values-v4.md section 8.1):
// truth-assisted, counted apart, never reported as finding. This file is stage 1 of T07: zero field only.
#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "native_product.hpp"
#include "t07_data_file.hpp"
#include "telescope_geometry.hpp"

namespace t07 {

// Not fixture values: stage-1 choices, written into every product as start_prior. A start upstream of plane 1, with a prior
// wide against what eight hits fix, so that the fit is the hits' least-squares line (straight-line case).
inline constexpr double refit_start_x_mm = -50.0;
inline constexpr double refit_prior_loc_sigma_mm = 10.0;
inline constexpr double refit_prior_angle_sigma = 0.1;
inline constexpr double refit_prior_relative_qop_sigma = 0.1;
inline constexpr double refit_prior_time_sigma = 1.0;

struct HitSet {
  std::string track_key;
  std::uint32_t event_ordinal = 0;
  double assumed_q_over_p = 0.0;
  std::vector<std::uint32_t> hit_keys;
};

struct RefitResult {
  TrackRecord track;
  std::vector<StateRecord> states;
  std::vector<ParameterRecord> parameters;
};

// A fit that used fewer hits than the known set is not a fit of that set (BP03): a surface the track missed drops a hit with no
// error from the fitter. Such a track fails.
inline bool fit_lost_a_hit(std::int32_t measurements, std::int32_t outliers, std::size_t hit_count) {
  return std::size_t(measurements + outliers) != hit_count;
}

class KalmanRefit {
 public:
  KalmanRefit(const TelescopeGeometry& telescope, double field_along_v_tesla, double sigma_loc0_mm, double sigma_loc1_mm);
  ~KalmanRefit();

  // Throws std::invalid_argument on a hit set the event does not hold. A fit that fails returns a failed track.
  RefitResult fit(const HitSet& hit_set, const DataEvent& event) const;

 private:
  struct Machinery;
  const TelescopeGeometry& m_telescope;
  double m_sigma_loc0_mm;
  double m_sigma_loc1_mm;
  std::unique_ptr<Machinery> m_machinery;
};

}  // namespace t07
