// g4sim/ExternalEvents.hh: a text event file, `g4sim-events/1` (g4sim plan, Section 6.3). No Geant4 here, so it can be tested alone.
//
// A line `event ID COUNT`, then COUNT lines `PDG X_MM Y_MM Z_MM PX_MEV PY_MEV PZ_MEV`. A line starting with # is a comment. Anything else is refused, because a line
// read across a line break would shift fields without a word: each line has exactly its fields, an event appears once, and a file that ends inside an event is refused.
#ifndef G4SIM_EXTERNALEVENTS_HH
#define G4SIM_EXTERNALEVENTS_HH

#include <array>
#include <fstream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace g4sim {

struct ExternalParticle {
  int pdg = 0;
  std::array<double, 3> position{}, momentum{};
};

inline std::map<long long, std::vector<ExternalParticle>> ParseExternalEvents(std::istream& in, const std::string& name) {
  std::map<long long, std::vector<ExternalParticle>> events;
  std::string line, extra, word;
  long long number = 0, current = -1, left = 0;
  const auto refuse = [&](const std::string& what) { throw std::runtime_error(name + ": line " + std::to_string(number) + ": " + what); };
  while (std::getline(in, line)) {
    ++number;
    std::istringstream fields(line);
    if (!(fields >> word) || word[0] == '#') continue;
    if (left > 0) {
      ExternalParticle row;
      std::istringstream particle(line);
      if (!(particle >> row.pdg >> row.position[0] >> row.position[1] >> row.position[2] >> row.momentum[0] >> row.momentum[1] >> row.momentum[2]) || (particle >> extra)) refuse("expected PDG X Y Z PX PY PZ");
      events[current].push_back(row);
      --left;
      continue;
    }
    if (word != "event" || !(fields >> current >> left) || (fields >> extra)) refuse("expected `event ID COUNT`");
    if (current < 0 || left < 0) refuse("an event number and a count are not negative");
    if (!events.emplace(current, std::vector<ExternalParticle>{}).second) refuse("event " + std::to_string(current) + " appears twice");
  }
  if (left > 0) refuse("the file ends inside event " + std::to_string(current));
  return events;
}

inline std::map<long long, std::vector<ExternalParticle>> ReadExternalEvents(const std::string& path) {
  std::ifstream in(path);
  if (!in) throw std::runtime_error("cannot read " + path);
  return ParseExternalEvents(in, path);
}

}  // namespace g4sim

#endif
