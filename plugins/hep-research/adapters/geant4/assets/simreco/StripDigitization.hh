// Strip digitization, shared by simreco's noise-digitization tail and by simreco_strip, the program registered as
// `simreco-strip` for stage 5 of the g4sim response pipeline. Standard library only.
#ifndef SIMRECO_STRIPDIGITIZATION_HH
#define SIMRECO_STRIPDIGITIZATION_HH

#include <algorithm>
#include <cmath>

// simreco's resolution of the strip digitization, kept as it is because the J15 results rest on it. It takes the
// charge-weighted position inside the sharing band to be exact, sigma^2 = (p - w)^3 / (12 p), which StripCluster does
// not do: it is smaller than the true scatter, by sqrt(p / (p - w)) at zero threshold. StripClusterSigma is the true one.
inline double StripSigma(double pitch, double sharing) {
  double q = std::max(pitch - std::min(sharing, pitch), 0.0);
  return std::sqrt(q * q * q / (12.0 * pitch));
}

// The RMS error of StripCluster for a crossing uniform over the strip. Where both strips stay above threshold the
// cluster runs from t p off the strip centre to the boundary while the crossing moves over w (1/2 - t), so the error
// falls linearly from (p - w) (1/2 - t) to 0; elsewhere the cluster sits at the centre of a span L = p - w (1 - 2 t).
inline double StripClusterSigma(double pitch, double sharing, double threshold) {
  const double w = std::min(sharing, pitch), t = std::min(std::max(threshold, 0.0), 0.5);
  const double span = pitch - w * (1 - 2 * t), largest = (pitch - w) * (0.5 - t);
  return std::sqrt(span * span * span / (12.0 * pitch) + w * (1 - 2 * t) / pitch * largest * largest / 3.0);
}

// The cluster position of a crossing at u on a grid of the given pitch starting at centre: two strips share the
// charge linearly within the sharing width around a strip boundary, and a strip below threshold drops out.
inline double StripCluster(double u, double centre, double pitch, double sharing, double threshold) {
  double rel = (u - centre) / pitch;
  double strip = std::floor(rel);
  double f = rel - strip;  // position within the strip, [0, 1)
  double w = sharing / pitch;
  double q0 = 1, q1 = 0, nb = strip + 1;
  if (f > 1 - w / 2) {
    q1 = (f - (1 - w / 2)) / w;
    q0 = 1 - q1;
  } else if (f < w / 2) {
    q1 = (w / 2 - f) / w;
    q0 = 1 - q1;
    nb = strip - 1;
  }
  double c0 = centre + (strip + 0.5) * pitch, c1 = centre + (nb + 0.5) * pitch;
  bool k0 = q0 >= threshold, k1 = q1 >= threshold;
  if (!k0 && !k1) return c0;
  double sq = (k0 ? q0 : 0) + (k1 ? q1 : 0);
  return ((k0 ? q0 * c0 : 0) + (k1 ? q1 * c1 : 0)) / sq;
}

#endif
