#include "Physics.hh"

#include <functional>
#include <map>

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

namespace {

const std::map<std::string, std::function<G4VPhysicsConstructor*()>>& EmTable() {
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

}  // namespace

std::vector<std::string> KnownEmConstructors() {
  std::vector<std::string> out;
  for (const auto& kv : EmTable()) out.push_back(kv.first);
  return out;
}

G4VModularPhysicsList* BuildPhysics(const Spec& spec, std::string& error) {
  G4VModularPhysicsList* list = nullptr;
  if (!spec.reference_list.empty()) {
    G4PhysListFactory factory;
    if (!factory.IsReferencePhysList(spec.reference_list)) {
      error = "unknown reference physics list " + spec.reference_list;
      return nullptr;
    }
    list = factory.GetReferencePhysList(spec.reference_list);
  } else {
    auto it = EmTable().find(spec.em_constructor);
    if (it == EmTable().end()) {
      error = "unknown EM constructor " + spec.em_constructor;
      return nullptr;
    }
    list = new EmOnlyList(it->second(), spec.decay);
  }
  if (spec.step_limit_mm > 0 || spec.min_ekin_MeV > 0) list->RegisterPhysics(new G4StepLimiterPhysics());
  list->SetDefaultCutValue(spec.default_cut_mm * mm);
  return list;
}
