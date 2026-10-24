// g4sim/SimHash.hh: SHA-256, the seed hash H of simulation runs, and portable random numbers (adapters/geant4,
// Geant4 program A2.1). C++17 standard library only; shared by layered_sim and the task-B programs.
//
// H(x1, ..., xn) = big-endian uint64 of the first 8 bytes of sha256("\x1f".join(str(x_i))) mod (2^31 - 1) + 1, a value
// in [1, 2^31 - 1]; integers are written in decimal without leading zeros. It must equal core/simulation/seeds.py
// (the Python implementation; tests/adapters/test_g4sim.py checks both on test vectors).
// SplitMix64 uses integer arithmetic only and is bit-identical across platforms. BoxMuller uses libm's log and cos,
// so it is bit-identical on one platform and agrees to a relative 1e-12 across platforms (build with
// -ffp-contract=off).
#ifndef G4SIM_SIMHASH_HH
#define G4SIM_SIMHASH_HH

#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <initializer_list>
#include <string>
#include <vector>

namespace g4sim {

class Sha256 {
 public:
  Sha256() { Reset(); }
  void Reset() {
    fState = {0x6a09e667u, 0xbb67ae85u, 0x3c6ef372u, 0xa54ff53au, 0x510e527fu, 0x9b05688cu, 0x1f83d9abu, 0x5be0cd19u};
    fLen = 0;
    fBuf.clear();
  }
  void Update(const std::string& s) { Update(reinterpret_cast<const unsigned char*>(s.data()), s.size()); }
  void Update(const unsigned char* p, std::size_t n) {
    for (std::size_t i = 0; i < n; ++i) {
      fBuf.push_back(p[i]);
      if (fBuf.size() == 64) {
        Block(fBuf.data());
        fBuf.clear();
      }
    }
    fLen += n;
  }
  std::array<unsigned char, 32> Digest() {
    std::uint64_t bits = fLen * 8;
    unsigned char pad = 0x80;
    Update(&pad, 1);
    unsigned char zero = 0;
    while (fBuf.size() != 56) Update(&zero, 1);
    unsigned char len[8];
    for (int i = 0; i < 8; ++i) len[i] = static_cast<unsigned char>(bits >> (56 - 8 * i));
    Update(len, 8);
    std::array<unsigned char, 32> out{};
    for (int i = 0; i < 8; ++i)
      for (int j = 0; j < 4; ++j) out[4 * i + j] = static_cast<unsigned char>(fState[i] >> (24 - 8 * j));
    return out;
  }
  static std::string Hex(const std::array<unsigned char, 32>& d) {
    static const char* k = "0123456789abcdef";
    std::string s;
    for (unsigned char c : d) {
      s += k[c >> 4];
      s += k[c & 15];
    }
    return s;
  }
  static std::string HexOf(const std::string& data) {
    Sha256 h;
    h.Update(data);
    return Hex(h.Digest());
  }

