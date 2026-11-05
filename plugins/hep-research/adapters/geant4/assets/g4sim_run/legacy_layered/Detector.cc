#include "Detector.hh"

#include <set>

#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "IrTree.hh"

namespace legacy_layered {

Detector::Detector(const Spec& spec, const minijson::Value& legacy) : fSpec(spec), fLegacy(legacy), fNames(spec.slabNames()) {}

// The tree comes from the IR's legacy block; what the observer asks of the detector is as in layered_sim.
G4VPhysicalVolume* Detector::Construct() {
  g4sim::IrTree tree = g4sim::BuildLegacyTree(fLegacy);
  fWorldLV = tree.logicals.at("World");
  fWorldX = 2 * static_cast<G4Box*>(fWorldLV->GetSolid())->GetXHalfLength();
  for (std::size_t i = 0; i < fNames.size(); ++i) {
    G4LogicalVolume* lv = tree.logicals.at(fNames[i]);
    fIndex[lv] = static_cast<int>(i);
    fSlabLV.push_back(lv);
  }
  fPlacements = static_cast<int>(fLegacy.at("positions", "legacy").arr.size()) - 1;
  return tree.world;
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

}  // namespace legacy_layered
