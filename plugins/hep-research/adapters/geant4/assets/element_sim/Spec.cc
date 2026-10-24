#include "Spec.hh"

#include <fstream>
#include <map>
#include <set>
#include <sstream>

#include "MiniJson.hh"
#include "SimHash.hh"
#include "SimObservables.hh"

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

Vec3 triple(const Value& v, const std::string& where) {
  const auto& a = v.array(where);
  if (a.size() != 3) throw JsonError(where + " must have three numbers");
  return {a[0].number(where), a[1].number(where), a[2].number(where)};
}

// nucleons of the light ions a gun may name with ekin_per_nucleon_MeV (heavier ions are deferred, Geant4 program B.9)
int Nucleons(const std::string& particle) {
  static const std::map<std::string, int> a = {{"proton", 1}, {"deuteron", 2}, {"triton", 3}, {"He3", 3}, {"alpha", 4}};
  auto it = a.find(particle);
  return it == a.end() ? 0 : it->second;
}

}  // namespace

int Spec::ElementIndex(const std::string& name) const {
  for (std::size_t i = 0; i < elements.size(); ++i)
    if (elements[i].name == name) return static_cast<int>(i);
  return -1;
}

int Spec::CalorimeterIndex() const {
  for (std::size_t i = 0; i < elements.size(); ++i)
    if (elements[i].role == "calorimeter") return static_cast<int>(i);
  return -1;
}

bool Spec::Level(const std::string& atLeast) const {
  static const std::map<std::string, int> rank = {{"none", 0}, {"summary", 1}, {"crossings", 2}, {"hits", 3}};
  return rank.at(event_level) >= rank.at(atLeast);
}

