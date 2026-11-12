# EIC facility context

> Scope: EIC facility (the collider), not any one experiment.
> Method owner: [hep-measurement](../../../../../skills/hep-measurement/SKILL.md) for how configuration facts enter a measurement design; [hep-theory](../../../../../skills/hep-theory/SKILL.md) owns DIS kinematics and QCD.

This overview names what the profile knows about the facility and where the numbers live. It quotes no number itself.

## Kinds of number

Every number in the facility modules is quoted from a numeric claim that carries one of four kinds, and says which: a **requirement** (the EIC project requirements pages), a **design target** (the Conceptual Design Report or the Yellow Report), a **design value** (an ePIC construction parameter, only in the detector modules), or a **proposal** (a run plan proposed by ePIC, only in the ePIC early-running module and never a facility value). None of them is an achieved or measured value. Derived values, such as a center-of-mass energy, are computed by a named plugin script from cited numbers and marked `derived:`.

## The facility

- The 2023 NSAC Long Range Plan recommends the expeditious completion of the EIC as the highest priority for facility construction; it records that the EIC became a DOE project in 2019 and that its conceptual design was approved in 2021 (eic:C51).
- In February 2026 DOE approved the second phase of long-lead procurements of accelerator and detector components as the EIC moves into construction; the EIC is built at Brookhaven National Laboratory in partnership with Jefferson Lab (eic:C50).
- The EIC Conceptual Design Report is the technical reference design for the EIC, as its OSTI record describes it (eic:C07); the facility modules quote its design targets from claims read in its full text.
- The EIC Yellow Report describes the physics case, the resulting detector requirements and the evolving detector concepts for the EIC experimental program; the studies behind it were commissioned and organized by the EIC User Group. Its concepts and detector requirement numbers are facility-level design literature, not ePIC facts (eic:C06).

## Where the values are

Beam species, energies, polarization and luminosity per configuration, with derived center-of-mass energies and the spec field format: [beam-configurations.md](beam-configurations.md). Crossing angle, crab crossing and the space around the interaction point: [interaction-region.md](interaction-region.md).

The configuration of a study is set by the project, never by a profile default: name it (species, E_e x E_h, polarization), say which number is a design target or a requirement, and hand the physics to the owner skill.

Frames: in general the laboratory frame is not the center-of-mass frame; `conventions.json` fixes how boosts, the crossing-angle treatment and the hadron-beam direction are stated per configuration, and the values come from the configuration and geometry release in use, not from this module.

## General method

How a configuration enters predictions is hep-theory's (`<plugin root>/skills/hep-theory/references/hadron-structure-essentials.md`).
