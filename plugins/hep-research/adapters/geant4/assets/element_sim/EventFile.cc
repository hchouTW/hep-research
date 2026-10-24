#include "EventFile.hh"

#include "G4AnalysisManager.hh"

std::vector<NtupleDef> EventFileNtuples(const Spec& spec) {
  std::vector<NtupleDef> defs;
  if (!spec.Level("summary")) return defs;
  defs.push_back({"run",
                  {{"spec_sha256", 'S'},
                   {"column_map_sha256", 'S'},
                   {"program", 'S'},
                   {"program_sources_sha256", 'S'},
                   {"geant4_version", 'S'},
                   {"logical_run_seed", 'I'},
                   {"first_event", 'I'},
                   {"last_event", 'I'},
                   {"event_file_version", 'S'},
                   {"level", 'S'},
                   {"columns_processes", 'S'},
                   {"columns_events", 'S'},
                   {"columns_deposits", 'S'},
                   {"columns_crossings", 'S'},
                   {"columns_hits", 'S'}}});
  defs.push_back({"processes", {{"process_id", 'I'}, {"name", 'S'}}});
  NtupleDef ev{"events",
               {{"event_id", 'I'},
                {"primary_pdg", 'I'},
                {"primary_ekin_MeV", 'D'},
                {"primary_x_mm", 'D'},
                {"primary_y_mm", 'D'},
                {"primary_z_mm", 'D'},
                {"primary_dx", 'D'},
                {"primary_dy", 'D'},
                {"primary_dz", 'D'}}};
  for (const auto& e : spec.elements) ev.columns.push_back({"edep_" + e.name + "_MeV", 'D'});
  for (const auto& e : spec.elements) ev.columns.push_back({"plen_" + e.name + "_mm", 'D'});
  ev.columns.push_back({"edep_world_MeV", 'D'});
  ev.columns.push_back({"escape_world_MeV", 'D'});
  if (spec.CalorimeterIndex() >= 0)
    for (const char* c : {"leak_rear_MeV", "leak_front_MeV", "leak_lateral_MeV"}) ev.columns.push_back({c, 'D'});
  ev.columns.push_back({"flags", 'I'});
  defs.push_back(ev);
  defs.push_back({"deposits",
                  {{"event_id", 'I'}, {"volume_id", 'I'}, {"copy", 'I'}, {"edep_MeV", 'D'}, {"edep_charged_MeV", 'D'}}});
  if (spec.Level("crossings"))
    defs.push_back({"crossings",
                    {{"event_id", 'I'},
                     {"plane_id", 'I'},
                     {"copy", 'I'},
                     {"track_id", 'I'},
                     {"parent_id", 'I'},
                     {"pdg", 'I'},
                     {"x_mm", 'D'},
                     {"y_mm", 'D'},
                     {"z_mm", 'D'},
                     {"dx", 'D'},
                     {"dy", 'D'},
                     {"dz", 'D'},
                     {"ekin_MeV", 'D'},
                     {"t_ns", 'D'},
                     {"edep_MeV", 'D'}}});
  if (spec.Level("hits"))
    defs.push_back({"hits",
                    {{"event_id", 'I'},
                     {"track_id", 'I'},
                     {"step_index", 'I'},
                     {"parent_id", 'I'},
                     {"pdg", 'I'},
                     {"volume_id", 'I'},
                     {"copy", 'I'},
                     {"pre_x_mm", 'D'},
                     {"pre_y_mm", 'D'},
                     {"pre_z_mm", 'D'},
                     {"post_x_mm", 'D'},
                     {"post_y_mm", 'D'},
                     {"post_z_mm", 'D'},
                     {"t_ns", 'D'},
                     {"edep_MeV", 'D'},
                     {"step_mm", 'D'},
                     {"process_id", 'I'}}});
  return defs;
}

std::string ColumnList(const NtupleDef& def) {
  std::string s;
  for (std::size_t i = 0; i < def.columns.size(); ++i)
    s += (i ? "," : "") + def.columns[i].name + ":" + def.columns[i].type;
  return s;
}

EventFile::EventFile(const Spec& spec) : fSpec(spec), fEnabled(spec.Level("summary")), fDefs(EventFileNtuples(spec)) {}

void EventFile::Book() {
  if (!fEnabled) return;
  auto* am = G4AnalysisManager::Instance();
  am->SetDefaultFileType("root");
  am->SetVerboseLevel(0);
  am->SetNtupleMerging(true);
  am->SetCompressionLevel(fSpec.compression);
  for (const auto& d : fDefs) {
    int id = am->CreateNtuple(d.name, d.name);
    for (const auto& c : d.columns) {
      if (c.type == 'I') am->CreateNtupleIColumn(id, c.name);
      else if (c.type == 'D') am->CreateNtupleDColumn(id, c.name);
      else am->CreateNtupleSColumn(id, c.name);
    }
    am->FinishNtuple(id);
    fIds.push_back(id);
  }
}

void EventFile::Open() {
  if (fEnabled) G4AnalysisManager::Instance()->OpenFile(fSpec.event_file);
}

void EventFile::Close() {
  if (!fEnabled) return;
  auto* am = G4AnalysisManager::Instance();
  am->Write();
  am->CloseFile();
}

int EventFile::Id(const std::string& ntuple) const {
  for (std::size_t i = 0; i < fDefs.size(); ++i)
    if (fDefs[i].name == ntuple) return fIds.empty() ? -1 : fIds[i];
  return -1;
}
