// NewScorers.hh: scorers of a new specification (g4sim plan, Sections 8.2, 8.3, 8.7, 9.1). One dispatcher SD per selected logical sends each step to its
// volume scorers; boundary scorers run from the stepping action, because an SD sees only steps that start inside it (GB5). All sums are per event.
//
// Negative tests of Section 15.1, for tests only: G4SIM_SCORER_CONTROL = drop_bin (bin 0 of every scorer is lost), force_post_step (every charged
// deposit goes to the post-step point), no_backflow, outflow_minus_incidence, kinetic_only_incidence; G4SIM_DEDX_CONTROL = nonionizing_as_ionizing.
#ifndef G4SIM_NEWSCORERS_HH
#define G4SIM_NEWSCORERS_HH

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <set>
#include <string>
#include <tuple>
#include <vector>

#include "Accounting.hh"
#include "BirksTerms.hh"
#include "G4EmSaturation.hh"
#include "G4Field.hh"
#include "G4FieldManager.hh"
#include "G4LogicalVolume.hh"
#include "G4LossTableManager.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4TouchableHistory.hh"
#include "G4Track.hh"
#include "G4VSensitiveDetector.hh"
#include "G4VSolid.hh"
#include "MiniJson.hh"
#include "NewBuild.hh"
#include "NewHits.hh"
#include "ScintillationSplit.hh"

