#include "native_product.hpp"

#include <cerrno>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <tuple>
#include <utility>

namespace t07 {
namespace {

constexpr std::array<const char*, 3> state_kinds{"measurement", "hole", "outlier"};
constexpr std::array<const char*, 3> state_types{"predicted", "filtered", "smoothed"};
constexpr std::array<const char*, 4> residual_types{"predicted", "filtered", "smoothed", "unbiased"};  // never mixed (BP03)
constexpr std::array<const char*, 3> topologies{"collision", "cosmic", "resonance-candidate"};       // R33
constexpr std::array<const char*, 3> constraints{"none", "beam", "vertex"};                          // R33

std::string number_text(double value) {
  if (!std::isfinite(value)) {
    throw std::runtime_error("a product holds finite numbers only");
  }
  char text[40];
  std::snprintf(text, sizeof(text), "%.17g", value);
  return text;
}

template <std::size_t size>
std::string numbers_text(const std::array<double, size>& values) {
  std::string text;
  for (const double value : values) {
    text += " " + number_text(value);
  }
  return text;
}

template <std::size_t size>
bool is_one_of(const std::string& text, const std::array<const char*, size>& allowed) {
  for (const char* item : allowed) {
    if (text == item) {
      return true;
    }
  }
  return false;
}

class TokenLine {
 public:
  TokenLine(const std::string& line, std::size_t line_number) : m_number(line_number) {
    std::istringstream stream(line);
    std::string token;
    while (stream >> token) {
      m_tokens.push_back(token);
    }
  }
  std::size_t size() const { return m_tokens.size(); }
  const std::string& text(std::size_t index) const { return m_tokens.at(index); }
  [[noreturn]] void refuse(const std::string& reason) const { throw std::runtime_error("line " + std::to_string(m_number) + ": " + reason); }
  double number(std::size_t index) const {
    const std::string& token = text(index);
    char* end = nullptr;
    const double value = std::strtod(token.c_str(), &end);
    if (*end != '\0' || end == token.c_str() || !std::isfinite(value)) {
      refuse("not a finite number: " + token);
    }
    return value;
  }
  std::uint64_t unsigned_integer(std::size_t index) const {
    const std::string& token = text(index);
    char* end = nullptr;
    errno = 0;
    const unsigned long long value = std::strtoull(token.c_str(), &end, 10);
    if (*end != '\0' || end == token.c_str() || errno == ERANGE || token[0] == '-') {
      refuse("not an unsigned integer: " + token);
    }
    return value;
  }
  std::int64_t integer(std::size_t index) const {
    const std::string& token = text(index);
    char* end = nullptr;
    errno = 0;
    const long long value = std::strtoll(token.c_str(), &end, 10);
    if (*end != '\0' || end == token.c_str() || errno == ERANGE) {
      refuse("not an integer: " + token);
    }
    return value;
  }
  std::int32_t small_integer(std::size_t index) const {
    const std::int64_t value = integer(index);
    if (value < std::numeric_limits<std::int32_t>::min() || value > std::numeric_limits<std::int32_t>::max()) {
      refuse("does not fit 32 bits: " + text(index));
    }
    return std::int32_t(value);
  }
  std::uint32_t count(std::size_t index) const {
    const std::int64_t value = integer(index);
    if (value < 0 || value > std::numeric_limits<std::uint32_t>::max()) {
      refuse("not a 32-bit count: " + text(index));
    }
    return std::uint32_t(value);
  }

