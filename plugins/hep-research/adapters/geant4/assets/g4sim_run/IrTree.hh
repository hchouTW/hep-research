// g4sim_run/IrTree.hh: the volume tree of a legacy run from the IR's legacy block (g4sim plan, Sections 7.4, 8.1). Geant4 API only;
// written from the Geant4 API (no example code copied or adapted).
//
// Every number comes from a float.hex() string of the re-acquisition record, read exactly by strtod. Lengths are the record's own; a material's
// density and A are divided by their units there, so they are multiplied back and the exact double recovered (RecoveredValues). Logical
// volumes are made in the record's id order and placements in the record's order, so the stores, and the probe's write-back, are the same.
#ifndef G4SIM_RUN_IRTREE_HH
#define G4SIM_RUN_IRTREE_HH

#include <cfloat>
#include <cmath>
#include <cstdlib>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

#include "G4Box.hh"
#include "G4Element.hh"
#include "G4IonisParamMat.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ProductionCuts.hh"
#include "G4Region.hh"
#include "G4SystemOfUnits.hh"
#include "G4UserLimits.hh"
#include "MiniJson.hh"

namespace g4sim {

inline double HexDouble(const minijson::Value& value, const std::string& where) { return std::strtod(value.string(where).c_str(), nullptr); }

struct IrTree {
  std::map<std::string, G4LogicalVolume*> logicals;  // by name
  std::vector<G4LogicalVolume*> by_id;
  G4VPhysicalVolume* world = nullptr;
};

struct MaterialValues {
  double density, a;  // internal units; a is 0 for a mixture
};

inline bool SameDerived(const G4Material& material, const minijson::Value& record) {
  const auto& elements = record.at("elements", "material").array("material.elements");
  if (material.GetNumberOfElements() != elements.size()) return false;
  for (std::size_t i = 0; i < elements.size(); ++i) {
    const G4Element* element = material.GetElement(static_cast<G4int>(i));
    if (element->GetA() / (g / mole) != HexDouble(elements[i].at("a_g_mole", "element"), "a")) return false;
    if (elements.size() == 1 && element->GetSymbol() != elements[i].at("symbol", "element").str) return false;
  }
  return material.GetDensity() / (g / cm3) == HexDouble(record.at("density_g_cm3", "material"), "density") && material.GetRadlen() == HexDouble(record.at("radiation_length_mm", "material"), "radiation length") &&
         material.GetNuclearInterLength() == HexDouble(record.at("nuclear_interaction_length_mm", "material"), "interaction length") &&
         material.GetElectronDensity() == HexDouble(record.at("electron_density_per_mm3", "material"), "electron density");
}

inline G4Material* MakeMaterial(const std::string& name, const minijson::Value& record, const MaterialValues& values) {
  const std::string& text = record.at("state", "material").string("material.state");
  G4State state = text == "gas" ? kStateGas : text == "liquid" ? kStateLiquid : text == "solid" ? kStateSolid : kStateUndefined;
  double temperature = HexDouble(record.at("temperature_K", "material"), "temperature");
  double pressure = HexDouble(record.at("pressure_Pa", "material"), "pressure") * pascal;
  const auto& elements = record.at("elements", "material").array("material.elements");
  if (elements.size() == 1)
    return new G4Material(name, HexDouble(elements[0].at("z", "element"), "z"), values.a, values.density, state, temperature, pressure);
  auto* material = new G4Material(name, values.density, static_cast<G4int>(elements.size()), state, temperature, pressure);
  // the old programs mix the NIST material of each element, in this order, so its components and the table's order are theirs
  for (const auto& element : elements) {
    const std::string nistName = "G4_" + element.at("symbol", "element").string("element.symbol");
    G4Material* component = G4NistManager::Instance()->FindOrBuildMaterial(nistName, false);
    if (!component) throw std::runtime_error("material " + name + ": no NIST material " + nistName);
    material->AddMaterial(component, HexDouble(element.at("mass_fraction", "element"), "mass fraction"));
  }
  return material;
}

// Takes a trial material back out of Geant4's tables, so the indices of the materials that follow are the old program's. An element Geant4
// built for it from its NIST data stays: the old program built the same one here, and NIST's builder keeps a pointer to it.
inline void Forget(G4Material* material, std::size_t materials, const std::string& trialName) {
  delete material;
  G4Material::GetMaterialTable()->resize(materials);
  auto* table = const_cast<G4ElementTable*>(G4Element::GetElementTable());
  while (!table->empty() && table->back()->GetName().rfind(trialName, 0) == 0) {
    delete table->back();
    table->resize(table->size() - 1);
  }
}

// The record holds density and A divided by their units, so multiplying back can land one ulp from the old program's double. The record's
// derived quantities tell which neighbour it was (GB18): a value that reproduces them all is the one.
inline MaterialValues RecoveredValues(const std::string& name, const minijson::Value& record) {
  const auto& elements = record.at("elements", "material").array("material.elements");
  const double recorded = HexDouble(record.at("density_g_cm3", "material"), "density");
  double density = recorded * g / cm3;
  if (elements.size() > 1) {  // a mixture is built once, because its NIST components stay in the tables: the density alone decides
    for (int steps : {0, -1, 1, -2, 2}) {
      double trial = density;
      for (int i = 0; i < std::abs(steps); ++i) trial = std::nextafter(trial, steps > 0 ? DBL_MAX : 0.);
      if (trial / (g / cm3) == recorded) return {trial, 0.};
    }
    throw std::runtime_error("material " + name + ": no density near the record divides back to it");
  }
  double a = HexDouble(elements[0].at("a_g_mole", "element"), "a") * g / mole;
  for (int stepsDensity : {0, -1, 1, -2, 2})
    for (int stepsA : {0, -1, 1, -2, 2}) {
      MaterialValues trial{density, a};
      for (int i = 0; i < std::abs(stepsDensity); ++i) trial.density = std::nextafter(trial.density, stepsDensity > 0 ? DBL_MAX : 0.);
      for (int i = 0; i < std::abs(stepsA); ++i) trial.a = std::nextafter(trial.a, stepsA > 0 ? DBL_MAX : 0.);
      const std::size_t materials = G4Material::GetMaterialTable()->size();
      G4Material* made = MakeMaterial(name + "_trial", record, trial);
      bool same = SameDerived(*made, record);
      Forget(made, materials, name + "_trial");
      if (same) return trial;
    }
  throw std::runtime_error("material " + name + ": no value near the record reproduces its derived quantities (GB18)");
}

// A G4_ name is NIST's; any other is rebuilt from the record alone (Section 7.4, GB18).
inline G4Material* LegacyMaterial(const std::string& name, const minijson::Value& legacy) {
  if (auto* found = G4Material::GetMaterial(name, false)) return found;
  if (name.rfind("G4_", 0) == 0) {
    if (auto* nist = G4NistManager::Instance()->FindOrBuildMaterial(name, false)) return nist;
    throw std::runtime_error("unknown NIST material " + name);
  }
  for (const auto& record : legacy.at("materials", "legacy").array("legacy.materials")) {
    if (record.at("name", "material").string("material.name") != name) continue;
    G4Material* material = MakeMaterial(name, record, RecoveredValues(name, record));
    if (!SameDerived(*material, record)) throw std::runtime_error("material " + name + ": the rebuilt material differs from the record (GB18)");
    // compared in the record's unit: multiplying the record back could overwrite Geant4's own value with one a rounding away
    const double excitation = HexDouble(record.at("mean_excitation_energy_eV", "material"), "I");
    if (material->GetIonisation()->GetMeanExcitationEnergy() / eV != excitation) material->GetIonisation()->SetMeanExcitationEnergy(excitation * eV);
    return material;
  }
  throw std::runtime_error("material " + name + " is not in the legacy block");
}

inline G4UserLimits* LegacyLimits(const minijson::Value& limits) {
  return new G4UserLimits(HexDouble(limits.at("max_step_mm", "limits"), "max step"), HexDouble(limits.at("max_track_length_mm", "limits"), "length"),
                          HexDouble(limits.at("max_time_ns", "limits"), "time"), HexDouble(limits.at("min_ekin_MeV", "limits"), "ekin"),
                          HexDouble(limits.at("min_range_mm", "limits"), "range"));
}

inline IrTree BuildLegacyTree(const minijson::Value& legacy) {
  IrTree tree;
  std::map<std::string, G4UserLimits*> shared;
  // in the record's order, which is Geant4's table: logical volumes are numbered differently, and the table's order is the old program's
  for (const auto& record : legacy.at("materials", "legacy").array("legacy.materials")) LegacyMaterial(record.at("name", "material").str, legacy);
  for (const auto& record : legacy.at("logical_volumes", "legacy").array("legacy.logical_volumes")) {
    const auto& solid = record.at("solid", "logical");
    if (solid.at("type", "solid").string("solid.type") != "G4Box") throw std::runtime_error("a legacy run has only boxes");
    const auto& p = solid.at("parameters", "solid");
    const std::string& name = record.at("name", "logical").string("logical.name");
    auto* box = new G4Box(name, HexDouble(p.at("half_x_mm", "box"), "x"), HexDouble(p.at("half_y_mm", "box"), "y"), HexDouble(p.at("half_z_mm", "box"), "z"));
    auto* logical = new G4LogicalVolume(box, LegacyMaterial(record.at("material", "logical").string("logical.material"), legacy), name);
    const auto& limits = record.at("user_limits", "logical");
    if (limits.isObject()) {
      std::string key;
      for (const char* name : {"max_step_mm", "max_track_length_mm", "max_time_ns", "min_ekin_MeV", "min_range_mm"}) key += limits.at(name, "limits").str + " ";
      auto found = shared.find(key);
      logical->SetUserLimits(found != shared.end() ? found->second : (shared[key] = LegacyLimits(limits)));
    }
    tree.logicals[name] = logical;
    tree.by_id.push_back(logical);
  }
  for (const auto& record : legacy.at("positions", "legacy").array("legacy.positions")) {
    auto* logical = tree.by_id.at(static_cast<std::size_t>(record.at("logical", "placement").number("placement.logical")));
    const auto& mother = record.at("mother_logical", "placement");
    const auto& t = record.at("translation_mm", "placement").array("translation");
    G4ThreeVector translation(HexDouble(t[0], "x"), HexDouble(t[1], "y"), HexDouble(t[2], "z"));
    auto* placed = new G4PVPlacement(nullptr, translation, logical, record.at("name", "placement").string("placement.name"),
                                     mother.isNumber() ? tree.by_id.at(static_cast<std::size_t>(mother.num)) : nullptr, false,
                                     static_cast<G4int>(record.at("copy_number", "placement").number("placement.copy_number")), true);
    if (!mother.isNumber()) tree.world = placed;
  }
  for (const auto& record : legacy.at("regions", "legacy").array("legacy.regions")) {
    const std::string& name = record.at("name", "region").string("region.name");
    if (name.rfind("DefaultRegion", 0) == 0) continue;
    auto* region = new G4Region(name);
    auto* cuts = new G4ProductionCuts();
    for (const auto& [particle, value] : record.at("cuts_mm", "region").obj) cuts->SetProductionCut(HexDouble(value, "cut"), particle);
    region->SetProductionCuts(cuts);
    for (const auto& root : record.at("root_volumes", "region").array("region.root_volumes")) region->AddRootLogicalVolume(tree.logicals.at(root.str));
  }
  return tree;
}

}  // namespace g4sim

#endif
