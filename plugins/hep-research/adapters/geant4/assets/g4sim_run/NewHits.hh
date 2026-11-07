// NewHits.hh: the hit file of a new specification (g4sim plan, Sections 9.2, 9.3). Flat ntuples written by g4tools; simroot's `hits` mode reads them. Written from the Geant4 11.4 API.
//
// Truth keeping: the primary, decay products, particles above a threshold, and particles crossing a reference plane are kept. Deposits of a track that is not kept go to its nearest kept
// ancestor, and a kept particle whose parent was dropped points there with ancestor_pruned set. Keeping is decided per track as it ends, and resolved at the end of the event.
// A hit's cell is its volume ID and the scorer's segmentation bin, kept exactly (HitColumns.hh). A step apportioned among bins makes one row per bin, each with its share of the deposit and the path, at the
// middle of the step's longest piece in that bin.
// G4SIM_HIT_CONTROL is for tests only, one fault each, and hits_closure.py must see it: see CONTROLS there. high_cells sets the top bit of every cell, so that a run can carry an ID no double holds through the file and simroot.
#ifndef G4SIM_NEWHITS_HH
#define G4SIM_NEWHITS_HH

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
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
#include "PlaneCrossing.hh"

namespace g4sim {

struct EnergyRule {
  double threshold = 0.;  // MeV
  std::string region;     // empty: everywhere
};

struct TruthRules {
  bool primary = true, decayProducts = false;
  bool all = false;  // every track: an oracle for the attribution, never a default
  std::vector<EnergyRule> energy;
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
    const char* control = std::getenv("G4SIM_HIT_CONTROL");
    fControl = control ? control : "";
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
    fEvent = static_cast<double>(event);
    fTracks.clear();
    fTracker.clear();
    fCalorimeter.clear();
    fContributions.clear();
    fCrossed.clear();
    fCrossings.clear();
    fStep = 0;
  }

  void BeginTrack(const G4Track* track) {
    const bool fresh = !fTracks.count(track->GetTrackID());  // a suspended track comes back here, and keeps what it was born with and what it has earned
    TrackRow& row = fTracks[track->GetTrackID()];
    if (!fresh) return;
    row.parent = track->GetParentID();
    row.pdg = track->GetDefinition()->GetPDGEncoding();
    row.vertex = track->GetVertexPosition();
    row.momentum = fControl == "momentum_zero" ? G4ThreeVector() : track->GetMomentum();
    row.kinetic = track->GetKineticEnergy() * (fControl == "secondary_energy_doubled" && track->GetParentID() != 0 ? 2. : 1.);
    const G4VProcess* creator = track->GetCreatorProcess();
    row.decay = creator && creator->GetProcessType() == fDecay;
    row.kept = fRules.all || (track->GetParentID() == 0 && fRules.primary) || (row.decay && fRules.decayProducts && fControl != "decay_rule_off");
  }

  void EndTrack(const G4Track* track) {
    TrackRow& row = fTracks[track->GetTrackID()];
    row.end = track->GetPosition();
    const bool left = !track->GetNextVolume();
    row.status = left != (fControl == "status_swapped") ? kLeftTheWorld : kEndedInside;
  }

