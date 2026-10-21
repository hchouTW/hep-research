#include "Spec.hh"

#include <fstream>
#include <set>
#include <sstream>

#include "MiniJson.hh"

using minijson::JsonError;
using minijson::Value;

namespace {

double optNumber(const Value& o, const std::string& k, double dflt, const std::string& where) {
  return o.has(k) ? o.obj.at(k).number(where + "." + k) : dflt;
}

bool optBool(const Value& o, const std::string& k, bool dflt, const std::string& where) {
  return o.has(k) ? o.obj.at(k).boolean(where + "." + k) : dflt;
}

std::string optString(const Value& o, const std::string& k, const std::string& dflt, const std::string& where) {
  return o.has(k) ? o.obj.at(k).string(where + "." + k) : dflt;
}

std::array<double, 3> triple(const Value& v, const std::string& where) {
  const auto& a = v.array(where);
  if (a.size() != 3) throw JsonError(where + " must have three numbers");
  return {a[0].number(where), a[1].number(where), a[2].number(where)};
}

}  // namespace

std::vector<std::string> Spec::slabNames() const {
  std::vector<std::string> out;
  std::set<std::string> seen;
  for (const auto& l : layers)
    for (const auto& s : l.slabs)
      if (seen.insert(s.name).second) out.push_back(s.name);
  return out;
}

