// Physics list from the spec: a reference list by name through G4PhysListFactory (optionally with an EM suffix), or a
// modular EM-only list (one named EM constructor plus G4DecayPhysics). G4StepLimiterPhysics is added when the spec
// sets step limits or a minimum kinetic energy (it also attaches G4UserSpecialCuts, which books a killed track's
// kinetic energy as a local deposit).
#ifndef LAYERED_SIM_PHYSICS_HH
#define LAYERED_SIM_PHYSICS_HH

#include <string>
#include <vector>

#include "Spec.hh"

class G4VModularPhysicsList;

// nullptr and a message when the name is unknown
G4VModularPhysicsList* BuildPhysics(const Spec& spec, std::string& error);
std::vector<std::string> KnownEmConstructors();

#endif
