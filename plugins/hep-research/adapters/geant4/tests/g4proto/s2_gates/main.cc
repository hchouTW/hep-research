// Prototypes GB3, GB5, GB7, GB8 and GB9 of the g4sim plan (Section 23): one program, judged by judge.py; it measures and gives no verdict.
// Written from the Geant4 11.4 API; no example code copied or adapted.
//   s2_gates gb9 OUT.json                decay tables and the unreleased-energy table
//   s2_gates gb7 OUT.json [MAX_STEP_MM]  G4UserSpecialCuts kills and e+- step lengths in silicon (a second run gets the limit)
//   s2_gates gb8 OUT.json | gb8em OUT.json   hadronic physics, a field and a low looper threshold; a pure-EM run
//   s2_gates gb5 OUT.json                steps seen by the stepping action and by two child SDs of one logical
//   s2_gates gb3 OUT.json ORDER          ORDER: forward, reverse, mother_only, none_manager, no_manager; field assignment and trajectories
#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <map>
#include <mutex>
#include <sstream>
#include <string>
#include <vector>

#include "Accounting.hh"
#include "FTFP_BERT.hh"
#include "G4Box.hh"
#include "G4ChargedGeantino.hh"
#include "G4ChordFinder.hh"
#include "G4DecayPhysics.hh"
#include "G4EmStandardPhysics_option4.hh"
#include "G4Field.hh"
#include "G4FieldManager.hh"
#include "G4IonTable.hh"
#include "G4LogicalVolume.hh"
#include "G4MultiSensitiveDetector.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4PropagatorInField.hh"
#include "G4Run.hh"
#include "G4RunManagerFactory.hh"
#include "G4SDManager.hh"
#include "G4StepLimiterPhysics.hh"
#include "G4SystemOfUnits.hh"
#include "G4Threading.hh"
#include "G4TransportationManager.hh"
#include "G4TransportationParameters.hh"
#include "G4UniformMagField.hh"
#include "G4UserEventAction.hh"
#include "G4UserLimits.hh"
#include "G4UserRunAction.hh"
#include "G4UserSteppingAction.hh"
#include "G4VSensitiveDetector.hh"
#include "G4VUserActionInitialization.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"

