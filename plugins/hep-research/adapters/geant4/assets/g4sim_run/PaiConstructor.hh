// PaiConstructor.hh: PAI for a region (g4sim plan, Section 6.2.9 as of addendum 11.1). AddPAIModel does nothing through the EM constructors in Geant4
// 11.4.3, so this constructor, registered after them, adds the region's models itself and leaves the models outside the region alone.
#ifndef G4SIM_PAICONSTRUCTOR_HH
#define G4SIM_PAICONSTRUCTOR_HH

#include <string>
#include <vector>

#include "G4BraggModel.hh"
#include "G4IonFluctuations.hh"
#include "G4LindhardSorensenIonModel.hh"
#include "G4LossTableManager.hh"
#include "G4MollerBhabhaModel.hh"
#include "G4PAIModel.hh"
#include "G4PAIPhotModel.hh"
#include "G4ParticleTable.hh"
#include "G4Region.hh"
#include "G4RegionStore.hh"
#include "G4SystemOfUnits.hh"
#include "G4UniversalFluctuation.hh"
#include "G4VEnergyLossProcess.hh"
#include "G4VPhysicsConstructor.hh"

namespace g4sim {

struct PaiRequest {
  std::string region, particle, model;
};

class PaiConstructor : public G4VPhysicsConstructor {
 public:
  explicit PaiConstructor(std::vector<PaiRequest> requests) : G4VPhysicsConstructor("g4sim_pai"), fRequests(std::move(requests)) {}
  void ConstructParticle() override {}
  void ConstructProcess() override {
    for (const PaiRequest& request : fRequests) {
      const G4Region* region = G4RegionStore::GetInstance()->GetRegion(request.region, false);
      const bool all = request.particle == "all";
      const G4ParticleDefinition* particle = all ? nullptr : G4ParticleTable::GetParticleTable()->FindParticle(request.particle);
      const std::string wanted = Mapped(request.particle);
      for (G4VEnergyLossProcess* item : G4LossTableManager::Instance()->GetEnergyLossProcessVector()) {
        const std::string name = item->GetProcessName();
        if (name != "eIoni" && name != "hIoni" && name != "muIoni" && name != "ionIoni") continue;
        if (!all && name != wanted) continue;
        const double lowest = name == "eIoni" ? 110 * eV : name == "muIoni" ? 5 * keV : 50 * keV;
        G4VEmModel* below = name == "eIoni" ? static_cast<G4VEmModel*>(new G4MollerBhabhaModel()) : name == "ionIoni" ? static_cast<G4VEmModel*>(new G4LindhardSorensenIonModel()) : new G4BraggModel();
        G4VEmFluctuationModel* fluctuation = name == "ionIoni" ? static_cast<G4VEmFluctuationModel*>(new G4IonFluctuations()) : new G4UniversalFluctuation();
        below->SetHighEnergyLimit(lowest);
        item->AddEmModel(-1, below, fluctuation, region);
        if (request.model == "PAIphoton") {
          auto* built = new G4PAIPhotModel(particle, "PAIPhotModel");
          built->SetLowEnergyLimit(lowest);
          item->AddEmModel(-1, built, built, region);
        } else {
          auto* built = new G4PAIModel(particle, "PAIModel");
          built->SetLowEnergyLimit(lowest);
          item->AddEmModel(-1, built, built, region);
        }
      }
    }
  }

 private:
  static std::string Mapped(const std::string& particle) {
    if (particle == "e-" || particle == "e+") return "eIoni";
    if (particle == "mu-" || particle == "mu+") return "muIoni";
    return particle == "GenericIon" ? "ionIoni" : "hIoni";
  }
  std::vector<PaiRequest> fRequests;
};

}  // namespace g4sim

#endif
