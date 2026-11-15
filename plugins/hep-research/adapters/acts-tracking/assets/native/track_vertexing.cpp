#include "track_vertexing.hpp"

#include <Acts/Definitions/Algebra.hpp>
#include <Acts/Definitions/Direction.hpp>
#include <Acts/Definitions/TrackParametrization.hpp>
#include <Acts/Definitions/Units.hpp>
#include <Acts/EventData/BoundTrackParameters.hpp>
#include <Acts/EventData/ParticleHypothesis.hpp>
#include <Acts/MagneticField/ConstantBField.hpp>
#include <Acts/Propagator/EigenStepper.hpp>
#include <Acts/Propagator/Propagator.hpp>
#include <Acts/Propagator/PropagatorOptions.hpp>
#include <Acts/Propagator/VoidNavigator.hpp>
#include <Acts/Surfaces/PerigeeSurface.hpp>
#include <Acts/Surfaces/Surface.hpp>
#include <Acts/Utilities/AnnealingUtility.hpp>
#include <Acts/Utilities/Logger.hpp>
#include <Acts/Vertexing/AdaptiveMultiVertexFinder.hpp>
#include <Acts/Vertexing/AdaptiveMultiVertexFitter.hpp>
#include <Acts/Vertexing/GaussianTrackDensity.hpp>
#include <Acts/Vertexing/HelicalTrackLinearizer.hpp>
#include <Acts/Vertexing/ImpactPointEstimator.hpp>
#include <Acts/Vertexing/TrackAtVertex.hpp>
#include <Acts/Vertexing/TrackDensityVertexFinder.hpp>
#include <Acts/Vertexing/Vertex.hpp>
#include <Acts/Vertexing/VertexingOptions.hpp>

#include <cmath>
#include <exception>
#include <iostream>
#include <optional>
#include <sstream>
#include <stdexcept>

#include "t07_fixture_constants.hpp"

