// g4sim_digi/Samplers.hh: sub-streams and the sampling algorithms of the response pipeline in C++ (g4sim plan, Section 10.2, S8). No Geant4.
//
// core/simulation/rng.py is normative, and this follows it operation by operation, in the same order of floating-point operations, so that a
// draw agrees with Python bit for bit wherever the C library agrees with Python's math module. Keys are not derived here: the job carries the
// two key words of every stream, computed in Python with canonical/1 (Philox.hh). Each draw, and each attempt of a rejection sampler, starts
// a new output group; an attempt that needs more than two variates takes consecutive groups.
//
// Sampling algorithms, as rng.py cites them: Box-Muller (one output); exponential -ln u; Poisson by the inverse transform below a mean of 30,
// else PTRS (Hormann 1993); binomial by the inverse transform below n p = 30, else BTPE (Kachitvichyanukul and Schmeiser 1988, with the sign
// correction of its final test); the multinomial as successive conditional binomials; Gamma by Marsaglia and Tsang (2000).
//
// Python's math.lgamma is CPython's own Lanczos approximation, not the C library's lgamma (on glibc the two differ in about 45% of values),
// so LogGamma below is CPython 3.13.2's m_lgamma for positive arguments (Modules/mathmodule.c, lanczos_sum and m_lgamma), adapted under the
// Python Software Foundation License (assets/PYTHON-LICENSE.txt): Copyright (c) 2001-2024 Python Software Foundation; All Rights Reserved.
// The constants and steps of PTRS and BTPE follow rng.py, which read them from NumPy's distributions.c (BSD licence, NumPy developers).
// Compile with -ffp-contract=off and without -ffast-math.
#pragma once

#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

#include "Philox.hh"

namespace g4sim {

struct StreamError : std::runtime_error {
  StreamError(const std::string& code, const std::string& message) : std::runtime_error(code + ": " + message), code(code) {}
  std::string code;
};

struct StreamKey {
  std::uint32_t word0 = 0, word1 = 0;
};

constexpr std::uint32_t kGroupsPerSubStream = 1u << 16;
constexpr std::uint64_t kEventLimit = 1ull << 32;
constexpr double kInverseLimit = 30.0;

// CPython 3.13.2, Modules/mathmodule.c: lanczos_sum and m_lgamma (positive arguments only)
namespace cpython {
constexpr int kLanczosN = 13;
constexpr double kLanczosG = 6.024680040776729583740234375;
constexpr double kLanczosNum[kLanczosN] = {
    23531376880.410759688572007674451636754734846804940, 42919803642.649098768957899047001988850926355848959,
    35711959237.355668049440185451547166705960488635843, 17921034426.037209699919755754458931112671403265390,
    6039542586.3520280050642916443072979210699388420708, 1439720407.3117216736632230727949123939715485786772,
    248874557.86205415651146038641322942321632125127801, 31426415.585400194380614231628318205362874684987640,
    2876370.6289353724412254090516208496135991145378768, 186056.26539522349504029498971604569928220784236328,
    8071.6720023658162106380029022722506138218516325024, 210.82427775157934587250973392071336271166969580291,
    2.5066282746310002701649081771338373386264310793408};
constexpr double kLanczosDen[kLanczosN] = {0.0, 39916800.0, 120543840.0, 150917976.0, 105258076.0, 45995730.0, 13339535.0,
                                            2637558.0, 357423.0, 32670.0, 1925.0, 66.0, 1.0};

inline double LanczosSum(double x) {
  double num = 0.0, den = 0.0;
  if (x < 5.0) {
    for (int i = kLanczosN; --i >= 0;) {
      num = num * x + kLanczosNum[i];
      den = den * x + kLanczosDen[i];
    }
  } else {
    for (int i = 0; i < kLanczosN; i++) {
      num = num / x + kLanczosNum[i];
      den = den / x + kLanczosDen[i];
    }
  }
  return num / den;
}
}  // namespace cpython

inline double LogGamma(double x) {
  if (!(x > 0.0) || !std::isfinite(x)) throw StreamError("lgamma-argument", "LogGamma takes positive finite arguments here");
  if (x == std::floor(x) && x <= 2.0) return 0.0;
  if (x < 1e-20) return -std::log(x);
  double r = std::log(cpython::LanczosSum(x)) - cpython::kLanczosG;
  r += (x - 0.5) * (std::log(x + cpython::kLanczosG - 0.5) - 1);
  return r;
}

class SubStream {
 public:
  SubStream(StreamKey key, std::uint64_t event, std::uint64_t identity, std::uint32_t subIndex = 0) : fKey(key), fEvent(event), fIdentity(identity), fSub(subIndex) {
    if (event >= kEventLimit) throw StreamError("event-range", "event " + std::to_string(event) + " is outside 2^32");
    if (subIndex >= (1u << 16)) throw StreamError("sub-index", "sub-index " + std::to_string(subIndex) + " needs more than 16 bits");
  }