Spec ReadSpec(const std::string& path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) throw JsonError("cannot read spec " + path);
  std::stringstream buf;
  buf << in.rdbuf();
  Value root = minijson::parse(buf.str());
  if (!root.isObject()) throw JsonError("the spec must be a JSON object");
  if (root.at("schema", "spec").string("schema") != "element_sim.spec/1")
    throw JsonError("schema must be element_sim.spec/1");
  Spec s;
  s.spec_path = path;
  s.spec_sha256 = g4sim::Sha256::HexOf(buf.str());

  const Value& w = root.at("world", "spec");
  s.world_material = w.at("material", "world").string("world.material");
  s.world_half_mm = triple(w.at("half_mm", "world"), "world.half_mm");

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
      s.materials.push_back(m);
    }

  std::set<std::string> names;
  for (const auto& ev : root.at("elements", "spec").array("elements")) {
    ElementDef e;
    e.name = ev.at("name", "element").string("element.name");
    e.material = ev.at("material", "element").string("element.material");
    e.centre_mm = triple(ev.at("centre_mm", "element"), "element " + e.name + ".centre_mm");
    e.half_mm = triple(ev.at("half_mm", "element"), "element " + e.name + ".half_mm");
    e.mother = optString(ev, "mother", "world", "element");
    e.role = ev.at("role", "element").string("element.role");
    if (ev.has("repeat")) {
      const Value& r = ev.obj.at("repeat");
      e.count = static_cast<int>(r.at("count", "repeat").number("repeat.count"));
      e.pitch_mm = triple(r.at("pitch_mm", "repeat"), "element " + e.name + ".repeat.pitch_mm");
    }
    if (ev.has("shift_mm")) e.shift_mm = triple(ev.obj.at("shift_mm"), "element " + e.name + ".shift_mm");
    for (double h : e.half_mm)
      if (!(h > 0)) throw JsonError("element " + e.name + ": half_mm must be positive");
    if (e.count < 1) throw JsonError("element " + e.name + ": repeat.count must be at least 1");
    if (!names.insert(e.name).second || e.name == "world" || e.name == "World")
      throw JsonError("element name " + e.name + " is not unique");
    s.elements.push_back(e);
  }
  for (const auto& e : s.elements)
    if (e.mother != "world" && s.ElementIndex(e.mother) < 0)
      throw JsonError("element " + e.name + " names unknown mother " + e.mother);

  if (root.has("field")) {
    const Value& f = root.obj.at("field");
    for (const auto& rv : f.at("regions", "field").array("field.regions")) {
      FieldRegionDef r;
      r.element = rv.at("element", "field.regions").string("field.regions.element");
      r.b_tesla = triple(rv.at("b_tesla", "field.regions"), "field.regions.b_tesla");
      if (s.ElementIndex(r.element) < 0) throw JsonError("field region names unknown element " + r.element);
      s.field.regions.push_back(r);
    }
    s.field.stepper = optString(f, "stepper", s.field.stepper, "field");
    s.field.driver = optString(f, "driver", s.field.driver, "field");
    s.field.delta_chord_mm = optNumber(f, "delta_chord_mm", s.field.delta_chord_mm, "field");
    s.field.delta_one_step_mm = optNumber(f, "delta_one_step_mm", s.field.delta_one_step_mm, "field");
    s.field.delta_intersection_mm = optNumber(f, "delta_intersection_mm", s.field.delta_intersection_mm, "field");
    s.field.min_epsilon_step = optNumber(f, "min_epsilon_step", s.field.min_epsilon_step, "field");
    s.field.max_epsilon_step = optNumber(f, "max_epsilon_step", s.field.max_epsilon_step, "field");
    s.field.max_step_mm = optNumber(f, "max_step_mm", s.field.max_step_mm, "field");
    s.field.max_track_time_ns = optNumber(f, "max_track_time_ns", s.field.max_track_time_ns, "field");
    if (s.field.stepper != "DormandPrince745" || s.field.driver != "InterpolationDriver")
      throw JsonError("field: only stepper DormandPrince745 with driver InterpolationDriver is built");
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
      CutRegionDef r;
      r.name = rv.at("name", "region").string("region.name");
      r.cut_mm = rv.at("cut_mm", "region").number("region.cut_mm");
      for (const auto& n : rv.at("elements", "region").array("region.elements")) {
        r.elements.push_back(n.string("region.elements"));
        if (s.ElementIndex(r.elements.back()) < 0)
          throw JsonError("region " + r.name + " names unknown element " + r.elements.back());
      }
      s.regions.push_back(r);
    }
  if (root.has("ui_commands"))
    for (const auto& c : root.obj.at("ui_commands").array("ui_commands")) s.ui_commands.push_back(c.string("ui_commands"));

  const Value& src = root.at("source", "spec");
  std::string type = src.at("type", "source").string("source.type");
  if (type != "gun") throw JsonError("source.type " + type + " is defined as an interface only (Geant4 program R.10.2)");
  s.particle = src.at("particle", "source").string("source.particle");
  if (src.has("ekin_per_nucleon_MeV")) {
    int a = Nucleons(s.particle);
    if (!a) throw JsonError("source.ekin_per_nucleon_MeV needs a light ion (proton, deuteron, triton, He3, alpha)");
    s.energy_MeV = a * src.obj.at("ekin_per_nucleon_MeV").number("source.ekin_per_nucleon_MeV");
  } else {
    s.energy_MeV = optNumber(src, "energy_MeV", 0, "source");
  }
  if (src.has("position_mm")) s.position_mm = triple(src.obj.at("position_mm"), "source.position_mm");
  if (src.has("direction")) s.direction = triple(src.obj.at("direction"), "source.direction");
  if (src.has("cycle"))
    for (const auto& cv : src.obj.at("cycle").array("source.cycle"))
      s.cycle.push_back({cv.at("energy_MeV", "source.cycle").number("source.cycle.energy_MeV"),
                         triple(cv.at("direction", "source.cycle"), "source.cycle.direction")});
  if (s.cycle.empty() && !(s.energy_MeV > 0)) throw JsonError("source needs energy_MeV, ekin_per_nucleon_MeV or cycle");

  const Value& r = root.at("run", "spec");
  s.events = static_cast<long>(r.at("events", "run").number("run.events"));
  s.first_event = static_cast<long>(optNumber(r, "first_event", 0, "run"));
  s.chunk = static_cast<int>(optNumber(r, "chunk", 0, "run"));
  const auto& seeds = r.at("seeds", "run").array("run.seeds");
  if (seeds.size() != 2) throw JsonError("run.seeds must have two integers");
  s.seeds = {static_cast<long>(seeds[0].number("run.seeds")), static_cast<long>(seeds[1].number("run.seeds"))};
  s.run_manager = optString(r, "run_manager", "serial", "run");
  s.threads = static_cast<int>(optNumber(r, "threads", 1, "run"));
  if (r.at("seeding", "run").string("run.seeding") != "per-event") throw JsonError("run.seeding must be per-event");
  s.logical_run_seed = static_cast<long long>(r.at("logical_run_seed", "run").number("run.logical_run_seed"));
  if (s.events < 1) throw JsonError("run.events must be at least 1");
  if (s.first_event < 0 || s.first_event + s.events - 1 > 2147483647L)
    throw JsonError("run.first_event + run.events - 1 must fit a 32-bit event number");
  if (s.logical_run_seed < 1) throw JsonError("run.logical_run_seed must be a positive integer");
  if (s.run_manager != "serial" && s.run_manager != "mt") throw JsonError("run.run_manager must be serial or mt");

  Value empty;
  empty.kind = Value::Kind::Object;
  const Value& o = root.has("output") ? root.obj.at("output") : empty;
  s.overlap_test_points = static_cast<int>(optNumber(o, "overlap_test_points", 0, "output"));
  if (o.has("observables") != o.has("blocks")) throw JsonError("output.observables and output.blocks go together");
  if (o.has("observables")) {
    s.observables = g4sim::ParseObservables(o.obj.at("observables"), "output.observables");
    const Value& b = o.obj.at("blocks");
    s.blocks = static_cast<long>(b.at("blocks", "output.blocks").number("output.blocks.blocks"));
    s.block_size = static_cast<long>(b.at("block_size", "output.blocks").number("output.blocks.block_size"));
    s.block_first_event = static_cast<long>(optNumber(b, "first_event", 0, "output.blocks"));
    if (s.blocks < 2 || s.block_size < 1 || s.block_first_event < 0 || s.block_first_event > s.first_event)
      throw JsonError("output.blocks: blocks at least 2, block_size positive, first_event in [0, run.first_event]");
  }
  s.debug_observable_dump = optBool(o, "debug_observable_dump", false, "output");
  if (s.debug_observable_dump && s.observables.empty())
    throw JsonError("output.debug_observable_dump needs output.observables");
  if (o.has("event_file")) {
    const Value& ef = o.obj.at("event_file");
    s.event_level = optString(ef, "level", "none", "output.event_file");
    s.compression = static_cast<int>(optNumber(ef, "compression", 1, "output.event_file"));
    s.max_events_hits = static_cast<long>(optNumber(ef, "max_events_hits", 100, "output.event_file"));
    if (s.event_level != "none" && s.event_level != "summary" && s.event_level != "crossings" && s.event_level != "hits")
      throw JsonError("output.event_file.level must be none, summary, crossings or hits");
  }
  if (s.event_level == "hits" && s.events > s.max_events_hits)
    throw JsonError("output.event_file.level hits allows at most max_events_hits = " + std::to_string(s.max_events_hits) +
                    " events");
  return s;
}
