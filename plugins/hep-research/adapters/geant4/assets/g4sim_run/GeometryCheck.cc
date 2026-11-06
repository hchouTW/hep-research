// g4sim_run/GeometryCheck.cc: run.mode geometry-check (g4sim plan, Section 19.2, S2): the volume tree of a new specification from its IR, with
// fields set explicitly in pre-order, one geantino event to trigger the probe, and the write-back. Written from the Geant4 11.4 API; no example
// code copied or adapted. No accounting and no scorers: those come in S3.
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

#include "G4Box.hh"
#include "G4ChordFinder.hh"
#include "G4Event.hh"
#include "G4Field.hh"
#include "G4FieldManager.hh"
#include "G4Geantino.hh"
#include "G4GeometryTolerance.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4Polyhedra.hh"
#include "G4ParticleGun.hh"
#include "G4ProductionCuts.hh"
#include "G4Region.hh"
#include "G4RotationMatrix.hh"
#include "G4Run.hh"
#include "G4RunManager.hh"
#include "G4RunManagerFactory.hh"
#include "G4SystemOfUnits.hh"
#include "G4Threading.hh"
#include "G4Trd.hh"
#include "G4Tubs.hh"
#include "G4UniformMagField.hh"
#include "G4UserRunAction.hh"
#include "G4VUserActionInitialization.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "MiniJson.hh"
#include "SimPhysics.hh"
#include "NewBuild.hh"
#include "WriteBack.hh"

namespace {

using minijson::Value;
using g4sim::Decimal;
using g4sim::NewDetector;
double Now() { return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count(); }

class Geantino : public G4VUserPrimaryGeneratorAction {
 public:
  Geantino() : fGun(new G4ParticleGun(1)) {
    fGun->SetParticleDefinition(G4Geantino::Definition());
    fGun->SetParticleEnergy(1. * GeV);
    fGun->SetParticleMomentumDirection({0, 0, 1});
  }
  void GeneratePrimaries(G4Event* event) override { fGun->GeneratePrimaryVertex(event); }

 private:
  G4ParticleGun* fGun;
};

class ProbeRun : public G4UserRunAction {
 public:
  void BeginOfRunAction(const G4Run*) override {
    if (!G4Threading::IsMasterThread()) return;
    g4sim::WriteBack("g4sim_run", "./probe.json", {});
    std::ofstream("tolerance.txt") << G4GeometryTolerance::GetInstance()->GetSurfaceTolerance() << '\n';
  }
};

class Actions : public G4VUserActionInitialization {
 public:
  void BuildForMaster() const override { SetUserAction(new ProbeRun()); }
  void Build() const override {
    SetUserAction(new ProbeRun());
    SetUserAction(new Geantino());
  }
};

}  // namespace

int GeometryCheck(const Value& ir, const Value& card) {
  const Value& physics = card.at("physics", "run card");
  const Value& run = card.at("run", "run card");
  const int threads = run.has("threads") ? static_cast<int>(run.obj.at("threads").num) : 2;
  auto* manager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::MTOnly, threads);
  manager->SetUserInitialization(new NewDetector(ir.at("physical", "ir"), physics.at("cuts_mm", "physics")));
  std::string error;
  const auto text = [&](const char* key) { return physics.has(key) ? physics.obj.at(key).str : std::string(); };
  G4VModularPhysicsList* list = g4sim::BuildPhysicsList(text("reference_list"), text("em_constructor"), true, false,
                                                        Decimal(physics.at("cuts_mm", "physics").at("default", "cuts")), error);
  if (!list) {
    std::cerr << error << std::endl;
    return 2;
  }
  manager->SetUserInitialization(list);
  manager->SetUserInitialization(new Actions());
  std::printf("G4SIM_START %.3f\n", Now());
  manager->Initialize();
  std::printf("G4SIM_INITIALIZED %.3f\n", Now());
  std::fflush(stdout);
  manager->BeamOn(1);
  std::printf("G4SIM_DONE %.3f\n", Now());
  delete manager;
  return 0;
}
