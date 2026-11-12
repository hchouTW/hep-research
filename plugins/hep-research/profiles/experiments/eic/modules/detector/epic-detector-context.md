# ePIC detector context

> Scope: ePIC experiment (the first experiment at the EIC), design-phase description.
> Method owner: [hep-detector](../../../../../skills/hep-detector/SKILL.md) for tracking, calorimetry, PID, timing, data-acquisition and performance methods; this module adds only what the collaboration or host laboratory states about ePIC.

- ePIC is the first experiment at the EIC, formed to design, build and operate it; "ePIC" and "EIC" are not interchangeable (eic:C01).
- The 2023 Long Range Plan describes the ePIC collaboration as the outcome of the competitive review, finalizing the designs of its detector subsystems at IR6, with a second detector possible years later (eic:C52).
- The design uses a 1.7 tesla superconducting magnet; this is a design value, not a measured field map (eic:C03).
- Subsystems named qualitatively: silicon detectors for tracking; calorimeters for electromagnetic energy; particle-identification technologies; dense calorimetry for jets; far-forward silicon detectors in the beam pipe and inside one of the EIC collider magnets, with calorimetry for photons and neutrons (eic:C04).
- Readout: a streaming data-acquisition system without a traditional hardware trigger is planned, with machine learning and AI described as key for processing and analysis; this is a plan, not a tested system (eic:C05).

## Subsystem map

Design values are construction parameters only (dimensions, positions, coverage, materials, segmentation, channel counts, field), each from a cited claim. Most come from the draft preliminary design report of December 2024 or from subsystem journal papers; they describe a design in progress.

| Region or system | Subsystems | Module | Claims |
| --- | --- | --- | --- |
| Tracking | silicon vertex tracker (MAPS), barrel and endcap MPGDs, AC-LGAD layers | [epic-tracking.md](epic-tracking.md) | eic:C58, eic:C59, eic:C61, eic:C62 |
| Particle identification | pfRICH (backward), hpDIRC (barrel), dRICH (forward), AC-LGAD time-of-flight | [epic-pid.md](epic-pid.md) | eic:C63, eic:C66, eic:C67, eic:C68 |
| Calorimetry | electromagnetic and hadronic calorimeters in the backward, barrel and forward regions | [epic-calorimetry.md](epic-calorimetry.md) | eic:C69, eic:C70, eic:C71, eic:C72 |
| Far-forward and far-backward | B0, off-momentum detectors, Roman pots, zero-degree calorimeter, luminosity monitor, low-Q² tagger | [epic-far-forward-backward.md](epic-far-forward-backward.md) | eic:C74, eic:C76, eic:C78 |
| Readout | streaming readout, front-end ASICs | [epic-readout-and-daq.md](epic-readout-and-daq.md) | eic:C79, eic:C73 |
| Early running | configurations proposed by ePIC, not facility values | [epic-early-running.md](epic-early-running.md) | eic:C82 |

**No performance number is shipped.** Resolution, efficiency, PID separation and acceptance values for ePIC are either simulation projections tied to a geometry release or future measurements. When asked, say that none is in the profile, then ask: which detector concept (ePIC or another), which geometry release and configuration (species, E_e x E_h), and whether a projection or a measurement is meant. A projection quoted later must carry its release and the word "projection" in its claim.

## General method

How to measure an efficiency or resolution, how to build a response matrix and how to compare data with simulation are hep-detector's (`<plugin root>/skills/hep-detector/references/detector-systems-overview.md`), not this module's.
