// layered_sim: a layered-geometry Geant4 simulation driven by a JSON spec (adapters/geant4, WP1 M2).
//
// Usage: layered_sim SPEC.json
// Order of set-up (Geant4 11.4): detector, physics list (its EM constructors call G4EmParameters::SetDefaults, so the
// /process/em, /process/msc and /process/eLoss commands exist only from here on), actions, then the spec's UI commands
// verbatim, then /run/initialize, the optional /geometry/test/run, the material dump, BeamOn, and the data-path record.
// Exit codes: 0 ok; 1 the run failed (a Geant4 fatal exception aborts with its own code); 2 the spec was refused.
// Output files are named by the spec; stdout carries the Geant4 log and, last, one line "LAYERED_SIM_STATUS {json}".
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
#include "Spec.hh"

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

// worker CSVs joined in event order (MT): the header of the first file, then every row sorted by event number
void MergeThreadCsv(const Spec& spec) {
  std::vector<std::pair<long, std::string>> rows;
  std::string header;
  for (int t = 0; t < spec.threads; ++t) {
    std::string path = ThreadCsvPath(spec, t);
    std::ifstream in(path);
    if (!in) continue;
    std::string line;
    int n = 0;
    while (std::getline(in, line)) {
      if (++n <= 2) {  // line 1 is "# SIMULATION", line 2 the column names
        if (n == 2 && header.empty()) header = "# SIMULATION\n" + line + "\n";
        continue;
      }
      rows.emplace_back(std::stol(line.substr(0, line.find(','))), line);
    }
    in.close();
    std::remove(path.c_str());
  }
  std::sort(rows.begin(), rows.end());
  std::ofstream out(spec.csv);
  out << header;
  for (const auto& r : rows) out << r.second << "\n";
}

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
  WriteMaterials(*det, spec.materials_out);
  rm->BeamOn(static_cast<int>(spec.events));
  if (spec.run_manager == "mt") MergeThreadCsv(spec);

  std::ofstream dp(spec.datapaths_out);
  dp << "{\"geant4_version\": " << Quote(G4Version) << ", \"before_initialization\": " << EnvJson(envBefore)
     << ", \"after_run\": " << EnvJson(DataEnv()) << "}\n";
  dp.close();
  delete rm;
  return Status("ok", "");
}
