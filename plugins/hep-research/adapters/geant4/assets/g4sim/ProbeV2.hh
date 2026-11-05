// g4sim/ProbeV2.hh: the complete legacy record of a Geant4 run (g4sim plan, Section 7.4). Geant4 API only; written from the
// Geant4 API (no example code copied or adapted).
//
// Called once per run on the master in BeginOfRunAction, like SimProbe.hh, which it includes and leaves unchanged. The record
// of SimProbe.hh is kept whole under "base", so an existing probe record can be compared with it directly, and this file adds
// what a re-acquisition needs: derived quantities of each material (radiation length, nuclear interaction length, electron
// density), the production cuts of each region with its root volumes, each particle's ordered process lists, and one field
// record per logical volume.
//
// The field of a logical volume is "source": "probe" when the master sees it. A logical volume named in
// declaredFieldVolumes that has no field manager on the master is "source": "declared": the master cannot report its field
// (GB22), and such a run cannot take its field assignment from this record.
//
// The probe draws no random numbers: it compares the engine state before and after itself, around SimProbe.hh as well.
#ifndef G4SIM_PROBEV2_HH
#define G4SIM_PROBEV2_HH

#include <set>
#include <sstream>
#include <string>
#include <vector>

#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"
#include "G4ProcessManager.hh"
#include "G4ProcessVector.hh"
#include "G4VProcess.hh"
#include "SimProbe.hh"

