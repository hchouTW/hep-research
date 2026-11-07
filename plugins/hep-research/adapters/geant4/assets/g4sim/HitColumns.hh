// g4sim/HitColumns.hh: the ntuples of a hit file (g4sim plan, Section 9.2), shared by the writer in g4sim_run and the reader in simroot. No Geant4 here.
#ifndef G4SIM_HITCOLUMNS_HH
#define G4SIM_HITCOLUMNS_HH

#include <cstdint>
#include <vector>

namespace g4sim {

// A cell is a 64-bit volume ID plus a segmentation bin; a scorer with a named readout also writes its encoded cellID, the same two halves (Section 6.2.6), and 0 otherwise. g4tools' integers have 32 bits and a double holds 53, so the ID is kept exactly as two 32-bit columns, which simroot joins.
inline int CellHigh(std::uint64_t cell) { return static_cast<int>(static_cast<std::uint32_t>(cell >> 32)); }
inline int CellLow(std::uint64_t cell) { return static_cast<int>(static_cast<std::uint32_t>(cell)); }
inline std::uint64_t CellOf(long long high, long long low) { return (static_cast<std::uint64_t>(static_cast<std::uint32_t>(high)) << 32) | static_cast<std::uint32_t>(low); }

struct HitColumn {
  const char* name;
  char type;
};

struct HitNtuple {
  const char* name;
  std::vector<HitColumn> columns;
};

inline const std::vector<HitNtuple>& HitNtuples() {
  // Event numbers reach 2^32 and time bins are unbounded, so both are doubles, exact to 2^53.
  static const std::vector<HitNtuple> ntuples = {
      {"mc_particles", {{"event_id", 'D'}, {"track_id", 'I'}, {"parent_id", 'I'}, {"pdg", 'I'}, {"ancestor_pruned", 'I'}, {"simulation_status", 'I'}, {"born_of_decay", 'I'}, {"x_mm", 'D'}, {"y_mm", 'D'}, {"z_mm", 'D'}, {"px_MeV", 'D'}, {"py_MeV", 'D'}, {"pz_MeV", 'D'}, {"ekin_MeV", 'D'},
                        {"end_x_mm", 'D'}, {"end_y_mm", 'D'}, {"end_z_mm", 'D'}}},
      {"tracker_hits", {{"event_id", 'D'}, {"step_index", 'I'}, {"track_id", 'I'}, {"step_track_id", 'I'}, {"step_number", 'I'}, {"cell_high", 'I'}, {"cell_low", 'I'}, {"segment", 'I'}, {"cell_id_high", 'I'}, {"cell_id_low", 'I'}, {"x_mm", 'D'}, {"y_mm", 'D'}, {"z_mm", 'D'}, {"px_MeV", 'D'}, {"py_MeV", 'D'}, {"pz_MeV", 'D'},
                        {"ekin_MeV", 'D'}, {"edep_MeV", 'D'}, {"time_ns", 'D'}, {"path_mm", 'D'}}},
      {"calorimeter_hits", {{"event_id", 'D'}, {"cell_high", 'I'}, {"cell_low", 'I'}, {"segment", 'I'}, {"cell_id_high", 'I'}, {"cell_id_low", 'I'}, {"edep_MeV", 'D'}, {"x_mm", 'D'}, {"y_mm", 'D'}, {"z_mm", 'D'}}},
      {"contributions", {{"event_id", 'D'}, {"cell_high", 'I'}, {"cell_low", 'I'}, {"segment", 'I'}, {"track_id", 'I'}, {"time_bin", 'D'}, {"edep_MeV", 'D'}, {"time_ns", 'D'}, {"x_mm", 'D'}, {"y_mm", 'D'}, {"z_mm", 'D'}}},
      {"plane_crossings", {{"event_id", 'D'}, {"plane", 'I'}, {"track_id", 'I'}, {"x_mm", 'D'}, {"y_mm", 'D'}, {"z_mm", 'D'}, {"dx", 'D'}, {"dy", 'D'}, {"dz", 'D'}, {"energy_MeV", 'D'}, {"time_ns", 'D'}}}};
  return ntuples;
}

}  // namespace g4sim

#endif