namespace g4sim {

inline std::string ScorerControl() {
  const char* value = std::getenv("G4SIM_SCORER_CONTROL");
  return value ? value : "";
}

constexpr int kClassesPerDecade = 4;
constexpr int kClassOffset = 40;  // log10 x from -10 upward stays positive
constexpr int kClassesPerKind = 200;

struct Segmentation {
  std::string kind = "none";
  int axis = 2;
  double width[3] = {0., 0., 0.};  // along_axis, cartesian: mm; polar: width[0] in r
  int phiBins = 1;
};

struct ScorerSpec {
  std::string name, quantity, split;
  std::set<std::string> templates;
  Segmentation segmentation;
  double fraction = 0.1, rigidityGV = -1., windowLow = -1., windowHigh = -1.;
  std::map<std::string, double> lightYield;  // edep_visible_ly_split: per MeV, by template
  std::string hitKind;  // level event_file: tracker or calorimeter
  bool Boundary() const { return quantity == "n_crossings" || quantity == "crossing_kinematics" || quantity == "energy_out_by_face"; }
  bool First() const { return quantity == "time_first" || quantity == "first_entry_kinematics"; }
};

inline Segmentation ReadSegmentation(const Value& block) {
  Segmentation out;
  out.kind = block.at("kind", "segmentation").str;
  if (block.has("axis")) out.axis = static_cast<int>(block.obj.at("axis").num);
  if (block.has("width_mm")) {
    const auto& widths = block.obj.at("width_mm").array("width_mm");
    for (std::size_t i = 0; i < widths.size() && i < 3; ++i) out.width[i] = widths[i].num;
  }
  if (block.has("phi_bins")) out.phiBins = static_cast<int>(block.obj.at("phi_bins").num);
  return out;
}

inline std::vector<ScorerSpec> ReadScorers(const Value& request) {
  std::vector<ScorerSpec> out;
  for (const auto& item : request.at("scorers", "request").array("scorers")) {
    ScorerSpec spec;
    spec.name = item.at("name", "scorer").str;
    spec.quantity = item.at("quantity", "scorer").str;
    for (const auto& name : item.at("templates", "scorer").array("templates")) spec.templates.insert(name.str);
    spec.segmentation = ReadSegmentation(item.at("segmentation", "scorer"));
    if (item.has("split")) spec.split = item.obj.at("split").str;
    if (item.has("fraction")) spec.fraction = item.obj.at("fraction").num;
    if (item.has("rigidity_GV")) spec.rigidityGV = item.obj.at("rigidity_GV").num;
    if (item.has("hit_kind")) spec.hitKind = item.obj.at("hit_kind").str;
    if (item.has("light_yield_per_MeV"))
      for (const auto& [name, value] : item.obj.at("light_yield_per_MeV").obj) spec.lightYield[name] = value.num;
    if (item.has("window_ns")) {
      spec.windowLow = item.obj.at("window_ns").arr[0].num;
      spec.windowHigh = item.obj.at("window_ns").arr[1].num;
    }
    out.push_back(spec);
  }
  return out;
}

using VolumeKey = long long;

// The volume ID of Section 7.1: the sum of (copy number + 1) x stride over the levels below the world.
inline VolumeKey VolumeId(const G4VTouchable* touchable, const std::vector<long long>& strides) {
  VolumeKey id = 0;
  const int depth = touchable->GetHistoryDepth();
  for (int level = 1; level <= depth; ++level) {
    const int fromTop = level - 1;
    const long long stride = fromTop < static_cast<int>(strides.size()) ? strides[static_cast<std::size_t>(fromTop)] : 0;
    id += static_cast<VolumeKey>(touchable->GetCopyNumber(depth - level) + 1) * stride;
  }
  return id;
}

inline int Clamp(int value, int count) { return value < 0 ? 0 : value >= count ? count - 1 : value; }

// A step's local geometry against one segmentation.
class Grid {
 public:
  Grid(const Segmentation& segmentation, const G4VSolid* solid) : fSegmentation(segmentation) {
    G4ThreeVector low, high;
    solid->BoundingLimits(low, high);
    fLow = low;
    for (int i = 0; i < 3; ++i) {
      const double width = Width(i);
      fCount[i] = width > 0. ? std::max(1, static_cast<int>(std::ceil((high[i] - low[i]) / width - 1e-9))) : 1;
    }
    fHighRadius = std::max(std::abs(low.x()), std::abs(high.x()));
  }
  double Width(int axis) const {
    const std::string& kind = fSegmentation.kind;
    if (kind == "along_axis") return axis == fSegmentation.axis ? fSegmentation.width[0] : 0.;
    if (kind == "cartesian_xy") return axis < 2 ? fSegmentation.width[axis] : 0.;
    if (kind == "cartesian_xyz") return fSegmentation.width[axis];
    return 0.;
  }
  int Bin(const G4ThreeVector& local) const {
    if (fSegmentation.kind == "none") return 0;
    if (fSegmentation.kind == "polar") {
      const int rings = std::max(1, static_cast<int>(std::ceil(fHighRadius / fSegmentation.width[0])));
      const int ring = Clamp(static_cast<int>(local.perp() / fSegmentation.width[0]), rings);
      const double phi = local.phi() < 0. ? local.phi() + CLHEP::twopi : local.phi();
      return ring * fSegmentation.phiBins + Clamp(static_cast<int>(phi / CLHEP::twopi * fSegmentation.phiBins), fSegmentation.phiBins);
    }
    int index[3];
    for (int i = 0; i < 3; ++i) index[i] = Width(i) > 0. ? Clamp(static_cast<int>(std::floor((local[i] - fLow[i]) / Width(i))), fCount[i]) : 0;
    return index[0] + fCount[0] * (index[1] + fCount[1] * index[2]);
  }
  // The bin width in the direction a step crosses (Section 8.7).
  double CrossingWidth(const G4ThreeVector& direction) const {
    if (fSegmentation.kind == "polar") return fSegmentation.width[0];
    double inverse = 0.;
    for (int i = 0; i < 3; ++i)
      if (Width(i) > 0.) inverse += std::abs(direction[i]) / Width(i);
    return inverse > 0. ? 1. / inverse : HUGE_VAL;
  }
  // The fraction of a straight line in each bin: exact for planes, by 64 pieces for polar.
  std::map<int, double> Apportion(const G4ThreeVector& a, const G4ThreeVector& b) const {
    std::vector<double> cuts = {0., 1.};
    if (fSegmentation.kind == "polar") {
      for (int i = 1; i < 64; ++i) cuts.push_back(i / 64.);
    } else {
      for (int i = 0; i < 3; ++i) {
        if (Width(i) <= 0. || a[i] == b[i]) continue;
        const double from = (std::min(a[i], b[i]) - fLow[i]) / Width(i), to = (std::max(a[i], b[i]) - fLow[i]) / Width(i);
        for (int plane = static_cast<int>(std::ceil(from)); plane <= static_cast<int>(std::floor(to)); ++plane) {
          const double t = (fLow[i] + plane * Width(i) - a[i]) / (b[i] - a[i]);
          if (t > 0. && t < 1.) cuts.push_back(t);
        }
      }
    }
    std::sort(cuts.begin(), cuts.end());
    std::map<int, double> out;
    for (std::size_t i = 0; i + 1 < cuts.size(); ++i) {
      const double middle = 0.5 * (cuts[i] + cuts[i + 1]);
      out[Bin(a + middle * (b - a))] += cuts[i + 1] - cuts[i];
    }
    return out;
  }

