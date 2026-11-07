// The driver's own product format, acts-tracking-product/1 (t07-t09-task-sheets.md, Output; plan Section 8.3). The ACTS
// package has no persistence layer. A text format of one record per line, doubles with 17 significant digits, so a double
// survives a write and a read exactly. Predicted, filtered and smoothed states are separate records (BP03). Failed tracks
// stay in the product with their category. Objects are found by product identity and key, never by row. The reader stops
// at anything it does not know. acts_native_product.py is the same format in Python and maps it to reconstruction-product/1.
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace t07 {

inline constexpr char product_format[] = "acts-tracking-product/1";

struct ProductHeader {
  std::string product_id;
  std::uint32_t revision = 1;
  std::string recipe;
  std::string stage;           // refit-known-hit-set: never reported as finding (BP03; t04-values-v4.md section 8.1)
  std::string evidence_class;  // truth-assisted for a known hit set
  std::string data_product;
  std::string data_sha256;
  std::string hit_sets_sha256;
  double field_tesla = 0.0;
  std::string qop_status;      // assumed-not-measured at zero field, where the hits carry no q/p
  std::string material_model;  // none: section 4.1 (R33 keeps the model's identity)
  std::array<double, 5> start_prior{};  // start x in mm; sigma of loc, angle, q/p per GeV, time
  std::string acts_version;
};

struct TrackRecord {
  std::string key;
  std::uint32_t event_ordinal = 0;
  std::string status;            // fitted or failed
  std::string failure_category;  // none, or fit (t04-prereg.md, Failure classes)
  std::int32_t measurements = 0;
  std::int32_t holes = 0;
  std::int32_t outliers = 0;
  double chi2 = 0.0;
  std::int32_t measured_coordinates = 0;  // ACTS nDoF: the sum of measurement sizes, with no fitted parameter removed
  double assumed_q_over_p = 0.0;
};

struct StateRecord {
  std::string track_key;
  std::int32_t index = 0;   // position along the track
  std::int32_t plane = 0;   // 1..8
  std::string kind;         // measurement, hole or outlier
  std::int64_t hit_key = -1;  // -1 prints as none, on a hole
  double loc0_mm = 0.0;
  double loc1_mm = 0.0;
  std::array<double, 3> covariance{};  // 00, 01, 11 of the measurement, apart from any residual covariance (R33)
  double path_length_mm = 0.0;
  double chi2 = 0.0;
};

struct ParameterRecord {
  std::string track_key;
  std::int32_t state_index = 0;
  std::string state_type;           // predicted, filtered or smoothed
  std::array<double, 6> parameters{};  // loc0, loc1, phi, theta, q/p, time
  std::array<double, 21> covariance{};  // upper triangle, row by row
};

struct ProductDocument {
  ProductHeader header;
  std::vector<TrackRecord> tracks;
  std::vector<StateRecord> states;
  std::vector<ParameterRecord> parameters;
};

std::string encode_product(const ProductDocument& document);
ProductDocument decode_product(const std::string& text);  // throws std::runtime_error on anything not of this format
std::string read_whole_file(const std::string& path);
void write_whole_file(const std::string& path, const std::string& text);

}  // namespace t07
