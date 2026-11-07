// Prototypes GB19, GB20 and GB21 of the g4sim plan (Section 23): one program, judged by judge.py; it measures and gives no verdict.
// Written from the Geant4 11.4 API; no example code copied or adapted. Serial run manager; every event is reseeded from (SEED, event), as seeding per-event does.
//   s3_steps gb19 OUT.json HOOK SEED EVENTS [TRACE_EVENT TRACE.txt]
//     HOOK: none, idle (region, process and a model that never triggers), consuming, triggering, region_only (no process, no model), process_only (no region, no model),
//           inert_process (no region, no model, and in place of the fast-simulation process a discrete process of our own that never limits a step)
//   s3_steps gb20 OUT.json LAYOUT IMPL BEAM SEED EVENTS [TRACE_EVENT TRACE.txt]  BEAM: geantino, physics
//     LAYOUT: linear_exact, linear_decimal (slices filling the mother), gapped, grid6, grid8, ring, module
//     IMPL: ordinary, replica, parameterised, assembly, assembly_raw (no copy-number pass), ordinary_module, ordinary_nudged (one centre moved by one ulp)
//   s3_steps gb21 OUT.json VARIANT SEED EVENTS      VARIANT: plain, emit, pixe, booked_as_deposit, pre_step_energy
// Every real number is written with %a.
#include <cfloat>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include "FTFP_BERT.hh"
#include "G4AssemblyVolume.hh"
#include "G4Box.hh"
#include "G4DynamicParticle.hh"
#include "G4Event.hh"
#include "G4EmParameters.hh"
#include "G4FastSimulationHelper.hh"
#include "G4FastStep.hh"
#include "G4FastTrack.hh"
#include "G4Gamma.hh"
#include "G4LogicalVolume.hh"
#include "G4LossTableManager.hh"
#include "G4Navigator.hh"
#include "G4NistManager.hh"
#include "G4PVParameterised.hh"
#include "G4PVPlacement.hh"
#include "G4PVReplica.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4ProcessManager.hh"
#include "G4ProcessVector.hh"
#include "G4Region.hh"
#include "G4ReplicaNavigation.hh"
#include "G4RunManagerFactory.hh"
#include "G4SDManager.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4TouchableHistory.hh"
#include "G4Track.hh"
#include "G4UAtomicDeexcitation.hh"
#include "G4UserEventAction.hh"
#include "G4UserSteppingAction.hh"
#include "G4VDiscreteProcess.hh"
#include "G4VFastSimulationModel.hh"
#include "G4VPVParameterisation.hh"
#include "G4VPhysicsConstructor.hh"
#include "G4VSensitiveDetector.hh"
#include "G4VUserActionInitialization.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "Randomize.hh"