 private:
  Segmentation fSegmentation;
  G4ThreeVector fLow;
  int fCount[3];
  double fHighRadius = 0.;
};

struct ScoreCell {
  double value = 0., absolute = 0.;
  long summands = 0;
};

struct FaceRow {
  double net = 0.;
  long out = 0, back = 0;
};

struct EnvelopeRow {
  double incident = 0., deposit = 0., killedKinetic = 0., residualU = 0.;
  long entered = 0;
  std::map<std::string, FaceRow> faces;
  std::map<G4int, std::string> leftBy;  // track -> the face it last left through
};

// One thread's sums for the current event.
class ScorerSums {
 public:
  static ScorerSums& Thread() {
    static G4ThreadLocal ScorerSums* instance = nullptr;
    if (!instance) instance = new ScorerSums();
    return *instance;
  }

  void Configure(const std::vector<ScorerSpec>* scorers, const std::vector<long long>* strides, std::FILE* cells, std::FILE* boundary, std::FILE* crossings) {
    fScorers = scorers;
    fStrides = strides;
    fCells = cells;
    fBoundary = boundary;
    fCrossings = crossings;
    fControl = ScorerControl();
    const char* dedx = std::getenv("G4SIM_DEDX_CONTROL");
    fMixNonIonizing = dedx && std::string(dedx) == "nonionizing_as_ionizing";
    fEnvelopes.assign(scorers->size(), EnvelopeRow());
    fLong.assign(scorers->size(), 0);
    fApportioned.assign(scorers->size(), 0);
  }
  void BeginEvent() {
    fSums.clear();
    fFirst.clear();
    for (auto& row : fEnvelopes) row = EnvelopeRow();
  }

  void Add(std::size_t scorer, VolumeKey volume, int bin, double value) {
    ScoreCell& cell = fSums[{scorer, volume, bin}];
    cell.value += value;
    cell.absolute += std::abs(value);
    ++cell.summands;
  }

  // The SD's dispatch: everything a volume scorer does with one step.
  void VolumeStep(const G4Step* step) {
    const G4StepPoint* pre = step->GetPreStepPoint();
    const G4VTouchable* touchable = pre->GetTouchable();
    const G4LogicalVolume* logical = touchable->GetVolume()->GetLogicalVolume();
    const VolumeKey volume = VolumeId(touchable, *fStrides);
    for (std::size_t i = 0; i < fScorers->size(); ++i) {
      const ScorerSpec& scorer = (*fScorers)[i];
      if (scorer.Boundary() || !scorer.templates.count(logical->GetName())) continue;
      if (scorer.windowHigh >= 0. && (pre->GetGlobalTime() / ns < scorer.windowLow || pre->GetGlobalTime() / ns >= scorer.windowHigh)) continue;
      if (scorer.First()) {
        const auto key = std::make_pair(i, volume);
        if (!fFirst.count(key)) fFirst[key] = {pre->GetGlobalTime() / ns, pre->GetKineticEnergy() / MeV, static_cast<double>(step->GetTrack()->GetDefinition()->GetPDGEncoding())};
        continue;
      }
      if (!scorer.hitKind.empty() && step->GetTotalEnergyDeposit() > 0.) {
        if (scorer.hitKind == "tracker") HitRecorder::Thread().Tracker(step, static_cast<double>(volume));
        else HitRecorder::Thread().Calorimeter(step, static_cast<double>(volume));
      }
      Score(i, scorer, step, touchable, volume);
    }
  }

