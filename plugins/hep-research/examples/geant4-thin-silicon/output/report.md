# Energy loss in 300 um of silicon with Geant4 11.4.3 (journey J14)

ILLUSTRATIVE (journey J14): Geant4 outputs are unvalidated; names no experiment. Simulation only: every figure or table made from these runs is labelled "Simulation".

Geant4 11.4.3 [@Agostinelli:2002hh; @Allison:2006ve; @Allison:2016lfl] was built from the v11.4.3 tag and run with an EM-only modular list
(G4EmStandardPhysics_option4 with G4DecayPhysics), production cut 0.01 mm, through adapters/geant4.

References: the Bethe mean rate (Eq. 34.5) and the Landau-Vavilov most probable loss (Eq. 34.12) of the Review of
Particle Physics [@ParticleDataGroup:2024cfk], with silicon inputs from the PDG atomic and nuclear
properties tables, never from the Geant4 material dump.

- Most probable energy loss of 10 GeV mu- (thin-layer-mpv, reference grade): relative difference to the PDG
  Landau-Vavilov value +0.0142, detection limit 0.0827; negative control
  caught; convergence gate pass.
- Mean stopping power of 100 MeV protons (stopping-power, reference grade): relative difference to Bethe
  -0.0018, detection limit 0.0378; negative control caught;
  convergence gate pass.

Label of both study records: unvalidated (phase 1: no Geant4-derived artifact is upgraded). Scopes phase 2
could re-issue: thin-layer-mpv, stopping-power.
Gaps of the MPV study: 1; of the stopping-power study: 1 (listed in the study records).
