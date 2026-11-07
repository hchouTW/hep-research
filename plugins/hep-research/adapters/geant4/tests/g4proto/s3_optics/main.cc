// Prototypes GB15, GB16 and GB17 of the g4sim plan (Section 23): small standalone Geant4 programs that record what Geant4 does; this program judges nothing.
//
// Usage: s3_optics gb15 PREFIX key=value...   per-step records in PREFIX.steps, totals in PREFIX.json
//        s3_optics gb16 FILE.json key=value...
//        s3_optics gb17 FILE.json key=value...
// Every floating-point value in a JSON file is a C hex float, so nothing is rounded on the way out.
// Geant4 11.4.3 only: G4Scintillation::GetNumPhotons, G4OpticalParameters::SetActiveVolume and the G4XTR*RadModel classes are read as they are in that version.
#include "G4Box.hh"
#include "G4Cerenkov.hh"
#include "G4DecayPhysics.hh"
#include "G4EmSaturation.hh"
#include "G4EmStandardPhysics.hh"
#include "G4Event.hh"
#include "G4GammaXTRadiator.hh"
#include "G4GaussXTRadiator.hh"
#include "G4LogicalVolume.hh"
#include "G4LossTableManager.hh"
#include "G4MTRunManager.hh"
#include "G4Material.hh"
#include "G4MaterialPropertiesTable.hh"
#include "G4NistManager.hh"
#include "G4OpticalParameters.hh"
#include "G4OpticalPhoton.hh"
#include "G4OpticalPhysics.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4ProcessManager.hh"
#include "G4RegularXTRadiator.hh"
#include "G4RunManager.hh"
#include "G4Scintillation.hh"
#include "G4ScintillationTrackInformation.hh"
#include "G4Step.hh"
#include "G4StrawTubeXTRadiator.hh"
#include "G4SystemOfUnits.hh"
#include "G4TransparentRegXTRadiator.hh"
#include "G4UserEventAction.hh"
#include "G4UserStackingAction.hh"
#include "G4UserSteppingAction.hh"
#include "G4VDiscreteProcess.hh"
#include "G4VModularPhysicsList.hh"
#include "G4VPhysicsConstructor.hh"
#include "G4VUserActionInitialization.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4VXTRenergyLoss.hh"
#include "G4XTRGammaRadModel.hh"
#include "G4XTRGaussRadModel.hh"
#include "G4XTRRegularRadModel.hh"
#include "G4XTRTransparentRegRadModel.hh"
#include "Randomize.hh"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace {

// --- Arguments and JSON ---------------------------------------------------------------------------------------------

class Options {
 public:
  Options(int argc, char** argv, int first) {
    for (int i = first; i < argc; ++i) {
      const std::string text = argv[i];
      const auto mark = text.find('=');
      if (mark == std::string::npos) Fail("an option must be key=value: " + text);
      values_[text.substr(0, mark)] = text.substr(mark + 1);
    }
  }
  double Number(const std::string& key, double fallback) {
    used_.insert(key);
    const auto found = values_.find(key);
    return found == values_.end() ? fallback : std::strtod(found->second.c_str(), nullptr);
  }
  long Count(const std::string& key, long fallback) { return std::lround(Number(key, static_cast<double>(fallback))); }
  std::string Text(const std::string& key, const std::string& fallback) {
    used_.insert(key);
    const auto found = values_.find(key);
    return found == values_.end() ? fallback : found->second;
  }
  void RefuseUnknown() const {
    for (const auto& item : values_)
      if (!used_.count(item.first)) Fail("unknown option: " + item.first);
  }
  [[noreturn]] static void Fail(const std::string& message) {
    std::printf("{\"status\": \"rejected\", \"message\": \"%s\"}\n", message.c_str());
    std::exit(2);
  }

 private:
  std::map<std::string, std::string> values_;
  std::set<std::string> used_;
};

std::string Hex(double value) {
  char text[64];
  std::snprintf(text, sizeof text, "\"%a\"", value);
  return text;
}

std::string Quoted(const std::string& text) { return "\"" + text + "\""; }

template <typename Value>
std::string Object(const std::map<std::string, Value>& items) {
  std::ostringstream out;
  out << '{';
  bool first = true;
  for (const auto& item : items) {
    out << (first ? "" : ", ") << Quoted(item.first) << ": " << item.second;
    first = false;
  }
  out << '}';
  return out.str();
}

void WriteText(const std::string& path, const std::string& text) {
  std::FILE* file = std::fopen(path.c_str(), "w");
  if (!file) Options::Fail("cannot write " + path);
  std::fputs(text.c_str(), file);
  std::fclose(file);
}

double CpuSeconds() { return static_cast<double>(std::clock()) / CLOCKS_PER_SEC; }

// --- Shared pieces --------------------------------------------------------------------------------------------------

// Polyvinyltoluene, C9H10 at 1.032 g/cm3: the textbook values, which Geant4's TestEm3 example and others also use.
G4Material* Plastic(const std::string& name, double birksMmPerMeV) {
  auto* nist = G4NistManager::Instance();
  auto* plastic = new G4Material(name, 1.032 * g / cm3, 2);
  plastic->AddElement(nist->FindOrBuildElement("C"), 9);
  plastic->AddElement(nist->FindOrBuildElement("H"), 10);
  plastic->GetIonisation()->SetBirksConstant(birksMmPerMeV * mm / MeV);
  return plastic;
}