  // The stepping action's part: boundary scorers.
  void BoundaryStep(const G4Step* step, UnreleasedEnergy& unreleased) {
    const G4StepPoint* pre = step->GetPreStepPoint();
    const G4StepPoint* post = step->GetPostStepPoint();
    const G4Track* track = step->GetTrack();
    const G4ParticleDefinition* particle = track->GetDefinition();
    const auto residual = [&]() { return particle->GetPDGEncoding() == -11 ? 2 * CLHEP::electron_mass_c2 : unreleased.Of(particle); };
    for (std::size_t i = 0; i < fScorers->size(); ++i) {
      const ScorerSpec& scorer = (*fScorers)[i];
      if (!scorer.Boundary()) continue;
      EnvelopeRow& row = fEnvelopes[i];
      const int preLevel = Level(pre->GetTouchable(), scorer);
      const bool preIn = preLevel >= 0;
      const bool postIn = post->GetTouchable() && post->GetTouchable()->GetVolume() && Level(post->GetTouchable(), scorer) >= 0;
      if (preIn) row.deposit += step->GetTotalEnergyDeposit();
      if (preIn && track->GetParentID() == 0 && track->GetCurrentStepNumber() == 1) BookIncident(row, pre->GetKineticEnergy(), residual());  // born inside
      if (!preIn && postIn) {
        const double equivalent = post->GetKineticEnergy() + residual();
        auto left = row.leftBy.find(track->GetTrackID());
        if (left != row.leftBy.end()) {
          FaceRow& face = row.faces[left->second];
          ++face.back;
          if (fControl != "no_backflow") face.net -= equivalent;
          row.leftBy.erase(left);
        } else {
          BookIncident(row, post->GetKineticEnergy(), residual());
        }
      } else if (preIn && !postIn) {
        const std::string name = Face(pre->GetTouchable(), preLevel, post->GetPosition());
        FaceRow& face = row.faces[name];
        ++face.out;
        face.net += post->GetKineticEnergy() + residual();
        row.leftBy[track->GetTrackID()] = name;
        if (fCrossings && scorer.quantity == "crossing_kinematics") {
          const G4ThreeVector p = post->GetPosition() / mm, d = post->GetMomentumDirection();
          std::fprintf(fCrossings, "%lld,%s,%s,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n", fEvent, scorer.name.c_str(), name.c_str(), particle->GetPDGEncoding(), post->GetKineticEnergy() / MeV,
                       p.x(), p.y(), p.z(), d.x(), d.y(), d.z(), post->GetGlobalTime() / ns);
        }
      }
      if (preIn && (track->GetTrackStatus() == fStopAndKill || track->GetTrackStatus() == fKillTrackAndSecondaries) && post->GetStepStatus() != fWorldBoundary) {
        const G4VProcess* ended = post->GetProcessDefinedStep();
        const std::string by = ended ? ended->GetProcessName() : "";
        if (by == "KillProcess" || by == "nKiller" || by == "Transportation" || by == "CoupledTransportation") {
          row.killedKinetic += by == "Transportation" || by == "CoupledTransportation" ? post->GetKineticEnergy() : pre->GetKineticEnergy() - step->GetTotalEnergyDeposit();
          row.residualU += residual();
        }
      }
    }
  }

  void BookStackingKill(const G4Track* track, UnreleasedEnergy& unreleased, const std::set<std::string>* unused = nullptr) {
    (void)unused;
    const G4VTouchable* touchable = track->GetTouchable();
    if (!touchable) return;
    for (std::size_t i = 0; i < fScorers->size(); ++i) {
      if (!(*fScorers)[i].Boundary() || Level(touchable, (*fScorers)[i]) < 0) continue;
      fEnvelopes[i].killedKinetic += track->GetKineticEnergy();
      fEnvelopes[i].residualU += track->GetDefinition()->GetPDGEncoding() == -11 ? 2 * CLHEP::electron_mass_c2 : unreleased.Of(track->GetDefinition());
    }
  }