namespace {

std::string gMode, gHook, gLayout, gImpl, gBeam, gVariant;
std::uint64_t gSeed = 0;
long gTraceEvent = -1;
std::ofstream gTrace;
long gCurrentEvent = -1;
G4VPhysicalVolume* gWorld = nullptr;
double gExtent = 40., gStackHalfZ = 100.;

std::string Hex(double value) {
  char text[64];
  std::snprintf(text, sizeof text, "%a", value);
  return text;
}

std::string HexWord(std::uint64_t value) {
  char text[32];
  std::snprintf(text, sizeof text, "%016llx", static_cast<unsigned long long>(value));
  return text;
}

// The public FNV-1a hash; Mix below is the public SplitMix64 finalizer.
struct Fnv {
  std::uint64_t state = 1469598103934665603ULL;
  void Bytes(const void* start, std::size_t size) {
    const auto* byte = static_cast<const unsigned char*>(start);
    for (std::size_t k = 0; k < size; ++k) state = (state ^ byte[k]) * 1099511628211ULL;
  }
  void Real(double value) { Bytes(&value, sizeof value); }
  void Whole(long value) { Bytes(&value, sizeof value); }
  void Text(const std::string& value) { Bytes(value.data(), value.size() + 1); }
};

// A generator of its own for the beam, so that primaries never touch the Geant4 engine and are the same in every run of a seed.
std::uint64_t Mix(std::uint64_t seed, std::uint64_t event, std::uint64_t slot) {
  std::uint64_t z = seed * 0x9E3779B97F4A7C15ULL + event * 0xBF58476D1CE4E5B9ULL + slot * 0x94D049BB133111EBULL + 0x2545F4914F6CDD1DULL;
  z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
  z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
  return z ^ (z >> 31);
}
double Unit(std::uint64_t seed, std::uint64_t event, std::uint64_t slot) { return (Mix(seed, event, slot) >> 11) * (1.0 / 9007199254740992.0); }

std::string Chain(const G4VTouchable* touchable) {
  std::string text;
  for (int level = touchable->GetHistoryDepth(); level >= 0; --level) {
    text += touchable->GetVolume(level)->GetLogicalVolume()->GetName();
    text += ':';
    text += std::to_string(touchable->GetCopyNumber(level));
    if (level) text += '/';
  }
  return text;
}

struct Cell {
  double deposit = 0, length = 0;
  long steps = 0;
};
std::map<std::string, Cell> gCells;
std::vector<std::string> gEvents;
Fnv gTraceHash, gRandomHash, gNavigationHash;
long gStepCount = 0;

class CellScorer : public G4VSensitiveDetector {
 public:
  explicit CellScorer(const G4String& name) : G4VSensitiveDetector(name) {}
  G4bool ProcessHits(G4Step* step, G4TouchableHistory*) override {
    Cell& cell = gCells[Chain(step->GetPreStepPoint()->GetTouchable())];
    cell.deposit += step->GetTotalEnergyDeposit();
    cell.length += step->GetStepLength();
    ++cell.steps;
    return true;
  }
};

// ---- GB19: the hook ----
struct HookCounts {
  long applicable = 0, trigger = 0, doIt = 0;
} gHookCounts;

class HookModel : public G4VFastSimulationModel {
 public:
  HookModel(const G4String& name, G4Region* region) : G4VFastSimulationModel(name, region) {}
  G4bool IsApplicable(const G4ParticleDefinition&) override {
    ++gHookCounts.applicable;
    return true;
  }
  G4bool ModelTrigger(const G4FastTrack&) override {
    ++gHookCounts.trigger;
    if (gHook == "consuming") G4UniformRand();
    return gHook == "triggering";
  }
  void DoIt(const G4FastTrack& track, G4FastStep& step) override {
    ++gHookCounts.doIt;
    step.KillPrimaryTrack();
    step.ProposeTotalEnergyDeposited(track.GetPrimaryTrack()->GetKineticEnergy());
  }
};

class InertProcess : public G4VDiscreteProcess {
 public:
  InertProcess() : G4VDiscreteProcess("InertProcess", fUserDefined) {}
  G4bool IsApplicable(const G4ParticleDefinition&) override { return true; }
  G4double GetMeanFreePath(const G4Track&, G4double, G4ForceCondition*) override { return DBL_MAX; }
  G4double PostStepGetPhysicalInteractionLength(const G4Track&, G4double, G4ForceCondition* condition) override {
    *condition = NotForced;
    return DBL_MAX;
  }
  G4VParticleChange* PostStepDoIt(const G4Track& track, const G4Step&) override {
    aParticleChange.Initialize(track);
    return &aParticleChange;
  }
};

class HookPhysics : public G4VPhysicsConstructor {
 public:
  HookPhysics() : G4VPhysicsConstructor("hook") {}
  void ConstructParticle() override {}
  void ConstructProcess() override {
    auto iterator = GetParticleIterator();
    iterator->reset();
    while ((*iterator)()) {
      G4ParticleDefinition* particle = iterator->value();
      if (!particle->GetProcessManager() || particle->IsShortLived()) continue;
      if (gHook == "inert_process") particle->GetProcessManager()->AddDiscreteProcess(new InertProcess());
      else G4FastSimulationHelper::ActivateFastSimulation(particle->GetProcessManager());
    }
  }
};

class HookDetector : public G4VUserDetectorConstruction {
 public:
  G4VPhysicalVolume* Construct() override {
    auto* nist = G4NistManager::Instance();
    auto* worldBox = new G4Box("World", 1000., 1000., 1000.);
    auto* world = new G4LogicalVolume(worldBox, nist->FindOrBuildMaterial("G4_AIR"), "World");
    gWorld = new G4PVPlacement(nullptr, G4ThreeVector(), world, "World", nullptr, false, 0);
    fFront = new G4LogicalVolume(new G4Box("Front", 200., 200., 10.), nist->FindOrBuildMaterial("G4_Al"), "Front");
    fEnvelope = new G4LogicalVolume(new G4Box("Envelope", 200., 200., 100.), nist->FindOrBuildMaterial("G4_PbWO4"), "Envelope");
    fBack = new G4LogicalVolume(new G4Box("Back", 200., 200., 20.), nist->FindOrBuildMaterial("G4_Si"), "Back");
    new G4PVPlacement(nullptr, G4ThreeVector(0, 0, -100.), fFront, "Front", world, false, 0);
    new G4PVPlacement(nullptr, G4ThreeVector(0, 0, 50.), fEnvelope, "Envelope", world, false, 0);
    new G4PVPlacement(nullptr, G4ThreeVector(0, 0, 200.), fBack, "Back", world, false, 0);
    if (gHook != "none" && gHook != "process_only" && gHook != "inert_process") {
      fRegion = new G4Region("fast_envelope");
      fRegion->AddRootLogicalVolume(fEnvelope);
    }
    return gWorld;
  }
  void ConstructSDandField() override {
    auto* scorer = new CellScorer("hook_scorer");
    G4SDManager::GetSDMpointer()->AddNewDetector(scorer);
    for (auto* logical : {fFront, fEnvelope, fBack}) SetSensitiveDetector(logical, scorer);
    if (fRegion && gHook != "region_only") new HookModel("hook_model", fRegion);
  }

