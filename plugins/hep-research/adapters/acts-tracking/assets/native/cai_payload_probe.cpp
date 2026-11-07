// CAI-T07-3 probe (plan R37; t07-t09-task-sheets.md, T07 open items: "the path is to be probed"). Shows, on noiseless hits, whether one
// route of payload_geometry.hpp moves a plane for the Kalman refit and whether a refit with the corrected payload removes the shift.
// Not the CAI check itself: no fixture, no statistics, no residual or derivative output. The residual here is a leave-one-out refit's
// smoothed state at the left-out plane, the second method R33 allows. Hits come from fixed tracks through the frozen nominal geometry.
// Links no generator code, so it holds the design values of the sagitta case itself.
//
//   cai_payload_probe --route placement|rebuild
//
// Lines: PASS or FAIL with what was measured, RECORD for a reading that has no expectation, last line RESULT. Exit 0 only with no FAIL.
//
// Sign convention (R37): the reconstruction geometry's plane moves by +shift along loc0, the hit keeps its local value, the prediction
// in the moved frame falls by shift, so r = x_meas - x_pred rises by +shift. If instead the true plane sits at +shift, the hit's local
// value falls by shift, r falls by shift, and the corrected payload is the reconstruction geometry moved by +shift.
//
// Tolerances, fixed here before any run. position_tolerance_mm is 1e-3 mm, the TRUTH tolerance of check_t07_generator.py, a twentieth of
// the hit sigma. It covers the tangent line of expected_local: over the at most 1 mm from the nominal plane the track's curvature bends
// it by under 1e-6 mm at 3 GeV. A shift of 0.25 mm is 250 tolerances. shown_mm is 20 tolerances: a case whose largest expected residual
// is smaller cannot show much, so that case fails. chi2_floor is 16 measurements at one position tolerance each. That derivation leaves
// out the fit's prior term, (true - start)^T P^-1 (true - start): 0.0625 from the old chord start, the most of job 7490742's 0.0724, and at
// most 1.05e-5 from the curve start (numpy). The floor stands, because the term is the start's error and not a tolerance to widen.
#include <Acts/Definitions/Algebra.hpp>
#include <Acts/Geometry/TrackingVolume.hpp>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <exception>
#include <functional>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "kalman_refit.hpp"
#include "payload_geometry.hpp"
#include "plane_propagation.hpp"
#include "t07_data_file.hpp"
#include "t07_fixture_constants.hpp"
#include "telescope_geometry.hpp"

