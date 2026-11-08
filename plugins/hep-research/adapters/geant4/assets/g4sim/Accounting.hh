// g4sim/Accounting.hh: termination classes, the unreleased-energy table and the conservation columns of legacy mode (g4sim plan, Sections
// 8.4, 8.9). Geant4 API only; written from the Geant4 API (no example code copied or adapted).
//
// It only reads: no random number, no change to a track, and its columns go to a separate file, so the old columns cannot move (Section 8.9).
// Every ended track falls into exactly one class. A track is decided by what ended it, never by its status alone, which world escapes and
// physical ends share with kills (GB8). Class (d), G4UserSpecialCuts, books only the residual energy U: its kinetic energy is already in the
// deposit (GB7). Class (b) never reaches a step, so the stacking action reports it here. A neutron ended by the physics list's nKiller is a
// further killed class, which Section 8.4 does not list: its kinetic energy and U are booked (maintainer's decision, g4sim-approvals.md).
//
// S7: an optical photon is a class of its own (Section 8.4). Its tracks, however they end, and any deposit they leave go only to the
// optical-photon terms, never to the deposit, escape, killed or unreleased terms: producing them takes no energy from the parent (GB16).
// Those columns are written only when optical physics is on (SetOptical), so no other run's columns move.
//
// G4SIM_ACCOUNTING_CONTROL names one negative control of Section 15.1, for tests only: no_escape, no_killed_unbooked, stop_status_is_killed,
// class_d_kinetic, neutron_rest_energy, nuclei_unreleased, optical_as_killed (a photon KillProcess takes booked as killed kinetic energy).
#ifndef G4SIM_ACCOUNTING_HH
#define G4SIM_ACCOUNTING_HH

#include <cstdio>
#include <cstdlib>
#include <map>
#include <string>

#include "G4DecayTable.hh"
#include "G4OpBoundaryProcess.hh"
#include "G4OpticalPhoton.hh"
#include "G4Event.hh"
#include "G4ParticleDefinition.hh"
#include "G4PhysicalConstants.hh"
#include "G4PrimaryParticle.hh"
#include "G4PrimaryVertex.hh"
#include "G4ProcessManager.hh"
#include "G4ProcessVector.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4Threading.hh"
#include "G4Track.hh"
#include "G4VDecayChannel.hh"
#include "G4VProcess.hh"

namespace g4sim {

inline std::string AccountingControl() {
  const char* value = std::getenv("G4SIM_ACCOUNTING_CONTROL");
  return value ? value : "";
}

inline bool ExecutesDecay(const G4ParticleDefinition* particle) {
  G4ProcessManager* manager = particle->GetProcessManager();
  if (!manager || !particle->GetDecayTable()) return false;
  G4ProcessVector* processes = manager->GetProcessList();
  for (G4int i = 0; i < processes->size(); ++i)
    if ((*processes)[i]->GetProcessName() == "Decay") return true;
  return false;
}

// Expected Q of the whole decay chain to stable particles, branches weighted by branching ratio, plus 2 m_e c^2 for every e+ in the chain;
// 0 for a particle this run does not decay (Section 8.4, GB9). An e+ itself is not in this table: its 2 m_e c^2 is ResidualEnergy's.
class UnreleasedEnergy {
 public:
  double Of(const G4ParticleDefinition* particle) {
    auto found = fTable.find(particle);
    if (found != fTable.end()) return found->second;
    double value = Compute(particle);
    fTable[particle] = value;
    return value;
  }