 private:
  G4LogicalVolume *fFront = nullptr, *fEnvelope = nullptr, *fBack = nullptr;
  G4Region* fRegion = nullptr;
};

// ---- GB20: one geometry, several placement implementations ----
struct Place {
  G4ThreeVector position;
  G4RotationMatrix active;  // the rotation of the volume; G4PVPlacement and a parameterisation want the inverse
  int copy = 0;
};

class TableParameterisation : public G4VPVParameterisation {
 public:
  explicit TableParameterisation(const std::vector<Place>& places) {
    for (const Place& place : places) {
      fPosition.push_back(place.position);
      fFrame.push_back(place.active.isIdentity() ? nullptr : new G4RotationMatrix(place.active.inverse()));
    }
  }
  void ComputeTransformation(const G4int number, G4VPhysicalVolume* volume) const override {
    volume->SetTranslation(fPosition[number]);
    volume->SetRotation(fFrame[number]);
  }

 private:
  std::vector<G4ThreeVector> fPosition;
  std::vector<G4RotationMatrix*> fFrame;
};

class PlacementDetector : public G4VUserDetectorConstruction {
 public:
  G4VPhysicalVolume* Construct() override {
    auto* nist = G4NistManager::Instance();
    auto* air = nist->FindOrBuildMaterial("G4_AIR");
    auto* scintillator = nist->FindOrBuildMaterial("G4_PLASTIC_SC_VINYLTOLUENE");
    auto* lead = nist->FindOrBuildMaterial("G4_Pb");
    auto* world = new G4LogicalVolume(new G4Box("World", 1000., 1000., 1000.), air, "World");
    gWorld = new G4PVPlacement(nullptr, G4ThreeVector(), world, "World", nullptr, false, 0);

    // pitch and thickness are exact fractions; each centre is the correctly rounded value of its exact decimal, as the IR's strings give it
    int count = 16;
    long pitchTop = 8, pitchBottom = 1, thickTop = 8, thickBottom = 1;
    if (gLayout == "linear_decimal") pitchTop = thickTop = 37, pitchBottom = thickBottom = 10;
    if (gLayout == "gapped") pitchTop = 10;
    std::vector<Place> places;
    double halfX = 40., halfY = 40., halfZ = 0.5 * thickTop / thickBottom, stackX = 40., stackY = 40., stackZ = 0;
    if (gLayout == "linear_exact" || gLayout == "linear_decimal" || gLayout == "gapped") {
      halfZ = static_cast<double>(thickTop) / (2. * thickBottom);
      stackZ = static_cast<double>(count * pitchTop) / (2. * pitchBottom);
      for (int k = 0; k < count; ++k) {
        Place place;
        place.position = G4ThreeVector(0, 0, static_cast<double>((2 * k - count + 1) * pitchTop) / (2. * pitchBottom));
        place.copy = k;
        places.push_back(place);
      }
    } else if (gLayout == "grid6" || gLayout == "grid8") {
      const int side = gLayout == "grid6" ? 6 : 8;  // the field width of i is 3 bits in both, so copy number = i + 8 j
      halfX = halfY = 4.;
      halfZ = 20.;
      stackX = stackY = 45.;
      stackZ = 21.;
      for (int j = 0; j < side; ++j)
        for (int i = 0; i < side; ++i) {
          Place place;
          place.position = G4ThreeVector((2 * i - side + 1) * 5., (2 * j - side + 1) * 5., 0.);
          place.copy = i + 8 * j;
          places.push_back(place);
        }
    } else if (gLayout == "ring") {
      halfX = halfY = halfZ = 20.;
      stackX = stackY = 150.;
      stackZ = 30.;
      for (int k = 0; k < 12; ++k) {
        Place place;
        const double angle = (30. * k + 15.) * CLHEP::deg;
        place.position = G4ThreeVector(100. * std::cos(angle), 100. * std::sin(angle), 0.);
        place.active.rotateZ(angle);
        place.copy = k;
        places.push_back(place);
      }
    } else if (gLayout == "module") {
      count = 8;
      stackZ = 64.;
      for (int k = 0; k < count; ++k) {
        Place place;
        place.position = G4ThreeVector(0, 0, (2 * k - count + 1) * 8.);
        place.copy = k;
        places.push_back(place);
      }
    } else {
      Refuse("unknown layout");
    }
    gExtent = stackX;
    gStackHalfZ = stackZ;
    auto* stack = new G4LogicalVolume(new G4Box("Stack", stackX, stackY, stackZ), air, "Stack");
    new G4PVPlacement(nullptr, G4ThreeVector(), stack, "Stack", world, false, 0);

    if (gLayout == "module") {
      BuildModules(stack, places, scintillator, lead, air);
      return gWorld;
    }
    auto* cell = new G4LogicalVolume(new G4Box("Cell", halfX, halfY, halfZ), scintillator, "Cell");
    auto* plate = new G4LogicalVolume(new G4Box("Plate", halfX, halfY, halfZ / 4.), lead, "Plate");
    new G4PVPlacement(nullptr, G4ThreeVector(), plate, "Plate", cell, false, 0);
    fScored = {cell, plate};

    if (gImpl == "ordinary_nudged") {
      places[count / 2].position.setZ(std::nextafter(places[count / 2].position.z(), DBL_MAX));
    }
    if (gImpl == "ordinary" || gImpl == "ordinary_nudged") {
      for (const Place& place : places) new G4PVPlacement(G4Transform3D(place.active, place.position), cell, "Cell", stack, false, place.copy);
    } else if (gImpl == "replica") {
      if (gLayout != "linear_exact" && gLayout != "linear_decimal") Refuse("a G4PVReplica fills its mother with equal slices along one axis: this layout has no replica form");
      new G4PVReplica("Cell", cell, stack, kZAxis, count, static_cast<double>(pitchTop) / pitchBottom);
    } else if (gImpl == "parameterised") {
      const bool linear = gLayout.rfind("linear", 0) == 0 || gLayout == "gapped";
      new G4PVParameterised("Cell", cell, stack, linear ? kZAxis : kUndefined, static_cast<int>(places.size()), new TableParameterisation(places));
    } else if (gImpl == "assembly" || gImpl == "assembly_raw") {
      auto* assembly = new G4AssemblyVolume();
      G4Transform3D origin;
      assembly->AddPlacedVolume(cell, origin);
      for (const Place& place : places) {
        G4Transform3D where(place.active, place.position);
        assembly->MakeImprint(stack, where);
      }
      if (gImpl == "assembly") {
        auto volume = assembly->GetVolumesIterator();
        for (const Place& place : places) (*volume++)->SetCopyNo(place.copy);
      }
    } else {
      Refuse("unknown implementation for this layout");
    }
    return gWorld;
  }
  void ConstructSDandField() override {
    auto* scorer = new CellScorer("cell_scorer");
    G4SDManager::GetSDMpointer()->AddNewDetector(scorer);
    for (auto* logical : fScored) SetSensitiveDetector(logical, scorer);
  }

