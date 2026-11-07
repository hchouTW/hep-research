// One event of t07-telescope-cai/1 as a pure function of (fixture, block, stratum, event_index): the seed rule of section 3.2, one
// track per event on the clean geometry of section 4.1, and for the sagitta fixture the same with the planes truly displaced.
#pragma once

#include <cstdint>

#include "plane_propagation.hpp"
#include "t07_cai_constants.hpp"
#include "t07_event_generator.hpp"

namespace t07 {

// Draw order, part of this generator's version: vertex (u, z, v); track (ln p, u slope, v slope); per plane two Gaussians, loc0 before
// loc1. Charge is drawn from nothing: +1 for an even event_index, -1 for an odd one, so each pair of events is exactly half and half,
// the nearest one track per event comes to section 4.1's Charge row.
//
// The deformation moves planes inside their own surface, along loc0, so a track crosses each plane where it crossed the nominal one and
// the propagation stays on the frozen geometry. Only the local coordinate changes: crossing.loc0 - d_k, in truth and in the hit. Bounds
// are no issue: d_k is at most 0.06 mm, against at least 25 mm from a crossing to the edge.
GeneratedEvent generate_cai_event(const CaiFixture& fixture, std::uint32_t block, std::uint32_t stratum, std::uint64_t event_index, const PlanePropagation& propagation);

}  // namespace t07