namespace {

std::string gMode, gOrder;
double gMaxStep = 0;
std::mutex gLock;
struct Totals {
  double killedKinetic = 0, killedDeposit = 0, maxElectronStep = 0, looperKinetic = 0, worstResidual = 0, worstRelative = 0;
  std::vector<double> electronSteps;
  long kills = 0, accountingErrors = 0, loopers = 0, tracks = 0, stepsAction = 0, sdFirst = 0, sdSecond = 0, eventsWithDifference = 0;
  std::vector<std::vector<double>> field_path, free_path;
  std::vector<std::string> sequences;
  std::map<std::string, std::map<std::string, std::string>> managers;
} gTotals;

std::string Hex(double value) {
  char text[64];
  std::snprintf(text, sizeof text, "%a", value);
  return text;
}

class CountingSD : public G4VSensitiveDetector {
 public:
  CountingSD(const G4String& name, long* count) : G4VSensitiveDetector(name), fCount(count) {}
  G4bool ProcessHits(G4Step*, G4TouchableHistory*) override {
    ++*fCount;
    return true;
  }
  long* fCount;
};
G4ThreadLocal long tFirst = 0, tSecond = 0, tAction = 0;
G4ThreadLocal std::string* tSequencePointer = nullptr;
#define tSequence (*(tSequencePointer ? tSequencePointer : (tSequencePointer = new std::string())))

class Detector : public G4VUserDetectorConstruction {
 public:
  G4VPhysicalVolume* Construct() override {
    auto* nist = G4NistManager::Instance();
    G4Material* vacuum = nist->FindOrBuildMaterial("G4_Galactic");
    auto* world = new G4LogicalVolume(new G4Box("World", 30 * m, 30 * m, 30 * m), vacuum, "World");
    auto* worldPlaced = new G4PVPlacement(nullptr, {}, world, "World", nullptr, false, 0);
    if (gMode == "gb3") {
      fWithField = new G4LogicalVolume(new G4Box("WithField", 10 * m, 10 * m, 5 * m), vacuum, "WithField");
      fFree = new G4LogicalVolume(new G4Box("Free", 10 * m, 10 * m, 5 * m), vacuum, "Free");
      fShared = new G4LogicalVolume(new G4Box("Shared", 1 * m, 1 * m, 1 * m), vacuum, "Shared");
      auto* limit = new G4UserLimits(200 * mm);  // a vacuum step would otherwise cross the volume at once: the trajectory needs points
      fWithField->SetUserLimits(limit);
      fFree->SetUserLimits(limit);
      new G4PVPlacement(nullptr, {0, 0, -10 * m}, fWithField, "WithField", world, false, 0);
      new G4PVPlacement(nullptr, {0, 0, 10 * m}, fFree, "Free", world, false, 0);
      new G4PVPlacement(nullptr, {8 * m, 8 * m, 0}, fShared, "Shared", fWithField, false, 0);
      new G4PVPlacement(nullptr, {8 * m, 8 * m, 0}, fShared, "Shared", fFree, false, 1);
      return worldPlaced;
    }
    const char* material = gMode == "gb7" ? "G4_Si" : "G4_Fe";
    fTarget = new G4LogicalVolume(new G4Box("Target", 50 * cm, 50 * cm, 50 * cm), nist->FindOrBuildMaterial(material), "Target");
    new G4PVPlacement(nullptr, {}, fTarget, "Target", world, false, 0);
    if (gMode == "gb7") fTarget->SetUserLimits(new G4UserLimits(gMaxStep > 0 ? gMaxStep : DBL_MAX, DBL_MAX, DBL_MAX, 5 * MeV));
    fWorld = world;
    return worldPlaced;
  }
  void ConstructSDandField() override {
    if (gMode == "gb5") {
      auto* multi = new G4MultiSensitiveDetector("multi");
      auto* first = new CountingSD("first", &tFirst);
      auto* second = new CountingSD("second", &tSecond);
      G4SDManager::GetSDMpointer()->AddNewDetector(multi);
      G4SDManager::GetSDMpointer()->AddNewDetector(first);
      G4SDManager::GetSDMpointer()->AddNewDetector(second);
      multi->AddSD(first);
      multi->AddSD(second);
      fTarget->SetSensitiveDetector(multi);
    }
    if (gMode == "gb8") {
      auto* field = new G4UniformMagField(G4ThreeVector(0, 1 * tesla, 0));
      auto* manager = new G4FieldManager(field);
      manager->CreateChordFinder(field);
      fWorld->SetFieldManager(manager, true);
    }
    if (gMode == "gb3") AssignGb3();
  }

