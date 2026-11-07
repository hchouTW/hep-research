// Whether a seed's start lies on the helix through its hits (D1 stage 5 report, Fix round 2). Hand-set tracks with no noise, no fixture event: the telescope's
// crossings by the ACTS propagator, a start from three of them, and the start's own crossings by the same propagator, read at the seed's planes. The prior
// says 0.03 mm there, so a start that misses by more than seed_miss_limit_mm is off. Fixed before the first run: a quarter of the 0.020 mm hit sigma, a sixth of the
// prior's width; the propagator's own 1e-4 mm is far under it. KalmanRefit::start_of, job 7494285's start, is read beside it, as the control that this
// search sees the fault: 0.5 mm by arithmetic at 1.5 GeV for 6-7-8.
//
// It also reads the shipped covariance (stage 5 review, m6): the sigma at each plane by two roads, each eigenvector of the start's covariance carried by the propagator,
// and each hit coordinate moved by one sigma and the start rebuilt. They must agree within seed_sigma_agreement, fixed before the first run. Beside them, printed and not
// judged: Lagrange's sigma along u, and along v the chord through the first and last hit (job 7494285's prior) and the line through the first hit with the last two's slope.
#include <Acts/Definitions/Algebra.hpp>
#include <Acts/Definitions/TrackParametrization.hpp>
#include <Acts/Utilities/UnitVectors.hpp>

#include <Eigen/Eigenvalues>

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
constexpr double seed_sigma_agreement = 0.02;  // relative: both roads are linear in a step of one sigma, so this is far above their difference if the covariance is right

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

struct PlaneSigmas {
  std::vector<double> along_u;
  std::vector<double> along_v;
};

void add_move(PlaneSigmas& sums, const std::vector<t07::PlaneCrossing>& moved, const std::vector<t07::PlaneCrossing>& centre) {
  for (std::size_t plane = 0; plane < centre.size(); ++plane) {
    const double move_u = moved.at(plane).loc0_mm - centre.at(plane).loc0_mm;
    const double move_v = moved.at(plane).loc1_mm - centre.at(plane).loc1_mm;
    sums.along_u[plane] += move_u * move_u;
    sums.along_v[plane] += move_v * move_v;
  }
}

// Carried from start->covariance, which holds the inflation already.
PlaneSigmas sigmas_of_covariance(const t07::PlanePropagation& propagation, const t07::SeedStart& start, const std::vector<t07::PlaneCrossing>& centre) {
  PlaneSigmas sums{std::vector<double>(centre.size(), 0.0), std::vector<double>(centre.size(), 0.0)};
  const Eigen::Matrix<double, 5, 5> covariance = start.covariance.topLeftCorner<5, 5>();
  const Eigen::SelfAdjointEigenSolver<Eigen::Matrix<double, 5, 5>> solver(covariance);
  const auto axes = Acts::createCurvilinearUnitVectors(start.direction);
  const double phi = std::atan2(start.direction.y(), start.direction.x());
  const double theta = std::acos(start.direction.z());
  for (int index = 0; index < 5; ++index) {
    const double eigenvalue = solver.eigenvalues()[index];
    if (eigenvalue <= 0.0) {
      continue;
    }
    const Eigen::Matrix<double, 5, 1> step = std::sqrt(eigenvalue) * solver.eigenvectors().col(index);
    const Acts::Vector3 position = start.position_mm + step[Acts::eBoundLoc0] * axes.first + step[Acts::eBoundLoc1] * axes.second;
    const Acts::Vector3 direction = Acts::makeDirectionFromPhiTheta(phi + step[Acts::eBoundPhi], theta + step[Acts::eBoundTheta]);
    add_move(sums, propagation.crossings(position, direction, start.q_over_p + step[Acts::eBoundQOverP]), centre);
  }
  return sums;
}

