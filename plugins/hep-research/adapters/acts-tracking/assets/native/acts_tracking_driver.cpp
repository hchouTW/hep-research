// The T07 native driver (t07-t09-task-sheets.md): ACTS 48.2.0 on measurements, with its own product format. It reads a data
// file and never opens truth: no input path with the truth suffix is opened, a truth file under another name is refused by its
// magic, and neither the truth code nor the seed stream nor the generation constants are linked here.
//
//   acts_tracking_driver self-test --work-dir DIR
//   acts_tracking_driver refit --data-file D --hit-sets H --field-tesla B --product-id NAME --product-file P
//   acts_tracking_driver rewrite-product --product-in P --product-file Q
//
// refit accepts zero field, where the hits carry no q/p, or section 4.1's 1 T, where they do. No noise, finding or vertexing here. From D1 stage 8 it
// writes acts-tracking-product/2: the /1 records, unchanged, and the R33 outputs of each fit (track_fit_outputs.hpp). rewrite-product reads either version.
#include <Acts/ActsVersion.hpp>
#include <Acts/Definitions/Algebra.hpp>
#include <Acts/Geometry/TrackingVolume.hpp>
#include <Acts/Surfaces/BoundaryTolerance.hpp>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "kalman_refit.hpp"
#include "native_product.hpp"
#include "plane_propagation.hpp"
#include "sha256.hpp"
#include "t07_data_file.hpp"
#include "t07_fixture_constants.hpp"
#include "telescope_geometry.hpp"
#include "track_fit_outputs.hpp"

