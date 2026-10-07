# EIC facility context

> Scope: EIC facility (the collider), not any one experiment.
> Method owner: [hep-analysis](../../../../../skills/hep-analysis/SKILL.md) for how configuration facts enter a measurement design; [hep-theory](../../../../../skills/hep-theory/SKILL.md) owns DIS kinematics and QCD.

Every bullet cites a claim; every number would need a claim read at page level or better, and this profile has none for beam parameters, so it quotes none.

- ePIC is designed to study collisions of electrons with protons or other nuclei; the page does not say which ion species, energies or polarizations, so a given study's configuration is stated by the project, not a profile default (C02).
- The EIC Conceptual Design Report is described on its OSTI record as the technical reference design for the EIC; this profile has not read its body and quotes no design parameter. A study that needs a value opens the report, adds a claim at the level read and labels it a design target (C07).
- The EIC Yellow Report describes the physics case, the resulting detector requirements and the evolving detector concepts for the EIC experimental program; the studies behind it were commissioned and organized by the EIC User Group. Its concepts and requirement numbers are facility-level design literature, not ePIC facts (C06).

Frames: The two beams are different species (C02) and in general unequal in energy, so the laboratory frame is not the center-of-mass frame; `conventions.json` fixes how boosts, the crossing-angle treatment and the hadron-beam direction are stated per configuration, and the values come from the configuration and geometry release in use, not from this module.

What to do with a facility question: name the configuration (species, E_e x E_h, polarization), say which number is a design target, and hand the physics to the owner skill. What this module does not contain: energies, luminosities, polarization fractions, crossing angles, bunch structure, IR dimensions.
