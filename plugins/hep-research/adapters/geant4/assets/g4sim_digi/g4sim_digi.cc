// g4sim_digi: the digitization of scintillation bins in C++ (g4sim plan, Section 10.5, S8), built because the Python response pipeline
// cannot meet the throughput budget (g4sim-performance-budget.md). No Geant4: the C++17 standard library and the shared headers.
// Written for this plugin (no example code copied or adapted); LogGamma in Samplers.hh is adapted from CPython (see there).
//
// core/simulation/digitize.py is normative and this follows it draw for draw: per (event, volume) the yield factor; per bin, on the volume
// stream of the scintillation stage at sub-index bin, N_b (Section 10.3) and its multinomial in channel order, then, with timing on, a time
// per detected photon in blocks of 2^15 photons, each block its own key; per channel, cell = volume x channels + channel, the sensor and the
// electronics on their channel streams. The keys come in the job, computed in Python with canonical/1.
//
// Usage: g4sim_digi JOB BINS CHANNELS_OUT [TIMES_OUT]   or   g4sim_digi --uniforms KEY0 KEY1 EVENT IDENTITY SUB N
//   JOB       a g4sim-digi-job/1 with its keys (digitize.job_with_keys)
//   BINS      CSV rows event,volume,bin,E_large_MeV,E_small_MeV,n_large (numbers as Python writes them; hex floats are exact)
//   CHANNELS  out: event,volume,channel,photoelectrons,charge,code (code -1 below threshold), sorted by event, volume, channel
//   TIMES     out (with timing on): event,volume,bin,channel,time_ns, sorted by event, volume, bin, channel, in draw order within
// A continuous value is written as the 16 hex digits of its IEEE 754 bits, exact and much cheaper than %a: a time row per detected photon
// made printing the larger part of the work (digitize.py's from_bits reads it).
// Exit 0 done, 2 bad input. Compile with -ffp-contract=off and without -ffast-math (Samplers.hh, Philox.hh).
#include <algorithm>
#include <charconv>
#include <cstring>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

#include "MiniJson.hh"
#include "Samplers.hh"

using minijson::Value;

namespace {

constexpr long long kPhotonBlock = 1LL << 15;
constexpr double kPoissonLimit = 10.0;
constexpr double kRoundingVariance = 1.0 / 12.0;

// Rows go through one buffer; integers by std::to_chars and doubles as their bits, so no printf format is parsed per photon
class RowWriter {
 public:
  explicit RowWriter(const std::string& path) : fOut(std::fopen(path.c_str(), "w")) {
    if (!fOut) throw std::runtime_error("cannot write " + path);
    fBuffer.reserve(1 << 20);
  }
  ~RowWriter() {
    Flush();
    std::fclose(fOut);
  }
  RowWriter& Int(long long value) {
    char text[24];
    const auto end = std::to_chars(text, text + sizeof text, value).ptr;
    fBuffer.append(text, end);
    fBuffer.push_back(',');
    return *this;
  }
  RowWriter& Unsigned(unsigned long long value) {
    char text[24];
    const auto end = std::to_chars(text, text + sizeof text, value).ptr;
    fBuffer.append(text, end);
    fBuffer.push_back(',');
    return *this;
  }
  RowWriter& Bits(double value) {
    std::uint64_t bits;
    std::memcpy(&bits, &value, sizeof bits);
    static const char* digits = "0123456789abcdef";
    for (int shift = 60; shift >= 0; shift -= 4) fBuffer.push_back(digits[(bits >> shift) & 0xF]);
    fBuffer.push_back(',');
    return *this;
  }
  void End() {
    fBuffer.back() = '\n';
    if (fBuffer.size() > (1u << 20)) Flush();
  }