  void Step(const G4Step* step) {
    const G4Track* track = step->GetTrack();
    const G4StepPoint* pre = step->GetPreStepPoint();
    const G4StepPoint* post = step->GetPostStepPoint();
    if (track->GetCurrentStepNumber() == 1) {
      const std::string& region = pre->GetPhysicalVolume()->GetLogicalVolume()->GetRegion()->GetName();
      for (const EnergyRule& rule : fRules.energy)
        if ((track->GetVertexKineticEnergy() / MeV > rule.threshold || fControl == "threshold_ignored") && (rule.region.empty() || rule.region == region)) fTracks[track->GetTrackID()].kept = true;
    }
    for (std::size_t i = 0; i < fPlanes.size(); ++i) {
      const double z = fPlanes[i].z * mm;
      if (!StepCrosses(pre->GetPosition().z() - z, post->GetPosition().z() - z)) continue;
      if (!fCrossed.insert({fControl == "one_crossing_per_event" ? 0 : track->GetTrackID(), i}).second) continue;
      const bool smooth = EndedSmoothly(step);
      const auto vector = [](const G4ThreeVector& v) { return Vector3{v.x(), v.y(), v.z()}; };
      const PlaneCrossing crossing = CrossingOf(vector(pre->GetPosition()), vector(pre->GetMomentumDirection()), vector(post->GetPosition()), vector(post->GetMomentumDirection()), step->GetStepLength(), z, smooth);
      G4ThreeVector point(crossing.position[0], crossing.position[1], crossing.position[2]);
      if (fControl == "crossing_at_pre_step") point = pre->GetPosition();
      if (fControl == "crossing_offset") point += G4ThreeVector(0., 0.5 * mm, 0.);
      const double energy = fControl == "crossing_energy_zero" ? 0. : KineticAt(step, crossing.fraction);
      const double time = fControl == "crossing_time_zero" ? 0. : pre->GetGlobalTime() + crossing.fraction * (post->GetGlobalTime() - pre->GetGlobalTime());
      fCrossings.push_back({static_cast<int>(i), track->GetTrackID(), point, G4ThreeVector(crossing.direction[0], crossing.direction[1], crossing.direction[2]), energy, time});
      fTracks[track->GetTrackID()].kept = true;
    }
  }

  // `deposit` is in MeV: the scorer's value for this cell and bin. `share` is the part of the step in the bin and `along` a point of that part along the step, from 0 to 1.
  void Tracker(const G4Step* step, std::uint64_t cell, int segment, double deposit, double share, double along) {
    if (fControl == "pieces_repeat_the_step") share = 1., along = 0.;
    const G4StepPoint* pre = step->GetPreStepPoint();
    const G4StepPoint* post = step->GetPostStepPoint();
    const double time = fControl == "time_zero" ? 0. : pre->GetGlobalTime() + (fControl == "time_not_interpolated" ? 0. : along) * (post->GetGlobalTime() - pre->GetGlobalTime());
    double kinetic = KineticAt(step, along);
    if (fControl == "kinematics_across_the_kink") kinetic = pre->GetKineticEnergy() + along * (post->GetKineticEnergy() - pre->GetKineticEnergy());
    G4ThreeVector momentum = DirectionAt(step, along) * std::sqrt(kinetic * (kinetic + 2. * step->GetTrack()->GetDynamicParticle()->GetMass()));
    if (fControl == "tracker_kinematics_zero") momentum = G4ThreeVector(), kinetic = 0.;
    fTracker.push_back({fStep++, step->GetTrack()->GetTrackID(), step->GetTrack()->GetCurrentStepNumber(), Marked(cell), segment, Along(step, along), momentum, kinetic, deposit, time, share * step->GetStepLength()});
  }

  void Calorimeter(const G4Step* step, std::uint64_t cell, int segment, double deposit, double along) {
    const G4StepPoint* pre = step->GetPreStepPoint();
    const G4StepPoint* post = step->GetPostStepPoint();
    cell = Marked(cell);
    const G4ThreeVector position = Along(step, along);
    const double time = pre->GetGlobalTime() + (fControl == "contribution_time_not_interpolated" ? 0. : along) * (post->GetGlobalTime() - pre->GetGlobalTime());
    CaloRow& row = fCalorimeter[{cell, segment}];
    if (row.edep == 0.) row.position = position;
    row.edep += deposit;
    Contribution& part = fContributions[{cell, segment, step->GetTrack()->GetTrackID(), std::floor(time / ns / fRules.timeBinNs)}];
    if (part.edep == 0.) {
      part.position = position;
      part.time = fControl == "time_zero" ? 0. : time;
    }
    part.edep += deposit;
  }

