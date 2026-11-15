#include "t07_seed_stream.hpp"

#include <cmath>
#include <numbers>

namespace t07 {
namespace {

std::uint64_t rotate_left(std::uint64_t value, int count) { return (value << count) | (value >> (64 - count)); }

}  // namespace

Sha256Digest event_seed_digest(std::uint64_t fixture_id, std::uint64_t block, std::uint64_t stratum, std::uint64_t event_index) {
  const std::array<std::uint64_t, 4> integers{fixture_id, block, stratum, event_index};
  std::array<std::uint8_t, 32> message{};
  for (int word = 0; word < 4; ++word) {
    for (int index = 0; index < 8; ++index) {
      message[8 * word + index] = std::uint8_t(integers[word] >> (8 * index));
    }
  }
  Sha256 hasher;
  hasher.add(message.data(), message.size());
  return hasher.finish();
}

EventSeedStream::EventSeedStream(const Sha256Digest& digest) : m_words{} {
  for (int word = 0; word < 4; ++word) {
    for (int index = 0; index < 8; ++index) {
      m_words[word] |= std::uint64_t(digest[8 * word + index]) << (8 * index);
    }
  }
}

std::uint64_t EventSeedStream::next_raw() {
  const std::uint64_t result = rotate_left(m_words[1] * 5, 7) * 9;
  const std::uint64_t shifted = m_words[1] << 17;
  m_words[2] ^= m_words[0];
  m_words[3] ^= m_words[1];
  m_words[1] ^= m_words[2];
  m_words[0] ^= m_words[3];
  m_words[2] ^= shifted;
  m_words[3] = rotate_left(m_words[3], 45);
  return result;
}

double EventSeedStream::uniform() { return double(next_raw() >> 11) * 0x1.0p-53; }

double EventSeedStream::uniform_between(double lower, double upper) { return lower + (upper - lower) * uniform(); }

double EventSeedStream::gaussian() {
  const double radial = 1.0 - uniform();  // (0, 1], so the logarithm is finite
  const double angle = uniform();
  return std::sqrt(-2.0 * std::log(radial)) * std::cos(2.0 * std::numbers::pi * angle);
}

std::uint32_t EventSeedStream::poisson(double mean) {
  std::uint32_t arrivals = 0;
  double elapsed = -std::log(1.0 - uniform());
  while (elapsed < mean) {
    ++arrivals;
    elapsed -= std::log(1.0 - uniform());
  }
  return arrivals;
}

}  // namespace t07
