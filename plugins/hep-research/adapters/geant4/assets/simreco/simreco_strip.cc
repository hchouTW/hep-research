// simreco_strip: stage 5 of the g4sim response pipeline, registered as `simreco-strip`. It reads a response-handoff/1
// file addressed to its stage, digitizes each crossing with simreco's strip model and writes the file for the next
// stage, so that core imports no part of it (g4sim plan, Section 10.1). C++17 standard library only, no Geant4.
//
// Rows in: {event, cell, y_mm, z_mm} with an optional sub_index. Rows out: the same with the cluster position, and
// sigma_y_mm, sigma_z_mm; a row lost to the efficiency is dropped. Each row is one sub-stream of the channel key, word 0
// the event, words 1-2 the cell and word 3 the sub-index, so a row's draws do not depend on the other rows, and two rows
// of one cell need different sub-indices. JSON numbers are doubles here, so a cell of 2^53 or more is refused. Output groups: 0 the y grid phase, 1 the z grid phase, 2 the
// efficiency. simreco's noise hits are not part of this stage: a hand-off row is a crossing, and a noise hit has none.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>

#include "MiniJson.hh"
#include "Philox.hh"
#include "StripDigitization.hh"

namespace {

constexpr const char* kSchema = "response-handoff/1";
constexpr const char* kUsage =
    "usage: simreco_strip --handoff-in PATH --handoff-out PATH --stage NAME --next-stage NAME --key0 N --key1 N\n"
    "                     --pitch-y-um X --pitch-z-um X --sharing-um X --threshold X --efficiency X\n"
    "--key0 and --key1 are the two words of core.simulation.rng.channel_key(run_seed, readout, stage, replica).\n";

struct Digitization {
  std::uint32_t key0 = 0, key1 = 0;
  double pitch_y = 0, pitch_z = 0, sharing = 0, threshold = 0, efficiency = 0;
};

// The first variate of an output group of the row's sub-stream, as core.simulation.rng.SubStream.group()[0].
double Draw(const Digitization& d, std::uint32_t event, std::uint64_t cell, std::uint32_t sub_index, std::uint32_t group) {
  g4sim::PhiloxWords counter = {event, static_cast<std::uint32_t>(cell), static_cast<std::uint32_t>(cell >> 32), sub_index << 16 | group};
  return g4sim::UniformsOf(g4sim::Philox4x32(counter, d.key0, d.key1))[0];
}

const minijson::Value& Field(const minijson::Value& row, const std::string& name) {
  auto found = row.obj.find(name);
  if (found == row.obj.end() || found->second.kind != minijson::Value::Kind::Number) throw std::runtime_error("a row has no number " + name);
  return found->second;
}

// A whole number in [0, limit): a double is exact below 2^53, and the casts below are defined only inside the range.
double Whole(const minijson::Value& row, const std::string& name, double limit) {
  const double value = Field(row, name).num;
  if (!(value >= 0. && value < limit) || value != std::floor(value)) throw std::runtime_error(name + " is not a whole number in range");
  return value;
}

std::string Number(double value) {
  char text[40];
  std::snprintf(text, sizeof text, "%.17g", value);
  return text;
}

int Run(const std::map<std::string, std::string>& options) {
  auto text = [&](const char* name) {
    auto found = options.find(name);
    if (found == options.end()) throw std::invalid_argument(std::string("missing --") + name);
    return found->second;
  };
  auto number = [&](const char* name) { return std::stod(text(name)); };
  Digitization d;
  d.key0 = static_cast<std::uint32_t>(std::stoull(text("key0")));
  d.key1 = static_cast<std::uint32_t>(std::stoull(text("key1")));
  d.pitch_y = number("pitch-y-um") * 1e-3;
  d.pitch_z = number("pitch-z-um") * 1e-3;
  d.sharing = number("sharing-um") * 1e-3;
  d.threshold = number("threshold");
  d.efficiency = number("efficiency");
  if (d.pitch_y <= 0 || d.pitch_z <= 0 || d.sharing < 0 || d.efficiency < 0 || d.efficiency > 1) throw std::invalid_argument("a strip parameter is out of range");
  const std::string stage = text("stage"), next_stage = text("next-stage");
  std::ifstream source(text("handoff-in"));
  if (!source) throw std::invalid_argument("cannot read --handoff-in");
  std::stringstream content;
  content << source.rdbuf();
  const minijson::Value document = minijson::parse(content.str());
  auto schema = document.obj.find("schema");
  auto addressee = document.obj.find("to");
  auto rows = document.obj.find("rows");
  if (schema == document.obj.end() || schema->second.str != kSchema || addressee == document.obj.end() || addressee->second.str != stage || rows == document.obj.end() || !rows->second.isArray())
    throw std::runtime_error("not a hand-off to " + stage);
  const double sigma_y = StripClusterSigma(d.pitch_y, d.sharing, d.threshold), sigma_z = StripClusterSigma(d.pitch_z, d.sharing, d.threshold);
  std::ofstream target(text("handoff-out"));
  if (!target) throw std::invalid_argument("cannot write --handoff-out");
  target << "{\"schema\": \"" << kSchema << "\", \"from\": \"" << stage << "\", \"to\": \"" << next_stage << "\", \"rows\": [";
  std::size_t kept = 0;
  std::set<std::tuple<std::uint32_t, std::uint64_t, std::uint32_t>> seen;
  for (const minijson::Value& row : rows->second.arr) {
    const double event_number = Whole(row, "event", 4294967296.), cell_number = Whole(row, "cell", 9007199254740992.);
    const auto event = static_cast<std::uint32_t>(event_number);
    const auto cell = static_cast<std::uint64_t>(cell_number);
    const auto sub_index = row.obj.count("sub_index") ? static_cast<std::uint32_t>(Whole(row, "sub_index", 65536.)) : 0u;
    if (!seen.insert({event, cell, sub_index}).second) throw std::runtime_error("two rows share an event, a cell and a sub_index, so they would share their draws");
    if (Draw(d, event, cell, sub_index, 2) >= d.efficiency) continue;
    const double y = StripCluster(Field(row, "y_mm").num, Draw(d, event, cell, sub_index, 0) * d.pitch_y, d.pitch_y, d.sharing, d.threshold);
    const double z = StripCluster(Field(row, "z_mm").num, Draw(d, event, cell, sub_index, 1) * d.pitch_z, d.pitch_z, d.sharing, d.threshold);
    target << (kept++ ? ",\n" : "\n") << "{\"event\": " << Number(event_number) << ", \"cell\": " << Number(cell_number) << ", \"y_mm\": " << Number(y) << ", \"z_mm\": " << Number(z)
           << (sub_index ? ", \"sub_index\": " + std::to_string(sub_index) : "") << ", \"sigma_y_mm\": " << Number(sigma_y) << ", \"sigma_z_mm\": " << Number(sigma_z) << "}";
  }
  target << "\n]}\n";
  target.close();
  if (!target) throw std::runtime_error("could not finish --handoff-out");
  std::cout << "{\"status\": \"ok\", \"rows_in\": " << rows->second.arr.size() << ", \"rows_out\": " << kept << "}\n";
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  std::map<std::string, std::string> options;
  for (int at = 1; at < argc; ++at) {
    const std::string word = argv[at];
    if (word == "--help") {
      std::cout << kUsage;
      return 0;
    }
    if (word.rfind("--", 0) != 0 || at + 1 >= argc) {
      std::cerr << kUsage;
      return 2;
    }
    options[word.substr(2)] = argv[++at];
  }
  try {
    return Run(options);
  } catch (const std::invalid_argument& error) {
    std::cout << "{\"status\": \"failed\", \"error_kind\": \"bad-input\"}\n";
    std::cerr << "simreco_strip: " << error.what() << "\n";
    return 2;
  } catch (const std::exception& error) {
    std::cout << "{\"status\": \"failed\", \"error_kind\": \"failed\"}\n";
    std::cerr << "simreco_strip: " << error.what() << "\n";
    return 1;
  }
}
