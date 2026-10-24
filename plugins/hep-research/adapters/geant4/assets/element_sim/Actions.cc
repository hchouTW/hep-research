#include "Actions.hh"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <set>

#include "Detector.hh"
#include "Field.hh"
#include "G4AccumulableManager.hh"
#include "G4AnalysisManager.hh"
#include "G4Event.hh"
#include "G4FieldManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4ProcessTable.hh"
#include "G4Run.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4Threading.hh"
#include "G4Track.hh"
#include "G4VProcess.hh"
#include "SimCsv.hh"
#include "SimObservables.hh"
#include "SimProbe.hh"
#include "SimSeed.hh"

using g4sim::Fmt;

void EventRecord::Reset(std::size_t nElements) {
  *this = EventRecord();
  edep.assign(nElements, 0.);
  plen.assign(nElements, 0.);
}

std::vector<std::string> CsvColumns(const Spec& spec) {
  std::vector<std::string> c = {"event", "chunk", "weight", "primary_pdg", "primary_ekin_MeV", "primary_x_mm",
                                "primary_y_mm", "primary_z_mm", "primary_dx", "primary_dy", "primary_dz"};
  for (const auto& e : spec.elements) c.push_back("edep_" + e.name + "_MeV");
  for (const auto& e : spec.elements) c.push_back("plen_" + e.name + "_mm");
  c.push_back("edep_world_MeV");
  c.push_back("escape_world_MeV");
  if (spec.CalorimeterIndex() >= 0)
    for (const char* n : {"leak_rear_MeV", "leak_front_MeV", "leak_lateral_MeV"}) c.push_back(n);
  return c;
}

std::string ThreadPath(const Spec& spec, const std::string& path, int thread) {
  return spec.run_manager == "mt" ? path + ".thread" + std::to_string(thread) : path;
}

RunFlags& Flags() {
  static RunFlags flags;
  return flags;
}

#ifdef ELEMENT_SIM_TEST_HOOKS
TestHooks& Hooks() {
  static TestHooks hooks;
  return hooks;
}
#endif

SummaryAccumulable::SummaryAccumulable(const Spec& spec)
    : G4VAccumulable("element_sim_summary"),
      fAcc(spec.observables.empty() ? g4sim::SummaryAccumulator()
                                    : g4sim::SummaryAccumulator(spec.observables, spec.block_size, spec.blocks,
                                                                spec.block_first_event)) {}

void SummaryAccumulable::Merge(const G4VAccumulable& other) {
  fAcc.Merge(static_cast<const SummaryAccumulable&>(other).fAcc);
}

RunAction::RunAction(const Spec& spec, const Detector& det, const RunInfo& info)
    : fSpec(spec), fDet(det), fInfo(info), fSummary(spec), fEventFile(spec) {
  if (!fSpec.observables.empty()) G4AccumulableManager::Instance()->Register(&fSummary);
  fEventFile.Book();
}

int RunAction::ProcessId(const std::string& name) const {
  auto it = fProcessIds.find(name);
  return it == fProcessIds.end() ? -1 : it->second;
}

void RunAction::BeginOfRunAction(const G4Run*) {
  if (!fSpec.observables.empty()) G4AccumulableManager::Instance()->Reset();
  if (G4Threading::IsMasterThread()) {  // once per run, master only (A2.4)
    g4sim::ProbeResult res = g4sim::RunProbe("element_sim: master BeginOfRunAction");
    std::ofstream(fSpec.probe_out) << res.json;
    if (!res.error.empty()) Flags().probeBadGeometry = true;
    if (!res.randomUnchanged) Flags().probeRandomChanged = true;
  }
  // process numbers: every process name of the process table, sorted (the same on every thread and in every job)
  std::set<std::string> names;
  for (const auto& n : *G4ProcessTable::GetProcessTable()->GetNameList()) names.insert(n);
  int k = 0;
  for (const auto& n : names) fProcessIds[n] = k++;
#ifdef ELEMENT_SIM_TEST_HOOKS
  if (Hooks().reportFieldManagers) {
    const auto& fms = ThreadFieldManagers();
    for (std::size_t r = 0; r < fms.size(); ++r)
      std::printf("ELEMENT_SIM_FIELD_MANAGER thread=%d region=%zu ptr=%p\n", G4Threading::G4GetThreadId(), r,
                  static_cast<void*>(fms[r]));
  }
#endif
  fEventFile.Open();
  bool mt = fSpec.run_manager == "mt";
  if (mt && G4Threading::IsMasterThread()) return;  // workers write; the master merges after the run
  int t = G4Threading::G4GetThreadId();
  fOut.open(ThreadPath(fSpec, fSpec.csv, t));
  fOut << "# SIMULATION\n";
  auto cols = CsvColumns(fSpec);
  for (std::size_t i = 0; i < cols.size(); ++i) fOut << (i ? "," : "") << cols[i];
  fOut << "\n";
  if (fSpec.debug_observable_dump) {
    fDump.open(ThreadPath(fSpec, fSpec.dump_out, t));
    fDump << "# OBSERVABLE DUMP\nevent";
    for (const auto& c : g4sim::NeededColumns(fSpec.observables)) fDump << "," << c;
    fDump << "\n";
  }
}

