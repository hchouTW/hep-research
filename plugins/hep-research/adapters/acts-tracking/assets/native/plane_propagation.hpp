// One propagation through the telescope with the ACTS propagator: EigenStepper, Navigator and a constant field along
// ACTS z (fixture v, so u bends), as the sheet names them. Used by the generator and the self-test.
#pragma once

#include <Acts/Definitions/Algebra.hpp>

#include <memory>
#include <vector>

#include "telescope_geometry.hpp"

namespace t07 {

struct PlaneCrossing {
  int plane = 0;  // 1..8
  double loc0_mm = 0.0;
  double loc1_mm = 0.0;
  double phi = 0.0;
  double theta = 0.0;
};

class PlanePropagation {
 public:
  PlanePropagation(const TelescopeGeometry& telescope, double field_along_v_tesla);
  ~PlanePropagation();

  // The crossings in order along the track. Throws when the propagation fails.
  std::vector<PlaneCrossing> crossings(const Acts::Vector3& start_mm, const Acts::Vector3& direction, double q_over_p_per_gev) const;

 private:
  struct Machinery;
  const TelescopeGeometry& m_telescope;
  std::unique_ptr<Machinery> m_machinery;
};

}  // namespace t07
