// Section 7's truth-seeded run, the entry only: the steps after the start are TrackFinder::search_resolve_fit of track_finding.cpp, the finder's own code
// path, so the CKF settings, the ambiguity resolution with ambiguity_most_shared_hits and the fit are the recipe's by construction, not by copy. Scoring
// side: CMakeLists.txt compiles this file into acts_truth_seeded_run only, so the finder's binary has no find_from_starts (the build job reads its symbols).
// A start here is given on a plane; it is not made from the event's hits, so the finder's skip rule for seeds does not apply and every start runs.
#include <stdexcept>
#include <string>

#include "track_finding.hpp"

namespace t07 {

EventFinding TrackFinder::find_from_starts(const DataEvent& event, std::uint32_t event_ordinal, const std::vector<PlaneStart>& starts) const {
  return find_from_starts(event, event_ordinal, starts, {}, false);
}

EventFinding TrackFinder::find_from_starts(const DataEvent& event, std::uint32_t event_ordinal, const std::vector<PlaneStart>& starts, const std::set<std::uint32_t>& traced_labels,
                                           bool trace_ambiguity) const {
  std::set<std::size_t> traced_searches;
  for (std::size_t index = 0; index < starts.size(); ++index) {
    if (traced_labels.count(starts[index].label) != 0) {
      traced_searches.insert(index);
    }
  }
  EventFinding finding;
  finding.event_ordinal = event_ordinal;
  finding.hit_count = event.hits.size();
  finding.seeds_found = starts.size();
  finding.seeds.reserve(starts.size());
  const Acts::ParticleHypothesis particle = hypothesis();
  std::size_t next = 0;
  const StartSource next_start = [&](const std::vector<std::vector<std::size_t>>& /*candidates_of_hit*/) -> std::optional<StartStep> {
    if (next == starts.size()) {
      return std::nullopt;
    }
    const PlaneStart& start = starts[next++];
    if (start.plane < 1 || start.plane > int(m_telescope.planes.size())) {
      throw std::invalid_argument("refused: a start on plane " + std::to_string(start.plane));
    }
    StartStep step;  // no seed hits: its triple stays empty, and the record names the start by its label
    step.parameters.emplace(m_telescope.planes.at(start.plane - 1), start.parameters, start.covariance, particle);
    return step;
  };
  search_resolve_fit(event, finding, next_start, trace_ambiguity, traced_searches);
  return finding;
}

}  // namespace t07