 private:
  [[noreturn]] static void Refuse(const char* reason) {
    std::printf("{\"status\": \"rejected\", \"message\": \"%s\"}\n", reason);
    std::exit(2);
  }
  // A module is a front and a rear plate. Flat ordinary placements and an assembly put both straight into the stack; ordinary_module keeps a mother per module.
  void BuildModules(G4LogicalVolume* stack, const std::vector<Place>& places, G4Material* front, G4Material* rear, G4Material* air) {
    auto* first = new G4LogicalVolume(new G4Box("Front", 40., 40., 4.), front, "Front");
    auto* second = new G4LogicalVolume(new G4Box("Rear", 40., 40., 4.), rear, "Rear");
    fScored = {first, second};
    const G4ThreeVector shift(0, 0, 4.);
    if (gImpl == "ordinary") {
      for (const Place& place : places) {
        new G4PVPlacement(nullptr, place.position - shift, first, "Front", stack, false, place.copy);
        new G4PVPlacement(nullptr, place.position + shift, second, "Rear", stack, false, place.copy);
      }
    } else if (gImpl == "ordinary_module") {
      auto* module = new G4LogicalVolume(new G4Box("Module", 40., 40., 8.), air, "Module");
      new G4PVPlacement(nullptr, -shift, first, "Front", module, false, 0);
      new G4PVPlacement(nullptr, shift, second, "Rear", module, false, 0);
      for (const Place& place : places) new G4PVPlacement(nullptr, place.position, module, "Module", stack, false, place.copy);
    } else if (gImpl == "assembly" || gImpl == "assembly_raw") {
      auto* assembly = new G4AssemblyVolume();
      G4ThreeVector minusShift = -shift, plusShift = shift;
      assembly->AddPlacedVolume(first, minusShift, nullptr);
      assembly->AddPlacedVolume(second, plusShift, nullptr);
      for (const Place& place : places) {
        G4Transform3D where(place.active, place.position);
        assembly->MakeImprint(stack, where);
      }
      if (gImpl == "assembly") {
        auto volume = assembly->GetVolumesIterator();
        for (const Place& place : places) {
          (*volume++)->SetCopyNo(place.copy);
          (*volume++)->SetCopyNo(place.copy);
        }
      }
    } else {
      Refuse("unknown implementation for this layout");
    }
  }
  std::vector<G4LogicalVolume*> fScored;
};

// The volume tree as a write-back: chain of logical:copy, translation and rotation in the mother, and the box half-lengths, one row per placed copy.
void WriteBack(const G4LogicalVolume* mother, const std::string& chain, std::ostringstream& rows, bool& first) {
  G4ReplicaNavigation replicas;
  for (std::size_t index = 0; index < mother->GetNoDaughters(); ++index) {
    G4VPhysicalVolume* daughter = mother->GetDaughter(index);
    const int copies = daughter->IsReplicated() ? daughter->GetMultiplicity() : 1;
    for (int number = 0; number < copies; ++number) {
      if (daughter->IsParameterised()) {
        daughter->GetParameterisation()->ComputeTransformation(number, daughter);
        daughter->SetCopyNo(number);
      } else if (daughter->IsReplicated()) {
        replicas.ComputeTransformation(number, daughter);
        daughter->SetCopyNo(number);
      }
      const G4LogicalVolume* logical = daughter->GetLogicalVolume();
      const std::string path = chain + "/" + logical->GetName() + ":" + std::to_string(daughter->GetCopyNo());
      const G4ThreeVector t = daughter->GetObjectTranslation();
      const G4RotationMatrix r = daughter->GetObjectRotationValue();
      const auto* box = dynamic_cast<const G4Box*>(logical->GetSolid());
      rows << (first ? "" : ",\n") << "[\"" << path << "\", \"" << logical->GetMaterial()->GetName() << "\", [\"" << Hex(t.x()) << "\", \"" << Hex(t.y()) << "\", \"" << Hex(t.z())
           << "\"], [\"" << Hex(r.xx()) << "\", \"" << Hex(r.xy()) << "\", \"" << Hex(r.xz()) << "\", \"" << Hex(r.yx()) << "\", \"" << Hex(r.yy()) << "\", \"" << Hex(r.yz()) << "\", \""
           << Hex(r.zx()) << "\", \"" << Hex(r.zy()) << "\", \"" << Hex(r.zz()) << "\"], [\"" << Hex(box->GetXHalfLength()) << "\", \"" << Hex(box->GetYHalfLength()) << "\", \""
           << Hex(box->GetZHalfLength()) << "\"]]";
      first = false;
      WriteBack(logical, path, rows, first);
    }
  }
}

// The navigator asked directly on a lattice of points that avoids the faces: which chain holds each point.
std::string NavigationScan() {
  G4Navigator navigator;
  navigator.SetWorldVolume(gWorld);
  std::ostringstream rows;
  bool first = true;
  for (int i = 0; i < 16; ++i)
    for (int j = 0; j < 16; ++j)
      for (int k = 0; k < 64; ++k) {
        const G4ThreeVector point(gExtent * (2 * i - 15.3) / 16.5, gExtent * (2 * j - 15.1) / 16.5, gStackHalfZ * (2 * k - 62.7) / 64.5);
        navigator.LocateGlobalPointAndSetup(point, nullptr, false, true);
        G4TouchableHistory* history = navigator.CreateTouchableHistory();
        rows << (first ? "" : ",") << '"' << Chain(history) << '"';
        first = false;
        delete history;
      }
  return rows.str();
}

// ---- GB21: the kill ----
struct KillPending {
  bool valid = false;
  double keEntry = 0, keAfterProbe = 0, killed = 0, depositAtKill = 0;
} gPending;
std::vector<std::string> gKillRows;
long gDefinedWithoutDoIt = 0, gStepsOfKillTracks = 0;
double gKillLength = 1.;
const G4VProcess *gKill = nullptr, *gProbe = nullptr;

// A discrete process that ends the step at the path length where the track is to die, and books the kinetic energy the track has then.
class KillProcess : public G4VDiscreteProcess {
 public:
  KillProcess() : G4VDiscreteProcess("KillProcess", fUserDefined) {}
  G4bool IsApplicable(const G4ParticleDefinition&) override { return true; }
  G4double GetMeanFreePath(const G4Track&, G4double, G4ForceCondition*) override { return DBL_MAX; }
  G4double PostStepGetPhysicalInteractionLength(const G4Track& track, G4double, G4ForceCondition* condition) override {
    *condition = NotForced;
    return std::max(gKillLength - track.GetTrackLength(), 0.);
  }
  G4VParticleChange* PostStepDoIt(const G4Track& track, const G4Step& step) override {
    aParticleChange.Initialize(track);
    const double kinetic = track.GetKineticEnergy();
    gPending.valid = true;
    gPending.depositAtKill = step.GetTotalEnergyDeposit();
    gPending.killed = gVariant == "pre_step_energy" ? step.GetPreStepPoint()->GetKineticEnergy() : kinetic;
    if (gVariant == "booked_as_deposit") aParticleChange.ProposeLocalEnergyDeposit(kinetic);
    aParticleChange.ProposeEnergy(0.);
    aParticleChange.ProposeTrackStatus(fStopAndKill);
    return &aParticleChange;
  }
};

// Runs before KillProcess in every step, forced. It reads the kinetic energy left by the along-step processes, independently of KillProcess;
// in variant emit it also makes a post-step secondary in the kill step, the only way one can exist there since no other discrete process runs in that step.
class PreKillProbe : public G4VDiscreteProcess {
 public:
  PreKillProbe() : G4VDiscreteProcess("PreKillProbe", fUserDefined) {}
  G4bool IsApplicable(const G4ParticleDefinition&) override { return true; }
  G4double GetMeanFreePath(const G4Track&, G4double, G4ForceCondition*) override { return DBL_MAX; }
  G4double PostStepGetPhysicalInteractionLength(const G4Track&, G4double, G4ForceCondition* condition) override {
    *condition = Forced;
    return DBL_MAX;
  }
  G4VParticleChange* PostStepDoIt(const G4Track& track, const G4Step& step) override {
    aParticleChange.Initialize(track);
    if (step.GetPostStepPoint()->GetProcessDefinedStep() != gKill) return &aParticleChange;
    const double kinetic = track.GetKineticEnergy();
    gPending.keEntry = gPending.keAfterProbe = kinetic;
    if (gVariant == "emit" && kinetic > 0) {
      const double energy = 0.25 * kinetic;
      gPending.keAfterProbe = kinetic - energy;
      aParticleChange.SetNumberOfSecondaries(1);
      aParticleChange.AddSecondary(new G4DynamicParticle(G4Gamma::Definition(), track.GetMomentumDirection(), energy));
      aParticleChange.ProposeEnergy(gPending.keAfterProbe);
    }
    return &aParticleChange;
  }
};

class KillPhysics : public G4VPhysicsConstructor {
 public:
  KillPhysics() : G4VPhysicsConstructor("kill") {}
  void ConstructParticle() override {}
  void ConstructProcess() override {
    auto* kill = new KillProcess();
    auto* probe = new PreKillProbe();
    gKill = kill;
    gProbe = probe;
    auto iterator = GetParticleIterator();
    iterator->reset();
    while ((*iterator)()) {
      G4ParticleDefinition* particle = iterator->value();
      if (!particle->GetProcessManager() || particle->IsShortLived()) continue;
      particle->GetProcessManager()->AddDiscreteProcess(probe, 500);
      particle->GetProcessManager()->AddDiscreteProcess(kill, 1000);
    }
  }
};

class KillDetector : public G4VUserDetectorConstruction {
 public:
  G4VPhysicalVolume* Construct() override {
    auto* nist = G4NistManager::Instance();
    auto* world = new G4LogicalVolume(new G4Box("World", 1000., 1000., 1000.), nist->FindOrBuildMaterial("G4_Galactic"), "World");
    gWorld = new G4PVPlacement(nullptr, G4ThreeVector(), world, "World", nullptr, false, 0);
    auto* block = new G4LogicalVolume(new G4Box("Block", 500., 500., 500.), nist->FindOrBuildMaterial(gVariant == "pixe" ? "G4_Pb" : "G4_Si"), "Block");
    new G4PVPlacement(nullptr, G4ThreeVector(), block, "Block", world, false, 0);
    return gWorld;
  }
};

void RecordKill(const G4Step* step) {
  const G4StepPoint* post = step->GetPostStepPoint();
  if (post->GetProcessDefinedStep() != gKill) return;
  if (!gPending.valid) {
    ++gDefinedWithoutDoIt;
    return;
  }
  gPending.valid = false;
  double secondaryAlong = 0, secondaryPost = 0;
  long secondaries = 0;
  if (const auto* made = step->GetSecondaryInCurrentStep()) {
    for (const G4Track* secondary : *made) {
      ++secondaries;
      (secondary->GetCreatorProcess() == gProbe ? secondaryPost : secondaryAlong) += secondary->GetKineticEnergy();
    }
  }
  std::ostringstream row;
  row << "[\"" << step->GetTrack()->GetDefinition()->GetParticleName() << "\", \"" << Hex(step->GetPreStepPoint()->GetKineticEnergy()) << "\", \"" << Hex(gPending.keEntry) << "\", \""
      << Hex(gPending.keAfterProbe) << "\", \"" << Hex(gPending.killed) << "\", \"" << Hex(gPending.depositAtKill) << "\", \"" << Hex(step->GetTotalEnergyDeposit()) << "\", \""
      << Hex(secondaryAlong) << "\", \"" << Hex(secondaryPost) << "\", \"" << Hex(post->GetKineticEnergy()) << "\", " << step->GetTrack()->GetTrackStatus() << ", " << secondaries << ", \""
      << Hex(step->GetStepLength()) << "\"]";
  gKillRows.push_back(row.str());
}

// ---- common actions ----
struct Beam {
  const char* particle;
  double energy;
};

class Primaries : public G4VUserPrimaryGeneratorAction {
 public:
  Primaries() : fGun(1) {}
  void GeneratePrimaries(G4Event* event) override {
    const long number = event->GetEventID();
    long seeds[3] = {static_cast<long>(Mix(gSeed, number, 0) >> 33) + 1, static_cast<long>(Mix(gSeed, number, 1) >> 33) + 1, 0};
    G4Random::setTheSeeds(seeds);
    if (gMode == "gb19") {
      static const Beam beams[] = {{"e-", 1 * GeV}, {"gamma", 500 * MeV}, {"pi+", 3 * GeV}, {"proton", 2 * GeV}, {"mu-", 1 * GeV}, {"neutron", 200 * MeV}};
      Shoot(beams[number % 6], G4ThreeVector(100. * (Unit(gSeed, number, 2) - 0.5), 100. * (Unit(gSeed, number, 3) - 0.5), -500.), G4ThreeVector(0, 0, 1));
    } else if (gMode == "gb20") {
      ShootPlacement(number);
    } else {
      static const Beam beams[] = {{"e-", 20 * MeV}, {"e+", 20 * MeV}, {"mu-", 200 * MeV}, {"mu+", 200 * MeV}, {"pi+", 200 * MeV},
                                   {"pi-", 200 * MeV}, {"proton", 100 * MeV}, {"alpha", 200 * MeV}, {"gamma", 20 * MeV}, {"neutron", 20 * MeV}};
      gKillLength = 0.02 * std::pow(1.6, (number / 10) % 12);
      Shoot(beams[number % 10], G4ThreeVector(0, 0, -490.), G4ThreeVector(0, 0, 1));
    }
    fGun.GeneratePrimaryVertex(event);
  }

