// g4sim/SimSeed.hh: per-event seeding of Geant4 runs (adapters/geant4, Geant4 program A2.2).
//
// Event i (the global event number) of logical run S starts from the two seeds (H(S, i, 0), H(S, i, 1)) of
// SimHash.hh, passed to G4Random::setTheSeeds as the zero-terminated array {s0, s1, 0} (as layered_sim.cc seeds a
// whole run). Called at the start of GeneratePrimaries, before any random draw: Geant4 calls GeneratePrimaries before
// BeginOfEventAction, and in MT the worker reseeds the engine from the master's seed queue just before it, so this
// reseed replaces the stream seed and the event depends only on (S, i), whatever the split into jobs and threads.
// The random status Geant4 stores before GeneratePrimaries (/random/setSavingFlag, StoreRandomNumberStatusToG4Event)
// is the status before this reseed: a per-event event is reproduced from (S, i), never from that stored status.
#ifndef G4SIM_SIMSEED_HH
#define G4SIM_SIMSEED_HH

#include "Randomize.hh"
#include "SimHash.hh"

namespace g4sim {

inline void ReseedEvent(long long logicalRunSeed, long long globalEvent) {
  auto s = EventSeeds(logicalRunSeed, globalEvent);
  long seeds[3] = {s[0], s[1], 0};
  G4Random::setTheSeeds(seeds);
}

}  // namespace g4sim

#endif
