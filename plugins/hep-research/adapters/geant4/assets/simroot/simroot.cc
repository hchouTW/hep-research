// simroot: read element_sim's per-event ROOT files (element_sim.events/1) through Geant4's G4RootAnalysisReader
// (Geant4 program B1.5). Links only Geant4's analysis library; creates no run manager. Written from the Geant4 11.4 API.
//
// Usage:
//   simroot info FILE...                              row counts and columns of each ntuple, the run rows (JSON)
//   simroot dump FILE... --ntuple N [--columns a,b] [--events A:B] [--out PATH]
//                                                     rows sorted by key as CSV (floats %.17g), stdout or PATH
//   simroot hash FILE...                              content_sha256 (JSON)
// Several files are read as one logical run (the same logical-run seed, column map, program, program sources and
// Geant4 version in every run row, else refused): rows of each ntuple are joined and sorted by key; the processes rows
// are deduplicated by process_id (the same number must name the same process); a duplicate key elsewhere is refused.
// Every file must have the same event-file version and column lists. The run ntuple (one row per file, differing per
// job) is never part of the content hash: content_sha256 is the sha256 of, for each of processes, events, deposits,
// crossings and hits that the level writes, a line "#<ntuple>", the column list "name:T,...", and one line per row
// in key order with integers in decimal, doubles as Python float.hex() and strings JSON-quoted, comma-separated.
// --events A:B keeps rows with A <= event_id < B (dump only). Geant4's own messages go to stderr; stdout carries
// only the result. Exit codes (core/status.py): 0 ok; 2 a file is missing, unreadable or inconsistent, or bad usage.
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include "G4RootAnalysisReader.hh"
#include "G4coutDestination.hh"
#include "G4ios.hh"
#include "SimHash.hh"
#include "SimSummary.hh"

