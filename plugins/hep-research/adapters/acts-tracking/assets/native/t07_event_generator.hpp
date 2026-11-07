// One T07 event as a pure function of (fixture, block, stratum, event_index): t04-values-v4.md sections 3.2 and 4.1.
#pragma once

#include <cstdint>

#include "plane_propagation.hpp"
#include "t07_data_file.hpp"
#include "t07_generation_constants.hpp"
#include "t07_truth_file.hpp"

namespace t07 {

struct GeneratedEvent {
  DataEvent data;
  TruthEvent truth;
};

// Draw order, part of the generator's version: per vertex (u, z, then v for the first and the step for a further one); the
// charge shuffle; per track (ln p, u slope, v slope); per track and plane (efficiency, then two Gaussians, loc0 before loc1);
// per plane (noise count, then per noise hit loc0, loc1). Two uniforms make one Gaussian.
GeneratedEvent generate_event(const FixtureSpec& fixture, std::uint32_t block, std::uint32_t stratum, std::uint64_t event_index,
                              const PlanePropagation& propagation);

}  // namespace t07
