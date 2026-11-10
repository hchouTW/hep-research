// t07-alignment-payload/1, the alignment payload the refit takes (plan R32, R33, R37; CAI-T07-3; D1 stage 9). fixture_tools/t07_alignment_payload.py
// states the format and is the same reader in Python; the two refuse the same defects. Data side: no generator, seed or truth code reaches this file.
//
//  - Mapping: a plane record is that plane's PlaneDelta (payload_geometry.hpp) in t07-plane-rigid/1's order (track_fit_outputs.hpp, r32_plane_parameters);
//    a plane without a record is at nominal. The driver applies it through the placement route, PlacedTelescope::with_deltas (user's choice 16).
//  - Identity: the content identity is the SHA-256 of the file's bytes; a product that consumed a payload records it (R32: "Every reconstruction
//    product records the identity and round of each payload it consumed"). A payload derived from another records that one's content identity.
//  - Refused, never applied (R32): a malformed file, a plane that does not exist, and a payload derived against another nominal geometry than the one
//    it would be applied to (nominal_geometry_id below).
#pragma once

#include <string>
#include <vector>

#include "payload_geometry.hpp"

namespace t07 {

inline constexpr char alignment_payload_format[] = "t07-alignment-payload/1";
inline constexpr char nominal_geometry_format[] = "t07-telescope-nominal/1";

struct AlignmentPayload {
  std::string content_sha256;   // the payload's content identity
  std::string derived_against;  // the nominal geometry identity its deltas apply to
  std::string origin;           // nominal or measured (R32)
  std::string derived_from;     // none, or the content identity of the payload it was derived from (R33)
  std::vector<int> planes;      // the planes with a record, in increasing order
  PlaneDeltas deltas{};         // every plane; nominal where there is no record
};

// The text whose SHA-256 is the nominal geometry identity: the eight planes of build_telescope_geometry(), each with its bounds and its
// local-to-global transform at 17 significant digits. Not g4sim's geometry_id (D2): the T07 telescope has no geometry IR (D1 stage 9 report).
std::string nominal_geometry_text();
std::string nominal_geometry_id();

// Throws std::invalid_argument on anything t07-alignment-payload/1 does not allow.
AlignmentPayload parse_alignment_payload(const std::string& text);
// The same, and refuses a payload derived against another geometry than geometry_id.
AlignmentPayload parse_alignment_payload_for(const std::string& text, const std::string& geometry_id);

}  // namespace t07
