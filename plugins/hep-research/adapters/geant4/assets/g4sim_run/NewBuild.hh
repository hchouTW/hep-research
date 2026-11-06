// NewBuild.hh: the volume tree of a new specification from its IR, shared by the geometry check and the run (g4sim plan, Sections 7, 8.1).
#ifndef G4SIM_NEWBUILD_HH
#define G4SIM_NEWBUILD_HH

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

#include "G4Box.hh"
#include "G4ChordFinder.hh"
#include "G4FieldManager.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4Polyhedra.hh"
#include "G4ProductionCuts.hh"
#include "G4Region.hh"
#include "G4RotationMatrix.hh"
#include "G4SystemOfUnits.hh"
#include "G4Threading.hh"
#include "G4Trd.hh"
#include "G4Tubs.hh"
#include "G4UniformMagField.hh"
#include "G4UserLimits.hh"
#include "G4VUserDetectorConstruction.hh"
#include "MiniJson.hh"

namespace g4sim {

using minijson::Value;
constexpr const char* kWorld = "world";
constexpr const char* kNoField = "none";
constexpr const char* kDefaultRegion = "default";

inline std::string Control() {
  const char* value = std::getenv("G4SIM_BUILDER_CONTROL");
  return value ? value : "";
}

inline double Now() { return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count(); }

inline double Decimal(const Value& value) { return value.isNumber() ? value.num : std::strtod(value.str.c_str(), nullptr); }

inline G4Material* NewMaterial(const std::string& name, const Value& materials) {
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
  if (definition.has("ionisation")) {
    const Value& ionisation = definition.obj.at("ionisation");
    if (ionisation.has("birks_mm_per_MeV")) material->GetIonisation()->SetBirksConstant(Decimal(ionisation.obj.at("birks_mm_per_MeV")) * mm / MeV);
    if (ionisation.has("mean_excitation_eV")) material->GetIonisation()->SetMeanExcitationEnergy(Decimal(ionisation.obj.at("mean_excitation_eV")) * eV);
  }
  return material;
}

// The solid of a template; the IR already holds what G4 takes, so nothing is derived here (the apothem of a prism, for one, GB23).
inline G4VSolid* NewSolid(const std::string& name, const Value& node) {
  const std::string& shape = node.at("shape", "template").str;
  if (shape == "box") {
    const auto& half = node.at("half_mm", "template").array("half_mm");
    return new G4Box(name, Decimal(half[0]), Decimal(half[1]), Decimal(half[2]));
  }
  const Value& solid = node.at("solid", "template");
  const auto length = [&](const char* key) { return Decimal(solid.at(key, "solid")); };
  if (shape == "trd") return new G4Trd(name, length("dx1_mm"), length("dx2_mm"), length("dy1_mm"), length("dy2_mm"), length("dz_mm"));
  if (shape == "tube")
    return new G4Tubs(name, length("rmin_mm"), length("rmax_mm"), length("dz_mm"), length("phi_start_deg") * deg, length("phi_span_deg") * deg);
  if (shape == "polygon_prism") {
    const double z[2] = {-length("dz_mm"), length("dz_mm")}, inner[2] = {0., 0.}, outer[2] = {length("apothem_mm"), length("apothem_mm")};
    return new G4Polyhedra(name, 0., CLHEP::twopi, static_cast<G4int>(solid.at("sides", "solid").num), 2, z, inner, outer);
  }
  throw std::runtime_error("template " + name + ": shape " + shape + " is not built");
}

class NewDetector : public G4VUserDetectorConstruction {
 public:
  using Attach = std::function<void(const std::map<std::string, G4LogicalVolume*>&)>;
  NewDetector(const Value& physical, const Value& cuts, Attach attach = nullptr, const Value* limits = nullptr) : fPhysical(physical), fCuts(cuts), fAttach(std::move(attach)), fLimits(limits) {}

  G4VPhysicalVolume* Construct() override {
    const Value& materials = fPhysical.at("materials", "physical");
    std::map<std::string, std::vector<G4LogicalVolume*>> regions;
    for (const auto& [name, node] : fPhysical.at("templates", "physical").obj) {
      auto* logical = new G4LogicalVolume(NewSolid(name, node), NewMaterial(node.at("material", "template").str, materials), name);
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
      // G4SIM_BUILDER_CONTROL=overlap is the negative test of Section 15.1: the IR layer refused such a placement, so the shift is applied here
      const double shift = Control() == "overlap" && static_cast<G4int>(placement.at("copy_number", "placement").num) == 1 ? -10. : 0.;
      fChildren[mother].push_back(name);
      new G4PVPlacement(rotation, G4ThreeVector(Decimal(c[0]) + shift, Decimal(c[1]), Decimal(c[2])), fLogicals.at(name), name, fLogicals.at(mother), false,
                        static_cast<G4int>(placement.at("copy_number", "placement").num), !std::getenv("G4SIM_NO_OVERLAP_CHECK"));
    }
    std::printf("G4SIM_TREE_BUILT %.3f\n", Now());
    std::fflush(stdout);
    for (const auto& [name, logicals] : regions) {
      auto* region = new G4Region(name);
      auto* cuts = new G4ProductionCuts();
      if (fCuts.has("regions") && fCuts.obj.at("regions").has(name)) cuts->SetProductionCut(Decimal(fCuts.obj.at("regions").obj.at(name)) * mm);
      else cuts->SetProductionCut(Decimal(fCuts.at("default", "cuts")) * mm);
      region->SetProductionCuts(cuts);
      for (auto* logical : logicals) region->AddRootLogicalVolume(logical);
      if (fLimits && fLimits->has(name))  // separated mode: only the maximum step (Section 8.4), which check-spec enforces
        for (auto* logical : logicals) logical->SetUserLimits(new G4UserLimits(Decimal(fLimits->obj.at(name).at("max_step_mm", "user_limits")) * mm));
    }
    return world;
  }

  // Once on the master and once on each worker: field managers are thread-local (GB3). "No field" is a manager with no detector field.
  void ConstructSDandField() override {
    std::map<std::string, G4FieldManager*> managers;
    std::set<std::string> done;
    std::ofstream record("field-managers.thread" + std::to_string(G4Threading::G4GetThreadId()) + ".txt");
    Assign(kWorld, managers, done, record);
    if (fAttach) fAttach(fLogicals);
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
  const Value& fCuts;
  Attach fAttach;
  const Value* fLimits;
  std::map<std::string, G4LogicalVolume*> fLogicals;
  std::map<std::string, std::vector<std::string>> fChildren;
};


}  // namespace g4sim

#endif
