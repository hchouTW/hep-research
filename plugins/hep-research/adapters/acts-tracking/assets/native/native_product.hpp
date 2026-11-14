// The driver's own product format (t07-t09-task-sheets.md, Output; plan Section 8.3). The ACTS package has no persistence layer.
// A text format of one record per line, doubles with 17 significant digits, so a double survives a write and a read exactly.
// Predicted, filtered and smoothed states are separate records (BP03). Failed tracks stay in the product with their category.
// Objects are found by product identity and key, never by row. The reader stops at anything it does not know.
// acts_native_product.py is the same format in Python and maps it to reconstruction-product/1.
//
// Two versions, both read. acts-tracking-product/1 is the finder's, the truth-seeded run's and every product of earlier jobs.
// acts-tracking-product/2 is the refit's from D1 stage 8 on: /1's records unchanged, plus the R33 outputs of the track fit
// (track_fit_outputs.hpp states the conventions, t07-r33/1): two header lines (r33_conventions, alignment_parametrization), one
// track_output and one residual_covariance per fitted track, four residual records (predicted, filtered, smoothed, unbiased;
// never mixed, BP03) and one measurement_output per measured state (kind measurement or outlier). A document's version is
// stated, never guessed from its content, so a /1 document is written byte for byte as before.
// D1 stage 9: a /2 product of a refit that applied an alignment payload (CAI-T07-3; alignment_payload.hpp) holds one more header line,
// alignment_payload <content identity> <origin> <derived_against> <derived_from> <round>, right after alignment_parametrization, and only then: R32's
// "every reconstruction product records the identity and round of each payload it consumed". A product with no payload is byte for byte as before; the
// round is none, since t07-alignment-payload/1 comes from no loop (R36). The finder and the truth-seeded run write /2 too when asked for R33's outputs
// (r33_product_outputs.hpp), with the same records.
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace t07 {

inline constexpr char product_format[] = "acts-tracking-product/1";
inline constexpr char product_format_r33[] = "acts-tracking-product/2";

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
  std::string r33_conventions;  // version 2 only: t07-r33/1, the conventions of track_fit_outputs.hpp
  // Version 2 only: the R32 parametrization the alignment derivatives are in, its frame and its level: t07-plane-rigid/1 local sensor.
  std::string alignment_parametrization;
  std::string alignment_frame;
  std::string alignment_level;
  // Version 2 only, and only when a payload was applied (D1 stage 9): its content identity, origin, the geometry it binds to, its source and its round.
  std::string alignment_payload_sha256;  // empty: no payload, no line
  std::string alignment_payload_origin;
  std::string alignment_payload_derived_against;
  std::string alignment_payload_derived_from;
  std::string alignment_payload_round;
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

// R33, per fitted track (acts-tracking-product/2 only).
struct TrackOutputRecord {
  std::string track_key;
  std::int32_t charge = 0;           // +1 or -1: the sign of the fitted q/p, times the hypothesis's charge magnitude 1. At zero field
                                     // (qop_status assumed-not-measured) it is the sign of the assumed q/p, measured by nothing
  double q_over_p = 0.0;             // per GeV, the smoothed state at reference_state_index
  double q_over_p_variance = 0.0;    // per GeV^2, of that state
  std::int32_t reference_state_index = 0;  // the first measurement state along the track
  std::string topology;              // collision, cosmic or resonance-candidate (R33)
  std::string constraint;            // none, beam or vertex (R33): no fit here holds a constraint
  std::string field;                 // on or off, as field_tesla says
};

// R33, per measurement state and state type: r = x_meas - x_pred in the measurement's local frame (loc0, loc1) and its covariance.
struct ResidualRecord {
  std::string track_key;
  std::int32_t state_index = 0;
  std::string state_type;               // predicted, filtered, smoothed or unbiased
  std::array<double, 2> residual{};     // loc0, loc1, mm
  std::array<double, 3> covariance{};   // 00, 01, 11, mm^2
};

// R33, per measurement state: where it sits, how the track crosses it and the alignment derivatives, at the smoothed state.
struct MeasurementOutputRecord {
  std::string track_key;
  std::int32_t state_index = 0;
  std::uint64_t geometry_id = 0;           // ACTS GeometryIdentifier value of the surface; the state record holds the plane number
  std::array<std::int32_t, 2> projector{};  // bound indices measured: dr_i/dx_j = -1 for j = projector[i], 0 otherwise, at the state's own
                                            // parameters; R33's local derivatives are reference_derivative
  std::array<double, 2> local_slope{};     // local direction t_loc0 / t_normal, t_loc1 / t_normal
  double incidence_rad = 0.0;              // angle between the direction and the surface normal
  double thickness_mm = 0.0;               // the surface's thickness, Surface::thickness()
  double path_factor = 0.0;                // 1 / |t_normal|: path in the sensitive volume per unit thickness
  double sensitive_path_mm = 0.0;          // thickness_mm * path_factor
  std::array<double, 12> alignment_derivative{};  // dr_loc0/d a_k then dr_loc1/d a_k, k in the order of r32_plane_parameters
  // dr/dq_ref, rows loc0 and loc1, columns the bound parameters (loc0, loc1, phi, theta, q/p, time) of the track's reference state
  // (track_output.reference_state_index, its first measurement): -H J_{k<-ref}, J the propagator's transport Jacobian of the smoothed reference state to this state's surface.
  std::array<double, 12> reference_derivative{};
};

// R33, per fitted track: the full covariance of its residuals against the smoothed states, over its measurement states (kind measurement) in
// state order, loc0 then loc1 of each; upper triangle row by row, (2n)(2n + 1)/2 numbers. Closed form with no material:
// Cov(r_i, r_j) = V_i delta_ij - D_i C_ref D_j^T, D the reference derivatives (track_fit_outputs.hpp derives it).
struct ResidualCovarianceRecord {
  std::string track_key;
  std::int32_t measurement_count = 0;
  std::vector<double> covariance;
};

struct ProductDocument {
  int format_version = 1;  // 1 or 2; the R33 records exist in version 2 only
  ProductHeader header;
  std::vector<TrackRecord> tracks;
  std::vector<StateRecord> states;
  std::vector<ParameterRecord> parameters;
  std::vector<TrackOutputRecord> track_outputs;
  std::vector<ResidualRecord> residuals;
  std::vector<MeasurementOutputRecord> measurement_outputs;
  std::vector<ResidualCovarianceRecord> residual_covariances;
};

std::string encode_product(const ProductDocument& document);
ProductDocument decode_product(const std::string& text);  // either version; throws std::runtime_error on anything not of these formats
std::string read_whole_file(const std::string& path);
void write_whole_file(const std::string& path, const std::string& text);

}  // namespace t07
