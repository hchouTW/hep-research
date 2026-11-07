// What a recipe may know of the telescope in t04-values-v4.md section 4.1 (design choices, synthetic data, no detector implied).
// Units: mm, GeV, T. Frame: fixture z along the telescope, u bending, v along the field. ACTS frame: x = fixture z, y = fixture u,
// z = fixture v, so fixture v is ACTS z (section 4.1, [R14]). How events are drawn is in t07_generation_constants.hpp, which the
// driver does not reach.
#pragma once

namespace t07 {

inline constexpr int plane_count = 8;                 // section 4.1, Planes
inline constexpr double plane_spacing_mm = 50.0;      // z = 0, 50, ..., 350 mm
inline constexpr double plane_half_width_mm = 150.0;  // active area 300 x 300 mm
inline constexpr double hit_sigma_mm = 0.020;         // Measurement
inline constexpr double field_tesla = 1.0;            // Field, along local v
inline constexpr double particle_mass_gev = 0.1;      // Particle

// Not fixture values: a choice of this generator, listed in the stage report. The world encloses the vertices and all planes.
inline constexpr double world_upstream_x_mm = -150.0;
inline constexpr double world_downstream_x_mm = 400.0;
inline constexpr double world_half_width_mm = 200.0;
inline constexpr double layer_envelope_mm = 1.0;

}  // namespace t07
