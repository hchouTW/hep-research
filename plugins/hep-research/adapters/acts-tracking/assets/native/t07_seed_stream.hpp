// t04-values-v4.md section 3.2: an event's generator state is "the same four integers hashed by the C++ driver".
// The hash is SHA-256 over the four integers as little-endian unsigned 64-bit words, in the order fixture_id, block,
// stratum, event_index. Its 32 bytes, read as four little-endian words, are the state of a xoshiro256** stream.
// The check repeats digest and stream in Python (check_t07_generator.py), so a wrong word order shows.
// Generator only: this digest is the event's truth in seed form, so the driver neither links it nor sees it (A09).
#pragma once

#include <array>
#include <cstdint>

#include "sha256.hpp"

namespace t07 {

Sha256Digest event_seed_digest(std::uint64_t fixture_id, std::uint64_t block, std::uint64_t stratum, std::uint64_t event_index);

class EventSeedStream {
 public:
  explicit EventSeedStream(const Sha256Digest& digest);
  std::uint64_t next_raw();
  double uniform();                                  // [0, 1), 53 bits
  double uniform_between(double lower, double upper);  // [lower, upper)
  double gaussian();                                 // unit normal, one Box-Muller value from two uniforms
  std::uint32_t poisson(double mean);                // arrivals of a unit-rate process inside [0, mean)

 private:
  std::array<std::uint64_t, 4> m_words;
};

}  // namespace t07