 private:
  void Flush() {
    std::fwrite(fBuffer.data(), 1, fBuffer.size(), fOut);
    fBuffer.clear();
  }
  std::FILE* fOut;
  std::string fBuffer;
};

struct Bin {
  double large = 0, small = 0;
  long long steps = 0;
};

g4sim::StreamKey KeyOf(const Value& pair, const std::string& where) {
  const auto& words = pair.array(where);
  if (words.size() != 2) throw minijson::JsonError(where + ": a key is two 32-bit words");
  return {static_cast<std::uint32_t>(words[0].number(where)), static_cast<std::uint32_t>(words[1].number(where))};
}

struct Job {
  std::string stageName;
  double lightYield = 0, resolutionScale = 0, yieldWidth = 0;
  std::size_t channels = 0;
  std::map<long long, std::vector<double>> efficiencies;
  bool timing = false, mapped = false;
  double decayNs = 0, riseNs = 0, transitNs = 0;
  std::vector<double> edges;
  std::map<long long, std::vector<long long>> transitCounts;
  double gain = 0, excessNoise = 0, darkRate = 0, gateNs = 0;
  double noiseSigma = 0, threshold = 0, lsb = 0;
  int bits = 0;
  g4sim::StreamKey stageKey, yieldKey, sensorKey, electronicsKey;
  std::vector<g4sim::StreamKey> timeKeys;
};

Job ReadJob(const Value& j) {
  if (j.at("schema", "job").str != "g4sim-digi-job/1") throw minijson::JsonError("job: not a g4sim-digi-job/1");
  Job job;
  const Value& stage = j.at("stage", "job");
  job.stageName = stage.at("name", "stage").str;
  job.lightYield = stage.at("light_yield_per_MeV", "stage").number("light_yield_per_MeV");
  job.resolutionScale = stage.at("resolution_scale", "stage").number("resolution_scale");
  if (stage.has("yield_relative_width")) job.yieldWidth = stage.obj.at("yield_relative_width").number("yield_relative_width");
  job.channels = j.at("channels", "job").array("channels").size();
  for (const auto& [bin, values] : j.at("efficiencies", "job").obj) {
    std::vector<double> row;
    for (const auto& value : values.array("efficiencies")) row.push_back(value.number("efficiency"));
    if (row.size() != job.channels) throw minijson::JsonError("efficiencies of bin " + bin + ": one per channel");
    job.efficiencies[std::stoll(bin)] = row;
  }
  if (j.has("timing") && j.obj.at("timing").isObject()) {
    const Value& timing = j.obj.at("timing");
    job.timing = true;
    job.decayNs = timing.at("decay_ns", "timing").number("decay_ns");
    if (timing.has("rise_ns")) job.riseNs = timing.obj.at("rise_ns").number("rise_ns");
    const Value& transit = timing.at("transit", "timing");
    const std::string kind = transit.at("kind", "transit").str;
    if (kind == "exponential") {
      job.transitNs = transit.at("transit_ns", "transit").number("transit_ns");
    } else if (kind == "mapped") {
      job.mapped = true;
      for (const auto& edge : transit.at("edges_ns", "transit").array("edges_ns")) job.edges.push_back(edge.number("edge"));
      for (const auto& [bin, counts] : transit.at("counts", "transit").obj) {
        std::vector<long long> row;
        for (const auto& count : counts.array("counts")) row.push_back(static_cast<long long>(count.number("count")));
        job.transitCounts[std::stoll(bin)] = row;
      }
    } else {
      throw minijson::JsonError("transit kind " + kind);
    }
  }
  const Value& sensor = j.at("sensor", "job");
  job.gain = sensor.at("gain", "sensor").number("gain");
  job.excessNoise = sensor.at("excess_noise", "sensor").number("excess_noise");
  job.darkRate = sensor.at("dark_rate_per_ns", "sensor").number("dark_rate_per_ns");
  job.gateNs = sensor.at("gate_ns", "sensor").number("gate_ns");
  const Value& electronics = j.at("electronics", "job");
  job.noiseSigma = electronics.at("noise_sigma", "electronics").number("noise_sigma");
  job.threshold = electronics.at("threshold", "electronics").number("threshold");
  job.lsb = electronics.at("lsb", "electronics").number("lsb");
  job.bits = static_cast<int>(electronics.at("bits", "electronics").number("bits"));
  const Value& keys = j.at("keys", "job");
  job.stageKey = KeyOf(keys.at("stage", "keys"), "keys.stage");
  job.yieldKey = KeyOf(keys.at("yield", "keys"), "keys.yield");
  job.sensorKey = KeyOf(keys.at("sensor", "keys"), "keys.sensor");
  job.electronicsKey = KeyOf(keys.at("electronics", "keys"), "keys.electronics");
  for (const auto& pair : keys.at("time_blocks", "keys").array("time_blocks")) job.timeKeys.push_back(KeyOf(pair, "keys.time_blocks"));
  return job;
}

// response.bin_photons
long long BinPhotons(g4sim::SubStream& stream, const Job& job, const Bin& bin, double factor) {
  double mean = job.lightYield * (bin.large + bin.small);
  const double variance = std::pow(job.resolutionScale, 2.0) * job.lightYield * bin.large + job.lightYield * bin.small + static_cast<double>(bin.steps) * kRoundingVariance;
  mean *= factor;
  if (mean <= kPoissonLimit) return stream.Poisson(mean);
  const double width = std::sqrt(std::max(variance * factor - kRoundingVariance, 0.0));
  return std::max(static_cast<long long>(std::floor(stream.Gaussian(mean, width) + 0.5)), 0LL);
}

// efficiency_map.transit_ns
double MappedTransit(const Job& job, long long bin, double uniform) {
  auto found = job.transitCounts.find(bin);
  if (found == job.transitCounts.end()) throw g4sim::StreamError("map-bin", "bin " + std::to_string(bin) + " has no arrival-time distribution");
  long long total = 0;
  for (long long count : found->second) total += count;
  if (total == 0) throw g4sim::StreamError("map-transit", "bin " + std::to_string(bin) + " detected no photon");
  const double target = uniform * static_cast<double>(total);
  double running = 0.0;
  for (std::size_t at = 0; at < found->second.size(); ++at) {
    const long long count = found->second[at];
    if (count && running + static_cast<double>(count) >= target) return job.edges[at] + (target - running) / static_cast<double>(count) * (job.edges[at + 1] - job.edges[at]);
    running += static_cast<double>(count);
  }
  return job.edges.back();
}

// response.photon_times
std::vector<double> PhotonTimes(const Job& job, long long event, unsigned long long volume, long long bin, long long photons) {
  std::vector<double> times;
  times.reserve(static_cast<std::size_t>(photons));
  for (long long start = 0; start < photons; start += kPhotonBlock) {
    const std::size_t block = static_cast<std::size_t>(start / kPhotonBlock);
    if (block >= job.timeKeys.size()) throw g4sim::StreamError("time-blocks", "the job carries keys for " + std::to_string(job.timeKeys.size()) + " photon blocks");
    g4sim::SubStream stream(job.timeKeys[block], static_cast<std::uint64_t>(event), volume, static_cast<std::uint32_t>(bin));
    for (long long at = 0; at < std::min(kPhotonBlock, photons - start); ++at) {
      const auto g = stream.Group();
      const double delay = -job.decayNs * std::log(g[0]) - (job.riseNs > 0 ? job.riseNs * std::log(stream.Group()[0]) : 0.0);
      const double transit = job.mapped ? MappedTransit(job, bin, g[1]) : -job.transitNs * std::log(g[1]);
      times.push_back(delay + transit);
    }
  }
  return times;
}

int Run(const std::string& jobPath, const std::string& binsPath, const std::string& channelsPath, const std::string& timesPath) {
  std::ifstream jobFile(jobPath);
  std::stringstream text;
  text << jobFile.rdbuf();
  const Job job = ReadJob(minijson::parse(text.str()));
  if (job.timing && timesPath.empty()) throw minijson::JsonError("timing is on: name the times file");
  std::map<std::pair<long long, unsigned long long>, std::map<long long, Bin>> grouped;
  std::set<std::tuple<long long, unsigned long long, long long>> seen;
  std::ifstream bins(binsPath);
  std::string line;
  while (std::getline(bins, line)) {
    if (line.empty()) continue;
    std::vector<std::string> fields;
    std::stringstream row(line);
    std::string field;
    while (std::getline(row, field, ',')) fields.push_back(field);
    if (fields.size() != 6) throw minijson::JsonError("a bins row has six fields: " + line);
    const long long event = std::stoll(fields[0]);
    const unsigned long long volume = std::stoull(fields[1]);
    const long long bin = std::stoll(fields[2]);
    if (!seen.insert({event, volume, bin}).second) throw g4sim::StreamError("bin-twice", "event " + fields[0] + ", volume " + fields[1] + ": bin " + fields[2] + " appears twice");
    grouped[{event, volume}][bin] = {std::strtod(fields[3].c_str(), nullptr), std::strtod(fields[4].c_str(), nullptr), std::stoll(fields[5])};
  }
  RowWriter channels(channelsPath);
  std::unique_ptr<RowWriter> times(job.timing ? new RowWriter(timesPath) : nullptr);
  for (const auto& [where, binRows] : grouped) {
    const auto& [event, volume] = where;
    double factor = 1.0;
    if (job.yieldWidth > 0) {  // response.yield_factor
      const double shape = 1.0 / std::pow(job.yieldWidth, 2.0);
      factor = g4sim::SubStream(job.yieldKey, static_cast<std::uint64_t>(event), volume).Gamma(shape) / shape;
    }
    std::vector<long long> photoelectrons(job.channels, 0);
    for (const auto& [binIndex, bin] : binRows) {
      auto efficiencies = job.efficiencies.find(binIndex);
      if (efficiencies == job.efficiencies.end()) throw g4sim::StreamError("efficiencies", "bin " + std::to_string(binIndex) + " has no efficiencies");
      g4sim::SubStream stream(job.stageKey, static_cast<std::uint64_t>(event), volume, static_cast<std::uint32_t>(binIndex));
      const long long photons = BinPhotons(stream, job, bin, factor);
      std::vector<long long> counts = stream.Multinomial(photons, efficiencies->second);
      counts.resize(job.channels);
      long long detected = 0;
      for (std::size_t at = 0; at < job.channels; ++at) photoelectrons[at] += counts[at], detected += counts[at];
      if (job.timing && detected) {
        const std::vector<double> drawn = PhotonTimes(job, event, volume, binIndex, detected);
        std::size_t start = 0;
        for (std::size_t at = 0; at < job.channels; ++at)
          for (long long k = 0; k < counts[at]; ++k) times->Int(event).Unsigned(volume).Int(binIndex).Unsigned(at).Bits(drawn[start++]).End();
      }
    }
    for (std::size_t at = 0; at < job.channels; ++at) {
      const unsigned long long cell = volume * job.channels + at;
      g4sim::SubStream sensor(job.sensorKey, static_cast<std::uint64_t>(event), cell);
      const long long total = photoelectrons[at] + sensor.Poisson(job.darkRate * job.gateNs);  // response.sensor_response
      const double charge = total ? std::max(sensor.Gaussian(static_cast<double>(total) * job.gain, job.excessNoise * job.gain * std::sqrt(static_cast<double>(total))), 0.0) : 0.0;
      g4sim::SubStream electronics(job.electronicsKey, static_cast<std::uint64_t>(event), cell);
      const double signal = electronics.Gaussian(charge, job.noiseSigma);  // response.electronics_response
      const long long top = (1LL << job.bits) - 1;
      const long long code = signal < job.threshold ? -1 : std::min(static_cast<long long>(signal / job.lsb), top);
      channels.Int(event).Unsigned(volume).Unsigned(at).Int(photoelectrons[at]).Bits(charge).Int(code).End();
    }
  }
  return 0;
}

}  // namespace

