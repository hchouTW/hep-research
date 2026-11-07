#include "payload_geometry.hpp"

#include <Acts/Geometry/CuboidVolumeBuilder.hpp>
#include <Acts/Geometry/TrackingVolume.hpp>
#include <Acts/Surfaces/PlanarBounds.hpp>
#include <Acts/Surfaces/PlaneSurface.hpp>
#include <Acts/Surfaces/RectangleBounds.hpp>
#include <Acts/Surfaces/SurfacePlacementBase.hpp>

#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace t07 {
namespace {

using PlaneTransforms = std::array<Acts::Transform3, plane_count>;

// What a payload puts in the context: the transform of every plane, so a placement only looks one up and can hand back a reference.
struct PlaneTransformSet {
  std::shared_ptr<const PlaneTransforms> transforms;
};

PlaneTransforms nominal_plane_transforms() {
  const TelescopeGeometry frozen = build_telescope_geometry();
  PlaneTransforms transforms;
  for (int plane = 0; plane < plane_count; ++plane) {
    transforms[plane] = frozen.planes.at(plane)->localToGlobalTransform(frozen.geometry_context);
  }
  return transforms;
}

PlaneTransforms moved_plane_transforms(const PlaneTransforms& nominal, const PlaneDeltas& deltas) {
  PlaneTransforms moved;
  for (int plane = 0; plane < plane_count; ++plane) {
    moved[plane] = moved_plane_transform(nominal[plane], deltas[plane]);
  }
  return moved;
}

Acts::GeometryContext context_of(const PlaneTransforms& transforms) {
  return Acts::GeometryContext(PlaneTransformSet{std::make_shared<const PlaneTransforms>(transforms)});
}

class PlacedPlane final : public Acts::SurfacePlacementBase {
 public:
  PlacedPlane(std::size_t plane_index, const Acts::Transform3& nominal, std::shared_ptr<const Acts::PlanarBounds> bounds)
      : m_plane_index(plane_index), m_nominal(nominal), m_surface(Acts::Surface::makeShared<Acts::PlaneSurface>(std::move(bounds), *this)) {}

  const Acts::Transform3& localToGlobalTransform(const Acts::GeometryContext& context) const override {
    if (const PlaneTransformSet* set = context.maybeGet<PlaneTransformSet>(); set != nullptr) {
      return set->transforms->at(m_plane_index);
    }
    if (m_building) {  // the headers do not say that every call inside the geometry build passes the context it was given
      return m_nominal;
    }
    throw std::logic_error("a context with no plane transforms reached a placed plane");
  }

  const Acts::Surface& surface() const override { return *m_surface; }
  Acts::Surface& surface() override { return *m_surface; }
  bool isSensitive() const override { return true; }

  std::shared_ptr<const Acts::Surface> shared_surface() const { return m_surface; }
  void finish_building() { m_building = false; }

 private:
  std::size_t m_plane_index;
  Acts::Transform3 m_nominal;
  bool m_building = true;
  std::shared_ptr<Acts::PlaneSurface> m_surface;
};

// The world of build_telescope_geometry(), around any eight planes. Its own constants are all in t07_fixture_constants.hpp.
TelescopeGeometry assemble_telescope(const std::vector<std::shared_ptr<const Acts::Surface>>& planes, const Acts::GeometryContext& context) {
  TelescopeGeometry telescope;
  telescope.geometry_context = context;
  telescope.planes = planes;

  Acts::CuboidVolumeBuilder::VolumeConfig volume_config;
  const double world_length_mm = world_downstream_x_mm - world_upstream_x_mm;
  volume_config.position = Acts::Vector3(0.5 * (world_downstream_x_mm + world_upstream_x_mm), 0.0, 0.0);
  volume_config.length = Acts::Vector3(world_length_mm, 2.0 * world_half_width_mm, 2.0 * world_half_width_mm);
  volume_config.name = "t07-telescope";
  for (const std::shared_ptr<const Acts::Surface>& plane : planes) {
    Acts::CuboidVolumeBuilder::LayerConfig layer_config;
    layer_config.surfaces = {plane};
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

}  // namespace

Acts::Transform3 moved_plane_transform(const Acts::Transform3& nominal, const PlaneDelta& delta) {
  Acts::Transform3 change = Acts::Transform3::Identity();
  change.translation() = Acts::Vector3(delta.shift_loc0_mm, delta.shift_loc1_mm, delta.shift_normal_mm);
  const Acts::RotationMatrix3 rotation_normal = Acts::AngleAxis3(delta.rotation_normal, Acts::Vector3::UnitZ()).toRotationMatrix();
  const Acts::RotationMatrix3 rotation_loc1 = Acts::AngleAxis3(delta.rotation_loc1, Acts::Vector3::UnitY()).toRotationMatrix();
  const Acts::RotationMatrix3 rotation_loc0 = Acts::AngleAxis3(delta.rotation_loc0, Acts::Vector3::UnitX()).toRotationMatrix();
  change.linear() = rotation_normal * rotation_loc1 * rotation_loc0;
  return nominal * change;
}

TelescopeGeometry rebuild_moved_telescope(const PlaneDeltas& deltas) {
  const PlaneTransforms moved = moved_plane_transforms(nominal_plane_transforms(), deltas);
  auto plane_bounds = std::make_shared<const Acts::RectangleBounds>(plane_half_width_mm, plane_half_width_mm);
  std::vector<std::shared_ptr<const Acts::Surface>> planes;
  for (const Acts::Transform3& transform : moved) {
    auto surface = Acts::Surface::makeShared<Acts::PlaneSurface>(transform, plane_bounds);
    surface->assignIsSensitive(true);  // as build_telescope_geometry(): a measurement surface with no placement
    planes.push_back(surface);
  }
  return assemble_telescope(planes, Acts::GeometryContext::dangerouslyDefaultConstruct());
}

// The placements are destroyed after the telescope, which is declared last: a surface keeps a plain pointer to its placement.
struct PlacedTelescope::Planes {
  PlaneTransforms nominal;
  std::vector<std::shared_ptr<PlacedPlane>> placements;
  TelescopeGeometry telescope;
};

PlacedTelescope::PlacedTelescope() : m_planes(new Planes) {
  m_planes->nominal = nominal_plane_transforms();
  auto plane_bounds = std::make_shared<const Acts::RectangleBounds>(plane_half_width_mm, plane_half_width_mm);
  std::vector<std::shared_ptr<const Acts::Surface>> planes;
  for (std::size_t plane = 0; plane < m_planes->nominal.size(); ++plane) {
    m_planes->placements.push_back(std::make_shared<PlacedPlane>(plane, m_planes->nominal[plane], plane_bounds));
    planes.push_back(m_planes->placements.back()->shared_surface());
  }
  m_planes->telescope = assemble_telescope(planes, context_of(m_planes->nominal));
  for (const std::shared_ptr<PlacedPlane>& placement : m_planes->placements) {
    placement->finish_building();
  }
}

PlacedTelescope::~PlacedTelescope() = default;

TelescopeGeometry PlacedTelescope::with_deltas(const PlaneDeltas& deltas) const {
  TelescopeGeometry telescope = m_planes->telescope;
  telescope.geometry_context = context_of(moved_plane_transforms(m_planes->nominal, deltas));
  return telescope;
}

}  // namespace t07
