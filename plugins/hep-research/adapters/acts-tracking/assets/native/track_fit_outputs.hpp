// R33's per-measurement outputs of the track fit (plan R33, R37; t07-t09-task-sheets.md, T07, "Formed in plugin code"), conventions t07-r33/1.
// Header only: the refit (kalman_refit.cpp) forms them and cai_track_output_check.cpp checks them, and no CMake target changes for it.
// Data side: no generator, seed or truth code reaches this file.
//
// Conventions, t07-r33/1 (the product header names them):
//  - Frame: the measurement's local frame, loc0 along fixture u (ACTS y), loc1 along fixture v (ACTS z), normal along the telescope
//    (telescope_geometry.hpp). The measurement is (loc0, loc1); the projector H takes bound (loc0, loc1), so H x = x.head<2>().
//  - r = x_meas - x_pred (R37, the detector glossary's convention), for each state type apart (BP03):
//      predicted  r = m - H x_p, R = V + H C_p H^T   (the state before the hit)
//      filtered   r = m - H x_f, R = V - H C_f H^T   (the state with the hit)
//      smoothed   r = m - H x_s, R = V - H C_s H^T   (all hits)
//      unbiased   the hit removed from the smoothed state (Fruhwirth, the inverse Kalman step): with R_s = V - H C_s H^T,
//                 r* = V R_s^-1 r_s and R* = V R_s^-1 V. Equal to m - H x*, x* = x_s - C_s H^T R_s^-1 r_s, C* = C_s + C_s H^T R_s^-1 H C_s,
//                 and R* = V + H C* H^T. tests/adapters/test_acts_track_outputs.py holds the algebra on a hand-made example.
//    The same signs as ACTS's calculatePredictedResidual, calculateFilteredResidual and calculateSmoothedResidual (Utilities/TrackHelpers.hpp).
//  - Alignment parametrization, t07-plane-rigid/1 (R32): per plane, in its own local frame, the PlaneDelta of payload_geometry.hpp, the
//    placement route of the CAI-T07-3 probe (user's choice 16): shift-loc0, shift-loc1, shift-normal in mm, then rotation-loc0,
//    rotation-loc1, rotation-normal in rad, about the plane's local axes through its centre; moved = nominal * shift * R(normal) * R(loc1) * R(loc0).
//    Level: sensor (one plane). The derivative is dr/da with the track state held fixed: the hit stays, the fixed trajectory meets the
//    moved plane. It is taken at the smoothed state.
//  - Reference derivative (R33, "the derivatives of the residual with respect to the track parameters (local)"): dr_k/dq_ref with q_ref the bound
//    parameters (loc0, loc1, phi, theta, q/p, time) of the track's reference state, the smoothed state at its first measurement
//    (track_output.reference_state_index): dr_k/dq_ref = -H J_{k<-ref}. D1 stage 8 fix round 2: J_{k<-ref} is the propagator's transport Jacobian
//    of the smoothed reference state carried to state k's surface (KalmanRefit::reference_transports), so it is linearized at the fitted
//    trajectory. The forward filter's stored Jacobians (fix round 1) are not used: they are linearized along the filter's predicted path.
//  - Full covariance of the residuals against the smoothed states (R33, "the full covariance of the track's residuals"), over the measurement
//    states in order, in the same linearization. With no material there is no process noise, so to first order about the fitted trajectory every
//    state is x_k = x_k0 + J_k dq, dq the change of the reference state. Write D_k = -H J_k and y_k = m_k - H x_k0, so r_k = y_k + D_k dq. The fit
//    minimises (dq - p)^T Pi (dq - p) + sum_k (y_k + D_k dq)^T V_k^-1 (y_k + D_k dq), Pi the prior's information and p its centre, giving
//    dq = C_ref (Pi p - sum_j D_j^T V_j^-1 y_j), C_ref = (Pi + sum D^T V^-1 D)^-1. Fix round 3 (re-review N1): the stored formula is the covariance
//    in the fit's own model, where the prior is information on a random state, p ~ N(dq_true, Pi^-1) independent of the hits; that is the model
//    the smoother uses, and the formula's diagonal is its smoothed residual covariance. In it Cov(dq) = C_ref and Cov(dq, y_j) = -C_ref D_j^T, so
//      Cov(r_i, r_j) = V_i delta_ij + D_i Cov(dq, y_j) + Cov(y_i, dq) D_j^T + D_i C_ref D_j^T = V_i delta_ij - D_i C_ref D_j^T.
//    The refit's prior is not that: its centre is fixed by the hits themselves (KalmanRefit::start_of, a curve through the first and last hit).
//    Over hit noise alone, with a centre fixed, Cov(dq) = C_ref - C_ref Pi C_ref and the covariance gains -D_i C_ref Pi C_ref D_j^T; the centre's
//    dependence on hits 1 and 8 adds terms of the same order. Both are of relative size Pi C_ref: the prior's widths (10 mm, 0.1 rad, 1 per GeV)
//    against what eight hits fix (0.02 mm, about 1e-4 rad, 0.0041 per GeV) make it at most (0.0041 / 1)^2 = 1.7e-5, far under every check
//    (about 1e-3 standard error of the empirical one).
//    C_ref is recomputed from the D's (reference_covariance_of), not taken from the smoother, so that J and C share one linearization point.
//    Its diagonal blocks, V - D_k C_ref D_k^T, are the smoothed residual covariances in this linearization. ACTS's smoother forms its own in the
//    forward filter's linearization (GainMatrixSmoother with the stored Jacobians, each step's taken at the previous filtered state), so the two
//    differ by the change of linearization point: a residual effect, not rounding, bounded in tests/adapters/test_acts_track_outputs.py.
//  - Outliers (none in the clean fixture): a hit the fit did not use. Its filtered and smoothed states lack the hit, so R = V + H C H^T and its
//    unbiased residual is the smoothed one; the residual covariance covers measurement states only.
//  - Incidence: the local direction t (the global direction in the plane's frame); local slopes t0/tn, t1/tn; incidence angle acos|tn|.
//    Path in the sensitive volume: Surface::thickness() / |tn|. The fixture's planes have no thickness (section 4.1, no material), so it is 0.
#pragma once

