// Pattern recognition of recipe reco.track.acts-ckf-planar/1 (t04-values-v4.md section 8.1): seeds from the hits, the ACTS combinatorial Kalman
// filter, greedy ambiguity resolution, and a Kalman fit of each selected hit set. Data side: it reads hits and what section 4.1 states of the
// telescope, and nothing here may reach truth, a generator or seed code. A truth-seeded run is not this recipe's output and has no route here.
//
// Every number below is development configuration and belongs to Freeze B (section 2.2, Configuration and Algorithmic budgets). None comes from
// a pull or a T08 target, or from any run: each is section 4.1 or 7, or arithmetic on them, as its comment says.
#pragma once

#include <Acts/Definitions/Algebra.hpp>
#include <Acts/Definitions/TrackParametrization.hpp>

#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "kalman_refit.hpp"
#include "t07_data_file.hpp"
#include "telescope_geometry.hpp"

namespace t07 {

struct SeedPlanes {
  int first = 0;
  int middle = 0;
  int last = 0;
};

// Any two lost planes leave one of these whole, so a track with 6 of 8 hits, section 7's reconstructable track, always has a seed, whichever
// two it lost. Four is the fewest that do it, and these have the smallest doublet and middle windows of the four-triple sets, so the fewest
// chance triples on section 4.1's noise (exhaustive search over the 56 triples). Upstream first, so that the track found first starts earliest.
inline constexpr std::array<SeedPlanes, 4> seed_plane_triples{{{1, 2, 3}, {1, 2, 4}, {3, 4, 5}, {6, 7, 8}}};
// Section 4.1: lowest bin edge 1.5 GeV, so a curvature of at most k B / p = 2e-4 per mm.
inline constexpr double seed_lowest_momentum_gev = 1.5;
// Section 4.1: vertex slopes up to 0.15, plus the bend k B L / p = 0.09 over the 450 mm to plane 8, and 0.15 / cos(0.24) along v.
inline constexpr double seed_largest_slope_u = 0.25;
inline constexpr double seed_largest_slope_v = 0.16;
// Hit noise allowed around a triple's interpolation, in the sigma of that interpolation: two-sided 5.7e-7 per coordinate, so no triple of true
// hits is lost to this cut at any size this fixture reaches.
inline constexpr double seed_window_sigma = 5.0;
// A seed starts on the helix through its three hits, with the covariance of that start from the hits' own errors (seed_start_of). Both are needed.
// ACTS makes a hole only when no hit passes, so on a plane where a track lost its hit a foreign hit inside the window is taken with no hole beside
// it and drags the track off: a diagonal prior's window of 30 to 300 mm^2 at plane 1 cost job 7493849 1 to 2 % of noise-fixture tracks (D1 stage 5
// report, Fix round 1). And a correlated prior holds only about a centre on the track: job 7494285's, a parabola, missed a 6-7-8 seed's own hits by
// up to 0.5 mm at 1.5 GeV where the prior allows 0.03 mm, and left out the factor between curvature and q/p (Fix round 2).
// The inflation: the filter meets the seed's hits a second time, which shrinks the covariance, so a true hit can fail the cut. In a linear model 1.5
// refuses as often as the diagonal did, 0.14 % of 1-2-3 seeds against 0.13 %, a rate job 7493849's clean fixture shows to be harmless; 1 refuses
// four times as often, and 2 widens every window by 1.8 in area.
inline constexpr double seed_prior_inflation = 1.5;
// Chi2 of a hit against a prediction, two coordinates: exp(-16 / 2) = 3.4e-4 of true hits lost per plane, and at the converged prediction a
// radius near 0.11 mm, inside the 0.15 mm circle of section 4.1's p_w. The same value bounds outliers, so no hit above the cut joins a track.
inline constexpr double finding_chi2_cut = 16.0;
// Section 7: reconstructable means at least 6 hits on distinct planes, of 8. So a branch with 3 holes cannot reach 6 and stops.
inline constexpr std::size_t finding_least_measurements = 6;
inline constexpr unsigned int finding_most_holes = 2;
// Budgets (K10). The widest window, 6-7-8 at plane 1, is about 9 mm^2, so about 0.5 hits at o3 where tracks fan out at 0.04 per mm^2 over 0.0115 of
// noise: 16 per surface leaves an honest event far from the limit, and 32 per seed likewise, so a mark means something. A seed reaching either
// limit is marked search-truncated. Correction: with the diagonal prior this comment gave a tail of 1e-7 from noise alone, leaving out the fan;
// job 7493849 reached the limits in 43 % of o3 noise events.
inline constexpr std::size_t finding_most_branches_per_surface = 16;
inline constexpr std::size_t finding_most_branches_per_seed = 32;
// 336 chance triples are expected per event at o3, closed form (tests/adapters/test_acts_finding.py), so this is thirty times that.
inline constexpr std::size_t finding_most_seeds_per_event = 10000;
// 32 branches of at most nine legs of a few steps stay under 1,000, so this never binds before the branch budget: a guard against a loop.
inline constexpr unsigned int finding_most_propagator_steps = 10000;
// Two tracks of one particle hold at least 4 of its hits each (section 7, more than 50 % of at least 6) of at most 8, so with 6-hit tracks
// sharing at most one hit, a duplicate needs noise on most planes. ACTS's default.
inline constexpr std::uint32_t ambiguity_most_shared_hits = 1;
// ACTS's default: each iteration evicts one candidate, and an o3 event holds far fewer. Reaching it is marked search-truncated.
inline constexpr std::uint32_t ambiguity_most_iterations = 1000;

// Where a seed's search starts: at x = refit_start_x_mm, upstream of plane 1, so that the filter reaches every plane.
struct SeedStart {
  Acts::Vector3 position_mm;
  Acts::Vector3 direction;
  double q_over_p = 0.0;
  Acts::BoundMatrix covariance = Acts::BoundMatrix::Zero();
};
// From three points on planes, along the track. Empty for a seed with no usable helix, which is counted as failed.
std::optional<SeedStart> seed_start_of(const std::array<Acts::Vector3, 3>& points, double sigma_loc0_mm, double sigma_loc1_mm, double field_along_v_tesla);

struct HitTriple {
  SeedPlanes planes;
  std::array<std::uint32_t, 3> hit_keys{};
};

struct SeedSearch {
  std::vector<HitTriple> triples;
  bool reached_budget = false;
};

// Triples of hits compatible with a track of section 4.1: a pair inside the slope window, a middle hit inside the curvature window. Hits only.
SeedSearch find_seeds(const DataEvent& event, double hit_sigma_mm, double field_along_v_tesla);

// A branch that survived the search. Outcome: selected, evicted by ambiguity resolution, or fit-failed. t04-prereg.md's failure classes.
struct FoundCandidate {
  std::string key;
  SeedPlanes seed_planes;
  std::string outcome;
  std::string failure_category;  // none, ambiguity or fit
  bool search_truncated = false;
  std::int32_t measurements = 0;
  std::int32_t holes = 0;
  double search_chi2 = 0.0;  // the filter's, with the seed's prior: for ambiguity resolution only
  double q_over_p = 0.0;     // the filter's last value
  double fit_chi2 = 0.0;     // of the selected hit set's own fit
  std::int32_t fit_coordinates = 0;
  std::vector<std::uint32_t> hit_keys;  // along the track
};

struct EventFinding {
  std::uint32_t event_ordinal = 0;
  std::size_t hit_count = 0;
  std::size_t seeds_found = 0;
  std::size_t seeds_run = 0;
  std::size_t seeds_skipped = 0;   // all three hits already on one candidate
  std::size_t seeds_failed = 0;    // no usable estimate, or the filter returned an error
  std::size_t seeds_without_candidate = 0;
  std::size_t seeds_truncated = 0;
  bool seed_budget_reached = false;
  bool ambiguity_budget_reached = false;
  std::string failure_category;  // none, seed-or-finding, search-truncated: of an event with no selected track
  std::vector<FoundCandidate> candidates;
  std::vector<RefitResult> fits;  // of the selected candidates that were fitted

  bool search_truncated() const { return seed_budget_reached || ambiguity_budget_reached || seeds_truncated > 0; }
};

// Every limit and cut, by name: BP03, "All seed/branch/resource limits enter the effective configuration".
std::vector<std::pair<std::string, std::string>> effective_configuration();

class TrackFinder {
 public:
  TrackFinder(const TelescopeGeometry& telescope, double field_along_v_tesla, double sigma_loc0_mm, double sigma_loc1_mm);
  ~TrackFinder();

  EventFinding find(const DataEvent& event, std::uint32_t event_ordinal) const;

 private:
  struct Machinery;
  const TelescopeGeometry& m_telescope;
  double m_field_along_v_tesla;
  double m_sigma_loc0_mm;
  double m_sigma_loc1_mm;
  KalmanRefit m_fitter;
  std::unique_ptr<Machinery> m_machinery;
};

}  // namespace t07
