#include "Actions.hh"

#include <cmath>
#include <cstdio>
#include <cstdlib>

#include "Detector.hh"
#include "G4Event.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4Run.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4Threading.hh"
#include "G4Track.hh"
#include "G4VProcess.hh"

namespace {

std::string Fmt(double x) {
  char buf[40];
  std::snprintf(buf, sizeof buf, "%.10g", x);
  return buf;
}

bool IsNeutrino(int pdg) {
  int a = std::abs(pdg);
  return a == 12 || a == 14 || a == 16;
}

}  // namespace

void EventRecord::Reset(std::size_t nSlabs, std::size_t nInst) {
  *this = EventRecord();
  edep.assign(nSlabs, 0.);
  chlen.assign(nSlabs, 0.);
  plen.assign(nSlabs, 0.);
  edepInst.assign(nInst, 0.);
}

std::vector<std::string> CsvColumns(const Spec& spec, const Detector& det) {
  std::vector<std::string> c = {"event", "chunk", "weight", "primary_pdg", "primary_ekin_MeV", "primary_x_mm",
                                "primary_y_mm", "primary_z_mm", "primary_dx", "primary_dy", "primary_dz"};
  for (const auto& n : det.SlabNames()) {
    c.push_back("edep_" + n + "_MeV");
    c.push_back("chlen_" + n + "_mm");
    c.push_back("plen_" + n + "_mm");
  }
  if (spec.per_instance)
    for (int i = 0; i < det.NumberOfPlacements(); ++i) c.push_back("edep_copy" + std::to_string(i) + "_MeV");
  for (const char* n : {"edep_world_MeV", "leak_gamma_MeV", "leak_e_MeV", "leak_nu_MeV", "leak_other_MeV",
                        "killed_booked_MeV", "killed_unbooked_MeV", "killed_eplus", "exit_ekin_MeV", "primary_eloss_MeV", "exit_dx",
                        "exit_dy", "exit_dz", "primary_fate", "primary_end_x_mm", "primary_end_process",
                        "n_sec_gamma", "n_sec_electron", "n_sec_positron", "n_sec_other"})
    c.push_back(n);
  return c;
}

std::string ThreadCsvPath(const Spec& spec, int thread) {
  return spec.run_manager == "mt" ? spec.csv + ".thread" + std::to_string(thread) : spec.csv;
}

void RunAction::BeginOfRunAction(const G4Run*) {
  bool mt = fSpec.run_manager == "mt";
  if (mt && G4Threading::IsMasterThread()) return;  // workers write; the master merges after the run
  fOut.open(ThreadCsvPath(fSpec, G4Threading::G4GetThreadId()));
  fOut << "# SIMULATION\n";
  auto cols = CsvColumns(fSpec, fDet);
  for (std::size_t i = 0; i < cols.size(); ++i) fOut << (i ? "," : "") << cols[i];
  fOut << "\n";
}

void RunAction::EndOfRunAction(const G4Run*) {
  if (fOut.is_open()) fOut.close();
}

void EventAction::BeginOfEventAction(const G4Event*) {
  fRec.Reset(fDet.SlabNames().size(), fSpec.per_instance ? fDet.NumberOfPlacements() : 0);
}

void EventAction::EndOfEventAction(const G4Event* event) {
  auto& o = fRun->Out();
  if (!o.is_open()) return;
  const G4PrimaryVertex* v = event->GetPrimaryVertex(0);
  const G4PrimaryParticle* p = v->GetPrimary(0);
  G4ThreeVector d = p->GetMomentumDirection();
  const EventRecord& r = fRec;
  o << (fSpec.first_event + event->GetEventID()) << "," << fSpec.chunk << "," << Fmt(v->GetWeight()) << ","
    << p->GetPDGcode() << "," << Fmt(p->GetKineticEnergy() / MeV) << "," << Fmt(v->GetX0() / mm) << ","
    << Fmt(v->GetY0() / mm) << "," << Fmt(v->GetZ0() / mm) << "," << Fmt(d.x()) << "," << Fmt(d.y()) << ","
    << Fmt(d.z());
  for (std::size_t i = 0; i < r.edep.size(); ++i)
    o << "," << Fmt(r.edep[i] / MeV) << "," << Fmt(r.chlen[i] / mm) << "," << Fmt(r.plen[i] / mm);
  for (double e : r.edepInst) o << "," << Fmt(e / MeV);
  o << "," << Fmt(r.edepWorld / MeV) << "," << Fmt(r.leakGamma / MeV) << "," << Fmt(r.leakE / MeV) << ","
    << Fmt(r.leakNu / MeV) << "," << Fmt(r.leakOther / MeV) << "," << Fmt(r.killedBooked / MeV) << ","
    << Fmt(r.killedUnbooked / MeV) << "," << r.killedEplus << "," << Fmt(r.exitEkin / MeV) << ","
    << Fmt((p->GetKineticEnergy() - r.exitEkin) / MeV) << ","
    << Fmt(r.exitDir.x()) << "," << Fmt(r.exitDir.y()) << "," << Fmt(r.exitDir.z()) << "," << r.fate << ","
    << Fmt(r.endX / mm) << "," << (r.endProcess.empty() ? "none" : r.endProcess) << "," << r.nGamma << ","
    << r.nElectron << "," << r.nPositron << "," << r.nOther << "\n";
}

