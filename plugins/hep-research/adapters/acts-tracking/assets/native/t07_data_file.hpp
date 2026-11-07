// The data-side file of the T07 fixtures: role reconstruction-input. It holds the measurement sigma and hits, and no generator name,
// fixture id, block, stratum, event index, digest or seed, each of which reaches the generator state (A09; t04-prereg.md, "Truth
// reaches a data-side recipe"). Hits lie on one grid and are sorted by plane and position, by one path for track and noise hits, so
// neither their bits nor their order say which is which. An event's identity is its position in the file, with the map to
// event_index on the truth side. The limit of all this: the seed of section 3.2 is four small integers, so whoever enumerates them
// with SHA-256 alone reproduces the file's event order, and with it every event_index and near flag, and with the generator every
// event. That search is an accepted limit; what this file promises is that no field and no bit of it shortens it.
// Little-endian and packed, layouts mirrored by t07_fixture_files.py, which names every allowed field.
#pragma once

#include <cstdint>
#include <fstream>
#include <string>
#include <vector>

namespace t07 {

inline constexpr char data_magic[9] = "T07HITS1";
inline constexpr char data_role[] = "reconstruction-input";
inline constexpr char truth_file_suffix[] = ".t07truth";
inline constexpr std::size_t role_field_bytes = 24;
inline constexpr std::size_t data_header_bytes = 52;
inline constexpr std::size_t data_hit_bytes = 24;

struct DataFileHeader {
  std::uint32_t event_count = 0;
  double sigma_loc0_mm = 0.0;
  double sigma_loc1_mm = 0.0;
};

struct PlaneHit {
  std::uint32_t hit_key = 0;  // position inside the event, so unique inside the event
  std::uint32_t plane = 0;    // 1..8
  double loc0_mm = 0.0;       // fixture u
  double loc1_mm = 0.0;       // fixture v
};

struct DataEvent {
  std::vector<PlaneHit> hits;
};

// Every input of the driver passes here first: a path with the truth suffix is refused before anything opens it.
void refuse_truth_path(const std::string& path);

class DataFileWriter {
 public:
  DataFileWriter(const std::string& path, const DataFileHeader& header);
  void write(const DataEvent& event);
  void close();

 private:
  std::ofstream m_output;
  std::string m_path;
  std::uint32_t m_expected = 0;
  std::uint32_t m_written = 0;
};

// Refuses anything that is not a data file by magic, role and length.
class DataFileReader {
 public:
  explicit DataFileReader(const std::string& path);
  const DataFileHeader& header() const { return m_header; }
  bool next(DataEvent& event);  // false after the last event; a short or over-long file is refused

 private:
  std::ifstream m_input;
  std::string m_path;
  DataFileHeader m_header;
  std::uint64_t m_bytes_left = 0;
  std::uint32_t m_read = 0;
};

}  // namespace t07
