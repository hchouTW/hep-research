// The planar telescope of t04-values-v4.md section 4.1 as an ACTS tracking geometry, built through
// Acts/Geometry/CuboidVolumeBuilder.hpp (t07-t09-task-sheets.md, ACTS interfaces). Fixture and generator use this one
// geometry. Local frame of a plane: loc0 along ACTS y (fixture u), loc1 along ACTS z (fixture v), normal along ACTS x.
#pragma once

#include <Acts/Definitions/Algebra.hpp>
#include <Acts/Geometry/GeometryContext.hpp>
#include <Acts/Geometry/TrackingGeometry.hpp>
#include <Acts/MagneticField/MagneticFieldContext.hpp>
#include <Acts/Surfaces/Surface.hpp>
#include <Acts/Utilities/CalibrationContext.hpp>

#include <memory>
#include <vector>

namespace t07 {

struct TelescopeGeometry {
  Acts::GeometryContext geometry_context = Acts::GeometryContext::dangerouslyDefaultConstruct();
  Acts::MagneticFieldContext field_context{};
  Acts::CalibrationContext calibration_context{};
  std::shared_ptr<const Acts::TrackingGeometry> tracking_geometry;
  std::vector<std::shared_ptr<const Acts::Surface>> planes;  // planes[0] is plane 1, at z = 0

  // 1..8, or 0 for a surface that is not a telescope plane.
  int plane_number_of(const Acts::Surface& surface) const;
};

TelescopeGeometry build_telescope_geometry();

}  // namespace t07