struct Emission {
  double yieldPerMeV = 1000.;
  double resolutionScale = 1.;
  std::vector<double> componentYields{1.};
};

// A complete scintillation table; RINDEX and ABSLENGTH make it trackable as well.
G4MaterialPropertiesTable* ScintillationTable(const Emission& emission, double absorptionMm) {
  std::vector<G4double> energies{2.0 * eV, 3.5 * eV}, flat{1., 1.}, index{1.58, 1.58}, absorption{absorptionMm * mm, absorptionMm * mm};
  auto* table = new G4MaterialPropertiesTable();
  table->AddProperty("RINDEX", energies, index);
  table->AddProperty("ABSLENGTH", energies, absorption);
  table->AddConstProperty("SCINTILLATIONYIELD", emission.yieldPerMeV / MeV);
  table->AddConstProperty("RESOLUTIONSCALE", emission.resolutionScale);
  for (std::size_t i = 0; i < emission.componentYields.size(); ++i) {
    const std::string number = std::to_string(i + 1);
    table->AddProperty("SCINTILLATIONCOMPONENT" + number, energies, flat);
    table->AddConstProperty("SCINTILLATIONTIMECONSTANT" + number, (i + 1) * 10. * ns);
    if (emission.componentYields.size() > 1) table->AddConstProperty("SCINTILLATIONYIELD" + number, emission.componentYields[i]);
  }
  return table;
}

G4LogicalVolume* Box(const std::string& name, double halfX, double halfY, double halfZ, G4Material* material) {
  return new G4LogicalVolume(new G4Box(name, halfX, halfY, halfZ), material, name);
}

void Place(G4LogicalVolume* volume, G4LogicalVolume* mother, double x, double z) {
  new G4PVPlacement(nullptr, G4ThreeVector(x, 0., z), volume, volume->GetName(), mother, false, 0, false);
}

class Gun : public G4VUserPrimaryGeneratorAction {
 public:
  Gun(const std::string& particle, double lowMeV, double highMeV, double startZ) : gun_(1), low_(lowMeV), high_(highMeV) {
    auto* definition = G4ParticleTable::GetParticleTable()->FindParticle(particle);
    if (!definition) Options::Fail("unknown particle " + particle);
    gun_.SetParticleDefinition(definition);
    gun_.SetParticleMomentumDirection(G4ThreeVector(0., 0., 1.));
    gun_.SetParticlePosition(G4ThreeVector(0., 0., startZ));
  }
  void GeneratePrimaries(G4Event* event) override {
    gun_.SetParticleEnergy((low_ + (high_ - low_) * G4UniformRand()) * MeV);
    gun_.GeneratePrimaryVertex(event);
  }

 private:
  G4ParticleGun gun_;
  double low_, high_;
};

G4Scintillation* FindScintillation() {
  auto* processes = G4ParticleTable::GetParticleTable()->FindParticle("e-")->GetProcessManager()->GetProcessList();
  for (std::size_t i = 0; i < processes->size(); ++i)
    if (auto* found = dynamic_cast<G4Scintillation*>((*processes)[i])) return found;
  return nullptr;
}

class EmWithOptics : public G4VModularPhysicsList {
 public:
  EmWithOptics() {
    SetVerboseLevel(0);
    RegisterPhysics(new G4EmStandardPhysics(0));
    RegisterPhysics(new G4DecayPhysics(0));
    RegisterPhysics(new G4OpticalPhysics(0));
  }
};

// --- GB15: per-step photon numbers ----------------------------------------------------------------------------------

#pragma pack(push, 1)
struct StepRecord {  // 28 bytes; judge.py reads the same layout
  double deposit;    // MeV, G4Step::GetTotalEnergyDeposit
  double visible;    // MeV, G4EmSaturation::VisibleEnergyDepositionAtAStep
  std::int32_t photons;  // G4Scintillation::GetNumPhotons, 0 if negative: the count before any split between components
  std::int32_t event;
  std::int32_t slice;  // z index of the pre-step point: the segmentation bin of Section 10.3 is (event, slice)
};
struct ComponentRecord {  // follows each StepRecord when the material has several components
  std::int32_t fast, medium, slow;  // optical secondaries of this step by G4ScintillationType
};
#pragma pack(pop)

struct StepCounters {
  long zeroDepositSteps = 0, zeroDepositPhotons = 0, stepsCompared = 0, secondariesDiffer = 0, stepsOutsideBlock = 0, emptyStepsAtRest = 0, negativeDraws = 0;
};

class BlockDetector : public G4VUserDetectorConstruction {
 public:
  BlockDetector(const Emission& emission, double birks, double halfMm) : emission_(emission), birks_(birks), half_(halfMm) {}
  G4VPhysicalVolume* Construct() override {
    auto* vacuum = G4NistManager::Instance()->FindOrBuildMaterial("G4_Galactic");
    auto* world = Box("world", 1.2 * half_ * mm, 1.2 * half_ * mm, 1.2 * half_ * mm, vacuum);
    auto* plastic = Plastic("block_plastic", birks_);
    plastic->SetMaterialPropertiesTable(ScintillationTable(emission_, 1e6));
    block_ = Box("block", half_ * mm, half_ * mm, half_ * mm, plastic);
    Place(block_, world, 0., 0.);
    return new G4PVPlacement(nullptr, G4ThreeVector(), world, "world", nullptr, false, 0, false);
  }
  const G4LogicalVolume* Block() const { return block_; }

