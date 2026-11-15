#include "alignment_payload.hpp"

#include <Acts/Surfaces/SurfaceBounds.hpp>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <regex>
#include <stdexcept>

#include "sha256.hpp"
#include "t07_fixture_constants.hpp"
#include "telescope_geometry.hpp"

namespace t07 {
namespace {

// What %.17g writes: no hexadecimal, inf or nan, which strtod would also take (the Python reader's rule).
const std::regex decimal_number(R"(^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$)");
const std::regex count_text(R"(^(0|[1-9][0-9]*)$)");
const std::regex identity_text(R"(^[0-9a-f]{64}$)");
constexpr std::size_t plane_record_values = 6;  // t07-plane-rigid/1: shift-loc0, shift-loc1, shift-normal, rotation-loc0, rotation-loc1, rotation-normal

std::string geometry_number(double value) {
  char text[40];
  std::snprintf(text, sizeof(text), "%.17g", value);
  return text;
}

std::vector<std::string> tokens_of(const std::string& line) {
  std::vector<std::string> tokens;
  std::size_t start = 0;
  while (true) {
    const std::size_t space = line.find(' ', start);
    tokens.push_back(line.substr(start, space == std::string::npos ? std::string::npos : space - start));
    if (space == std::string::npos) {
      return tokens;
    }
    start = space + 1;
  }
}

double payload_number(const std::string& token) {
  if (!std::regex_match(token, decimal_number)) {
    throw std::invalid_argument("refused: not a decimal number in the alignment payload: " + token);
  }
  const double value = std::strtod(token.c_str(), nullptr);
  if (!std::isfinite(value)) {
    throw std::invalid_argument("refused: not a finite number in the alignment payload: " + token);
  }
  return value;
}

}  // namespace

std::string nominal_geometry_text() {
  const TelescopeGeometry nominal = build_telescope_geometry();
  std::string text = std::string(nominal_geometry_format) + "\nplanes " + std::to_string(nominal.planes.size()) + "\n";
  for (std::size_t index = 0; index < nominal.planes.size(); ++index) {
    const Acts::Surface& plane = *nominal.planes[index];
    if (plane.bounds().type() != Acts::SurfaceBounds::eRectangle) {
      throw std::logic_error("a telescope plane is not a rectangle");
    }
    text += "plane " + std::to_string(index + 1) + " rectangle";
    for (const double value : plane.bounds().values()) {  // RectangleBounds: min x, min y, max x, max y
      text += " " + geometry_number(value);
    }
    const Acts::Transform3& transform = plane.localToGlobalTransform(nominal.geometry_context);
    for (int row = 0; row < 3; ++row) {
      for (int column = 0; column < 3; ++column) {
        text += " " + geometry_number(transform.linear()(row, column));
      }
    }
    for (int row = 0; row < 3; ++row) {
      text += " " + geometry_number(transform.translation()(row));
    }
    text += "\n";
  }
  return text;
}

std::string nominal_geometry_id() { return hex_of(sha256_of_text(nominal_geometry_text())); }

AlignmentPayload parse_alignment_payload(const std::string& text) {
  if (text.empty() || text.back() != '\n') {
    throw std::invalid_argument("refused: the alignment payload's last line is not finished");
  }
  std::vector<std::string> lines;
  {
    std::size_t start = 0;
    while (start < text.size()) {
      const std::size_t end = text.find('\n', start);
      lines.push_back(text.substr(start, end - start));
      start = end + 1;
    }
  }
  if (lines.empty() || lines[0] != alignment_payload_format) {
    throw std::invalid_argument(std::string("refused: not ") + alignment_payload_format);
  }
  if (lines.size() < 6) {
    throw std::invalid_argument("refused: the alignment payload ends inside its header");
  }
  auto keyed = [&](std::size_t index, const std::string& key, std::size_t values) {
    const std::vector<std::string> tokens = tokens_of(lines[index]);
    if (tokens.size() != values + 1 || tokens[0] != key) {
      throw std::invalid_argument("refused: expected the alignment payload record " + key + ", found " + lines[index]);
    }
    return tokens;
  };
  const std::vector<std::string> parametrization = keyed(1, "parametrization", 3);
  if (parametrization[1] != "t07-plane-rigid/1" || parametrization[2] != "local" || parametrization[3] != "sensor") {
    throw std::invalid_argument("refused: the alignment payload's parametrization is t07-plane-rigid/1 local sensor, not " + lines[1].substr(16));
  }
  AlignmentPayload payload;
  payload.derived_against = keyed(2, "derived_against", 1)[1];
  payload.origin = keyed(3, "origin", 1)[1];
  payload.derived_from = keyed(4, "derived_from", 1)[1];
  if (!std::regex_match(payload.derived_against, identity_text)) {
    throw std::invalid_argument("refused: the alignment payload's derived_against is not a 64-character lowercase hexadecimal identity");
  }
  if (payload.origin != "nominal" && payload.origin != "measured") {
    throw std::invalid_argument("refused: an alignment payload's origin is nominal or measured, not " + payload.origin);
  }
  if (payload.derived_from != "none" && !std::regex_match(payload.derived_from, identity_text)) {
    throw std::invalid_argument("refused: the alignment payload's derived_from is not none or a 64-character lowercase hexadecimal identity");
  }
  bool ended = false;
  for (std::size_t index = 5; index < lines.size(); ++index) {
    if (ended) {
      throw std::invalid_argument("refused: text after the alignment payload's end record");
    }
    const std::vector<std::string> tokens = tokens_of(lines[index]);
    if (tokens[0] == "end" && tokens.size() == 2) {
      if (!std::regex_match(tokens[1], count_text) || tokens[1].size() > 3 || std::stoul(tokens[1]) != payload.planes.size()) {
        throw std::invalid_argument("refused: the alignment payload's end record does not count its plane records");
      }
      ended = true;
      continue;
    }
    if (tokens[0] != "plane") {
      throw std::invalid_argument("refused: an unknown record in the alignment payload: " + tokens[0]);
    }
    if (tokens.size() != 2 + plane_record_values) {
      throw std::invalid_argument("refused: a plane record of the alignment payload holds " + std::to_string(tokens.size() - 2) + " values, not 6");
    }
    if (!std::regex_match(tokens[1], count_text) || tokens[1].size() > 2 || std::stoi(tokens[1]) < 1 || std::stoi(tokens[1]) > plane_count) {
      throw std::invalid_argument("refused: the alignment payload names plane " + tokens[1] + ", and the telescope has planes 1 to " + std::to_string(plane_count));
    }
    const int plane = std::stoi(tokens[1]);
    if (!payload.planes.empty() && plane <= payload.planes.back()) {
      throw std::invalid_argument("refused: the alignment payload names plane " + tokens[1] + " twice or out of order");
    }
    payload.planes.push_back(plane);
    PlaneDelta& delta = payload.deltas[std::size_t(plane - 1)];
    delta.shift_loc0_mm = payload_number(tokens[2]);
    delta.shift_loc1_mm = payload_number(tokens[3]);
    delta.shift_normal_mm = payload_number(tokens[4]);
    delta.rotation_loc0 = payload_number(tokens[5]);
    delta.rotation_loc1 = payload_number(tokens[6]);
    delta.rotation_normal = payload_number(tokens[7]);
  }
  if (!ended) {
    throw std::invalid_argument("refused: the alignment payload ends before its end record");
  }
  // R32: nominal is the ideal geometry, so a payload labelled nominal moves no plane (D1 stage 9 fix round 1, m5).
  if (payload.origin == "nominal") {
    for (const PlaneDelta& delta : payload.deltas) {
      if (delta.shift_loc0_mm != 0.0 || delta.shift_loc1_mm != 0.0 || delta.shift_normal_mm != 0.0 || delta.rotation_loc0 != 0.0 || delta.rotation_loc1 != 0.0 ||
          delta.rotation_normal != 0.0) {
        throw std::invalid_argument("refused: an alignment payload labelled nominal moves no plane: nominal is the ideal geometry (R32)");
      }
    }
  }
  payload.content_sha256 = hex_of(sha256_of_text(text));
  return payload;
}

AlignmentPayload parse_alignment_payload_for(const std::string& text, const std::string& geometry_id) {
  AlignmentPayload payload = parse_alignment_payload(text);
  if (payload.derived_against != geometry_id) {
    throw std::invalid_argument("refused: the alignment payload was derived against the geometry " + payload.derived_against + ", not the nominal geometry " + geometry_id +
                                " it would be applied to (R32)");
  }
  return payload;
}

}  // namespace t07
