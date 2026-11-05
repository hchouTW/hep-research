// g4sim_run/WriteBack.hh: the volume-tree write-back of g4sim_run (g4sim plan, Section 8.1), beside the old probe's file: ProbeV2 on the
// master at the run start. Geant4 API only.
#ifndef G4SIM_RUN_WRITEBACK_HH
#define G4SIM_RUN_WRITEBACK_HH

#include <fstream>
#include <set>
#include <string>

#include "G4Threading.hh"
#include "ProbeV2.hh"

namespace g4sim {

// The conservation file sits beside the event file: one per thread in MT, merged by event after the run like the event file (Section 8.9).
inline std::string ConservationPath(const std::string& eventsPath) {
  return eventsPath.substr(0, eventsPath.find_last_of('/') + 1) + "conservation.csv";
}

inline std::string ThreadConservationPath(const std::string& eventsPath, bool multiThreaded) {
  return ConservationPath(eventsPath) + (multiThreaded ? ".thread" + std::to_string(G4Threading::G4GetThreadId()) : "");
}

inline void WriteBack(const char* program, const std::string& probePath, const std::set<std::string>& declaredFields) {
  const std::string folder = probePath.substr(0, probePath.find_last_of('/') + 1);
  std::ofstream(folder + "probe-v2.json") << RunProbeV2(std::string(program) + ": g4sim_run write-back", declaredFields).json;
}

}  // namespace g4sim

#endif