 private:
  Emission emission_;
  double birks_, half_;
  G4LogicalVolume* block_ = nullptr;
};

class StepRecorder : public G4UserSteppingAction {
 public:
  StepRecorder(std::FILE* file, StepCounters* counters, G4Scintillation* process, const G4LogicalVolume* block, double halfMm, double sliceMm, int components, bool stacked)
      : file_(file), counters_(counters), process_(process), block_(block), half_(halfMm), slice_(sliceMm), components_(components), stacked_(stacked) {
    saturation_ = G4LossTableManager::Instance()->EmSaturation();
  }
  void UserSteppingAction(const G4Step* step) override {
    if (step->GetPreStepPoint()->GetTouchableHandle()->GetVolume()->GetLogicalVolume() != block_) {
      ++counters_->stepsOutsideBlock;
      return;
    }
    // A particle that stops with nothing to do at rest gets a last zero-length step in which no process runs, so GetNumPhotons still holds the step before.
    if (step->GetPostStepPoint()->GetStepStatus() == fAtRestDoItProc && step->GetTotalEnergyDeposit() <= 0.) {
      ++counters_->emptyStepsAtRest;
      return;
    }
    // GetNumPhotons keeps the raw draw: a Gaussian draw below -0.5 reads as a negative number, and the process then produces nothing.
    const int drawn = process_->GetNumPhotons();
    if (drawn < 0) ++counters_->negativeDraws;
    const int photons = std::max(drawn, 0);
    int parts[3] = {0, 0, 0}, secondaries = 0;
    if (stacked_) {
      for (const G4Track* secondary : *step->GetSecondaryInCurrentStep()) {
        if (secondary->GetDefinition() != G4OpticalPhoton::OpticalPhotonDefinition()) continue;
        ++secondaries;
        ++parts[G4ScintillationTrackInformation::Cast(secondary->GetUserInformation())->GetScintillationType()];
      }
      ++counters_->stepsCompared;
      if (components_ == 1 && secondaries != photons) ++counters_->secondariesDiffer;
    }
    const double deposit = step->GetTotalEnergyDeposit() / MeV;
    if (deposit <= 0.) {
      ++counters_->zeroDepositSteps;
      counters_->zeroDepositPhotons += photons;
      return;
    }
    const StepRecord record{deposit, saturation_->VisibleEnergyDepositionAtAStep(step) / MeV, photons,
                            G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID(),
                            static_cast<std::int32_t>(std::floor((step->GetPreStepPoint()->GetPosition().z() / mm + half_) / slice_))};
    std::fwrite(&record, sizeof record, 1, file_);
    if (components_ > 1) {
      const ComponentRecord split{parts[Fast], parts[Medium], parts[Slow]};
      std::fwrite(&split, sizeof split, 1, file_);
    }
  }

 private:
  std::FILE* file_;
  StepCounters* counters_;
  G4Scintillation* process_;
  const G4LogicalVolume* block_;
  G4EmSaturation* saturation_ = nullptr;
  double half_, slice_;
  int components_;
  bool stacked_;
};

class KillOpticalPhotons : public G4UserStackingAction {  // the per-step count is already taken from the parent's step
 public:
  G4ClassificationOfNewTrack ClassifyNewTrack(const G4Track* track) override {
    return track->GetDefinition() == G4OpticalPhoton::OpticalPhotonDefinition() ? fKill : fUrgent;
  }
};

