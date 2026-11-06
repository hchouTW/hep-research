// g4sim/BirksTerms.hh: the Birks variable and visible-energy parts of a step (g4sim plan, Sections 8.8, 9.1; GB13). G4EmSaturation keeps massFactor and
// effCharge private and computes them only for k_B > 0, so g4sim computes them for every material with the same formulas.
#ifndef G4SIM_BIRKSTERMS_HH
#define G4SIM_BIRKSTERMS_HH

#include <algorithm>
#include <utility>
#include <vector>

#include "G4Electron.hh"
#include "G4LossTableManager.hh"
#include "G4Material.hh"
#include "G4MaterialCutsCouple.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4PhysicalConstants.hh"
#include "G4Proton.hh"

namespace g4sim {

struct BirksTerms {
  double massFactor, effCharge;
};

inline BirksTerms OwnBirksTerms(const G4Material* material) {
  double ratio = 0., chargeSquared = 0., norm = 0.;
  const auto* elements = material->GetElementVector();
  const double* density = material->GetVecNbOfAtomsPerVolume();
  for (std::size_t i = 0; i < material->GetNumberOfElements(); ++i) {
    const int z = (*elements)[i]->GetZasInt();
    ratio += density[i] / G4NistManager::Instance()->GetAtomicMassAmu(z);
    chargeSquared += (z * z) * density[i];
    norm += density[i];
  }
  if (norm > 0.) norm = 1. / norm;
  return {ratio * (CLHEP::proton_mass_c2 * norm), chargeSquared * norm};
}

enum class DepositKind { kIonizing = 0, kNonIonizing = 1, kPhoton = 2, kZeroLength = 3 };

struct DepositPart {
  DepositKind kind;
  double energy, x;  // the part's energy and its Birks variable: deposit / (1 + k_B x)
};

// The parts of one step's deposit by the four cases of Section 8.8. G4SIM_DEDX_CONTROL=nonionizing_as_ionizing is the negative test of Section 15.1.
inline std::vector<DepositPart> DepositParts(const G4ParticleDefinition* particle, const G4MaterialCutsCouple* couple, double length, double deposit, double nonIonizing, bool mixNonIonizing) {
  if (deposit <= 0.) return {};
  if (length <= 0.) return {{DepositKind::kZeroLength, deposit, 0.}};
  auto* manager = G4LossTableManager::Instance();
  if (particle->GetPDGEncoding() == 22) return {{DepositKind::kPhoton, deposit, deposit / manager->GetRange(G4Electron::Electron(), deposit, couple)}};
  const BirksTerms terms = OwnBirksTerms(couple->GetMaterial());
  const auto lost = [&](double part) { return part / (manager->GetRange(G4Proton::Proton(), part * terms.massFactor, couple) / terms.effCharge); };
  double loss = std::max(nonIonizing, 0.), ionizing = deposit - loss;
  if (particle->GetPDGCharge() == 0. || ionizing < 0.) return {{DepositKind::kNonIonizing, deposit, lost(deposit)}};
  std::vector<DepositPart> parts;
  if (mixNonIonizing) return {{DepositKind::kIonizing, deposit, deposit / length}};
  if (ionizing > 0.) parts.push_back({DepositKind::kIonizing, ionizing, ionizing / length});
  if (loss > 0.) parts.push_back({DepositKind::kNonIonizing, loss, lost(loss)});
  return parts;
}

}  // namespace g4sim

#endif
