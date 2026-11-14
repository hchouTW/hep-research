// CAI-T07-2 (plan R37; t07-t09-task-sheets.md, T07, Acceptance) and the R33 cross-checks that need the fitter's own states (D1 stage 8). Data side: it reads a
// data file and a hit-set file, links no generator, seed or truth code, and holds no fixture identity.
//
//   cai_track_output_check --data-file D --hit-sets H --field-tesla 1
//
// For each hit set (exactly tracks_per_stratum of them) it refits through KalmanRefit with the R33 outputs, as the driver does, then:
//  1. Derivatives. At each measurement it holds the smoothed state fixed (position on the nominal plane, direction, q/p) and moves that plane through the placement
//     route (PlacedTelescope::with_deltas, payload_geometry.hpp) by +-h, +-h/2, +-h/4 in each degree of freedom of t07-plane-rigid/1. The fixed trajectory, the exact
//     helix of the uniform field through that state, is re-intersected with the moved plane (Newton), without refitting (R37). Central differences of the local position,
//     with the hit fixed, give dr/da = -dl/da. Against them: the derivative the product holds (ACTS's alignmentToBoundDerivative with the path correction, mapped,
//     track_fit_outputs.hpp) and the plugin's closed form, both at h/4; ACTS's against the closed form; and the halving rule below. Every plane, every degree of freedom.
//  2. ACTS's rotation helper read as rigid rotations (acts_alignment_map), on every plane.
//  3. The plugin's unbiased residual against ACTS's calculateUnbiasedParametersCovariance (Utilities/TrackHelpers.hpp) on every measurement.
//  4. A leave-one-out refit beside it, the second method R33 allows: reported against its prediction, not asserted. The fitter makes no state
//     before its first measurement and stops at its last (KalmanFitter.hpp: "no holes before the first measurement"; it ends once every
//     measurement is found), so planes 1 and 8 have no state to read in their leave-one-out fit, and the reading covers planes 2 to 7.
//  5. Reference derivatives (D1 stage 8, fix rounds 1 and 2). The product's dr_k/dq_ref = -H J_{k<-ref}, J the propagator's transport Jacobian of
//     the smoothed reference state carried to state k's surface (KalmanRefit::reference_transports), against central differences of the exact helix
//     about the same smoothed reference state: moved by +-h, +-h/2, +-h/4 in each bound parameter, the fixed helix through it re-intersected with each
//     measured nominal plane. Same halving rule. Both linearize at the same state, so they differ by the differences' step error and rounding
//     (numpy: truncation under 6e-8 (1 + |D|) at h/4, halving ratios 3.86 to 4.21 above the floor) and by the stepper's own error against the exact
//     helix: RK4 truncation over steps of at most 50 mm in the uniform field, of order (kappa s)^4 ~ 1e-8 relative, and the end point, accepted within
//     s_onSurfaceTolerance 1e-4 mm of the plane (Definitions/Tolerance.hpp), which moves the Jacobian by about kappa x 1e-4 mm ~ 2e-8. No material,
//     so no other effect. Tolerance 1e-6 (1 + |a|).
// Reference steps: 1e-3 mm in loc0 and loc1, 1e-3 rad in phi and theta, 1e-2 per GeV in q/p, 1e-3 mm in time (which no crossing depends on);
// tolerance 1e-6 (1 + |a|) at h/4 in each parameter's unit (fix round 2: a plain numerical tolerance; fix round 1's column scaling is withdrawn).
// Tolerances, steps and the halving rule, fixed before any run (tests/adapters/test_acts_track_outputs.py holds the same numbers and their numpy prediction):
//  - steps 1e-3 mm for shifts, 1e-3 rad for rotations, halved twice. Agreement at h/4: 1e-8 for shifts, 1e-5 mm/rad for rotations (predicted 3e-11 and 1.3e-6);
//    ACTS's against the closed form within 1e-8 (1 + |a|), rounding only.
//  - halving: where |D(h) - D(h/2)| exceeds rounding_floor, |D(h) - D(h/2)| / |D(h/2) - D(h/4)| lies in [3.5, 4.5] (central differences are second order, 4.000
//    predicted); where it does not, |D(h/2) - D(h/4)| stays under rounding_floor too.
//  - rigidity 1e-12; unbiased against ACTS 1e-9 of the residual's sigma and 1e-7 relative in the covariance; leave-one-out predicted within 1e-3 of sigma.
// Lines: CONFIG first, then PASS or FAIL with what was measured, DERIVATIVE and RECORD readings, last line RESULT. Exit 0 only with no FAIL.
#include <Acts/Definitions/Algebra.hpp>
#include <Acts/Definitions/TrackParametrization.hpp>
#include <Acts/Definitions/Units.hpp>
#include <Acts/Utilities/UnitVectors.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <exception>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "kalman_refit.hpp"
#include "payload_geometry.hpp"
#include "sha256.hpp"
#include "t07_data_file.hpp"
#include "t07_fixture_constants.hpp"
#include "telescope_geometry.hpp"
#include "track_fit_outputs.hpp"

