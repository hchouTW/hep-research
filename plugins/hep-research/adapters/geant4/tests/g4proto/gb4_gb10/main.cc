// Prototypes GB4 and GB10 of the g4sim plan (Section 23): one program, judged by judge.py.
//   gb4_gb10 T OUT.json        translation chain at X = 2e4 mm, d = 26
//   gb4_gb10 R OUT.json        rotated chain at X = 2e4 mm, d = 2, and the region geometry of GB4
//   gb4_gb10 extent OUT.json   SetWorldMaximumExtent: the tolerance becomes extent x 1e-11
// Each chain has its own world: the translation chain's outer boxes fill most of it. Every placement is checked for overlaps.
// Every double is written with %a, and every placement as the decimal strings that defined it, so judge.py can compute
// the true coordinates exactly. This program judges nothing itself.
#include "G4Box.hh"
#include "G4Event.hh"
#include "G4GeometryManager.hh"
#include "G4GeometryTolerance.hh"
#include "G4Geantino.hh"
#include "G4LogicalVolume.hh"
#include "G4LogicalVolumeStore.hh"
#include "G4NistManager.hh"
#include "G4Navigator.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleGun.hh"
#include "G4Region.hh"
#include "G4RotationMatrix.hh"
#include "G4RunManagerFactory.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4TransportationManager.hh"
#include "G4UserSteppingAction.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPhysicsList.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4Version.hh"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <random>
#include <sstream>
#include <string>
#include <vector>

namespace {

constexpr double kWorldHalf = 20000.0;  // X of the chains, mm
const char* kGapHalf = "0.0000005";     // half of c = 1e-6 mm

std::string Hex(double value) {
  char text[64];
  std::snprintf(text, sizeof text, "%a", value);
  return text;
}

struct Rational {  // one rotation about one axis, cos = c/h and sin = s/h, so judge.py has it exactly
  char axis;
  int c, s, h;
};

struct Level {
  std::string name;
  std::string tx, ty, tz;  // translation in the mother, decimal mm
  std::string half;        // cube half length, decimal mm
  bool rotated;
  Rational rotation;
};

double Num(const std::string& text) { return std::strtod(text.c_str(), nullptr); }

G4RotationMatrix* Matrix(const Rational& r) {
  const double c = double(r.c) / r.h, s = double(r.s) / r.h;
  CLHEP::HepRep3x3 m(1, 0, 0, 0, 1, 0, 0, 0, 1);
  if (r.axis == 'x') m = CLHEP::HepRep3x3(1, 0, 0, 0, c, -s, 0, s, c);
  if (r.axis == 'y') m = CLHEP::HepRep3x3(c, 0, s, 0, 1, 0, -s, 0, c);
  if (r.axis == 'z') m = CLHEP::HepRep3x3(c, -s, 0, s, c, 0, 0, 0, 1);
  return new G4RotationMatrix(m);
}

std::string Fixed(double value) {
  char text[64];
  std::snprintf(text, sizeof text, "%.3f", value);
  return text;
}

// Translation-only chain: 25 mothers and the two end boxes make d = 26 levels, drifting towards the world's far corner.
std::vector<Level> TranslationChain(int depth) {
  std::vector<Level> chain;
  double mother = kWorldHalf;
  for (int i = 1; i < depth; ++i) {
    const double half = 19900.0 - 760.137 * i;
    const double shift = mother - half - 0.25;
    chain.push_back({"T" + std::to_string(i), Fixed(shift), Fixed(shift * 0.75), Fixed(shift * 0.5), Fixed(half), false,
                     {'z', 1, 0, 1}});
    mother = Num(chain.back().half);
  }
  return chain;
}

// Rotated chain: one mother and the two end boxes make d = 2 levels, a rotation on each.
std::vector<Level> RotationChain() {
  return {{"R1", "18000.1", "3000.3", "-2000.7", "1000.9", true, {'z', 3, 4, 5}}};
}

const Rational kEndRotation{'y', 5, 12, 13};

struct Chain {
  std::string key;
  std::vector<Level> mothers;
  bool rotated_end;
  std::string end_half = "50";
};

G4LogicalVolume* Box(const std::string& name, double half, G4Material* material) {
  return new G4LogicalVolume(new G4Box(name, half, half, half), material, name);
}

int overlaps = 0;

void Checked(G4PVPlacement* placed) {
  if (placed->CheckOverlaps(1000, 0., false)) ++overlaps;
}

class Geometry : public G4VUserDetectorConstruction {
 public:
  Geometry(std::vector<Chain> chains, bool regions) : chains_(std::move(chains)), regions_(regions) {}