void RunAction::FillRunRows() {
  auto* am = G4AnalysisManager::Instance();
  int run = fEventFile.Id("run"), proc = fEventFile.Id("processes");
  std::map<std::string, std::string> lists;
  for (const auto& d : fEventFile.Ntuples()) lists[d.name] = ColumnList(d);
  std::vector<std::string> text = {fSpec.spec_sha256, fInfo.column_map_sha256, "element_sim 0.3.0",
                                   fInfo.program_sources_sha256, fInfo.geant4_version};
  int c = 0;
  for (const auto& s : text) am->FillNtupleSColumn(run, c++, s);
  am->FillNtupleIColumn(run, c++, static_cast<int>(fSpec.logical_run_seed));
  am->FillNtupleIColumn(run, c++, static_cast<int>(fSpec.first_event));
  am->FillNtupleIColumn(run, c++, static_cast<int>(fSpec.first_event + fSpec.events - 1));
  am->FillNtupleSColumn(run, c++, kEventFileVersion);
  am->FillNtupleSColumn(run, c++, fSpec.event_level);
  for (const char* n : {"processes", "events", "deposits", "crossings", "hits"})
    am->FillNtupleSColumn(run, c++, lists.count(n) ? lists[n] : "");
  am->AddNtupleRow(run);
  for (const auto& [name, id] : fProcessIds) {
    am->FillNtupleIColumn(proc, 0, id);
    am->FillNtupleSColumn(proc, 1, name);
    am->AddNtupleRow(proc);
  }
}

void RunAction::EndOfRunAction(const G4Run*) {
  if (fOut.is_open()) fOut.close();
  if (fDump.is_open()) fDump.close();
  bool filler = G4Threading::IsMultithreadedApplication() ? G4Threading::G4GetThreadId() == 0
                                                           : true;  // worker 0 (G-B1a), or the serial thread
  if (fEventFile.Enabled() && filler) FillRunRows();
  fEventFile.Close();
  if (fSpec.observables.empty()) return;
  if (G4Threading::IsWorkerThread()) {
    G4AccumulableManager::Instance()->Merge();
  } else if (!Flags().weightRejected && !Flags().summaryError) {
    std::string run = "{\"seeding\": \"per-event\", \"logical_run_seed\": " + std::to_string(fSpec.logical_run_seed) +
                      ", \"weight_column\": \"unit\"}";
    std::ofstream(fSpec.summary_out) << fSummary.Acc().Json(run, "{\"name\": \"element_sim\", \"version\": \"0.3.0\"}");
  }
}

void EventAction::BeginOfEventAction(const G4Event*) { fRec.Reset(fSpec.elements.size()); }

