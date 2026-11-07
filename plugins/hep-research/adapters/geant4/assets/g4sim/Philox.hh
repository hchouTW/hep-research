// g4sim/Philox.hh: the integer layer of the response pipeline in C++ (g4sim plan, Section 10.2). core/simulation/rng.py is normative; this agrees with it bit for bit in
// Philox4x32-10 and the uniform variates, and fsum is the correctly rounded sum. No Geant4 here.
//
// Philox is Salmon, Moraes, Dror and Shaw, SC11 (2011), doi:10.1145/2063384.2063405. Keys are never computed here: the driver derives them with canonical/1 in Python and passes the two
// words, so C++ needs no canonical encoder (Section 22). fsum is the algorithm of CPython's math.fsum, Shewchuk partial sums with its half-even correction, which Section 10.2 requires to be kept
// exactly (Python Software Foundation License, reproduced in assets/PYTHON-LICENSE.txt). Compile without -ffast-math or any reassociation, and on x86 with SSE2 arithmetic: fsum depends on exact IEEE double operations.
#ifndef G4SIM_PHILOX_HH
#define G4SIM_PHILOX_HH

#include <array>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <vector>

#if defined(__FAST_MATH__)
#error "g4sim/Philox.hh must not be compiled with -ffast-math: fsum depends on exact double arithmetic"
#endif

namespace g4sim {

using PhiloxWords = std::array<std::uint32_t, 4>;

inline PhiloxWords Philox4x32(PhiloxWords counter, std::uint32_t key0, std::uint32_t key1) {
  constexpr std::uint64_t kFirst = 0xD2511F53u, kSecond = 0xCD9E8D57u;
  for (int round = 0; round < 10; ++round) {
    if (round) {
      key0 += 0x9E3779B9u;
      key1 += 0xBB67AE85u;
    }
    const std::uint64_t first = kFirst * counter[0], second = kSecond * counter[2];
    counter = {static_cast<std::uint32_t>(second >> 32) ^ counter[1] ^ key0, static_cast<std::uint32_t>(second), static_cast<std::uint32_t>(first >> 32) ^ counter[3] ^ key1,
               static_cast<std::uint32_t>(first)};
  }
  return counter;
}

// (k + 0.5) 2^-52 for the high 52 bits of a 64-bit integer: strictly inside (0, 1), and exact.
inline double UniformOf(std::uint32_t high, std::uint32_t low) {
  const std::uint64_t k = ((static_cast<std::uint64_t>(high) << 32) | low) >> 12;
  return std::ldexp(static_cast<double>(2 * k + 1), -53);
}

inline std::array<double, 2> UniformsOf(const PhiloxWords& words) { return {UniformOf(words[0], words[1]), UniformOf(words[2], words[3])}; }

// Shewchuk partial sums: an exact representation of a chunk's sum, which a chunk hands over instead of a rounded double.
inline std::vector<double> PartialSums(const std::vector<double>& values) {
  std::vector<double> partials;
  for (double value : values) {
    if (!std::isfinite(value) || std::fabs(value) > 1e290) throw std::range_error("a summand is outside the range of Section 10.2");
    std::size_t kept = 0;
    for (double other : partials) {
      if (std::fabs(value) < std::fabs(other)) std::swap(value, other);
      const double high = value + other;
      const volatile double rounded = high - value;
      const double low = other - rounded;
      if (low != 0.) partials[kept++] = low;
      value = high;
    }
    partials.resize(kept);
    if (value != 0.) partials.push_back(value);  // as CPython: a zero leaves no partial, so a sum of -0.0 is 0.0
  }
  return partials;
}

// The correctly rounded sum of partial sums, with the half-even correction of the last step.
inline double RoundPartials(const std::vector<double>& partials) {
  if (partials.empty()) return 0.;
  std::size_t n = partials.size();
  double high = partials[--n], low = 0.;
  while (n > 0) {
    const double x = high, y = partials[--n];
    high = x + y;
    const volatile double rounded = high - x;
    low = y - rounded;
    if (low != 0.) break;
  }
  if (n > 0 && ((low < 0. && partials[n - 1] < 0.) || (low > 0. && partials[n - 1] > 0.))) {
    const double twice = low * 2., sum = high + twice;
    const volatile double rounded = sum - high;
    if (twice == rounded) high = sum;
  }
  return high;
}

inline double Fsum(const std::vector<double>& values) { return RoundPartials(PartialSums(values)); }

// One final rounding over every chunk's partial sums, as core.simulation.rng.merge_partial_sums: partials from several chunks are not ordered, so they are summed again.
inline double MergePartialSums(const std::vector<std::vector<double>>& chunks) {
  std::vector<double> all;
  for (const std::vector<double>& chunk : chunks) all.insert(all.end(), chunk.begin(), chunk.end());
  return Fsum(all);
}

}  // namespace g4sim

#endif
