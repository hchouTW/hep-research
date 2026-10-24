// g4sim/SimMaterials.hh: materials of a simulation spec (adapters/geant4, Geant4 program A2.1; moved from
// layered_sim's Detector.cc without change of behaviour). Geant4 API only.
//
// A material is looked up in this order: the Geant4 material table (already built), the spec's definitions (a single
// element (Z, A) or a mixture by mass fraction of named materials, built recursively component by component in the
// order listed), then the NIST database. Anything else throws std::runtime_error.
#ifndef G4SIM_SIMMATERIALS_HH
#define G4SIM_SIMMATERIALS_HH

#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4SystemOfUnits.hh"

namespace g4sim {

struct MaterialDef {  // a single element (Z, A) or a mixture by mass fraction of named materials, with a density
  std::string name;
  int z = 0;
  double a_g_mole = 0., density_g_cm3 = 0.;
  std::vector<std::pair<std::string, double>> components;  // (material name, mass fraction); empty: single element
  std::string state = "solid";  // solid, liquid, gas
  double temperature_K = -1., pressure_Pa = -1.;  // < 0: Geant4 default
};

inline G4Material* BuildMaterial(const std::string& name, const std::vector<MaterialDef>& defs) {
  if (auto* m = G4Material::GetMaterial(name, false)) return m;
  for (const auto& d : defs) {
    if (d.name != name) continue;
    G4State state = d.state == "gas" ? kStateGas : d.state == "liquid" ? kStateLiquid : kStateSolid;
    double t = d.temperature_K > 0 ? d.temperature_K * kelvin : NTP_Temperature;
    double p = d.pressure_Pa > 0 ? d.pressure_Pa * pascal : CLHEP::STP_Pressure;
    if (d.components.empty())
      return new G4Material(d.name, d.z, d.a_g_mole * g / mole, d.density_g_cm3 * g / cm3, state, t, p);
    auto* mix = new G4Material(d.name, d.density_g_cm3 * g / cm3, static_cast<G4int>(d.components.size()), state, t, p);
    for (const auto& [component, fraction] : d.components) mix->AddMaterial(BuildMaterial(component, defs), fraction);
    return mix;
  }
  if (auto* m = G4NistManager::Instance()->FindOrBuildMaterial(name, false)) return m;
  throw std::runtime_error("unknown material " + name + " (not defined in the spec and not a NIST name)");
}

}  // namespace g4sim

#endif
