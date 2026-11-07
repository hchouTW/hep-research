// Prototypes GB11 to GB14 of the g4sim plan (Section 23): this program writes what Geant4 did; judge.py judges.
//   s3_em pai LIST OUT.json [REGION:PARTICLE:MODEL ...]   the models and fluctuation models of each ionization process in each region
//   s3_em pai-late LIST OUT.json [REGION:PARTICLE:MODEL ...]   the same, with the activator run again after the EM constructor
//   s3_em pai-region LIST OUT.json [REGION:PARTICLE:MODEL ...] the same, with models added for the region only
//   s3_em birks LIST OUT.json MATERIAL                    visible energy step by step: g4sim's formula against G4EmSaturation
//   s3_em steps LIST OUT.json none|before|after           step functions and range factors read back; `before` sets them before the EM constructor
// Serial run manager: the models looked at are the ones the master thread owns. Every double is written with %a.
//
// OwnBirksTerms and OwnVisible follow G4EmSaturation.cc, and RegionPai is adapted from G4EmModelActivator::ActivatePAI, of Geant4 11.4.3. Copyright Holders of the Geant4
// Collaboration; Geant4 Software License, Version 1.0, in adapters/geant4/assets/GEANT4-LICENSE.txt. This product includes software developed by Members of the Geant4 Collaboration ( http://cern.ch/geant4 ).
#include "G4Box.hh"
#include "G4BraggModel.hh"
#include "G4Electron.hh"
#include "G4EmModelActivator.hh"
#include "G4EmParameters.hh"
#include "G4EmSaturation.hh"
#include "G4GenericIon.hh"
#include "G4IonFluctuations.hh"
#include "G4IonTable.hh"
#include "G4LindhardSorensenIonModel.hh"
#include "G4LogicalVolume.hh"
#include "G4LossTableManager.hh"
#include "G4Material.hh"
#include "G4MollerBhabhaModel.hh"
#include "G4NistManager.hh"
#include "G4PAIModel.hh"
#include "G4PAIPhotModel.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4PhysListFactory.hh"
#include "G4ProcessManager.hh"
#include "G4ProductionCuts.hh"
#include "G4ProductionCutsTable.hh"
#include "G4Proton.hh"
#include "G4Region.hh"
#include "G4RegionStore.hh"
#include "G4RunManagerFactory.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4Track.hh"
#include "G4UniversalFluctuation.hh"
#include "G4UserSteppingAction.hh"
#include "G4VEmFluctuationModel.hh"
#include "G4VEmModel.hh"
#include "G4EmProcessSubType.hh"
#include "G4VEnergyLossProcess.hh"
#include "G4VMultipleScattering.hh"
#include "G4VPhysicsConstructor.hh"
#include "G4VUserActionInitialization.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace {
std::string Hex(double value) {
  char text[64];
  std::snprintf(text, sizeof text, "%a", value);
  return std::string("\"") + text + "\"";
}

class Blocks : public G4VUserDetectorConstruction {
 public:
  explicit Blocks(const std::string& material) : material_(material) {}
  G4VPhysicalVolume* Construct() override {
    auto* nist = G4NistManager::Instance();
    auto* world = new G4LogicalVolume(new G4Box("World", 2 * m, 2 * m, 2 * m), nist->FindOrBuildMaterial("G4_Galactic"), "World");
    auto* placed = new G4PVPlacement(nullptr, {}, world, "World", nullptr, false, 0);
    int at = 0;
    for (const char* name : {"tracker", "calorimeter"}) {
      auto* block = new G4LogicalVolume(new G4Box(name, 50 * cm, 50 * cm, 20 * cm), nist->FindOrBuildMaterial(material_), name);
      new G4PVPlacement(nullptr, G4ThreeVector(0, 0, (at++ ? 30 : -30) * cm), block, name, world, false, 0);
      auto* region = new G4Region(name);
      region->AddRootLogicalVolume(block);
      region->SetProductionCuts(new G4ProductionCuts());  // a region of its own couple: without it the region shares the default couple, and PAI has nothing to act on
    }
    return placed;
  }

 private:
  std::string material_;
};