namespace {

constexpr int tracks_per_stratum = 25;
constexpr double shift_step_mm = 1e-3;
constexpr double rotation_step_rad = 1e-3;
constexpr int halvings = 2;
constexpr double shift_tolerance = 1e-8;
constexpr double rotation_tolerance_mm_per_rad = 1e-5;
constexpr double acts_closed_form_tolerance = 1e-8;
constexpr double ratio_low = 3.5;
constexpr double ratio_high = 4.5;
constexpr double rounding_floor = 1e-9;
constexpr double rigidity_tolerance = 1e-12;
constexpr double unbiased_acts_sigma = 1e-9;
constexpr double unbiased_acts_covariance = 1e-7;
constexpr double leave_one_out_predicted_sigma = 1e-3;
constexpr std::array<double, 6> reference_steps{1e-3, 1e-3, 1e-3, 1e-3, 1e-2, 1e-3};  // loc0, loc1 mm; phi, theta rad; q/p per GeV; time mm
constexpr double reference_relative = 1e-6;
constexpr double reference_absolute = 1e-6;
// Fix round 4 (coordinator's ruling): the reference derivatives' halving ratio is tested only where the first difference exceeds 1e-8. Below it the
// ratio is dominated by rounding (numpy, 16 seeds: theta reaches 4.500 just above the 1e-9 floor, but stays within 3.93 to 4.05 above 1e-8), so a test
// there measures arithmetic, not convergence. Set from the numerics before any job. At or under rounding_floor, |D(h/2) - D(h/4)| must stay under it
// too, as before; the agreement tolerance applies to every entry. The alignment derivatives keep their 1e-9 floor: their rotation ratios above it are
// 3.957 to 4.025 (fixture-like numpy), far inside the band, so they have no such issue.
constexpr double reference_ratio_floor = 1e-8;
constexpr std::array<const char*, 6> bound_names{"loc0", "loc1", "phi", "theta", "q/p", "time"};

std::vector<std::string> failed_lines;
std::size_t derivative_failures = 0;
constexpr std::size_t printed_derivative_failures = 20;  // later ones are counted, not printed

void verdict(const std::string& label, bool passed, const std::string& detail) {
  std::cout << (passed ? "PASS " : "FAIL ") << label << ": " << detail << std::endl;
  if (!passed) {
    failed_lines.push_back(label);
  }
}

std::string number_text(double value) {
  std::ostringstream text;
  text.precision(4);
  text << value;
  return text.str();
}

std::map<std::string, std::string> parse_flags(int argc, char** argv) {
  std::map<std::string, std::string> flags;
  for (int index = 1; index < argc; index += 2) {
    const std::string flag = argv[index];
    if (flag.rfind("--", 0) != 0 || index + 1 >= argc) {
      throw std::invalid_argument("expected --flag value, got " + flag);
    }
    flags[flag.substr(2)] = argv[index + 1];
  }
  for (const char* name : {"data-file", "hit-sets", "field-tesla"}) {
    if (flags.count(name) == 0) {
      throw std::invalid_argument(std::string("--") + name + " is required");
    }
  }
  if (flags.size() != 3) {
    throw std::invalid_argument("only --data-file, --hit-sets and --field-tesla");
  }
  return flags;
}

// acts-tracking-hit-sets/1, as the driver reads it: role truth-assisted, bound to the data file by its digest.
std::vector<t07::HitSet> read_hit_sets(const std::string& path, const std::string& data_sha256) {
  t07::refuse_truth_path(path);
  std::ifstream input(path);
  std::string format, role_key, role, digest_key, digest;
  input >> format >> role_key >> role >> digest_key >> digest;
  if (!input || format != "acts-tracking-hit-sets/1" || role_key != "role" || role != "truth-assisted" || digest_key != "data_sha256" || digest != data_sha256) {
    throw std::invalid_argument("refused: " + path + " is not acts-tracking-hit-sets/1 for this data file");
  }
  std::vector<t07::HitSet> hit_sets;
  std::string record;
  while (input >> record) {
    t07::HitSet hit_set;
    std::size_t count = 0;
    if (record != "hit_set" || !(input >> hit_set.track_key >> hit_set.event_ordinal >> hit_set.assumed_q_over_p >> count) || count > std::size_t(t07::plane_count)) {
      throw std::invalid_argument("refused: a malformed hit_set in " + path);
    }
    hit_set.hit_keys.resize(count);
    for (std::uint32_t& key : hit_set.hit_keys) {
      if (!(input >> key)) {
        throw std::invalid_argument("refused: a hit_set ends early in " + path);
      }
    }
    hit_sets.push_back(hit_set);
  }
  return hit_sets;
}

// The fixed trajectory: the exact helix through a state in a uniform field along ACTS z, dT/ds = w T x z, w = (q/p) k B.
struct Helix {
  Acts::Vector3 position;
  Acts::Vector3 direction;
  double bending_per_mm = 0.0;

