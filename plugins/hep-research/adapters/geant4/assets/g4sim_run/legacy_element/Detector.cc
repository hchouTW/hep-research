#include "Detector.hh"

#include <set>

#include "Field.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "IrTree.hh"

namespace legacy_element {

// The tree comes from the IR's legacy block; what the observer asks of the detector is as in element_sim.
G4VPhysicalVolume* Detector::Construct() {
  g4sim::IrTree tree = g4sim::BuildLegacyTree(fLegacy);
  fLVs = tree.logicals;
  fWorldLV = fLVs.at("World");
  for (std::size_t i = 0; i < fSpec.elements.size(); ++i) fIndex[fLVs.at(fSpec.elements[i].name)] = static_cast<int>(i);
  return tree.world;
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

}  // namespace legacy_element