  std::array<double, 2> Group() {
    if (fUsed >= kGroupsPerSubStream) throw StreamError("sub-stream-exhausted", "the output-group index reached 2^16");
    const std::uint32_t word3 = (fSub << 16) | fUsed;
    ++fUsed;
    return UniformsOf(Philox4x32({static_cast<std::uint32_t>(fEvent), static_cast<std::uint32_t>(fIdentity & 0xFFFFFFFFu), static_cast<std::uint32_t>(fIdentity >> 32), word3},
                                 fKey.word0, fKey.word1));
  }

  double Gaussian(double mean, double sigma) {
    const auto g = Group();
    return mean + sigma * std::sqrt(-2.0 * std::log(g[0])) * std::cos(2.0 * M_PI * g[1]);
  }

  double Exponential() { return -std::log(Group()[0]); }

  long long Poisson(double mean) {
    if (mean < 0 || std::isinf(mean) || std::isnan(mean)) throw StreamError("poisson-mean", "mean " + std::to_string(mean));
    if (mean == 0) return 0;
    return mean < kInverseLimit ? PoissonInverse(mean) : PoissonPtrs(mean);
  }

  long long Binomial(long long trials, double probability) {
    if (trials < 0 || !(0.0 <= probability && probability <= 1.0)) throw StreamError("binomial-parameters", std::to_string(trials) + ", " + std::to_string(probability));
    if (trials == 0 || probability == 0.0) return 0;
    if (probability == 1.0) return trials;
    const double low = std::min(probability, 1.0 - probability);
    const long long count = static_cast<double>(trials) * low < kInverseLimit ? BinomialInverse(trials, low) : BinomialBtpe(trials, low);
    return probability > 0.5 ? trials - count : count;
  }

  // successive conditional binomials in channel order; the last entry is what is left over, `not detected`
  std::vector<long long> Multinomial(long long trials, const std::vector<double>& probabilities) {
    double total = Fsum(probabilities);
    for (double value : probabilities)
      if (value < 0) total = 2.0;
    if (total > 1.0 + 1e-12) throw StreamError("multinomial-parameters", "probabilities sum to " + std::to_string(total));
    std::vector<long long> counts;
    long long left = trials;
    double remaining = 1.0;
    for (double value : probabilities) {
      const double share = remaining > 0.0 ? std::min(value / remaining, 1.0) : 0.0;
      const long long drawn = Binomial(left, share);
      counts.push_back(drawn);
      left -= drawn;
      remaining -= value;
    }
    counts.push_back(left);
    return counts;
  }

  double Gamma(double shape) {
    if (shape < 1.0) throw StreamError("gamma-shape", "shape " + std::to_string(shape) + " is below 1");
    const double d = shape - 1.0 / 3.0;
    const double c = 1.0 / std::sqrt(9.0 * d);
    while (true) {
      const auto g = Group();
      const double third = Group()[0];
      const double x = std::sqrt(-2.0 * std::log(g[0])) * std::cos(2.0 * M_PI * g[1]);
      const double v = std::pow(1.0 + c * x, 3);
      if (v > 0.0 && std::log(third) < 0.5 * x * x + d - d * v + d * std::log(v)) return d * v;
    }
  }

 private:
  long long PoissonInverse(double mean) {
    const double u = Group()[0];
    double term = std::exp(-mean);
    double total = term;
    long long count = 0;
    while (u > total && term > 0.0) {
      count += 1;
      term *= mean / static_cast<double>(count);
      total += term;
    }
    return count;
  }

