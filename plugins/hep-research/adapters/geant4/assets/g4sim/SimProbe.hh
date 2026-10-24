// g4sim/SimProbe.hh: the effective-config probe of Geant4 runs (adapters/geant4, Geant4 program A2.4). Geant4 API only;
// written from the Geant4 API (no example code copied or adapted).
//
// Called once per run on the master in BeginOfRunAction (inside G4RunManager::RunInitialization, after the kernel
// closed the geometry); workers are assumed identical. It records what Geant4 actually resolved: the geometry as a flat
// list of logical volumes and placements (from G4PhysicalVolumeStore, in creation order, each placement with its
// mother logical volume), materials as resolved (composition, density, state), the EM parameters (full text of
// G4EmParameters::StreamInfo plus parsed fields), the production cuts per material-cuts couple, the hadronic models per
// particle and process with their energy ranges per material and element (GetMinEnergy/GetMaxEnergy and IsBlocked;
// never GetHadronicInteraction or ChooseHadronicInteraction, which draw random numbers on overlapping ranges), the
// sub-processes of the general gamma and neutron processes, user limits, biasing wrappers, field managers (from adapter
// 0.3.0 with each field's value, accuracy parameters and the actual stepper and driver classes, and the list of
// distinct field managers with the volume each was attached to), the run manager type and the random-number status
// flags. Numbers are strings in the format of Python's float.hex()
// (SimHash.hh PyFloatHex); integers are JSON integers.
//
// The probe draws no random numbers; it compares the engine state (put()) before and after itself and reports
// random_state_unchanged. It is recorded only in state G4State_GeomClosed with more than zero couples; otherwise it
// writes recorded: false (the run still completes, but cannot upgrade). An infinite or NaN number in the geometry is an
// error (the caller exits 2). The canonical tree-v1 form and its hashes (tree_sha256, naming_sha256, target hash) are
// computed from this flat list by contracts/validate.py (geant4_tree_v1), one implementation for every program.
#ifndef G4SIM_SIMPROBE_HH
#define G4SIM_SIMPROBE_HH

#include <cxxabi.h>

#include <cmath>
#include <cstdlib>
#include <map>
#include <typeinfo>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include "G4ApplicationState.hh"
#include "G4Box.hh"
#include "G4ChordFinder.hh"
#include "G4Element.hh"
#include "G4EmParameters.hh"
#include "G4FieldManager.hh"
#include "G4GammaGeneralProcess.hh"
#include "G4HadronicInteraction.hh"
#include "G4HadronicProcess.hh"
#include "G4HadronicProcessType.hh"
#include "G4IonisParamMat.hh"
#include "G4LogicalVolume.hh"
#include "G4MTRunManager.hh"
#include "G4MagIntegratorStepper.hh"
#include "G4Material.hh"
#include "G4MaterialCutsCouple.hh"
#include "G4NeutronGeneralProcess.hh"
#include "G4ParticleTable.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4ProcessManager.hh"
#include "G4ProcessVector.hh"
#include "G4ProductionCuts.hh"
#include "G4ProductionCutsTable.hh"
#include "G4Region.hh"
#include "G4RegionStore.hh"
#include "G4RunManager.hh"
#include "G4StateManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4TaskRunManager.hh"
#include "G4Track.hh"
#include "G4TransportationManager.hh"
#include "G4Trd.hh"
#include "G4Tubs.hh"
#include "G4UniformMagField.hh"
#include "G4UserLimits.hh"
#include "G4VIntegrationDriver.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VSolid.hh"
#include "G4Version.hh"
#include "Randomize.hh"
#include "SimHash.hh"
#include "SimSummary.hh"

namespace g4sim {

constexpr const char* kProbeVersion = "g4sim-probe/1";

struct ProbeResult {
  std::string json;
  bool recorded = false;
  bool randomUnchanged = true;
  std::string error;  // non-empty: the geometry has an infinite or NaN number (exit 2)
};

namespace probe_detail {

class Writer {
 public:
  // A number as a float.hex() string; non-finite numbers in the geometry are flagged.
  std::string Hex(double x, bool geometry = false) {
    if (geometry && !std::isfinite(x)) fBadGeometry = true;
    return JsonQuote(PyFloatHex(x));
  }
  bool BadGeometry() const { return fBadGeometry; }

