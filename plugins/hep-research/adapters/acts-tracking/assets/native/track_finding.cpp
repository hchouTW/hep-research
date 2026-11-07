#include "track_finding.hpp"

#include <Acts/AmbiguityResolution/GreedyAmbiguityResolution.hpp>
#include <Acts/Definitions/TrackParametrization.hpp>
#include <Acts/Definitions/Units.hpp>
#include <Acts/EventData/BoundTrackParameters.hpp>
#include <Acts/EventData/ParticleHypothesis.hpp>
#include <Acts/EventData/SourceLink.hpp>
#include <Acts/EventData/TrackContainer.hpp>
#include <Acts/EventData/VectorMultiTrajectory.hpp>
#include <Acts/EventData/VectorTrackContainer.hpp>
#include <Acts/MagneticField/ConstantBField.hpp>
#include <Acts/Propagator/EigenStepper.hpp>
#include <Acts/Propagator/Navigator.hpp>
#include <Acts/Propagator/Propagator.hpp>
#include <Acts/Seeding/EstimateTrackParamsFromSeed.hpp>
#include <Acts/TrackFinding/CombinatorialKalmanFilter.hpp>
#include <Acts/TrackFinding/CombinatorialKalmanFilterError.hpp>
#include <Acts/TrackFinding/MeasurementSelector.hpp>
#include <Acts/TrackFinding/TrackStateCreator.hpp>
#include <Acts/TrackFitting/GainMatrixUpdater.hpp>
#include <Acts/Utilities/Logger.hpp>
#include <Acts/Utilities/UnitVectors.hpp>

#include <algorithm>
#include <cmath>
#include <functional>
#include <iostream>
#include <sstream>
#include <stdexcept>

#include "plane_hit_link.hpp"
#include "t07_fixture_constants.hpp"

