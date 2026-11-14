// The truth file of the T07 fixtures: role truth (t07-t09-task-sheets.md, Input). Only the generator links this code:
// CMakeLists.txt keeps it out of the driver, and tests/adapters/test_acts_tracking.py checks that. Its header names the generator,
// the seed integers and the SHA-256 of the data file it belongs to. Its event records run in the data file's order, so position
// pairs the two, and event_index and the seed digest appear here only.
#pragma once

#include <array>
#include <cstdint>
#include <fstream>
#include <string>
#include <vector>

#include "t07_data_file.hpp"
#include "t07_generation_constants.hpp"
#include "t07_seed_stream.hpp"

namespace t07 {

inline constexpr char truth_magic[9] = "T07TRUT1";
inline constexpr char truth_role[] = "truth";

struct TruthFileHeader {
  std::string generator;
  std::uint32_t fixture_id = 0;
  std::uint32_t block = 0;
  std::uint32_t stratum = 0;
  std::uint32_t event_count = 0;
  double sigma_loc0_mm = 0.0;
  double sigma_loc1_mm = 0.0;
};

struct TruthVertex {
  double u_mm = 0.0;
  double v_mm = 0.0;
  double z_mm = 0.0;
};

struct TruthCrossing {  // bound parameters at one plane, section 7, Track state
  double loc0_mm = 0.0;
  double loc1_mm = 0.0;
  double phi = 0.0;
  double theta = 0.0;
};

struct TruthTrack {
  std::uint32_t particle_key = 0;
  std::uint32_t vertex_index = 0;
  std::int32_t charge = 0;
  double momentum_gev = 0.0;
  double slope_u = 0.0;  // at the vertex, du/dz
  double slope_v = 0.0;  // at the vertex, dv/dz
  double q_over_p = 0.0;
  std::array<std::uint32_t, plane_count> hit_keys{};  // no_hit_key where the plane lost the hit
  std::array<TruthCrossing, plane_count> crossings{};
};

struct TruthEvent {
  Sha256Digest event_digest{};
  std::uint64_t event_index = 0;
  std::uint32_t momentum_bin = 0;
  std::uint32_t occupancy_level = 0;
  std::uint32_t near_separation = 0;  // 0 far, 1 near
  std::array<std::uint32_t, plane_count> noise_counts{};
  std::vector<TruthVertex> vertices;
  std::vector<TruthTrack> tracks;
};

class TruthFileWriter {
 public:
  TruthFileWriter(const std::string& path, const TruthFileHeader& header);
  void write(const TruthEvent& event);
  void close(const Sha256Digest& data_file_digest);  // the data file is finished first, so its identity goes in last

 private:
  std::ofstream m_output;
  std::string m_path;
  std::uint32_t m_expected = 0;
  std::uint32_t m_written = 0;
};

}  // namespace t07