namespace {

using g4sim::JsonQuote;

struct Fail : std::runtime_error {
  using std::runtime_error::runtime_error;
};

class ToStderr : public G4coutDestination {
 public:
  G4int ReceiveG4cout(const G4String& msg) override {
    std::cerr << msg;
    return 0;
  }
  G4int ReceiveG4cerr(const G4String& msg) override {
    std::cerr << msg;
    return 0;
  }
};

struct Column {
  std::string name;
  char type;
};

struct Cell {
  long long i = 0;
  double d = 0.;
  std::string s;
};

using Row = std::vector<Cell>;

struct Table {
  std::vector<Column> columns;
  std::vector<Row> rows;
};

const std::vector<Column> kRunColumns = {
    {"spec_sha256", 'S'},      {"column_map_sha256", 'S'}, {"program", 'S'},           {"program_sources_sha256", 'S'},
    {"geant4_version", 'S'},   {"logical_run_seed", 'I'},  {"first_event", 'I'},       {"last_event", 'I'},
    {"event_file_version", 'S'}, {"level", 'S'},           {"columns_processes", 'S'}, {"columns_events", 'S'},
    {"columns_deposits", 'S'}, {"columns_crossings", 'S'}, {"columns_hits", 'S'}};
const char* kContent[] = {"processes", "events", "deposits", "crossings", "hits"};

const std::map<std::string, std::vector<std::string>>& Keys() {
  static const std::map<std::string, std::vector<std::string>> keys = {
      {"processes", {"process_id"}},
      {"events", {"event_id"}},
      {"deposits", {"event_id", "volume_id", "copy"}},
      {"crossings", {"event_id", "plane_id", "copy", "track_id"}},
      {"hits", {"event_id", "track_id", "step_index"}}};
  return keys;
}

std::vector<Column> ParseColumns(const std::string& list) {
  std::vector<Column> out;
  std::stringstream in(list);
  std::string item;
  while (std::getline(in, item, ',')) {
    auto colon = item.rfind(':');
    if (colon == std::string::npos || colon + 2 != item.size() || std::string("IDS").find(item.back()) == std::string::npos)
      throw Fail("malformed column list entry " + item);
    out.push_back({item.substr(0, colon), item.back()});
  }
  return out;
}

// Reads every row of one ntuple of one file, binding the columns given.
Table ReadNtuple(G4RootAnalysisReader* reader, const std::string& file, const std::string& name,
                 const std::vector<Column>& columns) {
  int id = reader->GetNtuple(name, file);
  if (id < 0) throw Fail(file + ": no ntuple " + name);
  Table t;
  t.columns = columns;
  std::vector<G4int> ints(columns.size());
  std::vector<G4double> doubles(columns.size());
  std::vector<G4String> strings(columns.size());
  for (std::size_t c = 0; c < columns.size(); ++c) {
    bool ok = columns[c].type == 'I'   ? reader->SetNtupleIColumn(id, columns[c].name, ints[c])
              : columns[c].type == 'D' ? reader->SetNtupleDColumn(id, columns[c].name, doubles[c])
                                       : reader->SetNtupleSColumn(id, columns[c].name, strings[c]);
    if (!ok) throw Fail(file + ": ntuple " + name + " has no column " + columns[c].name);
  }
  while (reader->GetNtupleRow(id)) {
    Row r(columns.size());
    for (std::size_t c = 0; c < columns.size(); ++c) {
      r[c].i = ints[c];
      r[c].d = doubles[c];
      r[c].s = strings[c];
    }
    t.rows.push_back(r);
  }
  return t;
}

struct LogicalRun {
  std::vector<std::string> files;
  std::vector<Table> runRows;           // one table per file
  std::map<std::string, Table> tables;  // joined content ntuples
  std::string level;
};

int Index(const std::vector<Column>& cols, const std::string& name) {
  for (std::size_t i = 0; i < cols.size(); ++i)
    if (cols[i].name == name) return static_cast<int>(i);
  return -1;
}

std::string Text(const Cell& c, char type, bool hex) {
  if (type == 'I') return std::to_string(c.i);
  if (type == 'S') return hex ? JsonQuote(c.s) : c.s;
  if (hex) return g4sim::PyFloatHex(c.d);
  char buf[40];
  std::snprintf(buf, sizeof buf, "%.17g", c.d);
  return buf;
}

void SortByKey(const std::string& name, Table& t) {
  std::vector<int> key;
  for (const auto& k : Keys().at(name)) key.push_back(Index(t.columns, k));
  std::stable_sort(t.rows.begin(), t.rows.end(), [&](const Row& a, const Row& b) {
    for (int k : key)
      if (a[k].i != b[k].i) return a[k].i < b[k].i;
    return false;
  });
}

LogicalRun Read(const std::vector<std::string>& files) {
  LogicalRun run;
  run.files = files;
  std::map<std::string, std::string> lists;
  for (const auto& f : files) {
    if (!std::ifstream(f)) throw Fail("cannot read " + f);
    // a fresh reader per file: its ntuple ids and column bindings belong to the file it opened
    auto* reader = G4RootAnalysisReader::Instance();
    reader->SetVerboseLevel(0);
    Table rr = ReadNtuple(reader, f, "run", kRunColumns);
    if (rr.rows.size() != 1) throw Fail(f + ": the run ntuple has " + std::to_string(rr.rows.size()) + " rows, not 1");
    const Row& r = rr.rows[0];
    if (r[Index(kRunColumns, "event_file_version")].s != "element_sim.events/1")
      throw Fail(f + ": event_file_version is not element_sim.events/1");
    for (const char* k : {"logical_run_seed", "column_map_sha256", "program", "program_sources_sha256",
                          "geant4_version"}) {
      const Row& first = run.runRows.empty() ? r : run.runRows[0].rows[0];
      int c = Index(kRunColumns, k);
      if (first[c].s != r[c].s || first[c].i != r[c].i)
        throw Fail(f + ": " + k + " differs from the first file: not one logical run");
    }
    std::string level = r[Index(kRunColumns, "level")].s;
    if (!run.level.empty() && level != run.level) throw Fail(f + ": level " + level + " differs from " + run.level);
    run.level = level;
    for (const char* n : kContent) {
      std::string list = r[Index(kRunColumns, std::string("columns_") + n)].s;
      if (lists.count(n) && lists[n] != list) throw Fail(f + ": the columns of " + n + " differ between files");
      lists[n] = list;
      if (list.empty()) continue;
      Table t = ReadNtuple(reader, f, n, ParseColumns(list));
      Table& all = run.tables[n];
      all.columns = t.columns;
      all.rows.insert(all.rows.end(), t.rows.begin(), t.rows.end());
    }
    run.runRows.push_back(rr);
    reader->CloseFiles(true);
  }
  for (auto& [name, t] : run.tables) {
    SortByKey(name, t);
    std::vector<int> key;
    for (const auto& k : Keys().at(name)) key.push_back(Index(t.columns, k));
    std::vector<Row> kept;
    for (const auto& row : t.rows) {
      bool same = !kept.empty();
      for (int k : key) same = same && kept.back()[k].i == row[k].i;
      if (!same) {
        kept.push_back(row);
        continue;
      }
      if (name != "processes") throw Fail("ntuple " + name + ": a key appears twice (overlapping event ranges?)");
      if (kept.back()[Index(t.columns, "name")].s != row[Index(t.columns, "name")].s)
        throw Fail("process_id " + std::to_string(row[key[0]].i) + " names two processes in different files");
    }
    t.rows = kept;
  }
  return run;
}

std::string Hash(const LogicalRun& run, std::map<std::string, std::string>& perNtuple) {
  g4sim::Sha256 all;
  for (const char* n : kContent) {
    auto it = run.tables.find(n);
    if (it == run.tables.end()) continue;
    const Table& t = it->second;
    std::string head = std::string("#") + n + "\n";
    for (std::size_t c = 0; c < t.columns.size(); ++c)
      head += (c ? "," : "") + t.columns[c].name + ":" + t.columns[c].type;
    head += "\n";
    g4sim::Sha256 one;
    all.Update(head);
    one.Update(head);
    for (const auto& r : t.rows) {
      std::string line;
      for (std::size_t c = 0; c < t.columns.size(); ++c) line += (c ? "," : "") + Text(r[c], t.columns[c].type, true);
      line += "\n";
      all.Update(line);
      one.Update(line);
    }
    perNtuple[n] = g4sim::Sha256::Hex(one.Digest());
  }
  return g4sim::Sha256::Hex(all.Digest());
}

std::string Csv(const std::string& s) {
  if (s.find_first_of(",\"\n") == std::string::npos) return s;
  std::string out = "\"";
  for (char c : s) out += c == '"' ? std::string("\"\"") : std::string(1, c);
  return out + "\"";
}

int Usage(const std::string& why) {
  std::cout << "{\"status\": \"rejected\", \"error\": " << JsonQuote(why) << "}" << std::endl;
  std::cerr << "usage: simroot info FILE... | simroot dump FILE... --ntuple N [--columns a,b] [--events A:B] "
               "[--out PATH] | simroot hash FILE..."
            << std::endl;
  return 2;
}

int Help() {
  std::cout << "simroot: read element_sim per-event ROOT files (element_sim.events/1)\n"
               "  simroot info FILE...\n"
               "  simroot dump FILE... --ntuple N [--columns a,b] [--events A:B] [--out PATH]\n"
               "  simroot hash FILE...\n"
               "Exit codes: 0 ok; 2 a file is missing, unreadable or inconsistent, or bad usage.\n";
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  ToStderr sink;
  G4iosSetDestination(&sink);
  std::vector<std::string> args(argv + 1, argv + argc);
  if (args.empty()) return Usage("no subcommand");
  if (args[0] == "--help" || args[0] == "-h") return Help();
  std::string cmd = args[0], ntuple, columns, events, out;
  std::vector<std::string> files;
  for (std::size_t i = 1; i < args.size(); ++i) {
    const std::string& a = args[i];
    auto value = [&](std::string& dst) {
      if (i + 1 >= args.size()) throw Fail(a + " needs a value");
      dst = args[++i];
    };
    try {
      if (a == "--ntuple") value(ntuple);
      else if (a == "--columns") value(columns);
      else if (a == "--events") value(events);
      else if (a == "--out") value(out);
      else if (a.rfind("--", 0) == 0) return Usage("unknown option " + a);
      else files.push_back(a);
    } catch (const Fail& e) {
      return Usage(e.what());
    }
  }
  if (cmd != "info" && cmd != "dump" && cmd != "hash") return Usage("unknown subcommand " + cmd);
  if (files.empty()) return Usage("no input file");
  try {
    LogicalRun run = Read(files);
    if (cmd == "hash") {
      std::map<std::string, std::string> per;
      std::string h = Hash(run, per);
      std::cout << "{\"status\": \"ok\", \"content_sha256\": " << JsonQuote(h) << ", \"files\": " << files.size()
                << ", \"level\": " << JsonQuote(run.level) << ", \"ntuples\": {";
      bool first = true;
      for (const auto& [n, sha] : per) {
        std::cout << (first ? "" : ", ") << JsonQuote(n) << ": {\"rows\": " << run.tables.at(n).rows.size()
                  << ", \"sha256\": " << JsonQuote(sha) << "}";
        first = false;
      }
      std::cout << "}}" << std::endl;
      return 0;
    }
    if (cmd == "info") {
      std::cout << "{\"status\": \"ok\", \"level\": " << JsonQuote(run.level) << ", \"ntuples\": {";
      bool first = true;
      for (const auto& [n, t] : run.tables) {
        std::cout << (first ? "" : ", ") << JsonQuote(n) << ": {\"rows\": " << t.rows.size() << ", \"columns\": [";
        for (std::size_t c = 0; c < t.columns.size(); ++c)
          std::cout << (c ? ", " : "") << JsonQuote(t.columns[c].name + ":" + t.columns[c].type);
        std::cout << "]}";
        first = false;
      }
      std::cout << "}, \"run\": [";
      for (std::size_t f = 0; f < run.runRows.size(); ++f) {
        const Row& r = run.runRows[f].rows[0];
        std::cout << (f ? ", " : "") << "{\"file\": " << JsonQuote(files[f]);
        for (std::size_t c = 0; c < kRunColumns.size(); ++c)
          std::cout << ", " << JsonQuote(kRunColumns[c].name) << ": "
                    << (kRunColumns[c].type == 'I' ? std::to_string(r[c].i) : JsonQuote(r[c].s));
        std::cout << "}";
      }
      std::cout << "]}" << std::endl;
      return 0;
    }
    // dump
    if (ntuple.empty()) return Usage("dump needs --ntuple");
    auto it = run.tables.find(ntuple);
    if (it == run.tables.end()) return Usage("the files have no ntuple " + ntuple + " at level " + run.level);
    const Table& t = it->second;
    std::vector<int> pick;
    if (columns.empty()) {
      for (std::size_t c = 0; c < t.columns.size(); ++c) pick.push_back(static_cast<int>(c));
    } else {
      std::stringstream in(columns);
      std::string c;
      while (std::getline(in, c, ',')) {
        int k = Index(t.columns, c);
        if (k < 0) return Usage("ntuple " + ntuple + " has no column " + c);
        pick.push_back(k);
      }
    }
    long long lo = 0, hi = -1;
    bool range = !events.empty();
    if (range) {
      auto colon = events.find(':');
      if (colon == std::string::npos) return Usage("--events takes A:B");
      try {
        lo = std::stoll(events.substr(0, colon));
        hi = std::stoll(events.substr(colon + 1));
      } catch (const std::exception&) {
        return Usage("--events takes A:B with integers");
      }
    }
    int ev = Index(t.columns, "event_id");
    if (range && ev < 0) return Usage("--events: ntuple " + ntuple + " has no event_id");
    std::ofstream file;
    if (!out.empty()) {
      file.open(out, std::ios::binary);
      if (!file) throw Fail("cannot write " + out);
    }
    std::ostream& o = out.empty() ? std::cout : file;
    for (std::size_t c = 0; c < pick.size(); ++c) o << (c ? "," : "") << t.columns[pick[c]].name;
    o << "\n";
    std::size_t n = 0;
    for (const auto& r : t.rows) {
      if (range && (r[ev].i < lo || r[ev].i >= hi)) continue;
      for (std::size_t c = 0; c < pick.size(); ++c) o << (c ? "," : "") << Csv(Text(r[pick[c]], t.columns[pick[c]].type, false));
      o << "\n";
      ++n;
    }
    if (!out.empty())
      std::cout << "{\"status\": \"ok\", \"out\": " << JsonQuote(out) << ", \"rows\": " << n << "}" << std::endl;
    return 0;
  } catch (const Fail& e) {
    std::cout << "{\"status\": \"rejected\", \"error\": " << JsonQuote(e.what()) << "}" << std::endl;
    return 2;
  }
}