namespace g4sim {

constexpr const char* kProbeV2Version = "g4sim-probe/2";

struct ProbeV2Result {
  std::string json;
  bool recorded = false;
  bool randomUnchanged = true;
  std::string error;  // non-empty: the geometry has an infinite or NaN number (exit 2)
};

namespace probe_v2_detail {

using probe_detail::Join;
using probe_detail::Writer;

inline std::vector<const G4LogicalVolume*> Logicals() {
  std::vector<const G4LogicalVolume*> out;
  std::set<const G4LogicalVolume*> seen;
  for (const G4VPhysicalVolume* pv : *G4PhysicalVolumeStore::GetInstance()) {
    if (seen.insert(pv->GetLogicalVolume()).second) out.push_back(pv->GetLogicalVolume());
  }
  return out;
}

inline std::string DerivedMaterial(const G4Material* m, Writer& w) {
  std::ostringstream o;
  o << "{\"name\": " << JsonQuote(m->GetName()) << ", \"radiation_length_mm\": " << w.Hex(m->GetRadlen() / mm, true)
    << ", \"nuclear_interaction_length_mm\": " << w.Hex(m->GetNuclearInterLength() / mm, true)
    << ", \"electron_density_per_mm3\": " << w.Hex(m->GetElectronDensity() * mm3, true) << "}";
  return o.str();
}

inline std::string Materials(Writer& w) {
  std::vector<std::string> rows;
  std::set<const G4Material*> seen;
  for (const G4LogicalVolume* lv : Logicals()) {
    const G4Material* m = lv->GetMaterial();
    if (m && seen.insert(m).second) rows.push_back(DerivedMaterial(m, w));
  }
  return Join(rows);
}

inline std::string Regions(Writer& w) {
  static const char* kCutParticles[] = {"gamma", "e-", "e+", "proton"};
  std::vector<std::string> rows;
  for (G4Region* region : *G4RegionStore::GetInstance()) {
    std::ostringstream o;
    o << "{\"name\": " << JsonQuote(region->GetName()) << ", \"root_volumes\": ";
    std::vector<std::string> roots;
    auto root = region->GetRootLogicalVolumeIterator();
    for (std::size_t i = 0; i < region->GetNumberOfRootVolumes(); ++i, ++root) roots.push_back(JsonQuote((*root)->GetName()));
    o << Join(roots) << ", \"cuts_mm\": ";
    G4ProductionCuts* cuts = region->GetProductionCuts();
    if (cuts) {
      o << "{";
      for (int i = 0; i < 4; ++i) {
        o << (i ? ", " : "") << JsonQuote(kCutParticles[i]) << ": " << w.Hex(cuts->GetProductionCut(kCutParticles[i]) / mm);
      }
      o << "}";
    } else {
      o << "null";
    }
    o << ", \"user_limits\": " << probe_detail::UserLimitsJson(region->GetUserLimits(), w) << "}";
    rows.push_back(o.str());
  }
  return Join(rows);
}

inline std::string Ordered(G4ProcessVector* list) {
  std::vector<std::string> names;
  for (std::size_t i = 0; list && i < list->size(); ++i) {
    G4VProcess* process = (*list)[i];
    names.push_back(process ? JsonQuote(process->GetProcessName()) : "null");
  }
  return Join(names);
}

// Every particle with a process manager, each with its processes in registration order and the three ordered DoIt lists.
inline std::string Processes() {
  std::vector<std::string> rows;
  auto* particles = G4ParticleTable::GetParticleTable()->GetIterator();
  particles->reset();
  while ((*particles)()) {
    const G4ParticleDefinition* particle = particles->value();
    G4ProcessManager* manager = particle->GetProcessManager();
    if (!manager) continue;
    std::ostringstream o;
    o << "{\"particle\": " << JsonQuote(particle->GetParticleName()) << ", \"registered\": " << Ordered(manager->GetProcessList())
      << ", \"at_rest\": " << Ordered(manager->GetAtRestProcessVector(typeDoIt))
      << ", \"along_step\": " << Ordered(manager->GetAlongStepProcessVector(typeDoIt))
      << ", \"post_step\": " << Ordered(manager->GetPostStepProcessVector(typeDoIt)) << "}";
    rows.push_back(o.str());
  }
  return Join(rows);
}

inline std::string LogicalFields(const std::set<std::string>& declaredFieldVolumes) {
  std::vector<std::string> rows;
  std::vector<const G4FieldManager*> identities;
  auto identity = [&](const G4FieldManager* manager) {
    for (std::size_t i = 0; i < identities.size(); ++i) {
      if (identities[i] == manager) return static_cast<int>(i);
    }
    identities.push_back(manager);
    return static_cast<int>(identities.size()) - 1;
  };
  for (const G4LogicalVolume* lv : Logicals()) {
    const G4FieldManager* manager = lv->GetFieldManager();
    const bool hidden = !manager && declaredFieldVolumes.count(lv->GetName()) > 0;
    std::ostringstream o;
    o << "{\"logical\": " << JsonQuote(lv->GetName()) << ", \"source\": " << (hidden ? "\"declared\"" : "\"probe\"")
      << ", \"field_manager\": " << (manager ? std::to_string(identity(manager)) : std::string("null"))
      << ", \"region\": " << (lv->GetRegion() ? JsonQuote(lv->GetRegion()->GetName()) : "null") << "}";
    rows.push_back(o.str());
  }
  return Join(rows);
}

}  // namespace probe_v2_detail

// The record of the current run (master thread, BeginOfRunAction). `note` is stored verbatim.
inline ProbeV2Result RunProbeV2(const std::string& note, const std::set<std::string>& declaredFieldVolumes = {}) {
  using namespace probe_v2_detail;
  ProbeV2Result res;
  const std::vector<unsigned long> before = G4Random::getTheEngine()->put();
  ProbeResult base = RunProbe(note);
  res.recorded = base.recorded;
  res.error = base.error;
  Writer w;
  std::ostringstream o;
  std::string body = base.json;
  while (!body.empty() && (body.back() == '\n' || body.back() == ' ')) body.pop_back();
  o << "{\"probe_version\": " << JsonQuote(kProbeV2Version) << ", \"recorded\": " << (res.recorded ? "true" : "false")
    << ", \"base\": " << body;
  if (res.recorded) {
    o << ", \"materials\": " << Materials(w) << ", \"regions\": " << Regions(w) << ", \"logical_fields\": "
      << LogicalFields(declaredFieldVolumes) << ", \"processes\": " << Processes();
    if (w.BadGeometry()) res.error = "the geometry has an infinite or NaN number";
  }
  res.randomUnchanged = base.randomUnchanged && G4Random::getTheEngine()->put() == before;
  o << ", \"random_state_unchanged\": " << (res.randomUnchanged ? "true" : "false") << "}\n";
  res.json = o.str();
  return res;
}

}  // namespace g4sim

#endif
