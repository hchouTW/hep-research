#include "Detector.hh"

#include <set>
#include <stdexcept>

#include "Field.hh"
#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4PVPlacement.hh"
#include "G4ProductionCuts.hh"
#include "G4Region.hh"
#include "G4SystemOfUnits.hh"
#include "G4UserLimits.hh"
#include "SimMaterials.hh"

G4VPhysicalVolume* Detector::Construct() {
  const Vec3& w = fSpec.world_half_mm;
  auto* worldBox = new G4Box("World", w[0] * mm, w[1] * mm, w[2] * mm);
  fWorldLV = new G4LogicalVolume(worldBox, g4sim::BuildMaterial(fSpec.world_material, fSpec.materials), "World");
  auto* world = new G4PVPlacement(nullptr, {}, fWorldLV, "World", nullptr, false, 0, true);
  for (std::size_t i = 0; i < fSpec.elements.size(); ++i) {
    const ElementDef& e = fSpec.elements[i];
    auto* box = new G4Box(e.name, e.half_mm[0] * mm, e.half_mm[1] * mm, e.half_mm[2] * mm);
    auto* lv = new G4LogicalVolume(box, g4sim::BuildMaterial(e.material, fSpec.materials), e.name);
    fLVs[e.name] = lv;
    fIndex[lv] = static_cast<int>(i);
  }
  // mothers first (their daughters need the mother's placement), then daughters; centres are world coordinates
  for (int pass = 0; pass < 2; ++pass)
    for (const ElementDef& e : fSpec.elements) {
      bool daughter = e.mother != "world";
      if (daughter != (pass == 1)) continue;
      Vec3 origin{0, 0, 0};
      G4LogicalVolume* mother = fWorldLV;
      if (daughter) {
        const ElementDef& m = fSpec.elements[static_cast<std::size_t>(fSpec.ElementIndex(e.mother))];
        if (m.mother != "world" || m.count != 1)
          throw std::runtime_error("element " + e.name + ": its mother must be placed once in the world");
        origin = m.CopyCentre(0);
        mother = fLVs.at(e.mother);
      }
      for (int k = 0; k < e.count; ++k) {
        Vec3 c = e.CopyCentre(k);
        new G4PVPlacement(nullptr,
                          G4ThreeVector((c[0] - origin[0]) * mm, (c[1] - origin[1]) * mm, (c[2] - origin[2]) * mm),
                          fLVs.at(e.name), e.name, mother, false, k, true);
      }
    }
  for (const auto& rd : fSpec.regions) {
    auto* region = new G4Region(rd.name);
    auto* cuts = new G4ProductionCuts();
    cuts->SetProductionCut(rd.cut_mm * mm);
    region->SetProductionCuts(cuts);
    for (const auto& n : rd.elements) region->AddRootLogicalVolume(fLVs.at(n));
  }
  if (fSpec.HasField()) {  // the maximum step on each field element and on each of its daughters
    auto* limits = new G4UserLimits(fSpec.field.max_step_mm * mm);
    for (const auto& r : fSpec.field.regions) {
      fLVs.at(r.element)->SetUserLimits(limits);
      for (const auto& e : fSpec.elements)
        if (e.mother == r.element) fLVs.at(e.name)->SetUserLimits(limits);
    }
  }
  return world;
}

void Detector::ConstructSDandField() { AttachFields(fSpec, fLVs); }

int Detector::ElementIndex(const G4LogicalVolume* lv) const {
  auto it = fIndex.find(lv);
  return it == fIndex.end() ? -1 : it->second;
}

std::vector<const G4Material*> Detector::UsedMaterials() const {
  std::vector<const G4Material*> out;
  std::set<const G4Material*> seen;
  if (fWorldLV && seen.insert(fWorldLV->GetMaterial()).second) out.push_back(fWorldLV->GetMaterial());
  for (const auto& e : fSpec.elements) {
    const G4Material* m = fLVs.at(e.name)->GetMaterial();
    if (seen.insert(m).second) out.push_back(m);
  }
  return out;
}
