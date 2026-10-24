// element_sim: a box-element Geant4 simulation driven by a JSON spec (adapters/geant4, Geant4 program B1). Written from
// the Geant4 11.4 API; no example code (B5 or any other) was copied or adapted.
//
// Usage: element_sim SPEC.json   (run in the run folder; every output file is written there)
// Order of set-up (as layered_sim): detector, physics list (G4StepLimiterPhysics added when the spec has a field),
// actions, the spec's UI commands verbatim, /run/initialize, the optional /geometry/test/run, the material dump, the
// column map (written before BeamOn so that the event file's run row can carry its hash), BeamOn, the per-thread CSVs
// merged, and the data-path record. Seeding is always per-event: event i of logical run S starts from
// (H(S, i, 0), H(S, i, 1)) at the start of GeneratePrimaries (g4sim/SimSeed.hh).
// Outputs: events.csv (summary columns per event), materials.json, datapaths.json, column_map.json
// (simulation-columns/1), probe.json (the effective-config probe), summary.json with output.observables
// (simulation-summary/1), observables_dump.csv with output.debug_observable_dump, and events.root at event-file level
// summary or above (element_sim.events/1, EventFile.hh). The environment variable ELEMENT_SIM_SOURCES_SHA256 (set by
// geant4_run.py) is copied into the event file's run row. stdout carries the Geant4 log and, last, one line
// "ELEMENT_SIM_STATUS {json}".
// Exit codes: 0 ok; 1 the run failed (a Geant4 fatal exception aborts with its own code; the probe changed the random
// state); 2 the spec was refused (also: an observable names a column the CSV does not have, an event weight other
// than 1 while the summary accumulates, an infinite or NaN number in the geometry, hits level above its event limit).
// A build with -DELEMENT_SIM_TEST_HOOKS=ON adds the UI commands /element_sim/test/reportFieldManagers (every thread
// prints its field managers' addresses at the run start) and /element_sim/test/primaryOnlyCrossings (tests only).
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include "Actions.hh"
#include "Detector.hh"
#include "EventFile.hh"
#include "G4Element.hh"
#include "G4IonisParamMat.hh"
#include "G4Material.hh"
#include "G4ParticleTable.hh"
#include "G4RunManager.hh"
#include "G4RunManagerFactory.hh"
#include "G4SystemOfUnits.hh"
#include "G4UImanager.hh"
#include "G4VModularPhysicsList.hh"
#include "G4Version.hh"
#include "MiniJson.hh"
#include "Randomize.hh"
#include "SimCsv.hh"
#include "SimHash.hh"
#include "SimObservables.hh"
#include "SimPhysics.hh"
#include "SimSummary.hh"
#include "Spec.hh"
#ifdef ELEMENT_SIM_TEST_HOOKS
#include "G4UIcmdWithoutParameter.hh"
#include "G4UImessenger.hh"
#endif

