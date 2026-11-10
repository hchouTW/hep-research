// Section 7's truth-seeded run of recipe reco.track.acts-ckf-planar/1: a comparator on the scoring side, never reported as finding (t04-values-v4.md section 7,
// "Truth-seeded run"; t07-t09-task-sheets.md T07, Acceptance; decisions.md, "T07 stage 5": a separate scoring-side program, the finder stays truth-free).
//
//   acts_truth_seeded_run --data-file D --start-file S --product-id NAME --product-file P --record-file R --product-events K
//                         [--trace-file T --trace-starts E:P,E:P,...] [--reading-start-angle-sigma X] [--r33-outputs t07-r33/1]
//
// D1 stage 9 (stage 8 review m1): with --r33-outputs t07-r33/1 the product is acts-tracking-product/2, the same /1 records plus R33's outputs of each delivered
// track of the first K events (r33_product_outputs.hpp, the finder's own helper). An output only: the record is the same with or without it.
// D1 stage 6b, diagnostics, outputs only: --trace-file writes, for each named (event ordinal, particle) start, ACTS's own VERBOSE lines of the CKF and the
// navigator, every branch of that search with its states (on an ACTS error too, with the error), and this recipe's budget marks, and ACTS's ambiguity lines of those events. The record is the same
// with or without it. --reading-start-angle-sigma replaces section 7's 0.01 for phi and theta by X: NOT section 7, a reading only, never the default, for no
// gate. Its record and product say so in their stage (truth-seeded-ckf-reading-only) and variant line, and the scoring side refuses them as section 7's run.
//
// The CKF starts from the exact truth state of each particle at plane 1, with covariance diag(0.1 mm, 0.1 mm, 0.01, 0.01, 0.1 |q/p|) squared, and no seed finder
// (section 7). Everything after the start is the finder's own code path, TrackFinder::search_resolve_fit (track_finding.cpp), reached through
// find_from_starts (truth_seeded_search.cpp): the same CKF settings, ambiguity resolution and fit, by construction. Every particle in the start file is
// started, in its order. Section 4.1, Fiducial: every track crosses every plane, so every particle has a truth state at plane 1.
//
// Input: the data file, and the start file acts-tracking-truth-starts/1, which the scoring side writes from the truth file (tests/adapters/
// test_acts_truth_seeded.py): per particle its plane-1 loc0, loc1, phi, theta and q/p at 17 significant digits, which round-trip exactly. It names the data
// file by SHA-256, checked here. Output, each labelled truth-seeded: the record acts-tracking-truth-seeded-record/1, every line of it starting
// "truth-seeded", and the product acts-tracking-product/1 with stage truth-seeded-ckf and evidence class truth-assisted, so no reader of finding takes
// either (acts_finding_record.py refuses the record, fit_summary does not report the product as finding). Neither goes to the data side (A09).
#include <Acts/ActsVersion.hpp>

#include <cmath>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "kalman_refit.hpp"
#include "native_product.hpp"
#include "r33_product_outputs.hpp"
#include "sha256.hpp"
#include "t07_data_file.hpp"
#include "t07_fixture_constants.hpp"
#include "telescope_geometry.hpp"
#include "track_finding.hpp"

