// g4sim_run/GeometryCheck.cc: run.mode geometry-check (g4sim plan, Section 19.2, S2): the volume tree of a new specification from its IR, with
// fields set explicitly in pre-order, one geantino event to trigger the probe, and the write-back. Written from the Geant4 11.4 API; no example
// code copied or adapted. No accounting and no scorers: those come in S3.
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

#include "G4Box.hh"
#include "G4ChordFinder.hh"
#include "G4Event.hh"
#include "G4Field.hh"
#include "G4FieldManager.hh"
#include "G4Geantino.hh"
#include "G4GeometryTolerance.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleGun.hh"
#include "G4ProductionCuts.hh"
#include "G4Region.hh"
#include "G4RotationMatrix.hh"
#include "G4Run.hh"
#include "G4RunManager.hh"
#include "G4RunManagerFactory.hh"
#include "G4SystemOfUnits.hh"
#include "G4Threading.hh"
#include "G4UniformMagField.hh"
#include "G4UserRunAction.hh"
#include "G4VUserActionInitialization.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "MiniJson.hh"
#include "SimPhysics.hh"
#include "WriteBack.hh"

namespace {

using minijson::Value;
constexpr const char* kWorld = "world";
constexpr const char* kNoField = "none";
constexpr const char* kDefaultRegion = "default";

std::string Control() {
  const char* value = std::getenv("G4SIM_BUILDER_CONTROL");
  return value ? value : "";
}

double Decimal(const Value& value) { return value.isNumber() ? value.num : std::strtod(value.str.c_str(), nullptr); }

G4Material* NewMaterial(const std::string& name, const Value& materials) {
  if (auto* found = G4Material::GetMaterial(name, false)) return found;
  auto* nist = G4NistManager::Instance();
  if (name.rfind("G4_", 0) == 0) {
    if (auto* made = nist->FindOrBuildMaterial(name, false)) return made;
    throw std::runtime_error("unknown NIST material " + name);
  }
  const Value& definition = materials.at(name, "materials");
  G4Material* material = nullptr;
  if (definition.has("base")) {
    G4Material* base = nist->FindOrBuildMaterial(definition.obj.at("base").str, false);
    if (!base) throw std::runtime_error("material " + name + ": unknown base");
    material = definition.has("density_g_cm3") ? new G4Material(name, Decimal(definition.obj.at("density_g_cm3")) * g / cm3, base)
                                               : new G4Material(name, base->GetDensity(), base);
  } else {
    const auto& composition = definition.at("composition", "material").obj;
    material = new G4Material(name, Decimal(definition.at("density_g_cm3", "material")) * g / cm3, static_cast<G4int>(composition.size()));
    for (const auto& [symbol, fraction] : composition) material->AddElement(nist->FindOrBuildElement(symbol), Decimal(fraction));
  }
  return material;
}

class NewDetector : public G4VUserDetectorConstruction {
 public:
  explicit NewDetector(const Value& physical) : fPhysical(physical) {}

  G4VPhysicalVolume* Construct() override {
    const Value& materials = fPhysical.at("materials", "physical");
    std::map<std::string, std::vector<G4LogicalVolume*>> regions;
    for (const auto& [name, node] : fPhysical.at("templates", "physical").obj) {
      const auto& half = node.at("half_mm", "template").array("half_mm");
      auto* box = new G4Box(name, Decimal(half[0]), Decimal(half[1]), Decimal(half[2]));
      auto* logical = new G4LogicalVolume(box, NewMaterial(node.at("material", "template").str, materials), name);
      fLogicals[name] = logical;
      const std::string& region = node.at("region", "template").str;
      if (region != kDefaultRegion) regions[region].push_back(logical);
    }
    auto* world = new G4PVPlacement(nullptr, {}, fLogicals.at(kWorld), kWorld, nullptr, false, 0, true);
    for (const auto& placement : fPhysical.at("placements", "physical").array("placements")) {
      const auto& c = placement.at("centre_mm", "placement").array("centre_mm");
      G4RotationMatrix* rotation = nullptr;
      const Value& rows = placement.at("rotation", "placement");
      if (rows.isArray()) {
        double m[3][3];
        for (int i = 0; i < 3; ++i)
          for (int j = 0; j < 3; ++j) m[i][j] = Decimal(rows.arr[i].arr[j]);
        rotation = new G4RotationMatrix(G4Rep3x3(m[0][0], m[0][1], m[0][2], m[1][0], m[1][1], m[1][2], m[2][0], m[2][1], m[2][2]));
        if (Control() == "transposed_rotation") *rotation = rotation->inverse();  // negative test: the other rotation convention
      }
      const std::string& name = placement.at("template", "placement").str;
      const std::string& mother = placement.at("mother", "placement").str;
      fChildren[mother].push_back(name);
      new G4PVPlacement(rotation, G4ThreeVector(Decimal(c[0]), Decimal(c[1]), Decimal(c[2])), fLogicals.at(name), name, fLogicals.at(mother), false,
                        static_cast<G4int>(placement.at("copy_number", "placement").num), true);
    }
    for (const auto& [name, logicals] : regions) {
      auto* region = new G4Region(name);
      region->SetProductionCuts(new G4ProductionCuts());
      for (auto* logical : logicals) region->AddRootLogicalVolume(logical);
    }
    return world;
  }