  void EndEvent() {
    auto* manager = G4AnalysisManager::Instance();
    for (const auto& [id, row] : fTracks) {
      if (!row.kept) continue;
      const int parent = KeptAncestor(row.parent);
      int at = 0;
      manager->FillNtupleDColumn(0, at++, fEvent);
      manager->FillNtupleIColumn(0, at++, id);
      manager->FillNtupleIColumn(0, at++, parent);
      manager->FillNtupleIColumn(0, at++, row.pdg);
      manager->FillNtupleIColumn(0, at++, parent != row.parent ? 1 : 0);
      manager->FillNtupleIColumn(0, at++, row.status);
      manager->FillNtupleIColumn(0, at++, row.decay ? 1 : 0);
      for (const G4ThreeVector& v : {row.vertex / mm, row.momentum / MeV})
        for (int i = 0; i < 3; ++i) manager->FillNtupleDColumn(0, at++, v[i]);
      manager->FillNtupleDColumn(0, at++, row.kinetic / MeV);
      for (int i = 0; i < 3; ++i) manager->FillNtupleDColumn(0, at++, row.end[i] / mm);
      manager->AddNtupleRow(0);
    }
    for (const TrackerRow& row : fTracker) {
      int at = 0;
      manager->FillNtupleDColumn(1, at++, fEvent);
      manager->FillNtupleIColumn(1, at++, row.step);
      manager->FillNtupleIColumn(1, at++, Owner(row.track));
      manager->FillNtupleIColumn(1, at++, row.track);
      manager->FillNtupleIColumn(1, at++, row.stepNumber);
      manager->FillNtupleIColumn(1, at++, CellHigh(row.cell));
      manager->FillNtupleIColumn(1, at++, CellLow(row.cell));
      manager->FillNtupleIColumn(1, at++, row.segment);
      for (const G4ThreeVector& v : {row.position / mm, row.momentum / MeV})
        for (int i = 0; i < 3; ++i) manager->FillNtupleDColumn(1, at++, v[i]);
      manager->FillNtupleDColumn(1, at++, row.kinetic / MeV);
      manager->FillNtupleDColumn(1, at++, row.edep);
      manager->FillNtupleDColumn(1, at++, row.time / ns);
      manager->FillNtupleDColumn(1, at++, row.path / mm);
      manager->AddNtupleRow(1);
    }
    for (const auto& [key, row] : fCalorimeter) {
      int at = 0;
      manager->FillNtupleDColumn(2, at++, fEvent);
      manager->FillNtupleIColumn(2, at++, CellHigh(key.first));
      manager->FillNtupleIColumn(2, at++, CellLow(key.first));
      manager->FillNtupleIColumn(2, at++, key.second);
      manager->FillNtupleDColumn(2, at++, row.edep);
      for (int i = 0; i < 3; ++i) manager->FillNtupleDColumn(2, at++, row.position[i] / mm);
      manager->AddNtupleRow(2);
    }
    std::map<ContributionKey, Contribution> merged;  // pruned tracks fall onto their kept ancestor
    for (const auto& [key, part] : fContributions) {
      Contribution& target = merged[{std::get<0>(key), std::get<1>(key), Owner(std::get<2>(key)), std::get<3>(key)}];
      if (target.edep == 0.) {
        target.position = part.position;
        target.time = part.time;
      }
      target.edep += part.edep;
    }
    for (const auto& [key, part] : merged) {
      int at = 0;
      manager->FillNtupleDColumn(3, at++, fEvent);
      manager->FillNtupleIColumn(3, at++, CellHigh(std::get<0>(key)));
      manager->FillNtupleIColumn(3, at++, CellLow(std::get<0>(key)));
      manager->FillNtupleIColumn(3, at++, std::get<1>(key));
      manager->FillNtupleIColumn(3, at++, std::get<2>(key));
      manager->FillNtupleDColumn(3, at++, std::get<3>(key));
      manager->FillNtupleDColumn(3, at++, part.edep);
      manager->FillNtupleDColumn(3, at++, part.time / ns);
      for (int i = 0; i < 3; ++i) manager->FillNtupleDColumn(3, at++, part.position[i] / mm);
      manager->AddNtupleRow(3);
    }
    for (const Crossing& row : fCrossings) {
      int at = 0;
      manager->FillNtupleDColumn(4, at++, fEvent);
      manager->FillNtupleIColumn(4, at++, row.plane);
      manager->FillNtupleIColumn(4, at++, row.track);
      for (int i = 0; i < 3; ++i) manager->FillNtupleDColumn(4, at++, row.position[i] / mm);
      for (int i = 0; i < 3; ++i) manager->FillNtupleDColumn(4, at++, row.direction[i]);
      manager->FillNtupleDColumn(4, at++, row.energy / MeV);
      manager->FillNtupleDColumn(4, at++, row.time / ns);
      manager->AddNtupleRow(4);
    }
  }

