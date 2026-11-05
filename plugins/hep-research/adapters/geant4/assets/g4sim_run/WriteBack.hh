// g4sim_run/WriteBack.hh: the volume-tree write-back of g4sim_run (g4sim plan, Section 8.1), beside the old probe's file: ProbeV2 on the
// master at the run start. Geant4 API only.
#ifndef G4SIM_RUN_WRITEBACK_HH
#define G4SIM_RUN_WRITEBACK_HH

#include <fstream>
#include <set>
#include <string>

#include "ProbeV2.hh"

namespace g4sim {

inline void WriteBack(const char* program, const std::string& probePath, const std::set<std::string>& declaredFields) {
  const std::string folder = probePath.substr(0, probePath.find_last_of('/') + 1);
  std::ofstream(folder + "probe-v2.json") << RunProbeV2(std::string(program) + ": g4sim_run write-back", declaredFields).json;
}

}  // namespace g4sim

#endif
