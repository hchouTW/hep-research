// NewRun.cc: a run of a new specification in `separated` mode (g4sim plan, Section 8). Per-event seeding, so an event depends only on (logical seed, event)
// whatever the threads. Each worker writes its own files; g4sim_run.py merges them by event. Writes the effective EM settings, which the driver reads back.
#include <array>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include "Accounting.hh"
#include "G4EmParameters.hh"
#include "G4EmSaturation.hh"
#include "G4Event.hh"
#include "G4LossTableManager.hh"
#include "G4ParticleTable.hh"
#include "G4ProcessManager.hh"
#include "G4ProductionCutsTable.hh"
#include "G4Region.hh"
#include "G4RegionStore.hh"
#include "G4VEmFluctuationModel.hh"
#include "G4VEmModel.hh"
#include "G4Run.hh"
#include "G4RunManagerFactory.hh"
#include "G4SDManager.hh"
#include "G4Step.hh"
#include "G4StepLimiterPhysics.hh"
#include "G4Track.hh"
#include "G4UserEventAction.hh"
#include "G4UserRunAction.hh"
#include "G4UserStackingAction.hh"
#include "G4UserTrackingAction.hh"
#include "G4UserSteppingAction.hh"
#include "G4VEnergyLossProcess.hh"
#include "G4VModularPhysicsList.hh"
#include "G4VPhysicsConstructor.hh"
#include "G4VUserActionInitialization.hh"
#include "KillProcess.hh"
#include "MiniJson.hh"
#include "NewBuild.hh"
#include "NewScorers.hh"
#include "NewSource.hh"
#include "PaiConstructor.hh"
#include "SimPhysics.hh"
#include "WriteBack.hh"

