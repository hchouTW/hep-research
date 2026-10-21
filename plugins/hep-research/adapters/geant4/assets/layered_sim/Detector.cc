#include "Detector.hh"

#include <cfloat>
#include <set>
#include <stdexcept>

#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ProductionCuts.hh"
#include "G4Region.hh"
#include "G4SystemOfUnits.hh"
#include "G4UserLimits.hh"

Detector::Detector(const Spec& spec) : fSpec(spec), fNames(spec.slabNames()) {}

G4Material* Detector::Material(const std::string& name) {
  if (auto* m = G4Material::GetMaterial(name, false)) return m;
  for (const auto& d : fSpec.materials) {
    if (d.name != name) continue;
    G4State state = d.state == "gas" ? kStateGas : d.state == "liquid" ? kStateLiquid : kStateSolid;
    double t = d.temperature_K > 0 ? d.temperature_K * kelvin : NTP_Temperature;
    double p = d.pressure_Pa > 0 ? d.pressure_Pa * pascal : CLHEP::STP_Pressure;
    return new G4Material(d.name, d.z, d.a_g_mole * g / mole, d.density_g_cm3 * g / cm3, state, t, p);
  }
  if (auto* m = G4NistManager::Instance()->FindOrBuildMaterial(name, false)) return m;
  throw std::runtime_error("unknown material " + name + " (not defined in the spec and not a NIST name)");
}

G4VPhysicalVolume* Detector::Construct() {
  // one logical volume per slab name; a name used twice must keep its material and thickness
  std::map<std::string, const SlabDef*> def;
  double stack = 0.;
  for (const auto& l : fSpec.layers) {
    double layer = 0.;
    for (const auto& s : l.slabs) {
      auto it = def.find(s.name);
      if (it != def.end() && (it->second->material != s.material || it->second->thickness_mm != s.thickness_mm))
        throw std::runtime_error("slab name " + s.name + " is reused with another material or thickness");
      def[s.name] = &s;
      layer += s.thickness_mm * mm;
    }
    stack += l.repeat * layer;
  }
  double lat = fSpec.lateral_mm * mm;
  double wx, wy, wz;
  if (fSpec.world_scale > 0) {
    wx = fSpec.world_scale * stack;
    wy = wz = fSpec.world_scale * lat;
  } else {
    wx = fSpec.world_mm[0] * mm;
    wy = fSpec.world_mm[1] * mm;
    wz = fSpec.world_mm[2] * mm;
  }
  if (wx <= stack || wy < lat || wz < lat) throw std::runtime_error("the world does not contain the slab stack");
  fWorldX = wx;
  auto* worldBox = new G4Box("World", wx / 2, wy / 2, wz / 2);
  fWorldLV = new G4LogicalVolume(worldBox, Material(fSpec.world_material), "World");
  auto* world = new G4PVPlacement(nullptr, {}, fWorldLV, "World", nullptr, false, 0, true);

  G4UserLimits* limits = nullptr;
  if (fSpec.step_limit_mm > 0 || fSpec.min_ekin_MeV > 0)
    limits = new G4UserLimits(fSpec.step_limit_mm > 0 ? fSpec.step_limit_mm * mm : DBL_MAX, DBL_MAX, DBL_MAX,
                              fSpec.min_ekin_MeV * MeV);
  std::map<std::string, G4LogicalVolume*> lvs;
  for (std::size_t i = 0; i < fNames.size(); ++i) {
    const SlabDef& s = *def[fNames[i]];
    auto* box = new G4Box(s.name, s.thickness_mm * mm / 2, lat / 2, lat / 2);
    auto* lv = new G4LogicalVolume(box, Material(s.material), s.name);
    if (s.sensitive && limits) lv->SetUserLimits(limits);
    lvs[s.name] = lv;
    fIndex[lv] = static_cast<int>(i);
    fSlabLV.push_back(lv);
  }
  double x = -stack / 2;
  for (const auto& l : fSpec.layers)
    for (int r = 0; r < l.repeat; ++r)
      for (const auto& s : l.slabs) {
        double t = s.thickness_mm * mm;
        new G4PVPlacement(nullptr, G4ThreeVector(x + t / 2 + s.shift_mm * mm, 0, 0), lvs[s.name], s.name, fWorldLV,
                          false, fPlacements, true);
        ++fPlacements;
        x += t;
      }
  for (const auto& rd : fSpec.regions) {
    auto* region = new G4Region(rd.name);
    auto* cuts = new G4ProductionCuts();
    cuts->SetProductionCut(rd.cut_mm * mm);
    region->SetProductionCuts(cuts);
    for (const auto& n : rd.slabs) region->AddRootLogicalVolume(lvs[n]);
  }
  return world;
}

int Detector::SlabIndex(const G4LogicalVolume* lv) const {
  auto it = fIndex.find(lv);
  return it == fIndex.end() ? -1 : it->second;
}

std::vector<const G4Material*> Detector::UsedMaterials() const {
  std::vector<const G4Material*> out;
  std::set<const G4Material*> seen;
  if (fWorldLV && seen.insert(fWorldLV->GetMaterial()).second) out.push_back(fWorldLV->GetMaterial());
  for (auto* lv : fSlabLV)
    if (seen.insert(lv->GetMaterial()).second) out.push_back(lv->GetMaterial());
  return out;
}
