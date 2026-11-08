// NewBuild.hh: the volume tree of a new specification from its IR, shared by the geometry check and the run (g4sim plan, Sections 7, 8.1).
#ifndef G4SIM_NEWBUILD_HH
#define G4SIM_NEWBUILD_HH

#include <array>
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
#include "G4Cons.hh"
#include "G4Polycone.hh"
#include "G4Polyhedra.hh"
#include "G4Sphere.hh"
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
#include "FieldMap.hh"
#include "Optics.hh"
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
  } else if (definition.has("components")) {  // S7: a mixture of materials by mass fraction, as an XTR envelope's foil-gas mixture
    const auto& components = definition.obj.at("components").array("components");
    material = new G4Material(name, Decimal(definition.at("density_g_cm3", "material")) * g / cm3, static_cast<G4int>(components.size()));
    for (const auto& component : components)
      material->AddMaterial(NewMaterial(component.at("material", "component").str, materials), Decimal(component.at("mass_fraction", "component")));
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
  if (auto* table = OpticalTable(definition)) material->SetMaterialPropertiesTable(table);  // S7: optics, only inside optical_scope
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
  const auto angle = [&](const char* key) { return Decimal(solid.at(key, "solid")) * deg; };
  if (shape == "cone")
    return new G4Cons(name, length("rmin1_mm"), length("rmax1_mm"), length("rmin2_mm"), length("rmax2_mm"), length("dz_mm"), angle("phi_start_deg"), angle("phi_span_deg"));
  if (shape == "sphere_section")
    return new G4Sphere(name, length("rmin_mm"), length("rmax_mm"), angle("phi_start_deg"), angle("phi_span_deg"), angle("theta_start_deg"), angle("theta_span_deg"));
  if (shape == "polycone" || shape == "polyhedra") {  // the IR's polyhedra radii are already apothems, as G4Polyhedra takes them (GB23)
    const bool cone = shape == "polycone";
    const auto& zs = solid.at("z_mm", "solid").array("z_mm");
    const auto& inner = solid.at(cone ? "rmin_mm" : "apothem_rmin_mm", "solid").array("rmin");
    const auto& outer = solid.at(cone ? "rmax_mm" : "apothem_rmax_mm", "solid").array("rmax");
    std::vector<double> z, rmin, rmax;
    for (std::size_t i = 0; i < zs.size(); ++i) z.push_back(Decimal(zs[i])), rmin.push_back(Decimal(inner[i])), rmax.push_back(Decimal(outer[i]));
    const G4int planes = static_cast<G4int>(z.size());
    if (cone) return new G4Polycone(name, angle("phi_start_deg"), angle("phi_span_deg"), planes, z.data(), rmin.data(), rmax.data());
    return new G4Polyhedra(name, angle("phi_start_deg"), angle("phi_span_deg"), static_cast<G4int>(solid.at("sides", "solid").num), planes, z.data(), rmin.data(), rmax.data());
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
    fWorld = world;
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
      fPlaced[name].push_back(new G4PVPlacement(rotation, G4ThreeVector(Decimal(c[0]) + shift, Decimal(c[1]), Decimal(c[2])), fLogicals.at(name), name, fLogicals.at(mother), false,
                                                static_cast<G4int>(placement.at("copy_number", "placement").num), !std::getenv("G4SIM_NO_OVERLAP_CHECK")));
    }
    if (fPhysical.has("optical_surfaces")) BuildSurfaces(fPhysical.obj.at("optical_surfaces"), fLogicals, fPlaced);
    // G4SIM_BUILDER_CONTROL=leak_scope, for the tests of Section 15.1 only: the world takes the optical material of a template in the scope, a
    // specification check-spec refuses, so photons enter a volume outside optical_scope and only KillProcess stops them (GB16)
    if (Control() == "leak_scope")
      for (const auto& [name, logical] : fLogicals)
        if (name != kWorld && logical->GetMaterial()->GetMaterialPropertiesTable()) {
          fLogicals.at(kWorld)->SetMaterial(logical->GetMaterial());
          break;
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
    WriteFieldSamples(managers);
    if (fAttach) fAttach(fLogicals);
  }

 private:
  G4FieldManager* Manager(const std::string& name, std::map<std::string, G4FieldManager*>& managers) {
    auto found = managers.find(name);
    if (found != managers.end()) return found->second;
    G4FieldManager* manager = nullptr;
    const double sign = Control() == "flip_field" ? -1. : 1.;  // the negative test of Section 15.1
    const Value& declared = name == kNoField ? fPhysical : fPhysical.at("fields", "physical").at(name, "fields");
    if (name == kNoField) {
      manager = new G4FieldManager(static_cast<G4Field*>(nullptr));
    } else if (declared.has("map")) {
      const Value& map = declared.at("map", "field");
      std::array<double, 3> origin{}, step{};
      std::array<long, 3> count{};
      for (int axis = 0; axis < 3; ++axis) {
        origin[axis] = Decimal(map.at("origin_mm", "map").array("origin_mm")[axis]);
        step[axis] = Decimal(map.at("step_mm", "map").array("step_mm")[axis]);
        count[axis] = static_cast<long>(map.at("count", "map").array("count")[axis].num);
      }
      auto grid = ReadFieldGrid("field-map." + name + ".txt", origin, step, count);
      auto* field = new MapField(grid, ToLocal(map.at("frame_template", "map").str), sign);
      manager = new G4FieldManager(field);
      manager->CreateChordFinder(field);
    } else {
      const auto& b = declared.at("b_tesla", "field").array("b_tesla");
      auto* field = new G4UniformMagField(sign * G4ThreeVector(Decimal(b[0]) * tesla, Decimal(b[1]) * tesla, Decimal(b[2]) * tesla));
      manager = new G4FieldManager(field);
      manager->CreateChordFinder(field);
    }
    return managers[name] = manager;
  }

  // Global to the local frame of a template placed once in the tree (check-spec requires it of a field map's frame), composed level by
  // level as G4NavigationLevel composes a touchable's transform.
  G4AffineTransform ToLocal(const std::string& frame) const {
    std::vector<std::string> chain;
    for (std::string name = frame; name != kWorld;) {
      chain.push_back(name);
      std::string mother;
      for (const auto& [parent, children] : fChildren)
        for (const auto& child : children)
          if (child == name) mother = parent;
      if (mother.empty()) throw std::runtime_error("field map frame " + frame + " is not placed");
      name = mother;
    }
    G4AffineTransform transform;
    G4LogicalVolume* mother = fWorld->GetLogicalVolume();
    for (auto step = chain.rbegin(); step != chain.rend(); ++step) {
      G4VPhysicalVolume* placed = nullptr;
      for (std::size_t i = 0; i < mother->GetNoDaughters(); ++i)
        if (mother->GetDaughter(i)->GetLogicalVolume() == fLogicals.at(*step)) placed = mother->GetDaughter(i);
      if (!placed) throw std::runtime_error("field map frame " + frame + ": " + *step + " is not a daughter of " + mother->GetName());
      G4AffineTransform next;
      next.InverseProduct(transform, G4AffineTransform(placed->GetRotation(), placed->GetTranslation()));
      transform = next;
      mother = placed->GetLogicalVolume();
    }
    return transform;
  }

  // The read-back of a field (Section 6.2.8): g4sim_run.py lists global points in field-samples.txt; each thread writes the field its
  // manager gives there, in hexadecimal tesla, and the driver compares it with its own reading of the map.
  void WriteFieldSamples(std::map<std::string, G4FieldManager*>& managers) {
    std::ifstream in("field-samples.txt");
    if (!in) return;
    std::ofstream out("field-samples.thread" + std::to_string(G4Threading::G4GetThreadId()) + ".txt");
    std::string name, x, y, z;
    while (in >> name >> x >> y >> z) {
      const G4double point[4] = {std::strtod(x.c_str(), nullptr) * mm, std::strtod(y.c_str(), nullptr) * mm, std::strtod(z.c_str(), nullptr) * mm, 0.};
      G4double b[6] = {0., 0., 0., 0., 0., 0.};
      const G4Field* field = Manager(name, managers)->GetDetectorField();
      if (field) field->GetFieldValue(point, b);
      char line[256];
      std::snprintf(line, sizeof line, "%s %a %a %a\n", name.c_str(), b[0] / tesla, b[1] / tesla, b[2] / tesla);
      out << line;
    }
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
  G4VPhysicalVolume* fWorld = nullptr;
  std::map<std::string, std::vector<G4VPhysicalVolume*>> fPlaced;  // each template's physical volumes, for border surfaces
  std::map<std::string, std::vector<std::string>> fChildren;
};


}  // namespace g4sim

#endif