namespace {

using g4sim::Decimal;
using minijson::Value;

struct Shared {
  const Value* request = nullptr;
  std::vector<g4sim::ScorerSpec> scorers;
  std::vector<long long> strides;
  std::set<std::string> killedSecondaries;
  long long seed = 0, firstEvent = 0;
  bool hits = false;
  g4sim::TruthRules truth;
  std::vector<g4sim::ReferencePlane> planes;
};

// Section 6.2.9: the model and fluctuation model each ionization process really uses, in each region, at energies from 1 keV to 100 GeV. Read from Geant4, never predicted.
std::string RegionModels() {
  const auto* table = G4ProductionCutsTable::GetProductionCutsTable();
  std::map<std::string, std::size_t> couples;
  for (G4Region* region : *G4RegionStore::GetInstance()) {
    for (std::size_t i = 0; i < table->GetTableSize(); ++i) {
      const auto* couple = table->GetMaterialCutsCouple(static_cast<G4int>(i));
      if (couple->IsUsed() && region->FindCouple(const_cast<G4Material*>(couple->GetMaterial())) == couple) couples[region->GetName()] = i;
    }
  }
  std::ostringstream o;
  o << "{";
  bool firstRegion = true;
  for (const auto& [name, index] : couples) {
    o << (firstRegion ? "" : ", ") << '"' << name << "\": {";
    firstRegion = false;
    bool firstProcess = true;
    std::set<std::string> seen;
    for (G4VEnergyLossProcess* item : G4LossTableManager::Instance()->GetEnergyLossProcessVector()) {
      const std::string process = item->GetProcessName();
      const G4ParticleDefinition* particle = item->Particle();
      if ((process != "eIoni" && process != "hIoni" && process != "muIoni" && process != "ionIoni") || !particle) continue;
      if (!seen.insert(process + "/" + particle->GetParticleName()).second) continue;
      o << (firstProcess ? "" : ", ") << '"' << process << "/" << particle->GetParticleName() << "\": [";
      firstProcess = false;
      bool firstEnergy = true;
      for (double energy : {1e-3, 1e-2, 1e-1, 1., 1e1, 1e2, 1e3, 1e4, 1e5}) {
        std::size_t couple = index;
        G4VEmModel* model = item->SelectModelForMaterial(energy * MeV, couple);
        G4VEmFluctuationModel* fluctuation = model ? model->GetModelOfFluctuations() : nullptr;
        o << (firstEnergy ? "" : ", ") << "[\"" << (model ? model->GetName() : "none") << "\", \"" << (fluctuation ? fluctuation->GetName() : "none") << "\"]";
        firstEnergy = false;
      }
      o << "]";
    }
    o << "}";
  }
  o << "}";
  return o.str();
}

// Section 8.7, 8.8 and 6.2.9: what is really in effect, for the driver to compare with the run card.
void WriteEffective() {
  std::ostringstream report;
  report.precision(12);
  auto* parameters = G4EmParameters::Instance();
  parameters->StreamInfo(report);
  std::ofstream out("effective-em.json");
  out.precision(17);
  out << "{\"msc_range_factor\": " << parameters->MscRangeFactor() << ", \"msc_muhad_range_factor\": " << parameters->MscMuHadRangeFactor() << ", \"step_functions\": [";
  std::string line;
  std::istringstream lines(report.str());
  bool first = true;
  while (std::getline(lines, line)) {
    if (line.find("tep function") == std::string::npos) continue;
    out << (first ? "" : ", ") << '"' << line << '"';
    first = false;
  }
  out << "], \"birks_mm_per_MeV\": {";
  first = true;
  for (const G4Material* material : *G4Material::GetMaterialTable()) {
    out << (first ? "" : ", ") << '"' << material->GetName() << "\": " << material->GetIonisation()->GetBirksConstant() / (mm / MeV);
    first = false;
  }
  out << "}, \"ionisation\": {";
  first = true;
  auto iterator = G4ParticleTable::GetParticleTable()->GetIterator();
  iterator->reset();
  while ((*iterator)()) {
    const G4ParticleDefinition* particle = iterator->value();
    std::string name = "none";
    if (particle->GetProcessManager()) {
      const G4ProcessVector* processes = particle->GetProcessManager()->GetProcessList();
      for (std::size_t i = 0; i < processes->size(); ++i) {
        const std::string candidate = (*processes)[i]->GetProcessName();
        if (candidate == "eIoni" || candidate == "hIoni" || candidate == "muIoni" || candidate == "ionIoni") name = candidate;
      }
    }
    out << (first ? "" : ", ") << '"' << particle->GetParticleName() << "\": \"" << name << '"';
    first = false;
  }
  out << "}, \"models\": " << RegionModels() << "}\n";
}

class KillPhysics : public G4VPhysicsConstructor {
 public:
  explicit KillPhysics(const g4sim::KillLimits& limits) : G4VPhysicsConstructor("g4sim_kill"), fLimits(limits) {}
  void ConstructParticle() override {}
  void ConstructProcess() override {
    auto iterator = GetParticleIterator();
    iterator->reset();
    while ((*iterator)()) {
      G4ProcessManager* manager = iterator->value()->GetProcessManager();
      if (manager) manager->AddDiscreteProcess(new g4sim::KillProcess(fLimits));
    }
  }