namespace {

constexpr char label[] = "truth-seeded";
// /2 since stage 6b: the header holds a variant line (stage 6b review m7). /1, job 7503215's, had none; the scoring side reads both.
constexpr char record_format[] = "acts-tracking-truth-seeded-record/2";
constexpr char start_file_format[] = "acts-tracking-truth-starts/1";
constexpr char recipe[] = "reco.track.acts-ckf-planar/1";  // the recipe whose steps after the start run here
constexpr char stage[] = "truth-seeded-ckf";
constexpr char reading_stage[] = "truth-seeded-ckf-reading-only";  // --reading-start-angle-sigma: not section 7
constexpr char trace_format[] = "acts-tracking-truth-seeded-trace/1";
constexpr char evidence_class[] = "truth-assisted";

// Section 7, "Truth-seeded run", word for word: plane 1, and the five sigmas. The time entry is the recipe's own start (refit_prior_time_sigma, as
// seed_start_of sets it): section 7 names five bound parameters, ACTS carries a sixth, and no field or material here makes time matter.
constexpr int truth_start_plane = 1;
constexpr double truth_start_sigma_loc0_mm = 0.1;
constexpr double truth_start_sigma_loc1_mm = 0.1;
constexpr double truth_start_sigma_phi = 0.01;
constexpr double truth_start_sigma_theta = 0.01;
constexpr double truth_start_sigma_qop_share = 0.1;  // of |q/p|

struct TruthStart {
  std::uint32_t particle = 0;
  double loc0_mm = 0.0, loc1_mm = 0.0, phi = 0.0, theta = 0.0, q_over_p = 0.0;
};

std::map<std::string, std::string> parse_flags(int argc, char** argv) {
  const std::set<std::string> known{"data-file", "start-file", "product-id", "product-file", "record-file", "product-events"};
  const std::set<std::string> optional{"trace-file", "trace-starts", "reading-start-angle-sigma", "r33-outputs"};
  std::map<std::string, std::string> flags;
  for (int index = 1; index < argc; index += 2) {
    const std::string flag = argv[index];
    if (flag.rfind("--", 0) != 0 || index + 1 >= argc || (known.count(flag.substr(2)) == 0 && optional.count(flag.substr(2)) == 0)) {
      throw std::invalid_argument("expected a known --flag and its value, got " + flag);
    }
    flags[flag.substr(2)] = argv[index + 1];
  }
  for (const std::string& name : known) {
    if (flags.count(name) == 0) {
      throw std::invalid_argument("--" + name + " is required");
    }
  }
  if (flags.count("trace-file") != flags.count("trace-starts")) {
    throw std::invalid_argument("--trace-file and --trace-starts go together");
  }
  return flags;
}

std::uint32_t count_from_text(const std::string& text, const std::string& what) {
  std::size_t used = 0;
  unsigned long long value = 0;
  try {
    value = std::stoull(text, &used);
  } catch (const std::exception&) {
    throw std::invalid_argument(what + " is not a count: " + text);
  }
  if (used != text.size() || text.empty() || text.front() == '-' || value > 0xFFFFFFFFull) {
    throw std::invalid_argument(what + " is not a count: " + text);
  }
  return std::uint32_t(value);
}

double finite_from_text(const std::string& text) {
  std::size_t used = 0;
  double value = 0.0;
  try {
    value = std::stod(text, &used);
  } catch (const std::exception&) {
    throw std::invalid_argument("the start file holds a value that is not a number: " + text);
  }
  if (used != text.size() || !std::isfinite(value)) {
    throw std::invalid_argument("the start file holds a value that is not a finite number: " + text);
  }
  return value;
}

// --trace-starts: event ordinal and particle label pairs, E:P joined by commas.
std::map<std::uint32_t, std::set<std::uint32_t>> traced_starts_of(const std::string& text) {
  std::map<std::uint32_t, std::set<std::uint32_t>> traced;
  std::istringstream stream(text);
  for (std::string item; std::getline(stream, item, ',');) {
    const std::size_t colon = item.find(':');
    if (colon == std::string::npos) {
      throw std::invalid_argument("--trace-starts expects E:P items, got " + item);
    }
    traced[count_from_text(item.substr(0, colon), "a traced event")].insert(count_from_text(item.substr(colon + 1), "a traced particle"));
  }
  if (traced.empty()) {
    throw std::invalid_argument("--trace-starts names no start");
  }
  return traced;
}

std::string labelled_lines(const std::string& kind, const std::string& text) {
  std::string lines;
  std::istringstream stream(text);
  for (std::string line; std::getline(stream, line);) {
    lines += "truth-seeded " + kind + " " + line + "\n";
  }
  return lines;
}

std::size_t line_count(const std::string& text) {
  std::size_t lines = 0;
  std::istringstream stream(text);
  for (std::string line; std::getline(stream, line);) {
    ++lines;
  }
  return lines;
}

void refuse_overwriting_input(const std::string& written, const std::string& input) {
  if (std::filesystem::weakly_canonical(written) == std::filesystem::weakly_canonical(input)) {
    throw std::invalid_argument("refused: an output would overwrite " + input);
  }
}

std::string number_text(double value) {
  if (!std::isfinite(value)) {
    throw std::runtime_error("a record holds finite numbers only");
  }
  std::ostringstream text;
  text.precision(17);
  text << value;
  return text.str();
}

std::vector<std::string> tokens_of(const std::string& line) {
  std::istringstream stream(line);
  std::vector<std::string> tokens;
  for (std::string token; stream >> token;) {
    tokens.push_back(token);
  }
  return tokens;
}

// The start file, whole: events in the data file's order, each with its particles' plane-1 states. Anything else is refused before a search runs.
std::vector<std::vector<TruthStart>> read_start_file(const std::string& path, const std::string& data_sha256, std::uint32_t data_events) {
  std::ifstream input(path, std::ios::binary);
  if (!input) {
    throw std::invalid_argument("cannot read " + path);
  }
  std::string line;
  const auto expect = [&](const std::string& name) {
    if (!std::getline(input, line)) {
      throw std::invalid_argument(path + " ends before " + name);
    }
    const std::vector<std::string> tokens = tokens_of(line);
    if (tokens.size() != 2 || tokens[0] != name) {
      throw std::invalid_argument(path + ": expected " + name + ", found " + line);
    }
    return tokens[1];
  };
  if (!std::getline(input, line) || line != start_file_format) {
    throw std::invalid_argument(path + " is not " + start_file_format);
  }
  if (expect("role") != "truth") {
    throw std::invalid_argument(path + ": the start file has role truth");
  }
  if (expect("data_sha256") != data_sha256) {
    throw std::invalid_argument(path + " names another data file");
  }
  if (count_from_text(expect("events"), "events") != data_events) {
    throw std::invalid_argument(path + " holds another number of events than the data file");
  }
  std::vector<std::vector<TruthStart>> events(data_events);
  for (std::uint32_t ordinal = 0; ordinal < data_events; ++ordinal) {
    if (!std::getline(input, line)) {
      throw std::invalid_argument(path + " ends inside its events");
    }
    std::vector<std::string> tokens = tokens_of(line);
    if (tokens.size() != 3 || tokens[0] != "event" || count_from_text(tokens[1], "an event ordinal") != ordinal) {
      throw std::invalid_argument(path + ": expected event " + std::to_string(ordinal) + ", found " + line);
    }
    const std::uint32_t count = count_from_text(tokens[2], "a start count");
    for (std::uint32_t index = 0; index < count; ++index) {
      if (!std::getline(input, line)) {
        throw std::invalid_argument(path + " ends inside event " + std::to_string(ordinal));
      }
      tokens = tokens_of(line);
      if (tokens.size() != 7 || tokens[0] != "start") {
        throw std::invalid_argument(path + ": not a start: " + line);
      }
      TruthStart start{count_from_text(tokens[1], "a particle"), finite_from_text(tokens[2]), finite_from_text(tokens[3]), finite_from_text(tokens[4]), finite_from_text(tokens[5]),
                       finite_from_text(tokens[6])};
      if (start.q_over_p == 0.0) {
        throw std::invalid_argument(path + ": a start with q/p zero");
      }
      events[ordinal].push_back(start);
    }
  }
  if (!std::getline(input, line) || line != "end " + std::to_string(data_events) || std::getline(input, line)) {
    throw std::invalid_argument(path + " does not end at its end record");
  }
  return events;
}

std::vector<t07::PlaneStart> plane_starts_of(const std::vector<TruthStart>& starts, double sigma_angle) {
  std::vector<t07::PlaneStart> converted;
  for (const TruthStart& start : starts) {
    t07::PlaneStart plane_start;
    plane_start.label = start.particle;
    plane_start.plane = truth_start_plane;
    plane_start.parameters << start.loc0_mm, start.loc1_mm, start.phi, start.theta, start.q_over_p, 0.0;
    const double sigma_qop = truth_start_sigma_qop_share * std::abs(start.q_over_p);
    plane_start.covariance.diagonal() << truth_start_sigma_loc0_mm * truth_start_sigma_loc0_mm, truth_start_sigma_loc1_mm * truth_start_sigma_loc1_mm,
        sigma_angle * sigma_angle, sigma_angle * sigma_angle, sigma_qop * sigma_qop, t07::refit_prior_time_sigma * t07::refit_prior_time_sigma;
    converted.push_back(plane_start);
  }
  return converted;
}

// The recipe's configuration lines, unchanged, then what this run adds: the start. The first part's hash is the finder's configuration_sha256.
std::string recipe_configuration_text() {
  std::string text;
  for (const auto& [name, value] : t07::effective_configuration()) {
    text += "configuration " + name + " " + value + "\n";
  }
  return text;
}

std::string start_configuration_text(double sigma_phi, double sigma_theta) {
  return "configuration truth_start_plane " + std::to_string(truth_start_plane) + "\nconfiguration truth_start_sigma_loc0_mm " + number_text(truth_start_sigma_loc0_mm) +
         "\nconfiguration truth_start_sigma_loc1_mm " + number_text(truth_start_sigma_loc1_mm) + "\nconfiguration truth_start_sigma_phi " + number_text(sigma_phi) +
         "\nconfiguration truth_start_sigma_theta " + number_text(sigma_theta) + "\nconfiguration truth_start_sigma_qop_share " + number_text(truth_start_sigma_qop_share) +
         "\nconfiguration truth_start_sigma_time " + number_text(t07::refit_prior_time_sigma) + "\n";
}

std::string labelled(const std::string& text) {
  std::string lines;
  std::istringstream stream(text);
  for (std::string line; std::getline(stream, line);) {
    lines += std::string(label) + " " + line + "\n";
  }
  return lines;
}

std::string event_line(const t07::EventFinding& finding) {
  std::size_t selected = 0;
  for (const t07::FoundCandidate& candidate : finding.candidates) {
    selected += candidate.outcome == "selected" ? 1 : 0;
  }
  std::ostringstream line;
  line << label << " event " << finding.event_ordinal << " " << finding.hit_count << " " << finding.seeds_found << " " << finding.seeds_run << " " << finding.seeds_skipped << " "
       << finding.seeds_failed << " " << finding.seeds_without_candidate << " " << finding.seeds_truncated << " " << (finding.seed_budget_reached ? 1 : 0) << " "
       << (finding.ambiguity_budget_reached ? 1 : 0) << " " << finding.candidates.size() << " " << selected << " " << finding.failure_category << "\n";
  return line.str();
}

std::string start_line(const t07::SeedRecord& seed, std::uint32_t particle) {
  std::ostringstream line;
  line << label << " start " << particle << " " << seed.outcome << " " << seed.first_candidate << " " << seed.candidates << " " << seed.short_branches << "\n";
  return line.str();
}

std::string candidate_line(const t07::FoundCandidate& candidate, std::uint32_t event_ordinal, std::uint32_t particle) {
  std::string keys;
  for (const std::uint32_t hit_key : candidate.hit_keys) {
    keys += (keys.empty() ? "" : ",") + std::to_string(hit_key);
  }
  std::ostringstream line;
  line << label << " candidate " << candidate.key << " " << event_ordinal << " start-" << particle << " " << candidate.outcome << " " << candidate.failure_category << " "
       << (candidate.search_truncated ? 1 : 0) << " " << candidate.measurements << " " << candidate.holes << " " << number_text(candidate.search_chi2) << " "
       << number_text(candidate.q_over_p) << " " << number_text(candidate.fit_chi2) << " " << candidate.fit_coordinates << " " << keys << "\n";
  return line.str();
}

std::string acts_version_text() {
  std::ostringstream text;
  text << Acts::VersionInfo::fromLibrary().withoutCommit();
  return text.str();
}

int run(int argc, char** argv) {
  const auto flags = parse_flags(argc, argv);
  const std::string data_path = flags.at("data-file");
  const std::string start_path = flags.at("start-file");
  const std::string product_path = flags.at("product-file");
  const std::string record_path = flags.at("record-file");
  const std::uint32_t product_events = count_from_text(flags.at("product-events"), "--product-events");
  for (const std::string& written : {product_path, record_path}) {
    refuse_overwriting_input(written, data_path);
    refuse_overwriting_input(written, start_path);
  }
  refuse_overwriting_input(record_path, product_path);
  const bool reading = flags.count("reading-start-angle-sigma") != 0;
  const double sigma_phi = reading ? finite_from_text(flags.at("reading-start-angle-sigma")) : truth_start_sigma_phi;
  const double sigma_theta = reading ? sigma_phi : truth_start_sigma_theta;
  if (!(sigma_phi > 0.0)) {
    throw std::invalid_argument("--reading-start-angle-sigma is not a positive width");
  }
  const char* const run_stage = reading ? reading_stage : stage;
  const std::string trace_path = flags.count("trace-file") != 0 ? flags.at("trace-file") : "";
  const std::map<std::uint32_t, std::set<std::uint32_t>> traced = trace_path.empty() ? std::map<std::uint32_t, std::set<std::uint32_t>>{} : traced_starts_of(flags.at("trace-starts"));
  if (!trace_path.empty()) {
    for (const std::string& other : {data_path, start_path, product_path, record_path}) {
      refuse_overwriting_input(trace_path, other);
    }
  }

  t07::DataFileReader reader(data_path);
  const std::string data_sha256 = t07::sha256_of_file(data_path);
  const std::string start_sha256 = t07::sha256_of_file(start_path);
  const std::vector<std::vector<TruthStart>> starts = read_start_file(start_path, data_sha256, reader.header().event_count);
  const t07::TelescopeGeometry telescope = t07::build_telescope_geometry();
  const t07::TrackFinder finder(telescope, t07::field_tesla, reader.header().sigma_loc0_mm, reader.header().sigma_loc1_mm);
  const bool with_r33_outputs = t07::r33_outputs_asked(flags);
  std::unique_ptr<const t07::KalmanRefit> outputs_fitter;
  if (with_r33_outputs) {
    outputs_fitter = std::make_unique<const t07::KalmanRefit>(telescope, t07::field_tesla, reader.header().sigma_loc0_mm, reader.header().sigma_loc1_mm);
  }

  t07::ProductDocument document;
  t07::ProductHeader& header = document.header;
  header.product_id = flags.at("product-id");
  header.recipe = recipe;
  header.stage = run_stage;
  header.evidence_class = evidence_class;
  header.data_product = "t07-measurements-" + data_sha256.substr(0, 16);
  header.data_sha256 = data_sha256;
  header.hit_sets_sha256 = start_sha256;  // what came in besides the hits: the truth starts
  header.field_tesla = t07::field_tesla;
  header.qop_status = "measured";
  header.material_model = "none";
  header.start_prior = {t07::refit_start_x_mm, t07::refit_prior_loc_sigma_mm, t07::refit_prior_angle_sigma, t07::refit_prior_qop_sigma_per_gev, t07::refit_prior_time_sigma};
  header.acts_version = acts_version_text();
  if (with_r33_outputs) {
    t07::name_r33_conventions(document);
  }

  const std::string recipe_configuration = recipe_configuration_text();
  const std::string configuration = recipe_configuration + start_configuration_text(sigma_phi, sigma_theta);
  std::ofstream record(record_path, std::ios::binary);
  if (!record) {
    throw std::runtime_error("cannot write " + record_path);
  }
  record << record_format << "\n"
         << labelled("recipe " + std::string(recipe) + "\nstage " + run_stage + "\nevidence_class " + evidence_class + "\nvariant " +
                     (reading ? "not-section-7-reading-only" : "section-7") + "\nproduct_id " + header.product_id + "\ndata_sha256 " +
                     data_sha256 + "\nstart_sha256 " + start_sha256 + "\nproduct_events " + std::to_string(product_events) + "\nrecipe_configuration_sha256 " +
                     t07::hex_of(t07::sha256_of_text(recipe_configuration)) + "\nconfiguration_sha256 " + t07::hex_of(t07::sha256_of_text(configuration)) + "\n" + configuration);

  std::ofstream trace_stream;
  if (!trace_path.empty()) {
    trace_stream.open(trace_path, std::ios::binary);
    if (!trace_stream) {
      throw std::runtime_error("cannot write " + trace_path);
    }
    trace_stream << trace_format << "\n";
  }
  std::size_t traced_searches = 0;
  std::size_t asked_searches = 0;
  for (const auto& [ordinal, labels] : traced) {
    asked_searches += labels.size();
  }

  std::size_t events = 0;
  std::size_t candidates = 0;
  t07::DataEvent event;
  for (std::uint32_t ordinal = 0; reader.next(event); ++ordinal) {
    const std::vector<TruthStart>& event_starts = starts.at(ordinal);
    const auto traced_here = traced.find(ordinal);
    const std::set<std::uint32_t> traced_labels = traced_here == traced.end() ? std::set<std::uint32_t>{} : traced_here->second;
    t07::EventFinding finding = finder.find_from_starts(event, ordinal, plane_starts_of(event_starts, sigma_phi), traced_labels, !traced_labels.empty());
    for (const t07::SearchTrace& trace : finding.search_traces) {
      trace_stream << label << " event " << ordinal << " search " << trace.search << " start " << event_starts.at(trace.search).particle << " outcome "
                   << finding.seeds.at(trace.search).outcome << " result " << (trace.result == "ok" ? "ok" : "error") << " truncated " << (trace.truncated ? 1 : 0) << " step_limit " << (trace.step_limit ? 1 : 0) << " extra_branches "
                   << trace.extra_branches << " log_lines " << line_count(trace.acts_log) + (trace.result == "ok" ? 0 : 1) << " branch_lines " << line_count(trace.branches) << "\n"
                   << labelled_lines("log", trace.acts_log) << (trace.result == "ok" ? "" : labelled_lines("log", "error " + trace.result)) << labelled_lines("branch", trace.branches);
      ++traced_searches;
    }
    if (!traced_labels.empty()) {
      trace_stream << label << " ambiguity " << ordinal << " lines " << line_count(finding.ambiguity_trace) << "\n" << labelled_lines("log", finding.ambiguity_trace);
    }
    if (finding.seeds.size() != event_starts.size()) {
      throw std::runtime_error("event " + std::to_string(ordinal) + " ran " + std::to_string(finding.seeds.size()) + " of " + std::to_string(event_starts.size()) + " starts");
    }
    record << event_line(finding);
    std::vector<std::uint32_t> particle_of_candidate(finding.candidates.size());
    for (std::size_t index = 0; index < finding.seeds.size(); ++index) {
      const t07::SeedRecord& seed = finding.seeds[index];
      record << start_line(seed, event_starts[index].particle);
      for (std::size_t position = seed.first_candidate; position < seed.first_candidate + seed.candidates; ++position) {
        particle_of_candidate.at(position) = event_starts[index].particle;
      }
    }
    for (std::size_t position = 0; position < finding.candidates.size(); ++position) {
      record << candidate_line(finding.candidates[position], ordinal, particle_of_candidate[position]);
    }
    ++events;
    candidates += finding.candidates.size();
    if (ordinal < product_events) {
      for (t07::RefitResult& fit : finding.fits) {
        document.tracks.push_back(fit.track);
        document.states.insert(document.states.end(), fit.states.begin(), fit.states.end());
        document.parameters.insert(document.parameters.end(), fit.parameters.begin(), fit.parameters.end());
      }
      if (outputs_fitter) {
        t07::add_r33_outputs_of(*outputs_fitter, finding, event, document);
      }
    }
  }
  if (!trace_path.empty()) {
    if (traced_searches != asked_searches) {
      throw std::invalid_argument("--trace-starts names " + std::to_string(asked_searches) + " starts and " + std::to_string(traced_searches) + " were found");
    }
    trace_stream << label << " end " << traced_searches << "\n";
    trace_stream.close();
    if (!trace_stream) {
      throw std::runtime_error("cannot finish " + trace_path);
    }
  }
  record << label << " end " << events << " " << candidates << "\n";
  record.close();
  if (!record) {
    throw std::runtime_error("cannot finish " + record_path);
  }
  t07::write_whole_file(product_path, t07::encode_product(document));
  std::cout << "{\"status\": \"ok\", \"events\": " << events << ", \"candidates\": " << candidates << ", \"stage\": \"" << run_stage << "\", \"evidence_class\": \"" << evidence_class
            << "\", \"reported_as_finding\": false}\n";
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    return run(argc, argv);
  } catch (const std::invalid_argument& error) {
    std::cerr << "invalid input: " << error.what() << "\n";
    return 2;
  } catch (const std::exception& error) {
    std::cerr << "failed: " << error.what() << "\n";
    return 3;
  }
}
