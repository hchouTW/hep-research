// The T07 finder: pattern recognition through ACTS on a data file, recipe reco.track.acts-ckf-planar/1 (t04-values-v4.md section 8.1).
//
//   acts_tracking_finder --data-file D --product-id NAME --product-file P --record-file R --product-events K
//
// It takes hits and nothing else: a truth path or a truth file is refused, and there is no way in for a hit set or a start state. Output:
// - the record, acts-tracking-finding-record/1: every event and every candidate, with its seed planes, its outcome, its failure category
//   and whether its search was truncated. acts_finding_record.py reads it. A limit reached is marked, never silent (BP03).
// - the product, acts-tracking-product/1, for the first K events: per-surface states of the selected tracks, predicted, filtered and smoothed
//   kept apart. K bounds the size of a text product: 250 MB per 18,000 tracks at job 7493368.
// All at section 4.1's field; the seed windows and the q/p prior are settled for it, so no other is offered.
#include <Acts/ActsVersion.hpp>

#include <cmath>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
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

namespace {

constexpr char record_format[] = "acts-tracking-finding-record/1";
constexpr char finding_recipe[] = "reco.track.acts-ckf-planar/1";
constexpr char finding_stage[] = "find-ckf";
constexpr char finding_evidence_class[] = "data-side";

std::map<std::string, std::string> parse_flags(int argc, char** argv) {
  const std::set<std::string> known{"data-file", "product-id", "product-file", "record-file", "product-events"};
  std::map<std::string, std::string> flags;
  for (int index = 1; index < argc; index += 2) {
    const std::string flag = argv[index];
    if (flag.rfind("--", 0) != 0 || index + 1 >= argc || known.count(flag.substr(2)) == 0) {
      throw std::invalid_argument("expected a known --flag and its value, got " + flag);
    }
    flags[flag.substr(2)] = argv[index + 1];
  }
  for (const std::string& name : known) {
    if (flags.count(name) == 0) {
      throw std::invalid_argument("--" + name + " is required");
    }
  }
  return flags;
}

std::uint32_t count_from_text(const std::string& text) {
  std::size_t used = 0;
  unsigned long long value = 0;
  try {
    value = std::stoull(text, &used);
  } catch (const std::exception&) {
    throw std::invalid_argument("--product-events is not a count: " + text);
  }
  if (used != text.size() || text.front() == '-' || value > 0xFFFFFFFFull) {
    throw std::invalid_argument("--product-events is not a count: " + text);
  }
  return std::uint32_t(value);
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

int run(int argc, char** argv) {
  const auto flags = parse_flags(argc, argv);
  const std::string data_path = flags.at("data-file");
  const std::string product_path = flags.at("product-file");
  const std::string record_path = flags.at("record-file");
  const std::uint32_t product_events = count_from_text(flags.at("product-events"));
  refuse_overwriting_input(product_path, data_path);
  refuse_overwriting_input(record_path, data_path);
  refuse_overwriting_input(record_path, product_path);

  t07::DataFileReader reader(data_path);  // a truth path stops here, a truth file by its magic, before anything is written
  const std::string data_sha256 = t07::sha256_of_file(data_path);
  const t07::TelescopeGeometry telescope = t07::build_telescope_geometry();
  const t07::TrackFinder finder(telescope, t07::field_tesla, reader.header().sigma_loc0_mm, reader.header().sigma_loc1_mm);

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
  record << record_format << "\nrecipe " << finding_recipe << "\nstage " << finding_stage << "\nevidence_class " << finding_evidence_class << "\nproduct_id " << header.product_id
         << "\ndata_sha256 " << data_sha256 << "\nproduct_events " << product_events << "\nconfiguration_sha256 " << t07::hex_of(t07::sha256_of_text(configuration)) << "\n"
         << configuration;

  std::size_t events = 0;
  std::size_t candidates = 0;
  std::size_t selected = 0;
  std::size_t failed = 0;
  std::size_t truncated_events = 0;
  t07::DataEvent event;
  for (std::uint32_t ordinal = 0; reader.next(event); ++ordinal) {
    t07::EventFinding finding = finder.find(event, ordinal);
    record << event_line(finding);
    for (const t07::FoundCandidate& candidate : finding.candidates) {
      record << candidate_line(candidate, ordinal);
      selected += candidate.outcome == "selected" ? 1 : 0;
      failed += candidate.outcome == "fit-failed" ? 1 : 0;
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
  record << "end " << events << " " << candidates << "\n";
  record.close();
  if (!record) {
    throw std::runtime_error("cannot finish " + record_path);
  }
  t07::write_whole_file(product_path, t07::encode_product(document));
  std::cout << "{\"status\": \"ok\", \"events\": " << events << ", \"candidates\": " << candidates << ", \"tracks\": " << selected + failed << ", \"failed\": " << failed
            << ", \"search_truncated_events\": " << truncated_events << ", \"stage\": \"" << finding_stage << "\", \"evidence_class\": \"" << finding_evidence_class << "\"}\n";
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