 private:
  void AssignGb3() {
    auto* field = new G4UniformMagField(G4ThreeVector(0, 1 * tesla, 0));
    auto* with = new G4FieldManager(field);
    with->CreateChordFinder(field);
    auto* none = new G4FieldManager(static_cast<G4Field*>(nullptr));
    if (gOrder == "forward") {  // the builder: pre-order, explicitly, once per logical; the shared template is set to the IR's value
      fWithField->SetFieldManager(with, false);
      fFree->SetFieldManager(none, false);
      fShared->SetFieldManager(none, false);
    } else if (gOrder == "reverse") {
      fShared->SetFieldManager(none, false);
      fFree->SetFieldManager(none, false);
      fWithField->SetFieldManager(with, false);
    } else if (gOrder == "mother_only") {  // propagation decides: the daughter takes the mother set first, which is what the rule must avoid
      fWithField->SetFieldManager(with, true);
    } else if (gOrder == "none_manager") {
      fFree->SetFieldManager(none, false);
    }
    std::lock_guard<std::mutex> lock(gLock);
    auto& row = gTotals.managers[std::to_string(G4Threading::G4GetThreadId())];
    for (auto* logical : {fWithField, fFree, fShared}) {
      const G4FieldManager* manager = logical->GetFieldManager();
      row[logical->GetName()] = !manager ? "absent" : manager->GetDetectorField() ? "field" : "none";
    }
  }
  G4LogicalVolume *fTarget = nullptr, *fWorld = nullptr, *fWithField = nullptr, *fFree = nullptr, *fShared = nullptr;
};

class Stepping : public G4UserSteppingAction {
 public:
  void UserSteppingAction(const G4Step* step) override {
    g4sim::Accounting::Thread().Step(step);
    const G4Track* track = step->GetTrack();
    const G4StepPoint* post = step->GetPostStepPoint();
    const G4VProcess* process = post->GetProcessDefinedStep();
    std::lock_guard<std::mutex> lock(gLock);
    if (gMode == "gb7") {
      if (process && process->GetProcessName() == "UserSpecialCut") {
        gTotals.killedKinetic += step->GetPreStepPoint()->GetKineticEnergy();
        gTotals.killedDeposit += step->GetTotalEnergyDeposit();
        ++gTotals.kills;
      }
      const int pdg = track->GetDefinition()->GetPDGEncoding();
      if (std::abs(pdg) == 11 && step->GetPreStepPoint()->GetPhysicalVolume()->GetName() == "Target") {
        gTotals.maxElectronStep = std::max(gTotals.maxElectronStep, step->GetStepLength());
        if (gTotals.electronSteps.size() < 200000) gTotals.electronSteps.push_back(step->GetStepLength());
      }
    }
    if (gMode == "gb5" && step->GetPreStepPoint()->GetPhysicalVolume()->GetName() == "Target") ++tAction;
    if (gMode == "gb3") {
      const G4ThreeVector& p = post->GetPosition();
      const std::string volume = step->GetPreStepPoint()->GetPhysicalVolume()->GetName();
      if (volume == "WithField") gTotals.field_path.push_back({p.x(), p.z()});
      if (volume == "Free") gTotals.free_path.push_back({p.x(), p.y(), p.z()});
      tSequence += Hex(step->GetStepLength()) + " ";
    }
  }
};

class Event : public G4UserEventAction {
 public:
  void BeginOfEventAction(const G4Event*) override {
    g4sim::Accounting::Thread().BeginEvent();
    tFirst = tSecond = tAction = 0;
    tSequence.clear();
  }
  void EndOfEventAction(const G4Event* event) override {
    auto& accounting = g4sim::Accounting::Thread();
    accounting.EndEvent(event, 0);
    const g4sim::ConservationRow& row = accounting.Row();
    std::lock_guard<std::mutex> lock(gLock);
    gTotals.accountingErrors += row.accountingErrors;
    gTotals.tracks += row.tracksPhysical + row.tracksEscaped + row.tracksKilled;
    gTotals.looperKinetic += row.killedKineticLooper;
    gTotals.loopers += row.killedKineticLooper > 0;
    const double residual = std::abs(row.Residual());
    gTotals.worstResidual = std::max(gTotals.worstResidual, residual);
    if (row.incident > 0) gTotals.worstRelative = std::max(gTotals.worstRelative, residual / row.incident);
    gTotals.sequences.push_back(tSequence);
    gTotals.stepsAction += tAction;
    gTotals.sdFirst += tFirst;
    gTotals.sdSecond += tSecond;
    gTotals.eventsWithDifference += tFirst != tAction || tSecond != tAction;
  }
};

class Gun : public G4VUserPrimaryGeneratorAction {
 public:
  Gun() : fGun(new G4ParticleGun(1)) {
    auto* table = G4ParticleTable::GetParticleTable();
    const bool gb3 = gMode == "gb3";
    fGun->SetParticleDefinition(gb3 ? G4ChargedGeantino::Definition() : table->FindParticle(gMode == "gb8" || gMode == "gb5" ? "proton" : "e-"));
    fGun->SetParticleEnergy(gb3 ? 1 * GeV : gMode == "gb8" ? 10 * GeV : 200 * MeV);
    fGun->SetParticlePosition(gb3 ? G4ThreeVector(0, 0, gOrder == "none_manager" || gOrder == "no_manager" ? 5.5 * m : -14.9 * m) : G4ThreeVector(0, 0, -60 * cm));
    fGun->SetParticleMomentumDirection({0, 0, 1});
  }
  void GeneratePrimaries(G4Event* event) override { fGun->GeneratePrimaryVertex(event); }