class Beam : public G4VUserPrimaryGeneratorAction {
 public:
  Beam(const std::string& particle, double energy) : gun_(1) {
    gun_.SetParticleDefinition(G4ParticleTable::GetParticleTable()->FindParticle(particle));
    gun_.SetParticleEnergy(energy);
    gun_.SetParticlePosition(G4ThreeVector(0, 0, -60 * cm));
    gun_.SetParticleMomentumDirection(G4ThreeVector(0, 0, 1));
  }
  void GeneratePrimaries(G4Event* event) override { gun_.GeneratePrimaryVertex(event); }

 private:
  G4ParticleGun gun_;
};

// massFactor and effCharge computed by g4sim itself, for every material (Section 8.8).
struct BirksTerms {
  double massFactor, effCharge;
};

BirksTerms OwnBirksTerms(const G4Material* material) {
  double ratio = 0., chargeSquared = 0., norm = 0.;
  const auto* elements = material->GetElementVector();
  const double* density = material->GetVecNbOfAtomsPerVolume();
  for (std::size_t i = 0; i < material->GetNumberOfElements(); ++i) {
    const int z = (*elements)[i]->GetZasInt();
    ratio += density[i] / G4NistManager::Instance()->GetAtomicMassAmu(z);
    chargeSquared += (z * z) * density[i];
    norm += density[i];
  }
  if (norm > 0.) norm = 1. / norm;
  return {ratio * (CLHEP::proton_mass_c2 * norm), chargeSquared * norm};
}

struct Comparison {
  long steps = 0;
  double largest = 0., control = 0.;
};

// What Section 8.8 says for one step; effCharge is a parameter so the negative control can leave it at 1.
double OwnVisible(const G4ParticleDefinition* particle, const G4MaterialCutsCouple* couple, double length, double deposit, double nonIonizing, double massFactor, double effCharge, std::string* kind) {
  const double birks = couple->GetMaterial()->GetIonisation()->GetBirksConstant();
  auto* manager = G4LossTableManager::Instance();
  auto nonIonizingPart = [&](double part) {
    const double range = manager->GetRange(G4Proton::Proton(), part * massFactor, couple) / effCharge;
    return part / (1. + birks * (part / range));
  };
  if (length <= 0.) {
    *kind = "zero_length";
    return deposit;
  }
  if (particle->GetPDGEncoding() == 22) {
    *kind = "photon";
    return deposit / (1. + birks * (deposit / manager->GetRange(G4Electron::Electron(), deposit, couple)));
  }
  const double lost = std::max(nonIonizing, 0.), ionizing = deposit - lost;
  if (particle->GetPDGCharge() == 0. || ionizing < 0.) {
    *kind = "neutral";
    return nonIonizingPart(deposit);
  }
  *kind = lost > 0. ? "charged_with_nonionizing" : "charged";
  return ionizing / (1. + birks * (ionizing / length)) + (lost > 0. ? nonIonizingPart(lost) : 0.);
}

class BirksCheck : public G4UserSteppingAction {
 public:
  void UserSteppingAction(const G4Step* step) override {
    const double deposit = step->GetTotalEnergyDeposit();
    if (deposit <= 0.) return;
    const auto* couple = step->GetPreStepPoint()->GetMaterialCutsCouple();
    const auto* particle = step->GetTrack()->GetParticleDefinition();
    Compare(particle, couple, step->GetStepLength(), deposit, step->GetNonIonizingEnergyDeposit(), G4LossTableManager::Instance()->EmSaturation()->VisibleEnergyDepositionAtAStep(step), "");
  }
  void Compare(const G4ParticleDefinition* particle, const G4MaterialCutsCouple* couple, double length, double deposit, double nonIonizing, double geant4, const std::string& prefix) {
    const BirksTerms terms = OwnBirksTerms(couple->GetMaterial());
    std::string kind;
    const double own = OwnVisible(particle, couple, length, deposit, nonIonizing, terms.massFactor, terms.effCharge, &kind);
    const double control = OwnVisible(particle, couple, length, deposit, nonIonizing, terms.massFactor, 1., &kind);
    Comparison& row = rows[prefix + particle->GetParticleName() + "/" + kind];
    ++row.steps;
    row.largest = std::max(row.largest, std::abs(own / geant4 - 1.));
    row.control = std::max(row.control, std::abs(control / geant4 - 1.));
  }
  std::map<std::string, Comparison> rows;
};