  G4VPhysicalVolume* Construct() override {
    auto* vacuum = G4NistManager::Instance()->FindOrBuildMaterial("G4_Galactic");
    auto* world = Box("World", kWorldHalf, vacuum);
    auto* placed = new G4PVPlacement(nullptr, {}, world, "World", nullptr, false, 0);
    for (const auto& chain : chains_) {
      G4LogicalVolume* mother = world;
      for (const auto& level : chain.mothers) {
        auto* logical = Box(level.name, Num(level.half), vacuum);
        Checked(new G4PVPlacement(level.rotated ? Matrix(level.rotation) : nullptr,
                                  {Num(level.tx), Num(level.ty), Num(level.tz)}, logical, level.name, mother, false, 0));
        mother = logical;
      }
      const double half = Num(chain.end_half);
      const double offset = half + Num(kGapHalf);
      for (int side : {-1, 1}) {
        const std::string name = chain.key + (side < 0 ? "A" : "B");
        G4ThreeVector shift(side * offset, 0, 0);
        G4RotationMatrix* rotation = nullptr;
        if (chain.rotated_end) {  // the boxes face each other along their own x axis
          rotation = Matrix(kEndRotation);
          shift = rotation->inverse() * shift;
        }
        Checked(new G4PVPlacement(rotation, shift, Box(name, half, vacuum), name, mother, false, 0));
      }
    }
    if (!regions_) return placed;
    // GB4: three levels of nesting and two regions, in a corner the rotated chain does not reach.
    auto* level1 = Box("G1", 500, vacuum);
    auto* level2 = Box("G2", 300, vacuum);
    auto* level3 = Box("G3", 100, vacuum);
    auto* level4 = Box("G4", 50, vacuum);
    auto* sibling = Box("G5", 100, vacuum);
    Checked(new G4PVPlacement(nullptr, {-15000, -15000, -15000}, level1, "G1", world, false, 0));
    Checked(new G4PVPlacement(nullptr, {}, level2, "G2", level1, false, 0));
    Checked(new G4PVPlacement(nullptr, {}, level3, "G3", level2, false, 0));
    Checked(new G4PVPlacement(nullptr, {}, level4, "G4", level3, false, 0));
    Checked(new G4PVPlacement(nullptr, {-15000, 15000, -15000}, sibling, "G5", world, false, 0));
    (new G4Region("RegionOuter"))->AddRootLogicalVolume(level1);
    (new G4Region("RegionInner"))->AddRootLogicalVolume(level3);
    return placed;
  }

 private:
  std::vector<Chain> chains_;
  bool regions_;
};

class Physics : public G4VUserPhysicsList {
 public:
  void ConstructParticle() override { G4Geantino::GeantinoDefinition(); }
  void ConstructProcess() override { AddTransportation(); }
};

struct Shot {
  std::string chain;
  G4ThreeVector position, direction;
};

class Gun : public G4VUserPrimaryGeneratorAction {
 public:
  explicit Gun(const std::vector<Shot>& shots) : shots_(shots), gun_(1) {
    gun_.SetParticleDefinition(G4Geantino::Definition());
    gun_.SetParticleEnergy(1 * GeV);
  }
  void GeneratePrimaries(G4Event* event) override {
    const auto& shot = shots_.at(event->GetEventID());
    gun_.SetParticlePosition(shot.position);
    gun_.SetParticleMomentumDirection(shot.direction);
    gun_.GeneratePrimaryVertex(event);
  }