 private:
  std::vector<std::string> m_tokens;
  std::size_t m_number;
};

void require_token(const std::string& value, const std::string& name) {
  if (value.empty() || value.find_first_of(" \t\n\r") != std::string::npos) {
    throw std::runtime_error("the field " + name + " is empty or holds white space: '" + value + "'");
  }
}

}  // namespace

std::string encode_product(const ProductDocument& document) {
  const ProductHeader& header = document.header;
  for (const auto& [name, value] : std::vector<std::pair<std::string, std::string>>{
           {"product_id", header.product_id}, {"recipe", header.recipe}, {"stage", header.stage}, {"evidence_class", header.evidence_class},
           {"data_product", header.data_product}, {"data_sha256", header.data_sha256}, {"hit_sets_sha256", header.hit_sets_sha256},
           {"qop_status", header.qop_status}, {"material_model", header.material_model}, {"acts_version", header.acts_version}}) {
    require_token(value, name);
  }
  if (document.format_version != 1 && document.format_version != 2) {
    throw std::runtime_error("a product is version 1 or 2");
  }
  const bool with_r33 = document.format_version == 2;
  if (!with_r33 && (!document.track_outputs.empty() || !document.residuals.empty() || !document.measurement_outputs.empty() ||
                    !document.residual_covariances.empty())) {
    throw std::runtime_error("R33 records belong to acts-tracking-product/2 only");
  }
  if (with_r33) {
    require_token(header.r33_conventions, "r33_conventions");
    require_token(header.alignment_parametrization, "alignment_parametrization");
    require_token(header.alignment_frame, "alignment_frame");
    require_token(header.alignment_level, "alignment_level");
  }
  const bool with_payload = !header.alignment_payload_sha256.empty();
  if (with_payload) {
    if (!with_r33) {
      throw std::runtime_error("an applied alignment payload is recorded in acts-tracking-product/2 only");
    }
    for (const auto& [name, value] : std::vector<std::pair<std::string, std::string>>{
             {"alignment_payload", header.alignment_payload_sha256}, {"alignment_payload origin", header.alignment_payload_origin},
             {"alignment_payload derived_against", header.alignment_payload_derived_against}, {"alignment_payload derived_from", header.alignment_payload_derived_from},
             {"alignment_payload round", header.alignment_payload_round}}) {
      require_token(value, name);
    }
  }
  std::string text = std::string(with_r33 ? product_format_r33 : product_format) + "\n";
  text += "product_id " + header.product_id + "\n";
  text += "revision " + std::to_string(header.revision) + "\n";
  text += "recipe " + header.recipe + "\n";
  text += "stage " + header.stage + "\n";
  text += "evidence_class " + header.evidence_class + "\n";
  text += "data_product " + header.data_product + "\n";
  text += "data_sha256 " + header.data_sha256 + "\n";
  text += "hit_sets_sha256 " + header.hit_sets_sha256 + "\n";
  text += "field_tesla " + number_text(header.field_tesla) + "\n";
  text += "qop_status " + header.qop_status + "\n";
  text += "material_model " + header.material_model + "\n";
  text += "start_prior" + numbers_text(header.start_prior) + "\n";
  text += "acts_version " + header.acts_version + "\n";
  if (with_r33) {
    text += "r33_conventions " + header.r33_conventions + "\n";
    text += "alignment_parametrization " + header.alignment_parametrization + " " + header.alignment_frame + " " + header.alignment_level + "\n";
  }
  if (with_payload) {
    text += "alignment_payload " + header.alignment_payload_sha256 + " " + header.alignment_payload_origin + " " + header.alignment_payload_derived_against + " " +
            header.alignment_payload_derived_from + " " + header.alignment_payload_round + "\n";
  }
  for (const TrackRecord& track : document.tracks) {
    require_token(track.key, "track key");
    text += "track " + track.key + " " + std::to_string(track.event_ordinal) + " " + track.status + " " + track.failure_category + " " +
            std::to_string(track.measurements) + " " + std::to_string(track.holes) + " " + std::to_string(track.outliers) + " " +
            number_text(track.chi2) + " " + std::to_string(track.measured_coordinates) + " " + number_text(track.assumed_q_over_p) + "\n";
  }
  for (const StateRecord& state : document.states) {
    text += "state " + state.track_key + " " + std::to_string(state.index) + " " + std::to_string(state.plane) + " " + state.kind + " " +
            (state.hit_key < 0 ? std::string("none") : std::to_string(state.hit_key)) + " " + number_text(state.loc0_mm) + " " +
            number_text(state.loc1_mm) + numbers_text(state.covariance) + " " + number_text(state.path_length_mm) + " " + number_text(state.chi2) + "\n";
  }
  for (const ParameterRecord& record : document.parameters) {
    text += "parameters " + record.track_key + " " + std::to_string(record.state_index) + " " + record.state_type + numbers_text(record.parameters) +
            numbers_text(record.covariance) + "\n";
  }
  for (const TrackOutputRecord& output : document.track_outputs) {
    text += "track_output " + output.track_key + " " + std::to_string(output.charge) + " " + number_text(output.q_over_p) + " " + number_text(output.q_over_p_variance) +
            " " + std::to_string(output.reference_state_index) + " " + output.topology + " " + output.constraint + " " + output.field + "\n";
  }
  for (const ResidualRecord& residual : document.residuals) {
    text += "residual " + residual.track_key + " " + std::to_string(residual.state_index) + " " + residual.state_type + numbers_text(residual.residual) +
            numbers_text(residual.covariance) + "\n";
  }
  for (const MeasurementOutputRecord& output : document.measurement_outputs) {
    text += "measurement_output " + output.track_key + " " + std::to_string(output.state_index) + " " + std::to_string(output.geometry_id) + " " +
            std::to_string(output.projector[0]) + " " + std::to_string(output.projector[1]) + numbers_text(output.local_slope) + " " + number_text(output.incidence_rad) +
            " " + number_text(output.thickness_mm) + " " + number_text(output.path_factor) + " " + number_text(output.sensitive_path_mm) +
            numbers_text(output.alignment_derivative) + numbers_text(output.reference_derivative) + "\n";
  }
  for (const ResidualCovarianceRecord& record : document.residual_covariances) {
    text += "residual_covariance " + record.track_key + " " + std::to_string(record.measurement_count);
    for (const double value : record.covariance) {
      text += " " + number_text(value);
    }
    text += "\n";
  }
  text += "end " + std::to_string(document.tracks.size()) + " " + std::to_string(document.states.size()) + " " + std::to_string(document.parameters.size());
  if (with_r33) {
    text += " " + std::to_string(document.track_outputs.size()) + " " + std::to_string(document.residuals.size()) + " " +
            std::to_string(document.measurement_outputs.size()) + " " + std::to_string(document.residual_covariances.size());
  }
  return text + "\n";
}

ProductDocument decode_product(const std::string& text) {
  std::istringstream stream(text);
  std::string line;
  std::size_t line_number = 0;
  auto next_line = [&]() -> TokenLine {
    if (!std::getline(stream, line)) {
      throw std::runtime_error("the product ends before its end record");
    }
    return TokenLine(line, ++line_number);
  };
  auto keyed = [&](const std::string& key, std::size_t values) -> TokenLine {
    TokenLine fields = next_line();
    if (fields.size() != values + 1 || fields.text(0) != key) {
      fields.refuse("expected the record " + key);
    }
    return fields;
  };

  ProductDocument document;
  ProductHeader& header = document.header;
  {
    const TokenLine first = next_line();
    if (first.size() == 1 && first.text(0) == product_format) {
      document.format_version = 1;
    } else if (first.size() == 1 && first.text(0) == product_format_r33) {
      document.format_version = 2;
    } else {
      first.refuse("not " + std::string(product_format) + " or " + std::string(product_format_r33));
    }
  }
  const bool with_r33 = document.format_version == 2;
  header.product_id = keyed("product_id", 1).text(1);
  {
    const TokenLine fields = keyed("revision", 1);
    if (fields.integer(1) < 1) {
      fields.refuse("a revision starts at 1");
    }
    header.revision = fields.count(1);
  }
  header.recipe = keyed("recipe", 1).text(1);
  header.stage = keyed("stage", 1).text(1);
  header.evidence_class = keyed("evidence_class", 1).text(1);
  header.data_product = keyed("data_product", 1).text(1);
  header.data_sha256 = keyed("data_sha256", 1).text(1);
  header.hit_sets_sha256 = keyed("hit_sets_sha256", 1).text(1);
  header.field_tesla = keyed("field_tesla", 1).number(1);
  header.qop_status = keyed("qop_status", 1).text(1);
  if ((header.field_tesla == 0.0) != (header.qop_status == "assumed-not-measured")) {
    throw std::runtime_error("q/p is assumed at zero field, and only there");
  }
  header.material_model = keyed("material_model", 1).text(1);
  {
    const TokenLine fields = keyed("start_prior", 5);
    for (std::size_t index = 0; index < 5; ++index) {
      header.start_prior[index] = fields.number(index + 1);
    }
  }
  header.acts_version = keyed("acts_version", 1).text(1);
  if (with_r33) {
    header.r33_conventions = keyed("r33_conventions", 1).text(1);
    const TokenLine fields = keyed("alignment_parametrization", 3);
    header.alignment_parametrization = fields.text(1);
    header.alignment_frame = fields.text(2);
    header.alignment_level = fields.text(3);
    if (header.alignment_frame != "local" && header.alignment_frame != "global") {
      fields.refuse("an alignment frame is local or global (R32)");
    }
  }
  // D1 stage 9: the optional alignment_payload line, right after the header and before any record. The first record line is read here and, when it is not
  // that line, handed to the loop below unread.
  std::optional<TokenLine> pending;
  {
    TokenLine fields = next_line();
    if (fields.size() > 0 && fields.text(0) == "alignment_payload") {
      if (!with_r33 || fields.size() != 6) {
        fields.refuse("an alignment_payload line belongs to a /2 product and holds identity, origin, derived_against, derived_from and round");
      }
      header.alignment_payload_sha256 = fields.text(1);
      header.alignment_payload_origin = fields.text(2);
      header.alignment_payload_derived_against = fields.text(3);
      header.alignment_payload_derived_from = fields.text(4);
      header.alignment_payload_round = fields.text(5);
      if (header.alignment_payload_origin != "nominal" && header.alignment_payload_origin != "measured") {
        fields.refuse("an alignment payload's origin is nominal or measured (R32)");
      }
      // D1 stage 9 fix round 1, n4: the identities are 64 lowercase hexadecimal characters; the source may be none, the round none or a count.
      auto is_identity = [](const std::string& token) {
        return token.size() == 64 && token.find_first_not_of("0123456789abcdef") == std::string::npos;
      };
      const std::string& payload_round = header.alignment_payload_round;
      const bool round_is_count = !payload_round.empty() && payload_round.size() <= 9 && payload_round.find_first_not_of("0123456789") == std::string::npos && payload_round[0] != '0';
      if (!is_identity(header.alignment_payload_sha256) || !is_identity(header.alignment_payload_derived_against) ||
          (header.alignment_payload_derived_from != "none" && !is_identity(header.alignment_payload_derived_from)) || (payload_round != "none" && !round_is_count)) {
        fields.refuse("an alignment_payload line holds 64-character lowercase hexadecimal identities, a source that is one or none, and a round that is a count or none");
      }
    } else {
      pending.emplace(std::move(fields));
    }
  }

  std::set<std::string> track_keys;
  std::set<std::pair<std::string, std::int32_t>> state_keys;
  std::set<std::tuple<std::string, std::int32_t, std::string>> parameter_keys;
  std::map<std::pair<std::string, std::int32_t>, std::string> state_kind_of;
  std::map<std::string, std::string> status_of;
  std::set<std::string> output_keys;
  std::set<std::tuple<std::string, std::int32_t, std::string>> residual_keys;
  std::set<std::pair<std::string, std::int32_t>> measurement_output_keys;
  std::set<std::string> covariance_keys;
  std::map<std::string, std::int32_t> measured_of;  // measurement states per track, the residual covariance's size
  auto known_measurement = [&](const TokenLine& fields, const std::string& track_key, std::int32_t state_index) {
    const auto found = state_kind_of.find(std::make_pair(track_key, state_index));
    if (found == state_kind_of.end() || (found->second != "measurement" && found->second != "outlier")) {
      fields.refuse("an R33 record of a state that holds no hit of this product");
    }
  };
  while (true) {
    const TokenLine fields = pending.has_value() ? *pending : next_line();
    pending.reset();
    if (fields.size() == 0) {
      fields.refuse("an empty line");
    }
    const std::string& record = fields.text(0);
    if (record == "track" && fields.size() == 11) {
      TrackRecord track;
      track.key = fields.text(1);
      track.event_ordinal = fields.count(2);
      track.status = fields.text(3);
      track.failure_category = fields.text(4);
      if (track.status != "fitted" && track.status != "failed") {
        fields.refuse("unknown track status " + track.status);
      }
      if ((track.status == "failed") == (track.failure_category == "none")) {
        fields.refuse("a failed track states its category, and only a failed track");
      }
      track.measurements = fields.small_integer(5);
      track.holes = fields.small_integer(6);
      track.outliers = fields.small_integer(7);
      track.chi2 = fields.number(8);
      track.measured_coordinates = fields.small_integer(9);
      track.assumed_q_over_p = fields.number(10);
      if (!track_keys.insert(track.key).second) {
        fields.refuse("track key twice: " + track.key);
      }
      status_of[track.key] = track.status;
      document.tracks.push_back(track);
    } else if (record == "state" && fields.size() == 13) {
      StateRecord state;
      state.track_key = fields.text(1);
      state.index = fields.small_integer(2);
      state.plane = fields.small_integer(3);
      state.kind = fields.text(4);
      if (!is_one_of(state.kind, state_kinds)) {
        fields.refuse("unknown state kind " + state.kind);
      }
      state.hit_key = fields.text(5) == "none" ? -1 : fields.integer(5);
      if ((state.kind == "hole") != (state.hit_key < 0)) {
        fields.refuse("a hole has no hit, and every other state has one");
      }
      state.loc0_mm = fields.number(6);
      state.loc1_mm = fields.number(7);
      for (std::size_t index = 0; index < 3; ++index) {
        state.covariance[index] = fields.number(8 + index);
      }
      state.path_length_mm = fields.number(11);
      state.chi2 = fields.number(12);
      if (track_keys.count(state.track_key) == 0) {
        fields.refuse("a state of an unknown track");
      }
      if (!state_keys.insert(std::make_pair(state.track_key, state.index)).second) {
        fields.refuse("a state twice");
      }
      state_kind_of[std::make_pair(state.track_key, state.index)] = state.kind;
      measured_of[state.track_key] += state.kind == "measurement" ? 1 : 0;
      document.states.push_back(state);
    } else if (record == "parameters" && fields.size() == 31) {
      ParameterRecord parameters;
      parameters.track_key = fields.text(1);
      parameters.state_index = fields.small_integer(2);
      parameters.state_type = fields.text(3);
      if (!is_one_of(parameters.state_type, state_types)) {
        fields.refuse("unknown state type " + parameters.state_type);
      }
      for (std::size_t index = 0; index < 6; ++index) {
        parameters.parameters[index] = fields.number(4 + index);
      }
      for (std::size_t index = 0; index < 21; ++index) {
        parameters.covariance[index] = fields.number(10 + index);
      }
      if (state_keys.count(std::make_pair(parameters.track_key, parameters.state_index)) == 0) {
        fields.refuse("parameters of an unknown state");
      }
      if (!parameter_keys.insert(std::make_tuple(parameters.track_key, parameters.state_index, parameters.state_type)).second) {
        fields.refuse("parameters twice");
      }
      document.parameters.push_back(parameters);
    } else if (with_r33 && record == "track_output" && fields.size() == 9) {
      TrackOutputRecord output;
      output.track_key = fields.text(1);
      output.charge = fields.small_integer(2);
      output.q_over_p = fields.number(3);
      output.q_over_p_variance = fields.number(4);
      output.reference_state_index = fields.small_integer(5);
      output.topology = fields.text(6);
      output.constraint = fields.text(7);
      output.field = fields.text(8);
      const auto status = status_of.find(output.track_key);
      if (status == status_of.end() || status->second != "fitted") {
        fields.refuse("a track_output of a track that is not a fitted track of this product");
      }
      if (output.charge != 1 && output.charge != -1) {
        fields.refuse("a charge is +1 or -1");
      }
      if ((output.charge > 0) != (output.q_over_p > 0.0) || output.q_over_p == 0.0 || !(output.q_over_p_variance > 0.0)) {
        fields.refuse("the charge is the sign of q/p, and q/p has a positive variance");
      }
      if (!is_one_of(output.topology, topologies) || !is_one_of(output.constraint, constraints) || output.field != (header.field_tesla == 0.0 ? "off" : "on")) {
        fields.refuse("an unknown topology or constraint, or a field other than the header's");
      }
      known_measurement(fields, output.track_key, output.reference_state_index);
      if (!output_keys.insert(output.track_key).second) {
        fields.refuse("a track_output twice");
      }
      document.track_outputs.push_back(output);
    } else if (with_r33 && record == "residual" && fields.size() == 9) {
      ResidualRecord residual;
      residual.track_key = fields.text(1);
      residual.state_index = fields.small_integer(2);
      residual.state_type = fields.text(3);
      if (!is_one_of(residual.state_type, residual_types)) {
        fields.refuse("unknown residual type " + residual.state_type);
      }
      for (std::size_t index = 0; index < 2; ++index) {
        residual.residual[index] = fields.number(4 + index);
      }
      for (std::size_t index = 0; index < 3; ++index) {
        residual.covariance[index] = fields.number(6 + index);
      }
      known_measurement(fields, residual.track_key, residual.state_index);
      if (!residual_keys.insert(std::make_tuple(residual.track_key, residual.state_index, residual.state_type)).second) {
        fields.refuse("a residual twice");
      }
      document.residuals.push_back(residual);
    } else if (with_r33 && record == "measurement_output" && fields.size() == 36) {
      MeasurementOutputRecord output;
      output.track_key = fields.text(1);
      output.state_index = fields.small_integer(2);
      output.geometry_id = fields.unsigned_integer(3);
      if (output.geometry_id == 0) {
        fields.refuse("a geometry identifier is positive");
      }
      output.projector = {fields.small_integer(4), fields.small_integer(5)};
      output.local_slope = {fields.number(6), fields.number(7)};
      output.incidence_rad = fields.number(8);
      output.thickness_mm = fields.number(9);
      output.path_factor = fields.number(10);
      output.sensitive_path_mm = fields.number(11);
      for (std::size_t index = 0; index < 12; ++index) {
        output.alignment_derivative[index] = fields.number(12 + index);
        output.reference_derivative[index] = fields.number(24 + index);
      }
      known_measurement(fields, output.track_key, output.state_index);
      if (!measurement_output_keys.insert(std::make_pair(output.track_key, output.state_index)).second) {
        fields.refuse("a measurement_output twice");
      }
      document.measurement_outputs.push_back(output);
    } else if (with_r33 && record == "residual_covariance" && fields.size() >= 3) {
      ResidualCovarianceRecord covariance;
      covariance.track_key = fields.text(1);
      covariance.measurement_count = fields.small_integer(2);
      const auto status = status_of.find(covariance.track_key);
      if (status == status_of.end() || status->second != "fitted") {
        fields.refuse("a residual_covariance of a track that is not a fitted track of this product");
      }
      const std::int32_t measured = measured_of[covariance.track_key];
      const std::size_t size = std::size_t(2 * measured) * std::size_t(2 * measured + 1) / 2;
      if (covariance.measurement_count != measured || fields.size() != 3 + size) {
        fields.refuse("a residual_covariance that does not cover the track's measurements");
      }
      for (std::size_t index = 0; index < size; ++index) {
        covariance.covariance.push_back(fields.number(3 + index));
      }
      if (!covariance_keys.insert(covariance.track_key).second) {
        fields.refuse("a residual_covariance twice");
      }
      document.residual_covariances.push_back(covariance);
    } else if (record == "end" && fields.size() == (with_r33 ? 8u : 4u)) {
      if (std::size_t(fields.integer(1)) != document.tracks.size() || std::size_t(fields.integer(2)) != document.states.size() ||
          std::size_t(fields.integer(3)) != document.parameters.size()) {
        fields.refuse("the end record counts other numbers than the product holds");
      }
      if (with_r33 && (std::size_t(fields.integer(4)) != document.track_outputs.size() || std::size_t(fields.integer(5)) != document.residuals.size() ||
                       std::size_t(fields.integer(6)) != document.measurement_outputs.size() ||
                       std::size_t(fields.integer(7)) != document.residual_covariances.size())) {
        fields.refuse("the end record counts other R33 numbers than the product holds");
      }
      break;
    } else {
      fields.refuse("unknown record " + record);
    }
  }
  if (std::getline(stream, line)) {
    throw std::runtime_error("text after the end record");
  }
  if (with_r33) {  // R33 completeness: every state with a hit has all four residuals and its measurement output; every fitted track its track output
    for (const auto& [key, kind] : state_kind_of) {     // and, with a measurement, its residual covariance
      if (kind != "measurement" && kind != "outlier") {
        continue;
      }
      for (const char* type : residual_types) {
        if (residual_keys.count(std::make_tuple(key.first, key.second, std::string(type))) == 0) {
          throw std::runtime_error("a measurement state without its " + std::string(type) + " residual: " + key.first);
        }
      }
      if (measurement_output_keys.count(key) == 0) {
        throw std::runtime_error("a measurement state without its measurement_output: " + key.first);
      }
    }
    for (const auto& [key, status] : status_of) {
      if (status == "fitted" && output_keys.count(key) == 0) {
        throw std::runtime_error("a fitted track without its track_output: " + key);
      }
      if (status == "fitted" && measured_of[key] > 0 && covariance_keys.count(key) == 0) {
        throw std::runtime_error("a fitted track without its residual_covariance: " + key);
      }
    }
  }
  return document;
}

std::string read_whole_file(const std::string& path) {
  std::ifstream input(path, std::ios::binary);
  if (!input) {
    throw std::runtime_error("cannot open " + path);
  }
  std::ostringstream content;
  content << input.rdbuf();
  return content.str();
}

void write_whole_file(const std::string& path, const std::string& text) {
  std::ofstream output(path, std::ios::binary);
  output << text;
  output.close();
  if (!output) {
    throw std::runtime_error("cannot write " + path);
  }
}

}  // namespace t07
