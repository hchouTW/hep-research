// Fixture generators t07-telescope-clean/1 and t07-telescope-noise/1, t04-values-v4.md sections 3.2 and 4.1. Synthetic design
// values, no detector implied. Check: check_t07_generator.py. Writes a data file and, apart, a truth file with role truth.
//
//   t07_fixture_generator generate --fixture clean|noise --block B --stratum S --first-event I --count C --data-file D --truth-file T
//   t07_fixture_generator seed-vector --fixture-id F --block B --stratum S --event-index I --draws N
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <filesystem>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "plane_propagation.hpp"
#include "t07_event_generator.hpp"
#include "telescope_geometry.hpp"

namespace {

std::map<std::string, std::string> parse_flags(int argc, char** argv, int first) {
  std::map<std::string, std::string> flags;
  for (int index = first; index < argc; index += 2) {
    const std::string flag = argv[index];
    if (flag.rfind("--", 0) != 0 || index + 1 >= argc) {
      throw std::invalid_argument("expected --flag value, got " + flag);
    }
    flags[flag.substr(2)] = argv[index + 1];
  }
  return flags;
}

std::string required(const std::map<std::string, std::string>& flags, const std::string& name) {
  const auto found = flags.find(name);
  if (found == flags.end()) {
    throw std::invalid_argument("--" + name + " is required");
  }
  return found->second;
}

std::uint64_t required_integer(const std::map<std::string, std::string>& flags, const std::string& name) {
  const std::string text = required(flags, name);
  std::size_t used = 0;
  unsigned long long value = 0;
  try {
    value = std::stoull(text, &used);
  } catch (const std::out_of_range&) {
    throw std::invalid_argument("--" + name + " does not fit 64 bits: " + text);
  }
  if (used != text.size() || text[0] == '-') {
    throw std::invalid_argument("--" + name + " is not a non-negative integer: " + text);
  }
  return value;
}

std::uint32_t required_small_integer(const std::map<std::string, std::string>& flags, const std::string& name) {
  const std::uint64_t value = required_integer(flags, name);
  if (value > std::numeric_limits<std::uint32_t>::max()) {
    throw std::invalid_argument("--" + name + " does not fit 32 bits: " + std::to_string(value));
  }
  return std::uint32_t(value);
}

void require_only(const std::map<std::string, std::string>& flags, const std::set<std::string>& known) {
  for (const auto& [name, value] : flags) {
    if (known.count(name) == 0) {
      throw std::invalid_argument("unknown flag --" + name);
    }
  }
}

int generate(const std::map<std::string, std::string>& flags) {
  require_only(flags, {"fixture", "block", "stratum", "first-event", "count", "data-file", "truth-file"});
  const std::string fixture_name = required(flags, "fixture");
  if (fixture_name != "clean" && fixture_name != "noise") {
    throw std::invalid_argument("--fixture is clean or noise, not " + fixture_name);
  }
  const t07::FixtureSpec fixture = t07::fixture_spec(fixture_name == "clean" ? t07::FixtureKind::clean : t07::FixtureKind::noise);
  const std::uint32_t block = required_small_integer(flags, "block");
  if (std::find(t07::known_blocks.begin(), t07::known_blocks.end(), block) == t07::known_blocks.end()) {
    throw std::invalid_argument("--block is not a block of section 3.2: " + std::to_string(block));
  }
  const std::uint32_t stratum = required_small_integer(flags, "stratum");
  if (stratum >= std::uint32_t(t07::stratum_count)) {
    throw std::invalid_argument("--stratum is 0 to 11, not " + std::to_string(stratum));
  }
  const std::uint64_t first_event = required_integer(flags, "first-event");
  const std::uint32_t count = required_small_integer(flags, "count");
  if (first_event > std::numeric_limits<std::uint64_t>::max() - count) {
    throw std::invalid_argument("--first-event plus --count overflows");
  }
  const std::string data_path = required(flags, "data-file");
  const std::string truth_path = required(flags, "truth-file");
  if (std::filesystem::weakly_canonical(data_path) == std::filesystem::weakly_canonical(truth_path)) {
    throw std::invalid_argument("--data-file and --truth-file name one file");
  }

  t07::DataFileHeader data_header;
  data_header.event_count = count;
  data_header.sigma_loc0_mm = t07::hit_sigma_mm;
  data_header.sigma_loc1_mm = t07::hit_sigma_mm;
  t07::TruthFileHeader truth_header;
  truth_header.generator = fixture.generator;
  truth_header.fixture_id = fixture.fixture_id;
  truth_header.block = block;
  truth_header.stratum = stratum;
  truth_header.event_count = count;
  truth_header.sigma_loc0_mm = t07::hit_sigma_mm;
  truth_header.sigma_loc1_mm = t07::hit_sigma_mm;

  // Events leave in the order of their seed digests, so position in the file does not follow event_index (the near rule is
  // event_index mod 5). This hides it from a reader without the four integers only: enumerating them with SHA-256 gives the order
  // back, under the limit stated in t07_data_file.hpp. Each event stays a pure function of its four integers.
  std::vector<std::pair<t07::Sha256Digest, std::uint64_t>> file_order;
  file_order.reserve(count);
  for (std::uint64_t event_index = first_event; event_index < first_event + count; ++event_index) {
    file_order.emplace_back(t07::event_seed_digest(fixture.fixture_id, block, stratum, event_index), event_index);
  }
  std::sort(file_order.begin(), file_order.end());

  const t07::TelescopeGeometry telescope = t07::build_telescope_geometry();
  const t07::PlanePropagation propagation(telescope, t07::field_tesla);
  t07::DataFileWriter data_writer(data_path, data_header);
  t07::TruthFileWriter truth_writer(truth_path, truth_header);
  for (const auto& [digest, event_index] : file_order) {
    const t07::GeneratedEvent event = t07::generate_event(fixture, block, stratum, event_index, propagation);
    data_writer.write(event.data);
    truth_writer.write(event.truth);
  }
  data_writer.close();
  truth_writer.close(t07::sha256_digest_of_file(data_path));
  std::cout << "{\"status\": \"ok\", \"generator\": \"" << fixture.generator << "\", \"events\": " << count << "}\n";
  return 0;
}

int seed_vector(const std::map<std::string, std::string>& flags) {
  require_only(flags, {"fixture-id", "block", "stratum", "event-index", "draws"});
  const t07::Sha256Digest digest =
      t07::event_seed_digest(required_integer(flags, "fixture-id"), required_integer(flags, "block"), required_integer(flags, "stratum"),
                             required_integer(flags, "event-index"));
  std::cout << "digest " << t07::hex_of(digest) << "\n";
  t07::EventSeedStream stream(digest);
  const std::uint64_t draws = required_integer(flags, "draws");
  for (std::uint64_t draw = 0; draw < draws; ++draw) {
    std::printf("raw %016llx\n", static_cast<unsigned long long>(stream.next_raw()));
  }
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const std::string command = argc > 1 ? argv[1] : "";
    const auto flags = parse_flags(argc, argv, 2);
    if (command == "generate") {
      return generate(flags);
    }
    if (command == "seed-vector") {
      return seed_vector(flags);
    }
    throw std::invalid_argument("the command is generate or seed-vector");
  } catch (const std::invalid_argument& error) {
    std::cerr << "invalid input: " << error.what() << "\n";
    return 2;
  } catch (const std::exception& error) {
    std::cerr << "failed: " << error.what() << "\n";
    return 3;
  }
}
