// simreco: digitization and reconstruction of element_sim events (adapters/geant4, Geant4 program B2.1, B2.2). C++17
// standard library only; links no Geant4 (it reads the crossings simroot dumped and element_sim's per-event CSV).
//
// Usage: simreco SPEC.json   (the effective reco spec geant4_run.py reco writes: the user's simreco.spec/1 plus the
//        geometry, the particle table, the logical-run seed, the replica number and the input and output paths)
// Per event of the input CSV: the primary's (track 1) entries into the tracker planes give the measured points
// (nominal: Gaussian errors in y and z; with noise-digitization: strips, charge sharing, threshold, efficiency,
// noise hits and clustering; with pattern-recognition: hits of every charged track and noise associated plane by
// plane), the track fit of Fit.hh gives the signed inverse rigidity and the charge, the TOF layers give the station
// times and beta, the calorimeter's active deposit over the sampling fraction gives its energy. Random numbers:
// SplitMix64 and Box-Muller of SimHash.hh, event i's stream seeded with H(S, i, "digi"), replica m's misalignment with
// H(S, "align", m) and field non-uniformity with H(S, "fieldnu", m); never std::normal_distribution.
// Outputs: the per-event result CSV (first line "# RECONSTRUCTION", columns below) and, with output.observables, the
// run summary (simulation-summary/1, producer simreco) of the declared observables over the CSV columns.
// stdout ends with one line "SIMRECO_STATUS {json}". Exit codes: 0 ok; 2 the spec or an input was refused.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include "Fit.hh"
#include "MiniJson.hh"
#include "SimHash.hh"
#include "SimObservables.hh"
#include "SimSummary.hh"

using minijson::JsonError;
using minijson::Value;
using simreco::Hit;