 private:
  bool fBadGeometry = false;
};

inline std::string Join(const std::vector<std::string>& items) {
  std::string out = "[";
  for (std::size_t i = 0; i < items.size(); ++i) out += (i ? ", " : "") + items[i];
  return out + "]";
}

inline std::string Solid(const G4VSolid* s, Writer& w) {
  std::ostringstream o;
  o << "{\"type\": " << JsonQuote(s->GetEntityType()) << ", \"parameters\": ";
  if (auto* b = dynamic_cast<const G4Box*>(s)) {
    o << "{\"half_x_mm\": " << w.Hex(b->GetXHalfLength() / mm, true) << ", \"half_y_mm\": "
      << w.Hex(b->GetYHalfLength() / mm, true) << ", \"half_z_mm\": " << w.Hex(b->GetZHalfLength() / mm, true) << "}";
  } else if (auto* t = dynamic_cast<const G4Tubs*>(s)) {
    o << "{\"rmin_mm\": " << w.Hex(t->GetInnerRadius() / mm, true) << ", \"rmax_mm\": "
      << w.Hex(t->GetOuterRadius() / mm, true) << ", \"half_z_mm\": " << w.Hex(t->GetZHalfLength() / mm, true)
      << ", \"start_phi_rad\": " << w.Hex(t->GetStartPhiAngle(), true) << ", \"delta_phi_rad\": "
      << w.Hex(t->GetDeltaPhiAngle(), true) << "}";
  } else if (auto* d = dynamic_cast<const G4Trd*>(s)) {
    o << "{\"half_x1_mm\": " << w.Hex(d->GetXHalfLength1() / mm, true) << ", \"half_x2_mm\": "
      << w.Hex(d->GetXHalfLength2() / mm, true) << ", \"half_y1_mm\": " << w.Hex(d->GetYHalfLength1() / mm, true)
      << ", \"half_y2_mm\": " << w.Hex(d->GetYHalfLength2() / mm, true) << ", \"half_z_mm\": "
      << w.Hex(d->GetZHalfLength() / mm, true) << "}";
  } else {
    o << "null, \"gap\": \"solid type not decoded by the probe; parameters not recorded\"";
  }
  o << "}";
  return o.str();
}

inline std::string State(G4State s) {
  return s == kStateGas ? "gas" : s == kStateLiquid ? "liquid" : s == kStateSolid ? "solid" : "undefined";
}

inline std::string MaterialJson(const G4Material* m, Writer& w) {
  std::ostringstream o;
  o << "{\"name\": " << JsonQuote(m->GetName()) << ", \"density_g_cm3\": " << w.Hex(m->GetDensity() / (g / cm3), true)
    << ", \"state\": " << JsonQuote(State(m->GetState())) << ", \"temperature_K\": "
    << w.Hex(m->GetTemperature() / kelvin, true) << ", \"pressure_Pa\": " << w.Hex(m->GetPressure() / pascal, true)
    << ", \"mean_excitation_energy_eV\": " << w.Hex(m->GetIonisation()->GetMeanExcitationEnergy() / eV, true)
    << ", \"elements\": [";
  for (std::size_t i = 0; i < m->GetNumberOfElements(); ++i) {
    const G4Element* e = m->GetElement(static_cast<G4int>(i));
    o << (i ? ", " : "") << "{\"symbol\": " << JsonQuote(e->GetSymbol()) << ", \"z\": " << w.Hex(e->GetZ(), true)
      << ", \"a_g_mole\": " << w.Hex(e->GetA() / (g / mole), true) << ", \"mass_fraction\": "
      << w.Hex(m->GetFractionVector()[i], true) << "}";
  }
  o << "]}";
  return o.str();
}

inline std::string ClassName(const std::type_info& t) {
  int status = 0;
  char* name = abi::__cxa_demangle(t.name(), nullptr, nullptr, &status);
  std::string out = status == 0 && name ? name : t.name();
  std::free(name);
  return out;
}

// A field manager without a field gives {"present": false, "source": "probe"} (unchanged from adapter 0.2.0). With a
// field (adapter 0.3.0, Geant4 program B1.2): the field class, its value when uniform (tesla, float.hex()), the
// accuracy parameters read back through the manager and its chord finder, and the actual classes of driver and
// stepper (RTTI). Names of volumes are not part of it: the logical volume's field block enters the tree-v1 hash.
inline std::string FieldJson(const G4FieldManager* fm) {
  if (!fm) return "null";
  const G4Field* f = fm->GetDetectorField();
  if (!f) return "{\"present\": false, \"source\": \"probe\"}";
  Writer w;
  std::ostringstream o;
  o << "{\"present\": true, \"source\": \"probe\", \"type\": " << JsonQuote(ClassName(typeid(*f))) << ", \"b_tesla\": ";
  if (auto* u = dynamic_cast<const G4UniformMagField*>(f)) {
    G4ThreeVector b = const_cast<G4UniformMagField*>(u)->GetConstantFieldValue();
    o << "[" << w.Hex(b.x() / tesla) << ", " << w.Hex(b.y() / tesla) << ", " << w.Hex(b.z() / tesla) << "]";
  } else {
    o << "null";
  }
  o << ", \"delta_one_step_mm\": " << w.Hex(fm->GetDeltaOneStep() / mm) << ", \"delta_intersection_mm\": "
    << w.Hex(fm->GetDeltaIntersection() / mm) << ", \"min_epsilon_step\": " << w.Hex(fm->GetMinimumEpsilonStep())
    << ", \"max_epsilon_step\": " << w.Hex(fm->GetMaximumEpsilonStep());
  auto* cf = const_cast<G4FieldManager*>(fm)->GetChordFinder();
  if (cf) {
    o << ", \"delta_chord_mm\": " << w.Hex(cf->GetDeltaChord() / mm);
    G4VIntegrationDriver* driver = cf->GetIntegrationDriver();
    o << ", \"driver\": " << (driver ? JsonQuote(ClassName(typeid(*driver))) : "null") << ", \"stepper\": ";
    G4MagIntegratorStepper* stepper = driver ? driver->GetStepper() : nullptr;
    o << (stepper ? JsonQuote(ClassName(typeid(*stepper))) : "null");
  } else {
    o << ", \"delta_chord_mm\": null, \"driver\": null, \"stepper\": null";
  }
  o << "}";
  return o.str();
}

// Every distinct field manager with a field (by pointer), with the volume it was attached to: the first logical
// volume in store order that has it while its mother's volume does not (SetFieldManager(fm, true) propagates it to
// the daughters). The master's copies only: each worker builds its own.
inline std::string FieldsJson() {
  std::vector<std::string> rows;
  std::set<const G4FieldManager*> seen;
  std::map<const G4LogicalVolume*, const G4LogicalVolume*> motherOf;
  for (const G4VPhysicalVolume* pv : *G4PhysicalVolumeStore::GetInstance())
    if (pv->GetMotherLogical()) motherOf[pv->GetLogicalVolume()] = pv->GetMotherLogical();
  for (const G4VPhysicalVolume* pv : *G4PhysicalVolumeStore::GetInstance()) {
    const G4LogicalVolume* lv = pv->GetLogicalVolume();
    const G4FieldManager* fm = lv->GetFieldManager();
    if (!fm || !fm->GetDetectorField() || seen.count(fm)) continue;
    auto m = motherOf.find(lv);
    if (m != motherOf.end() && m->second->GetFieldManager() == fm) continue;  // propagated from the mother
    seen.insert(fm);
    rows.push_back("{\"attached_to\": " + JsonQuote(lv->GetName()) + ", \"field\": " + FieldJson(fm) + "}");
  }
  return Join(rows);
}

inline std::string UserLimitsJson(G4UserLimits* ul, Writer& w) {
  if (!ul) return "null";
  G4Track dummy;  // the base G4UserLimits getters return their stored values; the track is not read
  std::ostringstream o;
  o << "{\"type\": " << JsonQuote(ul->GetType()) << ", \"max_step_mm\": " << w.Hex(ul->GetMaxAllowedStep(dummy) / mm)
    << ", \"max_track_length_mm\": " << w.Hex(ul->GetUserMaxTrackLength(dummy) / mm) << ", \"max_time_ns\": "
    << w.Hex(ul->GetUserMaxTime(dummy) / ns) << ", \"min_ekin_MeV\": " << w.Hex(ul->GetUserMinEkine(dummy) / MeV)
    << ", \"min_range_mm\": " << w.Hex(ul->GetUserMinRange(dummy) / mm) << "}";
  return o.str();
}

inline std::string Geometry(Writer& w, std::vector<const G4Material*>& usedMaterials) {
  const auto* store = G4PhysicalVolumeStore::GetInstance();
  std::map<const G4LogicalVolume*, int> lvId;
  std::vector<const G4LogicalVolume*> lvs;
  auto idOf = [&](const G4LogicalVolume* lv) {
    auto it = lvId.find(lv);
    if (it != lvId.end()) return it->second;
    int id = static_cast<int>(lvs.size());
    lvId[lv] = id;
    lvs.push_back(lv);
    return id;
  };
  std::vector<std::string> placements;
  for (const G4VPhysicalVolume* pv : *store) {
    std::ostringstream o;
    const G4LogicalVolume* mother = pv->GetMotherLogical();
    int lid = idOf(pv->GetLogicalVolume());
    int mid = mother ? idOf(mother) : -1;
    G4ThreeVector t = pv->GetObjectTranslation();
    G4RotationMatrix r = pv->GetObjectRotationValue();
    o << "{\"name\": " << JsonQuote(pv->GetName()) << ", \"copy_number\": " << pv->GetCopyNo()
      << ", \"logical\": " << lid << ", \"mother_logical\": " << (mid < 0 ? std::string("null") : std::to_string(mid))
      << ", \"translation_mm\": [" << w.Hex(t.x() / mm, true) << ", " << w.Hex(t.y() / mm, true) << ", "
      << w.Hex(t.z() / mm, true) << "], \"rotation\": ";
    if (r.isIdentity()) {
      o << "null";
    } else {
      o << "[" << w.Hex(r.xx(), true) << ", " << w.Hex(r.xy(), true) << ", " << w.Hex(r.xz(), true) << ", "
        << w.Hex(r.yx(), true) << ", " << w.Hex(r.yy(), true) << ", " << w.Hex(r.yz(), true) << ", "
        << w.Hex(r.zx(), true) << ", " << w.Hex(r.zy(), true) << ", " << w.Hex(r.zz(), true) << "]";
    }
    if (pv->IsReplicated()) {
      EAxis axis;
      G4int n;
      G4double width, offset;
      G4bool consuming;
      pv->GetReplicationData(axis, n, width, offset, consuming);
      o << ", \"kind\": " << (pv->IsParameterised() ? "\"parameterised\"" : "\"replica\"")
        << ", \"replication\": {\"axis\": " << static_cast<int>(axis) << ", \"multiplicity\": " << n
        << ", \"width\": " << w.Hex(width, true) << ", \"offset\": " << w.Hex(offset, true)
        << ", \"consuming\": " << (consuming ? "true" : "false") << "}";
      if (pv->IsParameterised())
        o << ", \"gap\": \"the parameterisation's per-copy dimensions and materials are not recorded\"";
    } else {
      o << ", \"kind\": \"placement\"";
    }
    o << "}";
    placements.push_back(o.str());
  }
  std::vector<std::string> lvJson, matJson;
  std::set<const G4Material*> seen;
  for (std::size_t i = 0; i < lvs.size(); ++i) {
    const G4LogicalVolume* lv = lvs[i];
    const G4Material* m = lv->GetMaterial();
    if (m && seen.insert(m).second) {
      usedMaterials.push_back(m);
      matJson.push_back(MaterialJson(m, w));
    }
    std::ostringstream o;
    o << "{\"id\": " << i << ", \"name\": " << JsonQuote(lv->GetName()) << ", \"solid\": " << Solid(lv->GetSolid(), w)
      << ", \"material\": " << (m ? JsonQuote(m->GetName()) : "null") << ", \"field\": "
      << FieldJson(lv->GetFieldManager()) << ", \"user_limits\": "
      << UserLimitsJson(const_cast<G4LogicalVolume*>(lv)->GetUserLimits(), w) << ", \"region\": "
      << (lv->GetRegion() ? JsonQuote(lv->GetRegion()->GetName()) : "null") << "}";
    lvJson.push_back(o.str());
  }
  const G4FieldManager* global = G4TransportationManager::GetTransportationManager()->GetFieldManager();
  return "{\"units\": {\"length\": \"mm\", \"density\": \"g/cm3\", \"angle\": \"rad\"}, \"logical_volumes\": " +
         Join(lvJson) + ", \"placements\": " + Join(placements) + ", \"materials\": " + Join(matJson) +
         ", \"global_field\": " + FieldJson(global) + ", \"gdml_sha256\": null}";
}

// The per-region model requests StreamInfo does not print (/process/em/AddPAIRegion and the like): PAI, MicroElec,
// DNA and extra physics per region, from G4EmParameters.
inline std::string StringList(const std::vector<G4String>& v) {
  std::vector<std::string> q;
  for (const auto& x : v) q.push_back(JsonQuote(x));
  return Join(q);
}

inline std::string EmExtra() {
  const G4EmParameters* p = G4EmParameters::Instance();
  return "{\"pai\": {\"particles\": " + StringList(p->ParticlesPAI()) + ", \"regions\": " + StringList(p->RegionsPAI()) +
         ", \"types\": " + StringList(p->TypesPAI()) + "}, \"microelec_regions\": " + StringList(p->RegionsMicroElec()) +
         ", \"dna\": {\"regions\": " + StringList(p->RegionsDNA()) + ", \"types\": " + StringList(p->TypesDNA()) +
         "}, \"physics\": {\"regions\": " + StringList(p->RegionsPhysics()) + ", \"types\": " +
         StringList(p->TypesPhysics()) + "}}";
}

// Lines "description   value" of StreamInfo split at the last run of two or more spaces; other lines are kept only
// in the full text.
inline std::string EmParameters() {
  std::ostringstream text;
  G4EmParameters::Instance()->StreamInfo(text);
  std::string s = text.str();
  std::vector<std::string> fields;
  std::istringstream in(s);
  std::string line;
  while (std::getline(in, line)) {
    while (!line.empty() && (line.back() == ' ' || line.back() == '\r')) line.pop_back();
    std::size_t gap = line.rfind("  ");
    if (gap == std::string::npos) continue;
    std::string key = line.substr(0, gap), value = line.substr(gap + 2);
    while (!key.empty() && key.back() == ' ') key.pop_back();
    while (!value.empty() && value.front() == ' ') value.erase(value.begin());
    std::size_t start = key.find_first_not_of(' ');
    if (start == std::string::npos || value.empty() || key[start] == '=') continue;  // banners stay in the text only
    fields.push_back("[" + JsonQuote(key.substr(start)) + ", " + JsonQuote(value) + "]");
  }
  return "{\"source\": \"G4EmParameters::StreamInfo\", \"text\": " + JsonQuote(s) + ", \"fields\": " + Join(fields) +
         ", \"extra\": " + EmExtra() + "}";
}

inline std::string Cuts(Writer& w, std::size_t& couples) {
  const auto* table = G4ProductionCutsTable::GetProductionCutsTable();
  couples = table->GetTableSize();
  static const char* kParticles[] = {"gamma", "e-", "e+", "proton"};
  std::vector<std::string> rows;
  for (std::size_t i = 0; i < couples; ++i) {
    const G4MaterialCutsCouple* c = table->GetMaterialCutsCouple(static_cast<G4int>(i));
    std::vector<std::string> regions;
    for (G4Region* r : *G4RegionStore::GetInstance())
      if (r->FindCouple(const_cast<G4Material*>(c->GetMaterial())) == c) regions.push_back(JsonQuote(r->GetName()));
    std::ostringstream o;
    o << "{\"index\": " << i << ", \"material\": " << JsonQuote(c->GetMaterial()->GetName())
      << ", \"used\": " << (c->IsUsed() ? "true" : "false") << ", \"regions\": " << Join(regions)
      << ", \"range_cut_mm\": {";
    for (int k = 0; k < 4; ++k)
      o << (k ? ", " : "") << JsonQuote(kParticles[k]) << ": " << w.Hex(c->GetProductionCuts()->GetProductionCut(k) / mm);
    o << "}, \"energy_threshold_MeV\": {";
    for (std::size_t k = 0; k < 4; ++k)
      o << (k ? ", " : "") << JsonQuote(kParticles[k]) << ": " << w.Hex((*table->GetEnergyCutsVector(k))[i] / MeV);
    o << "}}";
    rows.push_back(o.str());
  }
  return Join(rows);
}

inline std::string Models(G4HadronicProcess* hp, const std::vector<const G4Material*>& mats, Writer& w) {
  auto& list = hp->GetHadronicInteractionList();
  std::vector<std::string> models, overlaps;
  for (std::size_t i = 0; i < list.size(); ++i) {
    G4HadronicInteraction* m = list[i];
    std::vector<std::string> blocked, ranges;
    for (const G4Material* mat : mats) {
      if (m->IsBlocked(mat)) blocked.push_back(JsonQuote(mat->GetName()));
      for (std::size_t e = 0; e < mat->GetNumberOfElements(); ++e) {
        const G4Element* el = mat->GetElement(static_cast<G4int>(e));
        if (m->IsBlocked(el)) blocked.push_back(JsonQuote(mat->GetName() + "/" + el->GetName()));
        double lo = m->GetMinEnergy(mat, el), hi = m->GetMaxEnergy(mat, el);
        if (lo != m->GetMinEnergy() || hi != m->GetMaxEnergy())
          ranges.push_back("{\"material\": " + JsonQuote(mat->GetName()) + ", \"element\": " +
                           JsonQuote(el->GetName()) + ", \"min_MeV\": " + w.Hex(lo / MeV) + ", \"max_MeV\": " +
                           w.Hex(hi / MeV) + "}");
      }
    }
    models.push_back("{\"name\": " + JsonQuote(m->GetModelName()) + ", \"min_MeV\": " + w.Hex(m->GetMinEnergy() / MeV) +
                     ", \"max_MeV\": " + w.Hex(m->GetMaxEnergy() / MeV) + ", \"blocked\": " + Join(blocked) +
                     ", \"ranges_differing\": " + Join(ranges) + "}");
    for (std::size_t j = i + 1; j < list.size(); ++j) {
      double lo = std::max(m->GetMinEnergy(), list[j]->GetMinEnergy());
      double hi = std::min(m->GetMaxEnergy(), list[j]->GetMaxEnergy());
      if (lo < hi)
        overlaps.push_back("{\"models\": [" + std::to_string(i) + ", " + std::to_string(j) + "], \"min_MeV\": " +
                           w.Hex(lo / MeV) + ", \"max_MeV\": " + w.Hex(hi / MeV) + ", \"selection\": \"random\"}");
    }
  }
  return "\"models\": " + Join(models) + ", \"overlaps\": " + Join(overlaps);
}

struct ProcessScan {
  std::vector<std::string> hadronic, general, biasing;
};

inline ProcessScan Processes(const std::vector<const G4Material*>& mats, Writer& w) {
  ProcessScan out;
  auto* it = G4ParticleTable::GetParticleTable()->GetIterator();
  it->reset();
  while ((*it)()) {
    G4ParticleDefinition* p = it->value();
    G4ProcessManager* pm = p->GetProcessManager();
    if (!pm) continue;
    G4ProcessVector* pv = pm->GetProcessList();
    for (std::size_t i = 0; i < pv->size(); ++i) {
      G4VProcess* proc = (*pv)[i];
      const std::string name = proc->GetProcessName();
      if (name.rfind("biasWrapper", 0) == 0) out.biasing.push_back(JsonQuote(p->GetParticleName() + ":" + name));
      if (auto* ng = dynamic_cast<G4NeutronGeneralProcess*>(proc)) {  // before G4HadronicProcess: it derives from it in 11.4
        std::vector<std::string> subs;
        for (int type : {fHadronElastic, fHadronInelastic, fCapture}) {
          G4HadronicProcess* sub = ng->GetHadronicProcess(type);
          if (!sub) continue;
          subs.push_back(JsonQuote(sub->GetProcessName()));
          out.hadronic.push_back("{\"particle\": " + JsonQuote(p->GetParticleName()) + ", \"process\": " +
                                 JsonQuote(sub->GetProcessName()) + ", \"via\": " + JsonQuote(name) + ", " +
                                 Models(sub, mats, w) + "}");
        }
        out.general.push_back("{\"particle\": " + JsonQuote(p->GetParticleName()) + ", \"process\": " +
                              JsonQuote(name) + ", \"sub_processes\": " + Join(subs) + "}");
      } else if (auto* hp = dynamic_cast<G4HadronicProcess*>(proc)) {
        out.hadronic.push_back("{\"particle\": " + JsonQuote(p->GetParticleName()) + ", \"process\": " +
                               JsonQuote(name) + ", \"via\": null, " + Models(hp, mats, w) + "}");
      } else if (auto* gg = dynamic_cast<G4GammaGeneralProcess*>(proc)) {
        std::vector<std::string> subs;
        for (const char* sub : {"phot", "compt", "conv", "Rayl"})
          if (gg->GetEmProcess(sub)) subs.push_back(JsonQuote(sub));
        out.general.push_back("{\"particle\": " + JsonQuote(p->GetParticleName()) + ", \"process\": " +
                              JsonQuote(name) + ", \"sub_processes\": " + Join(subs) +
                              ", \"gap\": \"a gamma-nuclear sub-process, if added, is not reachable through the "
                              "G4GammaGeneralProcess interface\"}");
      }
    }
  }
  return out;
}

inline std::string RunManagerJson() {
  G4RunManager* rm = G4RunManager::GetRunManager();
  std::string cls = "G4RunManager", type;
  bool mt = false;
  if (dynamic_cast<G4TaskRunManager*>(rm)) {
    cls = "G4TaskRunManager";
    mt = true;
  } else if (dynamic_cast<G4MTRunManager*>(rm)) {
    cls = "G4MTRunManager";
    mt = true;
  }
  std::vector<std::string> gaps;
  switch (rm->GetRunManagerType()) {
    case G4RunManager::sequentialRM: type = "sequential"; break;
    case G4RunManager::masterRM: type = "master"; break;
    case G4RunManager::workerRM: type = "worker"; break;
    case G4RunManager::subEventMasterRM: type = "sub-event-master"; gaps.push_back(JsonQuote("sub-event run manager")); break;
    case G4RunManager::subEventWorkerRM: type = "sub-event-worker"; gaps.push_back(JsonQuote("sub-event run manager")); break;
  }
  int seedOnce = mt ? G4MTRunManager::SeedOncePerCommunication() : 0;
  if (seedOnce != 0) gaps.push_back(JsonQuote("seedOncePerCommunication is not 0"));
  const char* env = std::getenv("G4RUN_MANAGER_TYPE");
  const char* force = std::getenv("G4FORCE_RUN_MANAGER_TYPE");
  std::ostringstream o;
  o << "{\"class\": " << JsonQuote(cls) << ", \"type\": " << JsonQuote(type) << ", \"seed_once_per_communication\": "
    << (mt ? std::to_string(seedOnce) : std::string("null")) << ", \"G4RUN_MANAGER_TYPE\": "
    << (env ? JsonQuote(env) : "null") << ", \"G4FORCE_RUN_MANAGER_TYPE\": " << (force ? JsonQuote(force) : "null")
    << ", \"note\": \"with MTOnly or SerialOnly the environment variable G4RUN_MANAGER_TYPE is ignored\", \"gaps\": "
    << Join(gaps) << ", \"random\": {\"engine\": " << JsonQuote(G4Random::getTheEngine()->name())
    << ", \"saving_flag\": " << (rm->GetRandomNumberStore() ? "true" : "false")
    << ", \"status_to_event\": " << rm->GetFlagRandomNumberStatusToG4Event() << "}}";
  return o.str();
}

inline std::string EngineVersion() {
  int v = G4VERSION_NUMBER;  // e.g. 1143
  return std::to_string(v / 100) + "." + std::to_string((v / 10) % 10) + "." + std::to_string(v % 10);
}

}  // namespace probe_detail

// The probe of the current run (master thread, BeginOfRunAction). `note` is stored verbatim.
inline ProbeResult RunProbe(const std::string& note) {
  using namespace probe_detail;
  ProbeResult res;
  std::vector<unsigned long> before = G4Random::getTheEngine()->put();
  G4ApplicationState state = G4StateManager::GetStateManager()->GetCurrentState();
  Writer w;
  std::size_t couples = 0;
  std::string cuts = Cuts(w, couples);
  res.recorded = state == G4State_GeomClosed && couples > 0;
  std::ostringstream o;
  o << "{\"probe_version\": " << JsonQuote(kProbeVersion) << ", \"engine\": \"geant4\", \"engine_version\": "
    << JsonQuote(EngineVersion()) << ", \"G4Version\": " << JsonQuote(G4Version) << ", \"recorded\": "
    << (res.recorded ? "true" : "false") << ", \"application_state\": "
    << JsonQuote(G4StateManager::GetStateManager()->GetStateString(state)) << ", \"couples\": " << couples
    << ", \"threads\": \"master only; workers assumed identical\", \"note\": " << JsonQuote(note);
  if (res.recorded) {
    std::vector<const G4Material*> mats;
    std::string geometry = Geometry(w, mats);
    ProcessScan procs = Processes(mats, w);
    o << ", \"geometry\": " << geometry << ", \"em_parameters\": " << EmParameters() << ", \"cuts\": " << cuts
      << ", \"hadronic\": " << Join(procs.hadronic) << ", \"general_processes\": " << Join(procs.general)
      << ", \"biasing\": {\"wrapped_processes\": " << Join(procs.biasing) << ", \"events_may_share_state\": "
      << (procs.biasing.empty() ? "false" : "true") << "}, \"run_manager\": " << RunManagerJson();
    std::string fields = FieldsJson();
    if (fields != "[]")  // only with a field (adapter 0.3.0), so a run without one keeps its 0.2.0 probe
      o << ", \"fields\": " << fields << ", \"fields_note\": \"the master's field managers; each worker builds its "
        << "own copy in its ConstructSDandField\"";
    if (w.BadGeometry()) res.error = "the geometry has an infinite or NaN number";
  } else {
    o << ", \"reason\": \"the probe runs in state G4State_GeomClosed with at least one material-cuts couple\"";
  }
  res.randomUnchanged = G4Random::getTheEngine()->put() == before;
  o << ", \"random_state_unchanged\": " << (res.randomUnchanged ? "true" : "false") << "}\n";
  res.json = o.str();
  return res;
}

}  // namespace g4sim

#endif
