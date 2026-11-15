#include "t07_event_generator.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace t07 {
namespace {

struct DrawnHit {  // a hit before the event's hits are sorted; track_index -1 marks noise
  PlaneHit hit;
  int track_index = -1;
};

std::vector<TruthVertex> draw_vertices(EventSeedStream& stream, int vertex_count, bool near_separation) {
  const auto& step_units = near_separation ? near_step_units : far_step_units;
  std::vector<TruthVertex> vertices;
  for (int index = 0; index < vertex_count; ++index) {
    TruthVertex vertex;
    vertex.u_mm = stream.uniform_between(-vertex_u_half_range_mm, vertex_u_half_range_mm);
    vertex.z_mm = stream.uniform_between(vertex_z_centre_mm - vertex_z_half_range_mm, vertex_z_centre_mm + vertex_z_half_range_mm);
    if (index == 0) {
      vertex.v_mm = stream.uniform_between(-vertex_v_half_range_mm, vertex_v_half_range_mm);
    } else {
      vertex.v_mm = vertices.back().v_mm + resolution_unit_mm * stream.uniform_between(step_units[0], step_units[1]);
    }
    vertices.push_back(vertex);
  }
  return vertices;
}

std::vector<int> draw_charges(EventSeedStream& stream, int track_count) {
  std::vector<int> charges(track_count, -1);
  std::fill(charges.begin(), charges.begin() + track_count / 2, 1);
  for (int index = track_count - 1; index > 0; --index) {  // Fisher-Yates
    const int other = int(stream.uniform() * double(index + 1));
    std::swap(charges[index], charges[other]);
  }
  return charges;
}

}  // namespace

GeneratedEvent generate_event(const FixtureSpec& fixture, std::uint32_t block, std::uint32_t stratum, std::uint64_t event_index,
                              const PlanePropagation& propagation) {
  if (stratum >= std::uint32_t(stratum_count)) {
    throw std::runtime_error("stratum out of range: " + std::to_string(stratum));
  }
  const int momentum_bin = momentum_bin_of(int(stratum));
  const int occupancy_level = occupancy_level_of(int(stratum));
  const int track_count = tracks_per_event[occupancy_level];
  const int vertex_count = vertices_per_event[occupancy_level];
  const int tracks_per_vertex = track_count / vertex_count;
  const bool near_separation = event_index % near_event_modulus == 0;

  GeneratedEvent event;
  event.truth.event_digest = event_seed_digest(fixture.fixture_id, block, stratum, event_index);
  event.truth.event_index = event_index;
  event.truth.momentum_bin = std::uint32_t(momentum_bin);
  event.truth.occupancy_level = std::uint32_t(occupancy_level);
  event.truth.near_separation = near_separation ? 1 : 0;

  EventSeedStream stream(event.truth.event_digest);
  event.truth.vertices = draw_vertices(stream, vertex_count, near_separation);
  const std::vector<int> charges = draw_charges(stream, track_count);

  const double log_lower = std::log(momentum_bins_gev[momentum_bin][0]);
  const double log_upper = std::log(momentum_bins_gev[momentum_bin][1]);
  event.truth.tracks.resize(track_count);
  for (int index = 0; index < track_count; ++index) {
    TruthTrack& track = event.truth.tracks[index];
    track.particle_key = std::uint32_t(index);
    track.vertex_index = std::uint32_t(index / tracks_per_vertex);
    track.charge = charges[index];
    track.momentum_gev = std::exp(stream.uniform_between(log_lower, log_upper));
    track.slope_u = stream.uniform_between(-slope_half_range, slope_half_range);
    track.slope_v = stream.uniform_between(-slope_half_range, slope_half_range);
    track.q_over_p = double(track.charge) / track.momentum_gev;
    track.hit_keys.fill(no_hit_key);
  }

  std::vector<DrawnHit> drawn;
  for (int index = 0; index < track_count; ++index) {
    TruthTrack& track = event.truth.tracks[index];
    const TruthVertex& vertex = event.truth.vertices[track.vertex_index];
    // ACTS frame: x = fixture z, y = fixture u, z = fixture v.
    const Acts::Vector3 start(vertex.z_mm, vertex.u_mm, vertex.v_mm);
    const Acts::Vector3 direction = Acts::Vector3(1.0, track.slope_u, track.slope_v).normalized();
    const std::vector<PlaneCrossing> crossings = propagation.crossings(start, direction, track.q_over_p);
    if (int(crossings.size()) != plane_count) {  // section 4.1, Fiducial: all tracks cross all planes, no resampling
      throw std::runtime_error("a track crossed " + std::to_string(crossings.size()) + " planes");
    }
    for (int plane = 0; plane < plane_count; ++plane) {
      const PlaneCrossing& crossing = crossings[plane];
      if (crossing.plane != plane + 1 || std::abs(crossing.loc0_mm) >= plane_half_width_mm || std::abs(crossing.loc1_mm) >= plane_half_width_mm) {
        throw std::runtime_error("a track left the active area at plane " + std::to_string(plane + 1));
      }
      track.crossings[plane] = {crossing.loc0_mm, crossing.loc1_mm, crossing.phi, crossing.theta};
      const bool kept = stream.uniform() < fixture.hit_efficiency;
      const double smear0 = hit_sigma_mm * stream.gaussian();
      const double smear1 = hit_sigma_mm * stream.gaussian();
      if (kept) {
        drawn.push_back({{0, std::uint32_t(plane + 1), crossing.loc0_mm + smear0, crossing.loc1_mm + smear1}, index});
      }
    }
  }

  if (fixture.kind == FixtureKind::noise) {
    for (int plane = 0; plane < plane_count; ++plane) {
      const std::uint32_t noise_count = stream.poisson(noise_means[occupancy_level]);
      event.truth.noise_counts[plane] = noise_count;
      for (std::uint32_t noise_hit = 0; noise_hit < noise_count; ++noise_hit) {
        const double loc0 = stream.uniform_between(-plane_half_width_mm, plane_half_width_mm);
        const double loc1 = stream.uniform_between(-plane_half_width_mm, plane_half_width_mm);
        drawn.push_back({{0, std::uint32_t(plane + 1), loc0, loc1}, -1});
      }
    }
  }

  // One code path for every hit, before anything reads a coordinate again: the grid, then plane and position order. Neither step
  // reads track_index, so neither the bits of a hit nor its place in the event depend on what made it.
  for (DrawnHit& entry : drawn) {
    entry.hit.loc0_mm = on_hit_grid(entry.hit.loc0_mm);
    entry.hit.loc1_mm = on_hit_grid(entry.hit.loc1_mm);
  }
  std::sort(drawn.begin(), drawn.end(), [](const DrawnHit& first, const DrawnHit& second) {
    return std::tie(first.hit.plane, first.hit.loc0_mm, first.hit.loc1_mm) < std::tie(second.hit.plane, second.hit.loc0_mm, second.hit.loc1_mm);
  });
  event.data.hits.reserve(drawn.size());
  for (std::size_t position = 0; position < drawn.size(); ++position) {
    DrawnHit& entry = drawn[position];
    entry.hit.hit_key = std::uint32_t(position);
    event.data.hits.push_back(entry.hit);
    if (entry.track_index >= 0) {
      event.truth.tracks[entry.track_index].hit_keys[entry.hit.plane - 1] = entry.hit.hit_key;
    }
  }
  return event;
}

}  // namespace t07
