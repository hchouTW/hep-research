// Refit of a known hit set with the ACTS Kalman fitter (recipe reco.track.acts-kf-refit/1, t04-values-v4.md section 8.1):
// truth-assisted, counted apart, never reported as finding. It runs at zero field, or at section 4.1's 1 T.
#pragma once

#include <Acts/Definitions/TrackParametrization.hpp>

#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
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
// The prior on q/p, per GeV: the assumed q/p is the start, and this width keeps it from being a constraint (D1 stage 2 review, C-M1;
// R37, CAI-T07-4). One width for every track, not a share of the assumed value: the measurement's own width, m = 0.00412 per GeV at 1 T,
// does not depend on p (section 4.1), so a share of q/p tightens with momentum towards m. A prior s centred on a moves a fit by
// (m/s)^2 of its distance to a. Lower limit: a set that assumes anywhere inside its track's momentum bin, at most 1/3 per GeV away in
// [1.5, 3), moves a q/p pull by m (1/3) / s^2, which must stay under the smallest design se of any pull gate, 0.962/sqrt(12000 x 36) =
// 0.00146 (section 5.1): s at least 0.97. Upper limit: the smoother cancels s^2 down to m^2, and in an independent float64 filter
// sigma(q/p) stays within 3e-4 of the least-squares value at s = 1, 9e-4 at 10, and is 7e-2 off at 100. So 1. A pull's width then falls
// short by 8.5e-6 and a true bias by 1.7e-5, at every momentum. Not derived from pulls (section 2.2). Held for 1 T only: at a weaker field
// m grows towards s, so the driver refuses one. tests/adapters/test_acts_refit_field.py holds this arithmetic.
// Domain (D1 stage 4 review, m2): all of that is the prior's share. The single pass also linearises about the start, and that share does not
// fall with s. Measured on closed-form helix hits in [1.5, 3) GeV, largest move of q/p: 0.003 sigma at 10 % off, 0.06 sigma at a bin edge,
// 0.21 sigma at a factor 2, 1.22 sigma at the wrong sign. So a set's assumed q/p must be within 10 % of its value, or the fit must be repeated
// from its own result, as the finder does with a seed's q/p (track_finding.cpp). "A start, not a constraint" holds in that domain only.
inline constexpr double refit_prior_qop_sigma_per_gev = 1.0;
inline constexpr double refit_prior_time_sigma = 1.0;

struct HitSet {
  std::string track_key;
  std::uint32_t event_ordinal = 0;
  double assumed_q_over_p = 0.0;
  std::vector<std::uint32_t> hit_keys;
};

// Where the fit starts, at x = refit_start_x_mm. direction is a unit vector.
struct RefitStart {
  Acts::Vector3 position_mm;
  Acts::Vector3 direction;
};

struct RefitResult {
  TrackRecord track;
  std::vector<StateRecord> states;
  std::vector<ParameterRecord> parameters;
};

// The R33 outputs of one fit (track_fit_outputs.hpp, t07-r33/1), in the product's records (acts-tracking-product/2), state indices along the
// track as in RefitResult. acts_unbiased is not written to the product: ACTS's own calculateUnbiasedParametersCovariance (Utilities/TrackHelpers.hpp)
// at each measurement, loc0 and loc1 of its unbiased state and covariance, filled only when with_acts_unbiased is set, so cai_track_output_check.cpp
// can hold the plugin's formula against it.
struct ActsUnbiasedReading {
  std::int32_t state_index = 0;
  std::array<double, 2> loc{};
  std::array<double, 3> covariance{};  // 00, 01, 11 of the unbiased state's loc0, loc1
};

struct RefitOutputs {
  bool with_acts_unbiased = false;  // set by the caller, kept by fit(): only cai_track_output_check asks for ACTS's unbiased state
  std::vector<TrackOutputRecord> track_output;  // one for a fitted track, none for a failed one
  std::vector<ResidualRecord> residuals;
  std::vector<MeasurementOutputRecord> measurement_outputs;
  std::vector<ResidualCovarianceRecord> residual_covariance;  // one for a fitted track, none for a failed one
  std::vector<ActsUnbiasedReading> acts_unbiased;  // empty unless with_acts_unbiased
};

// A fit that used fewer hits than the known set is not a fit of that set (BP03): a surface the track missed drops a hit with no
// error from the fitter. Such a track fails.
inline bool fit_lost_a_hit(std::int32_t measurements, std::int32_t outliers, std::size_t hit_count) {
  return std::size_t(measurements + outliers) != hit_count;
}

// Two planes fix a line and no curvature, so in a field their q/p would be the prior speaking under a product that says measured (D1 stage 4
// review, m5; t04-prereg.md, "Unidentifiable quantity reported with precision"). Such a set fails as a track and stays in the denominator.
inline constexpr std::size_t planes_to_measure_q_over_p = 3;
inline bool hit_set_measures_nothing_of_q_over_p(std::size_t plane_count_in_set, double field_along_v_tesla) {
  return field_along_v_tesla != 0.0 && plane_count_in_set < planes_to_measure_q_over_p;
}

class KalmanRefit {
 public:
  KalmanRefit(const TelescopeGeometry& telescope, double field_along_v_tesla, double sigma_loc0_mm, double sigma_loc1_mm);
  ~KalmanRefit();

  // The curve through the set's first and last hit with the set's assumed q/p, in this field: hits and what the hit set already
  // assumes, no truth. A straight chord is off by a slope of about k B (q/p) L / 2, and one Kalman pass linearises about that start:
  // on noiseless hits job 7490742 left 3e-4 per GeV in q/p at 3 GeV, and an independent filter gives 0.46 sigma(q/p) at worst at
  // 1.5 GeV. At zero field the curve is the chord, bit for bit. Hits are read as if on nominal planes, whatever payload the telescope
  // carries: harmless at the shifts probed, but a large move of the first or last plane moves the start, for R36's loop to mind.
  RefitStart start_of(const HitSet& hit_set, const DataEvent& event) const;

  // Throws std::invalid_argument on a hit set the event does not hold. A fit that fails returns a failed track.
  RefitResult fit(const HitSet& hit_set, const DataEvent& event) const;
  // The same from a stated start: cai_refit_start_probe.cpp compares starts through this. The prior stays centred on the start.
  RefitResult fit(const HitSet& hit_set, const DataEvent& event, const RefitStart& start) const;
  // The same fit, and its R33 outputs (D1 stage 8). The fit itself is the one above, bit for bit: the outputs only read its states.
  RefitResult fit(const HitSet& hit_set, const DataEvent& event, RefitOutputs& outputs) const;

 private:
  RefitResult fit_from(const HitSet& hit_set, const DataEvent& event, const RefitStart& start, RefitOutputs* outputs) const;
  // J_{k<-ref} per state, or nullopt with failure set when the smoothed reference state cannot be carried to a surface.
  std::optional<std::vector<Acts::BoundMatrix>> reference_transports(const RefitResult& result, std::int32_t reference, std::string& failure) const;
  struct Machinery;
  const TelescopeGeometry& m_telescope;
  double m_sigma_loc0_mm;
  double m_sigma_loc1_mm;
  double m_field_along_v_tesla;
  std::unique_ptr<Machinery> m_machinery;
};

}  // namespace t07
