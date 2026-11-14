#include "sha256.hpp"

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <vector>

namespace t07 {
namespace {

constexpr std::array<std::uint32_t, 64> round_constants{
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be,
    0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa,
    0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85,
    0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f,
    0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};

std::uint32_t rotate_right(std::uint32_t value, int count) { return (value >> count) | (value << (32 - count)); }

}  // namespace

Sha256::Sha256() : m_state{0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19} {}

void Sha256::compress(const std::uint8_t* block) {
  std::array<std::uint32_t, 64> schedule{};
  for (int word = 0; word < 16; ++word) {
    schedule[word] = (std::uint32_t(block[4 * word]) << 24) | (std::uint32_t(block[4 * word + 1]) << 16) |
                     (std::uint32_t(block[4 * word + 2]) << 8) | std::uint32_t(block[4 * word + 3]);
  }
  for (int word = 16; word < 64; ++word) {
    const std::uint32_t older = schedule[word - 15];
    const std::uint32_t newer = schedule[word - 2];
    const std::uint32_t sigma0 = rotate_right(older, 7) ^ rotate_right(older, 18) ^ (older >> 3);
    const std::uint32_t sigma1 = rotate_right(newer, 17) ^ rotate_right(newer, 19) ^ (newer >> 10);
    schedule[word] = schedule[word - 16] + sigma0 + schedule[word - 7] + sigma1;
  }
  auto [a, b, c, d, e, f, g, h] = m_state;
  for (int round = 0; round < 64; ++round) {
    const std::uint32_t big1 = rotate_right(e, 6) ^ rotate_right(e, 11) ^ rotate_right(e, 25);
    const std::uint32_t choose = (e & f) ^ (~e & g);
    const std::uint32_t first = h + big1 + choose + round_constants[round] + schedule[round];
    const std::uint32_t big0 = rotate_right(a, 2) ^ rotate_right(a, 13) ^ rotate_right(a, 22);
    const std::uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
    const std::uint32_t second = big0 + majority;
    h = g;
    g = f;
    f = e;
    e = d + first;
    d = c;
    c = b;
    b = a;
    a = first + second;
  }
  const std::array<std::uint32_t, 8> working{a, b, c, d, e, f, g, h};
  for (int word = 0; word < 8; ++word) {
    m_state[word] += working[word];
  }
}

void Sha256::add(const void* bytes, std::size_t length) {
  const auto* cursor = static_cast<const std::uint8_t*>(bytes);
  m_total_bytes += length;
  while (length > 0) {
    const std::size_t taken = std::min<std::size_t>(length, 64 - m_filled);
    std::memcpy(m_block.data() + m_filled, cursor, taken);
    m_filled += taken;
    cursor += taken;
    length -= taken;
    if (m_filled == 64) {
      compress(m_block.data());
      m_filled = 0;
    }
  }
}

Sha256Digest Sha256::finish() {
  const std::uint64_t total_bits = m_total_bytes * 8;
  const std::uint8_t marker = 0x80;
  add(&marker, 1);
  const std::uint8_t zero = 0;
  while (m_filled != 56) {
    add(&zero, 1);
  }
  std::array<std::uint8_t, 8> length_bytes{};
  for (int index = 0; index < 8; ++index) {
    length_bytes[index] = std::uint8_t(total_bits >> (56 - 8 * index));
  }
  add(length_bytes.data(), 8);
  Sha256Digest digest{};
  for (int word = 0; word < 8; ++word) {
    for (int index = 0; index < 4; ++index) {
      digest[4 * word + index] = std::uint8_t(m_state[word] >> (24 - 8 * index));
    }
  }
  return digest;
}

Sha256Digest sha256_of_text(const std::string& text) {
  Sha256 hasher;
  hasher.add(text.data(), text.size());
  return hasher.finish();
}

std::string hex_of(const Sha256Digest& digest) {
  std::string text;
  char pair[3];
  for (const std::uint8_t byte : digest) {
    std::snprintf(pair, sizeof(pair), "%02x", byte);
    text += pair;
  }
  return text;
}

Sha256Digest sha256_digest_of_file(const std::string& path) {
  std::ifstream input(path, std::ios::binary);
  if (!input) {
    throw std::runtime_error("cannot open " + path);
  }
  Sha256 hasher;
  std::vector<char> chunk(1 << 20);
  while (input) {
    input.read(chunk.data(), std::streamsize(chunk.size()));
    hasher.add(chunk.data(), std::size_t(input.gcount()));
  }
  return hasher.finish();
}

std::string sha256_of_file(const std::string& path) { return hex_of(sha256_digest_of_file(path)); }

}  // namespace t07