class Actions : public G4VUserActionInitialization {
 public:
  Actions(std::string particle, double energy, G4UserSteppingAction* stepping) : particle_(std::move(particle)), energy_(energy), stepping_(stepping) {}
  void Build() const override {
    SetUserAction(new Beam(particle_, energy_));
    if (stepping_) SetUserAction(stepping_);
  }

 private:
  std::string particle_;
  double energy_;
  G4UserSteppingAction* stepping_;
};

G4VModularPhysicsList* List(const std::string& name) {
  G4PhysListFactory factory;
  factory.SetVerbose(0);
  return factory.GetReferencePhysList(name);
}

// Falsification evidence for GB11: ActivatePAI, called from the EM constructor's ConstructProcess, skips every process, because
// IsIonisationProcess() only becomes true in PreparePhysicsTable. This constructor, registered after the EM one, sets the flag and runs the activator again.
class LatePai : public G4VPhysicsConstructor {
 public:
  LatePai() : G4VPhysicsConstructor("g4sim_late_pai") {}
  void ConstructParticle() override {}
  void ConstructProcess() override {
    for (G4VEnergyLossProcess* item : G4LossTableManager::Instance()->GetEnergyLossProcessVector())
      if (item->GetProcessSubType() == fIonisation) item->SetIonisation(true);
    G4EmModelActivator activator("g4sim_late_pai");
  }
};

// The other candidate for the addendum: the region's models only, as ActivatePAI adds them, with the world's default models left alone.
class RegionPai : public G4VPhysicsConstructor {
 public:
  RegionPai() : G4VPhysicsConstructor("g4sim_region_pai") {}
  void ConstructParticle() override {}
  void ConstructProcess() override {
    const auto* parameters = G4EmParameters::Instance();
    const auto regions = parameters->RegionsPAI();
    const auto particles = parameters->ParticlesPAI();
    const auto types = parameters->TypesPAI();
    for (std::size_t i = 0; i < regions.size(); ++i) {
      const G4Region* region = G4RegionStore::GetInstance()->GetRegion(regions[i], false);
      const std::string wanted = particles[i] == "e-" || particles[i] == "e+" ? "eIoni" : particles[i] == "mu-" || particles[i] == "mu+" ? "muIoni" : particles[i] == "GenericIon" ? "ionIoni" : "hIoni";
      const G4ParticleDefinition* particle = particles[i] == "all" ? nullptr : G4ParticleTable::GetParticleTable()->FindParticle(particles[i]);
      for (G4VEnergyLossProcess* item : G4LossTableManager::Instance()->GetEnergyLossProcessVector()) {
        const std::string name = item->GetProcessName();
        if (name != "eIoni" && name != "hIoni" && name != "muIoni" && name != "ionIoni") continue;
        if (particle && name != wanted) continue;
        const double lowest = name == "eIoni" ? 110 * eV : name == "muIoni" ? 5 * keV : 50 * keV;
        G4VEmModel* below = name == "eIoni" ? static_cast<G4VEmModel*>(new G4MollerBhabhaModel()) : name == "ionIoni" ? static_cast<G4VEmModel*>(new G4LindhardSorensenIonModel()) : new G4BraggModel();
        G4VEmFluctuationModel* belowFluctuation = name == "ionIoni" ? static_cast<G4VEmFluctuationModel*>(new G4IonFluctuations()) : new G4UniversalFluctuation();
        below->SetHighEnergyLimit(lowest);
        item->AddEmModel(-1, below, belowFluctuation, region);
        G4VEmModel* model;
        G4VEmFluctuationModel* fluctuation;
        if (types[i] == "PAIphoton") {
          auto* built = new G4PAIPhotModel(particle, "PAIPhotModel");
          model = built;
          fluctuation = built;
        } else {
          auto* built = new G4PAIModel(particle, "PAIModel");
          model = built;
          fluctuation = built;
        }
        model->SetLowEnergyLimit(lowest);
        item->AddEmModel(-1, model, fluctuation, region);
      }
    }
  }
};

std::string Models(const G4VEnergyLossProcess* item, std::size_t coupleIndex) {
  std::ostringstream o;
  o << "[";
  bool first = true;
  for (double energy : {1e-3, 1e-2, 1e-1, 1., 1e1, 1e2, 1e3, 1e4, 1e5}) {
    std::size_t index = coupleIndex;
    G4VEmModel* model = item->SelectModelForMaterial(energy * MeV, index);
    G4VEmFluctuationModel* fluctuation = model ? model->GetModelOfFluctuations() : nullptr;
    o << (first ? "" : ", ") << "[" << energy << ", \"" << (model ? model->GetName() : "none") << "\", \"" << (fluctuation ? fluctuation->GetName() : "none") << "\"]";
    first = false;
  }
  o << "]";
  return o.str();
}

