// Prototype GB1, one clause (g4sim plan, Section 23): with /run/beamOn 0 the probe does not run. The old programs refuse zero
// events before reaching Geant4, so this program calls BeamOn itself. It counts the calls of the master's BeginOfRunAction, in
// which the probe runs, after BeamOn(0) and after BeamOn(1), and prints the two counts as JSON.
#include <cstdio>

#include "G4Box.hh"
#include "G4Geantino.hh"
#include "G4LogicalVolume.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleGun.hh"
#include "G4Run.hh"
#include "G4RunManagerFactory.hh"
#include "G4SystemOfUnits.hh"
#include "G4UserRunAction.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPhysicsList.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "ProbeV2.hh"

namespace {

int probes = 0;
bool recorded = false;

class World : public G4VUserDetectorConstruction {
 public:
  G4VPhysicalVolume* Construct() override {
    auto* vacuum = G4NistManager::Instance()->FindOrBuildMaterial("G4_Galactic");
    auto* logical = new G4LogicalVolume(new G4Box("World", 100, 100, 100), vacuum, "World");
    return new G4PVPlacement(nullptr, {}, logical, "World", nullptr, false, 0);
  }
};

class Physics : public G4VUserPhysicsList {
 public:
  void ConstructParticle() override { G4Geantino::GeantinoDefinition(); }
  void ConstructProcess() override { AddTransportation(); }
};

class Gun : public G4VUserPrimaryGeneratorAction {
 public:
  Gun() : gun_(1) {
    gun_.SetParticleDefinition(G4Geantino::Definition());
    gun_.SetParticleEnergy(1 * GeV);
  }
  void GeneratePrimaries(G4Event* event) override { gun_.GeneratePrimaryVertex(event); }

 private:
  G4ParticleGun gun_;
};

class ProbeOnRun : public G4UserRunAction {
 public:
  void BeginOfRunAction(const G4Run*) override {
    ++probes;
    recorded = g4sim::RunProbeV2("beamon_zero").recorded;
  }
};

}  // namespace

int main() {
  auto* manager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::SerialOnly);
  manager->SetVerboseLevel(0);
  manager->SetUserInitialization(new World);
  manager->SetUserInitialization(new Physics);
  manager->SetUserAction(new Gun);
  manager->SetUserAction(new ProbeOnRun);
  manager->Initialize();
  manager->BeamOn(0);
  const int afterZero = probes;
  manager->BeamOn(1);
  std::printf("BEAMON_ZERO {\"after_zero\": %d, \"after_one\": %d, \"recorded\": %s}\n", afterZero, probes, recorded ? "true" : "false");
  delete manager;
  return 0;
}
