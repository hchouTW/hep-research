#include "t07_truth_file.hpp"

#include <stdexcept>

namespace t07 {
namespace {

template <typename value_t>
void put_value(std::string& bytes, value_t value) {
  bytes.append(reinterpret_cast<const char*>(&value), sizeof(value));
}

void put_fixed_text(std::string& bytes, const std::string& text, std::size_t width) {
  if (text.size() >= width) {
    throw std::runtime_error("a header field does not fit: " + text);
  }
  bytes += text;
  bytes.append(width - text.size(), '\0');
}

constexpr std::size_t data_digest_offset = 96;  // magic, role, generator, four integers, two sigmas
constexpr std::size_t data_digest_bytes = 32;

bool has_suffix(const std::string& text, const std::string& suffix) {
  return text.size() >= suffix.size() && text.compare(text.size() - suffix.size(), suffix.size(), suffix) == 0;
}

}  // namespace

TruthFileWriter::TruthFileWriter(const std::string& path, const TruthFileHeader& header)
    : m_path(path), m_expected(header.event_count) {
  if (!has_suffix(path, truth_file_suffix)) {
    throw std::runtime_error("a truth file carries the suffix " + std::string(truth_file_suffix) + ": " + path);
  }
  m_output.open(path, std::ios::binary);
  if (!m_output) {
    throw std::runtime_error("cannot write " + path);
  }
  std::string bytes(truth_magic, 8);
  put_fixed_text(bytes, truth_role, 24);
  put_fixed_text(bytes, header.generator, 32);
  put_value(bytes, header.fixture_id);
  put_value(bytes, header.block);
  put_value(bytes, header.stratum);
  put_value(bytes, header.event_count);
  put_value(bytes, header.sigma_loc0_mm);
  put_value(bytes, header.sigma_loc1_mm);
  bytes.append(data_digest_bytes, '\0');
  m_output.write(bytes.data(), std::streamsize(bytes.size()));
}

void TruthFileWriter::write(const TruthEvent& event) {
  std::string bytes(reinterpret_cast<const char*>(event.event_digest.data()), event.event_digest.size());
  put_value(bytes, event.event_index);
  put_value(bytes, event.momentum_bin);
  put_value(bytes, event.occupancy_level);
  put_value(bytes, event.near_separation);
  put_value(bytes, std::uint32_t(event.vertices.size()));
  put_value(bytes, std::uint32_t(event.tracks.size()));
  for (const std::uint32_t count : event.noise_counts) {
    put_value(bytes, count);
  }
  put_value(bytes, std::uint32_t(0));
  for (const TruthVertex& vertex : event.vertices) {
    put_value(bytes, vertex.u_mm);
    put_value(bytes, vertex.v_mm);
    put_value(bytes, vertex.z_mm);
  }
  for (const TruthTrack& track : event.tracks) {
    put_value(bytes, track.particle_key);
    put_value(bytes, track.vertex_index);
    put_value(bytes, track.charge);
    put_value(bytes, std::uint32_t(0));
    put_value(bytes, track.momentum_gev);
    put_value(bytes, track.slope_u);
    put_value(bytes, track.slope_v);
    put_value(bytes, track.q_over_p);
    for (const std::uint32_t key : track.hit_keys) {
      put_value(bytes, key);
    }
    for (const TruthCrossing& crossing : track.crossings) {
      put_value(bytes, crossing.loc0_mm);
      put_value(bytes, crossing.loc1_mm);
      put_value(bytes, crossing.phi);
      put_value(bytes, crossing.theta);
    }
  }
  m_output.write(bytes.data(), std::streamsize(bytes.size()));
  ++m_written;
}

void TruthFileWriter::close(const Sha256Digest& data_file_digest) {
  m_output.seekp(std::streamoff(data_digest_offset));
  m_output.write(reinterpret_cast<const char*>(data_file_digest.data()), std::streamsize(data_file_digest.size()));
  m_output.close();
  if (!m_output || m_written != m_expected) {
    throw std::runtime_error("incomplete truth file " + m_path);
  }
}

}  // namespace t07
