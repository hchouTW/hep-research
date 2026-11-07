// SHA-256 for file identities. The driver links this; it holds no seed and no stream.
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

namespace t07 {

using Sha256Digest = std::array<std::uint8_t, 32>;

class Sha256 {
 public:
  Sha256();
  void add(const void* bytes, std::size_t length);
  Sha256Digest finish();

 private:
  void compress(const std::uint8_t* block);
  std::array<std::uint32_t, 8> m_state;
  std::array<std::uint8_t, 64> m_block{};
  std::size_t m_filled = 0;
  std::uint64_t m_total_bytes = 0;
};

Sha256Digest sha256_of_text(const std::string& text);
std::string hex_of(const Sha256Digest& digest);
Sha256Digest sha256_digest_of_file(const std::string& path);
std::string sha256_of_file(const std::string& path);

}  // namespace t07
