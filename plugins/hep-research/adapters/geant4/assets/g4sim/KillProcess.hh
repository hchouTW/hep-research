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
#include <cstdlib>
#include <set>
#include <string>

#include "Accounting.hh"
#include "G4OpBoundaryProcess.hh"
#include "G4OpticalPhoton.hh"
#include "G4GeometryTolerance.hh"
#include "G4Navigator.hh"
#include "G4TransportationManager.hh"
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
    // a photon born in a volume outside the scope (a primary, or one made where an out-of-scope material has optical tables) takes no step there
    if (photon && BornOutside(track, track.GetTouchable()->GetVolume())) return 0.;
    return Limited(track) ? 0. : DBL_MAX;
  }
  G4VParticleChange* PostStepDoIt(const G4Track& track, const G4Step& step) override {
    aParticleChange.Initialize(track);
    if (fLimits.scoped && track.GetDefinition() == G4OpticalPhoton::OpticalPhotonDefinition()) {
      // Killed only on entering a volume outside the scope (Section 6.2.9): at a boundary step the post-step point lies in the next volume
      // even when OpBoundary, which acts first, reflected the photon back. The entry is judged by direction, whatever OpBoundary's status
      // (refraction, transmission, SameMaterial, a coated or dichroic passage): the photon goes on into the next volume when its direction
      // after OpBoundary lies on the same side of the boundary's normal as its direction before. Or the photon was already in such a volume.
      const G4VPhysicalVolume* here = step.GetPreStepPoint()->GetPhysicalVolume();
      const G4VPhysicalVolume* next = step.GetPostStepPoint()->GetPhysicalVolume();
      const auto outsideScope = [this](const G4VPhysicalVolume* volume) { return volume && !fLimits.opticalScope.count(volume->GetLogicalVolume()->GetName()); };
      // G4SIM_KILL_CONTROL=entry_by_status, the negative test of Section 15.1 for tests only: the entry judged by OpBoundary's refraction and
      // transmission statuses alone, which lets a photon through on SameMaterial (the leak_scope control's world)
      const char* control = std::getenv("G4SIM_KILL_CONTROL");
      const G4OpBoundaryProcess* boundary = Accounting::Boundary(track.GetDefinition());
      const bool byStatus = control && std::string(control) == "entry_by_status";
      const bool passes = byStatus ? boundary && (boundary->GetStatus() == FresnelRefraction || boundary->GetStatus() == Transmission) : Passes(step);
      const bool entering = step.GetPostStepPoint()->GetStepStatus() == fGeomBoundary && passes;
      // a reflected photon's next step starts on the boundary in the next volume and returns with zero length: not an entry either
      const bool inside_outside = outsideScope(here) && step.GetStepLength() > G4GeometryTolerance::GetInstance()->GetSurfaceTolerance();
      const bool outside = BornOutside(track, here) || inside_outside || (entering && outsideScope(next));
      if (!outside && !Limited(track)) return &aParticleChange;  // forced, and nothing to do
      Accounting::Thread().BookOpticalKill(track.GetKineticEnergy(), !outside);
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
  // The first step of a photon whose birth volume lies outside the scope (the step number is 1 from the first step's length on). The volume
  // is the track's before the step (in the step length) and the pre-step point's after it: by PostStepDoIt the track holds the next volume.
  bool BornOutside(const G4Track& track, const G4VPhysicalVolume* volume) const {
    return track.GetCurrentStepNumber() == 1 && volume && !fLimits.opticalScope.count(volume->GetLogicalVolume()->GetName());
  }
  // Whether the photon crossed the boundary of this step rather than turning back: the normal is the navigator's, as OpBoundary reads it.
  static bool Passes(const G4Step& step) {
    G4bool valid = false;
    G4Navigator* navigator = G4TransportationManager::GetTransportationManager()->GetNavigatorForTracking();
    const G4ThreeVector normal = navigator->GetGlobalExitNormal(step.GetPostStepPoint()->GetPosition(), &valid);
    if (!valid) return true;  // no normal to judge by: treated as an entry, so a photon is never let through unseen
    const double before = step.GetPreStepPoint()->GetMomentumDirection().dot(normal), after = step.GetPostStepPoint()->GetMomentumDirection().dot(normal);
    return (before > 0.) == (after > 0.);
  }
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
