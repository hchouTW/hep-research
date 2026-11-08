// The T07 finder: pattern recognition through ACTS on a data file, recipe reco.track.acts-ckf-planar/1 (t04-values-v4.md section 8.1).
//
//   acts_tracking_finder --data-file D --product-id NAME --product-file P --record-file R --product-events K [--seed-file S]
//                        [--ambiguity-trace-file T --ambiguity-trace-events E1,E2,...] [--vertex-recipe reco.vertex.acts-amvf/1]
//
// It takes hits and nothing else: a truth path or a truth file is refused, and there is no way in for a hit set or a start state. Section 7's comparator that
// starts from truth is another program, on the scoring side, and this one does not compile its entry (CMakeLists.txt; tests/adapters/test_acts_finding.py,
// FinderStaysTruthFree, keeps its names out of this file). Output:
// - the record, acts-tracking-finding-record/1: every event and every candidate of at least 6 hits, with its seed planes, its outcome, its failure
//   category and whether its search was truncated. acts_finding_record.py reads it. A limit reached is marked, never silent (BP03).
// - with --seed-file, acts-tracking-finding-seeds/1: every seed of every event, its three hits and what became of it. An output only, and large at o3
//   (50 MB per 3,000 events), so optional.
// - with --ambiguity-trace-file, acts-tracking-ambiguity-trace/1: for the event ordinals named, ACTS's own VERBOSE lines from GreedyAmbiguityResolution::
//   resolve, each removal with its track, nMeas, nShared and chi2 (D1 stage 6 brief, Resolver removal order). An output only: the record is the same with
//   or without it, and the event ordinals are positions in the data file, not truth.
// - the product, acts-tracking-product/1, for the first K events: per-surface states of the selected tracks, predicted, filtered and smoothed
//   kept apart. K bounds the size of a text product: 250 MB per 18,000 tracks at job 7493368. The product holds the tracks delivered: a fit-failed
//   candidate stays in the record, with its category, and has no track here, so fit_summary's failed count reads 0 on a finder product.
// - with --vertex-recipe, the record is acts-tracking-finding-record/2: the same lines, plus recipe reco.vertex.acts-amvf/1 on the delivered tracks
//   (track_vertexing.hpp), its configuration and its hash in the header, and after each event's candidates one vertexing line, its vertices with their
//   position, covariance and fit quality, and per vertex its tracks with their weights. The vertex step reads the fits after they are made and changes no
//   track, so removing those lines leaves the /1 record of the same run byte for byte (acts_finding_record.finding_lines_of). Without it, /1 as before.
// All at section 4.1's field; the seed windows and the q/p prior are settled for it, so no other is offered.
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
#include <vector>

#include "kalman_refit.hpp"
#include "native_product.hpp"
#include "sha256.hpp"
#include "t07_data_file.hpp"
#include "t07_fixture_constants.hpp"
#include "telescope_geometry.hpp"
#include "track_finding.hpp"
#include "track_vertexing.hpp"