namespace t07 {
namespace {

using Trajectory = Acts::VectorMultiTrajectory;
using FindingContainer = decltype(Acts::TrackContainer{Acts::VectorTrackContainer{}, Trajectory{}});
using TrackProxy = FindingContainer::TrackProxy;
using TrackStateProxy = FindingContainer::TrackStateProxy;
using TelescopePropagator = Acts::Propagator<Acts::EigenStepper<>, Acts::Navigator>;
using TelescopeFinder = Acts::CombinatorialKalmanFilter<TelescopePropagator, FindingContainer>;
using LinkIterator = std::vector<Acts::SourceLink>::const_iterator;
using StateCreator = Acts::TrackStateCreator<LinkIterator, FindingContainer>;
using BranchResult = Acts::CombinatorialKalmanFilterBranchStopperResult;
using NewStates = Acts::Result<Acts::CkfTypes::BranchVector<Acts::TrackIndexType>>;

// Diagnostic build only, temporary: acts_finder_no_phi_term of CMakeLists.txt defines this, so that job measures the phi term's own effect (D1 stage 5e brief).
// The recipe's acts_tracking_finder does not (the build job checks its flags, and its record says diagnostic_build none). Nothing at run time reaches it. It comes
// out at the next stage.
#if defined(T07_DIAGNOSTIC_NO_PHI_TERM)
constexpr char diagnostic_build[] = "no-phi-term";
constexpr char seed_covariance_phi_term[] = "absent";
#else
constexpr char diagnostic_build[] = "none";
constexpr char seed_covariance_phi_term[] = "present";
#endif
// The seed's code is not a number, so the record names it: the configuration hash then tells this recipe from job 7496491's, which took the last two's slope and
// had no phi term (D1 stage 5e review, m5). helix_at_start takes the chord unconditionally.
constexpr char seed_slope_along_v[] = "chord";

double plane_x_mm(int plane) { return (plane - 1) * plane_spacing_mm; }

// Largest second derivatives along the telescope of a track of section 4.1, in mm^-1: u'' = -w n (1 + u'^2) and v'' = -w n u' v', as in
// KalmanRefit::start_of, with w = k B / p at the lowest momentum.
struct CurvatureBounds {
  double along_u = 0.0;
  double along_v = 0.0;
};

CurvatureBounds curvature_bounds(double field_along_v_tesla) {
  const double turning_per_mm = field_along_v_tesla * Acts::UnitConstants::T / seed_lowest_momentum_gev;
  const double slope_norm = std::sqrt(1.0 + seed_largest_slope_u * seed_largest_slope_u + seed_largest_slope_v * seed_largest_slope_v);
  return {turning_per_mm * slope_norm * (1.0 + seed_largest_slope_u * seed_largest_slope_u), turning_per_mm * slope_norm * seed_largest_slope_u * seed_largest_slope_v};
}

// A plane's hits by rising loc0, for a window by binary search: the data file's order is not relied on.
std::array<std::vector<const PlaneHit*>, plane_count> hits_by_plane(const DataEvent& event) {
  std::array<std::vector<const PlaneHit*>, plane_count> planes;
  for (std::size_t position = 0; position < event.hits.size(); ++position) {
    const PlaneHit& hit = event.hits[position];
    if (hit.plane < 1 || hit.plane > std::uint32_t(plane_count) || hit.hit_key != position) {
      throw std::invalid_argument("refused: hit " + std::to_string(position) + " has plane " + std::to_string(hit.plane) + " and key " + std::to_string(hit.hit_key));
    }
    planes[hit.plane - 1].push_back(&hit);
  }
  for (auto& plane : planes) {
    std::sort(plane.begin(), plane.end(), [](const PlaneHit* first, const PlaneHit* second) { return first->loc0_mm < second->loc0_mm; });
  }
  return planes;
}

std::vector<const PlaneHit*>::const_iterator first_at_or_above(const std::vector<const PlaneHit*>& plane, double loc0_mm) {
  return std::lower_bound(plane.begin(), plane.end(), loc0_mm, [](const PlaneHit* hit, double value) { return hit->loc0_mm < value; });
}

// The hits of one event as source links, by plane and rising loc0. Rebuilt per event, read by the state creator.
struct EventLinks {
  std::array<std::vector<Acts::SourceLink>, plane_count> links;
  std::array<std::vector<double>, plane_count> loc0_mm;
};

EventLinks links_of(const std::array<std::vector<const PlaneHit*>, plane_count>& planes, const TelescopeGeometry& telescope, double sigma_loc0_mm, double sigma_loc1_mm) {
  EventLinks event_links;
  for (int index = 0; index < plane_count; ++index) {
    for (const PlaneHit* hit : planes[index]) {
      PlaneHitLink link;
      link.hit_key = hit->hit_key;
      link.surface = telescope.planes.at(index).get();
      link.loc0_mm = hit->loc0_mm;
      link.loc1_mm = hit->loc1_mm;
      link.variance0_mm2 = sigma_loc0_mm * sigma_loc0_mm;
      link.variance1_mm2 = sigma_loc1_mm * sigma_loc1_mm;
      event_links.links[index].emplace_back(std::move(link));
      event_links.loc0_mm[index].push_back(hit->loc0_mm);
    }
  }
  return event_links;
}

// What one seed's search has spent. The delegates below are const, as ACTS binds them, so they reach this through a pointer.
struct SeedBudget {
  std::size_t extra_branches = 0;
  bool truncated = false;
};

// ACTS's selector, and the two limits it does not report. MeasurementSelector cuts at numMeasurementsCutOff with no word, so the count is taken
// here from the chi2 it has just stored; the per-seed budget then keeps the best of what is left.
struct BudgetedSelector {
  using Candidates = std::vector<TrackStateProxy>;
  using Range = std::pair<Candidates::iterator, Candidates::iterator>;

  Acts::MeasurementSelector selector;
  SeedBudget* budget = nullptr;

  Acts::Result<Range> select(Candidates& candidates, bool& is_outlier, const Acts::Logger& logger) const {
    Acts::Result<Range> chosen = selector.select<Trajectory>(candidates, is_outlier, logger);
    if (!chosen.ok()) {
      return chosen;
    }
    auto [first, last] = *chosen;
    std::size_t kept = std::size_t(last - first);
    std::size_t passing = 0;
    for (auto& candidate : candidates) {
      passing += double(candidate.chi2()) < finding_chi2_cut ? 1 : 0;
    }
    if (passing > kept) {
      budget->truncated = true;
    }
    const std::size_t left = finding_most_branches_per_seed - std::min(budget->extra_branches, finding_most_branches_per_seed);
    if (kept > left + 1) {
      kept = left + 1;
      budget->truncated = true;
    }
    budget->extra_branches += kept > 0 ? kept - 1 : 0;
    return Acts::Result<Range>::success(Range{first, first + std::ptrdiff_t(kept)});
  }
};

// Hands the state creator only the hits of a surface that can pass the chi2 cut. For any hit, chi2 >= r0^2 / S00 with r0 the loc0 residual and
// S00 the residual variance, so a hit outside sqrt(cut S00) cannot pass: the window selects nothing the cut would keep, and it saves making a
// track state for each of a thousand noise hits per branch (TrackStateCreator.hpp warns of that size).
struct WindowedStates {
  const StateCreator* creator = nullptr;
  const TelescopeGeometry* telescope = nullptr;
  const EventLinks* event_links = nullptr;
  double loc0_variance_mm2 = 0.0;

