// g4sim/SimPhysics.hh: physics-list selection of a simulation spec (adapters/geant4, Geant4 program A2.1; moved from
// layered_sim's Physics.cc without change of behaviour). Geant4 API only.
//
// Either a G4PhysListFactory reference list (optionally with an EM suffix) or a modular EM-only list: one EM
// constructor plus G4DecayPhysics (unless decay is off). A step limit or a minimum kinetic energy adds
// G4StepLimiterPhysics; the default production cut is set last.
#ifndef G4SIM_SIMPHYSICS_HH
#define G4SIM_SIMPHYSICS_HH

#include <functional>
#include <map>
#include <string>
#include <vector>

#include "G4DecayPhysics.hh"
#include "G4EmLivermorePhysics.hh"
#include "G4EmLowEPPhysics.hh"
#include "G4EmPenelopePhysics.hh"
#include "G4EmStandardPhysics.hh"
#include "G4EmStandardPhysicsGS.hh"
#include "G4EmStandardPhysicsSS.hh"
#include "G4EmStandardPhysicsWVI.hh"
#include "G4EmStandardPhysics_option1.hh"
#include "G4EmStandardPhysics_option2.hh"
#include "G4EmStandardPhysics_option3.hh"
#include "G4EmStandardPhysics_option4.hh"
#include "G4PhysListFactory.hh"
#include "G4StepLimiterPhysics.hh"
#include "G4SystemOfUnits.hh"
#include "G4VModularPhysicsList.hh"

namespace g4sim {

inline const std::map<std::string, std::function<G4VPhysicsConstructor*()>>& EmConstructorTable() {
  static const std::map<std::string, std::function<G4VPhysicsConstructor*()>> table = {
      {"G4EmStandardPhysics", [] { return new G4EmStandardPhysics(); }},
      {"G4EmStandardPhysics_option1", [] { return new G4EmStandardPhysics_option1(); }},
      {"G4EmStandardPhysics_option2", [] { return new G4EmStandardPhysics_option2(); }},
      {"G4EmStandardPhysics_option3", [] { return new G4EmStandardPhysics_option3(); }},
      {"G4EmStandardPhysics_option4", [] { return new G4EmStandardPhysics_option4(); }},
      {"G4EmLivermorePhysics", [] { return new G4EmLivermorePhysics(); }},
      {"G4EmPenelopePhysics", [] { return new G4EmPenelopePhysics(); }},
      {"G4EmLowEPPhysics", [] { return new G4EmLowEPPhysics(); }},
      {"G4EmStandardPhysicsGS", [] { return new G4EmStandardPhysicsGS(); }},
      {"G4EmStandardPhysicsSS", [] { return new G4EmStandardPhysicsSS(); }},
      {"G4EmStandardPhysicsWVI", [] { return new G4EmStandardPhysicsWVI(); }},
  };
  return table;
}

class EmOnlyList : public G4VModularPhysicsList {
 public:
  EmOnlyList(G4VPhysicsConstructor* em, bool decay) {
    RegisterPhysics(em);
    if (decay) RegisterPhysics(new G4DecayPhysics());
  }
};

inline std::vector<std::string> KnownEmConstructors() {
  std::vector<std::string> out;
  for (const auto& kv : EmConstructorTable()) out.push_back(kv.first);
  return out;
}

// The physics list, or nullptr with `error` set for an unknown reference list or EM constructor.
inline G4VModularPhysicsList* BuildPhysicsList(const std::string& referenceList, const std::string& emConstructor,
                                               bool decay, bool stepLimiter, double defaultCutMm, std::string& error) {
  G4VModularPhysicsList* list = nullptr;
  if (!referenceList.empty()) {
    G4PhysListFactory factory;
    if (!factory.IsReferencePhysList(referenceList)) {
      error = "unknown reference physics list " + referenceList;
      return nullptr;
    }
    list = factory.GetReferencePhysList(referenceList);
  } else {
    auto it = EmConstructorTable().find(emConstructor);
    if (it == EmConstructorTable().end()) {
      error = "unknown EM constructor " + emConstructor;
      return nullptr;
    }
    list = new EmOnlyList(it->second(), decay);
  }
  if (stepLimiter) list->RegisterPhysics(new G4StepLimiterPhysics());
  list->SetDefaultCutValue(defaultCutMm * mm);
  return list;
}

}  // namespace g4sim

#endif
