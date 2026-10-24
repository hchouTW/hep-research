// User actions of element_sim (Geant4 program B1.3, B1.4): a particle gun reseeded per event (A2.2), a per-event
// record filled at stepping level (deposits per element and copy, energy leaving the world, calorimeter leakage by
// face, plane crossings of every charged track, steps with a deposit), one CSV per thread with the summary columns,
// the run summary of the declared observables (merged across threads through a G4VAccumulable), the per-event ROOT
// file (EventFile.hh) and the effective-config probe on the master at the start of the run.
#ifndef ELEMENT_SIM_ACTIONS_HH
#define ELEMENT_SIM_ACTIONS_HH

#include <atomic>
#include <fstream>
#include <map>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

#include "EventFile.hh"
#include "G4ThreeVector.hh"
#include "G4UserEventAction.hh"
#include "G4UserRunAction.hh"
#include "G4UserSteppingAction.hh"
#include "G4VAccumulable.hh"
#include "G4VUserActionInitialization.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "SimSummary.hh"
#include "Spec.hh"

class Detector;
class G4ParticleGun;

// What main() knows before the run and the run row of the event file records.
struct RunInfo {
  std::string column_map_sha256, program_sources_sha256, geant4_version;
};

struct CrossingRow {
  int plane = 0, copy = 0, track = 0, parent = 0, pdg = 0;
  G4ThreeVector pos, dir;
  double ekin = 0, time = 0, edep = 0;
};

struct HitRow {
  int track = 0, step = 0, parent = 0, pdg = 0, volume = 0, copy = 0, process = -1;
  G4ThreeVector pre, post;
  double time = 0, edep = 0, length = 0;
};

struct EventRecord {
  std::vector<double> edep;  // per element, summed over copies
  std::vector<double> plen;  // path length of the primary (track 1) per element, summed over copies
  double edepWorld = 0, escapeWorld = 0;
  double leakRear = 0, leakFront = 0, leakLateral = 0;  // energy carried out of the calorimeter mother, by face
  bool nonUnitWeight = false, primaryLeftWorld = false, primaryEnteredCalo = false;
  std::map<std::pair<int, int>, std::pair<double, double>> deposits;  // (element, copy) -> (deposit, charged deposit)
  std::vector<CrossingRow> crossings;
  std::map<std::tuple<int, int, int>, std::size_t> crossingIndex;  // (plane, copy, track) -> row
  std::vector<HitRow> hits;
  void Reset(std::size_t nElements);
};

// The per-event CSV columns of a spec (element_spec.py csv_columns is the Python twin).
std::vector<std::string> CsvColumns(const Spec& spec);

struct RunFlags {
  std::atomic<bool> weightRejected{false};      // an event with weight != 1 while the summary accumulates (exit 2)
  std::atomic<bool> probeBadGeometry{false};    // an infinite or NaN number in the geometry (exit 2)
  std::atomic<bool> probeRandomChanged{false};  // the probe changed the random-engine state (exit 1)
  std::atomic<bool> summaryError{false};        // an event the summary could not accumulate (exit 2)
};
RunFlags& Flags();

#ifdef ELEMENT_SIM_TEST_HOOKS
struct TestHooks {
  std::atomic<bool> reportFieldManagers{false};  // every thread prints its field-manager pointers at the run start
  std::atomic<bool> primaryOnlyCrossings{false};  // record crossings of the primary (track 1) only
};
TestHooks& Hooks();
#endif

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
  RunAction(const Spec& spec, const Detector& det, const RunInfo& info);
  void BeginOfRunAction(const G4Run*) override;
  void EndOfRunAction(const G4Run*) override;
  std::ofstream& Out() { return fOut; }
  std::ofstream& Dump() { return fDump; }
  SummaryAccumulable& Summary() { return fSummary; }
  EventFile& Events() { return fEventFile; }
  int ProcessId(const std::string& name) const;

 private:
  void FillRunRows();
  const Spec& fSpec;
  const Detector& fDet;
  const RunInfo& fInfo;
  std::ofstream fOut, fDump;
  SummaryAccumulable fSummary;
  EventFile fEventFile;
  std::map<std::string, int> fProcessIds;  // deterministic: process names sorted, numbered from 0
};

class EventAction : public G4UserEventAction {
 public:
  EventAction(const Spec& spec, RunAction* run) : fSpec(spec), fRun(run) {}
  void BeginOfEventAction(const G4Event*) override;
  void EndOfEventAction(const G4Event*) override;
  EventRecord& Record() { return fRec; }

 private:
  void FillEventFile(long number, const G4Event* event);
  const Spec& fSpec;
  RunAction* fRun;
  EventRecord fRec;
  std::vector<std::string> fCols, fNeeded;
};

class SteppingAction : public G4UserSteppingAction {
 public:
  SteppingAction(const Spec& spec, const Detector& det, EventAction* ev, RunAction* run);
  void UserSteppingAction(const G4Step*) override;

 private:
  const Spec& fSpec;
  const Detector& fDet;
  EventAction* fEv;
  RunAction* fRun;
  int fCalo;                    // element index of the calorimeter mother, or -1
  std::vector<bool> fInCalo;    // element is the calorimeter mother or one of its daughters
  std::vector<bool> fPlane;     // element role is tracker-plane or tof-layer
  bool fLevelSummary, fLevelCrossings, fLevelHits;  // the event file's level
};

class PrimaryGenerator : public G4VUserPrimaryGeneratorAction {
 public:
  explicit PrimaryGenerator(const Spec& spec);
  ~PrimaryGenerator() override;
  void GeneratePrimaries(G4Event*) override;

 private:
  const Spec& fSpec;
  G4ParticleGun* fGun;
};

class ActionInitialization : public G4VUserActionInitialization {
 public:
  ActionInitialization(const Spec& spec, const Detector& det, const RunInfo& info)
      : fSpec(spec), fDet(det), fInfo(info) {}
  void BuildForMaster() const override;
  void Build() const override;

 private:
  const Spec& fSpec;
  const Detector& fDet;
  const RunInfo& fInfo;
};

std::string ThreadPath(const Spec& spec, const std::string& path, int thread);

#endif
