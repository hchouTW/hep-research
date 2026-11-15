#include "kalman_refit.hpp"

#include <Acts/Definitions/TrackParametrization.hpp>
#include <Acts/Definitions/Units.hpp>
#include <Acts/EventData/AnyTrackStateProxy.hpp>
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
#include <Acts/Utilities/TrackHelpers.hpp>
#include <Acts/Utilities/UnitVectors.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <functional>
#include <iostream>
#include <set>
#include <stdexcept>

#include "plane_hit_link.hpp"
#include "t07_fixture_constants.hpp"
#include "track_fit_outputs.hpp"

namespace t07 {
namespace {

using Trajectory = Acts::VectorMultiTrajectory;
using TelescopePropagator = Acts::Propagator<Acts::EigenStepper<>, Acts::Navigator>;
using TelescopeFitter = Acts::KalmanFitter<TelescopePropagator, Trajectory>;

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

// R33 (track_fit_outputs.hpp, t07-r33/1) at one state with a hit, read from the state the fitter left: the hit, the three states, the surface.
// Nothing here changes the state. state_index is the reversed index the caller uses, renumbered with the others afterwards. A measurement's
// filtered and smoothed states hold the hit; an outlier's do not (the fitter left its filtered state at the predicted one and smoothed past
// it), so its covariances add, and its unbiased residual is its smoothed one.
template <typename state_proxy_t>
void add_measurement_outputs(state_proxy_t& state, std::int32_t state_index, bool holds_the_hit, const std::string& track_key, const TelescopeGeometry& telescope,
                             double field_along_v_tesla, RefitOutputs& outputs) {
  if (!state.hasPredicted() || !state.hasFiltered() || !state.hasSmoothed() || !state.hasCalibrated() || state.calibratedSize() != 2) {
    throw std::runtime_error("a state with a hit of " + track_key + " lacks a state type or its two-dimensional hit");
  }
  const Acts::BoundSubspaceIndices projector = state.projectorSubspaceIndices();
  if (projector[0] != Acts::eBoundLoc0 || projector[1] != Acts::eBoundLoc1) {
    throw std::runtime_error("a measurement of " + track_key + " is not (loc0, loc1)");
  }
  const Acts::Vector2 measurement = state.template calibrated<2>();
  const Acts::SquareMatrix2 measurement_covariance = state.template calibratedCovariance<2>();
  const Acts::BoundVector predicted = state.predicted();
  const Acts::BoundMatrix predicted_covariance = state.predictedCovariance();
  const Acts::BoundVector filtered = state.filtered();
  const Acts::BoundMatrix filtered_covariance = state.filteredCovariance();
  const Acts::BoundVector smoothed = state.smoothed();
  const Acts::BoundMatrix smoothed_covariance = state.smoothedCovariance();

  auto keep = [&](const char* state_type, const LocalResidual& residual) {
    ResidualRecord record;
    record.track_key = track_key;
    record.state_index = state_index;
    record.state_type = state_type;
    record.residual = {residual.value[0], residual.value[1]};
    record.covariance = {residual.covariance(0, 0), residual.covariance(0, 1), residual.covariance(1, 1)};
    outputs.residuals.push_back(record);
  };
  keep("predicted", residual_of(measurement, measurement_covariance, predicted.head<2>(), predicted_covariance.topLeftCorner<2, 2>(), false));
  keep("filtered", residual_of(measurement, measurement_covariance, filtered.head<2>(), filtered_covariance.topLeftCorner<2, 2>(), holds_the_hit));
  const LocalResidual smoothed_residual =
      residual_of(measurement, measurement_covariance, smoothed.head<2>(), smoothed_covariance.topLeftCorner<2, 2>(), holds_the_hit);
  keep("smoothed", smoothed_residual);
  keep("unbiased", holds_the_hit ? unbiased_from_smoothed(smoothed_residual, measurement_covariance) : smoothed_residual);

  // ACTS's own unbiased state (Utilities/TrackHelpers.hpp, the non-template overload, as ACTS's own template selects it): only when the caller
  // asks (cai_track_output_check), never in a production refit, and only where the hit was used.
  if (outputs.with_acts_unbiased && holds_the_hit) {
    std::pair<Acts::BoundVector, Acts::BoundMatrix> (&acts_unbiased_of)(const Acts::AnyConstTrackStateProxy&) = Acts::calculateUnbiasedParametersCovariance;
    const Acts::AnyConstTrackStateProxy any_state(state);
    const auto [unbiased_state, unbiased_covariance] = acts_unbiased_of(any_state);
    outputs.acts_unbiased.push_back({state_index, {unbiased_state[Acts::eBoundLoc0], unbiased_state[Acts::eBoundLoc1]},
                                     {unbiased_covariance(0, 0), unbiased_covariance(0, 1), unbiased_covariance(1, 1)}});
  }

  const Acts::Surface& surface = state.referenceSurface();
  const Acts::GeometryContext& context = telescope.geometry_context;
  const Acts::Vector3 direction = Acts::makeDirectionFromPhiTheta(smoothed[Acts::eBoundPhi], smoothed[Acts::eBoundTheta]);
  const Acts::Vector3 position = surface.localToGlobal(context, Acts::Vector2(smoothed[Acts::eBoundLoc0], smoothed[Acts::eBoundLoc1]), direction);
  const Incidence incidence = incidence_of(surface.localToGlobalTransform(context).linear(), direction);
  const ResidualDerivative derivative =
      acts_residual_derivative(surface, context, position, direction, path_derivative_of(direction, smoothed[Acts::eBoundQOverP], field_along_v_tesla, particle_mass_gev));
  MeasurementOutputRecord output;
  output.track_key = track_key;
  output.state_index = state_index;
  output.geometry_id = surface.geometryId().value();
  output.projector = {std::int32_t(projector[0]), std::int32_t(projector[1])};
  output.local_slope = incidence.local_slope;
  output.incidence_rad = incidence.angle_rad;
  output.thickness_mm = surface.thickness();
  output.path_factor = incidence.path_factor;
  output.sensitive_path_mm = output.thickness_mm * output.path_factor;
  for (int row = 0; row < 2; ++row) {
    for (int column = 0; column < 6; ++column) {
      output.alignment_derivative[6 * row + column] = derivative(row, column);
    }
  }
  outputs.measurement_outputs.push_back(output);  // reference_derivative follows once the states are numbered
}

Acts::BoundMatrix full_covariance(const std::array<double, 21>& upper) {
  Acts::BoundMatrix covariance;
  int entry = 0;
  for (int row = 0; row < 6; ++row) {
    for (int column = row; column < 6; ++column) {
      covariance(row, column) = covariance(column, row) = upper[entry++];
    }
  }
  return covariance;
}

const ParameterRecord& parameters_of(const RefitResult& result, std::int32_t state_index, const std::string& state_type) {
  for (const ParameterRecord& record : result.parameters) {
    if (record.state_index == state_index && record.state_type == state_type) {
      return record;
    }
  }
  throw std::runtime_error("the fit of " + result.track.key + " has no " + state_type + " state " + std::to_string(state_index));
}

// The first state along the track whose hit the fit used, or -1: the track's reference state.
std::int32_t reference_index_of(const RefitResult& result) {
  for (const StateRecord& state : result.states) {
    if (state.kind == "measurement") {
      return state.index;
    }
  }
  return -1;
}

// After the states are numbered along the track: the same numbers for the outputs, in state order; each output's derivative against the track's
// reference state, the smoothed state at its first measurement, from transports[k] = J_{k<-ref}, the propagator's Jacobian of the smoothed reference
// state carried to state k's surface (D1 stage 8 fix round 2; KalmanRefit::reference_transports); and, for a fitted track, its track output and the
// full covariance of its residuals against the smoothed states, with C_ref recomputed in the same linearization (track_fit_outputs.hpp).
// A failed track keeps its per-measurement outputs and has neither.
void number_outputs_along_the_track(std::int32_t state_count, const RefitResult& result, const std::vector<Acts::BoundMatrix>& transports,
                                    const Acts::BoundMatrix& prior_at_reference, double field_along_v_tesla, RefitOutputs& outputs) {
  for (ResidualRecord& record : outputs.residuals) {
    record.state_index = state_count - 1 - record.state_index;
  }
  for (MeasurementOutputRecord& record : outputs.measurement_outputs) {
    record.state_index = state_count - 1 - record.state_index;
  }
  for (ActsUnbiasedReading& reading : outputs.acts_unbiased) {
    reading.state_index = state_count - 1 - reading.state_index;
  }
  std::stable_sort(outputs.residuals.begin(), outputs.residuals.end(), [](const ResidualRecord& first, const ResidualRecord& second) { return first.state_index < second.state_index; });
  std::stable_sort(outputs.measurement_outputs.begin(), outputs.measurement_outputs.end(),
                   [](const MeasurementOutputRecord& first, const MeasurementOutputRecord& second) { return first.state_index < second.state_index; });
  std::stable_sort(outputs.acts_unbiased.begin(), outputs.acts_unbiased.end(),
                   [](const ActsUnbiasedReading& first, const ActsUnbiasedReading& second) { return first.state_index < second.state_index; });
  const std::int32_t reference = reference_index_of(result);
  if (reference < 0) {
    return;  // no state the fit used a hit on: nothing to refer derivatives to
  }
  for (MeasurementOutputRecord& output : outputs.measurement_outputs) {
    const ReferenceDerivative derivative = reference_derivative_of(transports.at(std::size_t(output.state_index)));
    for (int row = 0; row < 2; ++row) {
      for (int column = 0; column < 6; ++column) {
        output.reference_derivative[6 * row + column] = derivative(row, column);
      }
    }
  }
  if (result.track.status != "fitted") {
    return;
  }
  const ParameterRecord* reference_state = nullptr;
  for (const ParameterRecord& record : result.parameters) {
    if (record.state_index == reference && record.state_type == "smoothed") {
      reference_state = &record;
    }
  }
  if (reference_state == nullptr) {
    throw std::runtime_error("the fit of " + result.track.key + " has no smoothed state at its first measurement");
  }
  TrackOutputRecord output;
  output.track_key = result.track.key;
  output.q_over_p = reference_state->parameters[Acts::eBoundQOverP];
  output.q_over_p_variance = reference_state->covariance[18];  // (4, 4) in the upper triangle, row by row
  output.charge = output.q_over_p > 0.0 ? 1 : -1;
  output.reference_state_index = reference;
  output.topology = "collision";  // tracks from a vertex region (section 4.1), not cosmics, no resonance
  output.constraint = "none";     // no vertex or beam constraint enters the refit (BP04, R37)
  output.field = field_along_v_tesla == 0.0 ? "off" : "on";
  outputs.track_output.push_back(output);

  std::vector<ReferenceDerivative> derivatives;
  std::vector<Acts::SquareMatrix2> measurement_covariances;
  for (const MeasurementOutputRecord& measured : outputs.measurement_outputs) {
    const StateRecord& state = result.states.at(std::size_t(measured.state_index));
    if (state.kind != "measurement") {
      continue;  // an outlier's hit did not enter the fit, so the closed form does not cover it
    }
    ReferenceDerivative derivative;
    for (int row = 0; row < 2; ++row) {
      for (int column = 0; column < 6; ++column) {
        derivative(row, column) = measured.reference_derivative[6 * row + column];
      }
    }
    derivatives.push_back(derivative);
    Acts::SquareMatrix2 covariance;
    covariance << state.covariance[0], state.covariance[1], state.covariance[1], state.covariance[2];
    measurement_covariances.push_back(covariance);
  }
  const Acts::DynamicMatrix covariance =
      residual_covariance_of(derivatives, measurement_covariances, reference_covariance_of(derivatives, measurement_covariances, prior_at_reference));
  ResidualCovarianceRecord record;
  record.track_key = result.track.key;
  record.measurement_count = std::int32_t(derivatives.size());
  for (Eigen::Index row = 0; row < covariance.rows(); ++row) {
    for (Eigen::Index column = row; column < covariance.cols(); ++column) {
      record.covariance.push_back(covariance(row, column));
    }
  }
  outputs.residual_covariance.push_back(record);
}

}  // namespace

struct KalmanRefit::Machinery {
  TelescopeFitter fitter;
  Acts::GainMatrixUpdater updater;
  Acts::GainMatrixSmoother smoother;
  TelescopePropagator propagator;  // R33 only: the fit's own stepper, navigator and field, to carry the smoothed reference state
};

KalmanRefit::KalmanRefit(const TelescopeGeometry& telescope, double field_along_v_tesla, double sigma_loc0_mm, double sigma_loc1_mm)
    : m_telescope(telescope), m_sigma_loc0_mm(sigma_loc0_mm), m_sigma_loc1_mm(sigma_loc1_mm), m_field_along_v_tesla(field_along_v_tesla) {
  auto field = std::make_shared<Acts::ConstantBField>(Acts::Vector3(0.0, 0.0, field_along_v_tesla * Acts::UnitConstants::T));
  Acts::EigenStepper<> stepper(field);
  Acts::Navigator::Config navigator_config;
  navigator_config.trackingGeometry = telescope.tracking_geometry;
  Acts::Navigator navigator(navigator_config, Acts::getDefaultLogger("Navigator", Acts::Logging::ERROR, &std::cerr));
  TelescopePropagator propagator(std::move(stepper), std::move(navigator), Acts::getDefaultLogger("Propagator", Acts::Logging::ERROR, &std::cerr));
  Acts::EigenStepper<> transport_stepper(field);
  Acts::Navigator transport_navigator(navigator_config, Acts::getDefaultLogger("Navigator", Acts::Logging::ERROR, &std::cerr));
  TelescopePropagator transport(std::move(transport_stepper), std::move(transport_navigator), Acts::getDefaultLogger("Propagator", Acts::Logging::ERROR, &std::cerr));
  m_machinery.reset(new Machinery{TelescopeFitter(std::move(propagator), Acts::getDefaultLogger("KalmanFitter", Acts::Logging::ERROR, &std::cerr)), {}, {},
                                  std::move(transport)});
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

RefitResult KalmanRefit::fit(const HitSet& hit_set, const DataEvent& event) const { return fit_from(hit_set, event, start_of(hit_set, event), nullptr); }

RefitResult KalmanRefit::fit(const HitSet& hit_set, const DataEvent& event, const RefitStart& refit_start) const {
  return fit_from(hit_set, event, refit_start, nullptr);
}

RefitResult KalmanRefit::fit(const HitSet& hit_set, const DataEvent& event, RefitOutputs& outputs) const {
  const bool with_acts_unbiased = outputs.with_acts_unbiased;
  outputs = RefitOutputs{};
  outputs.with_acts_unbiased = with_acts_unbiased;
  return fit_from(hit_set, event, start_of(hit_set, event), &outputs);
}

// J_{k<-ref} for every state k (identity at the reference, zero at a hole): the smoothed reference state, with a covariance so that the stepper
// carries a Jacobian (EigenStepper::initialize sets jacToGlobal and jacTransport only when a covariance is given), propagated to state k's surface by
// the fit's propagator; Propagator::makeResult returns transportJacobian = transportToBound(state, target), "the jacobian from the previous anchor"
// (EigenStepper.hpp), and no actor re-anchors on the way, so it runs from the reference surface to the target. Its linearization point is the
// fitted (smoothed) trajectory. Backwards for a state before the reference (only an outlier can be there).
std::optional<std::vector<Acts::BoundMatrix>> KalmanRefit::reference_transports(const RefitResult& result, std::int32_t reference, std::string& failure) const {
  const ParameterRecord& smoothed = parameters_of(result, reference, "smoothed");
  Acts::BoundVector parameters;
  for (int row = 0; row < 6; ++row) {
    parameters[row] = smoothed.parameters[row];
  }
  const Acts::ParticleHypothesis hypothesis(Acts::PdgParticle::eInvalid, float(particle_mass_gev), 1.0f);
  const Acts::BoundTrackParameters start(m_telescope.planes.at(std::size_t(result.states.at(std::size_t(reference)).plane - 1)), parameters,
                                         Acts::BoundMatrix(Acts::BoundMatrix::Identity()), hypothesis);
  std::vector<Acts::BoundMatrix> transports(result.states.size(), Acts::BoundMatrix::Zero());
  for (const StateRecord& state : result.states) {
    if (state.kind == "hole") {
      continue;
    }
    if (state.index == reference) {
      transports[std::size_t(state.index)] = Acts::BoundMatrix::Identity();
      continue;
    }
    TelescopePropagator::Options<> options(m_telescope.geometry_context, m_telescope.field_context);
    options.direction = state.index > reference ? Acts::Direction::Forward() : Acts::Direction::Backward();
    const auto carried = m_machinery->propagator.propagate(start, *m_telescope.planes.at(std::size_t(state.plane - 1)), options);
    if (!carried.ok() || !carried.value().transportJacobian.has_value()) {
      failure = "the smoothed reference state could not be carried to plane " + std::to_string(state.plane) +
                (carried.ok() ? std::string(", no Jacobian") : ": " + carried.error().message());
      return std::nullopt;
    }
    transports[std::size_t(state.index)] = *carried.value().transportJacobian;
  }
  return transports;
}

RefitResult KalmanRefit::fit_from(const HitSet& hit_set, const DataEvent& event, const RefitStart& refit_start, RefitOutputs* outputs) const {
  const std::vector<const PlaneHit*> hits = checked_hits(hit_set, event);

  RefitResult result;
  result.track.key = hit_set.track_key;
  result.track.event_ordinal = hit_set.event_ordinal;
  result.track.assumed_q_over_p = hit_set.assumed_q_over_p;
  if (hit_set_measures_nothing_of_q_over_p(hits.size(), m_field_along_v_tesla)) {
    std::cerr << "fit of " << hit_set.track_key << " refused: " << hits.size() << " planes in a field measure no q/p\n";
    result.track.status = "failed";
    result.track.failure_category = "fit";  // stays in the product: no failed object leaves a denominator
    return result;
  }

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
    if (outputs != nullptr) {
      if (record.kind != "hole") {
        add_measurement_outputs(state, reversed_index, record.kind == "measurement", hit_set.track_key, m_telescope, m_field_along_v_tesla, *outputs);
      }
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
  if (outputs != nullptr) {
    const std::int32_t reference = reference_index_of(result);
    std::vector<Acts::BoundMatrix> transports;
    Acts::BoundMatrix prior_at_reference = Acts::BoundMatrix::Identity();
    if (reference >= 0) {
      // Fix round 3 (re-review N8): a transport that fails, as a crossing just outside a plane's bounds could make it (SurfaceReached takes no
      // boundary tolerance), fails this track as a fit failure, kept in the denominator and counted by the driver, instead of stopping the refit.
      // Only the outputs path reaches here, so the finder's and the truth-seeded run's products cannot change.
      std::string failure;
      const auto carried = reference_transports(result, reference, failure);
      if (!carried.has_value()) {
        std::cerr << "fit of " << hit_set.track_key << " failed: " << failure << "\n";
        RefitResult failed;
        failed.track = result.track;
        failed.track.status = "failed";
        failed.track.failure_category = "fit";
        *outputs = RefitOutputs{outputs->with_acts_unbiased};
        return failed;
      }
      transports = *carried;
      prior_at_reference = full_covariance(parameters_of(result, reference, "predicted").covariance);
    }
    number_outputs_along_the_track(state_count, result, transports, prior_at_reference, m_field_along_v_tesla, *outputs);
  }
  return result;
}

}  // namespace t07