  // Once on the master and once on each worker: field managers are thread-local (GB3). "No field" is a manager with no detector field.
  void ConstructSDandField() override {
    std::map<std::string, G4FieldManager*> managers;
    std::set<std::string> done;
    std::ofstream record("field-managers.thread" + std::to_string(G4Threading::G4GetThreadId()) + ".txt");
    Assign(kWorld, managers, done, record);
  }

 private:
  G4FieldManager* Manager(const std::string& name, std::map<std::string, G4FieldManager*>& managers) {
    auto found = managers.find(name);
    if (found != managers.end()) return found->second;
    G4FieldManager* manager = nullptr;
    if (name == kNoField) {
      manager = new G4FieldManager(static_cast<G4Field*>(nullptr));
    } else {
      const auto& b = fPhysical.at("fields", "physical").at(name, "fields").at("b_tesla", "field").array("b_tesla");
      auto* field = new G4UniformMagField(G4ThreeVector(Decimal(b[0]) * tesla, Decimal(b[1]) * tesla, Decimal(b[2]) * tesla));
      manager = new G4FieldManager(field);
      manager->CreateChordFinder(field);
    }
    return managers[name] = manager;
  }

  void Assign(const std::string& name, std::map<std::string, G4FieldManager*>& managers, std::set<std::string>& done, std::ofstream& record) {
    if (!done.insert(name).second) return;
    const std::string& field = fPhysical.at("templates", "physical").at(name, "templates").at("field", "template").str;
    // G4SIM_BUILDER_CONTROL=mother_only is the negative test of Section 15.1: a logical with no field of its own is left to propagation
    if (Control() == "mother_only" && field == kNoField) {
      if (name == kWorld) fLogicals.at(name)->SetFieldManager(Manager(field, managers), true);
    } else {
      fLogicals.at(name)->SetFieldManager(Manager(field, managers), Control() == "mother_only");
    }
    const G4FieldManager* actual = fLogicals.at(name)->GetFieldManager();
    record << name << ' ' << (actual && actual->GetDetectorField() ? "field" : kNoField) << ' ' << field << '\n';
    for (const auto& child : fChildren[name]) Assign(child, managers, done, record);
  }

  const Value& fPhysical;
  std::map<std::string, G4LogicalVolume*> fLogicals;
  std::map<std::string, std::vector<std::string>> fChildren;
};

class Geantino : public G4VUserPrimaryGeneratorAction {
 public:
  Geantino() : fGun(new G4ParticleGun(1)) {
    fGun->SetParticleDefinition(G4Geantino::Definition());
    fGun->SetParticleEnergy(1. * GeV);
    fGun->SetParticleMomentumDirection({0, 0, 1});
  }
  void GeneratePrimaries(G4Event* event) override { fGun->GeneratePrimaryVertex(event); }

 private:
  G4ParticleGun* fGun;
};

class ProbeRun : public G4UserRunAction {
 public:
  void BeginOfRunAction(const G4Run*) override {
    if (!G4Threading::IsMasterThread()) return;
    g4sim::WriteBack("g4sim_run", "./probe.json", {});
    std::ofstream("tolerance.txt") << G4GeometryTolerance::GetInstance()->GetSurfaceTolerance() << '\n';
  }
};

class Actions : public G4VUserActionInitialization {
 public:
  void BuildForMaster() const override { SetUserAction(new ProbeRun()); }
  void Build() const override {
    SetUserAction(new ProbeRun());
    SetUserAction(new Geantino());
  }
};

}  // namespace

int GeometryCheck(const Value& ir, const Value& card) {
  const Value& physics = card.at("physics", "run card");
  const Value& run = card.at("run", "run card");
  const int threads = run.has("threads") ? static_cast<int>(run.obj.at("threads").num) : 2;
  auto* manager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::MTOnly, threads);
  manager->SetUserInitialization(new NewDetector(ir.at("physical", "ir")));
  std::string error;
  const auto text = [&](const char* key) { return physics.has(key) ? physics.obj.at(key).str : std::string(); };
  G4VModularPhysicsList* list = g4sim::BuildPhysicsList(text("reference_list"), text("em_constructor"), true, false,
                                                        Decimal(physics.at("cuts_mm", "physics").at("default", "cuts")), error);
  if (!list) {
    std::cerr << error << std::endl;
    return 2;
  }
  manager->SetUserInitialization(list);
  manager->SetUserInitialization(new Actions());
  manager->Initialize();
  manager->BeamOn(1);
  delete manager;
  return 0;
}
