// g4sim_run/FastSim.hh: the fast-simulation hook (g4sim plan, Sections 6.2.9, 16, S8). Written from the Geant4 API (no example code copied
// or adapted); it follows the API's pattern as Geant4's Par01 and Par03 examples use it (a model on a region, created in ConstructSDandField;
// KillPrimaryTrack with ProposeTotalEnergyDeposited).
//
// A fast_sim_envelope requirement names envelope templates, each the only root of its own region (core/geometry/fast_sim.py). The run card's
// physics.fast_sim names one model of fast_sim_models.json and the particles whose process managers get G4FastSimulationManagerProcess:
// named particles only, because the process attached to all of them changes some histories even when no model triggers (GB19, addendum
// 11.1). A run with no fast_sim block attaches no process. Models are thread-local: AttachFastSimModels runs in ConstructSDandField on the
// master and on each worker, and the region's G4FastSimulationManager owns them.
//
// This plan delivers the hook and two test models only (S8 gate 3). `idle` never triggers and draws no random number. `absorb` triggers on
// every track entering the envelope, kills it, and books its kinetic energy as the deposit of that step, so the deposit inside the envelope
// closes against the energy that entered. A study's substitute model is added to MakeFastSimModel and to fast_sim_models.json, and is
// validated by the study under hep-ml's protocol, not by these gates.
#pragma once

#include <set>
#include <stdexcept>
#include <string>
#include <vector>

#include "G4FastSimulationHelper.hh"
#include "G4FastStep.hh"
#include "G4FastTrack.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"
#include "G4ProcessManager.hh"
#include "G4Region.hh"
#include "G4RegionStore.hh"
#include "G4Track.hh"
#include "G4VFastSimulationModel.hh"
#include "G4VPhysicsConstructor.hh"

namespace g4sim {

struct FastSimSetup {
  std::string model;
  std::vector<std::string> particles;
  std::vector<std::string> regions;  // the envelopes' own regions, from the IR
  bool Any() const { return !model.empty(); }
};

class IdleModel : public G4VFastSimulationModel {
 public:
  IdleModel(const G4String& name, G4Region* region) : G4VFastSimulationModel(name, region) {}
  G4bool IsApplicable(const G4ParticleDefinition&) override { return true; }
  G4bool ModelTrigger(const G4FastTrack&) override { return false; }
  void DoIt(const G4FastTrack&, G4FastStep&) override { throw std::logic_error("the idle fast-simulation model never triggers"); }
};

class AbsorbModel : public G4VFastSimulationModel {
 public:
  AbsorbModel(const G4String& name, G4Region* region) : G4VFastSimulationModel(name, region) {}
  G4bool IsApplicable(const G4ParticleDefinition&) override { return true; }
  G4bool ModelTrigger(const G4FastTrack&) override { return true; }
  void DoIt(const G4FastTrack& track, G4FastStep& step) override {
    step.KillPrimaryTrack();
    step.ProposeTotalEnergyDeposited(track.GetPrimaryTrack()->GetKineticEnergy());
  }
};

inline G4VFastSimulationModel* MakeFastSimModel(const std::string& model, G4Region* region) {
  const std::string name = "g4sim_fast_" + model + "_" + region->GetName();
  if (model == "idle") return new IdleModel(name, region);
  if (model == "absorb") return new AbsorbModel(name, region);
  throw std::runtime_error("fast-simulation model " + model + " is not built by g4sim_run");
}

// G4FastSimulationManagerProcess on the named particles only (GB19); a name the particle table does not know is an error, not a skip
class FastSimConstructor : public G4VPhysicsConstructor {
 public:
  explicit FastSimConstructor(std::vector<std::string> particles) : G4VPhysicsConstructor("g4sim_fast_sim"), fParticles(std::move(particles)) {}
  void ConstructParticle() override {}
  void ConstructProcess() override {
    for (const std::string& name : fParticles) {
      G4ParticleDefinition* particle = G4ParticleTable::GetParticleTable()->FindParticle(name);
      if (!particle || !particle->GetProcessManager()) throw std::runtime_error("fast simulation: unknown particle " + name);
      G4FastSimulationHelper::ActivateFastSimulation(particle->GetProcessManager());
    }
  }

 private:
  std::vector<std::string> fParticles;
};

// In ConstructSDandField: one model per envelope region, on this thread
inline void AttachFastSimModels(const FastSimSetup& setup) {
  const std::set<std::string> regions(setup.regions.begin(), setup.regions.end());  // one model per region, however many envelopes share it
  for (const std::string& name : regions) {
    G4Region* region = G4RegionStore::GetInstance()->GetRegion(name, false);
    if (!region) throw std::runtime_error("fast simulation: the envelope's region " + name + " was not built");
    MakeFastSimModel(setup.model, region);  // registers itself with the region's G4FastSimulationManager, which owns it
  }
}

}  // namespace g4sim
