// g4sim/KillProcess.hh: the kill mechanism of `separated` mode (g4sim plan, Sections 6.4, 8.4). Written from the Geant4 API.
//
// A discrete process, so it defines its step and the continuous loss is booked before the kill (GB21). The energy it takes is booked through the
// accounting interface and never as a deposit, unlike G4UserSpecialCuts (GB7). A track that meets a limit is killed in a step of length 0.
//
// S7, optical_scope (GB16): G4OpticalPhysics is global and SetActiveVolume cannot restrict production by volume, so an optical photon is
// forced through this process on every step and killed where its post-step point lies in a volume outside the scope, before it takes a step
// there (the S3 prototype's "boundary" mode: 0 steps outside the scope). An optical photon is booked only in the optical-photon terms.
#ifndef G4SIM_KILLPROCESS_HH
#define G4SIM_KILLPROCESS_HH

#include <cfloat>
#include <set>
#include <string>

#include "Accounting.hh"
#include "G4OpticalPhoton.hh"
#include "G4Step.hh"
#include "G4VPhysicalVolume.hh"
#include "G4Track.hh"
#include "G4VDiscreteProcess.hh"

namespace g4sim {

struct KillLimits {
  double minKinetic = -1., timeCut = -1.;  // negative: not set
  bool scoped = false;                       // S7: optical physics is on, and opticalScope holds the logical names inside optical_scope
  std::set<std::string> opticalScope;
  bool Any() const { return minKinetic >= 0. || timeCut >= 0. || scoped; }
};

class KillProcess : public G4VDiscreteProcess {
 public:
  explicit KillProcess(const KillLimits& limits) : G4VDiscreteProcess("KillProcess", fUserDefined), fLimits(limits) {}
  G4bool IsApplicable(const G4ParticleDefinition&) override { return true; }
  G4double GetMeanFreePath(const G4Track&, G4double, G4ForceCondition*) override { return DBL_MAX; }
  G4double PostStepGetPhysicalInteractionLength(const G4Track& track, G4double, G4ForceCondition* condition) override {
    const bool photon = fLimits.scoped && track.GetDefinition() == G4OpticalPhoton::OpticalPhotonDefinition();
    *condition = photon ? Forced : NotForced;  // a photon is looked at after every step, wherever the step ends
    return Limited(track) ? 0. : DBL_MAX;
  }
  G4VParticleChange* PostStepDoIt(const G4Track& track, const G4Step& step) override {
    aParticleChange.Initialize(track);
    if (fLimits.scoped && track.GetDefinition() == G4OpticalPhoton::OpticalPhotonDefinition()) {
      const G4VPhysicalVolume* next = step.GetPostStepPoint()->GetPhysicalVolume();
      const bool outside = next && !fLimits.opticalScope.count(next->GetLogicalVolume()->GetName());
      if (!outside && !Limited(track)) return &aParticleChange;  // forced, and nothing to do
      Accounting::Thread().BookOpticalKill(track.GetKineticEnergy());
      aParticleChange.ProposeEnergy(0.);
      aParticleChange.ProposeTrackStatus(fStopAndKill);
      return &aParticleChange;
    }
    Accounting::Thread().BookKill(track.GetKineticEnergy(), track.GetDefinition());
    aParticleChange.ProposeEnergy(0.);
    aParticleChange.ProposeTrackStatus(fStopAndKill);
    return &aParticleChange;
  }

 private:
  // The kinetic-energy limit never applies to an optical photon, whose energy of a few eV lies below any such limit; the time cut does.
  bool Limited(const G4Track& track) const {
    const bool photon = track.GetDefinition() == G4OpticalPhoton::OpticalPhotonDefinition();
    const bool slow = !photon && fLimits.minKinetic >= 0. && track.GetKineticEnergy() < fLimits.minKinetic;
    const bool late = fLimits.timeCut >= 0. && track.GetGlobalTime() > fLimits.timeCut;
    return slow || late;
  }
  KillLimits fLimits;
};

}  // namespace g4sim

#endif
