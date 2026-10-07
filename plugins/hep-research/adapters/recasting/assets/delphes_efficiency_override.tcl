# Delphes card fragment: STARTING TEMPLATE for replacing one efficiency module (status: documented, not run here).
# Start from the official card of the experiment that ships with your Delphes version (cards/delphes_card_*.tcl), copy
# it, and replace the module below with the efficiency published with the search you recast. Keep the copied card and
# its Delphes version with the sample: Delphes results are not comparable across cards.
# Run: DelphesHepMC3 <YOUR_CARD>.tcl output.root events.hepmc
module Efficiency MuonEfficiency {
  set InputArray MuonMomentumSmearing/muons
  set OutputArray muons
  # efficiency as a function of pt [GeV] and eta; replace with the published parametrization and its validity range
  set EfficiencyFormula {
    (pt <= 10.0) * (0.00) +
    (abs(eta) <= 2.4) * (pt > 10.0) * (<EFFICIENCY_BARREL_AND_ENDCAP>) +
    (abs(eta) > 2.4) * (0.00)
  }
}
