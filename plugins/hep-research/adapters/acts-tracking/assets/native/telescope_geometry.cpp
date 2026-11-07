#include "telescope_geometry.hpp"

#include <Acts/Geometry/CuboidVolumeBuilder.hpp>
#include <Acts/Geometry/TrackingVolume.hpp>
#include <Acts/Surfaces/PlaneSurface.hpp>
#include <Acts/Surfaces/RectangleBounds.hpp>

#include "t07_fixture_constants.hpp"

namespace t07 {

int TelescopeGeometry::plane_number_of(const Acts::Surface& surface) const {
  for (std::size_t index = 0; index < planes.size(); ++index) {
    if (planes[index].get() == &surface) {
      return int(index) + 1;
    }
  }
  return 0;
}

TelescopeGeometry build_telescope_geometry() {
  TelescopeGeometry telescope;

  // Columns of the rotation are the local axes in the ACTS frame: loc0 = y, loc1 = z, normal = x.
  Acts::RotationMatrix3 plane_rotation;
  plane_rotation.col(0) = Acts::Vector3(0.0, 1.0, 0.0);
  plane_rotation.col(1) = Acts::Vector3(0.0, 0.0, 1.0);
  plane_rotation.col(2) = Acts::Vector3(1.0, 0.0, 0.0);
  auto plane_bounds = std::make_shared<const Acts::RectangleBounds>(plane_half_width_mm, plane_half_width_mm);

  Acts::CuboidVolumeBuilder::VolumeConfig volume_config;
  const double world_length_mm = world_downstream_x_mm - world_upstream_x_mm;
  volume_config.position = Acts::Vector3(0.5 * (world_downstream_x_mm + world_upstream_x_mm), 0.0, 0.0);
  volume_config.length = Acts::Vector3(world_length_mm, 2.0 * world_half_width_mm, 2.0 * world_half_width_mm);
  volume_config.name = "t07-telescope";
  for (int plane = 0; plane < plane_count; ++plane) {
    Acts::Transform3 plane_transform = Acts::Transform3::Identity();
    plane_transform.linear() = plane_rotation;
    plane_transform.translation() = Acts::Vector3(plane * plane_spacing_mm, 0.0, 0.0);
    auto surface = Acts::Surface::makeShared<Acts::PlaneSurface>(plane_transform, plane_bounds);
    surface->assignIsSensitive(true);  // a measurement surface with no detector element (Surface.hpp, assignIsSensitive)
    telescope.planes.push_back(surface);

    Acts::CuboidVolumeBuilder::LayerConfig layer_config;
    layer_config.surfaces = {surface};
    layer_config.active = true;
    layer_config.envelopeX = {layer_envelope_mm, layer_envelope_mm};
    volume_config.layerCfg.push_back(layer_config);
  }

  Acts::CuboidVolumeBuilder::Config world_config;
  world_config.position = volume_config.position;
  world_config.length = volume_config.length;
  world_config.volumeCfg = {volume_config};

  Acts::CuboidVolumeBuilder world_builder(world_config);
  std::shared_ptr<Acts::TrackingVolume> world = world_builder.trackingVolume(telescope.geometry_context, nullptr, nullptr);
  telescope.tracking_geometry = std::make_shared<const Acts::TrackingGeometry>(world);
  return telescope;
}

}  // namespace t07
