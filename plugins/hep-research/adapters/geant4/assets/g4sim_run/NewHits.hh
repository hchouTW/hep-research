// NewHits.hh: the hit file of a new specification (g4sim plan, Sections 9.2, 9.3). Flat ntuples written by g4tools; simroot's `hits` mode reads them. Written from the Geant4 11.4 API.
//
// Truth keeping: the primary, decay products, particles above a threshold, and particles crossing a reference plane are kept. Deposits of a track that is not kept go to its nearest kept
// ancestor, and a kept particle whose parent was dropped points there with ancestor_pruned set. Keeping is decided per track as it ends, and resolved at the end of the event.
// Cell numbers are doubles: g4tools' integers have 32 bits, and a volume ID is exact in a double up to 2^53, its limit (Section 7.1).
#ifndef G4SIM_NEWHITS_HH
#define G4SIM_NEWHITS_HH

#include <cmath>
#include <map>
#include <set>
#include <string>
#include <tuple>
#include <vector>

#include "G4AnalysisManager.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4Track.hh"
#include "G4VProcess.hh"
#include "HitColumns.hh"
#include "MiniJson.hh"

namespace g4sim {

struct TruthRules {
  bool primary = true, decayProducts = false;
  double energyThreshold = -1.;  // MeV; negative: not used
  double timeBinNs = 1.;
};

struct ReferencePlane {
  double z = 0.;
};

class HitRecorder {
 public:
  static HitRecorder& Thread() {
    static G4ThreadLocal HitRecorder* instance = nullptr;
    if (!instance) instance = new HitRecorder();
    return *instance;
  }

  void Configure(const TruthRules& rules, const std::vector<ReferencePlane>& planes) {
    fRules = rules;
    fPlanes = planes;
  }

  static void Book() {
    auto* manager = G4AnalysisManager::Instance();
    manager->SetDefaultFileType("root");
    manager->SetNtupleMerging(true);
    manager->SetVerboseLevel(0);
    for (const HitNtuple& ntuple : HitNtuples()) {
      const int id = manager->CreateNtuple(ntuple.name, ntuple.name);
      for (const HitColumn& column : ntuple.columns) {
        if (column.type == 'I') manager->CreateNtupleIColumn(id, column.name);
        else manager->CreateNtupleDColumn(id, column.name);
      }
      manager->FinishNtuple(id);
    }
  }

  void BeginEvent(long long event) {
    fEvent = static_cast<int>(event);
    fTracks.clear();
    fTracker.clear();
    fCalorimeter.clear();
    fContributions.clear();
    fCrossed.clear();
    fCrossings.clear();
    fStep = 0;
  }

  void BeginTrack(const G4Track* track) {
    TrackRow& row = fTracks[track->GetTrackID()];
    row.parent = track->GetParentID();
    row.pdg = track->GetDefinition()->GetPDGEncoding();
    row.vertex = track->GetVertexPosition();
    row.momentum = track->GetMomentum();
    const G4VProcess* creator = track->GetCreatorProcess();
    const bool decay = creator && creator->GetProcessType() == fDecay;
    const double kinetic = track->GetKineticEnergy() / MeV;
    row.kept = (track->GetParentID() == 0 && fRules.primary) || (decay && fRules.decayProducts) || (fRules.energyThreshold >= 0. && kinetic > fRules.energyThreshold);
  }

  void EndTrack(const G4Track* track) { fTracks[track->GetTrackID()].end = track->GetPosition(); }

  void Step(const G4Step* step) {
    const G4Track* track = step->GetTrack();
    if (track->GetParentID() != 0) return;
    const G4StepPoint* pre = step->GetPreStepPoint();
    const G4StepPoint* post = step->GetPostStepPoint();
    for (std::size_t i = 0; i < fPlanes.size(); ++i) {
      const double z = fPlanes[i].z * mm;
      if (fCrossed.count(i) || (pre->GetPosition().z() - z) * (post->GetPosition().z() - z) > 0.) continue;
      fCrossed.insert(i);
      const double span = post->GetPosition().z() - pre->GetPosition().z();
      const double t = span != 0. ? (z - pre->GetPosition().z()) / span : 0.;
      const G4ThreeVector point = pre->GetPosition() + t * (post->GetPosition() - pre->GetPosition());
      const G4ThreeVector direction = pre->GetMomentumDirection();
      fCrossings.push_back({static_cast<int>(i), point, direction, pre->GetKineticEnergy() + t * (post->GetKineticEnergy() - pre->GetKineticEnergy()), pre->GetGlobalTime() + t * (post->GetGlobalTime() - pre->GetGlobalTime())});
      fTracks[track->GetTrackID()].kept = true;
    }
  }

  void Tracker(const G4Step* step, double cell) {
    const G4StepPoint* pre = step->GetPreStepPoint();
    fTracker.push_back({fStep++, step->GetTrack()->GetTrackID(), cell, pre->GetPosition(), pre->GetMomentum(), pre->GetKineticEnergy(), step->GetTotalEnergyDeposit(), pre->GetGlobalTime(), step->GetStepLength()});
  }

  void Calorimeter(const G4Step* step, double cell) {
    const G4StepPoint* pre = step->GetPreStepPoint();
    const double deposit = step->GetTotalEnergyDeposit();
    CaloRow& row = fCalorimeter[cell];
    if (row.edep == 0.) row.position = pre->GetPosition();
    row.edep += deposit;
    Contribution& part = fContributions[{cell, step->GetTrack()->GetTrackID(), static_cast<int>(std::floor(pre->GetGlobalTime() / ns / fRules.timeBinNs))}];
    if (part.edep == 0.) {
      part.position = pre->GetPosition();
      part.time = pre->GetGlobalTime();
    }
    part.edep += deposit;
  }