 private:
  const std::vector<Shot>& shots_;
  G4ParticleGun gun_;
};

class Steps : public G4UserSteppingAction {
 public:
  explicit Steps(std::vector<std::vector<std::string>>& paths) : paths_(paths) {}
  void UserSteppingAction(const G4Step* step) override {
    if (step->GetTrack()->GetCurrentStepNumber() == 1) paths_.emplace_back();
    paths_.back().push_back(step->GetPreStepPoint()->GetPhysicalVolume()->GetName());
    if (paths_.back().size() > 1000) step->GetTrack()->SetTrackStatus(fStopAndKill);
  }

 private:
  std::vector<std::vector<std::string>>& paths_;
};

G4ThreeVector Apply(const G4RotationMatrix& frame, const G4ThreeVector& v) { return frame.inverse() * v; }

// Global position of a point given in the end box's mother frame, in double: only used to choose sample points.
G4ThreeVector ToGlobal(const Chain& chain, G4ThreeVector local) {
  for (auto level = chain.mothers.rbegin(); level != chain.mothers.rend(); ++level) {
    if (level->rotated) {
      std::unique_ptr<G4RotationMatrix> frame(Matrix(level->rotation));
      local = Apply(*frame, local);
    }
    local += G4ThreeVector(Num(level->tx), Num(level->ty), Num(level->tz));
  }
  return local;
}

G4ThreeVector DirectionToGlobal(const Chain& chain, G4ThreeVector local) {
  for (auto level = chain.mothers.rbegin(); level != chain.mothers.rend(); ++level) {
    if (level->rotated) {
      std::unique_ptr<G4RotationMatrix> frame(Matrix(level->rotation));
      local = Apply(*frame, local);
    }
  }
  return local;
}

std::string Quoted(const std::string& text) { return "\"" + text + "\""; }

void WriteChain(std::ostream& out, const Chain& chain) {
  out << "{\"key\":" << Quoted(chain.key) << ",\"end_half\":" << Quoted(chain.end_half) << ",\"gap_half\":"
      << Quoted(kGapHalf) << ",\"rotated_end\":" << (chain.rotated_end ? "true" : "false")
      << ",\"end_rotation\":[" << Quoted(std::string(1, kEndRotation.axis)) << "," << kEndRotation.c << ","
      << kEndRotation.s << "," << kEndRotation.h << "],\"mothers\":[";
  for (size_t i = 0; i < chain.mothers.size(); ++i) {
    const auto& level = chain.mothers[i];
    out << (i ? "," : "") << "{\"name\":" << Quoted(level.name) << ",\"t\":[" << Quoted(level.tx) << "," << Quoted(level.ty)
        << "," << Quoted(level.tz) << "],\"half\":" << Quoted(level.half) << ",\"rotation\":";
    if (level.rotated) {
      out << "[" << Quoted(std::string(1, level.rotation.axis)) << "," << level.rotation.c << "," << level.rotation.s << ","
          << level.rotation.h << "]";
    } else {
      out << "null";
    }
    out << "}";
  }
  out << "]}";
}

int RunExtent(const std::string& path) {
  const double before = G4GeometryTolerance::GetInstance()->GetSurfaceTolerance();
  G4GeometryManager::GetInstance()->SetWorldMaximumExtent(2 * kWorldHalf);
  const double after = G4GeometryTolerance::GetInstance()->GetSurfaceTolerance();
  std::ofstream out(path);
  out << "{\"extent_mm\":" << Quoted(Hex(2 * kWorldHalf)) << ",\"before\":" << Quoted(Hex(before)) << ",\"after\":"
      << Quoted(Hex(after)) << "}\n";
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 3) {
    std::fprintf(stderr, "usage: gb4_gb10 T|R|extent OUT.json\n");
    return 2;
  }
  if (std::string(argv[1]) == "extent") return RunExtent(argv[2]);

