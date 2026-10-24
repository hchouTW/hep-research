// layered_sim: a layered-geometry Geant4 simulation driven by a JSON spec (adapters/geant4, WP1 M2).
//
// Usage: layered_sim SPEC.json
// Order of set-up (Geant4 11.4): detector, physics list (its EM constructors call G4EmParameters::SetDefaults, so the
// /process/em, /process/msc and /process/eLoss commands exist only from here on), actions, then the spec's UI commands
// verbatim, then /run/initialize, the optional /geometry/test/run, the material dump, BeamOn, and the data-path record.
// Exit codes: 0 ok; 1 the run failed (a Geant4 fatal exception aborts with its own code; the probe changed the random
// state); 2 the spec was refused (also: an observable names a column the CSV does not have, an event weight other than
// 1 while the summary accumulates, an infinite or NaN number in the geometry).
// Output files are named by the spec; next to the CSV the program also writes column_map.json (simulation-columns/1),
// probe.json (the effective-config probe, g4sim/SimProbe.hh), and with output.observables summary.json
// (simulation-summary/1) and, with output.debug_observable_dump, observables_dump.csv. stdout carries the Geant4 log
// and, last, one line "LAYERED_SIM_STATUS {json}". A build with -DLAYERED_SIM_TEST_HOOKS=ON adds the UI command
// /layered_sim/test/probeAfterInitialize (tests only): the probe also runs after /run/initialize, before BeamOn, and
// writes probe.test.json, which must say recorded: false.
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
#include "Physics.hh"
#include "Randomize.hh"
#include "SimCsv.hh"
#include "SimObservables.hh"
#include "SimSummary.hh"
#include "Spec.hh"
#ifdef LAYERED_SIM_TEST_HOOKS
#include "G4UIcmdWithoutParameter.hh"
#include "G4UImessenger.hh"
#include "SimProbe.hh"
#endif