 private:
  g4sim::KillLimits fLimits;
};

class Files : public G4UserRunAction {
 public:
  explicit Files(Shared& shared) : fShared(shared) {
    if (fShared.hits) g4sim::HitRecorder::Book();
  }
  void BeginOfRunAction(const G4Run*) override {
    if (fShared.hits) G4AnalysisManager::Instance()->OpenFile("hits.root");
    if (G4Threading::IsMasterThread()) {
      g4sim::WriteBack("g4sim_run", "./probe.json", {});
      if (G4Threading::IsMultithreadedApplication()) return;
    }
    g4sim::HitRecorder::Thread().Configure(fShared.truth, fShared.planes);
    const std::string thread = std::to_string(G4Threading::G4GetThreadId());
    fCells = std::fopen(("cells.thread" + thread + ".csv").c_str(), "w");
    fBoundary = std::fopen(("boundary.thread" + thread + ".csv").c_str(), "w");
    fCrossings = std::fopen(("crossings.thread" + thread + ".csv").c_str(), "w");
    Primaries() = std::fopen(("primaries.thread" + thread + ".csv").c_str(), "w");
    g4sim::Accounting::Thread().SetSeparated();
    g4sim::Accounting::Thread().Open("conservation.thread" + thread + ".csv");
    g4sim::ScorerSums::Thread().Configure(&fShared.scorers, &fShared.strides, fCells, fBoundary, fCrossings);
  }
  void EndOfRunAction(const G4Run*) override {
    if (fShared.hits) {
      G4AnalysisManager::Instance()->Write();
      G4AnalysisManager::Instance()->CloseFile();
    }
    if (G4Threading::IsMasterThread() && G4Threading::IsMultithreadedApplication()) return;
    std::ofstream sagitta("sagitta.thread" + std::to_string(G4Threading::G4GetThreadId()) + ".csv");
    for (std::size_t i = 0; i < fShared.scorers.size(); ++i) sagitta << fShared.scorers[i].name << ',' << g4sim::ScorerSums::Thread().ApportionedSteps(i) << ',' << g4sim::ScorerSums::Thread().LongSteps(i) << '\n';
    for (std::FILE* file : {fCells, fBoundary, fCrossings, Primaries()})
      if (file) std::fclose(file);
    Primaries() = nullptr;
    g4sim::Accounting::Thread().Close();
  }
  static std::FILE*& Primaries() {
    static G4ThreadLocal std::FILE* file = nullptr;
    return file;
  }

 private:
  Shared& fShared;
  std::FILE* fCells = nullptr;
  std::FILE* fBoundary = nullptr;
  std::FILE* fCrossings = nullptr;
};

class EventSums : public G4UserEventAction {
 public:
  explicit EventSums(Shared& shared) : fShared(shared) {}
  void BeginOfEventAction(const G4Event* event) override {
    g4sim::Accounting::Thread().BeginEvent();
    g4sim::ScorerSums::Thread().BeginEvent();
    g4sim::ScorerSums::Thread().SetEvent(fShared.firstEvent + event->GetEventID());
    if (fShared.hits) g4sim::HitRecorder::Thread().BeginEvent(fShared.firstEvent + event->GetEventID());
  }
  void EndOfEventAction(const G4Event* event) override {
    g4sim::Accounting::Thread().EndEvent(event, fShared.firstEvent);
    g4sim::ScorerSums::Thread().EndEvent(fShared.firstEvent + event->GetEventID());
    if (fShared.hits) g4sim::HitRecorder::Thread().EndEvent();
  }

 private:
  Shared& fShared;
};

class Steps : public G4UserSteppingAction {
 public:
  explicit Steps(bool hits) : fHits(hits) {}
  void UserSteppingAction(const G4Step* step) override {
    g4sim::Accounting& accounting = g4sim::Accounting::Thread();
    accounting.Step(step);
    g4sim::ScorerSums::Thread().BoundaryStep(step, accounting.Table());
    if (fHits) g4sim::HitRecorder::Thread().Step(step);
  }

 private:
  bool fHits;
};

class Tracks : public G4UserTrackingAction {
 public:
  void PreUserTrackingAction(const G4Track* track) override { g4sim::HitRecorder::Thread().BeginTrack(track); }
  void PostUserTrackingAction(const G4Track* track) override { g4sim::HitRecorder::Thread().EndTrack(track); }
};

// Class (b): secondaries the kill policy names are never tracked, and are booked here.
class Stacking : public G4UserStackingAction {
 public:
  explicit Stacking(const std::set<std::string>& names) : fNames(names) {}
  G4ClassificationOfNewTrack ClassifyNewTrack(const G4Track* track) override {
    if (track->GetParentID() == 0 || !fNames.count(track->GetDefinition()->GetParticleName())) return fUrgent;
    g4sim::Accounting::Thread().StackingKill(track);
    return fKill;
  }