namespace {

constexpr double kCmmPerNs = 299.792458;
constexpr const char* kTailNames[] = {"alignment", "calibration-non-uniformity", "noise-digitization",
                                      "pattern-recognition"};

struct Plane {
  int id = 0;  // element index in the element_sim spec (plane_id of the crossings)
  std::string name, role;
  double x_face = 0, centre_y = 0, centre_z = 0, half_y = 0, half_z = 0, x_over_x0 = 0, thickness = 0;
};

struct FieldRegion {
  double lo = 0, hi = 0, bz = 0;  // extent along x (mm), nominal B_z (T)
};

struct Particle {
  double mass = 0, charge = 0;
};

struct Strips {
  double pitch_y = 0, pitch_z = 0, sharing = 0, threshold = 0, efficiency = 1, noise_per_plane = 0;
};

struct Spec {
  long long seed = 0;
  int replica = 0;
  double sigma_y_mm = 0.01, sigma_z_mm = 0.03, sigma_t_ns = 0.1;
  double test_tof_offset_ns = 0;  // TEST ONLY: the negative control of the TOF bookkeeping benchmarks (B3.2)
  double offset_per_GV = 0, field_scale_global = 0;
  double sampling_fraction = 0, mip_active_MeV = 0;
  bool ms = true;
  double chi2_cut = 0;  // fit.chi2_per_ndof_cut: a fitted track is selected when chi2/ndof <= it (0: no cut)
  std::vector<Plane> trackers, tofs;
  std::vector<FieldRegion> field;
  std::vector<std::string> calo_active_columns;
  std::vector<std::string> calo_columns;  // every calorimeter element's deposit (containment)
  std::map<int, Particle> particles;
  std::set<std::string> tails;
  double align_sigma_y = 0, align_sigma_z = 0, align_sigma_rot = 0, align_residual_y = 0, align_residual_z = 0,
         align_residual_rot = 0;
  double fieldnu_sigma = 0, fieldnu_gradient = 0;
  Strips strips;
  double pr_window_mm = 1.0, pr_chi2_cut = 50, pr_min_hits = 4;
  std::string crossings, events, out_csv, out_summary;
  std::vector<g4sim::ObservableDecl> observables;
  long block_size = 0, blocks = 0, block_first_event = 0;
};

double Num(const Value& o, const std::string& k, double d, const std::string& where) {
  return o.has(k) ? o.obj.at(k).number(where + "." + k) : d;
}

Spec Read(const std::string& path) {
  std::ifstream in(path);
  if (!in) throw JsonError("cannot read " + path);
  std::stringstream buf;
  buf << in.rdbuf();
  Value r = minijson::parse(buf.str());
  if (r.at("schema", "spec").string("schema") != "simreco.effective/1") throw JsonError("schema must be simreco.effective/1");
  Spec s;
  s.seed = static_cast<long long>(r.at("logical_run_seed", "spec").number("logical_run_seed"));
  s.replica = static_cast<int>(r.at("replica", "spec").number("replica"));
  const Value& u = r.at("reco", "spec");
  const Value& pr = u.at("point_resolution_um", "reco");
  s.sigma_y_mm = pr.at("bending", "point_resolution_um").number("bending") * 1e-3;
  s.sigma_z_mm = pr.at("non_bending", "point_resolution_um").number("non_bending") * 1e-3;
  if (u.has("tof")) {
    s.sigma_t_ns = u.obj.at("tof").at("sigma_t_ps", "tof").number("sigma_t_ps") * 1e-3;
    if (u.obj.at("tof").has("test_layer_offset_ps"))
      s.test_tof_offset_ns = u.obj.at("tof").at("test_layer_offset_ps", "tof").number("test_layer_offset_ps") * 1e-3;
  }
  s.offset_per_GV = Num(u, "curvature_offset_per_GV", 0, "reco");
  s.field_scale_global = Num(u, "field_scale_global", 0, "reco");
  if (u.has("calorimeter")) {
    const Value& c = u.obj.at("calorimeter");
    s.sampling_fraction = Num(c, "sampling_fraction", 0, "calorimeter");
    s.mip_active_MeV = Num(c, "mip_active_MeV", 0, "calorimeter");
  }
  if (u.has("fit") && u.obj.at("fit").has("multiple_scattering"))
    s.ms = u.obj.at("fit").obj.at("multiple_scattering").boolean("fit.multiple_scattering");
  if (u.has("fit")) s.chi2_cut = Num(u.obj.at("fit"), "chi2_per_ndof_cut", 0, "fit");
  if (u.has("tail_sources")) {
    const Value& t = u.obj.at("tail_sources");
    for (const char* name : kTailNames) {
      if (!t.has(name)) continue;
      const Value& v = t.obj.at(name);
      if (!v.has("on") || !v.obj.at("on").boolean(std::string(name) + ".on")) continue;
      s.tails.insert(name);
      std::string w = std::string("tail_sources.") + name;
      if (std::string(name) == "alignment") {
        s.align_sigma_y = Num(v, "misalignment_sigma_y_um", 0, w) * 1e-3;
        s.align_sigma_z = Num(v, "misalignment_sigma_z_um", 0, w) * 1e-3;
        s.align_sigma_rot = Num(v, "misalignment_sigma_rot_urad", 0, w) * 1e-6;
        s.align_residual_y = Num(v, "residual_sigma_y_um", 0, w) * 1e-3;
        s.align_residual_z = Num(v, "residual_sigma_z_um", 0, w) * 1e-3;
        s.align_residual_rot = Num(v, "residual_sigma_rot_urad", 0, w) * 1e-6;
      } else if (std::string(name) == "calibration-non-uniformity") {
        s.fieldnu_sigma = Num(v, "sigma", 0, w);
        s.fieldnu_gradient = Num(v, "gradient_sigma", 0, w);
      } else if (std::string(name) == "noise-digitization") {
        s.strips = {Num(v, "pitch_y_um", 50, w) * 1e-3, Num(v, "pitch_z_um", 100, w) * 1e-3, Num(v, "sharing_um", 10, w) * 1e-3,
                    Num(v, "threshold", 0.2, w), Num(v, "efficiency", 1.0, w), Num(v, "noise_hits_per_plane", 0, w)};
      } else {
        s.pr_window_mm = Num(v, "window_mm", 1.0, w);
        s.pr_chi2_cut = Num(v, "chi2_per_ndof_cut", 50, w);
        s.pr_min_hits = Num(v, "min_hits", 4, w);
      }
    }
  }
  const Value& g = r.at("geometry", "spec");
  for (const auto& pv : g.at("planes", "geometry").array("geometry.planes")) {
    Plane p;
    p.id = static_cast<int>(pv.at("id", "plane").number("plane.id"));
    p.name = pv.at("name", "plane").string("plane.name");
    p.role = pv.at("role", "plane").string("plane.role");
    p.x_face = pv.at("x_face_mm", "plane").number("plane.x_face_mm");
    p.thickness = pv.at("thickness_mm", "plane").number("plane.thickness_mm");
    p.centre_y = pv.at("centre_y_mm", "plane").number("plane.centre_y_mm");
    p.centre_z = pv.at("centre_z_mm", "plane").number("plane.centre_z_mm");
    p.half_y = pv.at("half_y_mm", "plane").number("plane.half_y_mm");
    p.half_z = pv.at("half_z_mm", "plane").number("plane.half_z_mm");
    p.x_over_x0 = pv.at("x_over_x0", "plane").number("plane.x_over_x0");
    (p.role == "tracker-plane" ? s.trackers : s.tofs).push_back(p);
  }
  auto byx = [](const Plane& a, const Plane& b) { return a.x_face < b.x_face; };
  std::sort(s.trackers.begin(), s.trackers.end(), byx);
  std::sort(s.tofs.begin(), s.tofs.end(), byx);
  for (const auto& fv : g.at("field_regions", "geometry").array("geometry.field_regions"))
    s.field.push_back({fv.at("lo_mm", "field").number("lo_mm"), fv.at("hi_mm", "field").number("hi_mm"),
                       fv.at("bz_tesla", "field").number("bz_tesla")});
  for (const auto& c : g.at("calorimeter_active_columns", "geometry").array("calorimeter_active_columns"))
    s.calo_active_columns.push_back(c.string("calorimeter_active_columns"));
  if (g.has("calorimeter_columns"))
    for (const auto& c : g.at("calorimeter_columns", "geometry").array("calorimeter_columns"))
      s.calo_columns.push_back(c.string("calorimeter_columns"));
  for (const auto& pv : r.at("particles", "spec").array("particles"))
    s.particles[static_cast<int>(pv.at("pdg", "particle").number("pdg"))] = {
        pv.at("mass_GeV", "particle").number("mass_GeV"), pv.at("charge", "particle").number("charge")};
  const Value& io = r.at("io", "spec");
  s.crossings = io.at("crossings", "io").string("crossings");
  s.events = io.at("events", "io").string("events");
  s.out_csv = io.at("out_csv", "io").string("out_csv");
  s.out_summary = io.at("out_summary", "io").string("out_summary");
  if (u.has("output") && u.obj.at("output").has("observables")) {
    const Value& o = u.obj.at("output");
    s.observables = g4sim::ParseObservables(o.obj.at("observables"), "output.observables");
    const Value& b = o.at("blocks", "output");
    s.blocks = static_cast<long>(b.at("blocks", "blocks").number("blocks"));
    s.block_size = static_cast<long>(b.at("block_size", "blocks").number("block_size"));
    s.block_first_event = static_cast<long>(Num(b, "first_event", 0, "blocks"));
  }
  if (s.trackers.size() < 3) throw JsonError("at least three tracker planes are needed for a fit");
  return s;
}

std::vector<std::string> SplitCsv(const std::string& line) {
  std::vector<std::string> out;
  std::string cur;
  for (char c : line) {
    if (c == ',') {
      out.push_back(cur);
      cur.clear();
    } else {
      cur += c;
    }
  }
  out.push_back(cur);
  return out;
}

struct Crossing {
  int plane = 0, track = 0, pdg = 0;
  double x = 0, y = 0, z = 0, dx = 0, dy = 0, dz = 0, ekin = 0, t = 0, edep = 0;
};

// crossings by event, from simroot dump (header line, rows sorted by event)
std::map<long, std::vector<Crossing>> ReadCrossings(const std::string& path) {
  std::ifstream in(path);
  if (!in) throw JsonError("cannot read " + path);
  std::string line;
  std::getline(in, line);
  auto cols = SplitCsv(line);
  std::map<std::string, std::size_t> ix;
  for (std::size_t i = 0; i < cols.size(); ++i) ix[cols[i]] = i;
  for (const char* c : {"event_id", "plane_id", "track_id", "pdg", "x_mm", "y_mm", "z_mm", "dx", "dy", "dz",
                        "ekin_MeV", "t_ns", "edep_MeV"})
    if (!ix.count(c)) throw JsonError(path + " has no column " + c);
  std::map<long, std::vector<Crossing>> out;
  while (std::getline(in, line)) {
    if (line.empty()) continue;
    auto v = SplitCsv(line);
    if (v.size() != cols.size()) throw JsonError(path + ": a row with " + std::to_string(v.size()) + " of " +
                                                 std::to_string(cols.size()) + " columns");
    Crossing c;
    long ev = std::stol(v[ix["event_id"]]);
    c.plane = std::stoi(v[ix["plane_id"]]);
    c.track = std::stoi(v[ix["track_id"]]);
    c.pdg = std::stoi(v[ix["pdg"]]);
    c.x = std::stod(v[ix["x_mm"]]);
    c.y = std::stod(v[ix["y_mm"]]);
    c.z = std::stod(v[ix["z_mm"]]);
    c.dx = std::stod(v[ix["dx"]]);
    c.dy = std::stod(v[ix["dy"]]);
    c.dz = std::stod(v[ix["dz"]]);
    c.ekin = std::stod(v[ix["ekin_MeV"]]);
    c.t = std::stod(v[ix["t_ns"]]);
    c.edep = std::stod(v[ix["edep_MeV"]]);
    out[ev].push_back(c);
  }
  return out;
}

double BzAt(const Spec& s, double x, const std::vector<double>& delta) {
  for (std::size_t r = 0; r < s.field.size(); ++r)
    if (x >= s.field[r].lo && x <= s.field[r].hi) return s.field[r].bz * (1 + delta[r]);
  return 0.;
}

// the position resolution of the strip digitization: outside the sharing band (width w around each boundary) the
// cluster sits at the strip centre (uniform error over p - w), inside it the charge-weighted position is exact
// (linear sharing): sigma^2 = (p - w)^3 / (12 p)
inline double StripSigma(double pitch, double sharing) {
  double q = std::max(pitch - std::min(sharing, pitch), 0.0);
  return std::sqrt(q * q * q / (12.0 * pitch));
}

struct Measured {
  std::vector<Hit> hits;
  std::vector<int> planeIndex;  // index into s.trackers
  int fakes = 0;                // associated hits not from the primary
};

int Status(const std::string& status, const std::string& error) {
  std::cout << "SIMRECO_STATUS {\"status\": " << g4sim::JsonQuote(status)
            << (error.empty() ? "" : ", \"error\": " + g4sim::JsonQuote(error)) << "}" << std::endl;
  return status == "ok" ? 0 : 2;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc == 2 && (std::string(argv[1]) == "--help" || std::string(argv[1]) == "-h")) {
    std::cout << "simreco SPEC.json: digitization and reconstruction of element_sim events (see the header of "
                 "simreco.cc)\n";
    return 0;
  }
  if (argc != 2) return Status("rejected", "usage: simreco SPEC.json");
  Spec s;
  std::map<long, std::vector<Crossing>> crossings;
  try {
    s = Read(argv[1]);
    crossings = ReadCrossings(s.crossings);
  } catch (const std::exception& e) {
    return Status("rejected", e.what());
  }
  std::ifstream ev(s.events);
  std::string line;
  if (!ev || !std::getline(ev, line) || line != "# SIMULATION") return Status("rejected", "cannot read " + s.events);
  std::getline(ev, line);
  auto cols = SplitCsv(line);
  std::map<std::string, std::size_t> ix;
  for (std::size_t i = 0; i < cols.size(); ++i) ix[cols[i]] = i;
  for (const auto& c : s.calo_active_columns)
    if (!ix.count(c)) return Status("rejected", s.events + " has no column " + c);
  if (!ix.count("primary_pdg") || !ix.count("event")) return Status("rejected", s.events + " is not an element_sim CSV");