  void EndEvent() {
    auto* manager = G4AnalysisManager::Instance();
    for (const auto& [id, row] : fTracks) {
      if (!row.kept) continue;
      const int parent = KeptAncestor(row.parent);
      int at = 0;
      manager->FillNtupleIColumn(0, at++, fEvent);
      manager->FillNtupleIColumn(0, at++, id);
      manager->FillNtupleIColumn(0, at++, parent);
      manager->FillNtupleIColumn(0, at++, row.pdg);
      manager->FillNtupleIColumn(0, at++, parent != row.parent ? 1 : 0);
      for (const G4ThreeVector& v : {row.vertex / mm, row.momentum / MeV, row.end / mm})
        for (int i = 0; i < 3; ++i) manager->FillNtupleDColumn(0, at++, v[i]);
      manager->AddNtupleRow(0);
    }
    for (const TrackerRow& row : fTracker) {
      int at = 0;
      manager->FillNtupleIColumn(1, at++, fEvent);
      manager->FillNtupleIColumn(1, at++, row.step);
      manager->FillNtupleIColumn(1, at++, Owner(row.track));
      manager->FillNtupleDColumn(1, at++, row.cell);
      for (const G4ThreeVector& v : {row.position / mm, row.momentum / MeV})
        for (int i = 0; i < 3; ++i) manager->FillNtupleDColumn(1, at++, v[i]);
      manager->FillNtupleDColumn(1, at++, row.kinetic / MeV);
      manager->FillNtupleDColumn(1, at++, row.edep / MeV);
      manager->FillNtupleDColumn(1, at++, row.time / ns);
      manager->FillNtupleDColumn(1, at++, row.path / mm);
      manager->AddNtupleRow(1);
    }
    for (const auto& [cell, row] : fCalorimeter) {
      int at = 0;
      manager->FillNtupleIColumn(2, at++, fEvent);
      manager->FillNtupleDColumn(2, at++, cell);
      manager->FillNtupleDColumn(2, at++, row.edep / MeV);
      for (int i = 0; i < 3; ++i) manager->FillNtupleDColumn(2, at++, row.position[i] / mm);
      manager->AddNtupleRow(2);
    }
    std::map<std::tuple<double, int, int>, Contribution> merged;  // pruned tracks fall onto their kept ancestor
    for (const auto& [key, part] : fContributions) {
      Contribution& target = merged[{std::get<0>(key), Owner(std::get<1>(key)), std::get<2>(key)}];
      if (target.edep == 0.) {
        target.position = part.position;
        target.time = part.time;
      }
      target.edep += part.edep;
    }
    for (const auto& [key, part] : merged) {
      int at = 0;
      manager->FillNtupleIColumn(3, at++, fEvent);
      manager->FillNtupleDColumn(3, at++, std::get<0>(key));
      manager->FillNtupleIColumn(3, at++, std::get<1>(key));
      manager->FillNtupleIColumn(3, at++, std::get<2>(key));
      manager->FillNtupleDColumn(3, at++, part.edep / MeV);
      manager->FillNtupleDColumn(3, at++, part.time / ns);
      for (int i = 0; i < 3; ++i) manager->FillNtupleDColumn(3, at++, part.position[i] / mm);
      manager->AddNtupleRow(3);
    }
    for (const Crossing& row : fCrossings) {
      int at = 0;
      manager->FillNtupleIColumn(4, at++, fEvent);
      manager->FillNtupleIColumn(4, at++, row.plane);
      for (int i = 0; i < 3; ++i) manager->FillNtupleDColumn(4, at++, row.position[i] / mm);
      for (int i = 0; i < 3; ++i) manager->FillNtupleDColumn(4, at++, row.direction[i]);
      manager->FillNtupleDColumn(4, at++, row.energy / MeV);
      manager->FillNtupleDColumn(4, at++, row.time / ns);
      manager->AddNtupleRow(4);
    }
  }

 private:
  struct TrackRow {
    int parent = 0, pdg = 0;
    bool kept = false;
    G4ThreeVector vertex, momentum, end;
  };
  struct TrackerRow {
    int step, track;
    double cell;
    G4ThreeVector position, momentum;
    double kinetic, edep, time, path;
  };
  struct CaloRow {
    double edep = 0.;
    G4ThreeVector position;
  };
  struct Contribution {
    double edep = 0., time = 0.;
    G4ThreeVector position;
  };
  struct Crossing {
    int plane;
    G4ThreeVector position, direction;
    double energy, time;
  };

  int KeptAncestor(int id) const {
    while (id != 0) {
      const auto found = fTracks.find(id);
      if (found == fTracks.end()) return 0;
      if (found->second.kept) return id;
      id = found->second.parent;
    }
    return 0;
  }
  int Owner(int id) const {
    const auto found = fTracks.find(id);
    return found != fTracks.end() && found->second.kept ? id : KeptAncestor(id);
  }

  TruthRules fRules;
  std::vector<ReferencePlane> fPlanes;
  int fEvent = 0, fStep = 0;
  std::map<int, TrackRow> fTracks;
  std::vector<TrackerRow> fTracker;
  std::map<double, CaloRow> fCalorimeter;
  std::map<std::tuple<double, int, int>, Contribution> fContributions;
  std::set<std::size_t> fCrossed;
  std::vector<Crossing> fCrossings;
};

}  // namespace g4sim

#endif
