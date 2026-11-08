// g4sim/Optics.hh: optical property tables, optical surfaces and their write-back (g4sim plan, Sections 6.2.7, 7.4; S7). Written from
// the Geant4 API (no example code copied or adapted).
//
// The IR's material and surface entries are turned into G4MaterialPropertiesTable, G4OpticalSurface, G4LogicalSkinSurface and
// G4LogicalBorderSurface; OpticalRecord writes back what Geant4 holds, every number in hexadecimal, so the driver compares it with
// the IR (a wrong refractive index is the negative test of Section 15.1). G4SIM_BUILDER_CONTROL=wrong_rindex builds RINDEX 1% high.
#ifndef G4SIM_OPTICS_HH
#define G4SIM_OPTICS_HH

#include <cstdlib>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "G4LogicalBorderSurface.hh"
#include "G4LogicalSkinSurface.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4MaterialPropertiesTable.hh"
#include "G4OpticalParameters.hh"
#include "G4OpticalSurface.hh"
#include "G4SystemOfUnits.hh"
#include "G4VPhysicalVolume.hh"
#include "MiniJson.hh"
#include "SimSummary.hh"

namespace g4sim {

using minijson::Value;

inline double OpticalNumber(const Value& value) { return value.isNumber() ? value.num : std::strtod(value.str.c_str(), nullptr); }

inline bool WrongRindex() {
  const char* control = std::getenv("G4SIM_BUILDER_CONTROL");
  return control && std::string(control) == "wrong_rindex";
}

// A spectrum of the IR, energies in eV, values multiplied by `unit`.
inline void AddSpectrum(G4MaterialPropertiesTable* table, const std::string& key, const Value& spectrum, double unit, double scale = 1.) {
  std::vector<G4double> energies, values;
  for (const auto& e : spectrum.at("energy_eV", key).array("energy_eV")) energies.push_back(OpticalNumber(e) * eV);
  for (const auto& v : spectrum.at("value", key).array("value")) values.push_back(OpticalNumber(v) * unit * scale);
  table->AddProperty(key, energies, values);
}

// The optical table of an IR material, or nullptr when it has none; scintillation constants join it only with components (S7).
inline G4MaterialPropertiesTable* OpticalTable(const Value& definition) {
  const bool scintillates = definition.has("scintillation") && definition.obj.at("scintillation").has("components");
  if (!definition.has("optical") && !scintillates) return nullptr;
  auto* table = new G4MaterialPropertiesTable();
  if (definition.has("optical")) {
    const Value& optical = definition.obj.at("optical");
    AddSpectrum(table, "RINDEX", optical.at("rindex", "optical"), 1., WrongRindex() ? 1.01 : 1.);
    if (optical.has("absorption_length_mm")) AddSpectrum(table, "ABSLENGTH", optical.obj.at("absorption_length_mm"), mm);
    if (optical.has("rayleigh_length_mm")) AddSpectrum(table, "RAYLEIGH", optical.obj.at("rayleigh_length_mm"), mm);
    if (optical.has("mie")) {
      const Value& mie = optical.obj.at("mie");
      AddSpectrum(table, "MIEHG", mie.at("length_mm", "mie"), mm);
      table->AddConstProperty("MIEHG_FORWARD", OpticalNumber(mie.at("forward_g", "mie")));
      table->AddConstProperty("MIEHG_BACKWARD", OpticalNumber(mie.at("backward_g", "mie")));
      table->AddConstProperty("MIEHG_FORWARD_RATIO", OpticalNumber(mie.at("forward_ratio", "mie")));
    }
    if (optical.has("wls")) {
      const Value& wls = optical.obj.at("wls");
      AddSpectrum(table, "WLSABSLENGTH", wls.at("absorption_length_mm", "wls"), mm);
      AddSpectrum(table, "WLSCOMPONENT", wls.at("emission", "wls"), 1.);
      table->AddConstProperty("WLSTIMECONSTANT", OpticalNumber(wls.at("time_constant_ns", "wls")) * ns);
    }
  }
  if (scintillates) {
    const Value& scintillation = definition.obj.at("scintillation");
    table->AddConstProperty("SCINTILLATIONYIELD", OpticalNumber(scintillation.at("yield_per_MeV", "scintillation")) / MeV);
    table->AddConstProperty("RESOLUTIONSCALE", OpticalNumber(scintillation.at("resolution_scale", "scintillation")));
    int number = 0;
    for (const auto& component : scintillation.obj.at("components").array("components")) {
      const std::string k = std::to_string(++number);
      AddSpectrum(table, "SCINTILLATIONCOMPONENT" + k, component.at("spectrum", "component"), 1.);
      table->AddConstProperty("SCINTILLATIONTIMECONSTANT" + k, OpticalNumber(component.at("decay_ns", "component")) * ns);
      table->AddConstProperty("SCINTILLATIONRISETIME" + k, OpticalNumber(component.at("rise_ns", "component")) * ns);
      table->AddConstProperty("SCINTILLATIONYIELD" + k, OpticalNumber(component.at("fraction", "component")));
      // A rise time is used only when finite rise times are on; the driver turns them on whenever a component has one (S7)
    }
  }
  return table;
}

inline G4OpticalSurfaceModel SurfaceModel(const std::string& name) {
  if (name == "glisur") return glisur;
  if (name == "unified") return unified;
  throw std::runtime_error("unknown optical surface model " + name);
}

inline G4OpticalSurfaceFinish SurfaceFinish(const std::string& name) {
  static const std::map<std::string, G4OpticalSurfaceFinish> table = {
      {"polished", polished}, {"polishedfrontpainted", polishedfrontpainted}, {"polishedbackpainted", polishedbackpainted},
      {"ground", ground}, {"groundfrontpainted", groundfrontpainted}, {"groundbackpainted", groundbackpainted}};
  auto found = table.find(name);
  if (found == table.end()) throw std::runtime_error("unknown optical surface finish " + name);
  return found->second;
}

inline G4SurfaceType SurfaceType(const std::string& name) {
  if (name == "dielectric_dielectric") return dielectric_dielectric;
  if (name == "dielectric_metal") return dielectric_metal;
  throw std::runtime_error("unknown optical surface type " + name);
}

// The IR's surfaces: a skin on a logical, or a border between the single physical volumes of two templates placed once.
inline void BuildSurfaces(const Value& surfaces, const std::map<std::string, G4LogicalVolume*>& logicals,
                          const std::map<std::string, std::vector<G4VPhysicalVolume*>>& placed) {
  for (const auto& [name, entry] : surfaces.obj) {
    auto* surface = new G4OpticalSurface(name, SurfaceModel(entry.at("model", name).str), SurfaceFinish(entry.at("finish", name).str),
                                         SurfaceType(entry.at("type", name).str));
    surface->SetSigmaAlpha(entry.has("sigma_alpha_deg") ? OpticalNumber(entry.obj.at("sigma_alpha_deg")) * deg : 0.);  // the constructor would leave 1 rad
    auto* table = new G4MaterialPropertiesTable();
    if (entry.has("reflectivity")) AddSpectrum(table, "REFLECTIVITY", entry.obj.at("reflectivity"), 1.);
    if (entry.has("efficiency")) AddSpectrum(table, "EFFICIENCY", entry.obj.at("efficiency"), 1.);
    surface->SetMaterialPropertiesTable(table);
    if (entry.has("skin")) {
      new G4LogicalSkinSurface(name, logicals.at(entry.obj.at("skin").str), surface);
    } else {
      const auto& pair = entry.at("border", name).array("border");
      const auto& from = placed.at(pair[0].str);
      const auto& to = placed.at(pair[1].str);
      if (from.size() != 1 || to.size() != 1) throw std::runtime_error("border surface " + name + ": its templates are not placed once");
      new G4LogicalBorderSurface(name, from[0], to[0], surface);
    }
  }
}

// The write-back: each material's table and each surface, as Geant4 holds them.
template <class Writer>
std::string SpectrumRecord(const G4MaterialPropertyVector* vector, double unit, Writer& w) {
  std::ostringstream o;
  o << "{\"energy_eV\": [";
  for (std::size_t i = 0; i < vector->GetVectorLength(); ++i) o << (i ? ", " : "") << w.Hex(vector->Energy(i) / eV, true);
  o << "], \"value\": [";
  for (std::size_t i = 0; i < vector->GetVectorLength(); ++i) o << (i ? ", " : "") << w.Hex((*vector)[i] / unit, true);
  o << "]}";
  return o.str();
}

template <class Writer>
std::string TableRecord(const G4MaterialPropertiesTable* table, Writer& w) {
  static const std::map<std::string, double> vectors = {{"RINDEX", 1.}, {"ABSLENGTH", mm}, {"RAYLEIGH", mm}, {"MIEHG", mm}, {"WLSABSLENGTH", mm},
      {"WLSCOMPONENT", 1.}, {"SCINTILLATIONCOMPONENT1", 1.}, {"SCINTILLATIONCOMPONENT2", 1.}, {"SCINTILLATIONCOMPONENT3", 1.},
      {"REFLECTIVITY", 1.}, {"EFFICIENCY", 1.}};
  static const std::map<std::string, double> constants = {{"MIEHG_FORWARD", 1.}, {"MIEHG_BACKWARD", 1.}, {"MIEHG_FORWARD_RATIO", 1.},
      {"WLSTIMECONSTANT", ns}, {"SCINTILLATIONYIELD", 1. / MeV}, {"RESOLUTIONSCALE", 1.}, {"SCINTILLATIONTIMECONSTANT1", ns},
      {"SCINTILLATIONTIMECONSTANT2", ns}, {"SCINTILLATIONTIMECONSTANT3", ns}, {"SCINTILLATIONRISETIME1", ns}, {"SCINTILLATIONRISETIME2", ns},
      {"SCINTILLATIONRISETIME3", ns}, {"SCINTILLATIONYIELD1", 1.}, {"SCINTILLATIONYIELD2", 1.}, {"SCINTILLATIONYIELD3", 1.}};
  std::ostringstream o;
  o << "{";
  bool first = true;
  for (const auto& [key, unit] : vectors) {
    const G4MaterialPropertyVector* vector = table->GetProperty(key.c_str());
    if (!vector) continue;
    o << (first ? "" : ", ") << JsonQuote(key) << ": " << SpectrumRecord(vector, unit, w);
    first = false;
  }
  for (const auto& [key, unit] : constants) {
    if (!table->ConstPropertyExists(key.c_str())) continue;
    o << (first ? "" : ", ") << JsonQuote(key) << ": " << w.Hex(table->GetConstProperty(key.c_str()) / unit, true);
    first = false;
  }
  o << "}";
  return o.str();
}

template <class Writer>
std::string OpticalRecord(Writer& w) {
  std::ostringstream o;
  o << "{\"materials\": {";
  bool first = true;
  for (const G4Material* material : *G4Material::GetMaterialTable()) {
    if (!material->GetMaterialPropertiesTable()) continue;
    o << (first ? "" : ", ") << JsonQuote(material->GetName()) << ": " << TableRecord(material->GetMaterialPropertiesTable(), w);
    first = false;
  }
  o << "}, \"surfaces\": {";
  first = true;
  const auto surface = [&](const std::string& name, const G4OpticalSurface* optical, const std::string& where) {
    o << (first ? "" : ", ") << JsonQuote(name) << ": {" << where << ", \"model\": " << static_cast<int>(optical->GetModel())
      << ", \"finish\": " << static_cast<int>(optical->GetFinish()) << ", \"type\": " << static_cast<int>(optical->GetType())
      << ", \"sigma_alpha_rad\": " << w.Hex(optical->GetSigmaAlpha(), true) << ", \"table\": "
      << (optical->GetMaterialPropertiesTable() ? TableRecord(optical->GetMaterialPropertiesTable(), w) : std::string("{}")) << "}";
    first = false;
  };
  for (const auto& [logical, skin] : *G4LogicalSkinSurface::GetSurfaceTable())
    if (const auto* optical = dynamic_cast<const G4OpticalSurface*>(skin->GetSurfaceProperty()))
      surface(skin->GetName(), optical, "\"skin\": " + JsonQuote(logical->GetName()));
  for (const auto& [volumes, border] : *G4LogicalBorderSurface::GetSurfaceTable())
    if (const auto* optical = dynamic_cast<const G4OpticalSurface*>(border->GetSurfaceProperty()))
      surface(border->GetName(), optical, "\"border\": [" + JsonQuote(volumes.first->GetLogicalVolume()->GetName()) + ", " + JsonQuote(volumes.second->GetLogicalVolume()->GetName()) + "]");
  o << "}}";
  return o.str();
}

}  // namespace g4sim

#endif