  std::pair<Acts::Vector3, Acts::Vector3> at(double path_mm) const {
    if (bending_per_mm == 0.0) {
      return {position + path_mm * direction, direction};
    }
    const double turn = bending_per_mm * path_mm;
    const double sine = std::sin(turn);
    const double versine = 2.0 * std::sin(0.5 * turn) * std::sin(0.5 * turn);
    const Acts::Vector3 moved = position + Acts::Vector3((direction.x() * sine + direction.y() * versine) / bending_per_mm,
                                                         (direction.y() * sine - direction.x() * versine) / bending_per_mm, direction.z() * path_mm);
    const Acts::Vector3 turned(direction.x() * std::cos(turn) + direction.y() * sine, direction.y() * std::cos(turn) - direction.x() * sine, direction.z());
    return {moved, turned};
  }

  // Where the helix meets a plane, in that plane's local frame: Newton along the path from the straight-line guess.
  Acts::Vector2 local_crossing(const Acts::Transform3& plane) const {
    const Acts::Vector3 normal = plane.linear().col(2);
    const Acts::Vector3 centre = plane.translation();
    double path = -normal.dot(position - centre) / normal.dot(direction);
    for (int iteration = 0; iteration < 50; ++iteration) {
      const auto [point, tangent] = at(path);
      const double step = -normal.dot(point - centre) / normal.dot(tangent);
      path += step;
      if (std::abs(step) < 1e-13) {
        break;
      }
    }
    const Acts::Vector3 local = plane.inverse() * at(path).first;
    return Acts::Vector2(local.x(), local.y());
  }
};

void set_component(t07::PlaneDelta& delta, int dof, double value) {
  double* components[] = {&delta.shift_loc0_mm, &delta.shift_loc1_mm, &delta.shift_normal_mm, &delta.rotation_loc0, &delta.rotation_loc1, &delta.rotation_normal};
  *components[dof] = value;
}

// dr/da by central differences at one step: the hit fixed, so dr = -dl.
Acts::Vector2 central_difference(const t07::PlacedTelescope& placed, const Helix& helix, int plane_index, int dof, double step) {
  auto local_at = [&](double value) {
    t07::PlaneDeltas deltas{};
    set_component(deltas[plane_index], dof, value);
    const t07::TelescopeGeometry moved = placed.with_deltas(deltas);
    return helix.local_crossing(moved.planes.at(plane_index)->localToGlobalTransform(moved.geometry_context));
  };
  return -(local_at(step) - local_at(-step)) / (2.0 * step);
}

// The local crossing of a nominal plane by the exact helix through a bound state on another nominal plane.
Acts::Vector2 crossing_from(const Acts::Transform3& reference_plane, const std::array<double, 6>& bound, const Acts::Transform3& target) {
  Helix helix;
  helix.direction = Acts::makeDirectionFromPhiTheta(bound[Acts::eBoundPhi], bound[Acts::eBoundTheta]);
  helix.position = reference_plane * Acts::Vector3(bound[Acts::eBoundLoc0], bound[Acts::eBoundLoc1], 0.0);
  helix.bending_per_mm = bound[Acts::eBoundQOverP] * t07::field_tesla * Acts::UnitConstants::T;
  return helix.local_crossing(target);
}

struct DerivativeSummary {
  std::size_t entries = 0, at_floor = 0, halving_failures = 0;
  double acts_error = 0.0, closed_error = 0.0, acts_closed = 0.0, largest_halving = 0.0;
  double ratio_min = std::numeric_limits<double>::infinity(), ratio_max = 0.0;
};

const t07::ParameterRecord& parameters_at(const t07::RefitResult& result, std::int32_t state_index, const std::string& state_type) {
  for (const t07::ParameterRecord& record : result.parameters) {
    if (record.state_index == state_index && record.state_type == state_type) {
      return record;
    }
  }
  throw std::runtime_error("no " + state_type + " state " + std::to_string(state_index) + " in " + result.track.key);
}

int run(const std::map<std::string, std::string>& flags) {
  std::cout << "CONFIG tracks " << tracks_per_stratum << " shift_step_mm " << shift_step_mm << " rotation_step_rad " << rotation_step_rad << " halvings " << halvings
            << " shift_tolerance " << shift_tolerance << " rotation_tolerance_mm_per_rad " << rotation_tolerance_mm_per_rad << " acts_closed_form_tolerance "
            << acts_closed_form_tolerance << " ratio_band " << ratio_low << " " << ratio_high << " rounding_floor " << rounding_floor << " rigidity_tolerance "
            << rigidity_tolerance << " unbiased_acts_sigma " << unbiased_acts_sigma << " unbiased_acts_covariance " << unbiased_acts_covariance
            << " leave_one_out_predicted_sigma " << leave_one_out_predicted_sigma << " reference_steps";
  for (const double step : reference_steps) {
    std::cout << " " << step;
  }
  std::cout << " reference_relative " << reference_relative << " reference_absolute " << reference_absolute << " reference_ratio_floor " << reference_ratio_floor
            << std::endl;
  if (std::stod(flags.at("field-tesla")) != t07::field_tesla) {
    throw std::invalid_argument("the check runs at the fixture's field only");
  }
  const std::string data_path = flags.at("data-file");
  t07::DataFileReader reader(data_path);  // a truth path stops here
  const std::vector<t07::HitSet> hit_sets = read_hit_sets(flags.at("hit-sets"), t07::sha256_of_file(data_path));
  verdict("the hit-set file holds the stated number of tracks", int(hit_sets.size()) == tracks_per_stratum, std::to_string(hit_sets.size()));
  std::map<std::uint32_t, const t07::HitSet*> by_event;
  for (const t07::HitSet& hit_set : hit_sets) {
    if (!by_event.emplace(hit_set.event_ordinal, &hit_set).second) {
      throw std::invalid_argument("two hit sets in one event: the CAI fixture has one track per event");
    }
  }

  const t07::TelescopeGeometry telescope = t07::build_telescope_geometry();
  const t07::KalmanRefit fitter(telescope, t07::field_tesla, reader.header().sigma_loc0_mm, reader.header().sigma_loc1_mm);
  const t07::PlacedTelescope placed;
  const t07::TelescopeGeometry placed_nominal = placed.with_deltas(t07::PlaneDeltas{});
  bool same_nominal = true;
  double largest_rigidity_error = 0.0;
  for (int plane = 0; plane < t07::plane_count; ++plane) {
    const Acts::Transform3& frozen = telescope.planes.at(plane)->localToGlobalTransform(telescope.geometry_context);
    same_nominal = same_nominal && frozen.matrix() == placed_nominal.planes.at(plane)->localToGlobalTransform(placed_nominal.geometry_context).matrix();
    largest_rigidity_error = std::max(largest_rigidity_error, t07::acts_alignment_map(frozen.linear()).rigidity_error);
  }
  verdict("the placement route's nominal planes are the refit's, bit for bit", same_nominal, "all planes");
  verdict("ACTS's rotation helper reads as rigid rotations, by columns", largest_rigidity_error <= rigidity_tolerance, "largest error " + number_text(largest_rigidity_error));

  std::array<DerivativeSummary, 6> summaries;
  std::array<DerivativeSummary, 6> reference_summaries;
  std::size_t reference_failures = 0;
  std::size_t fitted = 0, measurements = 0, unbiased_failures = 0, leave_one_out_states = 0;
  double unbiased_value_error = 0.0, unbiased_covariance_error = 0.0, leave_one_out_value = 0.0, leave_one_out_covariance = 0.0;
  t07::DataEvent event;
  for (std::uint32_t ordinal = 0; reader.next(event); ++ordinal) {
    const auto found = by_event.find(ordinal);
    if (found == by_event.end()) {
      continue;
    }
    const t07::HitSet& hit_set = *found->second;
    t07::RefitOutputs outputs;
    outputs.with_acts_unbiased = true;
    const t07::RefitResult result = fitter.fit(hit_set, event, outputs);
    if (result.track.status != "fitted") {
      verdict("a hit set fits", false, hit_set.track_key + " " + result.track.failure_category);
      continue;
    }
    ++fitted;
    std::map<std::int32_t, const t07::ActsUnbiasedReading*> acts_of;
    for (const t07::ActsUnbiasedReading& reading : outputs.acts_unbiased) {
      acts_of[reading.state_index] = &reading;
    }
    const std::int32_t reference = outputs.track_output.at(0).reference_state_index;
    const t07::ParameterRecord& reference_record = parameters_at(result, reference, "smoothed");
    std::array<double, 6> reference_state{};
    for (int parameter = 0; parameter < 6; ++parameter) {
      reference_state[parameter] = reference_record.parameters[parameter];
    }
    const Acts::Transform3& reference_plane =
        telescope.planes.at(std::size_t(result.states.at(std::size_t(reference)).plane - 1))->localToGlobalTransform(telescope.geometry_context);
    std::map<std::int32_t, const t07::ResidualRecord*> unbiased_of;
    for (const t07::ResidualRecord& record : outputs.residuals) {
      if (record.state_type == "unbiased") {
        unbiased_of[record.state_index] = &record;
      }
    }
    for (std::size_t position = 0; position < outputs.measurement_outputs.size(); ++position) {
      const t07::MeasurementOutputRecord& output = outputs.measurement_outputs[position];
      const t07::StateRecord& state = result.states.at(std::size_t(output.state_index));
      const int plane_index = state.plane - 1;
      ++measurements;

      // 1. Derivatives, with the smoothed state held fixed.
      const t07::ParameterRecord& smoothed = parameters_at(result, output.state_index, "smoothed");
      const Acts::Transform3& nominal = telescope.planes.at(plane_index)->localToGlobalTransform(telescope.geometry_context);
      Helix helix;
      helix.direction = Acts::makeDirectionFromPhiTheta(smoothed.parameters[Acts::eBoundPhi], smoothed.parameters[Acts::eBoundTheta]);
      helix.position = nominal * Acts::Vector3(smoothed.parameters[Acts::eBoundLoc0], smoothed.parameters[Acts::eBoundLoc1], 0.0);
      helix.bending_per_mm = smoothed.parameters[Acts::eBoundQOverP] * t07::field_tesla * Acts::UnitConstants::T;
      const t07::ResidualDerivative closed = t07::closed_form_residual_derivative(Acts::Vector2(smoothed.parameters[Acts::eBoundLoc0], smoothed.parameters[Acts::eBoundLoc1]),
                                                                                  nominal.linear().transpose() * helix.direction);
      for (int dof = 0; dof < 6; ++dof) {
        const double step = dof < 3 ? shift_step_mm : rotation_step_rad;
        std::array<Acts::Vector2, halvings + 1> differences;
        for (int halving = 0; halving <= halvings; ++halving) {
          differences[halving] = central_difference(placed, helix, plane_index, dof, step / double(1 << halving));
        }
        DerivativeSummary& summary = summaries[dof];
        const double tolerance = dof < 3 ? shift_tolerance : rotation_tolerance_mm_per_rad;
        for (int row = 0; row < 2; ++row) {
          ++summary.entries;
          const double acts = output.alignment_derivative[6 * row + dof];
          const double finest = differences[halvings][row];
          const double acts_error = std::abs(acts - finest), closed_error = std::abs(closed(row, dof) - finest), acts_closed = std::abs(acts - closed(row, dof));
          summary.acts_error = std::max(summary.acts_error, acts_error);
          summary.closed_error = std::max(summary.closed_error, closed_error);
          summary.acts_closed = std::max(summary.acts_closed, acts_closed / (1.0 + std::abs(closed(row, dof))));
          if ((acts_error > tolerance || closed_error > tolerance || acts_closed > acts_closed_form_tolerance * (1.0 + std::abs(closed(row, dof)))) &&
              ++derivative_failures <= printed_derivative_failures) {
            verdict("derivative " + std::string(t07::r32_plane_parameters[dof]) + " row " + std::to_string(row), false,
                    hit_set.track_key + " plane " + std::to_string(state.plane) + ": ACTS " + number_text(acts) + ", closed form " + number_text(closed(row, dof)) +
                        ", differences " + number_text(finest));
          }
          const double first = std::abs(differences[0][row] - differences[1][row]);
          const double second = std::abs(differences[1][row] - differences[2][row]);
          summary.largest_halving = std::max(summary.largest_halving, first);
          bool halving_holds = true;
          if (first > rounding_floor) {
            const double ratio = second > 0.0 ? first / second : std::numeric_limits<double>::infinity();
            summary.ratio_min = std::min(summary.ratio_min, ratio);
            summary.ratio_max = std::max(summary.ratio_max, ratio);
            halving_holds = ratio >= ratio_low && ratio <= ratio_high;
          } else {
            ++summary.at_floor;
            halving_holds = second <= rounding_floor;
          }
          if (!halving_holds) {
            ++summary.halving_failures;
          }
        }
      }

      // 5. The derivative against the reference state, with every other state let go: the helix through the moved reference state.
      for (int parameter = 0; parameter < 6; ++parameter) {
        std::array<Acts::Vector2, halvings + 1> differences;
        for (int halving = 0; halving <= halvings; ++halving) {
          const double step = reference_steps[std::size_t(parameter)] / double(1 << halving);
          std::array<double, 6> plus = reference_state, minus = reference_state;
          plus[std::size_t(parameter)] += step;
          minus[std::size_t(parameter)] -= step;
          differences[halving] = -(crossing_from(reference_plane, plus, nominal) - crossing_from(reference_plane, minus, nominal)) / (2.0 * step);
        }
        DerivativeSummary& summary = reference_summaries[std::size_t(parameter)];
        for (int row = 0; row < 2; ++row) {
          ++summary.entries;
          const double stored = output.reference_derivative[6 * row + parameter];
          const double error = std::abs(stored - differences[halvings][row]);
          const double limit = reference_relative * std::abs(stored) + reference_absolute;
          summary.acts_error = std::max(summary.acts_error, error / (1.0 + std::abs(stored)));
          if (error > limit && ++reference_failures <= printed_derivative_failures) {
            verdict(std::string("reference derivative d r_") + (row == 0 ? "loc0" : "loc1") + " / d " + bound_names[std::size_t(parameter)], false,
                    hit_set.track_key + " plane " + std::to_string(state.plane) + ": product " + number_text(stored) + ", differences " + number_text(differences[halvings][row]));
          }
          const double first = std::abs(differences[0][row] - differences[1][row]);
          const double second = std::abs(differences[1][row] - differences[2][row]);
          summary.largest_halving = std::max(summary.largest_halving, first);
          bool halving_holds = true;
          if (first > reference_ratio_floor) {
            const double ratio = second > 0.0 ? first / second : std::numeric_limits<double>::infinity();
            summary.ratio_min = std::min(summary.ratio_min, ratio);
            summary.ratio_max = std::max(summary.ratio_max, ratio);
            halving_holds = ratio >= ratio_low && ratio <= ratio_high;
          } else if (first <= rounding_floor) {
            ++summary.at_floor;
            halving_holds = second <= rounding_floor;
          }  // between the two floors: rounding-dominated, no halving test (the agreement tolerance above still applies)
          summary.halving_failures += halving_holds ? 0 : 1;
        }
      }

      // 3. The unbiased residual against ACTS's own, on states the fit used.
      if (state.kind != "measurement") {
        continue;
      }
      const t07::ResidualRecord& plugin = *unbiased_of.at(output.state_index);
      const t07::ActsUnbiasedReading& acts = *acts_of.at(output.state_index);
      const double variance0 = state.covariance[0], variance1 = state.covariance[2];
      const std::array<double, 2> acts_residual{state.loc0_mm - acts.loc[0], state.loc1_mm - acts.loc[1]};
      const std::array<double, 3> acts_covariance{variance0 + acts.covariance[0], state.covariance[1] + acts.covariance[1], variance1 + acts.covariance[2]};
      bool unbiased_agrees = true;
      for (int row = 0; row < 2; ++row) {
        const double sigma = std::sqrt(plugin.covariance[row == 0 ? 0 : 2]);
        const double error = std::abs(plugin.residual[row] - acts_residual[row]) / sigma;
        unbiased_value_error = std::max(unbiased_value_error, error);
        unbiased_agrees = unbiased_agrees && error <= unbiased_acts_sigma;
      }
      for (int entry = 0; entry < 3; ++entry) {
        const double scale = std::sqrt(plugin.covariance[0] * plugin.covariance[2]);
        const double error = std::abs(plugin.covariance[entry] - acts_covariance[entry]) / scale;
        unbiased_covariance_error = std::max(unbiased_covariance_error, error);
        unbiased_agrees = unbiased_agrees && error <= unbiased_acts_covariance;
      }
      unbiased_failures += unbiased_agrees ? 0 : 1;

      // 4. Leave-one-out, reported.
      t07::HitSet left_out = hit_set;
      left_out.track_key += "-without-plane-" + std::to_string(state.plane);
      left_out.hit_keys.erase(std::remove(left_out.hit_keys.begin(), left_out.hit_keys.end(), std::uint32_t(state.hit_key)), left_out.hit_keys.end());
      const t07::RefitResult refit = fitter.fit(left_out, event);
      for (const t07::StateRecord& other : refit.states) {
        if (other.plane == state.plane && refit.track.status == "fitted") {
          const t07::ParameterRecord& refitted = parameters_at(refit, other.index, "smoothed");
          ++leave_one_out_states;
          for (int row = 0; row < 2; ++row) {
            const double residual = (row == 0 ? state.loc0_mm : state.loc1_mm) - refitted.parameters[row];
            const double variance = (row == 0 ? variance0 : variance1) + refitted.covariance[row == 0 ? 0 : 6];
            leave_one_out_value = std::max(leave_one_out_value, std::abs(residual - plugin.residual[row]) / std::sqrt(plugin.covariance[row == 0 ? 0 : 2]));
            leave_one_out_covariance = std::max(leave_one_out_covariance, std::abs(variance / plugin.covariance[row == 0 ? 0 : 2] - 1.0));
          }
        }
      }
    }
  }
  verdict("every hit set was fitted", int(fitted) == tracks_per_stratum, std::to_string(fitted) + " of " + std::to_string(tracks_per_stratum));
  verdict("every fitted track has eight measurements with outputs", measurements == fitted * std::size_t(t07::plane_count), std::to_string(measurements));
  for (int dof = 0; dof < 6; ++dof) {
    const DerivativeSummary& summary = summaries[dof];
    std::cout << "DERIVATIVE " << t07::r32_plane_parameters[dof] << " entries " << summary.entries << " acts_vs_differences " << number_text(summary.acts_error)
              << " closed_vs_differences " << number_text(summary.closed_error) << " acts_vs_closed_relative " << number_text(summary.acts_closed) << " largest_halving_change "
              << number_text(summary.largest_halving) << " ratio " << number_text(summary.ratio_min) << " to " << number_text(summary.ratio_max) << " at_floor "
              << summary.at_floor << std::endl;
    verdict(std::string("halving converges, ") + t07::r32_plane_parameters[dof], summary.halving_failures == 0 && summary.entries > 0,
            std::to_string(summary.halving_failures) + " of " + std::to_string(summary.entries) + " entries outside the rule");
  }
  for (int parameter = 0; parameter < 6; ++parameter) {
    const DerivativeSummary& summary = reference_summaries[std::size_t(parameter)];
    std::cout << "REFERENCE-DERIVATIVE " << bound_names[std::size_t(parameter)] << " entries " << summary.entries << " largest_error_per_1_plus_a " << number_text(summary.acts_error)
              << " largest_halving_change " << number_text(summary.largest_halving) << " ratio " << number_text(summary.ratio_min) << " to " << number_text(summary.ratio_max)
              << " at_floor " << summary.at_floor << std::endl;
    verdict(std::string("reference halving converges, ") + bound_names[std::size_t(parameter)], summary.halving_failures == 0 && summary.entries > 0,
            std::to_string(summary.halving_failures) + " of " + std::to_string(summary.entries) + " entries outside the rule");
  }
  verdict("every reference derivative agrees with its differences", reference_failures == 0,
          std::to_string(reference_failures) + " entries beyond a tolerance, every measurement, every bound parameter, both rows");
  verdict("every derivative agrees with its differences", derivative_failures == 0,
          std::to_string(derivative_failures) + " entries beyond a tolerance, every plane, every degree of freedom, both rows");
  verdict("the unbiased residual is ACTS's own", unbiased_failures == 0 && measurements > 0,
          "largest " + number_text(unbiased_value_error) + " sigma, covariance " + number_text(unbiased_covariance_error) + ", " + std::to_string(unbiased_failures) + " beyond");
  std::cout << "RECORD leave-one-out refit against the unbiased residual, " << leave_one_out_states << " states: largest " << number_text(leave_one_out_value)
            << " sigma, covariance " << number_text(leave_one_out_covariance) << " relative, "
            << (leave_one_out_value <= leave_one_out_predicted_sigma ? "within" : "beyond") << " the prediction " << leave_one_out_predicted_sigma << std::endl;
  std::cout << "RESULT " << (failed_lines.empty() ? "PASS" : "FAIL") << std::endl;
  return failed_lines.empty() ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    return run(parse_flags(argc, argv));
  } catch (const std::invalid_argument& error) {
    std::cout << "STOPPED: invalid input: " << error.what() << std::endl;
    return 2;
  } catch (const std::exception& error) {
    std::cout << "STOPPED: " << error.what() << ", so no line of this run is read as a result" << std::endl;
    return 3;
  }
}
