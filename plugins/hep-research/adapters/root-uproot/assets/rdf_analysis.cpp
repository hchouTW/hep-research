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
        std::cerr << "Usage: " << argv[0] << " input.root [output.root] [tree] [branch]\n";
        return 1;
    }

    const std::string input = argv[1];
    const std::string output = argc > 2 ? argv[2] : "output.root";
    const std::string treeName = argc > 3 ? argv[3] : "Events";
    const std::string branchName = argc > 4 ? argv[4] : "pt";

    if (!std::filesystem::exists(input)) {
        std::cerr << "ERROR: input file does not exist: " << input << "\n";
        return 1;
    }

    try {
        gROOT->SetBatch(kTRUE);

        ROOT::RDataFrame df(treeName, input);

        auto nEvents = df.Count();
        auto h = df.Histo1D(
            {("h_" + branchName).c_str(), (branchName + ";" + branchName + ";Events").c_str(), 50, 0.0, 100.0},
            branchName
        );

        TFile out(output.c_str(), "RECREATE");
        if (out.IsZombie()) {
            throw std::runtime_error("Could not create output file: " + output);
        }

        std::cout << "Events: " << *nEvents << "\n";

        h->Write();

        TCanvas c(("c_" + branchName).c_str(), ("c_" + branchName).c_str(), 800, 600);
        h->Draw("HIST");
        c.SaveAs((branchName + ".pdf").c_str());
        c.Write();

        out.Close();

        std::cout << "Wrote " << output << "\n";
        std::cout << "Wrote " << branchName << ".pdf\n";
    } catch (const std::exception& ex) {
        std::cerr << "ERROR: " << ex.what() << "\n";
        return 2;
    }

    return 0;
}
