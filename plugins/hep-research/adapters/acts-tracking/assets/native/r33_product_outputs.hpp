// R33's outputs for the tracks the finder and the truth-seeded run deliver (plan R33; D1 stage 8 review m1; D1 stage 9). Header only, so neither program's
// CMake target changes. Data side: it reads a finding and its event, and no generator, seed or truth code reaches this file.
//
// Where they live: in the program's product, acts-tracking-product/2, which already carries each delivered track's states for the first K events (the
// record carries candidate summaries of every event, and stays byte for byte as without R33's outputs). Asked for by --r33-outputs t07-r33/1; without the
// flag each program writes /1 as before, byte for byte.
//
// How: each delivered hit set is fitted again through KalmanRefit::fit(hit_set, event, RefitOutputs&), from the q/p the delivered fit itself assumed
// (TrackRecord::assumed_q_over_p, the start of the finder's last pass, track_finding.cpp), on a KalmanRefit with the finder's own geometry, field and
// sigmas. kalman_refit.hpp: "The fit itself is the one above, bit for bit: the outputs only read its states". So the same inputs reach the same code path,
// and this checks it: the /1 records of the fit again must equal the delivered fit's byte for byte, or the program stops. The outputs then belong to
// the delivered track and to nothing else.
#pragma once

#include <map>
#include <stdexcept>
#include <string>

#include "kalman_refit.hpp"
#include "native_product.hpp"
#include "t07_data_file.hpp"
#include "track_finding.hpp"
#include "track_fit_outputs.hpp"

namespace t07 {

inline bool r33_outputs_asked(const std::map<std::string, std::string>& flags) {
  const auto found = flags.find("r33-outputs");
  if (found == flags.end()) {
    return false;
  }
  if (found->second != r33_conventions_name) {
    throw std::invalid_argument("--r33-outputs names the R33 conventions, " + std::string(r33_conventions_name) + ", not " + found->second);
  }
  return true;
}

// The /2 header lines of track_fit_outputs.hpp's conventions.
inline void name_r33_conventions(ProductDocument& document) {
  document.format_version = 2;
  document.header.r33_conventions = r33_conventions_name;
  document.header.alignment_parametrization = alignment_parametrization_name;
  document.header.alignment_frame = alignment_frame_name;
  document.header.alignment_level = alignment_level_name;
}

// One track's /1 records, encoded under header: what "byte for byte" compares.
inline std::string version_one_records_of(const ProductHeader& header, const RefitResult& fit) {
  ProductDocument single;
  single.format_version = 1;
  single.header = header;
  single.header.r33_conventions.clear();
  single.header.alignment_parametrization.clear();
  single.header.alignment_frame.clear();
  single.header.alignment_level.clear();
  single.tracks.push_back(fit.track);
  single.states = fit.states;
  single.parameters = fit.parameters;
  return encode_product(single);
}

// Appends the R33 records of every delivered fit of this event to document, in the order of finding.fits.
inline void add_r33_outputs_of(const KalmanRefit& outputs_fitter, const EventFinding& finding, const DataEvent& event, ProductDocument& document) {
  std::map<std::string, const FoundCandidate*> selected;
  for (const FoundCandidate& candidate : finding.candidates) {
    if (candidate.outcome == "selected") {
      selected[candidate.key] = &candidate;
    }
  }
  for (const RefitResult& delivered : finding.fits) {
    const auto candidate = selected.find(delivered.track.key);
    if (candidate == selected.end()) {
      throw std::runtime_error("the delivered track " + delivered.track.key + " has no selected candidate");
    }
    HitSet hit_set;
    hit_set.track_key = delivered.track.key;
    hit_set.event_ordinal = delivered.track.event_ordinal;
    hit_set.assumed_q_over_p = delivered.track.assumed_q_over_p;
    hit_set.hit_keys = candidate->second->hit_keys;
    RefitOutputs outputs;
    const RefitResult again = outputs_fitter.fit(hit_set, event, outputs);
    if (version_one_records_of(document.header, again) != version_one_records_of(document.header, delivered)) {
      throw std::runtime_error("the fit with R33's outputs of " + delivered.track.key + " differs from the delivered fit: its outputs would belong to another track");
    }
    document.track_outputs.insert(document.track_outputs.end(), outputs.track_output.begin(), outputs.track_output.end());
    document.residuals.insert(document.residuals.end(), outputs.residuals.begin(), outputs.residuals.end());
    document.measurement_outputs.insert(document.measurement_outputs.end(), outputs.measurement_outputs.begin(), outputs.measurement_outputs.end());
    document.residual_covariances.insert(document.residual_covariances.end(), outputs.residual_covariance.begin(), outputs.residual_covariance.end());
  }
}

}  // namespace t07