// Each hit coordinate moved by one inflated sigma, and the start rebuilt.
PlaneSigmas sigmas_of_hits(const t07::PlanePropagation& propagation, const std::array<Acts::Vector3, 3>& points, const std::vector<t07::PlaneCrossing>& centre) {
  PlaneSigmas sums{std::vector<double>(centre.size(), 0.0), std::vector<double>(centre.size(), 0.0)};
  const double sigma_mm = t07::seed_prior_inflation * t07::hit_sigma_mm;
  for (int hit = 0; hit < 3; ++hit) {
    for (int coordinate = 1; coordinate < 3; ++coordinate) {
      std::array<Acts::Vector3, 3> moved_points = points;
      moved_points[hit][coordinate] += sigma_mm;
      const auto moved = t07::seed_start_of(moved_points, t07::hit_sigma_mm, t07::hit_sigma_mm, t07::field_tesla);
      if (moved) {
        add_move(sums, propagation.crossings(moved->position_mm, moved->direction, moved->q_over_p), centre);
      }
    }
  }
  return sums;
}

// The weights of three hits on a parabola at x, and the same for the two straight lines along v.
double norm_of(double first, double second, double third) { return std::sqrt(first * first + second * second + third * third); }

double lagrange_norm(const std::array<double, 3>& x, double at) {
  return norm_of((at - x[1]) * (at - x[2]) / ((x[0] - x[1]) * (x[0] - x[2])), (at - x[0]) * (at - x[2]) / ((x[1] - x[0]) * (x[1] - x[2])), (at - x[0]) * (at - x[1]) / ((x[2] - x[0]) * (x[2] - x[1])));
}

double chord_norm(const std::array<double, 3>& x, double at) {
  const double share = (at - x[0]) / (x[2] - x[0]);
  return norm_of(1.0 - share, 0.0, share);
}

double last_two_norm(const std::array<double, 3>& x, double at) {
  const double share = (at - x[0]) / (x[2] - x[1]);
  return norm_of(1.0, share, share);
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
      const std::vector<t07::PlaneCrossing> centre = propagation.crossings(start->position_mm, start->direction, start->q_over_p);
      const double miss_mm = largest_miss_mm(centre, truth, planes);
      const PlaneSigmas of_covariance = sigmas_of_covariance(propagation, *start, centre);
      const PlaneSigmas of_hits = sigmas_of_hits(propagation, points, centre);
      const std::array<double, 3> seed_x{points[0].x(), points[1].x(), points[2].x()};
      const double inflated_mm = t07::seed_prior_inflation * t07::hit_sigma_mm;
      for (std::size_t plane = 0; plane < centre.size(); ++plane) {
        const double sigma_u = std::sqrt(of_covariance.along_u[plane]);
        const double sigma_v = std::sqrt(of_covariance.along_v[plane]);
        const double hits_u = std::sqrt(of_hits.along_u[plane]);
        const double hits_v = std::sqrt(of_hits.along_v[plane]);
        const bool agreed = std::abs(sigma_u - hits_u) <= seed_sigma_agreement * hits_u && std::abs(sigma_v - hits_v) <= seed_sigma_agreement * hits_v;
        failed += agreed ? 0 : 1;
        const double plane_x = double(plane) * t07::plane_spacing_mm;
        std::cout << (agreed ? "WINDOW" : "FAIL window") << " seed " << planes.first << "-" << planes.middle << "-" << planes.last << " p " << track.momentum_gev << " q " << track.charge << " slopes " << track.slope_u
                  << " " << track.slope_v << " plane " << plane + 1 << ": covariance u " << sigma_u << " v " << sigma_v << ", hits u " << hits_u << " v " << hits_v << ", Lagrange u "
                  << inflated_mm * lagrange_norm(seed_x, plane_x) << ", chord v " << inflated_mm * chord_norm(seed_x, plane_x) << ", last-two v " << inflated_mm * last_two_norm(seed_x, plane_x) << "\n";
      }
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