  void EndEvent(long long event) {
    fEvent = event;
    std::map<std::size_t, double> totals;
    std::map<std::size_t, double> absolute;
    std::map<std::size_t, long> summands;
    for (const auto& [key, cell] : fSums) {
      const auto& [scorer, volume, bin] = key;
      totals[scorer] += cell.value;
      absolute[scorer] += cell.absolute;
      summands[scorer] += cell.summands;
      if (fControl == "drop_bin" && bin == 0) continue;
      std::fprintf(fCells, "%lld,%s,%lld,%d,%.17g,%ld,%.17g\n", event, (*fScorers)[scorer].name.c_str(), volume, bin, cell.value, cell.summands, cell.absolute);
    }
    for (const auto& [scorer, value] : fDirect) std::fprintf(fCells, "%lld,%s,-1,-1,%.17g,%ld,%.17g\n", event, (*fScorers)[scorer].name.c_str(), value, summands[scorer], absolute[scorer]);
    fDirect.clear();
    for (const auto& [key, first] : fFirst) std::fprintf(fCells, "%lld,%s,%lld,0,%.17g,%.0f,%.17g\n", event, (*fScorers)[key.first].name.c_str(), key.second, first[0], first[2], first[1]);
    for (std::size_t i = 0; i < fScorers->size(); ++i) {
      const ScorerSpec& scorer = (*fScorers)[i];
      if (!scorer.Boundary()) continue;
      const EnvelopeRow& row = fEnvelopes[i];
      double outflow = 0.;
      long out = 0, back = 0;
      for (const auto& [face, sums] : row.faces) {
        outflow += sums.net;
        out += sums.out;
        back += sums.back;
        std::fprintf(fBoundary, "%lld,%s,%s,%.17g,%ld,%ld\n", event, scorer.name.c_str(), face.c_str(), sums.net / MeV, sums.out, sums.back);
      }
      const double balance = fControl == "outflow_minus_incidence" ? row.incident - row.deposit - (outflow - row.incident) - row.killedKinetic - row.residualU
                                                                   : row.incident - row.deposit - outflow - row.killedKinetic - row.residualU;
      std::fprintf(fBoundary, "%lld,%s,balance,%.17g,%ld,%ld,%.17g,%.17g,%.17g,%.17g\n", event, scorer.name.c_str(), balance / MeV, out, back, row.incident / MeV, row.deposit / MeV, row.killedKinetic / MeV, row.residualU / MeV);
    }
  }
  void SetEvent(long long event) { fEvent = event; }
  long LongSteps(std::size_t i) const { return fLong[i]; }
  long ApportionedSteps(std::size_t i) const { return fApportioned[i]; }

 private:
  void BookIncident(EnvelopeRow& row, double kinetic, double residual) {
    row.incident += kinetic + (fControl == "kinetic_only_incidence" ? 0. : residual);
    ++row.entered;
  }
  // The level of `touchable` holding the scorer's envelope, or -1.
  static int Level(const G4VTouchable* touchable, const ScorerSpec& scorer) {
    for (int level = 0; level <= touchable->GetHistoryDepth(); ++level)
      if (scorer.templates.count(touchable->GetVolume(level)->GetLogicalVolume()->GetName())) return level;
    return -1;
  }
  static std::string Face(const G4VTouchable* touchable, int level, const G4ThreeVector& global) {
    const G4ThreeVector local = touchable->GetHistory()->GetTransform(touchable->GetHistoryDepth() - level).TransformPoint(global);
    const G4ThreeVector normal = touchable->GetVolume(level)->GetLogicalVolume()->GetSolid()->SurfaceNormal(local);
    int axis = 0;
    for (int i = 1; i < 3; ++i)
      if (std::abs(normal[i]) > std::abs(normal[axis])) axis = i;
    return std::string(normal[axis] < 0 ? "-" : "+") + "xyz"[axis];
  }