int RunPai(const std::string& listName, const char* out, const std::vector<std::string>& requests, const std::string& mode) {
  auto* manager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::SerialOnly);
  manager->SetUserInitialization(new Blocks("G4_Si"));
  auto* list = List(listName);
  manager->SetUserInitialization(list);
  for (const std::string& text : requests) {
    const auto first = text.find(':'), second = text.find(':', first + 1);
    G4EmParameters::Instance()->AddPAIModel(text.substr(first + 1, second - first - 1), text.substr(0, first), text.substr(second + 1));
  }
  if (mode == "pai-late") list->RegisterPhysics(new LatePai());
  if (mode == "pai-region") list->RegisterPhysics(new RegionPai());
  manager->SetUserInitialization(new Actions("e-", 1 * GeV, nullptr));
  manager->Initialize();
  manager->BeamOn(1);
  std::map<std::string, std::size_t> couples;
  const auto* table = G4ProductionCutsTable::GetProductionCutsTable();
  for (const char* name : {"DefaultRegionForTheWorld", "tracker", "calorimeter"}) {
    auto* region = G4RegionStore::GetInstance()->GetRegion(name, false);
    for (std::size_t i = 0; i < table->GetTableSize(); ++i) {
      const auto* couple = table->GetMaterialCutsCouple(static_cast<G4int>(i));
      if (couple->IsUsed() && region->FindCouple(const_cast<G4Material*>(couple->GetMaterial())) == couple) couples[name] = i;
    }
  }
  std::ofstream file(out);
  file << "{\"list\": \"" << listName << "\", \"particles\": {";
  bool firstParticle = true;
  auto iterator = G4ParticleTable::GetParticleTable()->GetIterator();
  iterator->reset();
  while ((*iterator)()) {
    const auto* particle = iterator->value();
    const auto* processes = particle->GetProcessManager() ? particle->GetProcessManager()->GetProcessList() : nullptr;
    if (!processes) continue;
    for (std::size_t i = 0; i < processes->size(); ++i) {
      const auto* loss = dynamic_cast<const G4VEnergyLossProcess*>((*processes)[i]);
      if (!loss || (loss->GetProcessName() != "eIoni" && loss->GetProcessName() != "hIoni" && loss->GetProcessName() != "muIoni" && loss->GetProcessName() != "ionIoni")) continue;
      file << (firstParticle ? "" : ", ") << "\"" << particle->GetParticleName() << "\": {\"name\": \"" << loss->GetProcessName() << "\", \"model_count\": " << loss->NumberOfModels() << ", \"regions\": {";
      firstParticle = false;
      bool firstRegion = true;
      for (const auto& [region, index] : couples) {
        file << (firstRegion ? "" : ", ") << "\"" << region << "\": " << Models(loss, index);
        firstRegion = false;
      }
      file << "}}";
    }
  }
  file << "}}\n";
  delete manager;
  return 0;
}

