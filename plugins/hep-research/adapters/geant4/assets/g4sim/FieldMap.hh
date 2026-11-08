// Field maps (Section 6.2.8, S7): a g4sim-field-map/1 grid in the local frame of the one template that declares the field.
// g4sim_run.py copies the file it hashed to field-map.<name>.txt in the run folder; the IR holds the grid and the hash.
// The interpolation follows core/geometry/fieldmap.py operation by operation, so both sides round alike.
#pragma once

#include <array>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <map>
#include <memory>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "G4AffineTransform.hh"
#include "G4MagneticField.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"

namespace g4sim {

struct FieldGrid {
  std::array<double, 3> origin{}, step{};
  std::array<long, 3> count{};
  std::vector<double> values;  // bx, by, bz in tesla per node, x fastest

  void At(const double point[3], double field[3]) const {
    long cells[3];
    double weights[3];
    for (int axis = 0; axis < 3; ++axis) {
      double u = (point[axis] - origin[axis]) / step[axis];
      u = std::min(std::max(u, 0.0), static_cast<double>(count[axis] - 1));
      const long index = std::min(static_cast<long>(std::floor(u)), count[axis] - 2);
      cells[axis] = index;
      weights[axis] = u - static_cast<double>(index);
    }
    field[0] = field[1] = field[2] = 0.0;
    for (int c = 0; c < 2; ++c)
      for (int b = 0; b < 2; ++b)
        for (int a = 0; a < 2; ++a) {
          const double w = (a ? weights[0] : 1.0 - weights[0]) * (b ? weights[1] : 1.0 - weights[1]) * (c ? weights[2] : 1.0 - weights[2]);
          const std::size_t node = 3 * static_cast<std::size_t>((cells[2] + c) * count[1] * count[0] + (cells[1] + b) * count[0] + (cells[0] + a));
          for (int k = 0; k < 3; ++k) field[k] += w * values[node + k];
        }
  }
};

// One read per file for the whole process: workers share the grid read-only; the field objects stay thread-local (GB3).
inline std::shared_ptr<const FieldGrid> ReadFieldGrid(const std::string& path, const std::array<double, 3>& origin, const std::array<double, 3>& step,
                                                      const std::array<long, 3>& count) {
  static std::mutex lock;
  static std::map<std::string, std::shared_ptr<const FieldGrid>> read;
  std::lock_guard<std::mutex> hold(lock);
  auto found = read.find(path);
  if (found != read.end()) return found->second;
  std::ifstream in(path);
  if (!in) throw std::runtime_error("field map " + path + " cannot be opened");
  std::string line;
  for (int header = 0; header < 5; ++header)
    if (!std::getline(in, line)) throw std::runtime_error("field map " + path + ": the header is short");
  auto grid = std::make_shared<FieldGrid>();
  grid->origin = origin;
  grid->step = step;
  grid->count = count;
  const std::size_t nodes = static_cast<std::size_t>(count[0] * count[1] * count[2]);
  grid->values.reserve(3 * nodes);
  while (std::getline(in, line)) {
    if (line.empty()) continue;
    std::istringstream row(line);
    std::string text;
    while (row >> text) grid->values.push_back(std::strtod(text.c_str(), nullptr));  // correctly rounded, as Python's float()
  }
  if (grid->values.size() != 3 * nodes) throw std::runtime_error("field map " + path + ": the value count is not 3 x the nodes of the IR's grid");
  return read[path] = grid;
}

class MapField : public G4MagneticField {
 public:
  MapField(std::shared_ptr<const FieldGrid> grid, const G4AffineTransform& toLocal, double sign)
      : fGrid(std::move(grid)), fToLocal(toLocal), fToGlobal(toLocal.Inverse()), fSign(sign) {}

  void GetFieldValue(const G4double point[4], G4double* field) const override {
    const G4ThreeVector local = fToLocal.TransformPoint(G4ThreeVector(point[0], point[1], point[2]));
    const double at[3] = {local.x() / mm, local.y() / mm, local.z() / mm};
    double b[3];
    fGrid->At(at, b);
    // the grid holds components along the frame template's axes: turned back into the global frame (rotation only)
    const G4ThreeVector global = fToGlobal.TransformAxis(G4ThreeVector(b[0], b[1], b[2]));
    for (int k = 0; k < 3; ++k) field[k] = fSign * global[k] * tesla;
  }

 private:
  std::shared_ptr<const FieldGrid> fGrid;
  G4AffineTransform fToLocal;  // global to the frame template's local frame, composed as G4NavigationLevel does
  G4AffineTransform fToGlobal;
  double fSign;
};

}  // namespace g4sim
