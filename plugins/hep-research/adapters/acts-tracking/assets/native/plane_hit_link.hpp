// A hit as ACTS sees it: the measurement travels inside the source link, as Acts/EventData/detail/TestSourceLink.hpp does it. Shared by the
// refit (kalman_refit.cpp) and the finder (track_finding.cpp), so both read a hit by one path.
#pragma once

#include <Acts/Definitions/Algebra.hpp>
#include <Acts/Definitions/TrackParametrization.hpp>
#include <Acts/EventData/SourceLink.hpp>
#include <Acts/EventData/VectorMultiTrajectory.hpp>
#include <Acts/Geometry/GeometryContext.hpp>
#include <Acts/Surfaces/Surface.hpp>
#include <Acts/Utilities/CalibrationContext.hpp>

#include <array>
#include <cstdint>

namespace t07 {

struct PlaneHitLink {
  std::uint32_t hit_key = 0;
  const Acts::Surface* surface = nullptr;
  double loc0_mm = 0.0;
  double loc1_mm = 0.0;
  double variance0_mm2 = 0.0;
  double variance1_mm2 = 0.0;
};

inline const Acts::Surface* surface_of_link(const Acts::SourceLink& source_link) { return source_link.get<PlaneHitLink>().surface; }

inline void calibrate_plane_hit(const Acts::GeometryContext& /*geometry_context*/, const Acts::CalibrationContext& /*calibration_context*/,
                                const Acts::SourceLink& source_link, Acts::VectorMultiTrajectory::TrackStateProxy track_state) {
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

}  // namespace t07