namespace {

std::map<std::string, std::string> parse_flags(int argc, char** argv, int first) {
  std::map<std::string, std::string> flags;
  for (int index = first; index < argc; index += 2) {
    const std::string flag = argv[index];
    if (flag.rfind("--", 0) != 0 || index + 1 >= argc) {
      throw std::invalid_argument("expected --flag value, got " + flag);
    }
    flags[flag.substr(2)] = argv[index + 1];
  }
  return flags;
}

std::string required(const std::map<std::string, std::string>& flags, const std::string& name) {
  const auto found = flags.find(name);
  if (found == flags.end()) {
    throw std::invalid_argument("--" + name + " is required");
  }
  return found->second;
}

void require_only(const std::map<std::string, std::string>& flags, const std::set<std::string>& known) {
  for (const auto& [name, value] : flags) {
    if (known.count(name) == 0) {
      throw std::invalid_argument("unknown flag --" + name);
    }
  }
}

void refuse_overwriting_input(const std::string& written, const std::string& input) {
  if (std::filesystem::weakly_canonical(written) == std::filesystem::weakly_canonical(input)) {
    throw std::invalid_argument("refused: the product would overwrite its input " + input);
  }
}

std::string acts_version_text() {
  std::ostringstream text;
  text << Acts::VersionInfo::fromLibrary().withoutCommit();
  return text.str();
}

struct HitSetFile {
  std::string data_sha256;
  std::vector<t07::HitSet> hit_sets;
};

// acts-tracking-hit-sets/1: known hit sets, role truth-assisted. A separate tool derives them; this driver opens no truth.
HitSetFile read_hit_sets(const std::string& path) {
  t07::refuse_truth_path(path);
  std::ifstream input(path);
  if (!input) {
    throw std::invalid_argument("cannot open " + path);
  }
  std::string format, role_key, role, digest_key;
  HitSetFile file;
  input >> format >> role_key >> role >> digest_key >> file.data_sha256;
  if (format != "acts-tracking-hit-sets/1" || role_key != "role" || role != "truth-assisted" || digest_key != "data_sha256") {
    throw std::invalid_argument("refused: " + path + " is not acts-tracking-hit-sets/1 with role truth-assisted");
  }
  std::string record;
  while (input >> record) {
    if (record != "hit_set") {
      throw std::invalid_argument("refused: unknown record " + record + " in " + path);
    }
    t07::HitSet hit_set;
    std::size_t hit_count = 0;
    if (!(input >> hit_set.track_key >> hit_set.event_ordinal >> hit_set.assumed_q_over_p >> hit_count)) {
      throw std::invalid_argument("refused: a malformed hit_set in " + path);
    }
    if (hit_count > std::size_t(t07::plane_count)) {  // one hit per plane at most, and no count from a file sizes an allocation
      throw std::invalid_argument("refused: a hit_set in " + path + " has more hits than planes");
    }
    hit_set.hit_keys.resize(hit_count);
    for (std::uint32_t& hit_key : hit_set.hit_keys) {
      if (!(input >> hit_key)) {
        throw std::invalid_argument("refused: a hit_set in " + path + " ends early");
      }
    }
    file.hit_sets.push_back(hit_set);
  }
  if (!input.eof()) {
    throw std::invalid_argument("refused: " + path + " does not read to its end");
  }
  return file;
}

int refit(const std::map<std::string, std::string>& flags) {
  require_only(flags, {"data-file", "hit-sets", "field-tesla", "product-id", "product-file"});
  const std::string data_path = required(flags, "data-file");
  const std::string hit_sets_path = required(flags, "hit-sets");
  const std::string out_path = required(flags, "product-file");
  const std::string product_id = required(flags, "product-id");
  const std::string field_text = required(flags, "field-tesla");
  std::size_t used = 0;
  double field = 0.0;
  try {
    field = std::stod(field_text, &used);
  } catch (const std::out_of_range&) {
    throw std::invalid_argument("--field-tesla is out of range: " + field_text);
  }
  if (used != field_text.size() || !std::isfinite(field)) {
    throw std::invalid_argument("--field-tesla is not a number: " + field_text);
  }
  // The prior on q/p is settled against sigma(q/p) at section 4.1's field (kalman_refit.hpp). At a weaker field the measurement widens towards
  // the prior, which would then be a constraint, and the product would still say "measured": an unidentifiable quantity reported with
  // precision (t04-prereg.md). tests/adapters/test_acts_refit_field.py fails if this goes.
  if (field != 0.0 && field != t07::field_tesla) {
    throw std::invalid_argument("refit accepts zero field or the fixture's field of " + std::to_string(t07::field_tesla) + " T, not " + field_text + ": its prior on q/p is settled for that field");
  }

  refuse_overwriting_input(out_path, data_path);
  refuse_overwriting_input(out_path, hit_sets_path);
  t07::DataFileReader reader(data_path);  // a truth path stops here, before any other input is read
  const std::string data_sha256 = t07::sha256_of_file(data_path);
  const HitSetFile hit_set_file = read_hit_sets(hit_sets_path);
  if (hit_set_file.data_sha256 != data_sha256) {
    throw std::invalid_argument("refused: the hit sets were made for another data file");
  }
  std::map<std::uint32_t, std::vector<const t07::HitSet*>> by_event;
  for (const t07::HitSet& hit_set : hit_set_file.hit_sets) {
    by_event[hit_set.event_ordinal].push_back(&hit_set);
  }
  if (!by_event.empty() && by_event.rbegin()->first >= reader.header().event_count) {
    throw std::invalid_argument("refused: a hit set names an event the data file does not hold");
  }

  const t07::TelescopeGeometry telescope = t07::build_telescope_geometry();
  const t07::KalmanRefit fitter(telescope, field, reader.header().sigma_loc0_mm, reader.header().sigma_loc1_mm);

  t07::ProductDocument document;
  document.format_version = 2;  // R33's outputs (D1 stage 8)
  t07::ProductHeader& header = document.header;
  header.product_id = product_id;
  header.recipe = "reco.track.acts-kf-refit/1";
  header.stage = "refit-known-hit-set";
  header.evidence_class = "truth-assisted";
  header.data_product = "t07-measurements-" + data_sha256.substr(0, 16);
  header.data_sha256 = data_sha256;
  header.hit_sets_sha256 = t07::sha256_of_file(hit_sets_path);
  header.field_tesla = field;
  header.qop_status = field == 0.0 ? "assumed-not-measured" : "measured";
  header.material_model = "none";
  header.start_prior = {t07::refit_start_x_mm, t07::refit_prior_loc_sigma_mm, t07::refit_prior_angle_sigma, t07::refit_prior_qop_sigma_per_gev,
                        t07::refit_prior_time_sigma};
  header.acts_version = acts_version_text();
  header.r33_conventions = t07::r33_conventions_name;
  header.alignment_parametrization = t07::alignment_parametrization_name;
  header.alignment_frame = t07::alignment_frame_name;
  header.alignment_level = t07::alignment_level_name;

  std::map<std::string, int> seen_keys;
  std::size_t failed = 0;
  t07::DataEvent event;
  for (std::uint32_t ordinal = 0; reader.next(event); ++ordinal) {
    const auto found = by_event.find(ordinal);
    if (found == by_event.end()) {
      continue;
    }
    for (const t07::HitSet* hit_set : found->second) {
      if (++seen_keys[hit_set->track_key] > 1) {
        throw std::invalid_argument("refused: track key twice: " + hit_set->track_key);
      }
      t07::RefitOutputs outputs;
      t07::RefitResult result = fitter.fit(*hit_set, event, outputs);
      failed += result.track.status == "failed" ? 1 : 0;
      document.tracks.push_back(result.track);
      document.states.insert(document.states.end(), result.states.begin(), result.states.end());
      document.parameters.insert(document.parameters.end(), result.parameters.begin(), result.parameters.end());
      document.track_outputs.insert(document.track_outputs.end(), outputs.track_output.begin(), outputs.track_output.end());
      document.residuals.insert(document.residuals.end(), outputs.residuals.begin(), outputs.residuals.end());
      document.measurement_outputs.insert(document.measurement_outputs.end(), outputs.measurement_outputs.begin(), outputs.measurement_outputs.end());
      document.residual_covariances.insert(document.residual_covariances.end(), outputs.residual_covariance.begin(), outputs.residual_covariance.end());
    }
  }
  t07::write_whole_file(out_path, t07::encode_product(document));
  std::cout << "{\"status\": \"ok\", \"tracks\": " << document.tracks.size() << ", \"failed\": " << failed
            << ", \"stage\": \"" << header.stage << "\", \"evidence_class\": \"" << header.evidence_class << "\"}\n";
  return 0;
}

int rewrite_product(const std::map<std::string, std::string>& flags) {
  require_only(flags, {"product-in", "product-file"});
  t07::refuse_truth_path(required(flags, "product-in"));
  const t07::ProductDocument document = t07::decode_product(t07::read_whole_file(required(flags, "product-in")));
  t07::write_whole_file(required(flags, "product-file"), t07::encode_product(document));
  std::cout << "{\"status\": \"ok\", \"tracks\": " << document.tracks.size() << "}\n";
  return 0;
}

class SelfTest {
 public:
  void check(const std::string& name, bool passed) {
    std::cout << (passed ? "PASS " : "FAIL ") << name << "\n";
    m_failed += passed ? 0 : 1;
  }
  template <typename action_t>
  void check_refused(const std::string& name, action_t action) {
    try {
      action();
    } catch (const std::exception&) {
      check(name, true);
      return;
    }
    check(name, false);
  }
  int finish() const {
    std::cout << (m_failed == 0 ? "ALL PASS" : "SOME FAILED") << "\n";
    return m_failed == 0 ? 0 : 1;
  }