int RunScintillation(const std::string& prefix, Options options) {
  Emission emission;
  emission.yieldPerMeV = options.Number("yield", 1000.);
  emission.resolutionScale = options.Number("resolution", 1.);
  const int components = static_cast<int>(options.Count("components", 1));
  if (components == 2) emission.componentYields = {options.Number("yield1", 0.7), options.Number("yield2", 0.3)};
  if (components == 3) emission.componentYields = {options.Number("yield1", 0.5), options.Number("yield2", 0.3), options.Number("yield3", 0.2)};
  const double birks = options.Number("birks", 0.126), halfMm = options.Number("half_mm", 500.), sliceMm = options.Number("slice_mm", 1.);
  const double lowMeV = options.Number("low_MeV", 1.), highMeV = options.Number("high_MeV", 20.);
  const long events = options.Count("events", 1000), seed = options.Count("seed", 1);
  const bool saturation = options.Count("saturation", 1) != 0;
  const bool stacked = components > 1 || options.Count("stack", 0) != 0;
  const std::string particle = options.Text("particle", "e-");
  options.RefuseUnknown();

  CLHEP::HepRandom::setTheSeed(seed);
  auto* parameters = G4OpticalParameters::Instance();
  parameters->SetProcessActivation("Cerenkov", false);
  parameters->SetScintStackPhotons(stacked);
  parameters->SetScintTrackSecondariesFirst(false);
  parameters->SetScintTrackInfo(stacked);

  G4RunManager manager;
  auto* detector = new BlockDetector(emission, birks, halfMm);
  manager.SetUserInitialization(detector);
  manager.SetUserInitialization(new EmWithOptics());
  std::FILE* file = std::fopen((prefix + ".steps").c_str(), "wb");
  if (!file) Options::Fail("cannot write " + prefix + ".steps");
  static char buffer[1 << 22];
  std::setvbuf(file, buffer, _IOFBF, sizeof buffer);
  manager.SetUserAction(new Gun(particle, lowMeV, highMeV, -halfMm + 1.));
  if (stacked) manager.SetUserAction(new KillOpticalPhotons());
  manager.Initialize();
  G4Scintillation* process = FindScintillation();
  if (!process) Options::Fail("no G4Scintillation on e-");
  if (!saturation) process->RemoveSaturation();
  const bool attached = process->GetSaturation() != nullptr;
  StepCounters counters;
  manager.SetUserAction(new StepRecorder(file, &counters, process, detector->Block(), halfMm, sliceMm, components, stacked));
  const double started = CpuSeconds();
  manager.BeamOn(static_cast<G4int>(events));
  const double spent = CpuSeconds() - started;
  std::fclose(file);

  std::map<std::string, std::string> items;
  items["events"] = std::to_string(events);
  items["seed"] = std::to_string(seed);
  items["yield_per_MeV"] = Hex(emission.yieldPerMeV);
  items["resolution_scale"] = Hex(emission.resolutionScale);
  items["birks_mm_per_MeV"] = Hex(birks);
  items["slice_mm"] = Hex(sliceMm);
  items["low_MeV"] = Hex(lowMeV);
  items["high_MeV"] = Hex(highMeV);
  items["particle"] = Quoted(particle);
  items["components"] = std::to_string(components);
  items["stacked"] = stacked ? "true" : "false";
  items["saturation_attached"] = attached ? "true" : "false";
  std::string yields = "[";
  for (std::size_t i = 0; i < emission.componentYields.size(); ++i) yields += (i ? ", " : "") + Hex(emission.componentYields[i]);
  items["component_yields"] = yields + "]";
  items["scintillation_by_particle_type"] = process->GetScintillationByParticleType() ? "true" : "false";
  items["record_bytes"] = std::to_string(sizeof(StepRecord) + (components > 1 ? sizeof(ComponentRecord) : 0));
  items["zero_deposit_steps"] = std::to_string(counters.zeroDepositSteps);
  items["zero_deposit_photons"] = std::to_string(counters.zeroDepositPhotons);
  items["negative_draws"] = std::to_string(counters.negativeDraws);
  items["empty_steps_at_rest"] = std::to_string(counters.emptyStepsAtRest);
  items["steps_outside_block"] = std::to_string(counters.stepsOutsideBlock);
  items["steps_compared_with_secondaries"] = std::to_string(counters.stepsCompared);
  items["steps_secondaries_differ"] = std::to_string(counters.secondariesDiffer);
  items["cpu_seconds"] = Hex(spent);
  std::string names = "[";
  bool first = true;
  G4MaterialPropertiesTable probe;
  for (const auto& name : probe.GetMaterialPropertyNames())
    if (name.rfind("SCINTILLATIONCOMPONENT", 0) == 0) {
      names += (first ? "" : ", ") + Quoted(name);
      first = false;
    }
  items["component_property_names"] = names + "]";
  WriteText(prefix + ".json", Object(items) + "\n");
  return 0;
}

// --- GB16: optical scope --------------------------------------------------------------------------------------------

// A stand-in for the plan's own KillProcess, which is not built yet: a discrete process on the optical photon, invoked on every step.
// "boundary" kills on the step whose post-step point lies in a volume outside the scope; "entry" lets the photon enter and kills it with a zero-length step there.
class ScopeKill : public G4VDiscreteProcess {
 public:
  ScopeKill(const std::string& mode, const std::set<std::string>* scope, long* killed) : G4VDiscreteProcess("ScopeKill"), entry_(mode == "entry"), scope_(scope), killed_(killed) {}
  G4bool IsApplicable(const G4ParticleDefinition& particle) override { return &particle == G4OpticalPhoton::OpticalPhotonDefinition(); }
  G4double PostStepGetPhysicalInteractionLength(const G4Track& track, G4double, G4ForceCondition* condition) override {
    *condition = entry_ ? NotForced : Forced;
    return entry_ && !scope_->count(track.GetVolume()->GetLogicalVolume()->GetName()) ? 0. : DBL_MAX;
  }
  G4double GetMeanFreePath(const G4Track&, G4double, G4ForceCondition*) override { return DBL_MAX; }
  G4VParticleChange* PostStepDoIt(const G4Track& track, const G4Step& step) override {
    aParticleChange.Initialize(track);
    const G4VPhysicalVolume* here = entry_ ? step.GetPreStepPoint()->GetPhysicalVolume() : step.GetPostStepPoint()->GetPhysicalVolume();
    if (here && !scope_->count(here->GetLogicalVolume()->GetName())) {
      aParticleChange.ProposeTrackStatus(fStopAndKill);
      ++*killed_;
    }
    return &aParticleChange;
  }

 private:
  bool entry_;
  const std::set<std::string>* scope_;
  long* killed_;
};

class ScopeKillPhysics : public G4VPhysicsConstructor {
 public:
  ScopeKillPhysics(const std::string& mode, const std::set<std::string>* scope, long* killed) : G4VPhysicsConstructor("scope_kill"), mode_(mode), scope_(scope), killed_(killed) {}
  void ConstructParticle() override {}
  void ConstructProcess() override { G4OpticalPhoton::OpticalPhotonDefinition()->GetProcessManager()->AddDiscreteProcess(new ScopeKill(mode_, scope_, killed_)); }

 private:
  std::string mode_;
  const std::set<std::string>* scope_;
  long* killed_;
};

