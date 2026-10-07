// Rivet analysis: STARTING TEMPLATE for a particle-level signal-region selection (status: documented, not run here).
// Build: rivet-build RivetTEMPLATE_ANALYSIS.so rivet_template_analysis.cc
// Run:   rivet --pwd -a TEMPLATE_ANALYSIS events.hepmc -o result.yoda
// Copy the selection from the paper you recast (object definitions, overlap removal, signal regions), and check the
// published cutflow before trusting a result. Rivet 4 names the jet algorithm JetAlg::ANTIKT; Rivet 3 used
// FastJets::ANTIKT.
#include "Rivet/Analysis.hh"
#include "Rivet/Projections/FinalState.hh"
#include "Rivet/Projections/FastJets.hh"

namespace Rivet {

  class TEMPLATE_ANALYSIS : public Analysis {
  public:
    RIVET_DEFAULT_ANALYSIS_CTOR(TEMPLATE_ANALYSIS);

    void init() {
      const FinalState fs(Cuts::abseta < 4.9);
      declare(FastJets(fs, JetAlg::ANTIKT, 0.4), "Jets");
      book(_h_mjj, "mjj", 24, 0.0, 1200.0);  // leading-pair mass [GeV]
      book(_c_sr, "signal_region");           // signal-region count
    }

    void analyze(const Event& event) {
      const Jets jets = apply<FastJets>(event, "Jets").jetsByPt(Cuts::pT > 30*GeV && Cuts::abseta < 2.5);
      if (jets.size() < 2) vetoEvent;
      _h_mjj->fill((jets[0].mom() + jets[1].mom()).mass()/GeV);
      _c_sr->fill();
    }

    void finalize() {
      scale(_h_mjj, crossSection()/picobarn/sumW());    // differential cross section [pb/GeV per bin width]
      scale(_c_sr, crossSection()/femtobarn/sumW());    // fiducial cross section [fb]
    }

  private:
    Histo1DPtr _h_mjj;
    CounterPtr _c_sr;
  };

  RIVET_DECLARE_PLUGIN(TEMPLATE_ANALYSIS);

}