  // replica draws: misalignment residuals per plane, field non-uniformity per region (common mean removed)
  std::size_t nt = s.trackers.size();
  std::vector<double> ay(nt, 0.), az(nt, 0.), arot(nt, 0.), delta(s.field.size(), 0.);
  if (s.tails.count("alignment")) {
    g4sim::BoxMuller g(static_cast<std::uint64_t>(g4sim::SeedHash({s.seed, "align", static_cast<long long>(s.replica)})));
    for (std::size_t k = 0; k < nt; ++k) {
      ay[k] = s.align_residual_y * g.Next();
      az[k] = s.align_residual_z * g.Next();
      arot[k] = s.align_residual_rot * g.Next();
    }
  }
  double gradient = 0;
  if (s.tails.count("calibration-non-uniformity")) {
    g4sim::BoxMuller g(static_cast<std::uint64_t>(g4sim::SeedHash({s.seed, "fieldnu", static_cast<long long>(s.replica)})));
    double mean = 0;
    for (auto& d : delta) {
      d = s.fieldnu_sigma * g.Next();
      mean += d;
    }
    if (!delta.empty()) mean /= static_cast<double>(delta.size());
    for (auto& d : delta) d -= mean;
    gradient = s.fieldnu_gradient * g.Next();
  }
  double xmid = 0.5 * (s.trackers.front().x_face + s.trackers.back().x_face);
  double lever = s.trackers.back().x_face - s.trackers.front().x_face;
  // the reconstruction field per segment: nominal x (1 + global scale) x (1 + delta(region)) x (1 + gradient term)
  simreco::SegmentField bz(nt - 1, 0.);
  for (std::size_t k = 0; k + 1 < nt; ++k) {
    double xm = 0.5 * (s.trackers[k].x_face + s.trackers[k + 1].x_face);
    bz[k] = BzAt(s, xm, delta) * (1 + s.field_scale_global) * (1 + gradient * (xm - xmid) / lever);
  }
  bool digi = s.tails.count("noise-digitization") > 0, patrec = s.tails.count("pattern-recognition") > 0;