 private:
  const std::set<std::string>& fNames;
};

class Actions : public G4VUserActionInitialization {
 public:
  explicit Actions(Shared& shared) : fShared(shared) {}
  void BuildForMaster() const override { SetUserAction(new Files(fShared)); }
  void Build() const override {
    auto* files = new Files(fShared);
    SetUserAction(files);
    SetUserAction(new EventSums(fShared));
    SetUserAction(new Steps(fShared.hits));
    if (fShared.hits) SetUserAction(new Tracks());
    if (!fShared.killedSecondaries.empty()) SetUserAction(new Stacking(fShared.killedSecondaries));
    SetUserAction(new Primary(fShared));
  }

 private:
  // The primaries file is opened in BeginOfRunAction, after this generator is built.
  class Primary : public G4VUserPrimaryGeneratorAction {
   public:
    explicit Primary(Shared& shared) : fShared(shared) {}
    void GeneratePrimaries(G4Event* event) override {
      if (!fSource) fSource = new g4sim::NewSource(fShared.request->at("source", "request"), fShared.seed, fShared.firstEvent, Files::Primaries());
      fSource->GeneratePrimaries(event);
    }

   private:
    Shared& fShared;
    g4sim::NewSource* fSource = nullptr;
  };
  Shared& fShared;
};

void SetEmParameters(const Value& physics) {
  if (!physics.has("em_parameters")) return;
  const Value& block = physics.obj.at("em_parameters");
  auto* parameters = G4EmParameters::Instance();
  const auto pair = [&](const char* key, void (G4EmParameters::*set)(G4double, G4double)) {
    if (block.has(key)) (parameters->*set)(Decimal(block.obj.at(key).arr[0]), Decimal(block.obj.at(key).arr[1]) * mm);
  };
  pair("step_function_electron", &G4EmParameters::SetStepFunction);
  pair("step_function_muon_hadron", &G4EmParameters::SetStepFunctionMuHad);
  pair("step_function_light_ion", &G4EmParameters::SetStepFunctionLightIons);
  pair("step_function_ion", &G4EmParameters::SetStepFunctionIons);
  if (block.has("msc_range_factor")) parameters->SetMscRangeFactor(Decimal(block.obj.at("msc_range_factor")));
  if (block.has("msc_muhad_range_factor")) parameters->SetMscMuHadRangeFactor(Decimal(block.obj.at("msc_muhad_range_factor")));
}

}  // namespace

