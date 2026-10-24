// g4sim/SimCsv.hh: per-event CSV writing helpers (adapters/geant4, Geant4 program A2.1; moved from layered_sim without
// change of behaviour). C++17 standard library only.
#ifndef G4SIM_SIMCSV_HH
#define G4SIM_SIMCSV_HH

#include <algorithm>
#include <cstdio>
#include <fstream>
#include <string>
#include <utility>
#include <vector>

namespace g4sim {

// A CSV number: 10 significant digits (the per-event CSV format of layered_sim.output/1).
inline std::string Fmt(double x) {
  char buf[40];
  std::snprintf(buf, sizeof buf, "%.10g", x);
  return buf;
}

// Per-thread files (path.thread<N>, N < threads) joined into `path` in event order: the first `headerLines` lines of
// the first file that exists, then every data row of every file sorted by its leading integer (the event number); the
// per-thread files are removed.
inline void MergeThreadFiles(const std::string& path, int threads, int headerLines) {
  std::vector<std::pair<long, std::string>> rows;
  std::string header;
  for (int t = 0; t < threads; ++t) {
    std::string part = path + ".thread" + std::to_string(t);
    std::ifstream in(part);
    if (!in) continue;
    std::string line, head;
    int n = 0;
    while (std::getline(in, line)) {
      if (++n <= headerLines) {
        head += line + "\n";
        if (n == headerLines && header.empty()) header = head;
        continue;
      }
      rows.emplace_back(std::stol(line.substr(0, line.find(','))), line);
    }
    in.close();
    std::remove(part.c_str());
  }
  std::sort(rows.begin(), rows.end());
  std::ofstream out(path);
  out << header;
  for (const auto& r : rows) out << r.second << "\n";
}

}  // namespace g4sim

#endif
