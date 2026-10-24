// The per-event ROOT file of element_sim (element_sim.events/1, Geant4 program B1.4), written through
// G4AnalysisManager with the g4tools ROOT writer bundled with Geant4 (ROOT itself is not needed). One file per job; in
// MT the master merges the workers' ntuples into it (SetNtupleMerging). Flat ntuples, scalar columns only (I, D, S);
// every row has a key and readers sort by it (row order after the merge is not fixed).
//
// G-B1a (2026-10-24, Geant4 11.4.3): G4RootAnalysisReader reads MT-merged, compressed files, including string
// columns; the MT master cannot fill a merged ntuple (Geant4 warns "Ntuple 0 does not exist"), so the run and
// processes rows are filled by worker 0 (the only thread in serial mode). Every thread books the same ntuples in
// the same order.
#ifndef ELEMENT_SIM_EVENTFILE_HH
#define ELEMENT_SIM_EVENTFILE_HH

#include <string>
#include <utility>
#include <vector>

#include "Spec.hh"

constexpr const char* kEventFileVersion = "element_sim.events/1";

// Column of an ntuple: name and type ('I', 'D' or 'S').
struct NtupleColumn {
  std::string name;
  char type;
};

struct NtupleDef {
  std::string name;
  std::vector<NtupleColumn> columns;
};

// The ntuples the spec's event level writes, in booking order (run, processes, events, deposits, then crossings and
// hits from their levels); the events ntuple's columns depend on the elements.
std::vector<NtupleDef> EventFileNtuples(const Spec& spec);
// "name:T,name:T,..." of one ntuple (the run row stores one per ntuple, so simroot binds columns without guessing)
std::string ColumnList(const NtupleDef& def);

// Booking (every thread, same order) and access by ntuple name.
class EventFile {
 public:
  explicit EventFile(const Spec& spec);
  void Book();
  void Open();
  void Close();
  bool Enabled() const { return fEnabled; }
  int Id(const std::string& ntuple) const;  // -1 if the level does not write it
  const std::vector<NtupleDef>& Ntuples() const { return fDefs; }

 private:
  const Spec& fSpec;
  bool fEnabled;
  std::vector<NtupleDef> fDefs;
  std::vector<int> fIds;
};

#endif