namespace {

using g4sim::JsonQuote;

const char* kDataVars[] = {"G4NEUTRONHPDATA", "G4LEDATA",        "G4LEVELGAMMADATA", "G4RADIOACTIVEDATA",
                           "G4PARTICLEXSDATA", "G4PIIDATA",      "G4REALSURFACEDATA", "G4SAIDXSDATA",
                           "G4ABLADATA",       "G4INCLDATA",     "G4ENSDFSTATEDATA", "G4CHANNELINGDATA",
                           "G4PARTICLEHPDATA", "G4NUDEXLIBDATA", "G4URRPTDATA",      "GEANT4_DATA_DIR"};

std::string Num(double x) {
  char buf[40];
  std::snprintf(buf, sizeof buf, "%.10g", x);
  return buf;
}

std::string EnvJson() {
  std::string s = "{";
  bool first = true;
  for (const char* v : kDataVars)
    if (const char* val = std::getenv(v)) {
      s += (first ? "" : ", ") + JsonQuote(v) + ": " + JsonQuote(val);
      first = false;
    }
  return s + "}";
}

int Status(const std::string& status, const std::string& error) {
  std::cout << "ELEMENT_SIM_STATUS {\"status\": " << JsonQuote(status)
            << (error.empty() ? "" : ", \"error\": " + JsonQuote(error)) << "}" << std::endl;
  return status == "ok" ? 0 : status == "rejected" ? 2 : 1;
}

void WriteMaterials(const Detector& det, const std::string& path) {
  std::ofstream o(path);
  o << "{\"source\": \"Geant4 material table after /run/initialize (for material-budget closure only; never a "
       "reference input)\", \"materials\": [";
  bool first = true;
  for (const G4Material* m : det.UsedMaterials()) {
    o << (first ? "" : ", ") << "{\"name\": " << JsonQuote(m->GetName())
      << ", \"density_g_cm3\": " << Num(m->GetDensity() / (g / cm3)) << ", \"radiation_length_cm\": "
      << Num(m->GetRadlen() / cm) << ", \"nuclear_interaction_length_cm\": " << Num(m->GetNuclearInterLength() / cm)
      << ", \"mean_excitation_energy_eV\": " << Num(m->GetIonisation()->GetMeanExcitationEnergy() / eV)
      << ", \"electron_density_per_cm3\": " << Num(m->GetElectronDensity() * cm3) << ", \"elements\": [";
    for (std::size_t i = 0; i < m->GetNumberOfElements(); ++i) {
      const G4Element* e = m->GetElement(static_cast<int>(i));
      o << (i ? ", " : "") << "{\"symbol\": " << JsonQuote(e->GetSymbol()) << ", \"z\": " << Num(e->GetZ())
        << ", \"a_g_mole\": " << Num(e->GetA() / (g / mole)) << ", \"mass_fraction\": "
        << Num(m->GetFractionVector()[i]) << "}";
    }
    o << "]}";
    first = false;
  }
  o << "]}\n";
}

struct ColumnInfo {
  std::string semantic, unit, definition;
};

ColumnInfo Describe(const std::string& c, const Spec& spec) {
  static const std::map<std::string, ColumnInfo> fixed = {
      {"event", {"event_number", "1", "global event number (first_event + Geant4 event ID)"}},
      {"event_id", {"event_number", "1", "global event number (first_event + Geant4 event ID)"}},
      {"chunk", {"chunk_index", "1", "chunk number of the job"}},
      {"weight", {"event_weight", "1", "primary vertex weight"}},
      {"primary_pdg", {"primary.pdg_code", "1", "PDG code of the primary"}},
      {"primary_ekin_MeV", {"primary.kinetic_energy", "MeV", "primary kinetic energy"}},
      {"primary_x_mm", {"primary.position.x", "mm", "gun position x"}},
      {"primary_y_mm", {"primary.position.y", "mm", "gun position y"}},
      {"primary_z_mm", {"primary.position.z", "mm", "gun position z"}},
      {"primary_dx", {"primary.direction.x", "1", "primary direction cosine x"}},
      {"primary_dy", {"primary.direction.y", "1", "primary direction cosine y"}},
      {"primary_dz", {"primary.direction.z", "1", "primary direction cosine z"}},
      {"edep_world_MeV", {"energy_deposit.world", "MeV", "deposit in the world volume outside every element"}},
      {"escape_world_MeV", {"leakage.world", "MeV",
                            "energy carried out of the world: kinetic energy, plus 2 m_e c^2 for an e+, times weight"}},
      {"leak_rear_MeV", {"leakage.rear", "MeV",
                         "net energy carried out of the calorimeter mother through its +x face (kinetic, plus 2 m_e "
                         "c^2 for an e+, times weight; energy carried back in through the face is subtracted)"}},
      {"leak_front_MeV", {"leakage.front", "MeV", "the same through the calorimeter mother's -x face"}},
      {"leak_lateral_MeV", {"leakage.lateral", "MeV", "the same through the calorimeter mother's y and z faces"}},
      {"flags", {"event.flags", "1", "bit 0: a track had weight != 1; bit 1: the primary left the world"}},
  };
  auto it = fixed.find(c);
  if (it != fixed.end()) return it->second;
  for (const auto& e : spec.elements)
    if (c == "edep_" + e.name + "_MeV")
      return {"energy_deposit." + e.name, "MeV", "weighted energy deposit summed over the copies of element " + e.name};
    else if (c == "plen_" + e.name + "_mm")
      return {"primary_path_length." + e.name, "mm", "path length of the primary (track 1) in element " + e.name +
                                                     ", summed over its copies"};
  return {c, "", ""};
}

ColumnInfo DescribeRoot(const std::string& ntuple, const NtupleColumn& col, const Spec& spec) {
  if (ntuple == "events") return Describe(col.name, spec);
  static const std::map<std::string, std::string> units = {
      {"x_mm", "mm"},       {"y_mm", "mm"},     {"z_mm", "mm"},     {"pre_x_mm", "mm"},  {"pre_y_mm", "mm"},
      {"pre_z_mm", "mm"},   {"post_x_mm", "mm"}, {"post_y_mm", "mm"}, {"post_z_mm", "mm"}, {"step_mm", "mm"},
      {"ekin_MeV", "MeV"},  {"edep_MeV", "MeV"}, {"edep_charged_MeV", "MeV"}, {"t_ns", "ns"}};
  auto u = units.find(col.name);
  std::string unit = u != units.end() ? u->second : (col.type == 'S' ? "" : "1");
  static const std::map<std::string, std::string> what = {
      {"crossings", "pre-step point of a charged track's first entry into a tracker plane or TOF layer (its deposit "
                    "in that plane in edep_MeV)"},
      {"deposits", "deposit per event and element copy (volume_id is the element index in the spec)"},
      {"hits", "step with a deposit (pre and post points, time at the pre point, defining process)"},
      {"processes", "process number table (process names sorted)"},
      {"run", "one row per file: hashes, versions, seeds and the column list of every ntuple"}};
  return {ntuple + "." + col.name, unit, what.count(ntuple) ? what.at(ntuple) : ""};
}

std::string ColumnMap(const Spec& spec) {
  std::ostringstream o;
  auto cols = CsvColumns(spec);
  std::map<std::string, std::string> units;
  o << "{\"column_map_version\": \"simulation-columns/1\", \"producer\": \"element_sim\", \"columns\": [";
  bool first = true;
  for (const auto& c : cols) {
    ColumnInfo d = Describe(c, spec);
    units[c] = d.unit;
    o << (first ? "" : ", ") << "{\"semantic\": " << JsonQuote(d.semantic) << ", \"column\": " << JsonQuote(c)
      << ", \"unit\": " << JsonQuote(d.unit) << ", \"definition\": " << JsonQuote(d.definition)
      << ", \"file\": \"csv\", \"operation\": {\"kind\": \"rename\"}}";
    first = false;
  }
  for (const auto& def : EventFileNtuples(spec))
    for (const auto& col : def.columns) {
      ColumnInfo d = DescribeRoot(def.name, col, spec);
      o << ", {\"semantic\": " << JsonQuote(d.semantic) << ", \"column\": " << JsonQuote(col.name)
        << ", \"unit\": " << JsonQuote(d.unit) << ", \"definition\": " << JsonQuote(d.definition)
        << ", \"file\": \"root\", \"ntuple\": " << JsonQuote(def.name) << ", \"operation\": {\"kind\": \"rename\"}}";
    }
  for (const auto& obs : spec.observables) {
    o << ", {\"semantic\": " << JsonQuote("observable." + obs.name) << ", \"column\": " << JsonQuote(obs.name)
      << ", \"unit\": " << JsonQuote(units[obs.source_column]) << ", \"definition\": "
      << JsonQuote("per-block accumulators of " + obs.source_column + " over the events the selection keeps")
      << ", \"file\": \"summary\", \"operation\": {\"kind\": " << (obs.selection.empty() ? "\"rename\"" : "\"filter\"")
      << ", \"source_column\": " << JsonQuote(obs.source_column) << ", \"selection\": [";
    for (std::size_t c = 0; c < obs.selection.size(); ++c) {
      const auto& sel = obs.selection[c];
      o << (c ? ", " : "") << "{\"column\": " << JsonQuote(sel.column) << ", \"op\": " << JsonQuote(sel.op)
        << ", \"value\": " << (sel.value.isNumber ? g4sim::JsonNum(sel.value.num) : JsonQuote(sel.value.str)) << "}";
    }
    o << "]}}";
  }
  o << "]}\n";
  return o.str();
}

#ifdef ELEMENT_SIM_TEST_HOOKS
class TestMessenger : public G4UImessenger {
 public:
  TestMessenger()
      : fField(new G4UIcmdWithoutParameter("/element_sim/test/reportFieldManagers", this)),
        fPrimary(new G4UIcmdWithoutParameter("/element_sim/test/primaryOnlyCrossings", this)) {
    fField->SetGuidance("tests only: every thread prints its field managers' addresses at the start of the run");
    fPrimary->SetGuidance("tests only: record the crossings of the primary (track 1) only");
  }
  ~TestMessenger() override {
    delete fField;
    delete fPrimary;
  }
  void SetNewValue(G4UIcommand* cmd, G4String) override {
    if (cmd == fField) Hooks().reportFieldManagers = true;
    if (cmd == fPrimary) Hooks().primaryOnlyCrossings = true;
  }

