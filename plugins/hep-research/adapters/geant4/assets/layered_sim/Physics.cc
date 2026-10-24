#include "Physics.hh"

#include "SimPhysics.hh"

std::vector<std::string> KnownEmConstructors() { return g4sim::KnownEmConstructors(); }

G4VModularPhysicsList* BuildPhysics(const Spec& spec, std::string& error) {
  return g4sim::BuildPhysicsList(spec.reference_list, spec.em_constructor, spec.decay,
                                 spec.step_limit_mm > 0 || spec.min_ekin_MeV > 0, spec.default_cut_mm, error);
}