 private:
  G4ParticleGun* fGun;
};

class Actions : public G4VUserActionInitialization {
 public:
  void Build() const override {
    SetUserAction(new Gun());
    SetUserAction(new Stepping());
    SetUserAction(new Event());
  }
  void BuildForMaster() const override {}
};

void Number(std::ostream& out, const char* key, double value, bool comma = true) {
  out << '"' << key << "\": \"" << Hex(value) << '"' << (comma ? ", " : "");
}

void WriteDecayTables(std::ostream& out) {
  auto* table = G4ParticleTable::GetParticleTable();
  g4sim::UnreleasedEnergy unreleased;
  out << "{\"particles\": {";
  bool first = true;
  for (const char* name : {"neutron", "mu-", "mu+", "pi-", "pi+", "pi0", "kaon-", "kaon+", "lambda", "proton", "e-"}) {
    G4ParticleDefinition* particle = table->FindParticle(name);
    out << (first ? "" : ", ") << '"' << name << "\": {";
    Number(out, "unreleased_MeV", unreleased.Of(particle) / MeV);
    Number(out, "mass_MeV", particle->GetPDGMass() / MeV);
    out << "\"channels\": [";
    G4DecayTable* decays = particle->GetDecayTable();
    for (G4int i = 0; decays && i < decays->entries(); ++i) {
      G4VDecayChannel* channel = decays->GetDecayChannel(i);
      out << (i ? ", " : "") << "{\"branch\": \"" << Hex(channel->GetBR()) << "\", \"daughters\": [";
      for (G4int d = 0; d < channel->GetNumberOfDaughters(); ++d) out << (d ? ", " : "") << '"' << channel->GetDaughter(d)->GetParticleName() << '"';
      out << "]}";
    }
    out << "]}";
    first = false;
  }
  G4ParticleDefinition* nucleus = G4IonTable::GetIonTable()->GetIon(27, 60, 0.);
  out << "}, \"nucleus_unreleased_MeV\": \"" << Hex(unreleased.Of(nucleus) / MeV) << "\"}";
}

void WriteProcessCheck(std::ostream& out) {
  long particles = 0, withCut = 0, empty = 0, shortLived = 0;
  std::string lacking;
  auto* iterator = G4ParticleTable::GetParticleTable()->GetIterator();
  iterator->reset();
  while ((*iterator)()) {
    G4ProcessManager* manager = iterator->value()->GetProcessManager();
    if (!manager) continue;
    G4ProcessVector* list = manager->GetProcessList();
    if (iterator->value()->IsShortLived()) {
      ++shortLived;
      continue;
    }
    if (list->size() == 0) {
      ++empty;
      continue;
    }
    ++particles;
    bool found = false;
    for (G4int i = 0; i < list->size(); ++i) found = found || (*list)[i]->GetProcessName() == "UserSpecialCut";
    withCut += found;
    if (!found) lacking += iterator->value()->GetParticleName() + " ";
  }
  out << "\"particles_with_a_process_manager\": " << particles << ", \"with_user_special_cuts\": " << withCut << ", \"short_lived\": " << shortLived
      << ", \"empty_process_list\": " << empty << ", \"lacking\": \"" << lacking << "\", ";
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 3) return 2;
  gMode = argv[1];
  const std::string outPath = argv[2];
  if (gMode == "gb7" && argc > 3) gMaxStep = std::strtod(argv[3], nullptr);
  if (gMode == "gb3" && argc > 3) gOrder = argv[3];
  const bool threaded = gMode == "gb3";
  auto* manager = G4RunManagerFactory::CreateRunManager(threaded ? G4RunManagerType::MTOnly : G4RunManagerType::SerialOnly, threaded ? 2 : 1);
  G4Random::setTheSeed(12345);
  manager->SetUserInitialization(new Detector());
  G4VModularPhysicsList* list = nullptr;
  if (gMode == "gb8em") {
    list = new G4VModularPhysicsList();
    list->RegisterPhysics(new G4EmStandardPhysics_option4());
    list->RegisterPhysics(new G4DecayPhysics());
  } else {
    list = new FTFP_BERT(0);
  }
  if (gMode == "gb7" || gMode == "gb3") list->RegisterPhysics(new G4StepLimiterPhysics());
  if (gMode == "gb8") {
    auto* parameters = G4TransportationParameters::Instance();
    parameters->SetNumberOfTrials(1);
    parameters->SetWarningAndImportantEnergies(1 * GeV, 10 * GeV);
  }
  manager->SetUserInitialization(list);
  manager->SetUserInitialization(new Actions());
  manager->Initialize();
  if (gMode == "gb8") G4TransportationManager::GetTransportationManager()->GetPropagatorInField()->SetMaxLoopCount(2);
  std::ofstream out(outPath);
  if (gMode == "gb9") {
    WriteDecayTables(out);
    delete manager;
    return 0;
  }
  manager->BeamOn(gMode == "gb3" ? 2 : gMode == "gb8" ? 200 : 100);
  out << "{";
  if (gMode == "gb7") WriteProcessCheck(out);
  Number(out, "killed_kinetic_MeV", gTotals.killedKinetic / MeV);
  Number(out, "killed_deposit_MeV", gTotals.killedDeposit / MeV);
  Number(out, "max_electron_step_mm", gTotals.maxElectronStep / mm);
  Number(out, "looper_kinetic_MeV", gTotals.looperKinetic / MeV);
  Number(out, "worst_residual_MeV", gTotals.worstResidual / MeV);
  Number(out, "worst_relative_residual", gTotals.worstRelative);
  std::sort(gTotals.electronSteps.begin(), gTotals.electronSteps.end());
  Number(out, "median_electron_step_mm", gTotals.electronSteps.empty() ? 0. : gTotals.electronSteps[gTotals.electronSteps.size() / 2] / mm);
  out << "\"kills\": " << gTotals.kills << ", \"accounting_errors\": " << gTotals.accountingErrors << ", \"tracks\": " << gTotals.tracks
      << ", \"events_with_a_looper\": " << gTotals.loopers << ", \"steps_action\": " << gTotals.stepsAction << ", \"steps_first_sd\": " << gTotals.sdFirst
      << ", \"steps_second_sd\": " << gTotals.sdSecond << ", \"events_with_a_difference\": " << gTotals.eventsWithDifference << ", \"managers\": {";
  bool firstThread = true;
  for (const auto& [thread, row] : gTotals.managers) {
    out << (firstThread ? "" : ", ") << '"' << thread << "\": {";
    bool firstRow = true;
    for (const auto& [name, value] : row) {
      out << (firstRow ? "" : ", ") << '"' << name << "\": \"" << value << '"';
      firstRow = false;
    }
    out << "}";
    firstThread = false;
  }
  out << "}, \"field_path_mm\": [";
  for (std::size_t i = 0; i < gTotals.field_path.size(); ++i) out << (i ? ", " : "") << "[\"" << Hex(gTotals.field_path[i][0]) << "\", \"" << Hex(gTotals.field_path[i][1]) << "\"]";
  out << "], \"free_path_mm\": [";
  for (std::size_t i = 0; i < gTotals.free_path.size(); ++i)
    out << (i ? ", " : "") << "[\"" << Hex(gTotals.free_path[i][0]) << "\", \"" << Hex(gTotals.free_path[i][1]) << "\", \"" << Hex(gTotals.free_path[i][2]) << "\"]";
  std::sort(gTotals.sequences.begin(), gTotals.sequences.end());
  out << "], \"step_sequence\": \"";
  for (const auto& sequence : gTotals.sequences) out << sequence << "| ";
  out << "\"}\n";
  out.close();
  delete manager;
  return 0;
}