 private:
  G4UIcmdWithoutParameter* fField;
  G4UIcmdWithoutParameter* fPrimary;
};
#endif

}  // namespace

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "usage: element_sim SPEC.json" << std::endl;
    return Status("rejected", "usage: element_sim SPEC.json");
  }
  Spec spec;
  try {
    spec = ReadSpec(argv[1]);
  } catch (const std::exception& e) {
    return Status("rejected", e.what());
  }
  std::string envBefore = EnvJson();

  G4Random::setTheEngine(new CLHEP::MixMaxRng());
  long seeds[3] = {spec.seeds[0], spec.seeds[1], 0};
  G4Random::setTheSeeds(seeds);

  auto type = spec.run_manager == "mt" ? G4RunManagerType::MTOnly : G4RunManagerType::SerialOnly;
  auto* rm = G4RunManagerFactory::CreateRunManager(type, spec.run_manager == "mt" ? spec.threads : 1);
  RunInfo info;
  if (const char* src = std::getenv("ELEMENT_SIM_SOURCES_SHA256")) info.program_sources_sha256 = src;
  info.geant4_version = G4Version;
  auto* det = new Detector(spec);
  try {
    rm->SetUserInitialization(det);
    std::string err;
    G4VModularPhysicsList* phys = g4sim::BuildPhysicsList(spec.reference_list, spec.em_constructor, spec.decay,
                                                          spec.HasField(), spec.default_cut_mm, err);
    if (!phys) return Status("rejected", err);
    rm->SetUserInitialization(phys);
  } catch (const std::exception& e) {
    return Status("rejected", e.what());
  }
  if (!G4ParticleTable::GetParticleTable()->FindParticle(spec.particle))
    return Status("rejected", "unknown particle " + spec.particle);
  rm->SetUserInitialization(new ActionInitialization(spec, *det, info));

  G4UImanager* ui = G4UImanager::GetUIpointer();
