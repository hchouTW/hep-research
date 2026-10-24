#include "Field.hh"

#include "G4ChordFinder.hh"
#include "G4DormandPrince745.hh"
#include "G4FieldManager.hh"
#include "G4InterpolationDriver.hh"
#include "G4LogicalVolume.hh"
#include "G4Mag_UsualEqRhs.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4UniformMagField.hh"

namespace {

std::vector<G4FieldManager*>& Managers() {
  static G4ThreadLocal std::vector<G4FieldManager*>* managers = nullptr;
  if (!managers) managers = new std::vector<G4FieldManager*>();
  return *managers;
}

}  // namespace

const std::vector<G4FieldManager*>& ThreadFieldManagers() { return Managers(); }

void AttachFields(const Spec& spec, const std::map<std::string, G4LogicalVolume*>& lvs) {
  auto& managers = Managers();
  managers.clear();
  const FieldDef& f = spec.field;
  for (const auto& region : f.regions) {
    G4ThreeVector b(region.b_tesla[0] * tesla, region.b_tesla[1] * tesla, region.b_tesla[2] * tesla);
    auto* field = new G4UniformMagField(b);
    auto* equation = new G4Mag_UsualEqRhs(field);
    auto* stepper = new G4DormandPrince745(equation, 6);
    auto* driver = new G4InterpolationDriver<G4DormandPrince745>(kDriverMinimumStepMm * mm, stepper, 6);
    auto* chordFinder = new G4ChordFinder(driver);
    chordFinder->SetDeltaChord(f.delta_chord_mm * mm);
    auto* fm = new G4FieldManager(field, chordFinder);
    fm->SetDeltaOneStep(f.delta_one_step_mm * mm);
    fm->SetDeltaIntersection(f.delta_intersection_mm * mm);
    fm->SetMinimumEpsilonStep(f.min_epsilon_step);
    fm->SetMaximumEpsilonStep(f.max_epsilon_step);
    lvs.at(region.element)->SetFieldManager(fm, true);
    managers.push_back(fm);
  }
}