void EventAction::FillEventFile(long number, const G4Event* event) {
  EventFile& ef = fRun->Events();
  if (!ef.Enabled()) return;
  auto* am = G4AnalysisManager::Instance();
  const G4PrimaryVertex* v = event->GetPrimaryVertex(0);
  const G4PrimaryParticle* p = v->GetPrimary(0);
  G4ThreeVector d = p->GetMomentumDirection();
  const EventRecord& r = fRec;
  int id = static_cast<int>(number);
  int ev = ef.Id("events"), c = 0;
  am->FillNtupleIColumn(ev, c++, id);
  am->FillNtupleIColumn(ev, c++, p->GetPDGcode());
  for (double x : {p->GetKineticEnergy() / MeV, v->GetX0() / mm, v->GetY0() / mm, v->GetZ0() / mm, d.x(), d.y(), d.z()})
    am->FillNtupleDColumn(ev, c++, x);
  for (double e : r.edep) am->FillNtupleDColumn(ev, c++, e / MeV);
  for (double l : r.plen) am->FillNtupleDColumn(ev, c++, l / mm);
  am->FillNtupleDColumn(ev, c++, r.edepWorld / MeV);
  am->FillNtupleDColumn(ev, c++, r.escapeWorld / MeV);
  if (fSpec.CalorimeterIndex() >= 0)
    for (double x : {r.leakRear, r.leakFront, r.leakLateral}) am->FillNtupleDColumn(ev, c++, x / MeV);
  am->FillNtupleIColumn(ev, c++, (r.nonUnitWeight ? 1 : 0) | (r.primaryLeftWorld ? 2 : 0));
  am->AddNtupleRow(ev);
  int dep = ef.Id("deposits");
  for (const auto& [key, val] : r.deposits) {
    am->FillNtupleIColumn(dep, 0, id);
    am->FillNtupleIColumn(dep, 1, key.first);
    am->FillNtupleIColumn(dep, 2, key.second);
    am->FillNtupleDColumn(dep, 3, val.first / MeV);
    am->FillNtupleDColumn(dep, 4, val.second / MeV);
    am->AddNtupleRow(dep);
  }
  int cr = ef.Id("crossings");
  if (cr >= 0)
    for (const auto& x : r.crossings) {
      int k = 0;
      for (int i : {id, x.plane, x.copy, x.track, x.parent, x.pdg}) am->FillNtupleIColumn(cr, k++, i);
      for (double y : {x.pos.x() / mm, x.pos.y() / mm, x.pos.z() / mm, x.dir.x(), x.dir.y(), x.dir.z(), x.ekin / MeV,
                       x.time / ns, x.edep / MeV})
        am->FillNtupleDColumn(cr, k++, y);
      am->AddNtupleRow(cr);
    }
  int hi = ef.Id("hits");
  if (hi >= 0)
    for (const auto& h : r.hits) {
      int k = 0;
      for (int i : {id, h.track, h.step, h.parent, h.pdg, h.volume, h.copy}) am->FillNtupleIColumn(hi, k++, i);
      for (double y : {h.pre.x() / mm, h.pre.y() / mm, h.pre.z() / mm, h.post.x() / mm, h.post.y() / mm,
                       h.post.z() / mm, h.time / ns, h.edep / MeV, h.length / mm})
        am->FillNtupleDColumn(hi, k++, y);
      am->FillNtupleIColumn(hi, k++, h.process);
      am->AddNtupleRow(hi);
    }
}

void EventAction::EndOfEventAction(const G4Event* event) {
  long number = fSpec.first_event + event->GetEventID();
  FillEventFile(number, event);
  auto& o = fRun->Out();
  if (!o.is_open()) return;
  const G4PrimaryVertex* v = event->GetPrimaryVertex(0);
  const G4PrimaryParticle* p = v->GetPrimary(0);
  G4ThreeVector d = p->GetMomentumDirection();
  const EventRecord& r = fRec;
  std::vector<double> values = {static_cast<double>(number), static_cast<double>(fSpec.chunk), v->GetWeight(),
                                static_cast<double>(p->GetPDGcode()), p->GetKineticEnergy() / MeV, v->GetX0() / mm,
                                v->GetY0() / mm, v->GetZ0() / mm, d.x(), d.y(), d.z()};
  for (double e : r.edep) values.push_back(e / MeV);
  for (double l : r.plen) values.push_back(l / mm);
  values.push_back(r.edepWorld / MeV);
  values.push_back(r.escapeWorld / MeV);
  if (fSpec.CalorimeterIndex() >= 0)
    for (double x : {r.leakRear, r.leakFront, r.leakLateral}) values.push_back(x / MeV);
  o << number << "," << fSpec.chunk;
  for (std::size_t i = 2; i < values.size(); ++i) {
    if (i == 3) o << "," << p->GetPDGcode();
    else o << "," << Fmt(values[i]);
  }
  o << "\n";
  if (fSpec.observables.empty()) return;
  if (v->GetWeight() != 1. || r.nonUnitWeight) {
    Flags().weightRejected = true;
    G4RunManager::GetRunManager()->AbortRun(true);
    return;
  }
  if (fCols.empty()) {
    fCols = CsvColumns(fSpec);
    fNeeded = g4sim::NeededColumns(fSpec.observables);
  }
  g4sim::Row row;
  for (std::size_t i = 0; i < fCols.size(); ++i) row[fCols[i]] = g4sim::Cell::Number(values[i]);
  try {
    fRun->Summary().Acc().Fill(number, row);
  } catch (const g4sim::SummaryError& e) {
    G4cerr << "element_sim: " << e.what() << G4endl;
    Flags().summaryError = true;
    G4RunManager::GetRunManager()->AbortRun(true);
    return;
  }
  std::ofstream& dump = fRun->Dump();
  if (dump.is_open()) {
    dump << number;
    for (const auto& c : fNeeded) {
      char buf[40];
      std::snprintf(buf, sizeof buf, "%.17g", row.at(c).num);
      dump << "," << buf;
    }
    dump << "\n";
  }
}

