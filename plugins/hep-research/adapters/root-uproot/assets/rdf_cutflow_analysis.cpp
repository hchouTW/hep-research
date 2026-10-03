#include <ROOT/RDataFrame.hxx>
#include <TFile.h>
#include <TROOT.h>
#include <TTree.h>

#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

struct Options {
    std::vector<std::string> inputs;
    std::string tree = "Events";
    fs::path output = "histograms.root";
};

Options parse_args(int argc, char** argv) {
    Options opts;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--input" && i + 1 < argc) {
            opts.inputs.emplace_back(argv[++i]);
        } else if (arg == "--tree" && i + 1 < argc) {
            opts.tree = argv[++i];
        } else if (arg == "--output" && i + 1 < argc) {
            opts.output = argv[++i];
        } else {
            throw std::runtime_error("Unknown or incomplete argument: " + arg);
        }
    }

    if (opts.inputs.empty()) {
        throw std::runtime_error("At least one --input file is required");
    }
    return opts;
}

void validate_inputs(const Options& opts) {
    const std::vector<std::string> required_branches = {
        "nMuon",
        "Muon_pt",
        "Muon_eta",
        "event_weight",
    };

    for (const auto& input : opts.inputs) {
        if (!fs::exists(input)) {
            throw std::runtime_error("Input file does not exist: " + input);
        }
        auto file = std::unique_ptr<TFile>(TFile::Open(input.c_str(), "READ"));
        if (!file || file->IsZombie()) {
            throw std::runtime_error("Could not open input file: " + input);
        }
        auto* tree = file->Get<TTree>(opts.tree.c_str());
        if (!tree) {
            throw std::runtime_error("Tree '" + opts.tree + "' not found in " + input);
        }
        for (const auto& branch : required_branches) {
            if (!tree->GetBranch(branch.c_str())) {
                throw std::runtime_error("Branch '" + branch + "' not found in " + input);
            }
        }
    }
}

int main(int argc, char** argv) {
    try {
        ROOT::EnableImplicitMT();
        gROOT->SetBatch(kTRUE);

        const auto opts = parse_args(argc, argv);
        validate_inputs(opts);

        ROOT::RDataFrame df(opts.tree, opts.inputs);
        auto selected = df
            .Filter("nMuon >= 2", "at least two muons")
            .Define("leading_muon_pt", "Muon_pt[0]")
            .Define("leading_muon_eta", "Muon_eta[0]")
            .Filter("leading_muon_pt > 25.0", "leading muon pt")
            .Filter("std::abs(leading_muon_eta) < 2.4", "leading muon eta");

        auto h_pt = selected.Histo1D(
            {"h_leading_muon_pt", "Leading muon p_{T};p_{T} [GeV];Events", 50, 0.0, 200.0},
            "leading_muon_pt",
            "event_weight");
        auto report = selected.Report();

        fs::create_directories(opts.output.parent_path().empty() ? "." : opts.output.parent_path());
        TFile out(opts.output.c_str(), "RECREATE");
        h_pt->Write();
        out.Close();

        report->Print();
        std::cout << "Wrote " << opts.output << '\n';
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
