// User actions of layered_sim: a particle gun, a per-event record filled at stepping and stacking level, and one CSV
// per thread (columns in output.schema.json).
#ifndef LAYERED_SIM_ACTIONS_HH
#define LAYERED_SIM_ACTIONS_HH

#include <fstream>
#include <string>
#include <vector>

#include "G4ThreeVector.hh"
#include "G4UserEventAction.hh"
#include "G4UserRunAction.hh"
#include "G4UserStackingAction.hh"
#include "G4UserSteppingAction.hh"
#include "G4VUserActionInitialization.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "Spec.hh"

class Detector;
class G4ParticleGun;

struct EventRecord {
  std::vector<double> edep, chlen, plen, edepInst;
  double edepWorld = 0, leakGamma = 0, leakE = 0, leakNu = 0, leakOther = 0;
  double killedBooked = 0, killedUnbooked = 0;
  long killedEplus = 0;
  double exitEkin = 0;
  G4ThreeVector exitDir;
  int fate = 0;  // +1 transmitted (left the world going +x), -1 reflected, 0 stopped or absorbed
  double endX = 0;
  std::string endProcess;
  long nGamma = 0, nElectron = 0, nPositron = 0, nOther = 0;
  void Reset(std::size_t nSlabs, std::size_t nInst);
};

std::vector<std::string> CsvColumns(const Spec& spec, const Detector& det);

class RunAction : public G4UserRunAction {
 public:
  RunAction(const Spec& spec, const Detector& det) : fSpec(spec), fDet(det) {}
  void BeginOfRunAction(const G4Run*) override;
  void EndOfRunAction(const G4Run*) override;
  std::ofstream& Out() { return fOut; }

 private:
  const Spec& fSpec;
  const Detector& fDet;
  std::ofstream fOut;
};

class EventAction : public G4UserEventAction {
 public:
  EventAction(const Spec& spec, const Detector& det, RunAction* run) : fSpec(spec), fDet(det), fRun(run) {}
  void BeginOfEventAction(const G4Event*) override;
  void EndOfEventAction(const G4Event*) override;
  EventRecord& Record() { return fRec; }

 private:
  const Spec& fSpec;
  const Detector& fDet;
  RunAction* fRun;
  EventRecord fRec;
};

class SteppingAction : public G4UserSteppingAction {
 public:
  SteppingAction(const Spec& spec, const Detector& det, EventAction* ev) : fSpec(spec), fDet(det), fEv(ev) {}
  void UserSteppingAction(const G4Step*) override;

 private:
  const Spec& fSpec;
  const Detector& fDet;
  EventAction* fEv;
};

class StackingAction : public G4UserStackingAction {
 public:
  StackingAction(const Spec& spec, EventAction* ev) : fSpec(spec), fEv(ev) {}
  G4ClassificationOfNewTrack ClassifyNewTrack(const G4Track*) override;

 private:
  const Spec& fSpec;
  EventAction* fEv;
};

class PrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  PrimaryGenerator(const Spec& spec, const Detector& det);
  ~PrimaryGenerator() override;
  void GeneratePrimaries(G4Event*) override;

 private:
  const Spec& fSpec;
  const Detector& fDet;
  G4ParticleGun* fGun;
};

class ActionInitialization : public G4VUserActionInitialization {
 public:
  ActionInitialization(const Spec& spec, const Detector& det) : fSpec(spec), fDet(det) {}
  void BuildForMaster() const override;
  void Build() const override;

 private:
  const Spec& fSpec;
  const Detector& fDet;
};

// path of the CSV this thread writes: the spec's path in serial mode, path.thread<N> for worker N in MT mode
std::string ThreadCsvPath(const Spec& spec, int thread);

#endif