namespace {

constexpr char record_format[] = "acts-tracking-finding-record/1";
constexpr char vertex_record_format[] = "acts-tracking-finding-record/2";  // with the vertex step (D1 stage 7)
constexpr char seed_file_format[] = "acts-tracking-finding-seeds/1";
constexpr char trace_file_format[] = "acts-tracking-ambiguity-trace/1";
constexpr char finding_recipe[] = "reco.track.acts-ckf-planar/1";
constexpr char finding_stage[] = "find-ckf";
constexpr char finding_evidence_class[] = "data-side";

std::map<std::string, std::string> parse_flags(int argc, char** argv) {
  const std::set<std::string> known{"data-file", "product-id", "product-file", "record-file", "product-events"};
  const std::set<std::string> optional_outputs{"seed-file", "ambiguity-trace-file", "ambiguity-trace-events"};
  const std::set<std::string> optional_steps{"vertex-recipe"};
  std::map<std::string, std::string> flags;
  for (int index = 1; index < argc; index += 2) {
    const std::string flag = argv[index];
    if (flag.rfind("--", 0) != 0 || index + 1 >= argc ||
        (known.count(flag.substr(2)) == 0 && optional_outputs.count(flag.substr(2)) == 0 && optional_steps.count(flag.substr(2)) == 0)) {
      throw std::invalid_argument("expected a known --flag and its value, got " + flag);
    }
    flags[flag.substr(2)] = argv[index + 1];
  }
  for (const std::string& name : known) {
    if (flags.count(name) == 0) {
      throw std::invalid_argument("--" + name + " is required");
    }
  }
  if (flags.count("ambiguity-trace-file") != flags.count("ambiguity-trace-events")) {
    throw std::invalid_argument("--ambiguity-trace-file and --ambiguity-trace-events go together");
  }
  if (flags.count("vertex-recipe") != 0 && flags.at("vertex-recipe") != t07::vertex_recipe) {
    throw std::invalid_argument("--vertex-recipe names " + flags.at("vertex-recipe") + ", and only " + t07::vertex_recipe + " is built");
  }
  return flags;
}

std::uint32_t count_from_text(const std::string& text, const std::string& what = "--product-events") {
  std::size_t used = 0;
  unsigned long long value = 0;
  try {
    value = std::stoull(text, &used);
  } catch (const std::exception&) {
    throw std::invalid_argument(what + " is not a count: " + text);
  }
  if (used != text.size() || text.front() == '-' || value > 0xFFFFFFFFull) {
    throw std::invalid_argument(what + " is not a count: " + text);
  }
  return std::uint32_t(value);
}

std::set<std::uint32_t> ordinals_from_text(const std::string& text) {
  std::set<std::uint32_t> ordinals;
  std::istringstream stream(text);
  for (std::string item; std::getline(stream, item, ',');) {
    ordinals.insert(count_from_text(item, "--ambiguity-trace-events"));
  }
  if (ordinals.empty()) {
    throw std::invalid_argument("--ambiguity-trace-events names no event");
  }
  return ordinals;
}

void refuse_overwriting_input(const std::string& written, const std::string& input) {
  if (std::filesystem::weakly_canonical(written) == std::filesystem::weakly_canonical(input)) {
    throw std::invalid_argument("refused: an output would overwrite " + input);
  }
}

std::string acts_version_text() {
  std::ostringstream text;
  text << Acts::VersionInfo::fromLibrary().withoutCommit();
  return text.str();
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

std::string planes_text(const t07::SeedPlanes& planes) {
  return std::to_string(planes.first) + "-" + std::to_string(planes.middle) + "-" + std::to_string(planes.last);
}

std::string configuration_text() {
  std::string text;
  for (const auto& [name, value] : t07::effective_configuration()) {
    text += "configuration " + name + " " + value + "\n";
  }
  return text;
}

std::string vertex_configuration_text(const t07::TrackVertexer& vertexer) {
  std::string text;
  for (const auto& [name, value] : vertexer.configuration()) {
    text += "vertex_configuration " + name + " " + value + "\n";
  }
  return text;
}

// One event's vertex step: its line, then each vertex and its tracks. Keys: event-<ordinal>-vertex-<index>, in ACTS's order.
std::string vertex_lines(const t07::EventVertices& vertices, std::uint32_t event_ordinal) {
  std::ostringstream lines;
  lines << "vertexing " << event_ordinal << " " << vertices.status << " " << vertices.input_tracks << " " << vertices.unconverted_tracks << " " << vertices.vertices.size() << "\n";
  for (std::size_t index = 0; index < vertices.vertices.size(); ++index) {
    const t07::FoundVertex& vertex = vertices.vertices[index];
    const std::string key = "event-" + std::to_string(event_ordinal) + "-vertex-" + std::to_string(index);
    lines << "vertex " << key << " " << event_ordinal;
    for (const double value : vertex.position_mm) {
      lines << " " << number_text(value);
    }
    for (const double value : vertex.covariance) {
      lines << " " << number_text(value);
    }
    lines << " " << number_text(vertex.chi2) << " " << number_text(vertex.ndf) << " " << vertex.tracks.size() << "\n";
    for (const t07::VertexTrack& track : vertex.tracks) {
      lines << "vertex-track " << key << " " << track.track_key << " " << number_text(track.weight) << " " << number_text(track.chi2) << " " << number_text(track.compatibility) << "\n";
    }
  }
  return lines.str();
}

std::string event_line(const t07::EventFinding& finding) {
  std::size_t selected = 0;
  for (const t07::FoundCandidate& candidate : finding.candidates) {
    selected += candidate.outcome == "selected" ? 1 : 0;
  }
  std::ostringstream line;
  line << "event " << finding.event_ordinal << " " << finding.hit_count << " " << finding.seeds_found << " " << finding.seeds_run << " " << finding.seeds_skipped << " "
       << finding.seeds_failed << " " << finding.seeds_without_candidate << " " << finding.seeds_truncated << " " << (finding.seed_budget_reached ? 1 : 0) << " "
       << (finding.ambiguity_budget_reached ? 1 : 0) << " " << finding.candidates.size() << " " << selected << " " << finding.failure_category << "\n";
  return line.str();
}

std::string candidate_line(const t07::FoundCandidate& candidate, std::uint32_t event_ordinal) {
  std::string keys;
  for (const std::uint32_t hit_key : candidate.hit_keys) {
    keys += (keys.empty() ? "" : ",") + std::to_string(hit_key);
  }
  std::ostringstream line;
  line << "candidate " << candidate.key << " " << event_ordinal << " " << planes_text(candidate.seed_planes) << " " << candidate.outcome << " " << candidate.failure_category << " "
       << (candidate.search_truncated ? 1 : 0) << " " << candidate.measurements << " " << candidate.holes << " " << number_text(candidate.search_chi2) << " "
       << number_text(candidate.q_over_p) << " " << number_text(candidate.fit_chi2) << " " << candidate.fit_coordinates << " " << keys << "\n";
  return line.str();
}

std::string seed_lines(const t07::EventFinding& finding) {
  std::ostringstream lines;
  lines << "event " << finding.event_ordinal << " " << finding.seeds.size() << "\n";
  for (const t07::SeedRecord& seed : finding.seeds) {
    const auto& keys = seed.triple.hit_keys;
    lines << "seed " << planes_text(seed.triple.planes) << " " << keys[0] << "," << keys[1] << "," << keys[2] << " " << seed.outcome << " " << seed.first_candidate << " " << seed.candidates << " "
          << seed.short_branches << "\n";
  }
  return lines.str();
}

int run(int argc, char** argv) {
  const auto flags = parse_flags(argc, argv);
  const std::string data_path = flags.at("data-file");
  const std::string product_path = flags.at("product-file");
  const std::string record_path = flags.at("record-file");
  const std::uint32_t product_events = count_from_text(flags.at("product-events"));
  refuse_overwriting_input(product_path, data_path);
  refuse_overwriting_input(record_path, data_path);
  refuse_overwriting_input(record_path, product_path);
  const std::string seed_path = flags.count("seed-file") != 0 ? flags.at("seed-file") : "";
  if (!seed_path.empty()) {
    refuse_overwriting_input(seed_path, data_path);
    refuse_overwriting_input(seed_path, record_path);
    refuse_overwriting_input(seed_path, product_path);
  }
  const std::string trace_path = flags.count("ambiguity-trace-file") != 0 ? flags.at("ambiguity-trace-file") : "";
  const std::set<std::uint32_t> traced_events = trace_path.empty() ? std::set<std::uint32_t>{} : ordinals_from_text(flags.at("ambiguity-trace-events"));
  if (!trace_path.empty()) {
    for (const std::string& other : {data_path, record_path, product_path}) {
      refuse_overwriting_input(trace_path, other);
    }
    if (!seed_path.empty()) {
      refuse_overwriting_input(trace_path, seed_path);
    }
  }

  t07::DataFileReader reader(data_path);  // a truth path stops here, a truth file by its magic, before anything is written
  const std::string data_sha256 = t07::sha256_of_file(data_path);
  const t07::TelescopeGeometry telescope = t07::build_telescope_geometry();
  const t07::TrackFinder finder(telescope, t07::field_tesla, reader.header().sigma_loc0_mm, reader.header().sigma_loc1_mm);
  // The vertex step only when asked for by its recipe's name: without it the record stays /1, as every earlier job wrote it.
  std::unique_ptr<const t07::TrackVertexer> vertexer;
  if (flags.count("vertex-recipe") != 0) {
    vertexer = std::make_unique<const t07::TrackVertexer>(telescope, t07::field_tesla);
  }

  t07::ProductDocument document;
  t07::ProductHeader& header = document.header;
  header.product_id = flags.at("product-id");
  header.recipe = finding_recipe;
  header.stage = finding_stage;
  header.evidence_class = finding_evidence_class;
  header.data_product = "t07-measurements-" + data_sha256.substr(0, 16);
  header.data_sha256 = data_sha256;
  header.hit_sets_sha256 = "none";  // nothing but hits came in
  header.field_tesla = t07::field_tesla;
  header.qop_status = "measured";
  header.material_model = "none";
  header.start_prior = {t07::refit_start_x_mm, t07::refit_prior_loc_sigma_mm, t07::refit_prior_angle_sigma, t07::refit_prior_qop_sigma_per_gev, t07::refit_prior_time_sigma};
  header.acts_version = acts_version_text();

  const std::string configuration = configuration_text();
  std::ofstream record(record_path, std::ios::binary);
  if (!record) {
    throw std::runtime_error("cannot write " + record_path);
  }
  record << (vertexer ? vertex_record_format : record_format) << "\nrecipe " << finding_recipe << "\nstage " << finding_stage << "\nevidence_class " << finding_evidence_class << "\nproduct_id " << header.product_id
         << "\ndata_sha256 " << data_sha256 << "\nproduct_events " << product_events << "\nconfiguration_sha256 " << t07::hex_of(t07::sha256_of_text(configuration)) << "\n"
         << configuration;
  if (vertexer) {
    const std::string vertex_configuration = vertex_configuration_text(*vertexer);
    record << "vertex_recipe " << t07::vertex_recipe << "\nvertex_configuration_sha256 " << t07::hex_of(t07::sha256_of_text(vertex_configuration)) << "\n" << vertex_configuration;
  }
  std::ofstream seed_stream;
  if (!seed_path.empty()) {
    seed_stream.open(seed_path, std::ios::binary);
    if (!seed_stream) {
      throw std::runtime_error("cannot write " + seed_path);
    }
    seed_stream << seed_file_format << "\n";
  }
  std::ofstream trace_stream;
  if (!trace_path.empty()) {
    trace_stream.open(trace_path, std::ios::binary);
    if (!trace_stream) {
      throw std::runtime_error("cannot write " + trace_path);
    }
    trace_stream << trace_file_format << "\n";
  }
  std::size_t traced = 0;

  std::size_t events = 0;
  std::size_t candidates = 0;
  std::size_t selected = 0;
  std::size_t failed = 0;
  std::size_t truncated_events = 0;
  std::size_t vertices = 0;
  std::size_t vertexing_failed = 0;
  t07::DataEvent event;
  for (std::uint32_t ordinal = 0; reader.next(event); ++ordinal) {
    const bool trace_this = traced_events.count(ordinal) != 0;
    t07::EventFinding finding = finder.find(event, ordinal, trace_this);
    record << event_line(finding);
    if (trace_this) {
      std::size_t lines = 0;
      for (const char letter : finding.ambiguity_trace) {
        lines += letter == '\n' ? 1 : 0;
      }
      trace_stream << "event " << ordinal << " lines " << lines << "\n" << finding.ambiguity_trace;
      ++traced;
    }
    if (!seed_path.empty()) {
      seed_stream << seed_lines(finding);
    }
    for (const t07::FoundCandidate& candidate : finding.candidates) {
      record << candidate_line(candidate, ordinal);
      selected += candidate.outcome == "selected" ? 1 : 0;
      failed += candidate.outcome == "fit-failed" ? 1 : 0;
    }
    if (vertexer) {
      // After the fit, on the delivered tracks only; it reads them and changes none.
      const t07::EventVertices found = vertexer->vertex(finding.fits);
      record << vertex_lines(found, ordinal);
      if (found.status != "ok") {
        // Kept by the scoring side with the finder's stderr (D1 stage 7b): one line per failed event, with ACTS's own message.
        std::cerr << "vertexing event " << ordinal << " failed: " << found.failure << "\n";
      }
      vertices += found.vertices.size();
      vertexing_failed += found.status == "ok" ? 0 : 1;
    }
    ++events;
    candidates += finding.candidates.size();
    truncated_events += finding.search_truncated() ? 1 : 0;
    if (ordinal < product_events) {
      for (t07::RefitResult& fit : finding.fits) {
        document.tracks.push_back(fit.track);
        document.states.insert(document.states.end(), fit.states.begin(), fit.states.end());
        document.parameters.insert(document.parameters.end(), fit.parameters.begin(), fit.parameters.end());
      }
    }
  }
  record << "end " << events << " " << candidates;
  if (vertexer) {
    record << " " << vertices;
  }
  record << "\n";
  record.close();
  if (!record) {
    throw std::runtime_error("cannot finish " + record_path);
  }
  if (!trace_path.empty()) {
    if (traced != traced_events.size()) {
      throw std::invalid_argument("--ambiguity-trace-events names an event the data file does not hold");
    }
    trace_stream << "end " << traced << "\n";
    trace_stream.close();
    if (!trace_stream) {
      throw std::runtime_error("cannot finish " + trace_path);
    }
  }
  if (!seed_path.empty()) {
    seed_stream << "end " << events << "\n";
    seed_stream.close();
    if (!seed_stream) {
      throw std::runtime_error("cannot finish " + seed_path);
    }
  }
  t07::write_whole_file(product_path, t07::encode_product(document));
  std::cout << "{\"status\": \"ok\", \"events\": " << events << ", \"candidates\": " << candidates << ", \"tracks\": " << selected + failed << ", \"failed\": " << failed
            << ", \"search_truncated_events\": " << truncated_events;
  if (vertexer) {
    std::cout << ", \"vertex_recipe\": \"" << t07::vertex_recipe << "\", \"vertices\": " << vertices << ", \"vertexing_failed_events\": " << vertexing_failed;
  }
  std::cout << ", \"stage\": \"" << finding_stage << "\", \"evidence_class\": \"" << finding_evidence_class << "\"}\n";
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