 private:
  double Compute(const G4ParticleDefinition* particle) {
    const std::string control = AccountingControl();
    if (control == "neutron_rest_energy" && particle->GetPDGEncoding() == 2112) return particle->GetPDGMass();
    if (control == "nuclei_unreleased" && particle->GetParticleType() == "nucleus") return 1. * MeV;
    if (!ExecutesDecay(particle)) return 0.;
    const G4DecayTable* table = particle->GetDecayTable();
    double weighted = 0., total = 0.;
    for (G4int i = 0; i < const_cast<G4DecayTable*>(table)->entries(); ++i) {
      G4VDecayChannel* channel = const_cast<G4DecayTable*>(table)->GetDecayChannel(i);
      double branch = channel->GetBR(), released = particle->GetPDGMass();
      for (G4int d = 0; d < channel->GetNumberOfDaughters(); ++d) {
        G4ParticleDefinition* daughter = channel->GetDaughter(d);
        released += (daughter->GetPDGEncoding() == -11 ? 2 * CLHEP::electron_mass_c2 : Of(daughter)) - daughter->GetPDGMass();
      }
      weighted += branch * released;
      total += branch;
    }
    return total > 0 ? weighted / total : 0.;
  }
  std::map<const G4ParticleDefinition*, double> fTable;
};

struct ConservationRow {
  double incident = 0, deposit = 0, escapeGamma = 0, escapeElectron = 0, escapeNeutrino = 0, escapeOther = 0;
  double killedKineticStacking = 0, killedKineticLooper = 0, killedKineticSpecialCut = 0, killedKineticNeutron = 0, unreleased = 0, eplusResidual = 0;
  double killedKineticProcess = 0;  // class (a): `separated` mode only, and written only there, so legacy columns cannot move
  long tracksPhysical = 0, tracksEscaped = 0, tracksKilled = 0, accountingErrors = 0;
  // the optical-photon terms (S7): counts and energies by fate, and the deposit photons leave, outside every identity
  long opticalProduced = 0, opticalDetected = 0, opticalAbsorbed = 0, opticalWls = 0, opticalEscaped = 0, opticalKilledScope = 0, opticalBoundaryAbsorbed = 0, opticalOther = 0;
  double opticalEnergyProduced = 0, opticalEnergyDetected = 0, opticalEnergyAbsorbed = 0, opticalEnergyWls = 0, opticalEnergyEscaped = 0, opticalEnergyKilled = 0,
         opticalEnergyBoundaryAbsorbed = 0, opticalEnergyOther = 0, opticalDeposit = 0;
  double Residual() const {
    return incident - deposit - (escapeGamma + escapeElectron + escapeNeutrino + escapeOther) -
           (killedKineticStacking + killedKineticLooper + killedKineticSpecialCut + killedKineticNeutron + killedKineticProcess) - unreleased - eplusResidual;
  }
};

class Accounting {
 public:
  static Accounting& Thread() {
    static G4ThreadLocal Accounting* instance = nullptr;
    if (!instance) instance = new Accounting();
    return *instance;
  }

  void Open(const std::string& path) {
    if (fOut) return;
    fPath = path;
    fOut = std::fopen(path.c_str(), "w");
    if (fOut) std::fprintf(fOut, "# CONSERVATION\n%s%s%s\n", Header(), fSeparated ? ",killed_kinetic_process_MeV" : "", fOptical ? OpticalHeader() : "");
  }
  void SetSeparated() { fSeparated = true; }
  void SetOptical() { fOptical = true; }
  // An optical photon KillProcess took outside the scope or at the time cut: the optical terms only (the negative control books it as killed)
  void BookOpticalKill(double kinetic) {
    if (AccountingControl() == "optical_as_killed") fRow.killedKineticProcess += kinetic;
    else fPendingOpticalKill = kinetic;
  }
  // Class (a): KillProcess books the kinetic energy it took, which the post-step point no longer holds.
  void BookKill(double kinetic, const G4ParticleDefinition* particle) {
    if (AccountingControl() != "no_killed_process") fRow.killedKineticProcess += kinetic;
    BookResidual(particle);
  }
  void BeginEvent() {
    fRow = ConservationRow();
    fPendingOpticalKill = -1.;
    fEnded.clear();
  }

  // The e+ residual and the unreleased energy of a particle that will not end by itself.
  void BookResidual(const G4ParticleDefinition* particle) {
    if (particle->GetPDGEncoding() == -11) fRow.eplusResidual += 2 * CLHEP::electron_mass_c2;
    else fRow.unreleased += fUnreleased.Of(particle);
  }

  void Step(const G4Step* step) {
    const G4Track* track = step->GetTrack();
    if (track->GetDefinition() == G4OpticalPhoton::OpticalPhotonDefinition()) {
      OpticalStep(step);
      return;
    }
    fRow.deposit += step->GetTotalEnergyDeposit();
    if (track->GetTrackStatus() != fStopAndKill && track->GetTrackStatus() != fKillTrackAndSecondaries) return;
    if (++fEnded[track->GetTrackID()] > 1) ++fRow.accountingErrors;
    const G4StepPoint* post = step->GetPostStepPoint();
    const G4VProcess* process = post->GetProcessDefinedStep();
    const std::string name = process ? process->GetProcessName() : "";
    const G4ParticleDefinition* particle = track->GetDefinition();
    const double kinetic = post->GetKineticEnergy();
    const std::string control = AccountingControl();
    if (post->GetStepStatus() == fWorldBoundary) {
      ++fRow.tracksEscaped;
      if (control == "stop_status_is_killed") {
        fRow.killedKineticLooper += kinetic;
        ++fRow.accountingErrors;
      }
      if (control != "no_escape") BookEscape(particle, kinetic);
    } else if (name == "KillProcess") {
      ++fRow.tracksKilled;  // already booked by BookKill
    } else if (name == "UserSpecialCut") {
      ++fRow.tracksKilled;
      if (control == "class_d_kinetic") fRow.killedKineticSpecialCut += step->GetPreStepPoint()->GetKineticEnergy();  // the post-step value is already 0
      BookResidual(particle);
    } else if (name == "nKiller") {
      ++fRow.tracksKilled;
      fRow.killedKineticNeutron += step->GetPreStepPoint()->GetKineticEnergy();  // the post-step value is already 0
      BookResidual(particle);
    } else if (name == "Transportation" || name == "CoupledTransportation") {
      ++fRow.tracksKilled;  // a looper: transportation ended it inside the world
      fRow.killedKineticLooper += kinetic;
      BookResidual(particle);
    } else {
      ++fRow.tracksPhysical;
      if (control == "stop_status_is_killed") {
        fRow.killedKineticLooper += kinetic;
        ++fRow.accountingErrors;
      }
    }
  }