 private:
  static std::uint32_t Rotr(std::uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }
  void Block(const unsigned char* p) {
    static const std::uint32_t k[64] = {
        0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u, 0x3956c25bu, 0x59f111f1u, 0x923f82a4u, 0xab1c5ed5u,
        0xd807aa98u, 0x12835b01u, 0x243185beu, 0x550c7dc3u, 0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u, 0xc19bf174u,
        0xe49b69c1u, 0xefbe4786u, 0x0fc19dc6u, 0x240ca1ccu, 0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau,
        0x983e5152u, 0xa831c66du, 0xb00327c8u, 0xbf597fc7u, 0xc6e00bf3u, 0xd5a79147u, 0x06ca6351u, 0x14292967u,
        0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu, 0x53380d13u, 0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u,
        0xa2bfe8a1u, 0xa81a664bu, 0xc24b8b70u, 0xc76c51a3u, 0xd192e819u, 0xd6990624u, 0xf40e3585u, 0x106aa070u,
        0x19a4c116u, 0x1e376c08u, 0x2748774cu, 0x34b0bcb5u, 0x391c0cb3u, 0x4ed8aa4au, 0x5b9cca4fu, 0x682e6ff3u,
        0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u, 0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u};
    std::uint32_t w[64];
    for (int i = 0; i < 16; ++i)
      w[i] = (std::uint32_t(p[4 * i]) << 24) | (std::uint32_t(p[4 * i + 1]) << 16) | (std::uint32_t(p[4 * i + 2]) << 8) |
             std::uint32_t(p[4 * i + 3]);
    for (int i = 16; i < 64; ++i) {
      std::uint32_t s0 = Rotr(w[i - 15], 7) ^ Rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
      std::uint32_t s1 = Rotr(w[i - 2], 17) ^ Rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
      w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    std::uint32_t a = fState[0], b = fState[1], c = fState[2], d = fState[3];
    std::uint32_t e = fState[4], f = fState[5], g = fState[6], h = fState[7];
    for (int i = 0; i < 64; ++i) {
      std::uint32_t t1 = h + (Rotr(e, 6) ^ Rotr(e, 11) ^ Rotr(e, 25)) + ((e & f) ^ (~e & g)) + k[i] + w[i];
      std::uint32_t t2 = (Rotr(a, 2) ^ Rotr(a, 13) ^ Rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
      h = g;
      g = f;
      f = e;
      e = d + t1;
      d = c;
      c = b;
      b = a;
      a = t1 + t2;
    }
    fState[0] += a;
    fState[1] += b;
    fState[2] += c;
    fState[3] += d;
    fState[4] += e;
    fState[5] += f;
    fState[6] += g;
    fState[7] += h;
  }
  std::array<std::uint32_t, 8> fState{};
  std::uint64_t fLen = 0;
  std::vector<unsigned char> fBuf;
};

// One part of H: an integer in decimal or a string as it is.
struct HashPart {
  std::string text;
  HashPart(long long v) : text(std::to_string(v)) {}  // NOLINT(google-explicit-constructor)
  HashPart(const std::string& s) : text(s) {}         // NOLINT(google-explicit-constructor)
  HashPart(const char* s) : text(s) {}                // NOLINT(google-explicit-constructor)
};

// The seed hash H (core/simulation/seeds.py): a value in [1, 2^31 - 1].
inline long SeedHash(std::initializer_list<HashPart> parts) {
  std::string joined;
  bool first = true;
  for (const auto& p : parts) {
    if (!first) joined += '\x1f';
    joined += p.text;
    first = false;
  }
  Sha256 h;
  h.Update(joined);
  auto d = h.Digest();
  std::uint64_t v = 0;
  for (int i = 0; i < 8; ++i) v = (v << 8) | d[i];
  const std::uint64_t modulus = 2147483647ull;  // 2^31 - 1
  return static_cast<long>(v % modulus + 1);
}

// The two seeds of event (or job start) e of logical run S: (H(S, e, 0), H(S, e, 1)).
inline std::array<long, 2> EventSeeds(long long s, long long e) {
  return {SeedHash({s, e, 0LL}), SeedHash({s, e, 1LL})};
}

// A double in the format of Python's float.hex() (C's %a differs: 0x1p+0 against 0x1.0000000000000p+0): 0.0 ->
// 0x0.0p+0, -0.0 -> -0x0.0p+0, subnormals as 0x0.<13 hex digits>p-1022, and inf, -inf, nan.
inline std::string PyFloatHex(double x) {
  std::uint64_t bits = 0;
  static_assert(sizeof bits == sizeof x, "64-bit double required");
  std::memcpy(&bits, &x, sizeof bits);
  bool neg = bits >> 63;
  int expo = static_cast<int>((bits >> 52) & 0x7ff);
  std::uint64_t mant = bits & ((1ull << 52) - 1);
  if (expo == 0x7ff) return mant ? "nan" : (neg ? "-inf" : "inf");
  std::string s = neg ? "-" : "";
  if (expo == 0 && mant == 0) return s + "0x0.0p+0";
  char digits[16];
  std::snprintf(digits, sizeof digits, "%013llx", static_cast<unsigned long long>(mant));
  int e = expo == 0 ? -1022 : expo - 1023;
  s += expo == 0 ? "0x0." : "0x1.";
  s += digits;
  s += e < 0 ? "p-" : "p+";
  s += std::to_string(e < 0 ? -e : e);
  return s;
}

// SplitMix64 (Steele, Lea and Flood 2014): integer arithmetic only, the same sequence on every platform.
class SplitMix64 {
 public:
  explicit SplitMix64(std::uint64_t seed) : fState(seed) {}
  std::uint64_t Next() {
    std::uint64_t z = (fState += 0x9e3779b97f4a7c15ull);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
    return z ^ (z >> 31);
  }
  double Uniform() { return (Next() >> 11) * (1.0 / 9007199254740992.0); }  // [0, 1), 53 bits

 private:
  std::uint64_t fState;
};

// Normal deviates by Box-Muller from SplitMix64 uniforms (one cached deviate per pair).
class BoxMuller {
 public:
  explicit BoxMuller(std::uint64_t seed) : fRng(seed) {}
  double Next() {
    if (fHave) {
      fHave = false;
      return fCached;
    }
    double u1 = 1.0 - fRng.Uniform();  // (0, 1]
    double u2 = fRng.Uniform();
    double r = std::sqrt(-2.0 * std::log(u1));
    double t = 2.0 * 3.14159265358979323846 * u2;
    fCached = r * std::sin(t);
    fHave = true;
    return r * std::cos(t);
  }

 private:
  SplitMix64 fRng;
  bool fHave = false;
  double fCached = 0.;
};

}  // namespace g4sim

#endif
