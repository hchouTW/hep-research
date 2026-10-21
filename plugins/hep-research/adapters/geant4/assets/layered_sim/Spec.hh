// The layered_sim run spec (spec.schema.json). geant4_run.py validates the spec fully before running; this reader
// checks what the program needs and throws minijson::JsonError (exit 2) on anything it cannot use.
#ifndef LAYERED_SIM_SPEC_HH
#define LAYERED_SIM_SPEC_HH

#include <array>
#include <string>
#include <vector>

struct MaterialDef {  // a single-element material defined by Z, A and density
  std::string name;
  int z = 0;
  double a_g_mole = 0., density_g_cm3 = 0.;
  std::string state = "solid";  // solid, liquid, gas
  double temperature_K = -1., pressure_Pa = -1.;  // < 0: Geant4 default
};

struct SlabDef {
  std::string name, material;
  double thickness_mm = 0.;
  bool sensitive = false;
  double shift_mm = 0.;  // shift of this slab's placements along x (negative controls of the overlap check only)
};

struct LayerDef {
  int repeat = 1;
  std::vector<SlabDef> slabs;
};

struct RegionDef {
  std::string name;
  std::vector<std::string> slabs;
  double cut_mm = 0.;
};

struct Spec {
  // geometry: slabs stacked along x, centred in the world
  double lateral_mm = 0.;
  std::vector<LayerDef> layers;
  std::string world_material;
  double world_scale = 0.;               // > 0: world = scale x stack (TestEm3 and TestEm5 use 1.2)
  std::array<double, 3> world_mm{0, 0, 0};  // used when world_scale == 0
  std::vector<MaterialDef> materials;
  // physics
  std::string reference_list;  // G4PhysListFactory name, optionally with an EM suffix
  std::string em_constructor;  // modular EM-only list: one EM constructor plus G4DecayPhysics
  bool decay = true;
  double default_cut_mm = 0.7;
  std::vector<RegionDef> regions;
  double step_limit_mm = 0.;      // > 0: G4UserLimits max step in sensitive slabs, G4StepLimiterPhysics added
  double min_ekin_MeV = 0.;       // > 0: G4UserLimits minimum kinetic energy in sensitive slabs (UserSpecialCut kills)
  bool kill_secondaries = false;  // stacking kill of every secondary (energy recorded as not booked)
  std::vector<std::string> ui_commands;
  // primary
  std::string particle;
  double energy_MeV = 0.;
  double gun_world_fraction = -0.5;  // gun x = fraction x world x length; y = z = 0
  std::array<double, 3> direction{1, 0, 0};
  // run
  long events = 0, first_event = 0;
  int chunk = 0;
  std::array<long, 2> seeds{0, 0};
  std::string run_manager = "serial";
  int threads = 1;
  // outputs
  std::string csv, materials_out, datapaths_out;
  int overlap_test_points = 0;  // > 0: /geometry/test/run after initialisation with this resolution
  bool per_instance = false;     // also write one deposit column per placed slab copy

  std::vector<std::string> slabNames() const;
};

Spec ReadSpec(const std::string& path);

#endif
