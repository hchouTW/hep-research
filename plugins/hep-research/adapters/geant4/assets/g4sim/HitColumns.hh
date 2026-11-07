// g4sim/HitColumns.hh: the ntuples of a hit file (g4sim plan, Section 9.2), shared by the writer in g4sim_run and the reader in simroot. No Geant4 here.
#ifndef G4SIM_HITCOLUMNS_HH
#define G4SIM_HITCOLUMNS_HH

#include <vector>

namespace g4sim {

constexpr const char* kHitsVersion = "g4sim.hits/1";

struct HitColumn {
  const char* name;
  char type;
};

struct HitNtuple {
  const char* name;
  std::vector<HitColumn> columns;
};

inline const std::vector<HitNtuple>& HitNtuples() {
  static const std::vector<HitNtuple> ntuples = {
      {"mc_particles", {{"event_id", 'I'}, {"track_id", 'I'}, {"parent_id", 'I'}, {"pdg", 'I'}, {"ancestor_pruned", 'I'}, {"x_mm", 'D'}, {"y_mm", 'D'}, {"z_mm", 'D'}, {"px_MeV", 'D'}, {"py_MeV", 'D'}, {"pz_MeV", 'D'},
                        {"end_x_mm", 'D'}, {"end_y_mm", 'D'}, {"end_z_mm", 'D'}}},
      {"tracker_hits", {{"event_id", 'I'}, {"step_index", 'I'}, {"track_id", 'I'}, {"cell", 'D'}, {"x_mm", 'D'}, {"y_mm", 'D'}, {"z_mm", 'D'}, {"px_MeV", 'D'}, {"py_MeV", 'D'}, {"pz_MeV", 'D'}, {"ekin_MeV", 'D'}, {"edep_MeV", 'D'}, {"time_ns", 'D'}, {"path_mm", 'D'}}},
      {"calorimeter_hits", {{"event_id", 'I'}, {"cell", 'D'}, {"edep_MeV", 'D'}, {"x_mm", 'D'}, {"y_mm", 'D'}, {"z_mm", 'D'}}},
      {"contributions", {{"event_id", 'I'}, {"cell", 'D'}, {"track_id", 'I'}, {"time_bin", 'I'}, {"edep_MeV", 'D'}, {"time_ns", 'D'}, {"x_mm", 'D'}, {"y_mm", 'D'}, {"z_mm", 'D'}}},
      {"plane_crossings", {{"event_id", 'I'}, {"plane", 'I'}, {"x_mm", 'D'}, {"y_mm", 'D'}, {"z_mm", 'D'}, {"dx", 'D'}, {"dy", 'D'}, {"dz", 'D'}, {"energy_MeV", 'D'}, {"time_ns", 'D'}}}};
  return ntuples;
}

}  // namespace g4sim

#endif
