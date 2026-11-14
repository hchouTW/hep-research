// g4sim_run/XtrConstructor.hh: the g4sim_xtr constructor (g4sim plan, Section 6.2.9, S7). Written from the Geant4 API (no example code copied
// or adapted). For each radiator of the run card it builds the Geant4 class the card names on the envelope logical volume of the IR's
// transition_radiation requirement, with its foil and gas materials, foil thickness, gap and foil count (GB17), and attaches it as a discrete
// process to the card's particles (e- and e+ when the card names none). check-spec has already judged the XTR rules and the class's structure
// against xtr_radiators.json; G4StrawTubeXTRadiator never reaches this file.
#ifndef G4SIM_XTRCONSTRUCTOR_HH
#define G4SIM_XTRCONSTRUCTOR_HH

#include <stdexcept>
#include <string>
#include <vector>

#include "G4GammaXTRadiator.hh"
#include "G4GaussXTRadiator.hh"
#include "G4LogicalVolumeStore.hh"
#include "G4Material.hh"
#include "G4ParticleTable.hh"
#include "G4ProcessManager.hh"
#include "G4RegularXTRadiator.hh"
#include "G4SystemOfUnits.hh"
#include "G4TransparentRegXTRadiator.hh"
#include "G4VPhysicsConstructor.hh"
#include "G4XTRGammaRadModel.hh"
#include "G4XTRGaussRadModel.hh"
#include "G4XTRRegularRadModel.hh"
#include "G4XTRTransparentRegRadModel.hh"
#include "MiniJson.hh"

namespace g4sim {

using minijson::Value;

struct XtrRadiator {
  std::string envelope, radiatorClass, foil, gas;
  double foilThickness = 0., gap = 0., alphaFoil = 0., alphaGas = 0.;
  int foils = 0;
  std::vector<std::string> particles;
};

inline double XtrNumber(const Value& value) { return value.isNumber() ? value.num : std::strtod(value.str.c_str(), nullptr); }

// The card's radiators joined to the IR's requirements by envelope template.
inline std::vector<XtrRadiator> ReadXtrRadiators(const Value& physical, const Value& physics) {
  std::vector<XtrRadiator> out;
  for (const auto& item : physics.at("xtr", "physics").array("xtr")) {
    XtrRadiator radiator;
    radiator.envelope = item.at("envelope", "xtr").str;
    radiator.radiatorClass = item.at("radiator_class", "xtr").str;
    if (item.has("particles"))
      for (const auto& name : item.obj.at("particles").array("particles")) radiator.particles.push_back(name.str);
    if (radiator.particles.empty()) radiator.particles = {"e-", "e+"};
    bool found = false;
    for (const auto& requirement : physical.at("physics_requirements", "physical").array("physics_requirements")) {
      if (requirement.at("need", "requirement").str != "transition_radiation" || requirement.at("templates", "requirement").arr.at(0).str != radiator.envelope) continue;
      radiator.foil = requirement.at("foil_material", "requirement").str;
      radiator.gas = requirement.at("gas_material", "requirement").str;
      radiator.foilThickness = XtrNumber(requirement.at("foil_thickness_um", "requirement")) * um;
      radiator.gap = XtrNumber(requirement.at("gap_um", "requirement")) * um;
      radiator.foils = static_cast<int>(requirement.at("foils", "requirement").num);
      if (requirement.has("alpha_foil")) radiator.alphaFoil = XtrNumber(requirement.obj.at("alpha_foil"));
      if (requirement.has("alpha_gas")) radiator.alphaGas = XtrNumber(requirement.obj.at("alpha_gas"));
      found = true;
    }
    if (!found) throw std::runtime_error("XTR radiator " + radiator.envelope + ": no transition_radiation requirement names this envelope");
    out.push_back(radiator);
  }
  return out;
}

class XtrConstructor : public G4VPhysicsConstructor {
 public:
  explicit XtrConstructor(std::vector<XtrRadiator> radiators) : G4VPhysicsConstructor("g4sim_xtr"), fRadiators(std::move(radiators)) {}
  void ConstructParticle() override {}
  void ConstructProcess() override {
    for (const XtrRadiator& r : fRadiators) {
      G4LogicalVolume* envelope = G4LogicalVolumeStore::GetInstance()->GetVolume(r.envelope, false);
      G4Material* foil = G4Material::GetMaterial(r.foil, false);
      G4Material* gas = G4Material::GetMaterial(r.gas, false);
      if (!envelope || !foil || !gas) throw std::runtime_error("XTR radiator " + r.envelope + ": envelope, foil or gas material not built");
      G4VXTRenergyLoss* process = Make(r, envelope, foil, gas);
      for (const std::string& name : r.particles) {
        G4ParticleDefinition* particle = G4ParticleTable::GetParticleTable()->FindParticle(name);
        if (!particle || !particle->GetProcessManager()) throw std::runtime_error("XTR radiator " + r.envelope + ": unknown particle " + name);
        particle->GetProcessManager()->AddDiscreteProcess(process);
      }
    }
  }

 private:
  static G4VXTRenergyLoss* Make(const XtrRadiator& r, G4LogicalVolume* envelope, G4Material* foil, G4Material* gas) {
    const std::string name = "xtr_" + r.envelope;
    const std::string& c = r.radiatorClass;
    if (c == "G4RegularXTRadiator") return new G4RegularXTRadiator(envelope, foil, gas, r.foilThickness, r.gap, r.foils, name);
    if (c == "G4TransparentRegXTRadiator") return new G4TransparentRegXTRadiator(envelope, foil, gas, r.foilThickness, r.gap, r.foils, name);
    if (c == "G4GammaXTRadiator") return new G4GammaXTRadiator(envelope, r.alphaFoil, r.alphaGas, foil, gas, r.foilThickness, r.gap, r.foils, name);
    if (c == "G4GaussXTRadiator") return new G4GaussXTRadiator(envelope, r.alphaFoil, r.alphaGas, foil, gas, r.foilThickness, r.gap, r.foils, name);
    if (c == "G4XTRRegularRadModel") return new G4XTRRegularRadModel(envelope, foil, gas, r.foilThickness, r.gap, r.foils, name);
    if (c == "G4XTRTransparentRegRadModel") return new G4XTRTransparentRegRadModel(envelope, foil, gas, r.foilThickness, r.gap, r.foils, name);
    if (c == "G4XTRGammaRadModel") return new G4XTRGammaRadModel(envelope, r.alphaFoil, r.alphaGas, foil, gas, r.foilThickness, r.gap, r.foils, name);
    if (c == "G4XTRGaussRadModel") return new G4XTRGaussRadModel(envelope, r.alphaFoil, r.alphaGas, foil, gas, r.foilThickness, r.gap, r.foils, name);
    throw std::runtime_error("XTR radiator class " + c + " is not built by g4sim_xtr");
  }
  std::vector<XtrRadiator> fRadiators;
};

}  // namespace g4sim

#endif
