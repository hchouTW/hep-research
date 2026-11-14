// g4sim/ScintillationSplit.hh: which side of G4Scintillation's regimes a step falls on (g4sim plan, Section 10.3; GB15). No Geant4 here, so the exact boundary can be tested.
//
// Geant4 draws a Gaussian for mu_s > 10 and Poisson for mu_s <= 10, so a step at exactly 10 is on the Poisson side.
// G4SIM_SPLIT_CONTROL=inclusive is the negative test of Section 15.1: it puts a step with mu_s = 10 into E^L.
#ifndef G4SIM_SCINTILLATIONSPLIT_HH
#define G4SIM_SCINTILLATIONSPLIT_HH

#include <cstdlib>
#include <string>

namespace g4sim {

constexpr double kGaussianRegimeMean = 10.;

inline bool ScintillationControl() {
  const char* value = std::getenv("G4SIM_SPLIT_CONTROL");
  return value && std::string(value) == "inclusive";
}

inline bool IsLargeStep(double mean, bool inclusive = false) { return inclusive ? mean >= kGaussianRegimeMean : mean > kGaussianRegimeMean; }

}  // namespace g4sim

#endif