int NewRun(const Value& ir, const Value& card, const Value& request) {
  const Value& physics = card.at("physics", "run card");
  const Value& run = card.at("run", "run card");
  Shared shared;
  shared.request = &request;
  shared.scorers = g4sim::ReadScorers(request);
  for (const auto& stride : ir.at("physical", "ir").at("volume_id", "physical").at("strides", "volume_id").array("strides")) shared.strides.push_back(static_cast<long long>(stride.num));
  shared.seed = static_cast<long long>(run.at("logical_run_seed", "run").num);
  shared.firstEvent = run.has("first_event") ? static_cast<long long>(run.obj.at("first_event").num) : 0;
  const int threads = run.has("threads") ? static_cast<int>(run.obj.at("threads").num) : 1;
  if (request.has("truth")) {
    const Value& truth = request.obj.at("truth");
    shared.hits = true;
    shared.truth.decayProducts = truth.at("decay_products", "truth").b;
    shared.truth.energyThreshold = truth.at("energy_above_MeV", "truth").num;
    shared.truth.energyRegion = truth.at("energy_region", "truth").str;
    shared.truth.all = truth.at("all", "truth").b;
    shared.truth.timeBinNs = truth.at("time_bin_ns", "truth").num;
    for (const auto& plane : truth.at("planes_z_mm", "truth").array("planes_z_mm")) shared.planes.push_back({plane.num});
  }
  g4sim::KillLimits limits;
  if (card.has("kill_policy")) {
    const Value& policy = card.obj.at("kill_policy");
    if (policy.has("min_kinetic_energy_MeV")) limits.minKinetic = Decimal(policy.obj.at("min_kinetic_energy_MeV")) * MeV;
    if (policy.has("time_cut_ns")) limits.timeCut = Decimal(policy.obj.at("time_cut_ns")) * ns;
    if (policy.has("kill_secondaries"))
      for (const auto& name : policy.obj.at("kill_secondaries").array("kill_secondaries")) shared.killedSecondaries.insert(name.str);
  }
  auto* manager = G4RunManagerFactory::CreateRunManager(run.at("mode", "run").str == "serial" ? G4RunManagerType::SerialOnly : G4RunManagerType::MTOnly, threads);
  const Value* userLimits = physics.has("user_limits") ? &physics.obj.at("user_limits") : nullptr;
  const auto attach = [&shared](const std::map<std::string, G4LogicalVolume*>& logicals) {
    std::set<std::string> selected;
    for (const auto& scorer : shared.scorers)
      if (!scorer.Boundary()) selected.insert(scorer.templates.begin(), scorer.templates.end());
    for (const std::string& name : selected) {
      auto* dispatcher = new g4sim::Dispatcher("g4sim_sd_" + name);
      G4SDManager::GetSDMpointer()->AddNewDetector(dispatcher);
      logicals.at(name)->SetSensitiveDetector(dispatcher);
    }
  };
  manager->SetUserInitialization(new g4sim::NewDetector(ir.at("physical", "ir"), physics.at("cuts_mm", "physics"), attach, userLimits));
  std::string error;
  const auto text = [&](const char* key) { return physics.has(key) ? physics.obj.at(key).str : std::string(); };
  const bool tooEarly = std::getenv("G4SIM_EM_TOO_EARLY") != nullptr;  // the negative test of Section 15.1: the EM constructor resets these (GB14)
  if (tooEarly) SetEmParameters(physics);
  G4VModularPhysicsList* list = g4sim::BuildPhysicsList(text("reference_list"), text("em_constructor"), true, userLimits != nullptr, Decimal(physics.at("cuts_mm", "physics").at("default", "cuts")), error);
  if (!list) {
    std::cerr << error << std::endl;
    return 2;
  }
  if (!tooEarly) SetEmParameters(physics);  // after the EM constructor and before initialization (GB14)
  if (physics.has("pai")) {
    std::vector<g4sim::PaiRequest> requests;
    for (const auto& item : physics.obj.at("pai").array("pai")) requests.push_back({item.at("region", "pai").str, item.at("particle", "pai").str, item.at("model", "pai").str});
    if (!requests.empty()) list->RegisterPhysics(new g4sim::PaiConstructor(requests));
  }
  if (limits.Any()) list->RegisterPhysics(new KillPhysics(limits));
  if (request.has("birks_active")) G4EmParameters::Instance()->SetBirksActive(true);
  manager->SetUserInitialization(list);
  manager->SetUserInitialization(new Actions(shared));
  std::printf("G4SIM_START %.3f\n", g4sim::Now());
  manager->Initialize();
  std::printf("G4SIM_INITIALIZED %.3f\n", g4sim::Now());
  std::fflush(stdout);
  // G4EmSaturation sets its particles and per-material terms here, not at SetBirksActive, which ran before the materials existed; built-in constants appear now too (GB13)
  if (request.has("birks_active")) G4LossTableManager::Instance()->EmSaturation()->InitialiseG4Saturation();
  WriteEffective();
  if (static_cast<G4int>(run.at("events", "run").num) == 0) {  // the driver's preflight: settings only
    delete manager;
    return 0;
  }
  manager->BeamOn(static_cast<G4int>(run.at("events", "run").num));
  std::printf("G4SIM_DONE %.3f\n", g4sim::Now());
  delete manager;
  return 0;
}