int RunBirks(const std::string& listName, const char* out, const std::string& materialName) {
  auto* manager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::SerialOnly);
  manager->SetUserInitialization(new Blocks(materialName));
  manager->SetUserInitialization(List(listName));
  const double before = G4NistManager::Instance()->FindOrBuildMaterial(materialName)->GetIonisation()->GetBirksConstant();
  G4EmParameters::Instance()->SetBirksActive(true);
  auto* check = new BirksCheck();
  manager->SetUserInitialization(new Actions("e-", 10 * MeV, check));
  manager->Initialize();
  const double after = G4NistManager::Instance()->FindOrBuildMaterial(materialName)->GetIonisation()->GetBirksConstant();
  for (const auto& [particle, energy] : std::vector<std::pair<std::string, double>>{{"e-", 50 * MeV}, {"mu-", 1 * GeV}, {"proton", 300 * MeV}, {"alpha", 400 * MeV}, {"neutron", 2 * MeV}, {"neutron", 200 * MeV}, {"proton", 2 * MeV}, {"alpha", 8 * MeV}, {"gamma", 30 * MeV}}) {
    manager->SetUserAction(new Beam(particle, energy));
    manager->BeamOn(300);
  }
  // Neutral hadrons leave no deposit in these runs (their recoils are tracked), so that branch and step length 0 are put to G4EmSaturation directly.
  const auto* couple = G4ProductionCutsTable::GetProductionCutsTable()->GetMaterialCutsCouple(G4NistManager::Instance()->FindOrBuildMaterial(materialName), G4RegionStore::GetInstance()->GetRegion("tracker")->GetProductionCuts());
  const auto* neutron = G4ParticleTable::GetParticleTable()->FindParticle("neutron");
  auto* saturation = G4LossTableManager::Instance()->EmSaturation();
  for (int i = 1; i <= 1000; ++i) {
    const double deposit = 1e-4 * std::pow(1.02, i) * MeV;
    check->Compare(neutron, couple, 0.37 * mm, deposit, 0., saturation->VisibleEnergyDeposition(neutron, couple, 0.37 * mm, deposit, 0.), "direct_");
    check->Compare(G4Electron::Electron(), couple, 0., deposit, 0., saturation->VisibleEnergyDeposition(G4Electron::Electron(), couple, 0., deposit, 0.), "direct_");
  }
  std::ofstream file(out);
  file << "{\"material\": \"" << materialName << "\", \"birks_before\": " << Hex(before) << ", \"birks_after\": " << Hex(after) << ", \"rows\": {";
  bool first = true;
  for (const auto& [key, row] : check->rows) {
    file << (first ? "" : ", ") << "\"" << key << "\": {\"steps\": " << row.steps << ", \"largest\": " << Hex(row.largest) << ", \"control\": " << Hex(row.control) << "}";
    first = false;
  }
  file << "}}\n";
  delete manager;
  return 0;
}

void SetHalved() {
  auto* parameters = G4EmParameters::Instance();
  parameters->SetStepFunction(0.1, 0.5 * mm);
  parameters->SetStepFunctionMuHad(0.1, 0.05 * mm);
  parameters->SetStepFunctionLightIons(0.1, 0.05 * mm);
  parameters->SetStepFunctionIons(0.1, 0.05 * mm);
  parameters->SetMscRangeFactor(0.02);
  parameters->SetMscMuHadRangeFactor(0.1);
}

int RunSteps(const std::string& listName, const char* out, const std::string& when) {
  auto* manager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::SerialOnly);
  manager->SetUserInitialization(new Blocks("G4_Si"));
  if (when == "before") SetHalved();
  auto* list = List(listName);
  if (when == "after") SetHalved();
  manager->SetUserInitialization(list);
  manager->SetUserInitialization(new Actions("e-", 1 * GeV, nullptr));
  manager->Initialize();
  manager->BeamOn(1);
  // G4EmParameters has no getter for the step functions, and the processes keep them private: StreamInfo is what Geant4 reports as in effect.
  std::ostringstream report;
  report.precision(12);
  G4EmParameters::Instance()->StreamInfo(report);
  std::ofstream file(out);
  file << "{\"when\": \"" << when << "\", \"msc_range_factor\": " << Hex(G4EmParameters::Instance()->MscRangeFactor()) << ", \"msc_muhad_range_factor\": " << Hex(G4EmParameters::Instance()->MscMuHadRangeFactor()) << ", \"report\": [";
  std::string line;
  std::istringstream lines(report.str());
  bool first = true;
  while (std::getline(lines, line)) {
    if (line.find("tep function") == std::string::npos) continue;
    file << (first ? "" : ", ") << "\"" << line << "\"";
    first = false;
  }
  file << "]}\n";
  delete manager;
  return 0;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 4) {
    std::puts("{\"status\": \"rejected\", \"message\": \"usage: s3_em pai|birks|steps LIST OUT.json ...\"}");
    return 2;
  }
  const std::string mode = argv[1], list = argv[2];
  if (mode == "pai" || mode == "pai-late" || mode == "pai-region") return RunPai(list, argv[3], std::vector<std::string>(argv + 4, argv + argc), mode);
  if (mode == "birks" && argc == 5) return RunBirks(list, argv[3], argv[4]);
  if (mode == "steps" && argc == 5) return RunSteps(list, argv[3], argv[4]);
  std::puts("{\"status\": \"rejected\", \"message\": \"unknown mode\"}");
  return 2;
}