class ScopeDetector : public G4VUserDetectorConstruction {
 public:
  // z: inside_scintillator then outside_scintillator on the beam line; side_volume beside the first, off the beam line.
  ScopeDetector(const Emission& emission, const std::string& outsideTable, const std::string& sideTable) : emission_(emission), outsideTable_(outsideTable), sideTable_(sideTable) {}
  G4VPhysicalVolume* Construct() override {
    auto* vacuum = G4NistManager::Instance()->FindOrBuildMaterial("G4_Galactic");
    auto* world = Box("world", 400. * mm, 200. * mm, 400. * mm, vacuum);
    auto* inside = Plastic("inside_plastic", 0.126);
    inside->SetMaterialPropertiesTable(ScintillationTable(emission_, 2000.));
    auto* outside = Plastic("outside_plastic", 0.126);
    if (outsideTable_ == "full") outside->SetMaterialPropertiesTable(ScintillationTable(emission_, 2000.));
    auto* side = Plastic("side_plastic", 0.126);
    if (sideTable_ == "rindex") {
      std::vector<G4double> energies{2.0 * eV, 3.5 * eV}, index{1.58, 1.58}, absorption{2000. * mm, 2000. * mm};
      auto* table = new G4MaterialPropertiesTable();
      table->AddProperty("RINDEX", energies, index);
      table->AddProperty("ABSLENGTH", energies, absorption);
      side->SetMaterialPropertiesTable(table);
    }
    Place(Box("inside_scintillator", 50. * mm, 50. * mm, 50. * mm, inside), world, 0., -50.);
    Place(Box("outside_scintillator", 50. * mm, 50. * mm, 50. * mm, outside), world, 0., 50.);
    Place(Box("side_volume", 50. * mm, 50. * mm, 50. * mm, side), world, 100., -50.);
    return new G4PVPlacement(nullptr, G4ThreeVector(), world, "world", nullptr, false, 0, false);
  }

 private:
  Emission emission_;
  std::string outsideTable_, sideTable_;
};

struct ScopeCounters {
  std::map<std::string, long> produced, opticalSteps, opticalZeroLengthSteps, opticalEnd, parents, excludedParents;
  long stepsChecked = 0;
  double worstRelative = 0., smallestPhotonEnergy = 1e300, closureWithPhotonsSmallestRelative = 1e300, photonEnergy = 0., depositInProducingSteps = 0.;
  long killedByScope = 0;
};

class ScopeRecorder : public G4UserSteppingAction {
 public:
  explicit ScopeRecorder(ScopeCounters* counters) : counters_(counters) {}
  void UserSteppingAction(const G4Step* step) override {
    const G4Track* track = step->GetTrack();
    const std::string volume = step->GetPreStepPoint()->GetPhysicalVolume()->GetLogicalVolume()->GetName();
    if (track->GetDefinition() == G4OpticalPhoton::OpticalPhotonDefinition()) {
      ++counters_->opticalSteps[volume];
      if (step->GetStepLength() <= 0.) ++counters_->opticalZeroLengthSteps[volume];
      if (track->GetTrackStatus() == fStopAndKill || track->GetTrackStatus() == fKillTrackAndSecondaries) {
        const G4VProcess* last = step->GetPostStepPoint()->GetProcessDefinedStep();
        ++counters_->opticalEnd[(last ? std::string(last->GetProcessName()) : std::string("none")) + "|" + volume];
      }
      return;
    }
    double optical = 0., others = 0.;
    long photons = 0;
    for (const G4Track* secondary : *step->GetSecondaryInCurrentStep()) {
      if (secondary->GetDefinition() == G4OpticalPhoton::OpticalPhotonDefinition()) {
        optical += secondary->GetKineticEnergy();
        ++photons;
        ++counters_->produced[volume + "|" + secondary->GetCreatorProcess()->GetProcessName()];
      } else {
        others += secondary->GetKineticEnergy();
      }
    }
    if (photons == 0) return;
    const std::string parent = track->GetDefinition()->GetParticleName();
    const G4VProcess* last = step->GetPostStepPoint()->GetProcessDefinedStep();
    if (parent == "e+" && last && last->GetProcessName() == "annihil") {  // the rest mass enters: a kinetic-energy identity does not apply
      ++counters_->excludedParents[parent + "|annihil"];
      return;
    }
    ++counters_->parents[parent];
    const double pre = step->GetPreStepPoint()->GetKineticEnergy(), post = track->GetKineticEnergy();
    const double deposit = step->GetTotalEnergyDeposit();
    const double residual = pre - post - deposit - others;
    counters_->worstRelative = std::max(counters_->worstRelative, std::fabs(residual) / pre);
    counters_->closureWithPhotonsSmallestRelative = std::min(counters_->closureWithPhotonsSmallestRelative, std::fabs(residual - optical) / pre);
    counters_->smallestPhotonEnergy = std::min(counters_->smallestPhotonEnergy, optical);
    counters_->photonEnergy += optical;
    counters_->depositInProducingSteps += deposit;
    ++counters_->stepsChecked;
  }

 private:
  ScopeCounters* counters_;
};

class ScopeActions : public G4VUserActionInitialization {  // with workers=1 the only worker fills the counters, so they need no lock
 public:
  ScopeActions(ScopeCounters* counters, double energyMeV) : counters_(counters), energy_(energyMeV) {}
  void Build() const override {
    SetUserAction(new Gun("e-", energy_, energy_, -150.));
    SetUserAction(new ScopeRecorder(counters_));
  }

