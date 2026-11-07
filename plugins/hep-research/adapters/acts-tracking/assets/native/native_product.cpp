#include "native_product.hpp"

#include <cerrno>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <tuple>
#include <utility>

namespace t07 {
namespace {

constexpr std::array<const char*, 3> state_kinds{"measurement", "hole", "outlier"};
constexpr std::array<const char*, 3> state_types{"predicted", "filtered", "smoothed"};

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
  std::string text = std::string(product_format) + "\n";
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
  text += "end " + std::to_string(document.tracks.size()) + " " + std::to_string(document.states.size()) + " " +
          std::to_string(document.parameters.size()) + "\n";
  return text;
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
    if (first.size() != 1 || first.text(0) != product_format) {
      first.refuse("not " + std::string(product_format));
    }
  }
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

  std::set<std::string> track_keys;
  std::set<std::pair<std::string, std::int32_t>> state_keys;
  std::set<std::tuple<std::string, std::int32_t, std::string>> parameter_keys;
  while (true) {
    const TokenLine fields = next_line();
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
    } else if (record == "end" && fields.size() == 4) {
      if (std::size_t(fields.integer(1)) != document.tracks.size() || std::size_t(fields.integer(2)) != document.states.size() ||
          std::size_t(fields.integer(3)) != document.parameters.size()) {
        fields.refuse("the end record counts other numbers than the product holds");
      }
      break;
    } else {
      fields.refuse("unknown record " + record);
    }
  }
  if (std::getline(stream, line)) {
    throw std::runtime_error("text after the end record");
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