  const bool rotated = std::string(argv[1]) == "R";
  std::vector<Chain> chains = {rotated ? Chain{"R", RotationChain(), true} : Chain{"T", TranslationChain(26), false}};
  std::vector<Shot> shots;
  std::vector<std::vector<std::string>> paths;
  auto* manager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::SerialOnly);
  manager->SetVerboseLevel(0);
  manager->SetUserInitialization(new Geometry(chains, rotated));
  manager->SetUserInitialization(new Physics);
  manager->Initialize();

  std::ostringstream regions;
  bool first = true;
  for (auto* logical : *G4LogicalVolumeStore::GetInstance()) {
    const std::string name = logical->GetName();
    if (name != "World" && name[0] != 'G') continue;
    regions << (first ? "" : ",") << Quoted(name) << ":" << Quoted(logical->GetRegion()->GetName());
    first = false;
  }

  const double tolerance = G4GeometryTolerance::GetInstance()->GetSurfaceTolerance();
  G4Box probe("probe", 1, 1, 1);
  const int inside_near = probe.Inside({1 + 0.4e-9, 0, 0});
  const int inside_far = probe.Inside({1 + 0.6e-9, 0, 0});

  G4Navigator* navigator = G4TransportationManager::GetTransportationManager()->GetNavigatorForTracking();
  std::mt19937_64 random(20261105);
  std::uniform_real_distribution<double> unit(-1.0, 1.0);
  std::ostringstream samples;
  first = true;
  for (const auto& chain : chains) {
    const double half = Num(chain.end_half);
    for (int i = 0; i < 2000; ++i) {
      // Near the facing faces, on both sides of the gap, in the mother frame of the end boxes.
      G4ThreeVector local(unit(random) * 1e-3, unit(random) * 0.8 * half, unit(random) * 0.8 * half);
      if (chain.rotated_end) {
        std::unique_ptr<G4RotationMatrix> frame(Matrix(kEndRotation));
        local = Apply(*frame, local);
      }
      const G4ThreeVector global = ToGlobal(chain, local);
      auto* volume = navigator->LocateGlobalPointAndSetup(global);
      const G4ThreeVector result = navigator->GetGlobalToLocalTransform().TransformPoint(global);
      samples << (first ? "" : ",") << "{\"chain\":" << Quoted(chain.key) << ",\"volume\":" << Quoted(volume->GetName())
              << ",\"global\":[" << Quoted(Hex(global.x())) << "," << Quoted(Hex(global.y())) << "," << Quoted(Hex(global.z()))
              << "],\"local\":[" << Quoted(Hex(result.x())) << "," << Quoted(Hex(result.y())) << ","
              << Quoted(Hex(result.z())) << "]}";
      first = false;
    }
    for (int i = 0; i < 50; ++i) {
      // A geantino from inside box A, along the normal of the gap: x in the end boxes' own frame.
      const double side = half + Num(kGapHalf);
      G4ThreeVector start(-side, unit(random) * 0.8 * half, unit(random) * 0.8 * half);
      G4ThreeVector direction(1, 0, 0);
      if (chain.rotated_end) {
        std::unique_ptr<G4RotationMatrix> frame(Matrix(kEndRotation));
        direction = Apply(*frame, direction);
        start = Apply(*frame, start);
      }
      shots.push_back({chain.key, ToGlobal(chain, start), DirectionToGlobal(chain, direction).unit()});
    }
  }

  manager->SetUserAction(new Gun(shots));
  manager->SetUserAction(new Steps(paths));
  manager->BeamOn(int(shots.size()));

  std::ofstream out(argv[2]);
  out << "{\"geant4\":" << Quoted(G4Version) << ",\"surface_tolerance\":" << Quoted(Hex(tolerance))
      << ",\"inside_at_0p4e-9\":" << inside_near << ",\"inside_at_0p6e-9\":" << inside_far
      << ",\"overlaps\":" << overlaps << ",\"kSurface\":" << int(kSurface) << ",\"kOutside\":" << int(kOutside) << ",\"regions\":{" << regions.str()
      << "},\"chains\":[";
  for (size_t i = 0; i < chains.size(); ++i) {
    if (i) out << ",";
    WriteChain(out, chains[i]);
  }
  out << "],\"samples\":[" << samples.str() << "],\"shots\":[";
  for (size_t i = 0; i < shots.size(); ++i) {
    out << (i ? "," : "") << "{\"chain\":" << Quoted(shots[i].chain) << ",\"path\":[";
    for (size_t j = 0; j < paths[i].size(); ++j) out << (j ? "," : "") << Quoted(paths[i][j]);
    out << "]}";
  }
  out << "]}\n";
  delete manager;
  return 0;
}
