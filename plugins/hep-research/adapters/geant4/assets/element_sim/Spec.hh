// The element_sim run spec (element_sim.spec/1, spec.schema.json). geant4_run.py check-spec validates the schema and
// the cross-field rules before a run (element_spec.py); this reader takes what the program needs and throws
// minijson::JsonError (exit 2) on anything it cannot use.
#ifndef ELEMENT_SIM_SPEC_HH
#define ELEMENT_SIM_SPEC_HH

#include <array>
#include <string>
#include <vector>

#include "SimMaterials.hh"
#include "SimSummary.hh"

using g4sim::MaterialDef;
using Vec3 = std::array<double, 3>;

struct ElementDef {
  std::string name, material, mother = "world", role;
  Vec3 centre_mm{0, 0, 0}, half_mm{0, 0, 0}, pitch_mm{0, 0, 0}, shift_mm{0, 0, 0};
  int count = 1;  // repeat.count: copies 0 .. count-1 at centre + k pitch
  Vec3 CopyCentre(int k) const {
    return {centre_mm[0] + k * pitch_mm[0] + shift_mm[0], centre_mm[1] + k * pitch_mm[1] + shift_mm[1],
            centre_mm[2] + k * pitch_mm[2] + shift_mm[2]};
  }
};

struct FieldRegionDef {
  std::string element;
  Vec3 b_tesla{0, 0, 0};
};

struct FieldDef {
  std::vector<FieldRegionDef> regions;  // empty: no field
  std::string stepper = "DormandPrince745", driver = "InterpolationDriver";
  double delta_chord_mm = 0.25, delta_one_step_mm = 0.01, delta_intersection_mm = 1e-5;
  double min_epsilon_step = 5e-5, max_epsilon_step = 1e-3, max_step_mm = 10.;
};

struct CutRegionDef {
  std::string name;
  std::vector<std::string> elements;
  double cut_mm = 0.;
};

struct CycleEntry {
  double energy_MeV = 0.;
  Vec3 direction{1, 0, 0};
};

struct Spec {
  std::string world_material;
  Vec3 world_half_mm{0, 0, 0};
  std::vector<MaterialDef> materials;
  std::vector<ElementDef> elements;
  FieldDef field;
  // physics
  std::string reference_list, em_constructor;
  bool decay = true;
  double default_cut_mm = 0.7;
  std::vector<CutRegionDef> regions;
  std::vector<std::string> ui_commands;
  // source (gun)
  std::string particle;
  double energy_MeV = 0.;  // kinetic energy (ekin_per_nucleon_MeV times the nucleon number for light ions)
  Vec3 position_mm{0, 0, 0}, direction{1, 0, 0};
  std::vector<CycleEntry> cycle;  // event i uses entry i mod n
  // run
  long events = 0, first_event = 0;
  int chunk = 0;
  std::array<long, 2> seeds{0, 0};
  std::string run_manager = "serial";
  int threads = 1;
  long long logical_run_seed = 0;  // S; seeding is always per-event
  // output
  int overlap_test_points = 0;
  std::vector<g4sim::ObservableDecl> observables;
  long block_size = 0, blocks = 0, block_first_event = 0;
  bool debug_observable_dump = false;
  std::string event_level = "none";  // none, summary, crossings, hits
  int compression = 1;
  long max_events_hits = 100;
  // files, all in the working directory (the run folder)
  std::string spec_path, spec_sha256;
  std::string csv = "events.csv", materials_out = "materials.json", datapaths_out = "datapaths.json";
  std::string summary_out = "summary.json", column_map_out = "column_map.json", probe_out = "probe.json";
  std::string dump_out = "observables_dump.csv", event_file = "events.root";

  int ElementIndex(const std::string& name) const;  // -1 if none
  int CalorimeterIndex() const;                     // the element with role calorimeter, or -1
  bool HasField() const { return !field.regions.empty(); }
  bool Level(const std::string& atLeast) const;     // event_level is at least this level
};

Spec ReadSpec(const std::string& path);

#endif