#include <Acts/Definitions/Algebra.hpp>
#include <Acts/Definitions/Alignment.hpp>
#include <Acts/Definitions/TrackParametrization.hpp>
#include <Acts/Definitions/Units.hpp>
#include <Acts/Geometry/GeometryContext.hpp>
#include <Acts/Surfaces/Surface.hpp>
#include <Acts/Surfaces/detail/AlignmentHelper.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <tuple>
#include <vector>

namespace t07 {

inline constexpr char r33_conventions_name[] = "t07-r33/1";
inline constexpr char alignment_parametrization_name[] = "t07-plane-rigid/1";  // the product header names it with its frame and level
inline constexpr char alignment_frame_name[] = "local";
inline constexpr char alignment_level_name[] = "sensor";
inline constexpr std::array<const char*, 6> r32_plane_parameters{"shift-loc0", "shift-loc1", "shift-normal", "rotation-loc0", "rotation-loc1", "rotation-normal"};

struct LocalResidual {
  Acts::Vector2 value = Acts::Vector2::Zero();
  Acts::SquareMatrix2 covariance = Acts::SquareMatrix2::Zero();
};

using ResidualDerivative = Acts::Matrix<2, 6>;  // rows loc0, loc1; columns in the order of r32_plane_parameters

// r = m - H x, R = V + H C H^T for a state without the hit (predicted), V - H C H^T for a state that holds it (filtered, smoothed).
inline LocalResidual residual_of(const Acts::Vector2& measurement, const Acts::SquareMatrix2& measurement_covariance, const Acts::Vector2& projected_state,
                                 const Acts::SquareMatrix2& projected_covariance, bool state_holds_the_hit) {
  LocalResidual residual;
  residual.value = measurement - projected_state;
  residual.covariance = state_holds_the_hit ? Acts::SquareMatrix2(measurement_covariance - projected_covariance)
                                            : Acts::SquareMatrix2(measurement_covariance + projected_covariance);
  return residual;
}

// The hit removed from the smoothed state, in the residual's terms: r* = V R_s^-1 r_s, R* = V R_s^-1 V, symmetrised against rounding.
inline LocalResidual unbiased_from_smoothed(const LocalResidual& smoothed, const Acts::SquareMatrix2& measurement_covariance) {
  const Acts::SquareMatrix2 weight = smoothed.covariance.inverse();
  LocalResidual unbiased;
  unbiased.value = measurement_covariance * (weight * smoothed.value);
  const Acts::SquareMatrix2 covariance = measurement_covariance * weight * measurement_covariance;
  unbiased.covariance = 0.5 * (covariance + covariance.transpose());
  return unbiased;
}

// The plugin's closed form of dr/da in t07-plane-rigid/1, from the local position on the plane and the local direction, to first order in a:
// a shift along loc_j moves the hit's frame, dl_i = -delta_ij; along the normal the trajectory meets the plane further on, dl_i = t_i / t_n;
// a rotation about loc0 or loc1 tilts the plane under the trajectory, dl_i = t_i l1 / t_n or -t_i l0 / t_n; about the normal, dl0 = l1, dl1 = -l0.
// r = m - l, so dr = -dl. Curvature enters at second order in a only. CAI-T07-2 holds it against finite differences.
inline ResidualDerivative closed_form_residual_derivative(const Acts::Vector2& local_position, const Acts::Vector3& local_direction) {
  const double slope0 = local_direction.x() / local_direction.z();
  const double slope1 = local_direction.y() / local_direction.z();
  const double l0 = local_position.x();
  const double l1 = local_position.y();
  ResidualDerivative local_change;
  local_change << -1.0, 0.0, slope0, slope0 * l1, -slope0 * l0, l1,  //
      0.0, -1.0, slope1, slope1 * l1, -slope1 * l0, -l0;
  return -local_change;
}

// The free vector's derivative along the path that alignmentToBoundDerivative takes (Surface.hpp: "the derivative of free parameters w.r.t.
// path length"): position T, time 1/beta, direction (q/p) T x B with B along ACTS z (section 4.1, field along fixture v), q/p constant.
inline Acts::FreeVector path_derivative_of(const Acts::Vector3& direction, double q_over_p_per_gev, double field_along_v_tesla, double mass_gev) {
  Acts::FreeVector derivative = Acts::FreeVector::Zero();
  derivative.segment<3>(Acts::eFreePos0) = direction;
  derivative[Acts::eFreeTime] = std::sqrt(1.0 + mass_gev * mass_gev * q_over_p_per_gev * q_over_p_per_gev);  // charge magnitude 1
  derivative.segment<3>(Acts::eFreeDir0) = q_over_p_per_gev * direction.cross(Acts::Vector3(0.0, 0.0, field_along_v_tesla * Acts::UnitConstants::T));
  return derivative;
}

// ACTS's alignment parameters (Definitions/Alignment.hpp): the centre in global Cartesian coordinates, then three rotation parameters, whose
// meaning ACTS gives as derivatives of the local axes (Surfaces/detail/AlignmentHelper.hpp, rotationToLocalAxesDerivative: "Derivative of
// local frame x/y/z axis vector w.r.t. its rotation angles (extrinsic Euler angles) around local x/y/z axis"). This is d(ACTS parameters) /
// d(t07-plane-rigid/1), read from that helper and not from a stated convention: each ACTS rotation parameter j turns the axes rigidly,
// d axis_i / d theta_j = omega_j x axis_i, so omega_j = 1/2 sum_i axis_i x (d axis_i / d theta_j); the plugin's rotation about local axis k
// is omega = R e_k, so d theta / d(rotation_k) = Omega^-1 R e_k. A shift s in the local frame moves the centre by R s. Columns of each helper
// matrix are read as the derivatives by angle; rigidity_error says how far that reading is from a rigid rotation (0 up to rounding).
struct ActsAlignmentMap {
  Acts::SquareMatrix<6> acts_per_plane_delta = Acts::SquareMatrix<6>::Zero();
  double rigidity_error = 0.0;
};

inline ActsAlignmentMap acts_alignment_map(const Acts::RotationMatrix3& rotation) {
  const auto [d_axis0, d_axis1, d_axis2] = Acts::detail::rotationToLocalAxesDerivative(rotation);
  const std::array<Acts::RotationMatrix3, 3> d_axes{d_axis0, d_axis1, d_axis2};
  Acts::SquareMatrix3 omega;
  for (int angle = 0; angle < 3; ++angle) {
    Acts::Vector3 sum = Acts::Vector3::Zero();
    for (int axis = 0; axis < 3; ++axis) {
      sum += rotation.col(axis).cross(d_axes[axis].col(angle));
    }
    omega.col(angle) = 0.5 * sum;
  }
  ActsAlignmentMap map;
  for (int angle = 0; angle < 3; ++angle) {
    for (int axis = 0; axis < 3; ++axis) {
      map.rigidity_error = std::max(map.rigidity_error, (omega.col(angle).cross(rotation.col(axis)) - d_axes[axis].col(angle)).cwiseAbs().maxCoeff());
    }
  }
  map.acts_per_plane_delta.block<3, 3>(Acts::eAlignmentCenter0, 0) = rotation;
  map.acts_per_plane_delta.block<3, 3>(Acts::eAlignmentRotation0, 3) = omega.inverse() * rotation;
  return map;
}

// dr/da in t07-plane-rigid/1 from ACTS: alignmentToBoundDerivative with the path correction (Surface.hpp; the correction comes in through
// path_derivative, as the header describes), its loc0 and loc1 rows, mapped by acts_alignment_map, and r = m - l gives the sign.
inline ResidualDerivative acts_residual_derivative(const Acts::Surface& surface, const Acts::GeometryContext& context, const Acts::Vector3& position,
                                                   const Acts::Vector3& direction, const Acts::FreeVector& path_derivative) {
  const Acts::AlignmentToBoundMatrix to_bound = surface.alignmentToBoundDerivative(context, position, direction, path_derivative);
  const ActsAlignmentMap map = acts_alignment_map(surface.localToGlobalTransform(context).linear());
  const Acts::Matrix<2, 6> local_rows = to_bound.topRows<2>();
  return -(local_rows * map.acts_per_plane_delta);
}

using ReferenceDerivative = Acts::Matrix<2, 6>;  // rows loc0, loc1; columns the reference state's bound parameters

// -H J_{k<-ref}: H takes loc0 and loc1, so the rows are J's first two, with the sign of r = m - x.
inline ReferenceDerivative reference_derivative_of(const Acts::BoundMatrix& transport) { return -transport.topRows<2>(); }

// C_ref in the same linearization as the D's: (Pi + sum_k D_k^T V_k^-1 D_k)^-1, Pi the inverse of the prior as the fit carried it to the reference
// (its predicted covariance there). The prior is wide, so its own linearization point does not matter; the time column of every D is zero, so C's
// time block is the prior's and enters no residual.
inline Acts::BoundMatrix reference_covariance_of(const std::vector<ReferenceDerivative>& derivatives, const std::vector<Acts::SquareMatrix2>& measurement_covariances,
                                                 const Acts::BoundMatrix& prior_at_reference) {
  Acts::BoundMatrix information = prior_at_reference.inverse();
  for (std::size_t index = 0; index < derivatives.size(); ++index) {
    information += derivatives[index].transpose() * measurement_covariances[index].inverse() * derivatives[index];
  }
  const Acts::BoundMatrix covariance = information.inverse();
  return 0.5 * (covariance + covariance.transpose());
}

// Cov(r_i, r_j) = V_i delta_ij - D_i C_ref D_j^T over the measurements in order, loc0 then loc1 of each.
inline Acts::DynamicMatrix residual_covariance_of(const std::vector<ReferenceDerivative>& derivatives, const std::vector<Acts::SquareMatrix2>& measurement_covariances,
                                                  const Acts::BoundMatrix& reference_covariance) {
  const Eigen::Index size = Eigen::Index(2 * derivatives.size());
  Acts::DynamicMatrix stacked(size, 6);
  Acts::DynamicMatrix covariance = Acts::DynamicMatrix::Zero(size, size);
  for (std::size_t index = 0; index < derivatives.size(); ++index) {
    stacked.block(Eigen::Index(2 * index), 0, 2, 6) = derivatives[index];
    covariance.block(Eigen::Index(2 * index), Eigen::Index(2 * index), 2, 2) = measurement_covariances[index];
  }
  covariance -= stacked * reference_covariance * stacked.transpose();
  return 0.5 * (covariance + covariance.transpose());
}

struct Incidence {
  Acts::Vector3 local_direction = Acts::Vector3::Zero();
  std::array<double, 2> local_slope{};
  double angle_rad = 0.0;
  double path_factor = 0.0;
};

inline Incidence incidence_of(const Acts::RotationMatrix3& rotation, const Acts::Vector3& direction) {
  Incidence incidence;
  incidence.local_direction = rotation.transpose() * direction;
  const double normal = incidence.local_direction.z();
  incidence.local_slope = {incidence.local_direction.x() / normal, incidence.local_direction.y() / normal};
  incidence.angle_rad = std::acos(std::min(1.0, std::abs(normal)));
  incidence.path_factor = 1.0 / std::abs(normal);
  return incidence;
}

}  // namespace t07
