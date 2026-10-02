#include <ROOT/RDataFrame.hxx>
#include <TCanvas.h>
#include <TFile.h>
#include <TROOT.h>
#include <TTree.h>

#include <iostream>
#include <memory>
#include <string>

void plot_branch(
    const char* inputPath,
    const char* treeName = "Events",
    const char* branchName = "pt",
    const char* outputPath = "output.root",
    int bins = 50,
    double xmin = 0.0,
    double xmax = 100.0
) {
    gROOT->SetBatch(kTRUE);

    auto file = std::unique_ptr<TFile>(TFile::Open(inputPath, "READ"));
    if (!file || file->IsZombie()) {
        std::cerr << "ERROR: could not open " << inputPath << "\n";
        return;
    }

    auto* tree = file->Get<TTree>(treeName);
    if (!tree) {
        file->ls();
        std::cerr << "ERROR: missing tree " << treeName << "\n";
        return;
    }

    if (!tree->GetBranch(branchName)) {
        tree->Print();
        std::cerr << "ERROR: missing branch " << branchName << "\n";
        return;
    }

    file->Close();

    ROOT::RDataFrame df(treeName, inputPath);

    const std::string hName = std::string("h_") + branchName;
    const std::string hTitle = std::string(branchName) + ";" + branchName + ";Events";
    auto h = df.Histo1D({hName.c_str(), hTitle.c_str(), bins, xmin, xmax}, branchName);

    TFile out(outputPath, "RECREATE");
    if (out.IsZombie()) {
        std::cerr << "ERROR: could not create " << outputPath << "\n";
        return;
    }

    h->Write();

    TCanvas c((std::string("c_") + branchName).c_str(), (std::string("c_") + branchName).c_str(), 800, 600);
    h->Draw("HIST");
    c.SaveAs((std::string(branchName) + ".pdf").c_str());
    c.Write();

    out.Close();
    std::cout << "Wrote " << outputPath << "\n";
}
