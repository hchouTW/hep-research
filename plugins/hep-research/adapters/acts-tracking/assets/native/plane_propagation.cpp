#include "plane_propagation.hpp"

#include <Acts/Definitions/Units.hpp>
#include <Acts/EventData/BoundTrackParameters.hpp>
#include <Acts/EventData/ParticleHypothesis.hpp>
#include <Acts/MagneticField/ConstantBField.hpp>
#include <Acts/Propagator/ActorList.hpp>
#include <Acts/Propagator/EigenStepper.hpp>
#include <Acts/Propagator/Navigator.hpp>
#include <Acts/Propagator/Propagator.hpp>
#include <Acts/Propagator/StandardAborters.hpp>
#include <Acts/Propagator/SurfaceCollector.hpp>
#include <Acts/Utilities/Logger.hpp>

#include <cmath>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>

#include "t07_fixture_constants.hpp"

namespace t07 {
namespace {

using TelescopePropagator = Acts::Propagator<Acts::EigenStepper<>, Acts::Navigator>;
using PlaneCollector = Acts::SurfaceCollector<>;
using CollectingActors = Acts::ActorList<PlaneCollector, Acts::EndOfWorldReached>;

// A position within this distance of the plane counts as on it, for Surface::globalToLocal. Above the propagator's own
// surface tolerance, far below the 0.020 mm hit sigma.
constexpr double on_plane_tolerance_mm = 1e-3;

TelescopePropagator make_propagator(const TelescopeGeometry& telescope, double field_along_v_tesla) {
  auto field = std::make_shared<Acts::ConstantBField>(Acts::Vector3(0.0, 0.0, field_along_v_tesla * Acts::UnitConstants::T));
  Acts::EigenStepper<> stepper(field);
  Acts::Navigator::Config navigator_config;
  navigator_config.trackingGeometry = telescope.tracking_geometry;
  Acts::Navigator navigator(navigator_config, Acts::getDefaultLogger("Navigator", Acts::Logging::ERROR, &std::cerr));
  return TelescopePropagator(std::move(stepper), std::move(navigator), Acts::getDefaultLogger("Propagator", Acts::Logging::ERROR, &std::cerr));
}

}  // namespace

struct PlanePropagation::Machinery {
  TelescopePropagator propagator;
};

PlanePropagation::PlanePropagation(const TelescopeGeometry& telescope, double field_along_v_tesla)
    : m_telescope(telescope), m_machinery(new Machinery{make_propagator(telescope, field_along_v_tesla)}) {}

PlanePropagation::~PlanePropagation() = default;

std::vector<PlaneCrossing> PlanePropagation::crossings(const Acts::Vector3& start_mm, const Acts::Vector3& direction, double q_over_p_per_gev) const {
  const Acts::ParticleHypothesis hypothesis(Acts::PdgParticle::eInvalid, float(particle_mass_gev), 1.0f);
  const Acts::Vector4 start_four(start_mm.x(), start_mm.y(), start_mm.z(), 0.0);
  const auto start = Acts::BoundTrackParameters::createCurvilinear(start_four, direction, q_over_p_per_gev, std::nullopt, hypothesis);

  TelescopePropagator::Options<CollectingActors> options(m_telescope.geometry_context, m_telescope.field_context);
  auto outcome = m_machinery->propagator.propagate(start, options, false);
  if (!outcome.ok()) {
    throw std::runtime_error("propagation failed: " + outcome.error().message());
  }
  const auto& collected = outcome.value().get<PlaneCollector::result_type>().collected;

  std::vector<PlaneCrossing> crossings;
  const Acts::Surface* previous = nullptr;
  for (const Acts::SurfaceHit& hit : collected) {
    if (hit.surface == previous) {
      continue;  // the same stop reported on a following step
    }
    previous = hit.surface;
    PlaneCrossing crossing;
    crossing.plane = m_telescope.plane_number_of(*hit.surface);
    if (crossing.plane == 0) {
      throw std::runtime_error("the propagation stopped on a sensitive surface that is not a telescope plane");
    }
    auto local = hit.surface->globalToLocal(m_telescope.geometry_context, hit.position, hit.direction, on_plane_tolerance_mm);
    if (!local.ok()) {
      throw std::runtime_error("a crossing of plane " + std::to_string(crossing.plane) + " is off the plane");
    }
    crossing.loc0_mm = local.value()[0];
    crossing.loc1_mm = local.value()[1];
    crossing.phi = std::atan2(hit.direction.y(), hit.direction.x());
    crossing.theta = std::acos(hit.direction.z() / hit.direction.norm());
    crossings.push_back(crossing);
  }
  return crossings;
}

}  // namespace t07