 private:
  enum SimulationStatus { kNotEnded = 0, kEndedInside = 1, kLeftTheWorld = 2 };
  using ContributionKey = std::tuple<std::uint64_t, int, int, double>;  // cell, segment, track, time bin
  struct TrackRow {
    int parent = 0, pdg = 0, status = kNotEnded;
    bool kept = false, decay = false;
    double kinetic = 0.;
    G4ThreeVector vertex, momentum, end;
  };
  struct TrackerRow {
    int step, track, stepNumber;
    std::uint64_t cell;
    int segment;
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
    int plane, track;
    G4ThreeVector position, direction;
    double energy, time;
  };

  // A step's post-step energy and direction hold what a discrete process did at its end, so neither is spread along the step: what the step deposited is lost along it, and the direction turns
  // only when Transportation ended the step, which is then the curve of a field.
  static double KineticAt(const G4Step* step, double along) { return std::max(step->GetPreStepPoint()->GetKineticEnergy() - along * step->GetTotalEnergyDeposit(), step->GetPostStepPoint()->GetKineticEnergy()); }
  static bool EndedSmoothly(const G4Step* step) {
    const G4VProcess* ended = step->GetPostStepPoint()->GetProcessDefinedStep();
    return ended && ended->GetProcessType() == fTransportation;
  }
  static G4ThreeVector DirectionAt(const G4Step* step, double along) {
    const G4ThreeVector& first = step->GetPreStepPoint()->GetMomentumDirection();
    return EndedSmoothly(step) ? (first + along * (step->GetPostStepPoint()->GetMomentumDirection() - first)).unit() : first;
  }

  static G4ThreeVector Along(const G4Step* step, double along) { return step->GetPreStepPoint()->GetPosition() + along * (step->GetPostStepPoint()->GetPosition() - step->GetPreStepPoint()->GetPosition()); }

  std::uint64_t Marked(std::uint64_t cell) const { return fControl == "high_cells" ? cell | (std::uint64_t{1} << 63) : cell; }

  int KeptAncestor(int id) const {
    int top = 0;
    while (id != 0) {
      const auto found = fTracks.find(id);
      if (found == fTracks.end()) return top;
      if (found->second.kept) {
        if (fControl != "ancestor_is_primary") return id;
        top = id;
      }
      id = found->second.parent;
    }
    return top;
  }
  int Owner(int id) const {
    const auto found = fTracks.find(id);
    return found != fTracks.end() && found->second.kept ? id : KeptAncestor(id);
  }

  TruthRules fRules;
  std::vector<ReferencePlane> fPlanes;
  std::string fControl;
  double fEvent = 0.;
  int fStep = 0;
  std::map<int, TrackRow> fTracks;
  std::vector<TrackerRow> fTracker;
  std::map<std::pair<std::uint64_t, int>, CaloRow> fCalorimeter;
  std::map<ContributionKey, Contribution> fContributions;
  std::set<std::pair<int, std::size_t>> fCrossed;
  std::vector<Crossing> fCrossings;
};

}  // namespace g4sim

#endif