 private:
  void Shoot(const Beam& beam, const G4ThreeVector& where, const G4ThreeVector& towards) {
    fGun.SetParticleDefinition(G4ParticleTable::GetParticleTable()->FindParticle(beam.particle));
    fGun.SetParticleEnergy(beam.energy);
    fGun.SetParticlePosition(where);
    fGun.SetParticleMomentumDirection(towards);
  }
  void ShootPlacement(long number) {
    const double x = gExtent * (2 * Unit(gSeed, number, 2) - 1), y = gExtent * (2 * Unit(gSeed, number, 3) - 1);
    Beam beam{"geantino", 1 * GeV};
    if (gBeam == "physics") {
      static const Beam beams[] = {{"e-", 1 * GeV}, {"pi+", 3 * GeV}, {"proton", 2 * GeV}, {"mu-", 1 * GeV}, {"gamma", 500 * MeV}};
      beam = beams[number % 5];
    }
    const long kind = gBeam == "geantino" ? number % 4 : 1;
    if (kind == 0) {  // along z through the lattice of cell faces
      Shoot(beam, G4ThreeVector(std::floor(x / 5.) * 5., std::floor(y / 5.) * 5., -400.), G4ThreeVector(0, 0, 1));
    } else if (kind == 1) {  // near z, tilted
      const G4ThreeVector towards(0.3 * (2 * Unit(gSeed, number, 4) - 1), 0.3 * (2 * Unit(gSeed, number, 5) - 1), 1.);
      Shoot(beam, G4ThreeVector(x, y, -gStackHalfZ - 1.), towards.unit());
    } else if (kind == 2) {  // sideways, in the plane of a face between layers
      const double z = gStackHalfZ * (2. * std::floor(16. * Unit(gSeed, number, 4)) / 16. - 1.);
      Shoot(beam, G4ThreeVector(-400., y, z), G4ThreeVector(1, 0, 0));
    } else {  // any direction from the middle of the stack
      const double cosine = 2 * Unit(gSeed, number, 4) - 1, phi = CLHEP::twopi * Unit(gSeed, number, 5), sine = std::sqrt(1 - cosine * cosine);
      Shoot(beam, G4ThreeVector(0.5 * x, 0.5 * y, 0.3 * gStackHalfZ), G4ThreeVector(sine * std::cos(phi), sine * std::sin(phi), cosine));
    }
  }
  G4ParticleGun fGun;
};

class Stepping : public G4UserSteppingAction {
 public:
  void UserSteppingAction(const G4Step* step) override {
    const G4StepPoint *pre = step->GetPreStepPoint(), *post = step->GetPostStepPoint();
    const G4Track* track = step->GetTrack();
    const G4VProcess* definer = post->GetProcessDefinedStep();
    const std::string process = definer ? definer->GetProcessName() : "none";
    const std::string from = Chain(pre->GetTouchable());
    const std::string to = post->GetTouchable() && post->GetPhysicalVolume() ? Chain(post->GetTouchable()) : "out";
    const G4ThreeVector a = pre->GetPosition(), b = post->GetPosition(), direction = post->GetMomentumDirection();
    const double values[] = {a.x(), a.y(), a.z(), b.x(), b.y(), b.z(), direction.x(), direction.y(), direction.z(), step->GetStepLength(),
                             step->GetTotalEnergyDeposit(), pre->GetKineticEnergy(), post->GetKineticEnergy(), post->GetGlobalTime()};
    gTraceHash.Whole(track->GetTrackID());
    gTraceHash.Whole(track->GetParentID());
    gTraceHash.Whole(track->GetDefinition()->GetPDGEncoding());
    gTraceHash.Whole(track->GetTrackStatus());
    gTraceHash.Text(process);
    for (double value : values) gTraceHash.Real(value);
    gNavigationHash.Whole(track->GetTrackID());
    gNavigationHash.Text(from);
    gNavigationHash.Text(to);
    const std::vector<unsigned long> state = G4Random::getTheEngine()->put();
    gRandomHash.Bytes(state.data(), state.size() * sizeof(unsigned long));
    ++gStepCount;
    if (gCurrentEvent == gTraceEvent) {
      gTrace << track->GetTrackID() << ' ' << track->GetDefinition()->GetParticleName() << ' ' << process << ' ' << from << ' ' << to;
      for (double value : values) gTrace << ' ' << Hex(value);
      gTrace << ' ' << Hex(pre->GetSafety()) << ' ' << Hex(post->GetSafety()) << ' ' << track->GetCurrentStepNumber() << ' ' << HexWord(gRandomHash.state) << '\n';
    }
    if (gKill) RecordKill(step);
  }
};

class Events : public G4UserEventAction {
 public:
  void BeginOfEventAction(const G4Event* event) override {
    gCurrentEvent = event->GetEventID();
    gCells.clear();
    gTraceHash = Fnv();
    gRandomHash = Fnv();
    gNavigationHash = Fnv();
    gStepCount = 0;
  }
  void EndOfEventAction(const G4Event* event) override {
    std::ostringstream line;
    const std::vector<unsigned long> state = G4Random::getTheEngine()->put();
    Fnv last;
    last.Bytes(state.data(), state.size() * sizeof(unsigned long));
    line << "{\"event\": " << event->GetEventID() << ", \"steps\": " << gStepCount << ", \"trace\": \"" << HexWord(gTraceHash.state) << "\", \"navigation\": \"" << HexWord(gNavigationHash.state)
         << "\", \"random\": \"" << HexWord(gRandomHash.state) << "\", \"random_end\": \"" << HexWord(last.state) << "\", \"cells\": [";
    bool first = true;
    for (const auto& [chain, cell] : gCells) {
      line << (first ? "" : ", ") << "[\"" << chain << "\", \"" << Hex(cell.deposit) << "\", \"" << Hex(cell.length) << "\", " << cell.steps << "]";
      first = false;
    }
    line << "]}";
    gEvents.push_back(line.str());
  }
};

class Actions : public G4VUserActionInitialization {
 public:
  void Build() const override {
    SetUserAction(new Primaries());
    SetUserAction(new Stepping());
    SetUserAction(new Events());
  }
};

std::string ProcessList(const char* name) {
  std::string text;
  G4ProcessVector* processes = G4ParticleTable::GetParticleTable()->FindParticle(name)->GetProcessManager()->GetProcessList();
  for (std::size_t k = 0; k < processes->size(); ++k) text += (k ? " " : "") + (*processes)[k]->GetProcessName();
  return text;
}

int Usage() {
  std::puts("{\"status\": \"rejected\", \"message\": \"usage: s3_steps gb19 OUT HOOK SEED EVENTS | gb20 OUT LAYOUT IMPL BEAM SEED EVENTS | gb21 OUT VARIANT SEED EVENTS\"}");
  return 2;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 3) return Usage();
  gMode = argv[1];
  const std::string target = argv[2];
  int next = 3;
  if (gMode == "gb19" && argc >= 6) {
    gHook = argv[next++];
  } else if (gMode == "gb20" && argc >= 8) {
    gLayout = argv[next++];
    gImpl = argv[next++];
    gBeam = argv[next++];
  } else if (gMode == "gb21" && argc >= 6) {
    gVariant = argv[next++];
  } else {
    return Usage();
  }
  gSeed = std::strtoull(argv[next++], nullptr, 10);
  const long events = std::strtol(argv[next++], nullptr, 10);
  if (argc == next + 2) {
    gTraceEvent = std::strtol(argv[next], nullptr, 10);
    gTrace.open(argv[next + 1]);
  }

