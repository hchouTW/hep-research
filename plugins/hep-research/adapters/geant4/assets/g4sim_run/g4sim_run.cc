// g4sim_run: the g4sim execution program (g4sim plan, Section 8). Written from the Geant4 11.4 API; no example code copied or adapted.
//
// Usage: g4sim_run IR.json OLD_SPEC.json   (in the run folder). S2 legacy mode: the IR's legacy block gives the volume tree, and the old
// specification, merged back from the three specifications by g4sim_translate.py, configures the legacy observer of its program.
// Exit codes as the old programs: 0 ok, 1 the run failed, 2 refused.
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#include "MiniJson.hh"

namespace legacy_element { int Run(const char* specPath, const minijson::Value& legacy); }
namespace legacy_layered { int Run(const char* specPath, const minijson::Value& legacy); }

static minijson::Value ReadJson(const char* path) {
  std::ifstream in(path);
  if (!in) throw minijson::JsonError(std::string("cannot read ") + path);
  std::stringstream text;
  text << in.rdbuf();
  return minijson::parse(text.str());
}

int main(int argc, char** argv) {
  if (argc != 3) {
    std::cerr << "usage: g4sim_run IR.json OLD_SPEC.json" << std::endl;
    return 2;
  }
  try {
    const minijson::Value ir = ReadJson(argv[1]);
    const minijson::Value old = ReadJson(argv[2]);
    const minijson::Value& legacy = ir.at("physical", "ir").at("legacy", "ir.physical");
    const std::string& format = old.at("schema", "old specification").string("schema");
    if (format.rfind("element_sim", 0) == 0) return legacy_element::Run(argv[2], legacy);
    if (format.rfind("layered_sim", 0) == 0) return legacy_layered::Run(argv[2], legacy);
    std::cerr << "unknown old specification " << format << std::endl;
  } catch (const std::exception& error) {
    std::cerr << error.what() << std::endl;
  }
  return 2;
}