  NewStates create(const Acts::GeometryContext& geometry_context, const Acts::CalibrationContext& calibration_context, const Acts::Surface& surface,
                   const Acts::CkfTypes::BoundState& bound_state, Acts::TrackIndexType previous_tip, std::vector<TrackStateProxy>& candidates, Trajectory& trajectory,
                   const Acts::Logger& logger) const {
    const int plane = telescope->plane_number_of(surface);
    if (plane == 0) {
      return NewStates::success({});
    }
    const auto& [parameters, jacobian, path_length] = bound_state;
    const double predicted_mm = parameters.parameters()[Acts::eBoundLoc0];
    const double predicted_variance_mm2 = (*parameters.covariance())(Acts::eBoundLoc0, Acts::eBoundLoc0);
    const double half_width_mm = std::sqrt(finding_chi2_cut * (predicted_variance_mm2 + loc0_variance_mm2));
    const std::vector<double>& loc0_mm = event_links->loc0_mm[plane - 1];
    const auto lowest = std::lower_bound(loc0_mm.begin(), loc0_mm.end(), predicted_mm - half_width_mm);
    const auto highest = std::upper_bound(loc0_mm.begin(), loc0_mm.end(), predicted_mm + half_width_mm);
    if (lowest == highest) {
      return NewStates::success({});
    }
    const std::vector<Acts::SourceLink>& links = event_links->links[plane - 1];
    const LinkIterator first = links.begin() + (lowest - loc0_mm.begin());
    const LinkIterator last = links.begin() + (highest - loc0_mm.begin());
    return creator->createSourceLinkTrackStates(geometry_context, calibration_context, surface, bound_state, first, last, previous_tip, candidates, trajectory, logger);
  }
};

// With no outliers (finding_chi2_cut bounds them too), a track with 3 holes of 8 planes holds at most 5 hits, under section 7's 6.
BranchResult stop_branch(const TrackProxy& track, const TrackStateProxy& /*state*/) {
  return track.nHoles() > finding_most_holes ? BranchResult::StopAndDrop : BranchResult::Continue;
}

Acts::MeasurementSelector budgeted_measurement_selector() {
  Acts::MeasurementSelectorCuts cuts;
  cuts.chi2CutOff = {finding_chi2_cut};
  cuts.numMeasurementsCutOff = {finding_most_branches_per_surface};
  cuts.chi2CutOffOutlier = {finding_chi2_cut};
  return Acts::MeasurementSelector(cuts);
}

bool on_one_candidate(const HitTriple& triple, const std::vector<std::vector<std::size_t>>& candidates_of_hit) {
  for (const std::size_t candidate : candidates_of_hit[triple.hit_keys[0]]) {
    const auto holds = [candidate](const std::vector<std::size_t>& held) { return std::find(held.begin(), held.end(), candidate) != held.end(); };
    if (holds(candidates_of_hit[triple.hit_keys[1]]) && holds(candidates_of_hit[triple.hit_keys[2]])) {
      return true;
    }
  }
  return false;
}

Acts::Vector3 global_of(const PlaneHit& hit) { return Acts::Vector3(plane_x_mm(int(hit.plane)), hit.loc0_mm, hit.loc1_mm); }

std::string planes_text(const SeedPlanes& planes) { return std::to_string(planes.first) + "-" + std::to_string(planes.middle) + "-" + std::to_string(planes.last); }

std::string number_text(double value) {
  std::ostringstream text;
  text.precision(17);
  text << value;
  return text.str();
}

}  // namespace

namespace {

struct HelixPoint {
  Acts::Vector3 position_mm;
  Acts::Vector3 direction;
  double q_over_p = 0.0;
};

// The helix through three points, at the start. ACTS gives it at the first point; the closed form of acts_tracking_driver.cpp's helix_crossing, which
// its self-test holds to the propagator within 1e-4 mm, carries it upstream: T_z constant, the azimuth falling at w = (q/p) k B per unit path.
std::optional<HelixPoint> helix_at_start(const std::array<Acts::Vector3, 3>& points, double field_along_v_tesla) {
  const Acts::Vector3 field_vector(0.0, 0.0, field_along_v_tesla * Acts::UnitConstants::T);
  const Acts::FreeVector estimate = Acts::estimateTrackParamsFromSeed(points[0], 0.0, points[1], points[2], field_vector);
  double q_over_p = estimate[Acts::eFreeQOverP];
  Acts::Vector3 tangent(estimate[Acts::eFreeDir0], estimate[Acts::eFreeDir1], estimate[Acts::eFreeDir2]);
  // ACTS's slope along the field is that of the last two hits alone (D1 stage 5d report). The recipe takes it from the first and last hit over their straight
  // transverse distance, on the same circle, so q/p scales with the transverse share of the tangent (track_finding.hpp states why, and the chord against the arc).
  const double transverse_before = std::hypot(tangent.x(), tangent.y());
  const double chord_slope = (points[2].z() - points[0].z()) / std::hypot(points[2].x() - points[0].x(), points[2].y() - points[0].y());
  tangent = Acts::Vector3(tangent.x() / transverse_before, tangent.y() / transverse_before, chord_slope).normalized();
  q_over_p *= std::hypot(tangent.x(), tangent.y()) / transverse_before;
  if (!std::isfinite(q_over_p) || q_over_p == 0.0 || !tangent.allFinite() || tangent.x() <= 0.0) {
    return std::nullopt;
  }
  const double turn_per_mm = q_over_p * field_along_v_tesla * Acts::UnitConstants::T;
  const double transverse = std::hypot(tangent.x(), tangent.y());
  const double phi_at_seed = std::atan2(tangent.y(), tangent.x());
  const double sine_at_start = std::sin(phi_at_seed) - turn_per_mm * (refit_start_x_mm - points[0].x()) / transverse;
  if (!(std::abs(sine_at_start) < 1.0)) {
    return std::nullopt;
  }
  const double phi_at_start = std::asin(sine_at_start);
  const double path_mm = (phi_at_seed - phi_at_start) / turn_per_mm;
  HelixPoint point;
  point.position_mm = Acts::Vector3(refit_start_x_mm, points[0].y() + transverse / turn_per_mm * (std::cos(phi_at_start) - std::cos(phi_at_seed)), points[0].z() + path_mm * tangent.z());
  point.direction = Acts::Vector3(transverse * std::cos(phi_at_start), transverse * std::sin(phi_at_start), tangent.z());
  point.q_over_p = q_over_p;
  return point;
}

// Numerical derivative only, a twentieth of a hit sigma: nothing of the result depends on it to first order. Not a cut or a limit.
constexpr double seed_derivative_step_sigma = 0.05;

}  // namespace

std::optional<SeedStart> seed_start_of(const std::array<Acts::Vector3, 3>& points, double sigma_loc0_mm, double sigma_loc1_mm, double field_along_v_tesla) {
  const std::optional<HelixPoint> centre = helix_at_start(points, field_along_v_tesla);
  if (!centre) {
    return std::nullopt;
  }
  // Curvilinear frame (Acts/Utilities/UnitVectors.hpp): the covariance is of bound parameters on the plane through the centre perpendicular to T. A start
  // moved by m inside the plane x = refit_start_x_mm meets that surface after a path -T.m. Its position there, projected on U and V, is m projected on U and V
  // to first order. Its direction is not the one at x = refit_start_x_mm: over that path the azimuth falls by w (-T.m), w = (q/p) k B as in helix_at_start,
  // so phi on the surface is phi at x = refit_start_x_mm plus w (T.m). Theta and q/p do not change along a helix in this field. Correction: until stage 5e
  // this comment said a move along T stays on the track, true of position only, and the phi term was missing; job 7496491's seed probe showed it (D1 stage 5d
  // report, section 5). The sign: a term of the other sign or none leaves the covariance and the hit roads 114 % and 53 % apart at worst, and this sign 0.9 %,
  // by the closed-form replica of D1 stage 5e (tests/adapters/test_acts_finding.py, SeedStartClosedForm).
  const auto curvilinear_axes = Acts::createCurvilinearUnitVectors(centre->direction);
  const Acts::Vector3 axis_u = curvilinear_axes.first;
  const Acts::Vector3 axis_v = curvilinear_axes.second;
  using StartVector = Eigen::Matrix<double, 5, 1>;
  const auto bound_of = [&](const HelixPoint& point) {
    const Acts::Vector3 moved_mm = point.position_mm - centre->position_mm;
    double phi = std::atan2(point.direction.y(), point.direction.x());
#ifndef T07_DIAGNOSTIC_NO_PHI_TERM
    phi += centre->q_over_p * field_along_v_tesla * Acts::UnitConstants::T * centre->direction.dot(moved_mm);
#endif
    StartVector bound;
    bound << axis_u.dot(moved_mm), axis_v.dot(moved_mm), phi, std::acos(point.direction.z() / point.direction.norm()), point.q_over_p;
    return bound;
  };
  // The start as a function of the six hit coordinates, differentiated: the covariance is of the function shipped, helix_at_start with its chord slope, along u
  // and v alike, since every column is a difference of that function; none is written apart.
  Eigen::Matrix<double, 5, 6> jacobian;
  for (int hit = 0; hit < 3; ++hit) {
    for (int coordinate = 0; coordinate < 2; ++coordinate) {
      const double sigma_mm = coordinate == 0 ? sigma_loc0_mm : sigma_loc1_mm;
      const double step_mm = seed_derivative_step_sigma * sigma_mm;
      std::array<Acts::Vector3, 3> above = points;
      std::array<Acts::Vector3, 3> below = points;
      above[hit][coordinate + 1] += step_mm;
      below[hit][coordinate + 1] -= step_mm;
      const std::optional<HelixPoint> higher = helix_at_start(above, field_along_v_tesla);
      const std::optional<HelixPoint> lower = helix_at_start(below, field_along_v_tesla);
      if (!higher || !lower) {
        return std::nullopt;
      }
      jacobian.col(2 * hit + coordinate) = (bound_of(*higher) - bound_of(*lower)) * (sigma_mm / (2.0 * step_mm));
    }
  }
  SeedStart start;
  start.position_mm = centre->position_mm;
  start.direction = centre->direction;
  start.q_over_p = centre->q_over_p;
  start.covariance.topLeftCorner<5, 5>() = seed_prior_inflation * seed_prior_inflation * jacobian * jacobian.transpose();
  start.covariance(Acts::eBoundTime, Acts::eBoundTime) = refit_prior_time_sigma * refit_prior_time_sigma;
  return start;
}

SeedSearch find_seeds(const DataEvent& event, double hit_sigma_mm, double field_along_v_tesla) {
  const auto planes = hits_by_plane(event);
  const CurvatureBounds curvature = curvature_bounds(field_along_v_tesla);
  SeedSearch search;
  for (const SeedPlanes& triple : seed_plane_triples) {
    const auto& first_hits = planes[triple.first - 1];
    const auto& middle_hits = planes[triple.middle - 1];
    const auto& last_hits = planes[triple.last - 1];
    const double to_middle_mm = plane_x_mm(triple.middle) - plane_x_mm(triple.first);
    const double from_middle_mm = plane_x_mm(triple.last) - plane_x_mm(triple.middle);
    const double lever_mm = to_middle_mm + from_middle_mm;
    const double share = to_middle_mm / lever_mm;
    const double noise_mm = seed_window_sigma * hit_sigma_mm * std::sqrt(1.0 + share * share + (1.0 - share) * (1.0 - share));
    const double window_u_mm = noise_mm + 0.5 * curvature.along_u * to_middle_mm * from_middle_mm;
    const double window_v_mm = noise_mm + 0.5 * curvature.along_v * to_middle_mm * from_middle_mm;
    for (const PlaneHit* first : first_hits) {
      const double reach_u_mm = seed_largest_slope_u * lever_mm;
      const double reach_v_mm = seed_largest_slope_v * lever_mm;
      for (auto last = first_at_or_above(last_hits, first->loc0_mm - reach_u_mm); last != last_hits.end() && (*last)->loc0_mm <= first->loc0_mm + reach_u_mm; ++last) {
        if (std::abs((*last)->loc1_mm - first->loc1_mm) > reach_v_mm) {
          continue;
        }
        const double line_u_mm = first->loc0_mm + share * ((*last)->loc0_mm - first->loc0_mm);
        const double line_v_mm = first->loc1_mm + share * ((*last)->loc1_mm - first->loc1_mm);
        for (auto middle = first_at_or_above(middle_hits, line_u_mm - window_u_mm); middle != middle_hits.end() && (*middle)->loc0_mm <= line_u_mm + window_u_mm; ++middle) {
          if (std::abs((*middle)->loc1_mm - line_v_mm) > window_v_mm) {
            continue;
          }
          if (search.triples.size() == finding_most_seeds_per_event) {
            search.reached_budget = true;
            return search;
          }
          search.triples.push_back({triple, {first->hit_key, (*middle)->hit_key, (*last)->hit_key}});
        }
      }
    }
  }
  return search;
}

std::vector<std::pair<std::string, std::string>> effective_configuration() {
  std::string triples;
  for (const SeedPlanes& triple : seed_plane_triples) {
    triples += (triples.empty() ? "" : ",") + planes_text(triple);
  }
  return {{"seed_plane_triples", triples},
          {"seed_lowest_momentum_gev", number_text(seed_lowest_momentum_gev)},
          {"seed_largest_slope_u", number_text(seed_largest_slope_u)},
          {"seed_largest_slope_v", number_text(seed_largest_slope_v)},
          {"seed_window_sigma", number_text(seed_window_sigma)},
          {"seed_prior_inflation", number_text(seed_prior_inflation)},
          {"finding_chi2_cut", number_text(finding_chi2_cut)},
          {"finding_least_measurements", std::to_string(finding_least_measurements)},
          {"finding_most_holes", std::to_string(finding_most_holes)},
          {"finding_most_branches_per_surface", std::to_string(finding_most_branches_per_surface)},
          {"finding_most_branches_per_seed", std::to_string(finding_most_branches_per_seed)},
          {"finding_most_seeds_per_event", std::to_string(finding_most_seeds_per_event)},
          {"finding_most_propagator_steps", std::to_string(finding_most_propagator_steps)},
          {"ambiguity_most_shared_hits", std::to_string(ambiguity_most_shared_hits)},
          {"ambiguity_most_iterations", std::to_string(ambiguity_most_iterations)},
          {"finding_fit_passes", std::to_string(finding_fit_passes)},
          {"seed_derivative_step_sigma", number_text(seed_derivative_step_sigma)},
          {"refit_start_x_mm", number_text(refit_start_x_mm)},
          {"refit_prior_loc_sigma_mm", number_text(refit_prior_loc_sigma_mm)},
          {"refit_prior_angle_sigma", number_text(refit_prior_angle_sigma)},
          {"refit_prior_qop_sigma_per_gev", number_text(refit_prior_qop_sigma_per_gev)},
          {"refit_prior_time_sigma", number_text(refit_prior_time_sigma)},
          {"diagnostic_build", diagnostic_build},
          {"seed_slope_along_v", seed_slope_along_v},
          {"seed_covariance_phi_term", seed_covariance_phi_term}};
}

struct TrackFinder::Machinery {
  TelescopeFinder finder;
  Acts::GainMatrixUpdater updater;
  Acts::GreedyAmbiguityResolution resolver;
};

namespace {

Acts::GreedyAmbiguityResolution::Config ambiguity_configuration() {
  Acts::GreedyAmbiguityResolution::Config configuration;
  configuration.maximumSharedHits = ambiguity_most_shared_hits;
  configuration.maximumIterations = ambiguity_most_iterations;
  configuration.nMeasurementsMin = finding_least_measurements;
  return configuration;
}

// GreedyAmbiguityResolution::computeInitialState, on the candidates kept here rather than on a track container: each seed's container is
// cleared before the next, so no container holds them all. The same fields, in the same way, and ACTS's resolve() decides.
Acts::GreedyAmbiguityResolution::State ambiguity_state_of(const std::vector<FoundCandidate>& candidates) {
  Acts::GreedyAmbiguityResolution::State state;
  for (const FoundCandidate& candidate : candidates) {
    const std::size_t track = state.numberOfTracks++;
    state.trackTips.push_back(int(track));
    state.trackChi2.push_back(float(candidate.search_chi2) / float(2 * candidate.measurements));
    state.measurementsPerTrack.emplace_back(candidate.hit_keys.begin(), candidate.hit_keys.end());
    state.selectedTracks.insert(track);
  }
  for (std::size_t track = 0; track < state.numberOfTracks; ++track) {
    for (const std::size_t measurement : state.measurementsPerTrack[track]) {
      state.tracksPerMeasurement[measurement].insert(track);
    }
  }
  state.sharedMeasurementsPerTrack.assign(state.numberOfTracks, 0);
  for (std::size_t track = 0; track < state.numberOfTracks; ++track) {
    for (const std::size_t measurement : state.measurementsPerTrack[track]) {
      if (state.tracksPerMeasurement[measurement].size() > 1) {
        ++state.sharedMeasurementsPerTrack[track];
      }
    }
  }
  return state;
}

}  // namespace

TrackFinder::TrackFinder(const TelescopeGeometry& telescope, double field_along_v_tesla, double sigma_loc0_mm, double sigma_loc1_mm)
    : m_telescope(telescope),
      m_field_along_v_tesla(field_along_v_tesla),
      m_sigma_loc0_mm(sigma_loc0_mm),
      m_sigma_loc1_mm(sigma_loc1_mm),
      m_fitter(telescope, field_along_v_tesla, sigma_loc0_mm, sigma_loc1_mm) {
  auto field = std::make_shared<Acts::ConstantBField>(Acts::Vector3(0.0, 0.0, field_along_v_tesla * Acts::UnitConstants::T));
  Acts::EigenStepper<> stepper(field);
  Acts::Navigator::Config navigator_config;
  navigator_config.trackingGeometry = telescope.tracking_geometry;
  Acts::Navigator navigator(navigator_config, Acts::getDefaultLogger("Navigator", Acts::Logging::ERROR, &std::cerr));
  TelescopePropagator propagator(std::move(stepper), std::move(navigator), Acts::getDefaultLogger("Propagator", Acts::Logging::ERROR, &std::cerr));
  m_machinery.reset(new Machinery{TelescopeFinder(std::move(propagator), Acts::getDefaultLogger("Finder", Acts::Logging::ERROR, &std::cerr)),
                                  {},
                                  Acts::GreedyAmbiguityResolution(ambiguity_configuration(), Acts::getDefaultLogger("Ambiguity", Acts::Logging::ERROR, &std::cerr))});
}

TrackFinder::~TrackFinder() = default;

EventFinding TrackFinder::find(const DataEvent& event, std::uint32_t event_ordinal) const {
  EventFinding finding;
  finding.event_ordinal = event_ordinal;
  finding.hit_count = event.hits.size();
  const SeedSearch seeds = find_seeds(event, m_sigma_loc0_mm, m_field_along_v_tesla);
  finding.seeds_found = seeds.triples.size();
  finding.seed_budget_reached = seeds.reached_budget;

  const EventLinks event_links = links_of(hits_by_plane(event), m_telescope, m_sigma_loc0_mm, m_sigma_loc1_mm);
  SeedBudget budget;
  BudgetedSelector selector{budgeted_measurement_selector(), &budget};
  StateCreator creator;
  creator.calibrator.connect<&calibrate_plane_hit>();
  creator.measurementSelector.connect<&BudgetedSelector::select>(&selector);
  WindowedStates windowed{&creator, &m_telescope, &event_links, m_sigma_loc0_mm * m_sigma_loc0_mm};

  Acts::CombinatorialKalmanFilterExtensions<FindingContainer> extensions;
  extensions.updater.connect<&Acts::GainMatrixUpdater::operator()<Trajectory>>(&m_machinery->updater);
  extensions.branchStopper.connect<&stop_branch>();
  extensions.createTrackStates.connect<&WindowedStates::create>(&windowed);

  Acts::PropagatorPlainOptions plain_options(m_telescope.geometry_context, m_telescope.field_context);
  plain_options.maxSteps = finding_most_propagator_steps;
  // Material: none (section 4.1), so scattering and energy loss are off.
  const TelescopeFinder::Options options(m_telescope.geometry_context, m_telescope.field_context, std::cref(m_telescope.calibration_context), extensions, plain_options, false, false);

  const Acts::ParticleHypothesis hypothesis(Acts::PdgParticle::eInvalid, float(particle_mass_gev), 1.0f);
  FindingContainer tracks = Acts::TrackContainer{Acts::VectorTrackContainer{}, Trajectory{}};
  std::vector<std::vector<std::size_t>> candidates_of_hit(event.hits.size());

  finding.seeds.reserve(seeds.triples.size());
  for (const HitTriple& triple : seeds.triples) {
    finding.seeds.push_back({triple, "no-candidate", finding.candidates.size(), 0, 0});
    SeedRecord& seed = finding.seeds.back();
    if (on_one_candidate(triple, candidates_of_hit)) {
      seed.outcome = "skipped";
      ++finding.seeds_skipped;
      continue;
    }
    ++finding.seeds_run;
    const std::optional<SeedStart> start = seed_start_of({global_of(event.hits[triple.hit_keys[0]]), global_of(event.hits[triple.hit_keys[1]]), global_of(event.hits[triple.hit_keys[2]])},
                                                         m_sigma_loc0_mm, m_sigma_loc1_mm, m_field_along_v_tesla);
    if (!start) {
      seed.outcome = "no-start";
      ++finding.seeds_failed;
      continue;
    }
    const Acts::Vector4 start_four(start->position_mm.x(), start->position_mm.y(), start->position_mm.z(), 0.0);
    const auto start_parameters = Acts::BoundTrackParameters::createCurvilinear(start_four, start->direction, start->q_over_p, start->covariance, hypothesis);

    tracks.clear();
    budget = SeedBudget{};
    auto found = m_machinery->finder.findTracks(start_parameters, options, tracks);
    if (!found.ok()) {
      if (found.error() == Acts::CombinatorialKalmanFilterError::PropagationReachesMaxSteps) {
        seed.outcome = "step-limit";
        budget.truncated = true;
      } else {
        seed.outcome = "filter-error";
        ++finding.seeds_failed;
      }
      finding.seeds_truncated += budget.truncated ? 1 : 0;
      continue;
    }
    finding.seeds_truncated += budget.truncated ? 1 : 0;

    std::size_t kept_from_seed = 0;
    for (auto track : *found) {
      if (track.nMeasurements() < finding_least_measurements) {
        ++seed.short_branches;
        continue;
      }
      FoundCandidate candidate;
      candidate.key = "event-" + std::to_string(event_ordinal) + "-candidate-" + std::to_string(finding.candidates.size());
      candidate.seed_planes = triple.planes;
      candidate.search_truncated = budget.truncated;
      candidate.measurements = std::int32_t(track.nMeasurements());
      candidate.holes = std::int32_t(track.nHoles());
      candidate.search_chi2 = track.chi2();
      bool at_tip = true;
      for (auto state : track.trackStatesReversed()) {
        if (at_tip) {
          candidate.q_over_p = state.filtered()[Acts::eBoundQOverP];
          at_tip = false;
        }
        if (state.typeFlags().isMeasurement()) {
          candidate.hit_keys.push_back(state.getUncalibratedSourceLink().template get<PlaneHitLink>().hit_key);
        }
      }
      std::reverse(candidate.hit_keys.begin(), candidate.hit_keys.end());
      for (const std::uint32_t hit_key : candidate.hit_keys) {
        candidates_of_hit[hit_key].push_back(finding.candidates.size());
      }
      finding.candidates.push_back(std::move(candidate));
      ++kept_from_seed;
    }
    finding.seeds_without_candidate += kept_from_seed == 0 ? 1 : 0;
    seed.candidates = kept_from_seed;
    seed.outcome = kept_from_seed == 0 ? "no-candidate" : "candidates";
  }

  Acts::GreedyAmbiguityResolution::State ambiguity = ambiguity_state_of(finding.candidates);
  if (!finding.candidates.empty()) {
    m_machinery->resolver.resolve(ambiguity);
  }
  // resolve() stops early only below the limit, so a track left at or above it means the iterations ran out with a conflict left.
  for (const std::size_t track : ambiguity.selectedTracks) {
    finding.ambiguity_budget_reached = finding.ambiguity_budget_reached || ambiguity.sharedMeasurementsPerTrack[track] >= ambiguity_most_shared_hits;
  }
  if (finding.seed_budget_reached || finding.ambiguity_budget_reached) {
    for (FoundCandidate& candidate : finding.candidates) {
      candidate.search_truncated = true;  // the search or the resolution stopped short for the whole event
    }
  }
  for (std::size_t index = 0; index < finding.candidates.size(); ++index) {
    FoundCandidate& candidate = finding.candidates[index];
    if (ambiguity.selectedTracks.count(index) == 0) {
      candidate.outcome = "evicted";
      candidate.failure_category = "ambiguity";
      continue;
    }
    // The filter's q/p carries the seed's prior and hits twice, so the hit set is fitted again with the refit's wide prior; and since that q/p
    // can sit outside the domain kalman_refit.hpp states, the fit is repeated from its own result.
    HitSet hit_set;
    hit_set.track_key = candidate.key;
    hit_set.event_ordinal = event_ordinal;
    hit_set.assumed_q_over_p = candidate.q_over_p;
    hit_set.hit_keys = candidate.hit_keys;
    RefitResult fit;
    bool fitted = std::isfinite(hit_set.assumed_q_over_p) && hit_set.assumed_q_over_p != 0.0;
    for (int pass = 0; fitted && pass < finding_fit_passes; ++pass) {
      fit = m_fitter.fit(hit_set, event);
      fitted = fit.track.status == "fitted";
      if (fitted) {
        const auto smoothed = std::find_if(fit.parameters.begin(), fit.parameters.end(), [](const ParameterRecord& record) { return record.state_type == "smoothed"; });
        fitted = smoothed != fit.parameters.end() && std::isfinite(smoothed->parameters[4]) && smoothed->parameters[4] != 0.0;
        if (fitted) {
          hit_set.assumed_q_over_p = smoothed->parameters[4];
        }
      }
    }
    if (!fitted) {
      candidate.outcome = "fit-failed";
      candidate.failure_category = "fit";
      continue;
    }
    candidate.outcome = "selected";
    candidate.failure_category = "none";
    candidate.fit_chi2 = fit.track.chi2;
    candidate.fit_coordinates = fit.track.measured_coordinates;
    finding.fits.push_back(std::move(fit));
  }

  const bool none_selected = finding.fits.empty();
  finding.failure_category = !none_selected ? "none" : (finding.search_truncated() ? "search-truncated" : "seed-or-finding");
  return finding;
}

}  // namespace t07