void SteppingAction::UserSteppingAction(const G4Step* step) {
  EventRecord& r = fEv->Record();
  const G4Track* track = step->GetTrack();
  const G4StepPoint* pre = step->GetPreStepPoint();
  const G4StepPoint* post = step->GetPostStepPoint();
  double w = track->GetWeight();
  double edep = step->GetTotalEnergyDeposit() * w;
  bool primary = track->GetTrackID() == 1;
  int idx = fDet.SlabIndex(pre->GetTouchableHandle()->GetVolume()->GetLogicalVolume());
  if (idx >= 0) {
    r.edep[idx] += edep;
    if (track->GetDefinition()->GetPDGCharge() != 0.) r.chlen[idx] += step->GetStepLength();
    if (primary) r.plen[idx] += step->GetStepLength();
    if (fSpec.per_instance) r.edepInst[pre->GetTouchableHandle()->GetCopyNumber()] += edep;
  } else {
    r.edepWorld += edep;
  }
  const G4VProcess* proc = post->GetProcessDefinedStep();
  std::string pname = proc ? proc->GetProcessName() : "";
  int pdg = track->GetDefinition()->GetPDGEncoding();
  if (pname == "UserSpecialCut") {
    // G4UserSpecialCuts books the track's kinetic energy as a local deposit, already in edep above; recorded here
    // as the kinetic energy at the start of the step (an upper bound when the step also had continuous loss)
    r.killedBooked += pre->GetKineticEnergy() * w;
    if (pdg == -11) ++r.killedEplus;  // a killed e+ does not annihilate
  }
  if (post->GetStepStatus() == fWorldBoundary) {
    double ek = post->GetKineticEnergy() * w;
    if (pdg == 22) r.leakGamma += ek;
    else if (std::abs(pdg) == 11) r.leakE += ek + (pdg == -11 ? 2 * CLHEP::electron_mass_c2 * w : 0.);
    else if (IsNeutrino(pdg)) r.leakNu += ek;
    else r.leakOther += ek;
    if (primary) {
      r.exitEkin = post->GetKineticEnergy();
      r.exitDir = post->GetMomentumDirection();
      r.fate = r.exitDir.x() >= 0 ? 1 : -1;
      r.endX = post->GetPosition().x();
      r.endProcess = "Transportation";
    }
  } else if (primary && track->GetTrackStatus() != fAlive) {
    r.endX = post->GetPosition().x();
    r.endProcess = pname;
  }
}

G4ClassificationOfNewTrack StackingAction::ClassifyNewTrack(const G4Track* track) {
  if (track->GetParentID() == 0) return fUrgent;
  EventRecord& r = fEv->Record();
  int pdg = track->GetDefinition()->GetPDGEncoding();
  if (pdg == 22) ++r.nGamma;
  else if (pdg == 11) ++r.nElectron;
  else if (pdg == -11) ++r.nPositron;
  else ++r.nOther;
  if (fSpec.kill_secondaries) {
    r.killedUnbooked += track->GetKineticEnergy() * track->GetWeight();
    if (pdg == -11) ++r.killedEplus;
    return fKill;
  }
  return fUrgent;
}

PrimaryGenerator::PrimaryGenerator(const Spec& spec, const Detector& det)
    : fSpec(spec), fDet(det), fGun(new G4ParticleGun(1)) {
  fGun->SetParticleDefinition(G4ParticleTable::GetParticleTable()->FindParticle(spec.particle));
  fGun->SetParticleEnergy(spec.energy_MeV * MeV);
  fGun->SetParticleMomentumDirection(G4ThreeVector(spec.direction[0], spec.direction[1], spec.direction[2]).unit());
}

PrimaryGenerator::~PrimaryGenerator() { delete fGun; }

void PrimaryGenerator::GeneratePrimaries(G4Event* event) {
  fGun->SetParticlePosition(G4ThreeVector(fSpec.gun_world_fraction * fDet.WorldXLength(), 0, 0));
  fGun->GeneratePrimaryVertex(event);
}

void ActionInitialization::BuildForMaster() const { SetUserAction(new RunAction(fSpec, fDet)); }

void ActionInitialization::Build() const {
  auto* run = new RunAction(fSpec, fDet);
  auto* ev = new EventAction(fSpec, fDet, run);
  SetUserAction(new PrimaryGenerator(fSpec, fDet));
  SetUserAction(run);
  SetUserAction(ev);
  SetUserAction(new SteppingAction(fSpec, fDet, ev));
  SetUserAction(new StackingAction(fSpec, ev));
}