 private:
  int m_failed = 0;
};

void check_version_and_hash(SelfTest& test) {
  test.check("ACTS header and library versions agree", Acts::VersionInfo::fromHeader().withoutCommit() == Acts::VersionInfo::fromLibrary().withoutCommit());
  test.check("ACTS is 48.2.0", acts_version_text() == "48.2.0");
  test.check("SHA-256 of abc", t07::hex_of(t07::sha256_of_text("abc")) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
}

void check_geometry(SelfTest& test, const t07::TelescopeGeometry& telescope) {
  const Acts::GeometryContext& context = telescope.geometry_context;
  int sensitive_count = 0;
  telescope.tracking_geometry->visitSurfaces([&sensitive_count](const Acts::Surface* /*surface*/) { ++sensitive_count; });
  test.check("the geometry holds eight sensitive surfaces", sensitive_count == t07::plane_count);
  test.check("the builder keeps eight planes", int(telescope.planes.size()) == t07::plane_count);
  bool found_again = true;
  bool placed = true;
  bool local_axes = true;
  for (std::size_t index = 0; index < telescope.planes.size(); ++index) {
    const Acts::Surface& plane = *telescope.planes[index];
    found_again = found_again && plane.isSensitive() && telescope.tracking_geometry->findSurface(plane.geometryId()) == &plane;
    const double x = double(index) * t07::plane_spacing_mm;
    const Acts::Vector3 along_track = Acts::Vector3::UnitX();
    const Acts::Vector3 centre = plane.localToGlobal(context, Acts::Vector2(0.0, 0.0), along_track);
    placed = placed && (centre - Acts::Vector3(x, 0.0, 0.0)).norm() < 1e-9;
    const Acts::Vector3 along_loc0 = plane.localToGlobal(context, Acts::Vector2(1.0, 0.0), along_track);
    const Acts::Vector3 along_loc1 = plane.localToGlobal(context, Acts::Vector2(0.0, 1.0), along_track);
    local_axes = local_axes && (along_loc0 - Acts::Vector3(x, 1.0, 0.0)).norm() < 1e-9 && (along_loc1 - Acts::Vector3(x, 0.0, 1.0)).norm() < 1e-9;
  }
  test.check("every plane is found by its geometry identifier", found_again);
  test.check("planes at z = 0, 50, ..., 350 mm along ACTS x", placed);
  test.check("loc0 is ACTS y, loc1 is ACTS z", local_axes);
  const Acts::Surface& first_plane = *telescope.planes.front();
  test.check("149.9 mm is inside the active area", first_plane.insideBounds(Acts::Vector2(149.9, -149.9)));
  test.check("150.1 mm is outside the active area", !first_plane.insideBounds(Acts::Vector2(150.1, 0.0)));
  test.check("the world holds the vertex region", telescope.tracking_geometry->lowestTrackingVolume(context, Acts::Vector3(-100.2, 0.05, 31.0)) != nullptr);
}

// A track in a uniform field along fixture v (ACTS z), from the Lorentz force. dp/dt = q v x B with |p| constant gives, for the
// unit tangent T and path s, dT/ds = (q/p) k B (T x z), with k the unit conversion of t04-values-v4.md section 4,
// 0.299792458 GeV/(T m). So T_z is constant, and the azimuth falls at the rate w = (q/p) k B: phi(s) = phi_0 - w s. With
// S = sqrt(T_x^2 + T_y^2), integrating T gives x(s) - x_0 = (S / w) (sin phi_0 - sin phi(s)),
// y(s) - y_0 = (S / w) (cos phi(s) - cos phi_0), z(s) - z_0 = s T_z. A plane fixes x, so sin phi, then s, y and z.
// v advances with path, and opposite charges reach a plane by different paths, so a field along v does not leave v alone.
constexpr double gev_per_tesla_mm = 0.299792458e-3;

// Fixed before the first run of this check, from the propagator's accuracy, with one disclosure: the 6.09e-6 mm of job 7489042's
// fixture TRUTH lines had been read by then, so judge this limit by the budget below, not as blind. Budget, for the two tracks below (slopes up to 0.15,
// p down to 1.5 GeV, so curvature c = k B / p = 2e-4 per mm).
// - Stop at a plane: within s_onSurfaceTolerance, 1e-4 mm (Definitions/Tolerance.hpp), of the plane along the track. That moves a
//   crossing along the track only, by at most 1e-4 mm times the largest tangent 0.24 (slope 0.15, bending 450 mm x c): 2.4e-5 mm.
// - Integration: EigenStepper accepts a step while its estimate is below 4 x stepTolerance = 4e-4 mm (EigenStepper.ipp,
//   isErrorTolerable), a cap, not the error. The next surface sets the step length: at most 110 mm from vertex to plane 1, then
//   at most 52 mm between planes. A fourth-order step in a uniform field errs by about h^5 c^4 in position, taken with the
//   constant 1, which overstates it: 2.6e-5 mm for the first leg and 6.1e-7 mm for each of seven others, 3.1e-5 mm in all.
// - Direction error of the first step, (h c)^5 = 5e-9, carried over the 450 mm: 2.3e-6 mm.
// Sum 5.7e-5 mm, so 1e-4 mm, a two-hundredth of the 0.020 mm hit sigma. Beyond it is a finding, not a reason to widen it.
constexpr double helix_tolerance_mm = 1e-4;
// T_z changes only through the stepper's renormalization of T, by at most (h c)^5 = 5e-9 per step on a T_z of at most 0.15. Nine
// legs: 7e-9. So 1e-8 of p. |p| itself is not read here: a crossing holds the direction, and with no material q/p does not change.
constexpr double momentum_along_v_tolerance = 1e-8;

struct HelixCrossing {
  double u_mm = 0.0;
  double v_mm = 0.0;
};

HelixCrossing helix_crossing(const Acts::Vector3& start_mm, const Acts::Vector3& direction, double q_over_p_per_gev, double field_along_v_tesla,
                             double plane_x_mm) {
  const Acts::Vector3 tangent = direction.normalized();
  const double transverse = std::hypot(tangent.x(), tangent.y());
  const double phi_start = std::atan2(tangent.y(), tangent.x());
  const double turn_rate = q_over_p_per_gev * gev_per_tesla_mm * field_along_v_tesla;
  const double phi_end = std::asin(std::sin(phi_start) - turn_rate * (plane_x_mm - start_mm.x()) / transverse);
  const double path = (phi_start - phi_end) / turn_rate;
  HelixCrossing crossing;
  crossing.u_mm = start_mm.y() + transverse / turn_rate * (std::cos(phi_end) - std::cos(phi_start));
  crossing.v_mm = start_mm.z() + path * tangent.z();
  return crossing;
}

std::string short_number(double value) {
  std::ostringstream text;
  text << std::setprecision(3) << value;
  return text.str();
}

struct HelixTestTrack {
  Acts::Vector3 start_mm;
  Acts::Vector3 direction;
  double momentum_gev;
};

void check_helix(SelfTest& test, const t07::TelescopeGeometry& telescope) {
  const std::vector<HelixTestTrack> tracks{{Acts::Vector3(-100.0, 1.0, 2.0), Acts::Vector3(1.0, 0.1, -0.05), 3.0},
                                           {Acts::Vector3(-100.2, 0.05, 30.0), Acts::Vector3(1.0, 0.15, 0.15), 1.5}};
  const t07::PlanePropagation in_field(telescope, t07::field_tesla);
  bool every_plane = true;
  double worst_u_mm = 0.0;
  double worst_v_mm = 0.0;
  double worst_momentum_along_v = 0.0;
  double smallest_reversed_field_miss_mm = 1e9;
  for (const HelixTestTrack& track : tracks) {
    const double tangent_along_v = track.direction.normalized().z();
    for (const double charge : {1.0, -1.0}) {
      const double q_over_p = charge / track.momentum_gev;
      const std::vector<t07::PlaneCrossing> crossings = in_field.crossings(track.start_mm, track.direction, q_over_p);
      every_plane = every_plane && int(crossings.size()) == t07::plane_count;
      double reversed_field_miss_mm = 0.0;
      for (std::size_t index = 0; index < crossings.size(); ++index) {
        const t07::PlaneCrossing& crossing = crossings[index];
        every_plane = every_plane && crossing.plane == int(index) + 1;
        const double plane_x_mm = double(index) * t07::plane_spacing_mm;
        const HelixCrossing expected = helix_crossing(track.start_mm, track.direction, q_over_p, t07::field_tesla, plane_x_mm);
        const HelixCrossing reversed = helix_crossing(track.start_mm, track.direction, q_over_p, -t07::field_tesla, plane_x_mm);
        worst_u_mm = std::max(worst_u_mm, std::abs(crossing.loc0_mm - expected.u_mm));
        worst_v_mm = std::max(worst_v_mm, std::abs(crossing.loc1_mm - expected.v_mm));
        worst_momentum_along_v = std::max(worst_momentum_along_v, std::abs(std::cos(crossing.theta) - tangent_along_v));
        reversed_field_miss_mm = std::max(reversed_field_miss_mm, std::abs(crossing.loc0_mm - reversed.u_mm));
      }
      smallest_reversed_field_miss_mm = std::min(smallest_reversed_field_miss_mm, reversed_field_miss_mm);
    }
  }
  test.check("both charges cross eight planes in order", every_plane);
  test.check("every crossing is on the helix: worst u " + short_number(worst_u_mm) + " mm, worst v " + short_number(worst_v_mm) + " mm, tolerance " +
                 short_number(helix_tolerance_mm) + " mm",
             every_plane && worst_u_mm < helix_tolerance_mm && worst_v_mm < helix_tolerance_mm);
  test.check("the momentum along v is conserved: worst change " + short_number(worst_momentum_along_v) + " of p, tolerance " +
                 short_number(momentum_along_v_tolerance) + " of p",
             every_plane && worst_momentum_along_v < momentum_along_v_tolerance);
  test.check("the comparison sees a reversed field: smallest miss " + short_number(smallest_reversed_field_miss_mm) + " mm",
             smallest_reversed_field_miss_mm > 100.0 * helix_tolerance_mm);

  const HelixTestTrack& first = tracks.front();
  const auto positive = in_field.crossings(first.start_mm, first.direction, 1.0 / first.momentum_gev);
  const auto negative = in_field.crossings(first.start_mm, first.direction, -1.0 / first.momentum_gev);
  const double last_plane_x_mm = (t07::plane_count - 1) * t07::plane_spacing_mm;
  const double helix_v_split_mm = helix_crossing(first.start_mm, first.direction, 1.0 / first.momentum_gev, t07::field_tesla, last_plane_x_mm).v_mm -
                                  helix_crossing(first.start_mm, first.direction, -1.0 / first.momentum_gev, t07::field_tesla, last_plane_x_mm).v_mm;
  const bool both_complete = int(positive.size()) == t07::plane_count && int(negative.size()) == t07::plane_count;
  test.check("charges bend apart in u", both_complete && positive.back().loc0_mm < negative.back().loc0_mm);
  const double measured_v_split_mm = both_complete ? positive.back().loc1_mm - negative.back().loc1_mm : 0.0;
  test.check("opposite charges split in v by path: measured " + short_number(measured_v_split_mm) + " mm, helix " + short_number(helix_v_split_mm) + " mm",
             both_complete && std::abs(measured_v_split_mm - helix_v_split_mm) < 2.0 * helix_tolerance_mm);
}

void check_propagation(SelfTest& test, const t07::TelescopeGeometry& telescope) {
  const Acts::Vector3 start(-100.0, 1.0, 2.0);
  const Acts::Vector3 direction = Acts::Vector3(1.0, 0.1, -0.05).normalized();
  const t07::PlanePropagation no_field(telescope, 0.0);
  const std::vector<t07::PlaneCrossing> line = no_field.crossings(start, direction, 1.0 / 3.0);
  test.check("a zero-field track crosses eight planes", int(line.size()) == t07::plane_count);
  bool straight = int(line.size()) == t07::plane_count;
  for (std::size_t index = 0; straight && index < line.size(); ++index) {
    const double distance = 100.0 + double(index) * t07::plane_spacing_mm;
    straight = line[index].plane == int(index) + 1 && std::abs(line[index].loc0_mm - (1.0 + 0.1 * distance)) < 1e-6 &&
               std::abs(line[index].loc1_mm - (2.0 - 0.05 * distance)) < 1e-6;
  }
  test.check("that track is the closed-form line", straight);

  check_helix(test, telescope);
}

void check_data_file(SelfTest& test, const std::string& work_dir) {
  const std::string path = work_dir + "/self-test.t07data";
  t07::DataFileHeader header;
  header.event_count = 1;
  header.sigma_loc0_mm = t07::hit_sigma_mm;
  header.sigma_loc1_mm = t07::hit_sigma_mm;
  t07::DataEvent written;
  written.hits = {{0, 1, 0.125, -7.5}, {1, 8, 1e-3, 149.0}};
  t07::DataFileWriter writer(path, header);
  writer.write(written);
  writer.close();
  t07::DataFileReader reader(path);
  t07::DataEvent read_back;
  const bool one_event = reader.next(read_back);
  bool same = one_event && read_back.hits.size() == 2;
  for (std::size_t index = 0; same && index < 2; ++index) {
    same = read_back.hits[index].plane == written.hits[index].plane && read_back.hits[index].loc0_mm == written.hits[index].loc0_mm &&
           read_back.hits[index].loc1_mm == written.hits[index].loc1_mm;
  }
  test.check("a data file reads back what was written", same && !reader.next(read_back));
  // An honest data file under the truth suffix: only the path check can refuse it, so this line fails if that check goes.
  const std::string text = t07::read_whole_file(path);
  const std::string truth_named = work_dir + "/honest-copy" + t07::truth_file_suffix;
  t07::write_whole_file(truth_named, text);
  test.check_refused("a truth path is refused before opening", [&] { t07::DataFileReader truth(truth_named); });
  const std::string truncated = work_dir + "/truncated.t07data";
  t07::write_whole_file(truncated, text.substr(0, t07::data_header_bytes + 4 + 10));
  test.check_refused("a truncated data file is refused", [&] {
    t07::DataFileReader short_file(truncated);
    t07::DataEvent event;
    short_file.next(event);
  });
}

t07::ProductDocument sample_document() {
  t07::ProductDocument document;
  t07::ProductHeader& header = document.header;
  header.product_id = "self-test.product";
  header.recipe = "reco.track.acts-kf-refit/1";
  header.stage = "refit-known-hit-set";
  header.evidence_class = "truth-assisted";
  header.data_product = "t07-measurements-0";
  header.data_sha256 = std::string(64, 'a');
  header.hit_sets_sha256 = std::string(64, 'b');
  header.field_tesla = 0.0;
  header.qop_status = "assumed-not-measured";
  header.material_model = "none";
  header.start_prior = {-50.0, 10.0, 0.1, 0.1, 1.0};
  header.acts_version = "48.2.0";
  t07::TrackRecord track;
  track.key = "track-0";
  track.status = "fitted";
  track.failure_category = "none";
  track.measurements = 1;
  track.chi2 = 1.0 / 3.0;
  track.measured_coordinates = 2;
  track.assumed_q_over_p = -1e-300;
  document.tracks.push_back(track);
  t07::TrackRecord failed = track;
  failed.key = "track-1";
  failed.status = "failed";
  failed.failure_category = "fit";
  document.tracks.push_back(failed);
  t07::StateRecord state;
  state.track_key = "track-0";
  state.plane = 1;
  state.kind = "measurement";
  state.hit_key = 4;
  state.loc0_mm = 0.1;
  state.covariance = {4e-4, 0.0, 4e-4};
  document.states.push_back(state);
  t07::ParameterRecord parameters;
  parameters.track_key = "track-0";
  parameters.state_type = "smoothed";
  parameters.parameters = {0.1, -0.2, 1e-17, 1.5707963267948966, 0.33333333333333331, 0.0};
  parameters.covariance[0] = 2.2250738585072014e-308;
  document.parameters.push_back(parameters);
  return document;
}

void check_lost_hits(SelfTest& test) {
  test.check("a fit with every hit keeps the track", !t07::fit_lost_a_hit(8, 0, 8) && !t07::fit_lost_a_hit(7, 1, 8));
  test.check("a fit that lost a hit fails the track", t07::fit_lost_a_hit(7, 0, 8));
}

void check_product(SelfTest& test) {
  const t07::ProductDocument document = sample_document();
  const std::string text = t07::encode_product(document);
  const t07::ProductDocument decoded = t07::decode_product(text);
  test.check("a product reads back to the same bytes", t07::encode_product(decoded) == text);
  test.check("a double survives exactly", decoded.parameters.at(0).parameters[4] == 0.33333333333333331 && decoded.tracks.at(0).assumed_q_over_p == -1e-300);
  const std::size_t last_record = text.rfind("end ");
  test.check_refused("a product without its end record is refused", [&] { t07::decode_product(text.substr(0, last_record)); });
  test.check_refused("an unknown record is refused", [&] { t07::decode_product(text.substr(0, last_record) + "seed x\n" + text.substr(last_record)); });
  test.check_refused("a wrong count is refused", [&] { t07::decode_product(text.substr(0, last_record) + "end 9 9 9\n"); });
  test.check_refused("another format is refused", [&] { t07::decode_product("acts-tracking-product/3\n" + text.substr(text.find('\n') + 1)); });
  test.check_refused("a /1 product under the /2 name is refused", [&] { t07::decode_product("acts-tracking-product/2\n" + text.substr(text.find('\n') + 1)); });
  std::string not_finite = text;
  not_finite.replace(not_finite.find("0.33333333333333331"), 19, "nan");
  test.check_refused("a number that is not finite is refused", [&] { t07::decode_product(not_finite); });
  std::string smoothed_lost = text;
  smoothed_lost.replace(smoothed_lost.find(" smoothed "), 10, " unknown ");
  test.check_refused("an unknown state type is refused", [&] { t07::decode_product(smoothed_lost); });
}

// acts-tracking-product/2: the sample with its R33 records, one per kind the measurement state needs.
t07::ProductDocument sample_r33_document() {
  t07::ProductDocument document = sample_document();
  document.format_version = 2;
  document.header.r33_conventions = t07::r33_conventions_name;
  document.header.alignment_parametrization = t07::alignment_parametrization_name;
  document.header.alignment_frame = t07::alignment_frame_name;
  document.header.alignment_level = t07::alignment_level_name;
  document.track_outputs.push_back({"track-0", 1, 0.33333333333333331, 1.0, 0, "collision", "none", "off"});
  for (const char* type : {"predicted", "filtered", "smoothed", "unbiased"}) {
    document.residuals.push_back({"track-0", 0, type, {0.25, -1e-300}, {4e-4, 1e-7, 3e-4}});
  }
  t07::MeasurementOutputRecord output;
  output.track_key = "track-0";
  output.geometry_id = 72057594037927936ull;  // 2^56, the shape of a volume identifier
  output.projector = {0, 1};
  output.local_slope = {0.15, -0.1};
  output.incidence_rad = 0.17;
  output.path_factor = 1.016;
  for (std::size_t index = 0; index < output.alignment_derivative.size(); ++index) {
    output.alignment_derivative[index] = 0.1 * double(index) - 0.55;
    output.reference_derivative[index] = index == 0 || index == 7 ? -1.0 : 0.0;
  }
  document.measurement_outputs.push_back(output);
  document.residual_covariances.push_back({"track-0", 1, {2e-4, 1e-7, 1.5e-4}});
  return document;
}

void check_r33_product(SelfTest& test) {
  const std::string text = t07::encode_product(sample_r33_document());
  const t07::ProductDocument decoded = t07::decode_product(text);
  test.check("a /2 product reads back to the same bytes", decoded.format_version == 2 && t07::encode_product(decoded) == text);
  test.check("a /2 product starts with its name", text.rfind("acts-tracking-product/2\n", 0) == 0);
  // Every line of /1 but its name and its end, in order, is a line of /2: drop /2's name, its two header lines, its R33 records and its end.
  auto lines_of = [](const std::string& whole) {
    std::vector<std::string> lines;
    std::istringstream stream(whole);
    for (std::string line; std::getline(stream, line);) {
      lines.push_back(line);
    }
    return lines;
  };
  std::vector<std::string> version_one = lines_of(t07::encode_product(sample_document()));
  version_one = std::vector<std::string>(version_one.begin() + 1, version_one.end() - 1);
  std::vector<std::string> kept;
  for (const std::string& line : lines_of(text)) {
    bool r33 = false;
    for (const char* start : {"acts-tracking-product/", "r33_conventions ", "alignment_parametrization ", "track_output ", "residual ", "measurement_output ",
                              "residual_covariance ", "end "}) {
      r33 = r33 || line.rfind(start, 0) == 0;
    }
    if (!r33) {
      kept.push_back(line);
    }
  }
  test.check("every /1 record line of a /2 product is /1's, in order", kept == version_one && !kept.empty());
  auto without = [&](const std::string& start) {
    std::string cut = text;
    const std::size_t from = cut.find(start);
    cut.erase(from, cut.find('\n', from) + 1 - from);
    return cut;
  };
  test.check_refused("a measurement without its unbiased residual is refused", [&] { t07::decode_product(without("residual track-0 0 unbiased")); });
  test.check_refused("a measurement without its measurement output is refused", [&] { t07::decode_product(without("measurement_output ")); });
  test.check_refused("a fitted track without its track output is refused", [&] { t07::decode_product(without("track_output ")); });
  test.check_refused("a fitted track without its residual covariance is refused", [&] { t07::decode_product(without("residual_covariance ")); });
  test.check_refused("a product without its alignment parametrization is refused", [&] { t07::decode_product(without("alignment_parametrization ")); });
  std::string short_covariance = text;
  short_covariance.replace(short_covariance.find("residual_covariance track-0 1 "), 30, "residual_covariance track-0 2 ");
  test.check_refused("a residual covariance of the wrong size is refused", [&] { t07::decode_product(short_covariance); });
  std::string mixed = text;
  mixed.replace(mixed.find("residual track-0 0 unbiased"), 27, "residual track-0 0 smoothed");
  test.check_refused("a residual type twice is refused", [&] { t07::decode_product(mixed); });
  std::string wrong_charge = text;
  wrong_charge.replace(wrong_charge.find("track_output track-0 1 "), 23, "track_output track-0 -1 ");
  test.check_refused("a charge against the sign of q/p is refused", [&] { t07::decode_product(wrong_charge); });
  std::string wrong_field = text;
  wrong_field.replace(wrong_field.find("collision none off"), 18, "collision none on");
  test.check_refused("a field other than the header's is refused", [&] { t07::decode_product(wrong_field); });
  test.check_refused("R33 records in a /1 product are refused", [&] { t07::decode_product("acts-tracking-product/1\n" + text.substr(text.find('\n') + 1)); });
  t07::ProductDocument r33_as_version_one = sample_r33_document();
  r33_as_version_one.format_version = 1;
  test.check_refused("a /1 document holding R33 records is not written", [&] { t07::encode_product(r33_as_version_one); });
}

int self_test(const std::map<std::string, std::string>& flags) {
  require_only(flags, {"work-dir"});
  const std::string work_dir = required(flags, "work-dir");
  SelfTest test;
  check_version_and_hash(test);
  const t07::TelescopeGeometry telescope = t07::build_telescope_geometry();
  check_geometry(test, telescope);
  check_propagation(test, telescope);
  check_data_file(test, work_dir);
  check_lost_hits(test);
  check_product(test);
  check_r33_product(test);
  return test.finish();
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const std::string command = argc > 1 ? argv[1] : "";
    const auto flags = parse_flags(argc, argv, 2);
    if (command == "self-test") {
      return self_test(flags);
    }
    if (command == "refit") {
      return refit(flags);
    }
    if (command == "rewrite-product") {
      return rewrite_product(flags);
    }
    throw std::invalid_argument("the command is self-test, refit or rewrite-product");
  } catch (const std::invalid_argument& error) {
    std::cerr << "invalid input: " << error.what() << "\n";
    return 2;
  } catch (const std::exception& error) {
    std::cerr << "failed: " << error.what() << "\n";
    return 3;
  }
}