Spec ReadSpec(const std::string& path) {
  std::ifstream in(path);
  if (!in) throw JsonError("cannot read spec " + path);
  std::stringstream buf;
  buf << in.rdbuf();
  Value root = minijson::parse(buf.str());
  if (!root.isObject()) throw JsonError("the spec must be a JSON object");
  if (root.at("schema", "spec").string("schema") != "layered_sim.spec/1")
    throw JsonError("schema must be layered_sim.spec/1");
  Spec s;

  const Value& g = root.at("geometry", "spec");
  s.lateral_mm = g.at("lateral_mm", "geometry").number("geometry.lateral_mm");
  if (s.lateral_mm <= 0) throw JsonError("geometry.lateral_mm must be positive");
  for (const auto& lv : g.at("layers", "geometry").array("geometry.layers")) {
    LayerDef l;
    l.repeat = static_cast<int>(optNumber(lv, "repeat", 1, "layer"));
    if (l.repeat < 1) throw JsonError("layer.repeat must be at least 1");
    for (const auto& sv : lv.at("slabs", "layer").array("layer.slabs")) {
      SlabDef d;
      d.name = sv.at("name", "slab").string("slab.name");
      d.material = sv.at("material", "slab").string("slab.material");
      d.thickness_mm = sv.at("thickness_mm", "slab").number("slab.thickness_mm");
      d.sensitive = optBool(sv, "sensitive", false, "slab");
      d.shift_mm = optNumber(sv, "shift_mm", 0, "slab");
      if (d.thickness_mm <= 0) throw JsonError("slab " + d.name + ": thickness_mm must be positive");
      l.slabs.push_back(d);
    }
    if (l.slabs.empty()) throw JsonError("a layer needs at least one slab");
    s.layers.push_back(l);
  }
  if (s.layers.empty()) throw JsonError("geometry.layers must not be empty");
  const Value& w = g.at("world", "geometry");
  s.world_material = w.at("material", "geometry.world").string("geometry.world.material");
  if (w.has("scale")) {
    s.world_scale = w.obj.at("scale").number("geometry.world.scale");
    if (s.world_scale <= 1) throw JsonError("geometry.world.scale must exceed 1");
  } else {
    s.world_mm = triple(w.at("size_mm", "geometry.world"), "geometry.world.size_mm");
  }

  if (root.has("materials"))
    for (const auto& mv : root.obj.at("materials").array("materials")) {
      MaterialDef m;
      m.name = mv.at("name", "material").string("material.name");
      if (mv.has("components")) {
        for (const auto& cv : mv.obj.at("components").array("material.components"))
          m.components.emplace_back(cv.at("material", "component").string("component.material"),
                                    cv.at("mass_fraction", "component").number("component.mass_fraction"));
      } else {
        m.z = static_cast<int>(mv.at("z", "material").number("material.z"));
        m.a_g_mole = mv.at("a_g_mole", "material").number("material.a_g_mole");
      }
      m.density_g_cm3 = mv.at("density_g_cm3", "material").number("material.density_g_cm3");
      m.state = optString(mv, "state", "solid", "material");
      m.temperature_K = optNumber(mv, "temperature_K", -1, "material");
      m.pressure_Pa = optNumber(mv, "pressure_Pa", -1, "material");
      if (m.components.empty() && (m.z < 1 || m.a_g_mole <= 0 || m.density_g_cm3 <= 0))
        throw JsonError("material " + m.name + ": z, a_g_mole and density_g_cm3 must be positive");
      if (!m.components.empty() && (m.components.size() < 2 || m.density_g_cm3 <= 0))
        throw JsonError("material " + m.name + ": a mixture needs at least two components and a positive density");
      s.materials.push_back(m);
    }

  const Value& p = root.at("physics", "spec");
  s.reference_list = optString(p, "reference_list", "", "physics");
  s.em_constructor = optString(p, "em_constructor", "", "physics");
  if (s.reference_list.empty() == s.em_constructor.empty())
    throw JsonError("physics needs exactly one of reference_list and em_constructor");
  s.decay = optBool(p, "decay", true, "physics");
  s.default_cut_mm = p.at("default_cut_mm", "physics").number("physics.default_cut_mm");
  if (p.has("regions"))
    for (const auto& rv : p.obj.at("regions").array("physics.regions")) {
      RegionDef r;
      r.name = rv.at("name", "region").string("region.name");
      r.cut_mm = rv.at("cut_mm", "region").number("region.cut_mm");
      for (const auto& n : rv.at("slabs", "region").array("region.slabs")) r.slabs.push_back(n.string("region.slabs"));
      s.regions.push_back(r);
    }
  s.step_limit_mm = optNumber(p, "step_limit_mm", 0, "physics");
  s.min_ekin_MeV = optNumber(p, "min_ekin_MeV", 0, "physics");
  s.kill_secondaries = optBool(p, "kill_secondaries", false, "physics");
  if (root.has("ui_commands"))
    for (const auto& c : root.obj.at("ui_commands").array("ui_commands")) s.ui_commands.push_back(c.string("ui_commands"));

  const Value& gun = root.at("gun", "spec");
  s.particle = gun.at("particle", "gun").string("gun.particle");
  s.energy_MeV = gun.at("energy_MeV", "gun").number("gun.energy_MeV");
  s.gun_world_fraction = optNumber(gun, "world_fraction", -0.5, "gun");
  if (gun.has("direction")) s.direction = triple(gun.obj.at("direction"), "gun.direction");

  const Value& r = root.at("run", "spec");
  s.events = static_cast<long>(r.at("events", "run").number("run.events"));
  s.first_event = static_cast<long>(optNumber(r, "first_event", 0, "run"));
  s.chunk = static_cast<int>(optNumber(r, "chunk", 0, "run"));
  const auto& seeds = r.at("seeds", "run").array("run.seeds");
  if (seeds.size() != 2) throw JsonError("run.seeds must have two integers");
  s.seeds = {static_cast<long>(seeds[0].number("run.seeds")), static_cast<long>(seeds[1].number("run.seeds"))};
  s.run_manager = optString(r, "run_manager", "serial", "run");
  s.threads = static_cast<int>(optNumber(r, "threads", 1, "run"));
  if (s.events < 1) throw JsonError("run.events must be at least 1");
  if (s.run_manager != "serial" && s.run_manager != "mt") throw JsonError("run.run_manager must be serial or mt");

  const Value& o = root.at("output", "spec");
  s.csv = o.at("csv", "output").string("output.csv");
  s.materials_out = o.at("materials", "output").string("output.materials");
  s.datapaths_out = o.at("datapaths", "output").string("output.datapaths");
  s.overlap_test_points = static_cast<int>(optNumber(o, "overlap_test_points", 0, "output"));
  s.per_instance = optBool(o, "per_instance", false, "output");

  std::set<std::string> names;
  for (const auto& n : s.slabNames()) names.insert(n);
  for (const auto& reg : s.regions)
    for (const auto& n : reg.slabs)
      if (!names.count(n)) throw JsonError("region " + reg.name + " names unknown slab " + n);
  return s;
}
