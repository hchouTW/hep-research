// Why job 7490742's probe left 3e-4 mm and 3e-4 per GeV on noiseless hits, on both routes: separates the refit's start, one Kalman pass,
// the stepper and the chi2 floor (d1-stage2-report.md, Fix round 1). Frozen geometry, 1 T, noiseless hits, no payload. Each start below
// goes through the same KalmanRefit::fit. Links no generator code.
//
//   cai_refit_start_probe
//
// What each cause predicts, and what an independent numpy filter gave before this ran: an extended Kalman filter and smoother on the
// closed-form helix, with this file's start, prior and tracks, no ACTS and no stepper. Largest over the seven tracks:
//
//   Start                     chi2         |q/p error|, per GeV   |left-out r|, mm
//   chord (the old start)     4.01322e-01  1.05027e-03            1.41151e-03
//   truth                     4.0e-20      3.2e-13                4.3e-13
//   chord, then a second pass 7.62059e-07  1.22276e-08            2.57650e-08
//   curve (the new start)     1.04718e-05  9.03694e-09            1.01228e-07
//
// - If the start is the cause, ACTS reproduces the chord row and collapses on the other three.
// - If one pass were wrong whatever the start, the truth row would keep the error: it does not, in numpy.
// - If the stepper were the cause, the truth row would keep it in ACTS, and numpy, which has no stepper, could not reproduce the chord
//   row. On job 7490742's tracks it already does, to 0.2 %: chi2 0.072442, r 3.061e-4, undone q/p 3.0855e-4.
// - Floor: the fit's chi2 holds the prior term (true - start)^T P^-1 (true - start), 0.0625 of the job's 0.0724, which the floor of
//   cai_payload_probe.cpp did not count. It vanishes with the start's error, so that floor is not changed.
//
// Limits, fixed here before any run. reproduction_share 5 %: the hits are ACTS crossings, up to 6.09e-6 mm from the helix (job 7489042),
// under 1 % of the smallest number compared. stepper_mm 1e-4 is the limit of the helix budget in acts_tracking_driver.cpp, the most a
// correct stepper may leave. chi2 limit: 16 measurements at that distance. q/p: the 1e-5 per GeV of cai_payload_probe.cpp.
#include <Acts/Definitions/Algebra.hpp>
#include <Acts/Definitions/Units.hpp>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <exception>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "kalman_refit.hpp"
#include "plane_propagation.hpp"
#include "t07_data_file.hpp"
#include "t07_fixture_constants.hpp"
#include "telescope_geometry.hpp"

