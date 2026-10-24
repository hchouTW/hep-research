// Field regions of element_sim (Geant4 program B1.2). Written from the Geant4 11.4 API; no example code (B5 or any
// other) was copied or adapted.
//
// For each field region the spec names, ConstructSDandField builds a G4UniformMagField, its equation of motion
// (G4Mag_UsualEqRhs), the stepper (G4DormandPrince745) and driver (G4InterpolationDriver<G4DormandPrince745>) built
// explicitly, a G4ChordFinder on that driver and a G4FieldManager with the spec's accuracy parameters, and attaches
// the manager to the region's element with SetFieldManager(fm, true) so that its daughters share it. All of these are
// thread-local: the master and every worker build their own copy in their own ConstructSDandField (a chord finder is
// not thread-safe). The maximum step is a G4UserLimits on the region's element and on each of its daughters
// (user limits do not propagate to daughters); G4StepLimiterPhysics is registered whenever the spec has a field.
#ifndef ELEMENT_SIM_FIELD_HH
#define ELEMENT_SIM_FIELD_HH

#include <map>
#include <string>
#include <vector>

#include "Spec.hh"

class G4LogicalVolume;
class G4FieldManager;

// The minimum step of the integration driver (mm); recorded by the probe through the driver.
constexpr double kDriverMinimumStepMm = 1e-5;

// Builds and attaches this thread's field managers; `lvs` maps element names to their logical volumes.
void AttachFields(const Spec& spec, const std::map<std::string, G4LogicalVolume*>& lvs);

// This thread's field managers, in the spec's region order (empty before AttachFields).
const std::vector<G4FieldManager*>& ThreadFieldManagers();

#endif