namespace {

constexpr double position_tolerance_mm = 1e-3;
constexpr double shown_mm = 20.0 * position_tolerance_mm;
constexpr double chi2_floor = 16.0 * (position_tolerance_mm / t07::hit_sigma_mm) * (position_tolerance_mm / t07::hit_sigma_mm);
constexpr double q_over_p_tolerance_per_gev = 1e-5;  // a quarter of a percent of sigma(q/p)
constexpr double tested_shift_mm = 0.25;
constexpr int tested_plane = 4;  // inside the track: both sides of it constrain the left-out fit
constexpr double in_envelope_normal_shift_mm = 0.5;     // layer_envelope_mm is 1
constexpr double past_envelope_normal_shift_mm = 1.5;   // read as a limit only, no expectation
constexpr double tested_rotation = 1e-2;                // at most 0.6 mm of normal offset where these tracks cross, inside the envelope

// The sagitta case, written apart from t07_cai_constants.hpp, which is generator code. Section 4 unit conversion, section 4.1 sigma(q/p).
constexpr double gev_per_tesla_mm = 0.299792458e-3;
constexpr double stated_sigma_q_over_p_per_gev = 0.00412;
constexpr double sagitta_bias_in_sigma = 5.0;
constexpr double sagitta_bias_tolerance = 0.10;  // of the bias: slope factor up to 4.5 %, prior up to 1.5 % at 3 GeV

struct ProbeTrack {
  double start_u_mm, start_v_mm, slope_u, slope_v, momentum_gev;
  int charge;
};

// Inside section 4.1's slopes and bins. Large slopes and offsets, so that a tilt of the plane shows at plane 4.
constexpr ProbeTrack probe_tracks[] = {{0.02, 12.0, 0.13, -0.05, 3.0, 1},  {-0.03, -20.0, -0.14, 0.13, 3.0, -1}, {0.0, 25.0, 0.14, 0.13, 6.0, 1},
                                       {0.01, -8.0, 0.05, -0.14, 6.0, -1}, {0.04, 3.0, -0.12, 0.09, 12.0, 1}};

std::vector<std::string> failed_lines;

void verdict(const std::string& label, bool passed, const std::string& detail) {
  std::cout << (passed ? "PASS " : "FAIL ") << label << ": " << detail << std::endl;
  if (!passed) {
    failed_lines.push_back(label);
  }
}

std::string number_text(double value) {
  std::ostringstream text;
  text.precision(6);
  text << value;
  return text.str();
}

double q_over_p_of(const ProbeTrack& track) { return double(track.charge) / track.momentum_gev; }

// A telescope and a refit on it. The refit holds a reference to the telescope, so this object does not move.
struct PayloadFit {
  t07::TelescopeGeometry telescope;
  t07::KalmanRefit fitter;
  explicit PayloadFit(t07::TelescopeGeometry geometry)
      : telescope(std::move(geometry)), fitter(telescope, t07::field_tesla, t07::hit_sigma_mm, t07::hit_sigma_mm) {}
};

using TelescopeFor = std::function<t07::TelescopeGeometry(const t07::PlaneDeltas&)>;

// Hits at the nominal crossings, with no smearing. hit_key is the position, plane order.
t07::DataEvent event_of(const std::vector<t07::PlaneCrossing>& crossings) {
  t07::DataEvent event;
  for (const t07::PlaneCrossing& crossing : crossings) {
    event.hits.push_back({std::uint32_t(event.hits.size()), std::uint32_t(crossing.plane), crossing.loc0_mm, crossing.loc1_mm});
  }
  return event;
}

t07::RefitResult refit(const PayloadFit& fit, const t07::DataEvent& event, double q_over_p, int left_out_plane) {
  t07::HitSet hit_set;
  hit_set.track_key = "probe";
  hit_set.assumed_q_over_p = q_over_p;
  for (const t07::PlaneHit& hit : event.hits) {
    if (int(hit.plane) != left_out_plane) {
      hit_set.hit_keys.push_back(hit.hit_key);
    }
  }
  t07::RefitResult result = fit.fitter.fit(hit_set, event);
  if (result.track.status != "fitted") {
    throw std::runtime_error("a refit failed, category " + result.track.failure_category);
  }
  return result;
}

const t07::ParameterRecord& smoothed_at(const t07::RefitResult& result, int plane) {
  for (const t07::StateRecord& state : result.states) {
    if (state.plane == plane) {
      for (const t07::ParameterRecord& parameters : result.parameters) {
        if (parameters.state_index == state.index && parameters.state_type == "smoothed") {
          return parameters;
        }
      }
    }
  }
  throw std::runtime_error("no smoothed state at plane " + std::to_string(plane));
}

// r = x_meas - x_pred at a plane, from the refit without that plane's hit.
Acts::Vector2 left_out_residual(const PayloadFit& fit, const t07::DataEvent& event, double q_over_p, int plane) {
  const t07::RefitResult result = refit(fit, event, q_over_p, plane);
  const t07::ParameterRecord& state = smoothed_at(result, plane);
  const t07::PlaneHit& hit = event.hits.at(plane - 1);
  return Acts::Vector2(hit.loc0_mm - state.parameters[0], hit.loc1_mm - state.parameters[1]);
}

// Where the tangent of a nominal crossing meets a moved plane, in that plane's frame. Independent of ACTS's navigation and propagation.
Acts::Vector2 expected_local(const Acts::Transform3& nominal, const Acts::Transform3& moved, const t07::PlaneCrossing& crossing) {
  const Acts::Vector3 on_nominal = nominal * Acts::Vector3(crossing.loc0_mm, crossing.loc1_mm, 0.0);
  const Acts::Vector3 direction(std::cos(crossing.phi) * std::sin(crossing.theta), std::sin(crossing.phi) * std::sin(crossing.theta), std::cos(crossing.theta));
  const Acts::Vector3 normal = moved.linear().col(2);
  const double step = normal.dot(moved.translation() - on_nominal) / normal.dot(direction);
  const Acts::Vector3 local = moved.inverse() * (on_nominal + step * direction);
  return Acts::Vector2(local.x(), local.y());
}

struct NoiselessTrack {
  ProbeTrack track;
  std::vector<t07::PlaneCrossing> crossings;
  t07::DataEvent event;
};

std::vector<NoiselessTrack> noiseless_tracks(const t07::PlanePropagation& propagation) {
  std::vector<NoiselessTrack> tracks;
  for (const ProbeTrack& track : probe_tracks) {
    const Acts::Vector3 start(-100.0, track.start_u_mm, track.start_v_mm);  // ACTS frame: x = fixture z, y = u, z = v
    const Acts::Vector3 direction = Acts::Vector3(1.0, track.slope_u, track.slope_v).normalized();
    NoiselessTrack noiseless{track, propagation.crossings(start, direction, q_over_p_of(track)), {}};
    if (int(noiseless.crossings.size()) != t07::plane_count) {
      throw std::runtime_error("a probe track crossed " + std::to_string(noiseless.crossings.size()) + " planes");
    }
    noiseless.event = event_of(noiseless.crossings);
    tracks.push_back(std::move(noiseless));
  }
  return tracks;
}

void same_geometry_as_frozen(const t07::TelescopeGeometry& nominal, const t07::TelescopeGeometry& frozen, const std::vector<NoiselessTrack>& tracks, bool alignable) {
  int sensitive_count = 0;
  nominal.tracking_geometry->visitSurfaces([&sensitive_count](const Acts::Surface* /*surface*/) { ++sensitive_count; });
  verdict("eight sensitive surfaces are visited", sensitive_count == t07::plane_count, std::to_string(sensitive_count));

  bool same_ids = true, same_transforms = true, sensitive = true, placed_as_stated = true;
  for (int plane = 0; plane < t07::plane_count; ++plane) {
    const Acts::Surface& ours = *nominal.planes.at(plane);
    const Acts::Surface& theirs = *frozen.planes.at(plane);
    same_ids = same_ids && ours.geometryId() == theirs.geometryId() && nominal.tracking_geometry->findSurface(ours.geometryId()) == &ours;
    same_transforms = same_transforms && ours.localToGlobalTransform(nominal.geometry_context).matrix() == theirs.localToGlobalTransform(frozen.geometry_context).matrix();
    sensitive = sensitive && ours.isSensitive();
    placed_as_stated = placed_as_stated && ours.isAlignable() == alignable && (ours.surfacePlacement() != nullptr) == alignable;
  }
  verdict("geometry identifiers equal the frozen geometry's", same_ids, "all planes, and each found again");
  verdict("nominal transforms equal the frozen geometry's, bit for bit", same_transforms, "all planes");
  verdict("planes are sensitive", sensitive, "all planes");
  verdict("planes are alignable through a placement, as this route says", placed_as_stated, alignable ? "placed" : "plain");

  const t07::PlanePropagation ours(nominal, t07::field_tesla);
  double largest = 0.0;
  for (const NoiselessTrack& track : tracks) {
    const Acts::Vector3 start(-100.0, track.track.start_u_mm, track.track.start_v_mm);
    const auto crossings = ours.crossings(start, Acts::Vector3(1.0, track.track.slope_u, track.track.slope_v).normalized(), q_over_p_of(track.track));
    if (crossings.size() != track.crossings.size()) {
      throw std::runtime_error("this route's telescope misses a plane");
    }
    for (std::size_t plane = 0; plane < crossings.size(); ++plane) {
      largest = std::max({largest, std::abs(crossings[plane].loc0_mm - track.crossings[plane].loc0_mm), std::abs(crossings[plane].loc1_mm - track.crossings[plane].loc1_mm)});
    }
  }
  verdict("crossings equal the frozen geometry's", largest < 1e-9, "largest difference " + number_text(largest) + " mm");
}

void plane_moves_alone(const TelescopeFor& telescope_for, const t07::TelescopeGeometry& frozen) {
  t07::PlaneDeltas deltas{};
  deltas[tested_plane - 1].shift_loc0_mm = tested_shift_mm;
  const t07::TelescopeGeometry moved = telescope_for(deltas);
  double moved_plane_error = 0.0, largest_other = 0.0;
  for (int plane = 0; plane < t07::plane_count; ++plane) {
    const Acts::Vector3 change = moved.planes.at(plane)->center(moved.geometry_context) - frozen.planes.at(plane)->center(frozen.geometry_context);
    if (plane == tested_plane - 1) {
      moved_plane_error = (change - Acts::Vector3(0.0, tested_shift_mm, 0.0)).norm();  // loc0 is ACTS y
    } else {
      largest_other = std::max(largest_other, change.norm());
    }
  }
  verdict("a shift along loc0 moves that plane along ACTS y", moved_plane_error < 1e-12, "error " + number_text(moved_plane_error) + " mm");
  verdict("no other plane moves", largest_other == 0.0, "largest " + number_text(largest_other) + " mm");
}

// Every degree of freedom of one plane: the refit's residual against the closed form, in the convention of the file comment.
void each_degree_of_freedom(const TelescopeFor& telescope_for, const t07::TelescopeGeometry& frozen, const std::vector<NoiselessTrack>& tracks) {
  struct NamedDelta {
    const char* name;
    t07::PlaneDelta delta;
  };
  const NamedDelta cases[] = {{"shift loc0", {.shift_loc0_mm = tested_shift_mm}},
                              {"shift loc1", {.shift_loc1_mm = -tested_shift_mm}},
                              {"shift normal", {.shift_normal_mm = in_envelope_normal_shift_mm}},
                              {"rotation about loc0", {.rotation_loc0 = tested_rotation}},
                              {"rotation about loc1", {.rotation_loc1 = tested_rotation}},
                              {"rotation about the normal", {.rotation_normal = tested_rotation}}};
  const Acts::Transform3& nominal = frozen.planes.at(tested_plane - 1)->localToGlobalTransform(frozen.geometry_context);
  for (const NamedDelta& one_case : cases) {
    t07::PlaneDeltas deltas{};
    deltas[tested_plane - 1] = one_case.delta;
    const PayloadFit fit(telescope_for(deltas));
    const Acts::Transform3 moved = t07::moved_plane_transform(nominal, one_case.delta);
    double largest_error = 0.0, largest_expected = 0.0;
    for (const NoiselessTrack& track : tracks) {
      const t07::PlaneHit& hit = track.event.hits.at(tested_plane - 1);
      const Acts::Vector2 expected = Acts::Vector2(hit.loc0_mm, hit.loc1_mm) - expected_local(nominal, moved, track.crossings.at(tested_plane - 1));
      const Acts::Vector2 measured = left_out_residual(fit, track.event, q_over_p_of(track.track), tested_plane);
      largest_error = std::max(largest_error, (measured - expected).cwiseAbs().maxCoeff());
      largest_expected = std::max(largest_expected, expected.cwiseAbs().maxCoeff());
    }
    verdict(std::string("residual follows the closed form, ") + one_case.name, largest_error < position_tolerance_mm && largest_expected > shown_mm,
            "largest error " + number_text(largest_error) + " mm, largest expected " + number_text(largest_expected) + " mm");
  }
}

// CAI-T07-1's sign, and CAI-T07-3's sentence: the true plane sits at +shift, nominal reconstruction sees it, the corrected payload removes it.
void corrected_payload_removes_the_shift(const TelescopeFor& telescope_for, const std::vector<NoiselessTrack>& tracks) {
  t07::PlaneDeltas corrected{}, wrong_sign{};
  corrected[tested_plane - 1].shift_loc0_mm = tested_shift_mm;
  wrong_sign[tested_plane - 1].shift_loc0_mm = -tested_shift_mm;
  const PayloadFit nominal(telescope_for(t07::PlaneDeltas{}));
  const PayloadFit with_corrected(telescope_for(corrected));
  const PayloadFit with_wrong_sign(telescope_for(wrong_sign));

  double sign_error = 0.0, honest_error = 0.0, removed_error = 0.0, wrong_error = 0.0, smallest_shifted_chi2 = 1e300, largest_corrected_chi2 = 0.0, largest_q_over_p_change = 0.0;
  for (const NoiselessTrack& track : tracks) {
    const double q_over_p = q_over_p_of(track.track);
    t07::DataEvent shifted = track.event;
    shifted.hits.at(tested_plane - 1).loc0_mm -= tested_shift_mm;

    honest_error = std::max(honest_error, (left_out_residual(with_corrected, track.event, q_over_p, tested_plane) - Acts::Vector2(tested_shift_mm, 0.0)).cwiseAbs().maxCoeff());
    sign_error = std::max(sign_error, (left_out_residual(nominal, shifted, q_over_p, tested_plane) - Acts::Vector2(-tested_shift_mm, 0.0)).cwiseAbs().maxCoeff());
    removed_error = std::max(removed_error, left_out_residual(with_corrected, shifted, q_over_p, tested_plane).cwiseAbs().maxCoeff());
    wrong_error = std::max(wrong_error, (left_out_residual(with_wrong_sign, shifted, q_over_p, tested_plane) - Acts::Vector2(-2.0 * tested_shift_mm, 0.0)).cwiseAbs().maxCoeff());

    smallest_shifted_chi2 = std::min(smallest_shifted_chi2, double(refit(nominal, shifted, q_over_p, 0).track.chi2));
    const t07::RefitResult corrected_fit = refit(with_corrected, shifted, q_over_p, 0);
    const t07::RefitResult honest_fit = refit(nominal, track.event, q_over_p, 0);
    largest_corrected_chi2 = std::max(largest_corrected_chi2, double(corrected_fit.track.chi2));
    largest_q_over_p_change = std::max(largest_q_over_p_change, std::abs(smoothed_at(corrected_fit, 1).parameters[4] - smoothed_at(honest_fit, 1).parameters[4]));
  }
  verdict("reconstruction plane moved by +shift, fixed hits: r rises by +shift", honest_error < position_tolerance_mm, "error " + number_text(honest_error) + " mm");
  verdict("true plane at +shift, nominal refit: r falls by shift", sign_error < position_tolerance_mm, "error " + number_text(sign_error) + " mm");
  verdict("CAI-T07-3: a refit with the corrected payload removes the shift", removed_error < position_tolerance_mm, "largest r " + number_text(removed_error) + " mm");
  verdict("control: a payload of the wrong sign doubles the shift", wrong_error < position_tolerance_mm, "error " + number_text(wrong_error) + " mm");
  verdict("the shift raises the fit's chi2", smallest_shifted_chi2 > 10.0, "smallest " + number_text(smallest_shifted_chi2));
  verdict("the corrected payload returns chi2 to its floor", largest_corrected_chi2 < chi2_floor, "largest " + number_text(largest_corrected_chi2) + ", floor " + number_text(chi2_floor));
  verdict("the corrected payload returns q/p to the honest fit's", largest_q_over_p_change < q_over_p_tolerance_per_gev, "largest change " + number_text(largest_q_over_p_change) + " per GeV");
}

// The design of CAI-T07-4 in one track per charge: t07-telescope-cai/1's displacement, its sign, and that the same deltas as a payload undo it.
void sagitta_as_payload(const TelescopeFor& telescope_for, const std::vector<NoiselessTrack>& tracks) {
  const double curvature_per_mm = sagitta_bias_in_sigma * stated_sigma_q_over_p_per_gev * gev_per_tesla_mm * t07::field_tesla / 2.0;
  const double centre_mm = 0.5 * (t07::plane_count - 1) * t07::plane_spacing_mm;
  const double mean_square_mm2 = t07::plane_spacing_mm * t07::plane_spacing_mm * (t07::plane_count * t07::plane_count - 1) / 12.0;
  t07::PlaneDeltas deformation{};
  for (int plane = 0; plane < t07::plane_count; ++plane) {
    const double offset_mm = plane * t07::plane_spacing_mm - centre_mm;
    deformation[plane].shift_loc0_mm = curvature_per_mm * (offset_mm * offset_mm - mean_square_mm2);
  }
  const PayloadFit nominal(telescope_for(t07::PlaneDeltas{}));
  const PayloadFit with_deformation(telescope_for(deformation));
  const double expected_bias = sagitta_bias_in_sigma * stated_sigma_q_over_p_per_gev;
  double largest_bias_error = 0.0, largest_undone = 0.0;
  for (const NoiselessTrack& track : tracks) {
    if (track.track.momentum_gev != 3.0) {
      continue;  // the refit's prior on q/p pulls harder at high momentum (kalman_refit.hpp), which is not what this line reads
    }
    const double q_over_p = q_over_p_of(track.track);
    t07::DataEvent deformed = track.event;
    for (int plane = 0; plane < t07::plane_count; ++plane) {
      deformed.hits.at(plane).loc0_mm -= deformation[plane].shift_loc0_mm;
    }
    const double biased = smoothed_at(refit(nominal, deformed, q_over_p, 0), 1).parameters[4];
    const double undone = smoothed_at(refit(with_deformation, deformed, q_over_p, 0), 1).parameters[4];
    largest_bias_error = std::max(largest_bias_error, std::abs(biased - q_over_p - expected_bias) / expected_bias);
    largest_undone = std::max(largest_undone, std::abs(undone - q_over_p));
  }
  verdict("sagitta deformation shifts q/p by +5 sigma for both charges", largest_bias_error < sagitta_bias_tolerance, "largest relative error " + number_text(largest_bias_error));
  verdict("the same deformation as a payload undoes it", largest_undone < q_over_p_tolerance_per_gev, "largest change " + number_text(largest_undone) + " per GeV");
}

void past_the_envelope(const TelescopeFor& telescope_for, const std::vector<NoiselessTrack>& tracks) {
  t07::PlaneDeltas deltas{};
  deltas[tested_plane - 1].shift_normal_mm = past_envelope_normal_shift_mm;
  try {
    const PayloadFit fit(telescope_for(deltas));
    const NoiselessTrack& track = tracks.front();
    const Acts::Vector2 residual = left_out_residual(fit, track.event, q_over_p_of(track.track), tested_plane);
    std::cout << "RECORD normal shift " << past_envelope_normal_shift_mm << " mm, past the layer envelope: fit held, r " << residual.x() << ", " << residual.y() << " mm" << std::endl;
  } catch (const std::exception& error) {
    std::cout << "RECORD normal shift " << past_envelope_normal_shift_mm << " mm, past the layer envelope: " << error.what() << std::endl;
  }
}

void placement_only_lines(const t07::PlacedTelescope& placed, const std::vector<NoiselessTrack>& tracks) {
  t07::PlaneDeltas moved_deltas{};
  moved_deltas[tested_plane - 1].shift_loc0_mm = tested_shift_mm;
  const t07::TelescopeGeometry nominal = placed.with_deltas(t07::PlaneDeltas{});
  const t07::TelescopeGeometry moved = placed.with_deltas(moved_deltas);
  verdict("two payloads share one tracking geometry and its surfaces", nominal.tracking_geometry == moved.tracking_geometry && nominal.planes == moved.planes, "no rebuild");

  const t07::KalmanRefit nominal_fit(nominal, t07::field_tesla, t07::hit_sigma_mm, t07::hit_sigma_mm);
  const t07::KalmanRefit moved_fit(moved, t07::field_tesla, t07::hit_sigma_mm, t07::hit_sigma_mm);
  t07::HitSet hit_set;
  hit_set.track_key = "interleaved";
  hit_set.assumed_q_over_p = q_over_p_of(tracks.front().track);
  for (const t07::PlaneHit& hit : tracks.front().event.hits) {
    hit_set.hit_keys.push_back(hit.hit_key);
  }
  const auto first = nominal_fit.fit(hit_set, tracks.front().event);
  const auto between = moved_fit.fit(hit_set, tracks.front().event);
  const auto again = nominal_fit.fit(hit_set, tracks.front().event);
  verdict("a nominal refit repeats bit for bit after a moved one", smoothed_at(first, 1).parameters == smoothed_at(again, 1).parameters, "smoothed state at plane 1");
  verdict("the moved refit between them differs", smoothed_at(first, tested_plane).parameters != smoothed_at(between, tested_plane).parameters, "smoothed state at the moved plane");

  bool refused = false;
  try {
    (void)nominal.planes.front()->localToGlobalTransform(Acts::GeometryContext::dangerouslyDefaultConstruct());
  } catch (const std::logic_error&) {
    refused = true;
  }
  verdict("a context with no payload is refused", refused, "an empty context");
}

void run_route(const std::string& route) {
  const t07::TelescopeGeometry frozen = t07::build_telescope_geometry();
  const t07::PlanePropagation frozen_propagation(frozen, t07::field_tesla);
  const std::vector<NoiselessTrack> tracks = noiseless_tracks(frozen_propagation);
  if (route == "placement") {
    const t07::PlacedTelescope placed;
    const TelescopeFor telescope_for = [&placed](const t07::PlaneDeltas& deltas) { return placed.with_deltas(deltas); };
    same_geometry_as_frozen(telescope_for(t07::PlaneDeltas{}), frozen, tracks, true);
    plane_moves_alone(telescope_for, frozen);
    each_degree_of_freedom(telescope_for, frozen, tracks);
    corrected_payload_removes_the_shift(telescope_for, tracks);
    sagitta_as_payload(telescope_for, tracks);
    past_the_envelope(telescope_for, tracks);
    placement_only_lines(placed, tracks);
  } else {
    const TelescopeFor telescope_for = [](const t07::PlaneDeltas& deltas) { return t07::rebuild_moved_telescope(deltas); };
    same_geometry_as_frozen(telescope_for(t07::PlaneDeltas{}), frozen, tracks, false);
    plane_moves_alone(telescope_for, frozen);
    each_degree_of_freedom(telescope_for, frozen, tracks);
    corrected_payload_removes_the_shift(telescope_for, tracks);
    sagitta_as_payload(telescope_for, tracks);
    past_the_envelope(telescope_for, tracks);
  }
}

}  // namespace

int main(int argc, char** argv) {
  const std::string route = argc == 3 && std::string(argv[1]) == "--route" ? argv[2] : "";
  if (route != "placement" && route != "rebuild") {
    std::cerr << "invalid input: usage: cai_payload_probe --route placement|rebuild\n";
    return 2;
  }
  std::cout << "PROBE route " << route << std::endl;
  try {
    run_route(route);
  } catch (const std::exception& error) {
    std::cout << "STOPPED: " << error.what() << ", so no line of this run is read as a result" << std::endl;
    return 3;
  }
  std::cout << "RESULT " << (failed_lines.empty() ? "PASS" : "FAIL") << " (" << failed_lines.size() << " failed lines)" << std::endl;
  return failed_lines.empty() ? 0 : 1;
}