 private:
  ScopeCounters* counters_;
  double energy_;
};

int RunScope(const std::string& path, Options options) {
  Emission emission;
  emission.yieldPerMeV = options.Number("yield", 500.);
  const std::string outsideTable = options.Text("outside_table", "none"), sideTable = options.Text("side_table", "none"), kill = options.Text("kill", "none");
  const std::string active = options.Text("active_volume", ""), activeType = options.Text("active_type", "scintillation");
  const bool general = options.Count("cerenkov_general", 0) != 0, cerenkov = options.Count("cerenkov", 1) != 0;
  const long events = options.Count("events", 20), seed = options.Count("seed", 1);
  const double energyMeV = options.Number("energy_MeV", 30.);
  const bool worker = options.Count("worker", 0) != 0;  // G4GeneralCerenkov initializes its models only on workers
  options.RefuseUnknown();

  CLHEP::HepRandom::setTheSeed(seed);
  auto* parameters = G4OpticalParameters::Instance();
  parameters->SetProcessActivation("Cerenkov", cerenkov);
  parameters->SetProcessActivation("OpRayleigh", false);
  parameters->SetProcessActivation("OpMieHG", false);
  if (general) parameters->EnableCerenkovGeneral(true);
  if (!active.empty()) parameters->SetActiveVolume(active, activeType == "cerenkov" ? kCerenkovDefault : kScintillationDefault);

  const std::set<std::string> scope{"inside_scintillator"};
  ScopeCounters counters;
  G4RunManager* manager = nullptr;
  if (worker) {
    auto* threaded = new G4MTRunManager();
    threaded->SetNumberOfThreads(1);
    manager = threaded;
  } else {
    manager = new G4RunManager();
  }
  manager->SetUserInitialization(new ScopeDetector(emission, outsideTable, sideTable));
  auto* physics = new EmWithOptics();
  if (kill != "none") physics->RegisterPhysics(new ScopeKillPhysics(kill, &scope, &counters.killedByScope));
  manager->SetUserInitialization(physics);
  manager->SetUserInitialization(new ScopeActions(&counters, energyMeV));
  manager->Initialize();
  const double started = CpuSeconds();
  manager->BeamOn(static_cast<G4int>(events));

  std::map<std::string, std::string> items;
  auto counts = [](const std::map<std::string, long>& source) { return Object(source); };
  items["events"] = std::to_string(events);
  items["seed"] = std::to_string(seed);
  items["yield_per_MeV"] = Hex(emission.yieldPerMeV);
  items["energy_MeV"] = Hex(energyMeV);
  items["kill"] = Quoted(kill);
  items["outside_table"] = Quoted(outsideTable);
  items["side_table"] = Quoted(sideTable);
  items["active_volume"] = Quoted(active);
  items["active_type"] = Quoted(activeType);
  items["cerenkov_general"] = general ? "true" : "false";
  items["cerenkov"] = cerenkov ? "true" : "false";
  items["worker"] = worker ? "true" : "false";
  items["produced"] = counts(counters.produced);
  items["optical_steps"] = counts(counters.opticalSteps);
  items["optical_zero_length_steps"] = counts(counters.opticalZeroLengthSteps);
  items["optical_end"] = counts(counters.opticalEnd);
  items["parents"] = counts(counters.parents);
  items["excluded_parents"] = counts(counters.excludedParents);
  items["killed_by_scope"] = std::to_string(counters.killedByScope);
  items["steps_checked"] = std::to_string(counters.stepsChecked);
  items["worst_relative"] = Hex(counters.worstRelative);
  items["smallest_relative_with_photon_energy"] = Hex(counters.closureWithPhotonsSmallestRelative);
  items["smallest_photon_energy_MeV"] = Hex(counters.smallestPhotonEnergy);
  items["photon_energy_MeV"] = Hex(counters.photonEnergy);
  items["deposit_in_producing_steps_MeV"] = Hex(counters.depositInProducingSteps);
  items["cpu_seconds"] = Hex(CpuSeconds() - started);
  WriteText(path, Object(items) + "\n");
  return 0;
}

// --- GB17: XTR radiators --------------------------------------------------------------------------------------------

struct RadiatorInputs {
  std::string name;
  G4LogicalVolume* envelope = nullptr;
  G4Material* foil = nullptr;
  G4Material* gas = nullptr;
  G4Material* medium = nullptr;
  double foilMm = 0.02, gapMm = 0.5;
  int foils = 200;
  double alphaFoil = 100., alphaGas = 40.;
};

