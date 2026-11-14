# EIC interaction region

> Scope: EIC facility (the collider) interaction-region design targets and requirements, not any one experiment.
> Method owner: [hep-measurement](../../../../../skills/hep-measurement/SKILL.md) for how the crossing geometry enters a measurement design; hep-theory owns the kinematics and hep-detector the reconstruction methods.

Two kinds of number appear here, each labelled by its claim: design targets of the 2021 Conceptual Design Report (CDR) and the Yellow Report, and requirements of the EIC project requirements page as read on 2026-11-11. Where they differ, both are shown; the requirement is the more recent statement.

## Crossing angle and crab crossing

- The CDR design brings the beams together at a total crossing angle of 25 mrad and compensates it with crab cavities (197 MHz) in each beam (eic:C41).
- The project requirements set a 25 mrad crossing angle for the colliding beams and require its compensation with crab cavities in both the electron and the hadron beam (eic:C47).
- The Yellow Report gives the same 25 mrad crossing angle, with crab cavities in each beam compensating the luminosity loss (eic:C54).

What this means for an analysis, without methods: the laboratory frame is neither the center-of-mass frame nor the head-on frame, because the beams are unequal and cross at an angle. Whether an analysis boosts to the head-on frame, and which crossing angle it uses and from where, is stated under `eic:crossing_angle_treatment` in `conventions.json`; this profile does not fix it.

## Space around the interaction point

- The CDR design keeps a region of ±4.5 m around the interaction point free of accelerator elements (eic:C42).
- The project requirements set a stay-clear volume that extends -4.5 m along Z in the electron direction and +5 m in the hadron direction, with an additional 0.5 m on either side, a total stay-clear length of 10.5 m (eic:C48).
- The Yellow Report's reference space kept free of machine elements is [-4.5, 5.0] m along the beam line around the IP (eic:C56).
- The first interaction-region detector system is placed at the IP of IR6; the requirements keep the feasibility of a second interaction region and detector (eic:C49).

## Far-forward and far-backward regions

- The Yellow Report describes the detector integration as extending over ± 40 m beyond the main detector: a far-forward region downstream of the ion beam covering about 30 m, and a far-backward region along the outgoing lepton beam for luminosity monitoring and low-Q² coverage (eic:C57).

These are envelopes for the detector, not the detector's dimensions. The detectors that ePIC places along the outgoing beams (far-forward and far-backward) belong to the ePIC modules, not to this facility module.

## General method

DIS kinematics in the head-on and laboratory frames belong to hep-theory (`<plugin root>/skills/hep-theory/references/dis-kinematics.md`), and the reconstruction of x, y and Q^2, including events with a crossing angle, to hep-detector (`<plugin root>/skills/hep-detector/references/dis-kinematic-reconstruction.md`, with the reconstruction chain in `event-reconstruction.md`).