  std::ofstream out(s.out_csv);
  const std::vector<std::string> outCols = {"event", "replica", "pdg", "charge_true", "rig_true_GV", "n_true_planes",
                                            "fit_ok", "n_hits", "n_fake_hits", "chi2", "ndof", "selected", "charge_reco",
                                            "rig_reco_GV", "inv_rig_res", "rho_sigma", "rho_pull", "charge_flip", "beta_true", "beta_reco",
                                            "beta_res", "tof1_layer_dt_ps", "tof2_layer_dt_ps", "tof1_layer_resid_ps",
                                            "tof2_layer_resid_ps", "e_cal_MeV",
                                            "e_over_mip", "containment", "rear_leak_fraction"};
  out << "# RECONSTRUCTION\n";
  for (std::size_t i = 0; i < outCols.size(); ++i) out << (i ? "," : "") << outCols[i];
  out << "\n";
  g4sim::SummaryAccumulator acc = s.observables.empty()
                                      ? g4sim::SummaryAccumulator()
                                      : g4sim::SummaryAccumulator(s.observables, s.block_size, s.blocks,
                                                                  s.block_first_event);
  long nevents = 0;
  std::map<int, std::size_t> trackerIndex;
  for (std::size_t k = 0; k < nt; ++k) trackerIndex[s.trackers[k].id] = k;
  try {  // a malformed number in the events CSV is unusable input (exit 2), never an abort
  while (std::getline(ev, line)) {
    if (line.empty()) continue;
    auto v = SplitCsv(line);
    if (v.size() != cols.size())
      return Status("rejected", s.events + ": a row with " + std::to_string(v.size()) + " of " +
                                    std::to_string(cols.size()) + " columns");
    long event = std::stol(v[ix["event"]]);
    int pdg = std::stoi(v[ix["primary_pdg"]]);
    auto pit = s.particles.find(pdg);
    if (pit == s.particles.end()) return Status("rejected", "no mass and charge for PDG code " + std::to_string(pdg));
    const Particle part = pit->second;
    const auto& xs = crossings[event];
    g4sim::BoxMuller rng(static_cast<std::uint64_t>(g4sim::SeedHash({s.seed, static_cast<long long>(event), "digi"})));
    g4sim::SplitMix64 uni(static_cast<std::uint64_t>(g4sim::SeedHash({s.seed, static_cast<long long>(event), "digi-u"})));
    // truth: the primary's entries into the tracker planes
    std::vector<const Crossing*> prim(nt, nullptr);
    double invp_sum = 0;
    int ntrue = 0;
    for (const auto& c : xs)
      if (c.track == 1 && trackerIndex.count(c.plane)) {
        prim[trackerIndex[c.plane]] = &c;
        double e = c.ekin * 1e-3 + part.mass, p = std::sqrt(std::max(0.0, e * e - part.mass * part.mass));
        if (p > 0) invp_sum += 1 / p;
        ++ntrue;
      }
    // true signed inverse rigidity q/R: the mean of |q|/p_i over the plane entries, with the sign of q (B2.1)
    double rho_true = ntrue && part.charge != 0 ? (part.charge > 0 ? 1 : -1) * std::fabs(part.charge) * invp_sum / ntrue
                                                : 0;
    // measured hits: per plane candidates
    std::vector<std::vector<Hit>> cand(nt);
    std::vector<std::vector<int>> candTrack(nt);
    for (const auto& c : xs) {
      auto t = trackerIndex.find(c.plane);
      if (t == trackerIndex.end()) continue;
      if (!patrec && c.track != 1) continue;
      std::size_t k = t->second;
      const Plane& pl = s.trackers[k];
      Hit h;
      h.x = pl.x_face;
      h.x_over_x0 = pl.x_over_x0;
      double yt = c.y + ay[k] - arot[k] * (c.z - pl.centre_z), zt = c.z + az[k] + arot[k] * (c.y - pl.centre_y);
      if (digi) {
        // the strip grid's phase is random per plane and event: tracks illuminate a sensor uniformly and the grids
        // of different planes are not aligned to each other, so a fixed pencil beam must not see the same
        // quantization in every event (that would make the digitization error a common offset, not a measurement
        // error: J15 at 100 GV)
        double phase_y = uni.Uniform() * s.strips.pitch_y, phase_z = uni.Uniform() * s.strips.pitch_z;
        if (uni.Uniform() >= s.strips.efficiency) continue;
        auto cluster = [&](double u, double centre, double pitch) {
          // two strips share the charge linearly within the sharing width around a strip boundary
          double rel = (u - centre) / pitch;
          double strip = std::floor(rel);
          double f = rel - strip;  // position within the strip, [0, 1)
          double w = s.strips.sharing / pitch;
          double q0 = 1, q1 = 0, nb = strip + 1;
          if (f > 1 - w / 2) {
            q1 = (f - (1 - w / 2)) / w;
            q0 = 1 - q1;
          } else if (f < w / 2) {
            q1 = (w / 2 - f) / w;
            q0 = 1 - q1;
            nb = strip - 1;
          }
          double c0 = centre + (strip + 0.5) * pitch, c1 = centre + (nb + 0.5) * pitch;
          bool k0 = q0 >= s.strips.threshold, k1 = q1 >= s.strips.threshold;
          if (!k0 && !k1) return c0;
          double sq = (k0 ? q0 : 0) + (k1 ? q1 : 0);
          return ((k0 ? q0 * c0 : 0) + (k1 ? q1 * c1 : 0)) / sq;
        };
        h.y = cluster(yt, pl.centre_y + phase_y, s.strips.pitch_y);
        h.z = cluster(zt, pl.centre_z + phase_z, s.strips.pitch_z);
        h.sigma_y = StripSigma(s.strips.pitch_y, s.strips.sharing);
        h.sigma_z = StripSigma(s.strips.pitch_z, s.strips.sharing);
      } else {
        h.y = yt + s.sigma_y_mm * rng.Next();
        h.z = zt + s.sigma_z_mm * rng.Next();
        h.sigma_y = s.sigma_y_mm;
        h.sigma_z = s.sigma_z_mm;
      }
      cand[k].push_back(h);
      candTrack[k].push_back(c.track);
    }
    if (digi && s.strips.noise_per_plane > 0)
      for (std::size_t k = 0; k < nt; ++k) {
        // Poisson number of noise hits (inversion with the uniform stream), uniform over the plane
        double l = std::exp(-s.strips.noise_per_plane), p = uni.Uniform();
        int n = 0;
        double cum = l;
        while (p > cum && n < 50) {
          ++n;
          l *= s.strips.noise_per_plane / n;
          cum += l;
        }
        for (int j = 0; j < n; ++j) {
          if (!patrec) break;
          const Plane& pl = s.trackers[k];
          Hit h;
          h.x = pl.x_face;
          h.x_over_x0 = pl.x_over_x0;
          h.y = pl.centre_y + (2 * uni.Uniform() - 1) * pl.half_y;
          h.z = pl.centre_z + (2 * uni.Uniform() - 1) * pl.half_z;
          h.sigma_y = digi ? StripSigma(s.strips.pitch_y, s.strips.sharing) : s.sigma_y_mm;
          h.sigma_z = digi ? StripSigma(s.strips.pitch_z, s.strips.sharing) : s.sigma_z_mm;
          cand[k].push_back(h);
          candTrack[k].push_back(-1);
        }
      }
    simreco::FitOptions fo;
    fo.multiple_scattering = s.ms;
    fo.mass_GeV = part.mass;
    fo.charge = part.charge != 0 ? part.charge : 1.;
    // a track's arcs between consecutive hits: the field of an arc that skips planes (a missing hit) is the
    // path-weighted mean over the plane segments it spans; a skipped plane still scatters, and its x/X0 is added to
    // the preceding hit (its lever arm one plane longer: the covariance errs on the large side)
    auto segOf = [&](const Measured& m) {
      simreco::SegmentField seg;
      for (std::size_t i = 0; i + 1 < m.hits.size(); ++i) {
        std::size_t a = static_cast<std::size_t>(m.planeIndex[i]), b = static_cast<std::size_t>(m.planeIndex[i + 1]);
        double num = 0, den = 0;
        for (std::size_t q = a; q < b && q + 1 < nt; ++q) {
          double dx = s.trackers[q + 1].x_face - s.trackers[q].x_face;
          num += bz[q] * dx;
          den += dx;
        }
        seg.push_back(den > 0 ? num / den : bz[std::min(a, nt - 2)]);
      }
      return seg;
    };
    auto hitsOf = [&](const Measured& m) {
      std::vector<Hit> hs = m.hits;
      for (std::size_t i = 0; i + 1 < hs.size(); ++i)
        for (int q = m.planeIndex[i] + 1; q < m.planeIndex[i + 1]; ++q) hs[i].x_over_x0 += s.trackers[q].x_over_x0;
      return hs;
    };
    Measured best;
    simreco::FitResult fit;
    if (!patrec) {
      for (std::size_t k = 0; k < nt; ++k)
        if (!cand[k].empty()) {
          best.hits.push_back(cand[k][0]);
          best.planeIndex.push_back(static_cast<int>(k));
        }
    } else {
      // seeds: every triplet of hits on the first, middle and last planes with hits (a helix through three points,
      // so the curvature is in the seed); then each other plane in turn takes the nearest hit within the window around
      // the prediction of the current fit; the candidate with the best chi2/ndof and at least min_hits hits wins
      double bestq = 1e300;
      std::vector<std::size_t> withHits;
      for (std::size_t k = 0; k < nt; ++k)
        if (!cand[k].empty()) withHits.push_back(k);
      auto sorted = [](Measured m) {  // hits in increasing x (the fit propagates plane by plane)
        std::vector<std::size_t> o(m.hits.size());
        for (std::size_t i = 0; i < o.size(); ++i) o[i] = i;
        std::sort(o.begin(), o.end(), [&](std::size_t a, std::size_t b) { return m.planeIndex[a] < m.planeIndex[b]; });
        Measured r;
        r.fakes = m.fakes;
        for (std::size_t i : o) {
          r.hits.push_back(m.hits[i]);
          r.planeIndex.push_back(m.planeIndex[i]);
        }
        return r;
      };
      if (withHits.size() >= 3) {
        std::size_t k0 = withHits.front(), k2 = withHits.back(), k1 = withHits[withHits.size() / 2];
        for (std::size_t a = 0; a < cand[k0].size() && a < 8; ++a)
          for (std::size_t b = 0; b < cand[k1].size() && b < 8; ++b)
            for (std::size_t c = 0; c < cand[k2].size() && c < 8; ++c) {
              Measured m;
              m.fakes = (candTrack[k0][a] != 1) + (candTrack[k1][b] != 1) + (candTrack[k2][c] != 1);
              m.hits = {cand[k0][a], cand[k1][b], cand[k2][c]};
              m.planeIndex = {static_cast<int>(k0), static_cast<int>(k1), static_cast<int>(k2)};
              for (std::size_t k : withHits) {
                if (k == k0 || k == k1 || k == k2) continue;
                Measured cur = sorted(m);
                simreco::FitResult f = simreco::FitTrack(hitsOf(cur), segOf(cur), fo);
                if (!f.ok) break;
                // predict at plane k: propagate the current fit through the planes up to x_k
                std::vector<Hit> hs;
                simreco::SegmentField seg;
                for (std::size_t q = 0; q <= k; ++q) {
                  Hit probe = cur.hits.front();
                  probe.x = s.trackers[q].x_face;
                  if (q >= static_cast<std::size_t>(cur.planeIndex.front())) hs.push_back(probe);
                }
                for (std::size_t q = static_cast<std::size_t>(cur.planeIndex.front()); q < k; ++q) seg.push_back(bz[q]);
                std::vector<double> yy, ss, sp;
                double cl = 1 / std::sqrt(1 + f.tan_lambda * f.tan_lambda);
                if (k < static_cast<std::size_t>(cur.planeIndex.front())) continue;  // the seed starts at the first plane
                simreco::Propagate(hs, seg, f.y0, f.s0, f.rho, cl, yy, ss, sp);
                double py = yy.back(), pz = f.z0 + f.tan_lambda * sp.back();
                double bd = 1e300;
                int bi = -1;
                for (std::size_t q = 0; q < cand[k].size(); ++q) {
                  double d = std::hypot(cand[k][q].y - py, (cand[k][q].z - pz) * s.sigma_y_mm / s.sigma_z_mm);
                  if (d < bd) {
                    bd = d;
                    bi = static_cast<int>(q);
                  }
                }
                if (bi >= 0 && bd <= s.pr_window_mm) {
                  m.hits.push_back(cand[k][bi]);
                  m.planeIndex.push_back(static_cast<int>(k));
                  m.fakes += candTrack[k][bi] != 1;
                }
              }
              if (m.hits.size() < static_cast<std::size_t>(s.pr_min_hits)) continue;
              Measured fin = sorted(m);
              simreco::FitResult f = simreco::FitTrack(hitsOf(fin), segOf(fin), fo);
              if (!f.ok || f.ndof < 1) continue;
              double q = f.chi2 / f.ndof;
              if (q < bestq) {
                bestq = q;
                best = fin;
                fit = f;
              }
            }
      }
      if (fit.ok && fit.chi2 / fit.ndof > s.pr_chi2_cut) fit.ok = false;
    }
    if (!patrec && best.hits.size() >= 3) fit = simreco::FitTrack(hitsOf(best), segOf(best), fo);
    double rho_reco = fit.ok ? fit.rho + s.offset_per_GV : 0;
    bool ok = fit.ok && rho_true != 0 && rho_reco != 0;
    double charge_reco = ok ? (rho_reco > 0 ? 1 : -1) : 0, charge_true = part.charge > 0 ? 1 : (part.charge < 0 ? -1 : 0);
    double rig_true = rho_true != 0 ? 1 / std::fabs(rho_true) : 0;  // rho = q / R
    double rig_reco = ok ? 1 / std::fabs(rho_reco) : 0;
    double res = ok ? rho_reco / rho_true - 1 : 0;
    // the selection: a fitted track that passes the fit-quality cut (and, with pattern recognition, its own cut);
    // charge confusion and the resolution are counted over selected tracks
    bool selected = ok && (s.chi2_cut <= 0 || fit.chi2 / std::max(fit.ndof, 1) <= s.chi2_cut);
    // TOF: layer times smeared; station time = mean of the two layers transported to the station centre
    std::map<int, const Crossing*> tofc;
    for (const auto& c : xs)
      if (c.track == 1)
        for (const auto& t : s.tofs)
          if (t.id == c.plane) tofc[c.plane] = &c;
    double beta_true = 0, beta_reco = 0, dt1 = 0, dt2 = 0, r1 = 0, r2 = 0;
    if (s.tofs.size() >= 4 && tofc.size() == 4 && ok) {
      double tl[4], xl[4];
      for (int k = 0; k < 4; ++k) {
        const Crossing* c = tofc[s.tofs[k].id];
        tl[k] = c->t + (k == 2 ? s.test_tof_offset_ns : 0.) + s.sigma_t_ns * rng.Next();
        xl[k] = c->x;
      }
      double pTot = rig_true * std::fabs(part.charge);
      double beta_nom = pTot / std::hypot(pTot, part.mass);
      double st1 = 0.5 * (s.tofs[0].x_face + s.tofs[1].x_face + s.tofs[1].thickness);
      double st2 = 0.5 * (s.tofs[2].x_face + s.tofs[3].x_face + s.tofs[3].thickness);
      // transport along x at the measured beta (the stations are outside the field)
      double t1 = 0.5 * ((tl[0] + (st1 - xl[0]) / (beta_nom * kCmmPerNs)) + (tl[1] + (st1 - xl[1]) / (beta_nom * kCmmPerNs)));
      double t2 = 0.5 * ((tl[2] + (st2 - xl[2]) / (beta_nom * kCmmPerNs)) + (tl[3] + (st2 - xl[3]) / (beta_nom * kCmmPerNs)));
      // path between station centres: straight from TOF1 to the first plane, the fitted arc, straight to TOF2
      std::vector<double> yy, ss, sp;
      double cl = 1 / std::sqrt(1 + fit.tan_lambda * fit.tan_lambda);
      simreco::Propagate(best.hits, segOf(best), fit.y0, fit.s0, fit.rho, cl, yy, ss, sp);
      double c0 = std::sqrt(1 - fit.s0 * fit.s0), c1 = std::sqrt(1 - ss.back() * ss.back());
      double inFront = (best.hits.front().x - st1) / (c0 * cl), behind = (st2 - best.hits.back().x) / (c1 * cl);
      double path = inFront + sp.back() / cl + behind;
      beta_reco = path / (kCmmPerNs * (t2 - t1));
      // the truth, independent of the reconstruction (so tof-beta checks the reconstructed path and the timing): the
      // primary's own crossings from the first to the last TOF layer, chord lengths over their time difference
      std::vector<const Crossing*> pts;
      for (const auto& c : xs)
        if (c.track == 1 && c.x >= xl[0] - 1e-9 && c.x <= xl[3] + 1e-9) pts.push_back(&c);
      std::sort(pts.begin(), pts.end(), [](const Crossing* a, const Crossing* b) { return a->x < b->x; });
      double chord = 0;
      for (std::size_t i = 1; i < pts.size(); ++i)
        chord += std::sqrt((pts[i]->x - pts[i - 1]->x) * (pts[i]->x - pts[i - 1]->x) +
                           (pts[i]->y - pts[i - 1]->y) * (pts[i]->y - pts[i - 1]->y) +
                           (pts[i]->z - pts[i - 1]->z) * (pts[i]->z - pts[i - 1]->z));
      double dtt = pts.size() > 1 ? pts.back()->t - pts.front()->t : 0;
      beta_true = dtt > 0 ? chord / (kCmmPerNs * dtt) : 0;
      dt1 = (tl[1] - tl[0]) * 1e3;
      dt2 = (tl[3] - tl[2]) * 1e3;
      // the two-layer residual against the inter-layer flight time along the true trajectory (bookkeeping, B2.7)
      r1 = dt1 - (tofc[s.tofs[1].id]->t - tofc[s.tofs[0].id]->t) * 1e3;
      r2 = dt2 - (tofc[s.tofs[3].id]->t - tofc[s.tofs[2].id]->t) * 1e3;
    }
    double eact = 0;
    for (const auto& c : s.calo_active_columns) eact += std::stod(v[ix[c]]);
    double ecal = s.sampling_fraction > 0 ? eact / s.sampling_fraction : 0;
    double emip = s.mip_active_MeV > 0 ? eact / s.mip_active_MeV : 0;
    // shower containment (B2.3): the calorimeter's total deposit (every calorimeter element) over the incident
    // kinetic energy; not 1 - net leakage / E0: the net leakage per face subtracts energy that enters through a face
    // other than the primary's first entry, so photons radiated upstream (TOF, silicon) count as negative front
    // leakage and that ratio exceeds 1 (J15, 10 GeV electrons). The rear-leakage fraction is the rear face's net
    // outflow over E0 (little enters through the rear face)
    double contain = 0, rear = 0;
    if (ix.count("primary_ekin_MeV")) {
      double e0 = std::stod(v[ix["primary_ekin_MeV"]]) + (pdg == -11 ? 2e3 * part.mass : 0.);  // an e+ annihilates
      double dep = 0;
      for (const auto& c : s.calo_columns)
        if (ix.count(c)) dep += std::stod(v[ix[c]]);
      if (e0 > 0) {
        contain = dep / e0;
        if (ix.count("leak_rear_MeV")) rear = std::stod(v[ix["leak_rear_MeV"]]) / e0;
      }
    }
    std::vector<double> row = {static_cast<double>(event), static_cast<double>(s.replica), static_cast<double>(pdg),
                               charge_true, rig_true, static_cast<double>(ntrue), ok ? 1. : 0.,
                               static_cast<double>(best.hits.size()), static_cast<double>(best.fakes),
                               ok ? fit.chi2 : 0., ok ? static_cast<double>(fit.ndof) : 0., selected ? 1. : 0.,
                               charge_reco, rig_reco, res,
                               ok ? fit.sigma_rho : 0., ok && fit.sigma_rho > 0 ? (rho_reco - rho_true) / fit.sigma_rho : 0.,
                               selected && charge_reco != charge_true ? 1. : 0., beta_true, beta_reco,
                               beta_true > 0 && beta_reco > 0 ? beta_reco / beta_true - 1 : 0., dt1, dt2, r1, r2,
                               ecal, emip,
                               contain, rear};
    for (std::size_t i = 0; i < row.size(); ++i) {
      char buf[40];
      std::snprintf(buf, sizeof buf, "%.17g", row[i]);
      out << (i ? "," : "") << buf;
    }
    out << "\n";
    if (!acc.Empty()) {
      g4sim::Row r;
      for (std::size_t i = 0; i < row.size(); ++i) r[outCols[i]] = g4sim::Cell::Number(row[i]);
      try {
        acc.Fill(event, r);
      } catch (const g4sim::SummaryError& e) {
        return Status("rejected", e.what());
      }
    }
    ++nevents;
  }
  } catch (const std::logic_error& e) {
    return Status("rejected", std::string("malformed number in ") + s.events + ": " + e.what());
  }
  out.close();
  std::string tails = "[";
  bool first = true;
  for (const char* n : kTailNames)
    if (s.tails.count(n)) {
      tails += (first ? "" : ", ") + g4sim::JsonQuote(n);
      first = false;
    }
  tails += "]";
  if (!acc.Empty()) {
    std::string run = "{\"seeding\": \"per-event\", \"logical_run_seed\": " + std::to_string(s.seed) +
                      ", \"weight_column\": \"unit\", \"replica\": " + std::to_string(s.replica) +
                      ", \"tail_sources_simulated\": " + tails + "}";
    std::ofstream(s.out_summary) << acc.Json(run, "{\"name\": \"simreco\", \"version\": \"0.4.1\"}");
  }
  std::cout << "SIMRECO_EVENTS " << nevents << "\nSIMRECO_TAILS " << tails << std::endl;
  return Status("ok", "");
}