SteppingAction::SteppingAction(const Spec& spec, const Detector& det, EventAction* ev, RunAction* run)
    : fSpec(spec), fDet(det), fEv(ev), fRun(run), fCalo(spec.CalorimeterIndex()), fLevelSummary(spec.Level("summary")),
      fLevelCrossings(spec.Level("crossings")), fLevelHits(spec.Level("hits")) {
  for (const auto& e : spec.elements) {
    bool calo = fCalo >= 0 && (e.name == spec.elements[fCalo].name || e.mother == spec.elements[fCalo].name);
    fInCalo.push_back(calo);
    fPlane.push_back(e.role == "tracker-plane" || e.role == "tof-layer");
  }
}

void SteppingAction::UserSteppingAction(const G4Step* step) {
  EventRecord& r = fEv->Record();
  const G4Track* track = step->GetTrack();
  const G4StepPoint* pre = step->GetPreStepPoint();
  const G4StepPoint* post = step->GetPostStepPoint();
  double w = track->GetWeight();
  if (w != 1.) r.nonUnitWeight = true;
  double edep = step->GetTotalEnergyDeposit() * w;
  bool charged = track->GetDefinition()->GetPDGCharge() != 0.;
  int pdg = track->GetDefinition()->GetPDGEncoding();
  int idx = fDet.ElementIndex(pre->GetTouchableHandle()->GetVolume()->GetLogicalVolume());
  int copy = pre->GetTouchableHandle()->GetCopyNumber();
  if (idx >= 0) {
    r.edep[idx] += edep;
    if (track->GetTrackID() == 1) r.plen[idx] += step->GetStepLength();
    if (fLevelSummary && edep != 0.) {
      auto& d = r.deposits[{idx, copy}];
      d.first += edep;
      if (charged) d.second += edep;
    }
  } else {
    r.edepWorld += edep;
  }
  // plane crossings: the first entry of every charged track into a tracker plane or TOF layer (B1.3)
  if (idx >= 0 && fPlane[idx] && charged && fLevelCrossings) {
    auto key = std::make_tuple(idx, copy, track->GetTrackID());
    auto it = r.crossingIndex.find(key);
    bool record = true;
#ifdef ELEMENT_SIM_TEST_HOOKS
    if (Hooks().primaryOnlyCrossings && track->GetTrackID() != 1) record = false;
#endif
    if (it == r.crossingIndex.end() && record && pre->GetStepStatus() == fGeomBoundary) {
      CrossingRow x;
      x.plane = idx;
      x.copy = copy;
      x.track = track->GetTrackID();
      x.parent = track->GetParentID();
      x.pdg = pdg;
      x.pos = pre->GetPosition();
      x.dir = pre->GetMomentumDirection();
      x.ekin = pre->GetKineticEnergy();
      x.time = pre->GetGlobalTime();
      x.edep = edep;
      r.crossingIndex[key] = r.crossings.size();
      r.crossings.push_back(x);
    } else if (it != r.crossingIndex.end()) {
      r.crossings[it->second].edep += edep;
    }
  }
  if (fLevelHits && edep != 0.) {
    HitRow h;
    h.track = track->GetTrackID();
    h.step = track->GetCurrentStepNumber();
    h.parent = track->GetParentID();
    h.pdg = pdg;
    h.volume = idx;
    h.copy = copy;
    h.pre = pre->GetPosition();
    h.post = post->GetPosition();
    h.time = pre->GetGlobalTime();
    h.edep = edep;
    h.length = step->GetStepLength();
    const G4VProcess* proc = post->GetProcessDefinedStep();
    h.process = proc ? fRun->ProcessId(proc->GetProcessName()) : -1;
    r.hits.push_back(h);
  }
  auto carried = [&]() {  // the energy a particle takes with it: kinetic, plus 2 m_e c^2 for an e+ (it annihilates)
    double ek = post->GetKineticEnergy() * w;
    if (pdg == -11) ek += 2 * CLHEP::electron_mass_c2 * w;
    return ek;
  };
  // calorimeter leakage, the net outflow per face: a step that starts inside the calorimeter mother (or a daughter)
  // and ends outside adds the energy it carries to the face it leaves through; a step that enters from outside
  // subtracts it from the face it enters through (energy coming back, e.g. backsplash returned by TOF2), except the
  // primary's first entry (the incident particle is the input, not a return)
  if (fCalo >= 0) {
    const G4VPhysicalVolume* pv = post->GetTouchableHandle()->GetVolume();
    int pidx = pv ? fDet.ElementIndex(pv->GetLogicalVolume()) : -1;
    bool preIn = idx >= 0 && fInCalo[idx], postIn = pidx >= 0 && fInCalo[pidx];
    bool incident = !preIn && postIn && track->GetTrackID() == 1 && !r.primaryEnteredCalo;
    if (incident) r.primaryEnteredCalo = true;
    if (preIn != postIn && !incident) {
      const ElementDef& c = fSpec.elements[fCalo];
      G4ThreeVector local = post->GetPosition() - G4ThreeVector(c.CopyCentre(0)[0] * mm, c.CopyCentre(0)[1] * mm,
                                                                 c.CopyCentre(0)[2] * mm);
      double rx = std::fabs(local.x()) / (c.half_mm[0] * mm), ry = std::fabs(local.y()) / (c.half_mm[1] * mm),
             rz = std::fabs(local.z()) / (c.half_mm[2] * mm);
      double ek = preIn ? carried() : -carried();
      if (rx >= ry && rx >= rz) (local.x() > 0 ? r.leakRear : r.leakFront) += ek;
      else r.leakLateral += ek;
    }
  }
  if (post->GetStepStatus() == fWorldBoundary) {
    r.escapeWorld += carried();
    if (track->GetTrackID() == 1) r.primaryLeftWorld = true;
  }
}

