#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="${1:-root_cpp_analysis}"
mkdir -p "$PROJECT_NAME/src"

cat > "$PROJECT_NAME/CMakeLists.txt" <<CMAKE
cmake_minimum_required(VERSION 3.16)
project(${PROJECT_NAME} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ROOT REQUIRED COMPONENTS RIO Tree Hist Graf Graf3d Gpad ROOTDataFrame)

add_executable(analysis src/analysis.cpp)
target_include_directories(analysis PRIVATE \${ROOT_INCLUDE_DIRS})
target_link_libraries(analysis PRIVATE \${ROOT_LIBRARIES})
CMAKE

cat > "$PROJECT_NAME/src/analysis.cpp" <<'CPP'
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
        std::cerr << "Usage: " << argv[0] << " input.root [output.root]\n";
        return 1;
    }

    const std::string input = argv[1];
    const std::string output = argc > 2 ? argv[2] : "output.root";
    const std::string treeName = "Events";
    const std::string branchName = "pt";

    if (!std::filesystem::exists(input)) {
        std::cerr << "ERROR: input file does not exist: " << input << "\n";
        return 1;
    }

    try {
        gROOT->SetBatch(kTRUE);

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
        c.SaveAs("pt.pdf");
        c.Write();

        out.Close();
        std::cout << "Wrote " << output << "\n";
        std::cout << "Wrote pt.pdf\n";
    } catch (const std::exception& ex) {
        std::cerr << "ERROR: " << ex.what() << "\n";
        return 2;
    }

    return 0;
}
CPP

echo "Created $PROJECT_NAME"
echo "Build with: cmake -S $PROJECT_NAME -B $PROJECT_NAME/build && cmake --build $PROJECT_NAME/build -j"
