// Vertexing of recipe reco.vertex.acts-amvf/1 (t04-values-v4.md section 8.1; t07-t09-task-sheets.md, T07): ACTS's adaptive multi-vertex finder on the tracks the
// finder delivered, after ambiguity resolution and the fit. Data side: it reads the fitted tracks' smoothed states and what section 4.1 states of the telescope, and
// nothing here may reach truth, a generator or seed code. Only acts_tracking_finder compiles it (CMakeLists.txt), and only when --vertex-recipe asks for it.
//
// What the installed 48.2.0 headers require (Acts/Vertexing/, read in full; D1 stage 7 report):
// - AdaptiveMultiVertexFinder is not a template. Its fitter is AdaptiveMultiVertexFitter, fixed by "using VertexFitter = AdaptiveMultiVertexFitter;" in
//   AdaptiveMultiVertexFinder.hpp: the sheet's FullBilloirVertexFitter is not what this finder uses, and it is not used here.
// - The fitter linearizes through a TrackLinearizer delegate, here HelicalTrackLinearizer, which propagates with a BasePropagator to a perigee whose transverse
//   plane is the global x-y plane, so the field is taken along global z. Section 4.1's field is along fixture v, which is ACTS z [R14].
// - The seed finder is any IVertexFinder. TrackDensityVertexFinder with GaussianTrackDensity, the density of the tracks' d0 and z0 along global z, is the one
//   section 8.5 names ("models tracks by d0/z0 and finds a z seed"). It reads loc0 and loc1 of each track's parameters as d0 and z0, and the finder cuts on the
//   z of each track's position (tracksMaxZinterval), so every track is handed over as perigee parameters about one line along ACTS z.
// - That line: x = vertex_reference_x_mm, y = vertex_reference_y_mm, the nominal fixture z and u of section 4.1's vertex rows ("nominal u, z is a design
//   constant for a perigee reference, not per-event truth"). TrackDensityVertexFinder places its seed at the constraint's position plus z (libActsCore, read
//   at TrackDensityVertexFinder::find: fullPosition() + (0, 0, z, 0), and the z width taken only into a non-zero constraint covariance), so the same point is
//   the constraint's position, with zero covariance. useConstraintInFit is false: no beam constraint enters any fit (section 4.1, Beam constraint: none, BP04).
//
// Every number is development configuration for Freeze B (section 2.2) and enters vertex_configuration(), hashed into the record. All are ACTS's defaults except
// the reference point, which is section 4.1's nominal, and initialVariances (vertex_initial_variance, below, stage 7b); none comes from a pull or a gate.
#pragma once

#include <array>
#include <cstddef>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "kalman_refit.hpp"
#include "telescope_geometry.hpp"

namespace t07 {

inline constexpr char vertex_recipe[] = "reco.vertex.acts-amvf/1";
// Section 4.1, Vertex position: fixture z uniform -100 +- 0.2 mm and u uniform +- 0.05 mm, so the nominal is z -100, u 0, which is ACTS x -100, y 0. The
// line runs along ACTS z (fixture v), through z = 0, so a track's z0 about it is its global z there.
inline constexpr double vertex_reference_x_mm = -100.0;
inline constexpr double vertex_reference_y_mm = 0.0;
inline constexpr double vertex_reference_z_mm = 0.0;
// AdaptiveMultiVertexFinder::Config::initialVariances, all four components, in mm^2 (and the time unit squared): the prior every fit starts from, since no fit
// constraint is used. ACTS's default 1e8 is lost to rounding in KalmanVertexUpdater, which inverts the vertex covariance to a weight and back with Eigen's
// cofactor 3x3 inverse at every track: job 7522969 returned non-positive-definite covariances in 11.6 % of 3-track vertices (D1 stage 7 reading). At 1e4
// (sigma 100 mm) the condition after one track is about 3e7 rather than 3e11, and a numerical copy of the update equals the batch fit to 7e-8. Still loose:
// 100 mm against a vertex region of at most 30 mm, and a weight of 1e-4 per mm^2 against track weights of about 3e3 per mm^2 across the tracks (y, z: about
// 3e-8 of the information), and along them (x) against about 2.2 to 50 per mm^2 at 3 tracks, so 2e-6 to 4.5e-5 (D1 stage 7b review m4), so it is no constraint (none
// enters any fit). A development value for Freeze B, chosen for the numerics, not against a gate (decisions.md, "Stage 7: results").
inline constexpr double vertex_initial_variance = 1e4;

struct VertexTrack {
  std::string track_key;  // the candidate key of a selected track of this event
  double weight = 0.0;    // TrackAtVertex::trackWeight
  double chi2 = 0.0;      // TrackAtVertex::chi2Track
  double compatibility = 0.0;  // TrackAtVertex::vertexCompatibility
};

struct FoundVertex {
  std::array<double, 3> position_mm{};  // global ACTS x, y, z
  std::array<double, 6> covariance{};   // xx, xy, xz, yy, yz, zz
  double chi2 = 0.0;
  double ndf = 0.0;  // not an integer: annealing weights enter it
  std::vector<VertexTrack> tracks;  // in ACTS's order
};

struct EventVertices {
  std::string status = "ok";  // ok, or failed: ACTS returned an error or a non-finite number, and the event keeps no vertex
  std::string failure;        // why, for a failed event: ACTS's own message; the finder prints it with the event (D1 stage 7b)
  std::size_t input_tracks = 0;        // tracks handed to the finder
  std::size_t unconverted_tracks = 0;  // fitted tracks whose state could not be carried to the reference line: not handed over, and counted here
  std::vector<FoundVertex> vertices;
};

class TrackVertexer {
 public:
  TrackVertexer(const TelescopeGeometry& telescope, double field_along_v_tesla);
  ~TrackVertexer();

  // The tracks are the fits the finder delivered, in its order. Each enters through its first smoothed state, carried to the reference line.
  EventVertices vertex(const std::vector<RefitResult>& fits) const;

  // Every configuration value, by name, read from the configuration objects the finder was built with.
  const std::vector<std::pair<std::string, std::string>>& configuration() const;

 private:
  struct Machinery;
  const TelescopeGeometry& m_telescope;
  std::unique_ptr<Machinery> m_machinery;
};

}  // namespace t07