namespace {

const char* kDataVars[] = {"G4NEUTRONHPDATA", "G4LEDATA",        "G4LEVELGAMMADATA", "G4RADIOACTIVEDATA",
                           "G4PARTICLEXSDATA", "G4PIIDATA",      "G4REALSURFACEDATA", "G4SAIDXSDATA",
                           "G4ABLADATA",       "G4INCLDATA",     "G4ENSDFSTATEDATA", "G4CHANNELINGDATA",
                           "G4PARTICLEHPDATA", "G4NUDEXLIBDATA", "G4URRPTDATA",      "GEANT4_DATA_DIR"};

std::string Quote(const std::string& s) {
  std::string out = "\"";
  for (char c : s) {
    if (c == '"' || c == '\\') out += '\\';
    if (c == '\n') {
      out += "\\n";
      continue;
    }
    out += c;
  }
  return out + "\"";
}

std::string Num(double x) {
  char buf[40];
  std::snprintf(buf, sizeof buf, "%.10g", x);
  return buf;
}

std::map<std::string, std::string> DataEnv() {
  std::map<std::string, std::string> out;
  for (const char* v : kDataVars)
    if (const char* val = std::getenv(v)) out[v] = val;
  return out;
}

std::string EnvJson(const std::map<std::string, std::string>& env) {
  std::string s = "{";
  bool first = true;
  for (const auto& kv : env) {
    s += (first ? "" : ", ") + Quote(kv.first) + ": " + Quote(kv.second);
    first = false;
  }
  return s + "}";
}

int Status(const std::string& status, const std::string& error) {
  std::cout << "LAYERED_SIM_STATUS {\"status\": " << Quote(status)
            << (error.empty() ? "" : ", \"error\": " + Quote(error)) << "}" << std::endl;
  return status == "ok" ? 0 : status == "rejected" ? 2 : 1;
}

void WriteMaterials(const Detector& det, const std::string& path) {
  std::ofstream o(path);
  o << "{\"source\": \"Geant4 material table after /run/initialize (for material-budget closure only; never a "
       "reference input)\", \"materials\": [";
  bool first = true;
  for (const G4Material* m : det.UsedMaterials()) {
    o << (first ? "" : ", ") << "{\"name\": " << Quote(m->GetName())
      << ", \"density_g_cm3\": " << Num(m->GetDensity() / (g / cm3)) << ", \"radiation_length_cm\": "
      << Num(m->GetRadlen() / cm) << ", \"nuclear_interaction_length_cm\": " << Num(m->GetNuclearInterLength() / cm)
      << ", \"mean_excitation_energy_eV\": " << Num(m->GetIonisation()->GetMeanExcitationEnergy() / eV)
      << ", \"electron_density_per_cm3\": " << Num(m->GetElectronDensity() * cm3) << ", \"elements\": [";
    for (std::size_t i = 0; i < m->GetNumberOfElements(); ++i) {
      const G4Element* e = m->GetElement(static_cast<int>(i));
      o << (i ? ", " : "") << "{\"symbol\": " << Quote(e->GetSymbol()) << ", \"z\": " << Num(e->GetZ())
        << ", \"a_g_mole\": " << Num(e->GetA() / (g / mole)) << ", \"mass_fraction\": "
        << Num(m->GetFractionVector()[i]) << "}";
    }
    o << "]}";
    first = false;
  }
  o << "]}\n";
}

// Semantic name, unit and operational definition of a CSV column (simulation-columns/1; output.schema.json).
struct ColumnInfo {
  std::string semantic, unit, definition;
};

ColumnInfo Describe(const std::string& c, const std::vector<std::string>& slabs) {
  static const std::map<std::string, ColumnInfo> fixed = {
      {"event", {"event_number", "1", "global event number (first_event + Geant4 event ID)"}},
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
      {"edep_world_MeV", {"energy_deposit.world", "MeV", "deposit in the world volume"}},
      {"leak_gamma_MeV", {"leakage.gamma", "MeV", "kinetic energy of photons leaving the world"}},
      {"leak_e_MeV", {"leakage.electron", "MeV", "kinetic energy of e-+ leaving the world, plus 2 m_e c^2 for an e+"}},
      {"leak_nu_MeV", {"leakage.neutrino", "MeV", "neutrinos leaving the world"}},
      {"leak_other_MeV", {"leakage.other", "MeV", "every other particle leaving the world"}},
      {"leak_rear_MeV", {"leakage.rear", "MeV", "all leakage through the +x end face of the world"}},
      {"leak_front_MeV", {"leakage.front", "MeV", "all leakage through the -x end face of the world"}},
      {"leak_lateral_MeV", {"leakage.lateral", "MeV", "all leakage through the y and z faces of the world"}},
      {"killed_booked_MeV", {"killed.booked", "MeV",
                             "kinetic energy at the start of the step in which G4UserSpecialCuts killed a track"}},
      {"killed_unbooked_MeV", {"killed.unbooked", "MeV", "kinetic energy of secondaries killed at stacking"}},
      {"killed_eplus", {"killed.positrons", "1", "number of killed e+"}},
      {"exit_ekin_MeV", {"primary.exit_kinetic_energy", "MeV", "primary kinetic energy when it leaves the world"}},
      {"primary_eloss_MeV", {"primary.energy_loss", "MeV", "primary kinetic energy minus exit_ekin_MeV"}},
      {"exit_dx", {"primary.exit_direction.x", "1", "primary direction cosine x when it leaves the world"}},
      {"exit_dy", {"primary.exit_direction.y", "1", "primary direction cosine y when it leaves the world"}},
      {"exit_dz", {"primary.exit_direction.z", "1", "primary direction cosine z when it leaves the world"}},
      {"primary_fate", {"primary.fate", "1", "+1 transmitted (left going +x), -1 reflected, 0 stopped or absorbed"}},
      {"primary_end_x_mm", {"primary.end_position.x", "mm", "x where the primary ended or left"}},
      {"primary_end_process", {"primary.end_process", "", "process that ended the primary (Transportation when it "
                                                          "left the world; none if it never ended)"}},
      {"n_sec_gamma", {"secondaries.gamma", "1", "number of secondary photons"}},
      {"n_sec_electron", {"secondaries.electron", "1", "number of secondary electrons"}},
      {"n_sec_positron", {"secondaries.positron", "1", "number of secondary positrons"}},
      {"n_sec_other", {"secondaries.other", "1", "number of other secondaries"}},
  };
  auto it = fixed.find(c);
  if (it != fixed.end()) return it->second;
  for (const auto& s : slabs) {
    if (c == "edep_" + s + "_MeV")
      return {"energy_deposit." + s, "MeV", "weighted energy deposit summed over the copies of slab " + s};
    if (c == "chlen_" + s + "_mm")
      return {"charged_track_length." + s, "mm", "track length of charged particles in slab " + s};
    if (c == "plen_" + s + "_mm") return {"primary_path_length." + s, "mm", "path length of the primary in slab " + s};
  }
  if (c.rfind("edep_copy", 0) == 0)
    return {"energy_deposit." + c.substr(5, c.size() - 9), "MeV", "deposit in one placed slab copy"};
  return {c, "", ""};
}

void WriteColumnMap(const Spec& spec, const Detector& det) {
  using g4sim::JsonQuote;
  auto cols = CsvColumns(spec, det);
  std::map<std::string, std::string> units;
  std::ofstream o(spec.column_map_out);
  o << "{\"column_map_version\": \"simulation-columns/1\", \"producer\": \"layered_sim\", \"columns\": [";
  for (std::size_t i = 0; i < cols.size(); ++i) {
    ColumnInfo d = Describe(cols[i], det.SlabNames());
    units[cols[i]] = d.unit;
    o << (i ? ", " : "") << "{\"semantic\": " << JsonQuote(d.semantic) << ", \"column\": " << JsonQuote(cols[i])
      << ", \"unit\": " << JsonQuote(d.unit) << ", \"definition\": " << JsonQuote(d.definition)
      << ", \"file\": \"csv\", \"operation\": {\"kind\": \"rename\"}}";
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
}

#ifdef LAYERED_SIM_TEST_HOOKS
// Tests only: /layered_sim/test/probeAfterInitialize asks for the probe after /run/initialize, before BeamOn;
// /layered_sim/test/randomGun makes GeneratePrimaries draw the gun position from G4UniformRand.
class TestMessenger : public G4UImessenger {
 public:
  TestMessenger()
      : fProbe(new G4UIcmdWithoutParameter("/layered_sim/test/probeAfterInitialize", this)),
        fGun(new G4UIcmdWithoutParameter("/layered_sim/test/randomGun", this)) {
    fProbe->SetGuidance("tests only: run the probe after /run/initialize (it must write recorded: false)");
    fGun->SetGuidance("tests only: GeneratePrimaries draws the gun's y and z from G4UniformRand");
  }
  ~TestMessenger() override {
    delete fProbe;
    delete fGun;
  }
  void SetNewValue(G4UIcommand* cmd, G4String) override {
    if (cmd == fProbe) requested = true;
    if (cmd == fGun) TestRandomGun() = true;
  }
  bool requested = false;

 private:
  G4UIcmdWithoutParameter* fProbe;
  G4UIcmdWithoutParameter* fGun;
};
#endif

}  // namespace

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "usage: layered_sim SPEC.json" << std::endl;
    return Status("rejected", "usage: layered_sim SPEC.json");
  }
  Spec spec;
  try {
    spec = ReadSpec(argv[1]);
  } catch (const std::exception& e) {
    return Status("rejected", e.what());
  }
  auto envBefore = DataEnv();

  G4Random::setTheEngine(new CLHEP::MixMaxRng());
  long seeds[3] = {spec.seeds[0], spec.seeds[1], 0};
  G4Random::setTheSeeds(seeds);

  auto type = spec.run_manager == "mt" ? G4RunManagerType::MTOnly : G4RunManagerType::SerialOnly;
  auto* rm = G4RunManagerFactory::CreateRunManager(type, spec.run_manager == "mt" ? spec.threads : 1);

  auto* det = new Detector(spec);
  try {
    rm->SetUserInitialization(det);
    std::string err;
    G4VModularPhysicsList* phys = BuildPhysics(spec, err);
    if (!phys) return Status("rejected", err);
    rm->SetUserInitialization(phys);
  } catch (const std::exception& e) {
    return Status("rejected", e.what());
  }
  if (!G4ParticleTable::GetParticleTable()->FindParticle(spec.particle))
    return Status("rejected", "unknown particle " + spec.particle);
  rm->SetUserInitialization(new ActionInitialization(spec, *det));

  G4UImanager* ui = G4UImanager::GetUIpointer();