namespace {

constexpr double reproduction_share = 0.05;
constexpr double stepper_mm = 1e-4;
constexpr double chi2_limit = 16.0 * (stepper_mm / t07::hit_sigma_mm) * (stepper_mm / t07::hit_sigma_mm);
constexpr double q_over_p_limit_per_gev = 1e-5;
constexpr int left_out_plane = 4;
constexpr double track_start_x_mm = -100.0;

struct ProbeTrack {
  double start_u_mm, start_v_mm, slope_u, slope_v, momentum_gev;
  int charge;
};

// cai_payload_probe.cpp's five, and the two hardest of the fixture: lowest momentum, largest slopes.
constexpr ProbeTrack probe_tracks[] = {{0.02, 12.0, 0.13, -0.05, 3.0, 1},  {-0.03, -20.0, -0.14, 0.13, 3.0, -1}, {0.0, 25.0, 0.14, 0.13, 6.0, 1},
                                       {0.01, -8.0, 0.05, -0.14, 6.0, -1}, {0.04, 3.0, -0.12, 0.09, 12.0, 1},    {0.0, 30.0, 0.15, 0.15, 1.5, 1},
                                       {0.0, -30.0, -0.15, 0.15, 1.5, -1}};

struct Reading {
  double chi2 = 0.0, q_over_p_error = 0.0, left_out_residual = 0.0;
};

int failed_lines = 0;

void verdict(const std::string& label, bool passed, const std::string& detail) {
  std::cout << (passed ? "PASS " : "FAIL ") << label << ": " << detail << std::endl;
  failed_lines += passed ? 0 : 1;
}

double q_over_p_of(const ProbeTrack& track) { return double(track.charge) / track.momentum_gev; }

// The closed form of check_t07_generator.py's helix_crossings, from a point and angles to the plane x, for a track in this file's field.
t07::RefitStart helix_at(double from_x_mm, double from_y_mm, double from_z_mm, double phi, double theta, double q_over_p, double to_x_mm) {
  const double bending_per_mm = q_over_p * t07::field_tesla * Acts::UnitConstants::T;
  const double transverse = std::sin(theta);
  const double end_phi = std::asin(std::sin(phi) - bending_per_mm * (to_x_mm - from_x_mm) / transverse);
  const double path_mm = (phi - end_phi) / bending_per_mm;
  t07::RefitStart start;
  start.position_mm = Acts::Vector3(to_x_mm, from_y_mm + transverse / bending_per_mm * (std::cos(end_phi) - std::cos(phi)), from_z_mm + path_mm * std::cos(theta));
  start.direction = Acts::Vector3(std::cos(end_phi) * transverse, std::sin(end_phi) * transverse, std::cos(theta));
  return start;
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

t07::RefitResult checked(t07::RefitResult result) {
  if (result.track.status != "fitted") {
    throw std::runtime_error("a refit failed, category " + result.track.failure_category);
  }
  return result;
}

// The old start of KalmanRefit::fit: the straight line through the set's first and last hit.
t07::RefitStart chord_start(const t07::HitSet& hit_set, const t07::DataEvent& event) {
  const t07::PlaneHit& first_hit = event.hits.at(hit_set.hit_keys.front());
  const t07::PlaneHit& last_hit = event.hits.at(hit_set.hit_keys.back());
  const double first_z = (first_hit.plane - 1) * t07::plane_spacing_mm;
  const double last_z = (last_hit.plane - 1) * t07::plane_spacing_mm;
  const double slope_u = (last_hit.loc0_mm - first_hit.loc0_mm) / (last_z - first_z);
  const double slope_v = (last_hit.loc1_mm - first_hit.loc1_mm) / (last_z - first_z);
  t07::RefitStart start;
  start.position_mm = Acts::Vector3(t07::refit_start_x_mm, first_hit.loc0_mm + slope_u * (t07::refit_start_x_mm - first_z), first_hit.loc1_mm + slope_v * (t07::refit_start_x_mm - first_z));
  start.direction = Acts::Vector3(1.0, slope_u, slope_v).normalized();
  return start;
}

t07::RefitStart truth_start(const ProbeTrack& track) {
  const Acts::Vector3 direction = Acts::Vector3(1.0, track.slope_u, track.slope_v).normalized();
  return helix_at(track_start_x_mm, track.start_u_mm, track.start_v_mm, std::atan2(direction.y(), direction.x()), std::acos(direction.z()), q_over_p_of(track), t07::refit_start_x_mm);
}

// A second pass: the first pass's smoothed state at plane 1, carried back to the start.
t07::RefitStart second_pass_start(const t07::KalmanRefit& fitter, const t07::HitSet& hit_set, const t07::DataEvent& event) {
  const t07::RefitResult first_pass = checked(fitter.fit(hit_set, event, chord_start(hit_set, event)));
  const t07::ParameterRecord& state = smoothed_at(first_pass, 1);
  return helix_at(0.0, state.parameters[0], state.parameters[1], state.parameters[2], state.parameters[3], state.parameters[4], t07::refit_start_x_mm);
}

using StartRule = std::function<t07::RefitStart(const ProbeTrack&, const t07::HitSet&, const t07::DataEvent&)>;

t07::HitSet hit_set_of(const ProbeTrack& track, const t07::DataEvent& event, int without_plane) {
  t07::HitSet hit_set;
  hit_set.track_key = "start-probe";
  hit_set.assumed_q_over_p = q_over_p_of(track);
  for (const t07::PlaneHit& hit : event.hits) {
    if (int(hit.plane) != without_plane) {
      hit_set.hit_keys.push_back(hit.hit_key);
    }
  }
  return hit_set;
}

Reading read_track(const t07::KalmanRefit& fitter, const ProbeTrack& track, const t07::DataEvent& event, const StartRule& rule) {
  const t07::HitSet all_hits = hit_set_of(track, event, 0);
  const t07::RefitResult whole = checked(fitter.fit(all_hits, event, rule(track, all_hits, event)));
  const t07::HitSet without_one = hit_set_of(track, event, left_out_plane);
  const t07::RefitResult left_out = checked(fitter.fit(without_one, event, rule(track, without_one, event)));
  const t07::PlaneHit& hit = event.hits.at(left_out_plane - 1);
  const t07::ParameterRecord& state = smoothed_at(left_out, left_out_plane);
  Reading reading;
  reading.chi2 = whole.track.chi2;
  reading.q_over_p_error = smoothed_at(whole, 1).parameters[4] - q_over_p_of(track);
  reading.left_out_residual = std::max(std::abs(hit.loc0_mm - state.parameters[0]), std::abs(hit.loc1_mm - state.parameters[1]));
  return reading;
}

Reading read_all(const std::string& name, const t07::KalmanRefit& fitter, const std::vector<t07::DataEvent>& events, const StartRule& rule) {
  Reading largest;
  std::size_t index = 0;
  for (const ProbeTrack& track : probe_tracks) {
    const Reading reading = read_track(fitter, track, events.at(index++), rule);
    std::cout << "TABLE " << name << " p " << track.momentum_gev * track.charge << " chi2 " << reading.chi2 << " q/p error " << reading.q_over_p_error << " left-out r " << reading.left_out_residual << std::endl;
    largest.chi2 = std::max(largest.chi2, reading.chi2);
    largest.q_over_p_error = std::max(largest.q_over_p_error, std::abs(reading.q_over_p_error));
    largest.left_out_residual = std::max(largest.left_out_residual, reading.left_out_residual);
  }
  return largest;
}

std::string text_of(const Reading& reading) {
  return "chi2 " + std::to_string(reading.chi2) + ", q/p " + std::to_string(reading.q_over_p_error) + " per GeV, r " + std::to_string(reading.left_out_residual) + " mm";
}

bool near_share(double measured, double expected) { return std::abs(measured - expected) < reproduction_share * expected; }

void run() {
  const t07::TelescopeGeometry telescope = t07::build_telescope_geometry();
  const t07::PlanePropagation propagation(telescope, t07::field_tesla);
  const t07::KalmanRefit fitter(telescope, t07::field_tesla, t07::hit_sigma_mm, t07::hit_sigma_mm);
  std::vector<t07::DataEvent> events;
  for (const ProbeTrack& track : probe_tracks) {
    t07::DataEvent event;
    const Acts::Vector3 start(track_start_x_mm, track.start_u_mm, track.start_v_mm);  // ACTS frame: x = fixture z, y = u, z = v
    for (const t07::PlaneCrossing& crossing : propagation.crossings(start, Acts::Vector3(1.0, track.slope_u, track.slope_v).normalized(), q_over_p_of(track))) {
      event.hits.push_back({std::uint32_t(event.hits.size()), std::uint32_t(crossing.plane), crossing.loc0_mm, crossing.loc1_mm});
    }
    if (int(event.hits.size()) != t07::plane_count) {
      throw std::runtime_error("a probe track missed a plane");
    }
    events.push_back(event);
  }

  const auto within_limits = [](const Reading& reading) {
    return reading.chi2 < chi2_limit && reading.q_over_p_error < q_over_p_limit_per_gev && reading.left_out_residual < stepper_mm;
  };

  const Reading chord = read_all("chord", fitter, events, [](const ProbeTrack&, const t07::HitSet& hit_set, const t07::DataEvent& event) { return chord_start(hit_set, event); });
  verdict("the chord start reproduces the independent filter, so the refit is a plain Kalman pass from that start",
          near_share(chord.chi2, 4.01322e-01) && near_share(chord.q_over_p_error, 1.05027e-03) && near_share(chord.left_out_residual, 1.41151e-03), text_of(chord));
  verdict("control: the chord start is outside the limits the other starts must meet", !within_limits(chord), "limits chi2 " + std::to_string(chi2_limit) + ", q/p 1e-05, r 1e-04");

  const Reading truth = read_all("truth", fitter, events, [](const ProbeTrack& track, const t07::HitSet&, const t07::DataEvent&) { return truth_start(track); });
  verdict("from truth the error is gone: one pass and the stepper are not its cause", within_limits(truth), text_of(truth));

  const Reading second_pass = read_all("second-pass", fitter, events, [&fitter](const ProbeTrack&, const t07::HitSet& hit_set, const t07::DataEvent& event) { return second_pass_start(fitter, hit_set, event); });
  verdict("a second pass from the first pass's state converges: the error is linearisation about the start", within_limits(second_pass), text_of(second_pass));

  const Reading curve = read_all("curve", fitter, events, [&fitter](const ProbeTrack&, const t07::HitSet& hit_set, const t07::DataEvent& event) { return fitter.start_of(hit_set, event); });
  verdict("the curve start needs one pass, from hits and the assumed q/p alone", within_limits(curve), text_of(curve));

  const t07::KalmanRefit no_field_fitter(telescope, 0.0, t07::hit_sigma_mm, t07::hit_sigma_mm);
  bool same_at_no_field = true;
  std::size_t index = 0;
  for (const ProbeTrack& track : probe_tracks) {
    const t07::DataEvent& event = events.at(index++);
    const t07::HitSet hit_set = hit_set_of(track, event, 0);
    const t07::RefitStart curved = no_field_fitter.start_of(hit_set, event);
    const t07::RefitStart straight = chord_start(hit_set, event);
    same_at_no_field = same_at_no_field && curved.position_mm == straight.position_mm && curved.direction == straight.direction;
  }
  verdict("at zero field the curve is the chord, bit for bit", same_at_no_field, "all tracks");
}

}  // namespace

int main(int argc, char** /*argv*/) {
  if (argc != 1) {
    std::cerr << "invalid input: this program takes no argument\n";
    return 2;
  }
  std::cout.precision(6);
  try {
    run();
  } catch (const std::exception& error) {
    std::cout << "STOPPED: " << error.what() << ", so no line of this run is read as a result" << std::endl;
    return 3;
  }
  std::cout << "RESULT " << (failed_lines == 0 ? "PASS" : "FAIL") << " (" << failed_lines << " failed lines)" << std::endl;
  return failed_lines == 0 ? 0 : 1;
}