  // Class (b): a secondary the stacking action kills is never tracked.
  void StackingKill(const G4Track* track) {
    ++fRow.tracksKilled;
    if (AccountingControl() == "no_killed_unbooked") return;
    fRow.killedKineticStacking += track->GetKineticEnergy();
    BookResidual(track->GetDefinition());
  }

  void EndEvent(const G4Event* event, long firstEvent) {
    for (G4int v = 0; v < event->GetNumberOfPrimaryVertex(); ++v) {
      const G4PrimaryVertex* vertex = event->GetPrimaryVertex(v);
      for (G4int i = 0; i < vertex->GetNumberOfParticle(); ++i) {
        const G4PrimaryParticle* primary = vertex->GetPrimary(i);
        const G4ParticleDefinition* particle = primary->GetParticleDefinition();
        if (particle == G4OpticalPhoton::OpticalPhotonDefinition()) continue;  // a primary photon (a mapping run) is in the optical terms only
        fRow.incident += primary->GetKineticEnergy() + (particle->GetPDGEncoding() == -11 ? 2 * CLHEP::electron_mass_c2 : fUnreleased.Of(particle));
      }
    }
    if (!fOut) return;
    const ConservationRow& r = fRow;
    std::fprintf(fOut, "%ld,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%ld,%ld,%ld,%ld", firstEvent + event->GetEventID(),
                 r.incident / MeV, r.deposit / MeV, r.escapeGamma / MeV, r.escapeElectron / MeV, r.escapeNeutrino / MeV, r.escapeOther / MeV,
                 r.killedKineticStacking / MeV, r.killedKineticLooper / MeV, r.killedKineticSpecialCut / MeV, r.killedKineticNeutron / MeV, r.unreleased / MeV,
                 r.eplusResidual / MeV, r.Residual() / MeV, r.tracksPhysical, r.tracksEscaped, r.tracksKilled, r.accountingErrors);
    if (fSeparated) std::fprintf(fOut, ",%.17g", r.killedKineticProcess / MeV);
    if (fOptical)
      std::fprintf(fOut, ",%ld,%ld,%ld,%ld,%ld,%ld,%ld,%ld,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g", r.opticalProduced, r.opticalDetected, r.opticalAbsorbed,
                   r.opticalWls, r.opticalEscaped, r.opticalKilledScope, r.opticalBoundaryAbsorbed, r.opticalOther, r.opticalEnergyProduced / MeV,
                   r.opticalEnergyDetected / MeV, r.opticalEnergyAbsorbed / MeV, r.opticalEnergyWls / MeV, r.opticalEnergyEscaped / MeV, r.opticalEnergyKilled / MeV,
                   r.opticalEnergyBoundaryAbsorbed / MeV, r.opticalEnergyOther / MeV, r.opticalDeposit / MeV);
    std::fputc('\n', fOut);
  }
  void Close() {
    if (fOut) std::fclose(fOut);
    fOut = nullptr;
  }
  UnreleasedEnergy& Table() { return fUnreleased; }
  const ConservationRow& Row() const { return fRow; }

  static const char* Header() {
    return "event,incident_MeV,deposit_MeV,escape_gamma_MeV,escape_electron_MeV,escape_neutrino_MeV,escape_other_MeV,killed_kinetic_stacking_MeV,"
           "killed_kinetic_looper_MeV,killed_kinetic_special_cut_MeV,killed_kinetic_neutron_MeV,unreleased_MeV,eplus_residual_MeV,residual_MeV,tracks_physical,tracks_escaped,"
           "tracks_killed,accounting_errors";
  }