  void Score(std::size_t i, const ScorerSpec& scorer, const G4Step* step, const G4VTouchable* touchable, VolumeKey volume) {
    const G4Track* track = step->GetTrack();
    const G4ParticleDefinition* particle = track->GetDefinition();
    const G4MaterialCutsCouple* couple = step->GetPreStepPoint()->GetMaterialCutsCouple();
    const double deposit = step->GetTotalEnergyDeposit(), length = step->GetStepLength(), nonIonizing = step->GetNonIonizingEnergyDeposit();
    const bool charged = particle->GetPDGCharge() != 0.;
    if (scorer.quantity == "edep_by_dedx_class") {
      for (const DepositPart& part : DepositParts(particle, couple, length, deposit, nonIonizing, fMixNonIonizing)) {
        const int bin = static_cast<int>(part.kind) * kClassesPerKind + (part.x > 0. ? Clamp(static_cast<int>(std::floor(std::log10(part.x) * kClassesPerDecade)) + kClassOffset, kClassesPerKind) : 0);
        Add(i, volume, bin, part.energy / MeV);
        fDirect[i] += part.energy / MeV;
      }
      return;
    }
    double value = 0.;
    if (scorer.quantity == "edep") value = deposit / MeV;
    else if (scorer.quantity == "edep_charged") value = charged ? deposit / MeV : 0.;
    else if (scorer.quantity == "edep_nonionizing") value = nonIonizing / MeV;
    else if (scorer.quantity == "edep_visible" || scorer.quantity == "edep_visible_ly_split") value = G4LossTableManager::Instance()->EmSaturation()->VisibleEnergyDepositionAtAStep(step) / MeV;
    else if (scorer.quantity == "track_length") value = charged || particle->GetParticleName() == "geantino" ? length / mm : 0.;  // a geantino scan measures paths (S3 gate 2)
    if (value == 0.) return;
    fDirect[i] += value;
    // edep_visible_ly_split: bin 2b holds E^L_b and 2b + 1 holds E^S_b, by the whole step's mu_s; a row's count of summands is n^L_b for the first (Section 10.3)
    const bool split = scorer.quantity == "edep_visible_ly_split";
    const int part = split ? (IsLargeStep(scorer.lightYield.at(touchable->GetVolume()->GetLogicalVolume()->GetName()) * value, ScintillationControl()) ? 0 : 1) : 0;
    const int stride = split ? 2 : 1;
    if (scorer.segmentation.kind == "none") {
      Add(i, volume, part, value);
      return;
    }
    const G4AffineTransform& toLocal = touchable->GetHistory()->GetTopTransform();
    const G4ThreeVector a = toLocal.TransformPoint(step->GetPreStepPoint()->GetPosition()), b = toLocal.TransformPoint(step->GetPostStepPoint()->GetPosition());
    const Grid grid(scorer.segmentation, touchable->GetVolume()->GetLogicalVolume()->GetSolid());
    const G4ThreeVector chord = b - a;
    const double width = chord.mag() > 0. ? grid.CrossingWidth(chord.unit()) : HUGE_VAL;
    if (!charged || length <= scorer.fraction * width || fControl == "force_post_step") {
      Add(i, volume, grid.Bin(b) * stride + part, value);
      return;
    }
    Sagitta(i, step, length, grid);
    if (scorer.split == "midpoint") {
      Add(i, volume, grid.Bin(0.5 * (a + b)) * stride + part, value);
      return;
    }
    for (const auto& [bin, share] : grid.Apportion(a, b)) Add(i, volume, bin * stride + part, value * share);
  }

  // Section 8.7: an apportioned step's sagitta against 10% of the bin width.
  void Sagitta(std::size_t i, const G4Step* step, double length, const Grid& grid) {
    ++fApportioned[i];
    const G4FieldManager* manager = step->GetPreStepPoint()->GetTouchable()->GetVolume()->GetLogicalVolume()->GetFieldManager();
    const G4Field* field = manager ? manager->GetDetectorField() : nullptr;
    if (!field) return;
    const G4ThreeVector position = step->GetPreStepPoint()->GetPosition();
    const double point[4] = {position.x(), position.y(), position.z(), 0.};
    double b[6] = {0, 0, 0, 0, 0, 0};
    field->GetFieldValue(point, b);
    const double tesla_ = G4ThreeVector(b[0], b[1], b[2]).mag() / tesla;
    const double charge = std::abs(step->GetTrack()->GetDynamicParticle()->GetCharge());
    if (tesla_ <= 0. || charge <= 0.) return;
    const double radius = step->GetPreStepPoint()->GetMomentum().mag() / GeV / (0.3 * charge * tesla_) * m;
    const G4ThreeVector chord = step->GetPostStepPoint()->GetPosition() - position;
    if (chord.mag() > 0. && length * length / (8. * radius) > 0.1 * grid.CrossingWidth(chord.unit())) ++fLong[i];
  }

  const std::vector<ScorerSpec>* fScorers = nullptr;
  const std::vector<long long>* fStrides = nullptr;
  std::FILE* fCells = nullptr;
  std::FILE* fBoundary = nullptr;
  std::FILE* fCrossings = nullptr;
  std::string fControl;
  bool fMixNonIonizing = false;
  long long fEvent = 0;
  std::map<std::tuple<std::size_t, VolumeKey, int>, ScoreCell> fSums;
  std::map<std::size_t, double> fDirect;
  std::map<std::pair<std::size_t, VolumeKey>, std::array<double, 3>> fFirst;
  std::vector<EnvelopeRow> fEnvelopes;
  std::vector<long> fLong, fApportioned;
};

class Dispatcher : public G4VSensitiveDetector {
 public:
  explicit Dispatcher(const std::string& name) : G4VSensitiveDetector(name) {}
  G4bool ProcessHits(G4Step* step, G4TouchableHistory*) override {
    ScorerSums::Thread().VolumeStep(step);
    return true;
  }
};

}  // namespace g4sim

#endif
