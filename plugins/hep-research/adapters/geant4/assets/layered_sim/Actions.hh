// User actions of layered_sim: a particle gun, a per-event record filled at stepping and stacking level, and one CSV
// per thread (columns in output.schema.json). From adapter 0.2.0 (Geant4 program A2): optional per-event reseeding at
// the start of GeneratePrimaries (run.seeding per-event, g4sim/SimSeed.hh), the run summary of the declared observables
// accumulated per block and merged across threads through a G4VAccumulable (summary.json), an optional per-event dump
// of the observables' columns, and the effective-config probe on the master at the start of the run (probe.json).
#ifndef LAYERED_SIM_ACTIONS_HH
#define LAYERED_SIM_ACTIONS_HH

#include <atomic>
#include <fstream>
#include <string>
#include <vector>

#include "G4ThreeVector.hh"
#include "G4UserEventAction.hh"
#include "G4UserRunAction.hh"
#include "G4UserStackingAction.hh"
#include "G4UserSteppingAction.hh"
#include "G4VAccumulable.hh"
#include "G4VUserActionInitialization.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "SimSummary.hh"
#include "Spec.hh"

class Detector;
class G4ParticleGun;

struct EventRecord {
  std::vector<double> edep, chlen, plen, edepInst;
  double edepWorld = 0, leakGamma = 0, leakE = 0, leakNu = 0, leakOther = 0;
  double leakRear = 0, leakFront = 0, leakLateral = 0;  // the same leakage by the world face crossed
  double killedBooked = 0, killedUnbooked = 0;
  long killedEplus = 0;
  double exitEkin = 0;
  G4ThreeVector exitDir;
  int fate = 0;  // +1 transmitted (left the world going +x), -1 reflected, 0 stopped or absorbed
  double endX = 0;
  std::string endProcess;
  long nGamma = 0, nElectron = 0, nPositron = 0, nOther = 0;
  bool nonUnitWeight = false;  // a step of a track with weight != 1 (the summary refuses weighted accumulation)
  void Reset(std::size_t nSlabs, std::size_t nInst);
};

std::vector<std::string> CsvColumns(const Spec& spec, const Detector& det);

// What the run found that main() turns into an exit status after BeamOn.
struct RunFlags {
  std::atomic<bool> weightRejected{false};     // an event with weight != 1 while the summary accumulates (exit 2)
  std::atomic<bool> probeBadGeometry{false};   // an infinite or NaN number in the geometry (exit 2)
  std::atomic<bool> probeRandomChanged{false};  // the probe changed the random-engine state (exit 1)
  std::atomic<bool> summaryError{false};        // an event the summary could not accumulate (exit 2)
};
RunFlags& Flags();
#ifdef LAYERED_SIM_TEST_HOOKS
// Tests only (/layered_sim/test/randomGun): GeneratePrimaries draws the gun's y and z from G4UniformRand, so a test can
// show that per-event seeding keeps events independent of the split even when the generator draws random numbers.
std::atomic<bool>& TestRandomGun();
#endif

// The run summary of one thread, merged into the master's by G4AccumulableManager (same registration order on master
// and workers: one accumulable each).
class SummaryAccumulable : public G4VAccumulable {
 public:
  explicit SummaryAccumulable(const Spec& spec);
  void Merge(const G4VAccumulable& other) override;
  void Reset() override { fAcc.Reset(); }
  g4sim::SummaryAccumulator& Acc() { return fAcc; }

 private:
  g4sim::SummaryAccumulator fAcc;
};

class RunAction : public G4UserRunAction {
 public:
  RunAction(const Spec& spec, const Detector& det);
  void BeginOfRunAction(const G4Run*) override;
  void EndOfRunAction(const G4Run*) override;
  std::ofstream& Out() { return fOut; }
  std::ofstream& Dump() { return fDump; }
  SummaryAccumulable& Summary() { return fSummary; }

 private:
  void WriteProbe() const;
  void WriteSummary();
  const Spec& fSpec;
  const Detector& fDet;
  std::ofstream fOut, fDump;
  SummaryAccumulable fSummary;
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
  std::vector<std::string> fCols, fNeeded;  // CSV columns and the observables' columns (set at the first event)
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
// the same for the observable dump
std::string ThreadDumpPath(const Spec& spec, int thread);

#endif