  long long PoissonPtrs(double mean) {
    const double root = std::sqrt(mean), logMean = std::log(mean);
    const double b = 0.931 + 2.53 * root;
    const double a = -0.059 + 0.02483 * b;
    const double inverseAlpha = 1.1239 + 1.1328 / (b - 3.4);
    const double vLimit = 0.9277 - 3.6224 / (b - 2.0);
    while (true) {
      const auto g = Group();
      const double u = g[0] - 0.5, v = g[1];
      const double us = 0.5 - std::fabs(u);
      const long long count = static_cast<long long>(std::floor((2.0 * a / us + b) * u + mean + 0.43));
      if (us >= 0.07 && v <= vLimit) return count;
      if (count < 0 || (us < 0.013 && v > us)) continue;
      if (std::log(v) + std::log(inverseAlpha) - std::log(a / (us * us) + b) <= -mean + static_cast<double>(count) * logMean - LogGamma(static_cast<double>(count) + 1.0)) return count;
    }
  }

  long long BinomialInverse(long long trials, double probability) {
    const double u = Group()[0];
    double term = std::exp(static_cast<double>(trials) * std::log1p(-probability));
    const double ratio = probability / (1.0 - probability);
    double total = term;
    long long count = 0;
    while (u > total && count < trials && term > 0.0) {
      count += 1;
      term *= ratio * static_cast<double>(trials - count + 1) / static_cast<double>(count);
      total += term;
    }
    return count;
  }

  static double StirlingTail(double value) {
    const double square = value * value;
    return (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / square) / square) / square) / square) / value / 166320.0;
  }

  long long BinomialBtpe(long long n, double r) {
    const double q = 1.0 - r;
    const double nd = static_cast<double>(n);
    const double fm = nd * r + r;
    const long long m = static_cast<long long>(std::floor(fm));
    const double md = static_cast<double>(m);
    const double nrq = nd * r * q;
    const double p1 = std::floor(2.195 * std::sqrt(nrq) - 4.6 * q) + 0.5;
    const double xm = md + 0.5;
    const double xl = xm - p1, xr = xm + p1;
    const double c = 0.134 + 20.5 / (15.3 + md);
    double a = (fm - xl) / (fm - xl * r);
    const double left = a * (1.0 + a / 2.0);
    a = (xr - fm) / (xr * q);
    const double right = a * (1.0 + a / 2.0);
    const double p2 = p1 * (1.0 + 2.0 * c);
    const double p3 = p2 + c / left;
    const double p4 = p3 + c / right;
    while (true) {
      const auto g = Group();
      double v = g[1];
      const double u = g[0] * p4;
      long long y;
      if (u <= p1) return static_cast<long long>(std::floor(xm - p1 * v + u));
      if (u <= p2) {
        const double x = xl + (u - p1) / c;
        v = v * c + 1.0 - std::fabs(md - x + 0.5) / p1;
        if (v > 1.0) continue;
        y = static_cast<long long>(std::floor(x));
      } else if (u <= p3) {
        y = static_cast<long long>(std::floor(xl + std::log(v) / left));
        if (y < 0) continue;
        v = v * (u - p2) * left;
      } else {
        y = static_cast<long long>(std::floor(xr - std::log(v) / right));
        if (y > n) continue;
        v = v * (u - p3) * right;
      }
      const long long k = y > m ? y - m : m - y;
      const double kd = static_cast<double>(k);
      if (k <= 20 || kd >= nrq / 2.0 - 1.0) {
        const double s = r / q;
        const double aa = s * static_cast<double>(n + 1);
        double f = 1.0;
        for (long long i = m + 1; i <= y; ++i) f *= aa / static_cast<double>(i) - s;
        for (long long i = y + 1; i <= m; ++i) f /= aa / static_cast<double>(i) - s;
        if (v <= f) return y;
        continue;
      }
      const double rho = (kd / nrq) * ((kd * (kd / 3.0 + 0.625) + 0.16666666666666666) / nrq + 0.5);
      const double t = static_cast<double>(-k * k) / (2.0 * nrq);
      const double logV = std::log(v);
      if (logV < t - rho) return y;
      if (logV > t + rho) continue;
      const double x1 = static_cast<double>(y) + 1.0, f1 = md + 1.0, z = nd + 1.0 - md, w = static_cast<double>(n - y) + 1.0;
      const double limit = xm * std::log(f1 / x1) + (static_cast<double>(n - m) + 0.5) * std::log(z / w) + static_cast<double>(y - m) * std::log(w * r / (x1 * q)) +
                           StirlingTail(f1) + StirlingTail(z) - StirlingTail(x1) - StirlingTail(w);
      if (logV <= limit) return y;
    }
  }

  StreamKey fKey;
  std::uint64_t fEvent, fIdentity;
  std::uint32_t fSub, fUsed = 0;
};

}  // namespace g4sim
