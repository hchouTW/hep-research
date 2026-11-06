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
#include "G4Run.hh"
#include "G4RunManagerFactory.hh"
#include "G4SDManager.hh"
#include "G4Step.hh"
#include "G4StepLimiterPhysics.hh"
#include "G4Track.hh"
#include "G4UserEventAction.hh"
#include "G4UserRunAction.hh"
#include "G4UserStackingAction.hh"
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
};

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
  out << "}}\n";
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
  explicit Files(Shared& shared) : fShared(shared) {}
  void BeginOfRunAction(const G4Run*) override {
    if (G4Threading::IsMasterThread()) {
      g4sim::WriteBack("g4sim_run", "./probe.json", {});
      if (G4Threading::IsMultithreadedApplication()) return;
    }
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
  }
  void EndOfEventAction(const G4Event* event) override {
    g4sim::Accounting::Thread().EndEvent(event, fShared.firstEvent);
    g4sim::ScorerSums::Thread().EndEvent(fShared.firstEvent + event->GetEventID());
  }

 private:
  Shared& fShared;
};

class Steps : public G4UserSteppingAction {
 public:
  void UserSteppingAction(const G4Step* step) override {
    g4sim::Accounting& accounting = g4sim::Accounting::Thread();
    accounting.Step(step);
    g4sim::ScorerSums::Thread().BoundaryStep(step, accounting.Table());
  }
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
    SetUserAction(new Steps());
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
