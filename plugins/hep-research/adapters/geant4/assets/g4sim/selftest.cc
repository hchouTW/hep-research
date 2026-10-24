// g4sim/selftest.cc: a Geant4-free driver of SimHash.hh and SimSummary.hh for tests/adapters/test_g4sim.py, which
// compares its output with core/simulation/seeds.py, Python's float.hex() and core/simulation/summary.py.
// Build: c++ -std=c++17 -O2 -ffp-contract=off -I. selftest.cc -o g4sim_selftest
// Usage: g4sim_selftest REQUEST.json   (prints one JSON object)
// REQUEST: {"seed_hash": [[part, ...], ...], "float_hex": ["<64-bit pattern as 16 hex digits>", ...],
//           "splitmix": {"seed": "<decimal>", "n": N}, "box_muller": {"seed": "<decimal>", "n": N},
//           "summary": {"observables": [...], "block_size": B, "blocks": K, "first_event": E, "rows": [{...}, ...],
//                       "split": S}}   (S > 1: the rows are filled into S accumulators in turn, then merged)
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>

#include "MiniJson.hh"
#include "SimHash.hh"
#include "SimObservables.hh"
#include "SimSummary.hh"

using minijson::Value;

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "usage: g4sim_selftest REQUEST.json\n";
    return 2;
  }
  std::ifstream in(argv[1]);
  std::stringstream buf;
  buf << in.rdbuf();
  Value req = minijson::parse(buf.str());
  std::ostringstream out;
  out << "{";
  bool first = true;
  auto key = [&](const char* k) {
    out << (first ? "" : ", ") << "\"" << k << "\": ";
    first = false;
  };
  if (req.has("seed_hash")) {
    key("seed_hash");
    out << "[";
    bool f = true;
    for (const auto& parts : req.obj.at("seed_hash").array("seed_hash")) {
      std::string joined;
      // H over the parts as given (numbers as integers in decimal, strings as they are)
      std::vector<g4sim::HashPart> ps;
      for (const auto& p : parts.array("parts"))
        ps.push_back(p.isString() ? g4sim::HashPart(p.str) : g4sim::HashPart(static_cast<long long>(p.num)));
      long h = 0;
      switch (ps.size()) {
        case 1: h = g4sim::SeedHash({ps[0]}); break;
        case 2: h = g4sim::SeedHash({ps[0], ps[1]}); break;
        case 3: h = g4sim::SeedHash({ps[0], ps[1], ps[2]}); break;
        default: h = g4sim::SeedHash({ps[0], ps[1], ps[2], ps[3]}); break;
      }
      out << (f ? "" : ", ") << h;
      f = false;
    }
    out << "]";
  }
  if (req.has("float_hex")) {
    key("float_hex");
    out << "[";
    bool f = true;
    for (const auto& p : req.obj.at("float_hex").array("float_hex")) {
      std::uint64_t bits = std::strtoull(p.str.c_str(), nullptr, 16);
      double x;
      std::memcpy(&x, &bits, sizeof x);
      out << (f ? "" : ", ") << g4sim::SummaryAccumulator::Quote(g4sim::PyFloatHex(x));
      f = false;
    }
    out << "]";
  }
  if (req.has("splitmix")) {
    const Value& s = req.obj.at("splitmix");
    g4sim::SplitMix64 r(std::strtoull(s.at("seed", "splitmix").str.c_str(), nullptr, 10));
    key("splitmix");
    out << "[";
    for (int i = 0; i < static_cast<int>(s.at("n", "splitmix").num); ++i) out << (i ? ", " : "") << "\"" << r.Next() << "\"";
    out << "]";
  }
  if (req.has("box_muller")) {
    const Value& s = req.obj.at("box_muller");
    g4sim::BoxMuller r(std::strtoull(s.at("seed", "box_muller").str.c_str(), nullptr, 10));
    key("box_muller");
    out << "[";
    for (int i = 0; i < static_cast<int>(s.at("n", "box_muller").num); ++i)
      out << (i ? ", " : "") << g4sim::SummaryAccumulator::Num(r.Next());
    out << "]";
  }
  if (req.has("summary")) {
    const Value& s = req.obj.at("summary");
    auto decls = g4sim::ParseObservables(s.at("observables", "summary"), "observables");
    long b = static_cast<long>(s.at("block_size", "summary").num), k = static_cast<long>(s.at("blocks", "summary").num);
    long f0 = static_cast<long>(s.at("first_event", "summary").num);
    int split = s.has("split") ? static_cast<int>(s.obj.at("split").num) : 1;
    std::vector<g4sim::SummaryAccumulator> parts;
    for (int i = 0; i < split; ++i) parts.emplace_back(decls, b, k, f0);
    int i = 0;
    for (const auto& r : s.at("rows", "summary").array("rows")) {
      g4sim::Row row;
      for (const auto& kv : r.obj) row[kv.first] = g4sim::ToCell(kv.second, "row");
      parts[static_cast<std::size_t>(i++ % split)].Fill(static_cast<long>(row["event"].num), row);
    }
    for (int j = 1; j < split; ++j) parts[0].Merge(parts[static_cast<std::size_t>(j)]);
    key("summary");
    out << parts[0].Json("{}", "{\"name\": \"layered_sim\"}");
  }
  out << "}\n";
  std::cout << out.str();
  return 0;
}
