#include <TCanvas.h>
#include <TFile.h>
#include <TF1.h>
#include <TH1.h>
#include <TROOT.h>

#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " input.root hist_name [plot.pdf]\n";
        return 1;
    }

    const std::string input = argv[1];
    const std::string histName = argv[2];
    const std::string plot = argc > 3 ? argv[3] : "fit.pdf";

    try {
        gROOT->SetBatch(kTRUE);

        auto file = std::unique_ptr<TFile>(TFile::Open(input.c_str(), "READ"));
        if (!file || file->IsZombie()) {
            throw std::runtime_error("Could not open input file: " + input);
        }

        auto* hist = file->Get<TH1>(histName.c_str());
        if (!hist) {
            file->ls();
            throw std::runtime_error("Could not find histogram: " + histName);
        }

        if (hist->GetEntries() == 0) {
            throw std::runtime_error("Cannot fit empty histogram: " + histName);
        }

        hist->SetDirectory(nullptr);
        file->Close();

        TF1 fit("fit", "gaus", hist->GetXaxis()->GetXmin(), hist->GetXaxis()->GetXmax());
        auto result = hist->Fit(&fit, "RS");
        const int status = static_cast<int>(result);

        std::cout << "fit status = " << status << "\n";
        std::cout << "constant = " << fit.GetParameter(0) << " +/- " << fit.GetParError(0) << "\n";
        std::cout << "mean     = " << fit.GetParameter(1) << " +/- " << fit.GetParError(1) << "\n";
        std::cout << "sigma    = " << fit.GetParameter(2) << " +/- " << fit.GetParError(2) << "\n";
        if (fit.GetNDF() > 0) {
            std::cout << "chi2/ndf = " << fit.GetChisquare() / fit.GetNDF() << "\n";
        }

        TCanvas c("c_fit", "c_fit", 800, 600);
        hist->Draw("E");
        fit.Draw("SAME");
        c.SaveAs(plot.c_str());
        std::cout << "Wrote " << plot << "\n";
    } catch (const std::exception& ex) {
        std::cerr << "ERROR: " << ex.what() << "\n";
        return 2;
    }

    return 0;
}
