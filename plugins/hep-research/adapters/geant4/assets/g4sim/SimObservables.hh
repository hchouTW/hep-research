// g4sim/SimObservables.hh: reading simulation-observables/1 declarations (contracts/schemas/simulation_observables.json)
// from MiniJson values into SimSummary.hh's ObservableDecl (adapters/geant4, Geant4 program A2.3). C++17 standard
// library only. The full schema check is done in Python before a run (geant4_run.py); this reader takes the fields the
// accumulators need and ignores the estimator fields (tolerance_mode, tolerance, estimator, quantile, threshold_index).
#ifndef G4SIM_SIMOBSERVABLES_HH
#define G4SIM_SIMOBSERVABLES_HH

#include <set>
#include <string>
#include <vector>

#include "MiniJson.hh"
#include "SimSummary.hh"

namespace g4sim {

inline Cell ToCell(const minijson::Value& v, const std::string& where) {
  return v.isString() ? Cell::Text(v.str) : Cell::Number(v.number(where));
}

inline std::vector<ObservableDecl> ParseObservables(const minijson::Value& arr, const std::string& where) {
  std::vector<ObservableDecl> out;
  std::set<std::string> names;
  for (const auto& o : arr.array(where)) {
    ObservableDecl d;
    d.name = o.at("name", where).string(where + ".name");
    if (!names.insert(d.name).second) throw minijson::JsonError(where + ": observable " + d.name + " is declared twice");
    d.source_column = o.at("source_column", where).string(where + ".source_column");
    if (o.has("selection"))
      for (const auto& c : o.obj.at("selection").array(where + ".selection"))
        d.selection.push_back({c.at("column", where).string(where + ".selection.column"),
                               c.at("op", where).string(where + ".selection.op"),
                               ToCell(c.at("value", where), where + ".selection.value")});
    const minijson::Value& b = o.at("bins", where);
    d.lo = b.at("lo", where).number(where + ".bins.lo");
    d.hi = b.at("hi", where).number(where + ".bins.hi");
    d.width = b.at("width", where).number(where + ".bins.width");
    if (o.has("thresholds"))
      for (const auto& t : o.obj.at("thresholds").array(where + ".thresholds")) d.thresholds.push_back(t.number(where));
    if (o.has("values")) d.values = o.obj.at("values").boolean(where + ".values");
    if (o.has("values_max")) {
      d.valuesMax = static_cast<long>(o.obj.at("values_max").number(where + ".values_max"));
      if (d.valuesMax < 1) throw minijson::JsonError(where + ": values_max must be a positive integer");
    }
    BinCount(d);  // throws SummaryError on a binning that is not a positive whole number of bins
    out.push_back(d);
  }
  if (out.empty()) throw minijson::JsonError(where + " must declare at least one observable");
  return out;
}

// The per-event columns an observable list reads (source columns and selection columns), sorted.
inline std::vector<std::string> NeededColumns(const std::vector<ObservableDecl>& obs) {
  std::set<std::string> cols;
  for (const auto& o : obs) {
    cols.insert(o.source_column);
    for (const auto& c : o.selection) cols.insert(c.column);
  }
  return {cols.begin(), cols.end()};
}

}  // namespace g4sim

#endif
