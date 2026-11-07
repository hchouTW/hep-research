// g4sim/KillProcess.hh: the kill mechanism of `separated` mode (g4sim plan, Sections 6.4, 8.4). Written from the Geant4 API.
//
// A discrete process, so it defines its step and the continuous loss is booked before the kill (GB21). The energy it takes is booked through the
// accounting interface and never as a deposit, unlike G4UserSpecialCuts (GB7). A track that meets a limit is killed in a step of length 0.
#ifndef G4SIM_KILLPROCESS_HH
#define G4SIM_KILLPROCESS_HH

#include <cfloat>

#include "Accounting.hh"
#include "G4Step.hh"
#include "G4Track.hh"
#include "G4VDiscreteProcess.hh"

namespace g4sim {

struct KillLimits {
  double minKinetic = -1., timeCut = -1.;  // negative: not set
  bool Any() const { return minKinetic >= 0. || timeCut >= 0.; }
};

class KillProcess : public G4VDiscreteProcess {
 public:
  explicit KillProcess(const KillLimits& limits) : G4VDiscreteProcess("KillProcess", fUserDefined), fLimits(limits) {}
  G4bool IsApplicable(const G4ParticleDefinition&) override { return true; }
  G4double GetMeanFreePath(const G4Track&, G4double, G4ForceCondition*) override { return DBL_MAX; }
  G4double PostStepGetPhysicalInteractionLength(const G4Track& track, G4double, G4ForceCondition* condition) override {
    *condition = NotForced;
    const bool slow = fLimits.minKinetic >= 0. && track.GetKineticEnergy() < fLimits.minKinetic;
    const bool late = fLimits.timeCut >= 0. && track.GetGlobalTime() > fLimits.timeCut;
    return slow || late ? 0. : DBL_MAX;
  }
  G4VParticleChange* PostStepDoIt(const G4Track& track, const G4Step&) override {
    aParticleChange.Initialize(track);
    Accounting::Thread().BookKill(track.GetKineticEnergy(), track.GetDefinition());
    aParticleChange.ProposeEnergy(0.);
    aParticleChange.ProposeTrackStatus(fStopAndKill);
    return &aParticleChange;
  }

 private:
  KillLimits fLimits;
};

}  // namespace g4sim

#endif