  static const char* OpticalHeader() {
    return ",optical_produced,optical_detected,optical_absorbed,optical_wls,optical_escaped,optical_killed_scope,optical_boundary_absorbed,optical_other,"
           "optical_energy_produced_MeV,optical_energy_detected_MeV,optical_energy_absorbed_MeV,optical_energy_wls_MeV,optical_energy_escaped_MeV,"
           "optical_energy_killed_MeV,optical_energy_boundary_absorbed_MeV,optical_energy_other_MeV,optical_deposit_MeV";
  }

 private:
  // An optical photon's step: produced on its first step, ended exactly once, by fate (S7). Detection is the boundary process's status.
  void OpticalStep(const G4Step* step) {
    const G4Track* track = step->GetTrack();
    ConservationRow& r = fRow;
    r.opticalDeposit += step->GetTotalEnergyDeposit();
    if (track->GetCurrentStepNumber() == 1) {
      ++r.opticalProduced;
      r.opticalEnergyProduced += step->GetPreStepPoint()->GetKineticEnergy();
    }
    if (track->GetTrackStatus() != fStopAndKill && track->GetTrackStatus() != fKillTrackAndSecondaries) return;
    if (++fEnded[track->GetTrackID()] > 1) ++r.accountingErrors;
    const double energy = step->GetPreStepPoint()->GetKineticEnergy();  // the post-step value of an absorbed photon is already 0
    const G4VProcess* process = step->GetPostStepPoint()->GetProcessDefinedStep();
    const std::string name = process ? process->GetProcessName() : "";
    if (fPendingOpticalKill >= 0.) {
      ++r.opticalKilledScope;
      r.opticalEnergyKilled += fPendingOpticalKill;
      fPendingOpticalKill = -1.;
    } else if (name == "KillProcess") {  // the negative control: already booked as killed kinetic energy
      ++r.tracksKilled;
    } else if (step->GetPostStepPoint()->GetStepStatus() == fWorldBoundary) {
      ++r.opticalEscaped;
      r.opticalEnergyEscaped += energy;
    } else if (name == "OpAbsorption") {
      ++r.opticalAbsorbed;
      r.opticalEnergyAbsorbed += energy;
    } else if (name == "OpWLS" || name == "OpWLS2") {
      ++r.opticalWls;
      r.opticalEnergyWls += energy;
    } else if (step->GetPostStepPoint()->GetStepStatus() == fGeomBoundary) {
      // Transportation defines a boundary step; OpBoundary, a forced process, ends the photon there, and its status says how
      const auto* boundary = Boundary(track->GetDefinition());
      if (boundary && boundary->GetStatus() == Detection) {
        ++r.opticalDetected;
        r.opticalEnergyDetected += energy;
      } else {
        ++r.opticalBoundaryAbsorbed;  // absorbed by the surface, or a next volume with no refractive index (NoRINDEX)
        r.opticalEnergyBoundaryAbsorbed += energy;
      }
    } else {
      ++r.opticalOther;
      r.opticalEnergyOther += energy;
    }
  }
 public:
  // The thread's OpBoundary process, whose status says what happened to a photon at a boundary step (S7).
  static const G4OpBoundaryProcess* Boundary(const G4ParticleDefinition* photon) {
    static G4ThreadLocal const G4OpBoundaryProcess* boundary = nullptr;
    if (!boundary && photon->GetProcessManager()) boundary = dynamic_cast<const G4OpBoundaryProcess*>(photon->GetProcessManager()->GetProcess("OpBoundary"));
    return boundary;
  }

 private:
  void BookEscape(const G4ParticleDefinition* particle, double kinetic) {
    const int pdg = particle->GetPDGEncoding();
    const double equivalent = kinetic + (pdg == -11 ? 2 * CLHEP::electron_mass_c2 : fUnreleased.Of(particle));
    if (pdg == 22) fRow.escapeGamma += equivalent;
    else if (std::abs(pdg) == 11) fRow.escapeElectron += equivalent;
    else if (std::abs(pdg) == 12 || std::abs(pdg) == 14 || std::abs(pdg) == 16) fRow.escapeNeutrino += equivalent;
    else fRow.escapeOther += equivalent;
  }
  UnreleasedEnergy fUnreleased;
  ConservationRow fRow;
  std::map<int, int> fEnded;
  std::FILE* fOut = nullptr;
  bool fSeparated = false;
  bool fOptical = false;
  double fPendingOpticalKill = -1.;  // set by KillProcess in PostStepDoIt, taken by the stepping action of the same step
  std::string fPath;
};

}  // namespace g4sim

#endif