G4VXTRenergyLoss* MakeRadiator(const RadiatorInputs& in) {
  const double t = in.foilMm * mm, g = in.gapMm * mm;
  if (in.name == "G4RegularXTRadiator") return new G4RegularXTRadiator(in.envelope, in.foil, in.gas, t, g, in.foils, "xtr_radiator");
  if (in.name == "G4TransparentRegXTRadiator") return new G4TransparentRegXTRadiator(in.envelope, in.foil, in.gas, t, g, in.foils, "xtr_radiator");
  if (in.name == "G4GammaXTRadiator") return new G4GammaXTRadiator(in.envelope, in.alphaFoil, in.alphaGas, in.foil, in.gas, t, g, in.foils, "xtr_radiator");
  if (in.name == "G4GaussXTRadiator") return new G4GaussXTRadiator(in.envelope, in.alphaFoil, in.alphaGas, in.foil, in.gas, t, g, in.foils, "xtr_radiator");
  if (in.name == "G4StrawTubeXTRadiator") return new G4StrawTubeXTRadiator(in.envelope, in.foil, in.gas, t, g, in.medium, false, "xtr_radiator");
  if (in.name == "G4XTRRegularRadModel") return new G4XTRRegularRadModel(in.envelope, in.foil, in.gas, t, g, in.foils, "xtr_radiator");
  if (in.name == "G4XTRTransparentRegRadModel") return new G4XTRTransparentRegRadModel(in.envelope, in.foil, in.gas, t, g, in.foils, "xtr_radiator");
  if (in.name == "G4XTRGammaRadModel") return new G4XTRGammaRadModel(in.envelope, in.alphaFoil, in.alphaGas, in.foil, in.gas, t, g, in.foils, "xtr_radiator");
  if (in.name == "G4XTRGaussRadModel") return new G4XTRGaussRadModel(in.envelope, in.alphaFoil, in.alphaGas, in.foil, in.gas, t, g, in.foils, "xtr_radiator");
  Options::Fail("unknown radiator class " + in.name);
}

class RadiatorDetector : public G4VUserDetectorConstruction {
 public:
  explicit RadiatorDetector(RadiatorInputs* inputs) : inputs_(inputs) {}
  G4VPhysicalVolume* Construct() override {
    auto* nist = G4NistManager::Instance();
    inputs_->foil = nist->FindOrBuildMaterial("G4_POLYETHYLENE");
    inputs_->gas = nist->FindOrBuildMaterial("G4_AIR");
    inputs_->medium = nist->FindOrBuildMaterial("G4_AIR");
    const double t = inputs_->foilMm, gap = inputs_->gapMm;
    const double massFoil = inputs_->foil->GetDensity() * t, massGas = inputs_->gas->GetDensity() * gap;
    // Section 11, rule 2: the volume-weighted mixture; rule 3: n(t + g) is the upper end of the allowed thickness.
    auto* mixture = new G4Material("radiator_mixture", (massFoil + massGas) / (t + gap), 2);
    mixture->AddMaterial(inputs_->foil, massFoil / (massFoil + massGas));
    mixture->AddMaterial(inputs_->gas, massGas / (massFoil + massGas));
    const double half = 0.5 * inputs_->foils * (t + gap);
    auto* vacuum = nist->FindOrBuildMaterial("G4_Galactic");
    auto* world = Box("world", 300. * mm, 300. * mm, (4. * half + 100.) * mm, vacuum);
    inputs_->envelope = Box("radiator_envelope", 200. * mm, 200. * mm, half * mm, mixture);
    Place(inputs_->envelope, world, 0., -(half + 5.) * mm);
    Place(Box("twin_volume", 200. * mm, 200. * mm, half * mm, mixture), world, 0., (half + 5.) * mm);
    return new G4PVPlacement(nullptr, G4ThreeVector(), world, "world", nullptr, false, 0, false);
  }

 private:
  RadiatorInputs* inputs_;
};

class RadiatorPhysics : public G4VPhysicsConstructor {
 public:
  RadiatorPhysics(RadiatorInputs* inputs, std::vector<std::string> particles, G4VXTRenergyLoss** made, int verbosity) : G4VPhysicsConstructor("xtr_radiator"), inputs_(inputs), particles_(std::move(particles)), made_(made), verbosity_(verbosity) {}
  void ConstructParticle() override {}
  void ConstructProcess() override {
    *made_ = MakeRadiator(*inputs_);
    (*made_)->SetVerboseLevel(verbosity_);
    for (const auto& name : particles_) G4ParticleTable::GetParticleTable()->FindParticle(name)->GetProcessManager()->AddDiscreteProcess(*made_);
  }

 private:
  RadiatorInputs* inputs_;
  std::vector<std::string> particles_;
  G4VXTRenergyLoss** made_;
  int verbosity_;
};

class EmWithRadiator : public G4VModularPhysicsList {
 public:
  EmWithRadiator() {
    SetVerboseLevel(0);
    RegisterPhysics(new G4EmStandardPhysics(0));
    RegisterPhysics(new G4DecayPhysics(0));
  }
};

struct RadiatorCounters {
  long events = 0, photons = 0, fromPrimary = 0, strictlyInside = 0, onSurface = 0, outsideEnvelope = 0, eventsWithPhoton = 0;
  long thisEvent = 0;
  double sumSquares = 0., energyMeV = 0.;
  std::map<std::string, long> vertexVolume;
};

class RadiatorRecorder : public G4UserSteppingAction {
 public:
  RadiatorRecorder(RadiatorCounters* counters, const RadiatorInputs* inputs) : counters_(counters), inputs_(inputs) {}
  void UserSteppingAction(const G4Step* step) override {
    for (const G4Track* secondary : *step->GetSecondaryInCurrentStep()) {
      const G4VProcess* creator = secondary->GetCreatorProcess();
      if (!creator || creator->GetProcessName() != "xtr_radiator") continue;
      ++counters_->photons;
      ++counters_->thisEvent;
      counters_->energyMeV += secondary->GetKineticEnergy() / MeV;
      if (step->GetTrack()->GetParentID() == 0) ++counters_->fromPrimary;
      const G4ThreeVector here = secondary->GetPosition();
      const G4VPhysicalVolume* placed = step->GetPreStepPoint()->GetPhysicalVolume();
      ++counters_->vertexVolume[placed->GetLogicalVolume()->GetName()];
      if (placed->GetLogicalVolume() != inputs_->envelope) {
        ++counters_->outsideEnvelope;
        continue;
      }
      const EInside where = inputs_->envelope->GetSolid()->Inside(here - placed->GetTranslation());
      if (where == kInside) ++counters_->strictlyInside;
      else if (where == kSurface) ++counters_->onSurface;
      else ++counters_->outsideEnvelope;
    }
  }

