#include "t07_cai_event_generator.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace t07 {

GeneratedEvent generate_cai_event(const CaiFixture& fixture, std::uint32_t block, std::uint32_t stratum, std::uint64_t event_index, const PlanePropagation& propagation) {
  if (stratum >= std::uint32_t(cai_stratum_count)) {
    throw std::runtime_error("stratum out of range: " + std::to_string(stratum));
  }
  GeneratedEvent event;
  event.truth.event_digest = event_seed_digest(fixture.fixture_id, block, stratum, event_index);
  event.truth.event_index = event_index;
  event.truth.momentum_bin = stratum;
  EventSeedStream stream(event.truth.event_digest);

  TruthVertex vertex;
  vertex.u_mm = stream.uniform_between(-vertex_u_half_range_mm, vertex_u_half_range_mm);
  vertex.z_mm = stream.uniform_between(vertex_z_centre_mm - vertex_z_half_range_mm, vertex_z_centre_mm + vertex_z_half_range_mm);
  vertex.v_mm = stream.uniform_between(-vertex_v_half_range_mm, vertex_v_half_range_mm);
  event.truth.vertices.push_back(vertex);

  TruthTrack track;
  track.charge = stream.uniform() < 0.5 ? 1 : -1;
  track.momentum_gev = std::exp(stream.uniform_between(std::log(momentum_bins_gev[stratum][0]), std::log(momentum_bins_gev[stratum][1])));
  track.slope_u = stream.uniform_between(-slope_half_range, slope_half_range);
  track.slope_v = stream.uniform_between(-slope_half_range, slope_half_range);
  track.q_over_p = double(track.charge) / track.momentum_gev;
  track.hit_keys.fill(no_hit_key);

  // ACTS frame: x = fixture z, y = fixture u, z = fixture v.
  const Acts::Vector3 start(vertex.z_mm, vertex.u_mm, vertex.v_mm);
  const Acts::Vector3 direction = Acts::Vector3(1.0, track.slope_u, track.slope_v).normalized();
  const std::vector<PlaneCrossing> crossings = propagation.crossings(start, direction, track.q_over_p);
  if (int(crossings.size()) != plane_count) {  // section 4.1, Fiducial: all tracks cross all planes, no resampling
    throw std::runtime_error("a track crossed " + std::to_string(crossings.size()) + " planes");
  }
  for (int plane = 0; plane < plane_count; ++plane) {
    const PlaneCrossing& crossing = crossings[plane];
    const double displacement_mm = fixture.kind == CaiFixtureKind::sagitta ? cai_sagitta_displacement_mm(plane) : 0.0;
    const double loc0_mm = crossing.loc0_mm - displacement_mm;
    if (crossing.plane != plane + 1 || std::abs(loc0_mm) >= plane_half_width_mm || std::abs(crossing.loc1_mm) >= plane_half_width_mm) {
      throw std::runtime_error("a track left the active area at plane " + std::to_string(plane + 1));
    }
    track.crossings[plane] = {loc0_mm, crossing.loc1_mm, crossing.phi, crossing.theta};
    const double smear0 = hit_sigma_mm * stream.gaussian();
    const double smear1 = hit_sigma_mm * stream.gaussian();
    // The grid of t07_generation_constants.hpp. One hit per plane, so plane order is position order and hit_key is the plane's index.
    event.data.hits.push_back({std::uint32_t(plane), std::uint32_t(plane + 1), on_hit_grid(loc0_mm + smear0), on_hit_grid(crossing.loc1_mm + smear1)});
    track.hit_keys[plane] = std::uint32_t(plane);
  }
  event.truth.tracks.push_back(track);
  return event;
}

}  // namespace t07
