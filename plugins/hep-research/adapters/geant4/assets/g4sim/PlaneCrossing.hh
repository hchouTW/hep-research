// g4sim/PlaneCrossing.hh: where a step crosses a plane of constant z, and in which direction (g4sim plan, Section 6.3). No Geant4 here, so it can be tested against a helix.
//
// A step in a field curves, so a chord is off by its sagitta. When the step ends smoothly, a cubic Hermite curve through its two ends with their directions follows the path to fourth order in
// its length, and is the chord when the two directions agree. A step ended by a discrete process has a post-step direction that belongs after the kink, so the caller passes `smooth` false and gets the chord.
#ifndef G4SIM_PLANECROSSING_HH
#define G4SIM_PLANECROSSING_HH

#include <array>
#include <cmath>

namespace g4sim {

using Vector3 = std::array<double, 3>;

struct PlaneCrossing {
  double fraction = 0.;  // of the step, in the curve's parameter
  Vector3 position{}, direction{};
};

// Whether a step from z offset `before` to `after` crosses: arriving exactly on the plane counts, and leaving it does not, so a track is not counted twice and a track born on the plane is not counted.
inline bool StepCrosses(double before, double after) { return before * after < 0. || (after == 0. && before != 0.); }

inline PlaneCrossing CrossingOf(const Vector3& from, const Vector3& start, const Vector3& to, const Vector3& end, double length, double z, bool smooth) {
  Vector3 first = start, last = end;
  if (!smooth)
    for (int i = 0; i < 3; ++i) first[i] = last[i] = length > 0. ? (to[i] - from[i]) / length : 0.;
  const auto point = [&](double s, int i) {
    const double s2 = s * s, s3 = s2 * s;
    return (2 * s3 - 3 * s2 + 1) * from[i] + (s3 - 2 * s2 + s) * length * first[i] + (3 * s2 - 2 * s3) * to[i] + (s3 - s2) * length * last[i];
  };
  const double rising = to[2] >= from[2] ? 1. : -1.;
  double low = 0., high = 1.;
  for (int round = 0; round < 60; ++round) {
    const double middle = 0.5 * (low + high);
    (rising * (point(middle, 2) - z) < 0. ? low : high) = middle;
  }
  PlaneCrossing out;
  out.fraction = 0.5 * (low + high);
  const double s = out.fraction, s2 = s * s;
  double size = 0.;
  for (int i = 0; i < 3; ++i) {
    out.position[i] = point(s, i);
    out.direction[i] = (6 * s2 - 6 * s) * from[i] + (3 * s2 - 4 * s + 1) * length * first[i] + (6 * s - 6 * s2) * to[i] + (3 * s2 - 2 * s) * length * last[i];
    size += out.direction[i] * out.direction[i];
  }
  size = std::sqrt(size);
  for (int i = 0; i < 3; ++i) out.direction[i] = size > 0. ? out.direction[i] / size : first[i];
  out.position[2] = z;
  return out;
}

}  // namespace g4sim

#endif