PrimaryGenerator::PrimaryGenerator(const Spec& spec) : fSpec(spec), fGun(new G4ParticleGun(1)) {
  fGun->SetParticleDefinition(G4ParticleTable::GetParticleTable()->FindParticle(spec.particle));
  fGun->SetParticleEnergy(spec.energy_MeV * MeV);
  fGun->SetParticleMomentumDirection(G4ThreeVector(spec.direction[0], spec.direction[1], spec.direction[2]).unit());
  fGun->SetParticlePosition(G4ThreeVector(spec.position_mm[0] * mm, spec.position_mm[1] * mm, spec.position_mm[2] * mm));
}

PrimaryGenerator::~PrimaryGenerator() { delete fGun; }

void PrimaryGenerator::GeneratePrimaries(G4Event* event) {
  long long number = fSpec.first_event + event->GetEventID();
  g4sim::ReseedEvent(fSpec.logical_run_seed, number);  // before any random draw of this event (A2.2)
  if (!fSpec.cycle.empty()) {
    const CycleEntry& c = fSpec.cycle[static_cast<std::size_t>(number % static_cast<long long>(fSpec.cycle.size()))];
    fGun->SetParticleEnergy(c.energy_MeV * MeV);
    fGun->SetParticleMomentumDirection(G4ThreeVector(c.direction[0], c.direction[1], c.direction[2]).unit());
  }
  fGun->GeneratePrimaryVertex(event);
}

void ActionInitialization::BuildForMaster() const { SetUserAction(new RunAction(fSpec, fDet, fInfo)); }

void ActionInitialization::Build() const {
  auto* run = new RunAction(fSpec, fDet, fInfo);
  auto* ev = new EventAction(fSpec, run);
  SetUserAction(new PrimaryGenerator(fSpec));
  SetUserAction(run);
  SetUserAction(ev);
  SetUserAction(new SteppingAction(fSpec, fDet, ev, run));
}
