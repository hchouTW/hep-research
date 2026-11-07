#include "kalman_refit.hpp"

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
#include <Acts/TrackFitting/GainMatrixSmoother.hpp>
#include <Acts/TrackFitting/GainMatrixUpdater.hpp>
#include <Acts/TrackFitting/KalmanFitter.hpp>
#include <Acts/Utilities/Logger.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <functional>
#include <iostream>
#include <set>
#include <stdexcept>

#include "t07_fixture_constants.hpp"

namespace t07 {
namespace {

using Trajectory = Acts::VectorMultiTrajectory;
using TelescopePropagator = Acts::Propagator<Acts::EigenStepper<>, Acts::Navigator>;
using TelescopeFitter = Acts::KalmanFitter<TelescopePropagator, Trajectory>;

// The measurement travels inside the source link, as Acts/EventData/detail/TestSourceLink.hpp does it.
struct PlaneHitLink {
  std::uint32_t hit_key = 0;
  const Acts::Surface* surface = nullptr;
  double loc0_mm = 0.0;
  double loc1_mm = 0.0;
  double variance0_mm2 = 0.0;
  double variance1_mm2 = 0.0;
};

const Acts::Surface* surface_of_link(const Acts::SourceLink& source_link) { return source_link.get<PlaneHitLink>().surface; }

void calibrate_plane_hit(const Acts::GeometryContext& /*geometry_context*/, const Acts::CalibrationContext& /*calibration_context*/,
                         const Acts::SourceLink& source_link, Trajectory::TrackStateProxy track_state) {
  const PlaneHitLink& link = source_link.get<PlaneHitLink>();
  track_state.setUncalibratedSourceLink(Acts::SourceLink{source_link});
  track_state.allocateCalibrated(2);
  track_state.template calibrated<2>() = Acts::Vector2(link.loc0_mm, link.loc1_mm);
  Acts::SquareMatrix<2> covariance = Acts::SquareMatrix<2>::Zero();
  covariance(0, 0) = link.variance0_mm2;
  covariance(1, 1) = link.variance1_mm2;
  track_state.template calibratedCovariance<2>() = covariance;
  track_state.setProjectorSubspaceIndices(std::array{Acts::eBoundLoc0, Acts::eBoundLoc1});
}

template <typename parameters_t, typename covariance_t>
ParameterRecord parameter_record(const std::string& track_key, std::int32_t state_index, const std::string& state_type,
                                 const parameters_t& parameters, const covariance_t& covariance) {
  ParameterRecord record;
  record.track_key = track_key;
  record.state_index = state_index;
  record.state_type = state_type;
  for (int row = 0; row < 6; ++row) {
    record.parameters[row] = parameters[row];
  }
  int entry = 0;
  for (int row = 0; row < 6; ++row) {
    for (int column = row; column < 6; ++column) {
      record.covariance[entry++] = covariance(row, column);
    }
  }
  return record;
}

// The set's hits in plane order, after every refusal of a set the fitter could not fit as stated.
std::vector<const PlaneHit*> checked_hits(const HitSet& hit_set, const DataEvent& event) {
  // The fitter keeps one measurement per surface and drops a second one with no message (make_propagator_options,
  // try_emplace), so a hit set with two hits on a plane is refused here.
  std::vector<const PlaneHit*> hits;
  std::set<std::uint32_t> planes;
  for (const std::uint32_t hit_key : hit_set.hit_keys) {
    if (hit_key >= event.hits.size()) {
      throw std::invalid_argument("hit set " + hit_set.track_key + " names hit " + std::to_string(hit_key) + ", not in its event");
    }
    const PlaneHit& hit = event.hits[hit_key];
    if (!planes.insert(hit.plane).second) {
      throw std::invalid_argument("hit set " + hit_set.track_key + " has two hits on plane " + std::to_string(hit.plane));
    }
    hits.push_back(&hit);
  }
  if (planes.size() < 2) {
    throw std::invalid_argument("hit set " + hit_set.track_key + " has fewer than two planes, so no start line");
  }
  if (!std::isfinite(hit_set.assumed_q_over_p) || hit_set.assumed_q_over_p == 0.0) {
    throw std::invalid_argument("hit set " + hit_set.track_key + " assumes no usable q/p");
  }
  std::sort(hits.begin(), hits.end(), [](const PlaneHit* first, const PlaneHit* second) { return first->plane < second->plane; });
  return hits;
}

}  // namespace

struct KalmanRefit::Machinery {
  TelescopeFitter fitter;
  Acts::GainMatrixUpdater updater;
  Acts::GainMatrixSmoother smoother;
};

KalmanRefit::KalmanRefit(const TelescopeGeometry& telescope, double field_along_v_tesla, double sigma_loc0_mm, double sigma_loc1_mm)
    : m_telescope(telescope), m_sigma_loc0_mm(sigma_loc0_mm), m_sigma_loc1_mm(sigma_loc1_mm), m_field_along_v_tesla(field_along_v_tesla) {
  auto field = std::make_shared<Acts::ConstantBField>(Acts::Vector3(0.0, 0.0, field_along_v_tesla * Acts::UnitConstants::T));
  Acts::EigenStepper<> stepper(field);
  Acts::Navigator::Config navigator_config;
  navigator_config.trackingGeometry = telescope.tracking_geometry;
  Acts::Navigator navigator(navigator_config, Acts::getDefaultLogger("Navigator", Acts::Logging::ERROR, &std::cerr));
  TelescopePropagator propagator(std::move(stepper), std::move(navigator), Acts::getDefaultLogger("Propagator", Acts::Logging::ERROR, &std::cerr));
  m_machinery.reset(new Machinery{TelescopeFitter(std::move(propagator), Acts::getDefaultLogger("KalmanFitter", Acts::Logging::ERROR, &std::cerr)), {}, {}});
}

KalmanRefit::~KalmanRefit() = default;

RefitStart KalmanRefit::start_of(const HitSet& hit_set, const DataEvent& event) const {
  const std::vector<const PlaneHit*> hits = checked_hits(hit_set, event);
  const PlaneHit& first_hit = *hits.front();
  const PlaneHit& last_hit = *hits.back();
  const double first_z = (first_hit.plane - 1) * plane_spacing_mm;
  const double last_z = (last_hit.plane - 1) * plane_spacing_mm;
  const double slope_u = (last_hit.loc0_mm - first_hit.loc0_mm) / (last_z - first_z);
  const double slope_v = (last_hit.loc1_mm - first_hit.loc1_mm) / (last_z - first_z);
  // With T the unit tangent and w = (q/p) k B, dT/ds = w (T x z) gives along x, n = sqrt(1 + u'^2 + v'^2):
  // u'' = -w n (1 + u'^2), v'' = -w n u' v'. So through both hits, u(x) = chord(x) + (u''/2)(x - first_z)(x - last_z), and likewise v.
  // Acts::UnitConstants::T is k in the native units of mm and GeV.
  const double bending_per_mm = hit_set.assumed_q_over_p * m_field_along_v_tesla * Acts::UnitConstants::T;
  const double slope_norm = std::sqrt(1.0 + slope_u * slope_u + slope_v * slope_v);
  const double half_u_curvature = -0.5 * bending_per_mm * slope_norm * (1.0 + slope_u * slope_u);
  const double half_v_curvature = -0.5 * bending_per_mm * slope_norm * slope_u * slope_v;
  const double from_first = refit_start_x_mm - first_z;
  const double from_last = refit_start_x_mm - last_z;
  RefitStart start;
  start.position_mm = Acts::Vector3(refit_start_x_mm, first_hit.loc0_mm + slope_u * from_first + half_u_curvature * from_first * from_last,
                                    first_hit.loc1_mm + slope_v * from_first + half_v_curvature * from_first * from_last);
  start.direction = Acts::Vector3(1.0, slope_u + half_u_curvature * (from_first + from_last), slope_v + half_v_curvature * (from_first + from_last)).normalized();
  return start;
}

RefitResult KalmanRefit::fit(const HitSet& hit_set, const DataEvent& event) const { return fit(hit_set, event, start_of(hit_set, event)); }

RefitResult KalmanRefit::fit(const HitSet& hit_set, const DataEvent& event, const RefitStart& refit_start) const {
  const std::vector<const PlaneHit*> hits = checked_hits(hit_set, event);

  std::vector<Acts::SourceLink> source_links;
  for (const PlaneHit* hit : hits) {
    PlaneHitLink link;
    link.hit_key = hit->hit_key;
    link.surface = m_telescope.planes.at(hit->plane - 1).get();
    link.loc0_mm = hit->loc0_mm;
    link.loc1_mm = hit->loc1_mm;
    link.variance0_mm2 = m_sigma_loc0_mm * m_sigma_loc0_mm;
    link.variance1_mm2 = m_sigma_loc1_mm * m_sigma_loc1_mm;
    source_links.emplace_back(std::move(link));
  }

  const Acts::Vector4 start_four(refit_start.position_mm.x(), refit_start.position_mm.y(), refit_start.position_mm.z(), 0.0);
  Acts::BoundMatrix prior = Acts::BoundMatrix::Zero();
  prior(Acts::eBoundLoc0, Acts::eBoundLoc0) = refit_prior_loc_sigma_mm * refit_prior_loc_sigma_mm;
  prior(Acts::eBoundLoc1, Acts::eBoundLoc1) = refit_prior_loc_sigma_mm * refit_prior_loc_sigma_mm;
  prior(Acts::eBoundPhi, Acts::eBoundPhi) = refit_prior_angle_sigma * refit_prior_angle_sigma;
  prior(Acts::eBoundTheta, Acts::eBoundTheta) = refit_prior_angle_sigma * refit_prior_angle_sigma;
  prior(Acts::eBoundQOverP, Acts::eBoundQOverP) = refit_prior_qop_sigma_per_gev * refit_prior_qop_sigma_per_gev;
  prior(Acts::eBoundTime, Acts::eBoundTime) = refit_prior_time_sigma * refit_prior_time_sigma;
  const Acts::ParticleHypothesis hypothesis(Acts::PdgParticle::eInvalid, float(particle_mass_gev), 1.0f);
  const auto start = Acts::BoundTrackParameters::createCurvilinear(start_four, refit_start.direction, hit_set.assumed_q_over_p, prior, hypothesis);

  Acts::KalmanFitterExtensions<Trajectory> extensions;
  extensions.surfaceAccessor.connect<&surface_of_link>();
  extensions.calibrator.connect<&calibrate_plane_hit>();
  extensions.updater.connect<&Acts::GainMatrixUpdater::operator()<Trajectory>>(&m_machinery->updater);
  extensions.smoother.connect<&Acts::GainMatrixSmoother::operator()<Trajectory>>(&m_machinery->smoother);

  const Acts::PropagatorPlainOptions plain_options(m_telescope.geometry_context, m_telescope.field_context);
  // Material: none (section 4.1), so scattering and energy loss are off.
  const Acts::KalmanFitterOptions<Trajectory> fit_options(m_telescope.geometry_context, m_telescope.field_context, std::cref(m_telescope.calibration_context),
                                                          extensions, plain_options, nullptr, false, false);

  Acts::TrackContainer track_container{Acts::VectorTrackContainer{}, Trajectory{}};
  auto fitted = m_machinery->fitter.fit(source_links.begin(), source_links.end(), start, fit_options, track_container);

  RefitResult result;
  result.track.key = hit_set.track_key;
  result.track.event_ordinal = hit_set.event_ordinal;
  result.track.assumed_q_over_p = hit_set.assumed_q_over_p;
  if (!fitted.ok()) {
    std::cerr << "fit of " << hit_set.track_key << " failed: " << fitted.error().message() << "\n";
    result.track.status = "failed";
    result.track.failure_category = "fit";  // stays in the product: no failed object leaves a denominator
    return result;
  }
  auto track = fitted.value();
  result.track.status = "fitted";
  result.track.failure_category = "none";
  result.track.measurements = std::int32_t(track.nMeasurements());
  result.track.holes = std::int32_t(track.nHoles());
  result.track.outliers = std::int32_t(track.nOutliers());
  result.track.chi2 = track.chi2();
  result.track.measured_coordinates = std::int32_t(track.nDoF());
  if (fit_lost_a_hit(result.track.measurements, result.track.outliers, hit_set.hit_keys.size())) {
    result.track.status = "failed";
    result.track.failure_category = "fit";
  }

  for (auto state : track.trackStatesReversed()) {
    const auto flags = state.typeFlags();
    StateRecord record;
    record.track_key = hit_set.track_key;
    record.plane = m_telescope.plane_number_of(state.referenceSurface());
    if (record.plane == 0) {
      throw std::runtime_error("the fit of " + hit_set.track_key + " holds a state on a surface that is not a telescope plane");
    }
    record.kind = flags.isHole() ? "hole" : (flags.isOutlier() ? "outlier" : "measurement");
    if (!flags.isHole()) {
      const PlaneHitLink link = state.getUncalibratedSourceLink().template get<PlaneHitLink>();
      record.hit_key = link.hit_key;
      record.loc0_mm = link.loc0_mm;
      record.loc1_mm = link.loc1_mm;
      record.covariance = {link.variance0_mm2, 0.0, link.variance1_mm2};
    }
    record.path_length_mm = state.pathLength();
    record.chi2 = state.chi2();
    result.states.push_back(record);
    const std::int32_t reversed_index = std::int32_t(result.states.size()) - 1;
    if (state.hasPredicted()) {
      result.parameters.push_back(parameter_record(hit_set.track_key, reversed_index, "predicted", state.predicted(), state.predictedCovariance()));
    }
    if (state.hasFiltered()) {
      result.parameters.push_back(parameter_record(hit_set.track_key, reversed_index, "filtered", state.filtered(), state.filteredCovariance()));
    }
    if (state.hasSmoothed()) {
      result.parameters.push_back(parameter_record(hit_set.track_key, reversed_index, "smoothed", state.smoothed(), state.smoothedCovariance()));
    }
  }

  // Number the states along the track; the loop above walked them backwards.
  std::reverse(result.states.begin(), result.states.end());
  const std::int32_t state_count = std::int32_t(result.states.size());
  for (std::int32_t index = 0; index < state_count; ++index) {
    result.states[index].index = index;
  }
  for (ParameterRecord& record : result.parameters) {
    record.state_index = state_count - 1 - record.state_index;
  }
  std::stable_sort(result.parameters.begin(), result.parameters.end(),
                   [](const ParameterRecord& first, const ParameterRecord& second) { return first.state_index < second.state_index; });
  return result;
}

}  // namespace t07
