#include "t07_data_file.hpp"

#include <array>
#include <bit>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <stdexcept>

#include "t07_fixture_constants.hpp"

static_assert(std::endian::native == std::endian::little, "the file layouts are little-endian");

namespace t07 {
namespace {

template <typename value_t>
void put_value(std::string& bytes, value_t value) {
  bytes.append(reinterpret_cast<const char*>(&value), sizeof(value));
}

template <typename value_t>
value_t take_value(const char*& cursor) {
  value_t value;
  std::memcpy(&value, cursor, sizeof(value));
  cursor += sizeof(value);
  return value;
}

std::string role_field() {
  std::string field(data_role);
  field.append(role_field_bytes - field.size(), '\0');
  return field;
}

}  // namespace

void refuse_truth_path(const std::string& path) {
  const std::string suffix = truth_file_suffix;
  if (path.size() >= suffix.size() && path.compare(path.size() - suffix.size(), suffix.size(), suffix) == 0) {
    throw std::invalid_argument("refused: " + path + " is a truth file, and the data-side driver never opens truth");
  }
}

DataFileWriter::DataFileWriter(const std::string& path, const DataFileHeader& header)
    : m_output(path, std::ios::binary), m_path(path), m_expected(header.event_count) {
  if (!m_output) {
    throw std::runtime_error("cannot write " + path);
  }
  std::string bytes(data_magic, 8);
  bytes += role_field();
  put_value(bytes, header.event_count);
  put_value(bytes, header.sigma_loc0_mm);
  put_value(bytes, header.sigma_loc1_mm);
  m_output.write(bytes.data(), std::streamsize(bytes.size()));
}

void DataFileWriter::write(const DataEvent& event) {
  std::string bytes;
  put_value(bytes, std::uint32_t(event.hits.size()));
  for (const PlaneHit& hit : event.hits) {
    put_value(bytes, hit.hit_key);
    put_value(bytes, hit.plane);
    put_value(bytes, hit.loc0_mm);
    put_value(bytes, hit.loc1_mm);
  }
  m_output.write(bytes.data(), std::streamsize(bytes.size()));
  ++m_written;
}

void DataFileWriter::close() {
  m_output.close();
  if (!m_output || m_written != m_expected) {
    throw std::runtime_error("incomplete data file " + m_path);
  }
}

DataFileReader::DataFileReader(const std::string& path) : m_path(path) {
  refuse_truth_path(path);
  m_input.open(path, std::ios::binary);
  if (!m_input) {
    throw std::invalid_argument("cannot open " + path);
  }
  const std::uint64_t file_bytes = std::filesystem::file_size(path);
  std::string raw(data_header_bytes, '\0');
  m_input.read(raw.data(), std::streamsize(raw.size()));
  if (std::size_t(m_input.gcount()) != raw.size() || raw.compare(0, 8, data_magic) != 0) {
    throw std::invalid_argument("refused: " + path + " is not a T07 data file");
  }
  if (raw.compare(8, role_field_bytes, role_field()) != 0) {
    throw std::invalid_argument("refused: " + path + " does not have the role " + data_role);
  }
  const char* cursor = raw.data() + 8 + role_field_bytes;
  m_header.event_count = take_value<std::uint32_t>(cursor);
  m_header.sigma_loc0_mm = take_value<double>(cursor);
  m_header.sigma_loc1_mm = take_value<double>(cursor);
  if (!(m_header.sigma_loc0_mm > 0.0) || !(m_header.sigma_loc1_mm > 0.0) || !std::isfinite(m_header.sigma_loc0_mm) ||
      !std::isfinite(m_header.sigma_loc1_mm)) {
    throw std::invalid_argument("refused: " + path + " states no usable measurement sigma");
  }
  m_bytes_left = file_bytes - data_header_bytes;
}

bool DataFileReader::next(DataEvent& event) {
  if (m_read == m_header.event_count) {
    if (m_bytes_left != 0) {
      throw std::invalid_argument("refused: " + m_path + " holds bytes after its last event");
    }
    return false;
  }
  std::array<char, sizeof(std::uint32_t)> raw{};
  if (m_bytes_left < raw.size()) {
    throw std::invalid_argument("refused: " + m_path + " ends before event record " + std::to_string(m_read));
  }
  m_input.read(raw.data(), std::streamsize(raw.size()));
  const char* cursor = raw.data();
  const auto hit_count = take_value<std::uint32_t>(cursor);
  m_bytes_left -= raw.size();
  const std::uint64_t hit_bytes = std::uint64_t(hit_count) * data_hit_bytes;
  if (hit_bytes > m_bytes_left) {  // before any allocation: a count from a corrupt file sizes nothing
    throw std::invalid_argument("refused: " + m_path + " ends inside the hits of event " + std::to_string(m_read));
  }
  event.hits.resize(hit_count);
  std::string hits(hit_bytes, '\0');
  m_input.read(hits.data(), std::streamsize(hits.size()));
  if (std::uint64_t(m_input.gcount()) != hit_bytes) {
    throw std::invalid_argument("refused: " + m_path + " could not be read at event " + std::to_string(m_read));
  }
  m_bytes_left -= hit_bytes;
  cursor = hits.data();
  for (std::uint32_t position = 0; position < hit_count; ++position) {
    PlaneHit& hit = event.hits[position];
    hit.hit_key = take_value<std::uint32_t>(cursor);
    hit.plane = take_value<std::uint32_t>(cursor);
    hit.loc0_mm = take_value<double>(cursor);
    hit.loc1_mm = take_value<double>(cursor);
    if (hit.hit_key != position || hit.plane < 1 || hit.plane > std::uint32_t(plane_count) || !std::isfinite(hit.loc0_mm) ||
        !std::isfinite(hit.loc1_mm)) {
      throw std::invalid_argument("refused: " + m_path + " holds a malformed hit in event " + std::to_string(m_read));
    }
  }
  ++m_read;
  return true;
}

}  // namespace t07
