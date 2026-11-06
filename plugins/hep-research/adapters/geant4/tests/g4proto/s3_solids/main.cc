// Prototypes GB23 and GB24 of the g4sim plan (Section 23): real Geant4 solids asked what judge.py wrote; this program judges nothing.
// Usage: s3_solids QUESTIONS.txt ANSWERS.txt
//   prism ID SIDES APOTHEM HALF_Z X Y Z    -> ID inside|surface|outside
//   box ID HX HY HZ, trd ID X1 X2 Y1 Y2 Z, tube ID RMIN RMAX Z START SPAN (radians), polyprism ID SIDES APOTHEM HALF_Z -> ID %a
// Every number is a C hex float, so nothing is rounded on the way in or out.
#include "G4Box.hh"
#include "G4Polyhedra.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4Trd.hh"
#include "G4Tubs.hh"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

namespace {
double Read(std::istringstream& line) {
  std::string text;
  line >> text;
  return std::strtod(text.c_str(), nullptr);
}

std::unique_ptr<G4Polyhedra> Prism(int sides, double apothem, double halfZ) {
  const double z[2] = {-halfZ, halfZ}, inner[2] = {0., 0.}, outer[2] = {apothem, apothem};
  return std::make_unique<G4Polyhedra>("prism", 0., CLHEP::twopi, sides, 2, z, inner, outer);
}
}  // namespace

int main(int argc, char** argv) {
  if (argc != 3) {
    std::puts("{\"status\": \"rejected\", \"message\": \"usage: s3_solids QUESTIONS.txt ANSWERS.txt\"}");
    return 2;
  }
  std::ifstream questions(argv[1]);
  std::ofstream answers(argv[2]);
  std::string text;
  while (std::getline(questions, text)) {
    std::istringstream line(text);
    std::string kind, id;
    line >> kind >> id;
    char volume[64];
    if (kind == "prism") {
      int sides;
      line >> sides;
      const double apothem = Read(line), halfZ = Read(line), x = Read(line), y = Read(line), z = Read(line);
      const EInside where = Prism(sides, apothem, halfZ)->Inside(G4ThreeVector(x, y, z));
      answers << id << ' ' << (where == kInside ? "inside" : where == kSurface ? "surface" : "outside") << '\n';
      continue;
    }
    double value = 0.;
    if (kind == "box") {
      const double a = Read(line), b = Read(line), c = Read(line);
      value = G4Box("s", a, b, c).GetCubicVolume();
    } else if (kind == "trd") {
      const double a = Read(line), b = Read(line), c = Read(line), d = Read(line), e = Read(line);
      value = G4Trd("s", a, b, c, d, e).GetCubicVolume();
    } else if (kind == "tube") {
      const double a = Read(line), b = Read(line), c = Read(line), d = Read(line), e = Read(line);
      value = G4Tubs("s", a, b, c, d, e).GetCubicVolume();
    } else if (kind == "polyprism") {
      int sides;
      line >> sides;
      const double apothem = Read(line), halfZ = Read(line);
      value = Prism(sides, apothem, halfZ)->GetCubicVolume();
    } else {
      std::printf("{\"status\": \"rejected\", \"message\": \"unknown question %s\"}\n", kind.c_str());
      return 2;
    }
    std::snprintf(volume, sizeof volume, "%a", value);
    answers << id << ' ' << volume << '\n';
  }
  std::puts("{\"status\": \"ok\"}");
  return 0;
}
