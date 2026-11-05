// Test hook of the re-acquisition prototypes GB1 and GB22 (g4sim plan, Section 23); never part of a program in the plugin.
// Around ProbeV2 it saves the full engine state to two files, and it dumps the doubles of G4PhysicalVolumeStore with %a,
// separately from the probe's own formatter, so judge.py compares two independently written records.
// G4PROTO_OUT names the output folder; G4PROTO_DECLARED lists, comma separated, the logical volumes the program declares a
// field on.
#ifndef G4PROTO_PROBEHOOK_HH
#define G4PROTO_PROBEHOOK_HH

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <set>
#include <sstream>
#include <string>

#include "G4PhysicalVolumeStore.hh"
#include "ProbeV2.hh"
#include "Randomize.hh"

namespace g4proto {

inline std::string Hexadecimal(double value) {
  char text[64];
  std::snprintf(text, sizeof text, "%a", value);
  return text;
}

inline void Record(const char* program) {
  const char* folder = std::getenv("G4PROTO_OUT");
  if (!folder) return;
  const std::string out(folder);
  std::set<std::string> declared;
  if (const char* names = std::getenv("G4PROTO_DECLARED")) {
    std::stringstream list(names);
    std::string name;
    while (std::getline(list, name, ',')) declared.insert(name);
  }
  {
    std::ofstream state(out + "/rng-before.txt");
    G4Random::saveFullState(state);
  }
  g4sim::ProbeV2Result result = g4sim::RunProbeV2(std::string(program) + ": re-acquisition", declared);
  {
    std::ofstream state(out + "/rng-after.txt");
    G4Random::saveFullState(state);
  }
  std::ofstream(out + "/probe-v2.json") << result.json;
  std::ofstream dump(out + "/store-dump.txt");
  for (const G4VPhysicalVolume* volume : *G4PhysicalVolumeStore::GetInstance()) {
    const G4ThreeVector t = volume->GetObjectTranslation();
    const G4RotationMatrix r = volume->GetObjectRotationValue();
    dump << volume->GetName() << ' ' << volume->GetCopyNo() << ' ' << Hexadecimal(t.x()) << ' ' << Hexadecimal(t.y()) << ' '
         << Hexadecimal(t.z());
    for (double value : {r.xx(), r.xy(), r.xz(), r.yx(), r.yy(), r.yz(), r.zx(), r.zy(), r.zz()}) dump << ' ' << Hexadecimal(value);
    dump << '\n';
  }
}

}  // namespace g4proto

#endif