  auto* manager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::SerialOnly);
  if (gMode == "gb19") manager->SetUserInitialization(new HookDetector());
  else if (gMode == "gb20") manager->SetUserInitialization(new PlacementDetector());
  else manager->SetUserInitialization(new KillDetector());
  auto* physics = new FTFP_BERT(0);
  if (gMode == "gb19" && gHook != "none" && gHook != "region_only") physics->RegisterPhysics(new HookPhysics());
  if (gMode == "gb21") physics->RegisterPhysics(new KillPhysics());
  if (gVariant == "pixe") {  // set after the EM constructor, which resets them (GB14)
    auto* parameters = G4EmParameters::Instance();
    parameters->SetFluo(true);
    parameters->SetAuger(true);
    parameters->SetPixe(true);
    parameters->SetDeexcitationIgnoreCut(true);
    parameters->SetDeexActiveRegion("DefaultRegionForTheWorld", true, true, true);
    G4LossTableManager::Instance()->SetAtomDeexcitation(new G4UAtomicDeexcitation());
  }
  manager->SetUserInitialization(physics);
  manager->SetUserInitialization(new Actions());
  manager->Initialize();
  manager->BeamOn(events);

  std::ofstream file(target);
  file << "{\"status\": \"measured\", \"mode\": \"" << gMode << "\", \"seed\": " << gSeed << ",\n";
  if (gMode == "gb19") {
    file << "\"hook\": \"" << gHook << "\", \"hook_counts\": {\"applicable\": " << gHookCounts.applicable << ", \"trigger\": " << gHookCounts.trigger << ", \"do_it\": " << gHookCounts.doIt << "},\n";
    file << "\"processes\": {\"e-\": \"" << ProcessList("e-") << "\", \"gamma\": \"" << ProcessList("gamma") << "\", \"proton\": \"" << ProcessList("proton") << "\"},\n";
  }
  if (gMode == "gb20") {
    std::ostringstream rows;
    bool first = true;
    const std::string scan = NavigationScan();
    WriteBack(gWorld->GetLogicalVolume(), "World:0", rows, first);
    file << "\"layout\": \"" << gLayout << "\", \"impl\": \"" << gImpl << "\", \"beam\": \"" << gBeam << "\",\n\"tree\": [" << rows.str() << "],\n\"scan\": [" << scan << "],\n";
  }
  if (gMode == "gb21") {
    file << "\"variant\": \"" << gVariant << "\", \"defined_without_do_it\": " << gDefinedWithoutDoIt << ", \"processes\": {\"e-\": \"" << ProcessList("e-") << "\"},\n\"kills\": [\n";
    for (std::size_t k = 0; k < gKillRows.size(); ++k) file << (k ? ",\n" : "") << gKillRows[k];
    file << "],\n";
  }
  file << "\"events\": [\n";
  for (std::size_t k = 0; k < gEvents.size(); ++k) file << (k ? ",\n" : "") << gEvents[k];
  file << "]}\n";
  file.close();
  delete manager;
  std::puts("{\"status\": \"ok\"}");
  return 0;
}
