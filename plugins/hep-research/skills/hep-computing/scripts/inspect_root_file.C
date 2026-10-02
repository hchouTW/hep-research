#include <TFile.h>
#include <TKey.h>
#include <TTree.h>

#include <iostream>
#include <memory>
#include <string>

void inspect_root_file(const char* inputPath, const char* treeName = "") {
    auto file = std::unique_ptr<TFile>(TFile::Open(inputPath, "READ"));
    if (!file || file->IsZombie()) {
        std::cerr << "ERROR: could not open " << inputPath << "\n";
        return;
    }

    std::cout << "Top-level keys in " << inputPath << ":\n";
    for (auto* obj : *file->GetListOfKeys()) {
        auto* key = dynamic_cast<TKey*>(obj);
        if (!key) continue;
        std::cout << "  " << key->GetName() << "  [" << key->GetClassName() << "]\n";
    }

    if (std::string(treeName).empty()) {
        return;
    }

    auto* tree = file->Get<TTree>(treeName);
    if (!tree) {
        std::cerr << "ERROR: tree not found: " << treeName << "\n";
        return;
    }

    std::cout << "\nTree printout for " << treeName << ":\n";
    tree->Print();
}