// --uniforms KEY0 KEY1 EVENT IDENTITY SUB N: the first N output groups of one sub-stream, two variates per line as %a (gate 2, level 1)
int Uniforms(char** argv) {
  g4sim::SubStream stream({static_cast<std::uint32_t>(std::stoul(argv[2])), static_cast<std::uint32_t>(std::stoul(argv[3]))}, std::stoull(argv[4]), std::stoull(argv[5]),
                          static_cast<std::uint32_t>(std::stoul(argv[6])));
  for (long long at = 0, n = std::stoll(argv[7]); at < n; ++at) {
    const auto g = stream.Group();
    std::printf("%a,%a\n", g[0], g[1]);
  }
  return 0;
}

int main(int argc, char** argv) {
  if (argc == 8 && std::string(argv[1]) == "--uniforms") {
    try {
      return Uniforms(argv);
    } catch (const std::exception& err) {
      std::cerr << "g4sim_digi: " << err.what() << std::endl;
      return 2;
    }
  }
  if (argc != 4 && argc != 5) {
    std::cerr << "usage: g4sim_digi JOB BINS CHANNELS_OUT [TIMES_OUT]" << std::endl;
    return 2;
  }
  try {
    return Run(argv[1], argv[2], argv[3], argc == 5 ? argv[4] : "");
  } catch (const std::exception& err) {
    std::cerr << "g4sim_digi: " << err.what() << std::endl;
    return 2;
  }
}
