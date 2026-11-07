// Whether a seed's start lies on the helix through its hits (D1 stage 5 report, Fix round 2). Hand-set tracks with no noise, no fixture event: the telescope's
// crossings by the ACTS propagator, a start from three of them, and the start's own crossings by the same propagator, read at the seed's planes. The prior
// says 0.03 mm there, so a start that misses by more than seed_miss_limit_mm is off. Fixed before the first run: a quarter of the 0.020 mm hit sigma, a sixth of the
// prior's width; the propagator's own 1e-4 mm is far under it. KalmanRefit::start_of, job 7494285's start, is read beside it, as the control that this
// search sees the fault: 0.5 mm by arithmetic at 1.5 GeV for 6-7-8.
#include <Acts/Definitions/Algebra.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <string>
#include <vector>

#include "kalman_refit.hpp"
#include "plane_propagation.hpp"
#include "t07_fixture_constants.hpp"
#include "telescope_geometry.hpp"
#include "track_finding.hpp"

namespace {

constexpr double seed_miss_limit_mm = 0.005;
constexpr double control_miss_floor_mm = 0.1;

struct ProbeTrack {
  double momentum_gev;
  double charge;
  double slope_u;
  double slope_v;
};

double largest_miss_mm(const std::vector<t07::PlaneCrossing>& from_start, const std::vector<t07::PlaneCrossing>& truth, const t07::SeedPlanes& planes) {
  double largest = 0.0;
  for (const int plane : {planes.first, planes.middle, planes.last}) {
    largest = std::max({largest, std::abs(from_start.at(plane - 1).loc0_mm - truth.at(plane - 1).loc0_mm), std::abs(from_start.at(plane - 1).loc1_mm - truth.at(plane - 1).loc1_mm)});
  }
  return largest;
}

}  // namespace

int main() {
  const t07::TelescopeGeometry telescope = t07::build_telescope_geometry();
  const t07::PlanePropagation propagation(telescope, t07::field_tesla);
  const t07::KalmanRefit refit(telescope, t07::field_tesla, t07::hit_sigma_mm, t07::hit_sigma_mm);
  const std::vector<ProbeTrack> tracks{{1.5, 1.0, 0.15, 0.15}, {1.5, 1.0, -0.15, 0.15}, {1.5, -1.0, 0.15, -0.15}, {1.5, -1.0, -0.15, -0.15}, {1.5, 1.0, 0.0, 0.0},
                                       {3.0, 1.0, -0.15, 0.15}, {6.0, -1.0, 0.15, 0.1},   {12.0, 1.0, 0.1, -0.15},  {24.0, -1.0, -0.15, 0.05}};
  int failed = 0;
  double worst_control_mm = 0.0;
  for (const ProbeTrack& track : tracks) {
    const double q_over_p = track.charge / track.momentum_gev;
    const Acts::Vector3 vertex_mm(-100.0, 0.0, 0.0);
    const Acts::Vector3 direction = Acts::Vector3(1.0, track.slope_u, track.slope_v).normalized();
    const std::vector<t07::PlaneCrossing> truth = propagation.crossings(vertex_mm, direction, q_over_p);
    if (int(truth.size()) != t07::plane_count) {
      std::cout << "FAIL a probe track left the telescope\n";
      return 1;
    }
    t07::DataEvent event;
    for (const t07::PlaneCrossing& crossing : truth) {
      event.hits.push_back({std::uint32_t(event.hits.size()), std::uint32_t(crossing.plane), crossing.loc0_mm, crossing.loc1_mm});
    }
    for (const t07::SeedPlanes& planes : t07::seed_plane_triples) {
      std::array<Acts::Vector3, 3> points;
      const std::array<int, 3> chosen{planes.first, planes.middle, planes.last};
      for (int index = 0; index < 3; ++index) {
        const t07::PlaneCrossing& crossing = truth.at(chosen[index] - 1);
        points[index] = Acts::Vector3((chosen[index] - 1) * t07::plane_spacing_mm, crossing.loc0_mm, crossing.loc1_mm);
      }
      const auto start = t07::seed_start_of(points, t07::hit_sigma_mm, t07::hit_sigma_mm, t07::field_tesla);
      if (!start) {
        std::cout << "FAIL no seed start at p " << track.momentum_gev << "\n";
        ++failed;
        continue;
      }
      const double miss_mm = largest_miss_mm(propagation.crossings(start->position_mm, start->direction, start->q_over_p), truth, planes);
      t07::HitSet seed_hits;
      seed_hits.track_key = "control";
      seed_hits.assumed_q_over_p = q_over_p;
      seed_hits.hit_keys = {std::uint32_t(planes.first - 1), std::uint32_t(planes.middle - 1), std::uint32_t(planes.last - 1)};
      const t07::RefitStart parabola = refit.start_of(seed_hits, event);
      const double control_mm = largest_miss_mm(propagation.crossings(parabola.position_mm, parabola.direction, q_over_p), truth, planes);
      worst_control_mm = std::max(worst_control_mm, control_mm);
      const bool passed = miss_mm <= seed_miss_limit_mm;
      failed += passed ? 0 : 1;
      std::cout << (passed ? "PASS" : "FAIL") << " seed " << planes.first << "-" << planes.middle << "-" << planes.last << " p " << track.momentum_gev << " q " << track.charge << " slopes "
                << track.slope_u << " " << track.slope_v << ": helix start misses by " << miss_mm << " mm, parabola by " << control_mm << " mm\n";
    }
  }
  const bool control_seen = worst_control_mm > control_miss_floor_mm;
  std::cout << (control_seen ? "PASS" : "FAIL") << " the search sees the parabola's fault: worst " << worst_control_mm << " mm\n";
  failed += control_seen ? 0 : 1;
  std::cout << (failed == 0 ? "RESULT PASS" : "RESULT FAIL") << "\n";
  return failed == 0 ? 0 : 1;
}
