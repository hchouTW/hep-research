// Slabs stacked along x, each placed with its own G4PVPlacement (checkOverlaps on, no replicas), centred in the world.
#ifndef LAYERED_SIM_DETECTOR_HH
#define LAYERED_SIM_DETECTOR_HH

#include <map>
#include <string>
#include <vector>

#include "G4VUserDetectorConstruction.hh"
#include "Spec.hh"

class G4LogicalVolume;
class G4Material;

class Detector : public G4VUserDetectorConstruction {
 public:
  explicit Detector(const Spec& spec);
  G4VPhysicalVolume* Construct() override;

  // slab-name index of a logical volume, or -1 for the world
  int SlabIndex(const G4LogicalVolume* lv) const;
  const std::vector<std::string>& SlabNames() const { return fNames; }
  int NumberOfPlacements() const { return fPlacements; }
  double WorldXLength() const { return fWorldX; }
  std::vector<const G4Material*> UsedMaterials() const;

 private:
  G4Material* Material(const std::string& name);
  const Spec& fSpec;
  std::vector<std::string> fNames;
  std::map<const G4LogicalVolume*, int> fIndex;
  std::vector<G4LogicalVolume*> fSlabLV;
  G4LogicalVolume* fWorldLV = nullptr;
  int fPlacements = 0;
  double fWorldX = 0.;
};

#endif
