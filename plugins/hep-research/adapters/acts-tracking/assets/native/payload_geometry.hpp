// Two ways an alignment payload can reach the telescope, for CAI-T07-3 (plan R33, R37; t07-t09-task-sheets.md, T07 open items). Both
// give an ordinary TelescopeGeometry, which KalmanRefit and PlanePropagation take as they are, so neither touches
// telescope_geometry.*: nominal plane positions are read from build_telescope_geometry() at run time, not written again here.
//
//  - PlacedTelescope, the route judged right: each plane is a surface owned by an Acts::SurfacePlacementBase, whose transform comes
//    from the Acts::GeometryContext. One build serves every payload; a payload is a context. Acts/Surfaces/SurfacePlacementBase.hpp
//    documents this as the way to let a sensor surface float. A plain surface ignores the context, so the context alone does nothing.
//  - rebuild_moved_telescope, the fallback: plain surfaces at the moved transforms, a new tracking geometry per payload. It uses only
//    the calls job 7490165 ran. Its surfaces are new objects each time.
//
// Data side: no generator code reaches this file (tests/adapters/test_acts_tracking.py). A delta here is the probe's parametrization
// of one plane in its own local frame; the mapping from a conditions payload (R32) to it is a later stage.
#pragma once

#include <Acts/Definitions/Algebra.hpp>

#include <array>
#include <memory>

#include "t07_fixture_constants.hpp"
#include "telescope_geometry.hpp"

namespace t07 {

// In the plane's local frame: shifts first, then rotations about the local axes, in radians. loc0, loc1 span the plane; normal is the
// third axis. moved = nominal * shift * R(normal) * R(loc1) * R(loc0).
struct PlaneDelta {
  double shift_loc0_mm = 0.0;
  double shift_loc1_mm = 0.0;
  double shift_normal_mm = 0.0;
  double rotation_loc0 = 0.0;
  double rotation_loc1 = 0.0;
  double rotation_normal = 0.0;
};

using PlaneDeltas = std::array<PlaneDelta, plane_count>;  // [0] is plane 1

Acts::Transform3 moved_plane_transform(const Acts::Transform3& nominal, const PlaneDelta& delta);

// Fallback route: a new tracking geometry with its planes moved.
TelescopeGeometry rebuild_moved_telescope(const PlaneDeltas& deltas);

// Placement route. After construction a context that holds no plane transforms is refused, by std::logic_error from the placement,
// so no call can read a nominal plane by forgetting its payload.
class PlacedTelescope {
 public:
  PlacedTelescope();
  ~PlacedTelescope();

  // The same surfaces and tracking geometry under the context of these deltas. Valid while this object lives.
  TelescopeGeometry with_deltas(const PlaneDeltas& deltas) const;

 private:
  struct Planes;
  std::unique_ptr<Planes> m_planes;
};

}  // namespace t07