 private:
  RadiatorCounters* counters_;
  const RadiatorInputs* inputs_;
};

class RadiatorEvents : public G4UserEventAction {
 public:
  explicit RadiatorEvents(RadiatorCounters* counters) : counters_(counters) {}
  void BeginOfEventAction(const G4Event*) override { counters_->thisEvent = 0; }
  void EndOfEventAction(const G4Event*) override {
    ++counters_->events;
    counters_->sumSquares += static_cast<double>(counters_->thisEvent) * counters_->thisEvent;
    if (counters_->thisEvent > 0) ++counters_->eventsWithPhoton;
  }

 private:
  RadiatorCounters* counters_;
};

int RunRadiator(const std::string& path, Options options) {
  RadiatorInputs inputs;
  inputs.name = options.Text("class", "G4RegularXTRadiator");
  inputs.foilMm = options.Number("foil_mm", 0.02);
  inputs.gapMm = options.Number("gap_mm", 0.5);
  inputs.foils = static_cast<int>(options.Count("foils", 200));
  inputs.alphaFoil = options.Number("alpha_foil", 100.);
  inputs.alphaGas = options.Number("alpha_gas", 40.);
  const std::string particle = options.Text("particle", "e-");
  const double energyMeV = options.Number("energy_MeV", 2000.);
  const long events = options.Count("events", 1000), seed = options.Count("seed", 1);
  const bool electronsToo = options.Count("attach_electrons", 1) != 0;  // each attached particle rebuilds the radiator's tables
  options.RefuseUnknown();

  CLHEP::HepRandom::setTheSeed(seed);
  G4VXTRenergyLoss* radiator = nullptr;
  G4RunManager manager;
  manager.SetUserInitialization(new RadiatorDetector(&inputs));
  auto* physics = new EmWithRadiator();
  std::vector<std::string> attached{particle};
  if (particle != "e-" && electronsToo) attached.push_back("e-");
  physics->RegisterPhysics(new RadiatorPhysics(&inputs, attached, &radiator, 0));
  manager.SetUserInitialization(physics);
  const double reach = 0.5 * inputs.foils * (inputs.foilMm + inputs.gapMm);
  manager.SetUserAction(new Gun(particle, energyMeV, energyMeV, -(2. * reach + 20.)));
  RadiatorCounters counters;
  manager.SetUserAction(new RadiatorRecorder(&counters, &inputs));
  manager.SetUserAction(new RadiatorEvents(&counters));
  const double started = CpuSeconds();
  manager.Initialize();
  const double initialized = CpuSeconds();
  manager.BeamOn(static_cast<G4int>(events));

  auto* definition = G4ParticleTable::GetParticleTable()->FindParticle(particle);
  std::map<std::string, std::string> items;
  items["class"] = Quoted(inputs.name);
  items["particle"] = Quoted(particle);
  items["energy_MeV"] = Hex(energyMeV);
  items["gamma"] = Hex(1. + energyMeV * MeV / definition->GetPDGMass());
  items["seed"] = std::to_string(seed);
  items["events"] = std::to_string(counters.events);
  items["photons"] = std::to_string(counters.photons);
  items["photons_from_primary"] = std::to_string(counters.fromPrimary);
  items["events_with_photon"] = std::to_string(counters.eventsWithPhoton);
  items["photon_count_sum_squares"] = Hex(counters.sumSquares);
  items["photon_energy_MeV"] = Hex(counters.energyMeV);
  items["strictly_inside"] = std::to_string(counters.strictlyInside);
  items["on_surface"] = std::to_string(counters.onSurface);
  items["outside_envelope"] = std::to_string(counters.outsideEnvelope);
  items["vertex_volume"] = Object(counters.vertexVolume);
  items["attach_electrons"] = electronsToo ? "true" : "false";
  items["foil_mm"] = Hex(inputs.foilMm);
  items["gap_mm"] = Hex(inputs.gapMm);
  items["foils"] = std::to_string(inputs.foils);
  items["alpha_foil_read_back"] = Hex(radiator->GetAlphaPlate());
  items["alpha_gas_read_back"] = Hex(radiator->GetAlphaGas());
  items["initialize_cpu_seconds"] = Hex(initialized - started);
  items["run_cpu_seconds"] = Hex(CpuSeconds() - initialized);
  WriteText(path, Object(items) + "\n");
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 3) Options::Fail("usage: s3_optics gb15|gb16|gb17 PATH key=value...");
  const std::string mode = argv[1];
  Options options(argc, argv, 3);
  if (mode == "gb15") return RunScintillation(argv[2], options);
  if (mode == "gb16") return RunScope(argv[2], options);
  if (mode == "gb17") return RunRadiator(argv[2], options);
  Options::Fail("unknown mode " + mode);
}