#ifdef ELEMENT_SIM_TEST_HOOKS
  TestMessenger testHooks;
#endif
  for (const auto& cmd : spec.ui_commands) {
    int code = ui->ApplyCommand(cmd);
    std::cout << "ELEMENT_SIM_UI " << JsonQuote(cmd) << " " << code << std::endl;
    if (code != 0) return Status("rejected", "UI command refused (code " + std::to_string(code) + "): " + cmd);
  }
  try {
    if (ui->ApplyCommand("/run/initialize") != 0) return Status("failed", "/run/initialize failed");
  } catch (const std::exception& e) {
    return Status("rejected", e.what());
  }
  if (spec.overlap_test_points > 0) {
    ui->ApplyCommand("/geometry/test/resolution " + std::to_string(spec.overlap_test_points));
    ui->ApplyCommand("/geometry/test/run");
  }
  {
    auto cols = CsvColumns(spec);
    for (const auto& c : g4sim::NeededColumns(spec.observables))
      if (std::find(cols.begin(), cols.end(), c) == cols.end())
        return Status("rejected", "output.observables names column " + c + ", which the CSV does not have");
  }
  WriteMaterials(*det, spec.materials_out);
  std::string cmap = ColumnMap(spec);
  std::ofstream(spec.column_map_out, std::ios::binary) << cmap;
  info.column_map_sha256 = g4sim::Sha256::HexOf(cmap);
  rm->BeamOn(static_cast<int>(spec.events));
  if (spec.run_manager == "mt") {
    g4sim::MergeThreadFiles(spec.csv, spec.threads, 2);  // line 1 "# SIMULATION", line 2 the column names
    if (spec.debug_observable_dump) g4sim::MergeThreadFiles(spec.dump_out, spec.threads, 2);
  }
  std::ofstream dp(spec.datapaths_out);
  dp << "{\"geant4_version\": " << JsonQuote(G4Version) << ", \"before_initialization\": " << envBefore
     << ", \"after_run\": " << EnvJson() << "}\n";
  dp.close();
  delete rm;
  if (Flags().weightRejected)
    return Status("rejected", "an event has weight != 1 while output.observables accumulates the run summary (A2.3)");
  if (Flags().summaryError) return Status("rejected", "an event could not be accumulated into the run summary");
  if (Flags().probeBadGeometry) return Status("rejected", "the probe found an infinite or NaN number in the geometry");
  if (Flags().probeRandomChanged) return Status("failed", "the probe changed the random-engine state");
  return Status("ok", "");
}
