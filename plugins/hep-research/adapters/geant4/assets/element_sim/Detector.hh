// Box elements of element_sim (Geant4 program B1.1): each element is one G4LogicalVolume, placed once per copy with
// its own G4PVPlacement (checkOverlaps on) in the world or in its mother element (one level of nesting; centres are
// world coordinates in the spec and converted to mother coordinates here). Field regions are attached in
// ConstructSDandField (Field.hh); production-cut regions and the field's step limits are set in Construct.
#ifndef ELEMENT_SIM_DETECTOR_HH
#define ELEMENT_SIM_DETECTOR_HH

#include <map>
#include <string>
#include <vector>

#include "G4VUserDetectorConstruction.hh"
#include "Spec.hh"

class G4LogicalVolume;
class G4Material;

class Detector : public G4VUserDetectorConstruction {
 public:
  explicit Detector(const Spec& spec) : fSpec(spec) {}
  G4VPhysicalVolume* Construct() override;
  void ConstructSDandField() override;

  // element index of a logical volume, or -1 for the world
  int ElementIndex(const G4LogicalVolume* lv) const;
  const G4LogicalVolume* WorldLV() const { return fWorldLV; }
  std::vector<const G4Material*> UsedMaterials() const;

 private:
  const Spec& fSpec;
  std::map<const G4LogicalVolume*, int> fIndex;
  std::map<std::string, G4LogicalVolume*> fLVs;
  G4LogicalVolume* fWorldLV = nullptr;
};

#endif