#ifdef LAYERED_SIM_TEST_HOOKS
  TestMessenger testHooks;
#endif
  for (const auto& cmd : spec.ui_commands) {
    int code = ui->ApplyCommand(cmd);
    std::cout << "LAYERED_SIM_UI " << Quote(cmd) << " " << code << std::endl;
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
    auto cols = CsvColumns(spec, *det);
    for (const auto& c : g4sim::NeededColumns(spec.observables))
      if (std::find(cols.begin(), cols.end(), c) == cols.end())
        return Status("rejected", "output.observables names column " + c + ", which the CSV does not have");
  }
#ifdef LAYERED_SIM_TEST_HOOKS
  if (testHooks.requested) {
    std::string dir = spec.probe_out.substr(0, spec.probe_out.size() - std::string("probe.json").size());
    std::ofstream(dir + "probe.test.json") << g4sim::RunProbe("test hook: after /run/initialize, before BeamOn").json;
  }
#endif
  WriteMaterials(*det, spec.materials_out);
  rm->BeamOn(static_cast<int>(spec.events));
  if (spec.run_manager == "mt") {
    g4sim::MergeThreadFiles(spec.csv, spec.threads, 2);  // line 1 "# SIMULATION", line 2 the column names
    if (spec.debug_observable_dump) g4sim::MergeThreadFiles(spec.dump_out, spec.threads, 2);
  }
  WriteColumnMap(spec, *det);

  std::ofstream dp(spec.datapaths_out);
  dp << "{\"geant4_version\": " << Quote(G4Version) << ", \"before_initialization\": " << EnvJson(envBefore)
     << ", \"after_run\": " << EnvJson(DataEnv()) << "}\n";
  dp.close();
  delete rm;
  if (Flags().weightRejected)
    return Status("rejected", "an event has weight != 1 while output.observables accumulates the run summary (A2.3)");
  if (Flags().summaryError) return Status("rejected", "an event could not be accumulated into the run summary");
  if (Flags().probeBadGeometry) return Status("rejected", "the probe found an infinite or NaN number in the geometry");
  if (Flags().probeRandomChanged) return Status("failed", "the probe changed the random-engine state");
  return Status("ok", "");
}
