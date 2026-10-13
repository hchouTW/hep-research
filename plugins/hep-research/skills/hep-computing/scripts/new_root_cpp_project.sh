#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $(basename "$0") [--dir DIR] [--force] [--json] [PROJECT_NAME]"
  echo "Create a minimal CMake + ROOT RDataFrame C++ project in DIR (default: ./PROJECT_NAME)."
  echo "PROJECT_NAME (default: root_cpp_analysis) must match ^[A-Za-z_][A-Za-z0-9_]*\$; it names the CMake project."
  echo "An existing non-empty DIR is refused unless --force is given (then only the generated files are rewritten)."
  echo "The generated program writes output.root and pt.pdf into an output folder (third argument, default output/)."
  echo "--json: print one JSON object with \"status\" (created, error) instead of text."
  echo "Exit codes: 0 created, 2 bad usage, invalid name or refused target."
}

JSON=0
FORCE=0
DIR=""
NAME=""
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --json) JSON=1; shift ;;
    --force) FORCE=1; shift ;;
    --dir)
      [ $# -ge 2 ] || { echo "ERROR: --dir needs a value" >&2; usage >&2; exit 2; }
      DIR="$2"; shift 2 ;;
    --dir=*) DIR="${1#--dir=}"; shift ;;
    -*) echo "ERROR: project name must not start with '-': $1" >&2; usage >&2; exit 2 ;;
    *)
      [ -z "$NAME" ] || { echo "ERROR: more than one project name: $NAME $1" >&2; exit 2; }
      NAME="$1"; shift ;;
  esac
done

json_str() {
  printf '"%s"' "$(printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr '\n\t\r' '   ')"
}

refuse() {
  if [ "$JSON" -eq 1 ]; then
    printf '{"status": "error", "error": %s}\n' "$(json_str "$1")"
  else
    echo "ERROR: $1" >&2
  fi
  exit 2
}

PROJECT_NAME="${NAME:-root_cpp_analysis}"
if ! printf '%s' "$PROJECT_NAME" | grep -Eq '^[A-Za-z_][A-Za-z0-9_]*$'; then
  refuse "project name must match ^[A-Za-z_][A-Za-z0-9_]*\$ (letters, digits, underscore): $PROJECT_NAME"
fi
TARGET="${DIR:-./$PROJECT_NAME}"
if [ -e "$TARGET" ] && [ ! -d "$TARGET" ]; then
  refuse "target exists and is not a folder: $TARGET"
fi
if [ -d "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ] && [ "$FORCE" -ne 1 ]; then
  refuse "target folder is not empty: $TARGET (use --force to rewrite the generated files)"
fi
mkdir -p "$TARGET/src" || refuse "cannot create $TARGET/src"

cat > "$TARGET/CMakeLists.txt" <<CMAKE
cmake_minimum_required(VERSION 3.16)
project(${PROJECT_NAME} LANGUAGES CXX)

find_package(ROOT REQUIRED COMPONENTS RIO Tree Hist Gpad ROOTDataFrame)
# the C++ standard ROOT was built with (C++17 for ROOT 6.38); do not set a second one
set(CMAKE_CXX_STANDARD \${ROOT_CXX_STANDARD})
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(analysis src/analysis.cpp)
target_link_libraries(analysis PRIVATE ROOT::RIO ROOT::Tree ROOT::Hist ROOT::Gpad ROOT::ROOTDataFrame)
CMAKE

cat > "$TARGET/src/analysis.cpp" <<'CPP'
#include <ROOT/RDataFrame.hxx>
#include <TCanvas.h>
#include <TFile.h>
#include <TROOT.h>

#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " input.root [tree] [output_dir]\n";
        return 2;
    }

    const std::string input = argv[1];
    const std::string treeName = argc > 2 ? argv[2] : "Events";
    const std::filesystem::path outDir = argc > 3 ? argv[3] : "output";
    const std::string branchName = "pt";

    if (!std::filesystem::exists(input)) {
        std::cerr << "ERROR: input file does not exist: " << input << "\n";
        return 2;
    }

    try {
        gROOT->SetBatch(kTRUE);
        std::filesystem::create_directories(outDir);
        const std::string output = (outDir / "output.root").string();
        const std::string figure = (outDir / "pt.pdf").string();

        ROOT::RDataFrame df(treeName, input);
        auto h = df.Histo1D(
            {"h_pt", "p_{T};p_{T} [GeV];Events", 50, 0.0, 200.0},
            branchName
        );

        TFile out(output.c_str(), "RECREATE");
        if (out.IsZombie()) {
            throw std::runtime_error("Could not create output file: " + output);
        }

        h->Write();

        TCanvas c("c_pt", "c_pt", 800, 600);
        h->Draw("HIST");
        c.SaveAs(figure.c_str());
        c.Write();

        out.Close();
        std::cout << "Wrote " << output << "\n";
        std::cout << "Wrote " << figure << "\n";
    } catch (const std::exception& ex) {
        std::cerr << "ERROR: " << ex.what() << "\n";
        return 1;
    }

    return 0;
}
CPP

q() { printf '%q' "$1"; }
BUILD="cmake -S $(q "$TARGET") -B $(q "$TARGET/build") && cmake --build $(q "$TARGET/build") -j"
if [ "$JSON" -eq 1 ]; then
  printf '{"status": "created", "project": %s, "dir": %s, "build": %s}\n' \
    "$(json_str "$PROJECT_NAME")" "$(json_str "$TARGET")" "$(json_str "$BUILD")"
else
  echo "Created $TARGET"
  echo "Build with: $BUILD"
fi