namespace t07 {
namespace {

// The propagator the linearizer and the impact point estimator are given, and that carries each track to the reference line: no navigator, since every
// target is a surface named in the call, and no material (section 4.1).
using VertexPropagator = Acts::Propagator<Acts::EigenStepper<>, Acts::VoidNavigator>;

std::string number_text(double value) {
  std::ostringstream text;
  text.precision(17);
  text << value;
  return text.str();
}

std::string flag_text(bool value) { return value ? "1" : "0"; }

std::string list_text(const std::vector<double>& values) {
  std::string text;
  for (const double value : values) {
    text += (text.empty() ? "" : ",") + number_text(value);
  }
  return text;
}

std::unique_ptr<const Acts::Logger> quiet_logger(const std::string& name) { return Acts::getDefaultLogger(name, Acts::Logging::ERROR, &std::cerr); }

// The first smoothed state along a fitted track, nearest the vertices, as ACTS bound parameters on its plane. Empty when the fit holds none.
std::optional<Acts::BoundTrackParameters> first_smoothed_state(const RefitResult& fit, const TelescopeGeometry& telescope) {
  for (const ParameterRecord& record : fit.parameters) {  // in state order (KalmanRefit::fit sorts them)
    if (record.state_type != "smoothed") {
      continue;
    }
    for (const StateRecord& state : fit.states) {
      if (state.index != record.state_index) {
        continue;
      }
      if (state.plane < 1 || state.plane > plane_count) {
        return std::nullopt;
      }
      Acts::BoundVector parameters = Acts::BoundVector::Zero();
      for (int row = 0; row < 6; ++row) {
        parameters[row] = record.parameters[row];
      }
      Acts::BoundMatrix covariance = Acts::BoundMatrix::Zero();
      int entry = 0;
      for (int row = 0; row < 6; ++row) {
        for (int column = row; column < 6; ++column) {
          covariance(row, column) = record.covariance[entry];
          covariance(column, row) = record.covariance[entry];
          ++entry;
        }
      }
      if (!parameters.allFinite() || !covariance.allFinite()) {
        return std::nullopt;
      }
      const Acts::ParticleHypothesis hypothesis(Acts::PdgParticle::eInvalid, float(particle_mass_gev), 1.0f);
      return Acts::BoundTrackParameters(telescope.planes.at(state.plane - 1), parameters, covariance, hypothesis);
    }
    return std::nullopt;
  }
  return std::nullopt;
}

bool all_finite(const FoundVertex& vertex) {
  bool finite = std::isfinite(vertex.chi2) && std::isfinite(vertex.ndf);
  for (const double value : vertex.position_mm) {
    finite = finite && std::isfinite(value);
  }
  for (const double value : vertex.covariance) {
    finite = finite && std::isfinite(value);
  }
  for (const VertexTrack& track : vertex.tracks) {
    finite = finite && std::isfinite(track.weight) && std::isfinite(track.chi2) && std::isfinite(track.compatibility);
  }
  return finite;
}

}  // namespace

struct TrackVertexer::Machinery {
  std::shared_ptr<const Acts::MagneticFieldProvider> field;
  std::shared_ptr<const VertexPropagator> propagator;
  std::shared_ptr<const Acts::Surface> reference_line;
  Acts::Vertex reference_point;
  std::unique_ptr<const Acts::HelicalTrackLinearizer> linearizer;
  std::unique_ptr<const Acts::AdaptiveMultiVertexFinder> finder;
  std::vector<std::pair<std::string, std::string>> configuration;
};

TrackVertexer::TrackVertexer(const TelescopeGeometry& telescope, double field_along_v_tesla) : m_telescope(telescope), m_machinery(new Machinery) {
  Machinery& machinery = *m_machinery;
  const auto field = std::make_shared<Acts::ConstantBField>(Acts::Vector3(0.0, 0.0, field_along_v_tesla * Acts::UnitConstants::T));
  machinery.field = field;
  machinery.propagator = std::make_shared<VertexPropagator>(Acts::EigenStepper<>(field), Acts::VoidNavigator(), quiet_logger("VertexPropagator"));
  const Acts::Vector3 reference(vertex_reference_x_mm, vertex_reference_y_mm, vertex_reference_z_mm);
  machinery.reference_line = Acts::Surface::makeShared<Acts::PerigeeSurface>(reference);
  machinery.reference_point = Acts::Vertex(reference);  // zero covariance: a position for the seed, never a constraint (useConstraintInFit false below)

  Acts::HelicalTrackLinearizer::Config linearizer_config;
  linearizer_config.bField = field;
  linearizer_config.propagator = machinery.propagator;
  machinery.linearizer = std::make_unique<Acts::HelicalTrackLinearizer>(linearizer_config, quiet_logger("HelicalTrackLinearizer"));

  Acts::ImpactPointEstimator::Config estimator_config(field, machinery.propagator);
  const Acts::ImpactPointEstimator estimator(estimator_config, quiet_logger("ImpactPointEstimator"));

  const Acts::AnnealingUtility::Config annealing_config;
  Acts::AdaptiveMultiVertexFitter::Config fitter_config(estimator);
  fitter_config.annealingTool = Acts::AnnealingUtility(annealing_config);
  fitter_config.extractParameters.connect<&Acts::InputTrack::extractParameters>();
  fitter_config.trackLinearizer.connect<&Acts::HelicalTrackLinearizer::linearizeTrack>(machinery.linearizer.get());

  Acts::GaussianTrackDensity::Config density_config;
  density_config.extractParameters.connect<&Acts::InputTrack::extractParameters>();
  const Acts::GaussianTrackDensity density(density_config);
  const Acts::TrackDensityVertexFinder::Config seeder_config{density};
  const auto seeder = std::make_shared<Acts::TrackDensityVertexFinder>(seeder_config);

  machinery.configuration = {
      {"vertex_seed_finder", "TrackDensityVertexFinder"},
      {"vertex_seed_density", "GaussianTrackDensity"},
      {"vertex_seed_gaussian_shaped", flag_text(density_config.isGaussianShaped)},
      {"vertex_seed_d0_max_significance", number_text(density_config.d0MaxSignificance)},
      {"vertex_seed_z0_max_significance", number_text(density_config.z0MaxSignificance)},
      {"vertex_fitter", "AdaptiveMultiVertexFitter"},
      {"vertex_linearizer", "HelicalTrackLinearizer"},
      {"vertex_linearizer_target_tolerance", number_text(linearizer_config.targetTolerance)},
      {"vertex_estimator_max_iterations", std::to_string(estimator_config.maxIterations)},
      {"vertex_estimator_precision", number_text(estimator_config.precision)},
      {"vertex_fitter_max_iterations", std::to_string(fitter_config.maxIterations)},
      {"vertex_fitter_max_dist_to_lin_point_mm", number_text(fitter_config.maxDistToLinPoint)},
      {"vertex_fitter_min_weight", number_text(fitter_config.minWeight)},
      {"vertex_fitter_max_relative_shift", number_text(fitter_config.maxRelativeShift)},
      {"vertex_fitter_do_smoothing", flag_text(fitter_config.doSmoothing)},
      {"vertex_fitter_use_time", flag_text(fitter_config.useTime)},
      {"vertex_annealing_cut_off", number_text(annealing_config.cutOff)},
      {"vertex_annealing_temperatures", list_text(annealing_config.setOfTemperatures)},
  };

  Acts::AdaptiveMultiVertexFitter fitter(std::move(fitter_config), quiet_logger("AdaptiveMultiVertexFitter"));
  Acts::AdaptiveMultiVertexFinder::Config finder_config(std::move(fitter), seeder, estimator, field);
  finder_config.extractParameters.connect<&Acts::InputTrack::extractParameters>();
  finder_config.initialVariances = Acts::Vector4::Constant(vertex_initial_variance);  // away from ACTS's 1e8: track_vertexing.hpp says why
  const Acts::AdaptiveMultiVertexFinder::Config& read = finder_config;
  const std::vector<std::pair<std::string, std::string>> finder_values = {
      {"vertex_finder_tracks_max_z_interval_mm", number_text(read.tracksMaxZinterval)},
      {"vertex_finder_tracks_max_significance", number_text(read.tracksMaxSignificance)},
      {"vertex_finder_max_vertex_chi2", number_text(read.maxVertexChi2)},
      {"vertex_finder_do_real_multi_vertex", flag_text(read.doRealMultiVertex)},
      {"vertex_finder_use_fast_compatibility", flag_text(read.useFastCompatibility)},
      {"vertex_finder_max_merge_vertex_significance", number_text(read.maxMergeVertexSignificance)},
      {"vertex_finder_min_weight", number_text(read.minWeight)},
      {"vertex_finder_max_iterations", std::to_string(read.maxIterations)},
      {"vertex_finder_add_single_track_vertices", flag_text(read.addSingleTrackVertices)},
      {"vertex_finder_do_full_splitting", flag_text(read.doFullSplitting)},
      {"vertex_finder_maximum_vertex_contamination", number_text(read.maximumVertexContamination)},
      {"vertex_finder_use_seed_constraint", flag_text(read.useSeedConstraint)},
      {"vertex_finder_initial_variances", list_text({read.initialVariances[0], read.initialVariances[1], read.initialVariances[2], read.initialVariances[3]})},
      {"vertex_finder_default_constraint_fit_quality", list_text({read.defaultConstrFitQuality.first, read.defaultConstrFitQuality.second})},
      {"vertex_finder_use_vertex_cov_for_ip_estimation", flag_text(read.useVertexCovForIPEstimation)},
      {"vertex_finder_use_time", flag_text(read.useTime)},
      {"vertex_finder_do_not_break_while_seeding", flag_text(read.doNotBreakWhileSeeding)},
      {"vertex_reference_x_mm", number_text(vertex_reference_x_mm)},
      {"vertex_reference_y_mm", number_text(vertex_reference_y_mm)},
      {"vertex_reference_z_mm", number_text(vertex_reference_z_mm)},
      {"vertex_constraint_in_fit", "none"},
      {"vertex_track_state", "first-smoothed-to-reference-line"},
      {"vertex_reference_propagation_max_steps", std::to_string(Acts::PropagatorPlainOptions(telescope.geometry_context, telescope.field_context).maxSteps)},
  };
  machinery.configuration.insert(machinery.configuration.end(), finder_values.begin(), finder_values.end());
  machinery.finder = std::make_unique<Acts::AdaptiveMultiVertexFinder>(std::move(finder_config), quiet_logger("AdaptiveMultiVertexFinder"));
}

TrackVertexer::~TrackVertexer() = default;

const std::vector<std::pair<std::string, std::string>>& TrackVertexer::configuration() const { return m_machinery->configuration; }

EventVertices TrackVertexer::vertex(const std::vector<RefitResult>& fits) const {
  const Machinery& machinery = *m_machinery;
  EventVertices result;
  // Filled in full before any pointer to an element is taken, so the elements never move: InputTrack holds their addresses, and the finder orders its maps by
  // them, which this vector keeps in the finder's track order.
  std::vector<Acts::BoundTrackParameters> perigees;
  std::vector<std::string> keys;
  perigees.reserve(fits.size());
  for (const RefitResult& fit : fits) {
    const std::optional<Acts::BoundTrackParameters> start = first_smoothed_state(fit, m_telescope);
    if (!start) {
      ++result.unconverted_tracks;
      continue;
    }
    // The reference line lies upstream of plane 1, where every track starts.
    Acts::PropagatorPlainOptions options(m_telescope.geometry_context, m_telescope.field_context);
    options.direction = Acts::Direction::Backward();
    auto carried = machinery.propagator->propagateToSurface(*start, *machinery.reference_line, options);
    if (!carried.ok() || !carried->covariance().has_value() || !carried->parameters().allFinite() || !carried->covariance()->allFinite()) {
      ++result.unconverted_tracks;
      continue;
    }
    perigees.push_back(*carried);
    keys.push_back(fit.track.key);
  }
  std::vector<Acts::InputTrack> inputs;
  inputs.reserve(perigees.size());
  for (const Acts::BoundTrackParameters& perigee : perigees) {
    inputs.emplace_back(&perigee);
  }
  result.input_tracks = inputs.size();
  if (inputs.empty()) {
    return result;
  }

  const Acts::VertexingOptions options(m_telescope.geometry_context, m_telescope.field_context, machinery.reference_point, false);
  try {
    auto state = machinery.finder->makeState(m_telescope.field_context);
    auto found = machinery.finder->find(inputs, options, state);
    if (!found.ok()) {
      result.failure = found.error().message();
      result.status = "failed";
      return result;
    }
    for (const Acts::Vertex& vertex : *found) {
      FoundVertex out;
      const Acts::Vector3 position = vertex.position();
      const Acts::SquareMatrix3 covariance = vertex.covariance();
      out.position_mm = {position.x(), position.y(), position.z()};
      out.covariance = {covariance(0, 0), covariance(0, 1), covariance(0, 2), covariance(1, 1), covariance(1, 2), covariance(2, 2)};
      out.chi2 = vertex.fitQuality().first;
      out.ndf = vertex.fitQuality().second;
      for (const Acts::TrackAtVertex& track : vertex.tracks()) {
        const Acts::BoundTrackParameters* original = track.originalParams.as<Acts::BoundTrackParameters>();
        const std::ptrdiff_t index = original - perigees.data();
        if (index < 0 || std::size_t(index) >= perigees.size()) {
          throw std::runtime_error("a track at a vertex is none of the event's tracks");
        }
        out.tracks.push_back({keys[std::size_t(index)], track.trackWeight, track.chi2Track, track.vertexCompatibility});
      }
      if (!all_finite(out)) {
        result.failure = "a vertex holds a number that is not finite";
        result.status = "failed";
        result.vertices.clear();
        return result;
      }
      result.vertices.push_back(std::move(out));
    }
  } catch (const std::exception& error) {
    result.failure = std::string("exception: ") + error.what();
    result.status = "failed";
    result.vertices.clear();
  }
  return result;
}

}  // namespace t07
