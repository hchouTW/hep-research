# ePIC detector context

> Scope: ePIC experiment (the first experiment at the EIC), design-phase description.
> Method owner: [detector-response](../../../../../skills/detector-response/SKILL.md) for tracking, calorimetry, PID, timing, data-acquisition and performance methods; this module adds only what the collaboration or host laboratory states about ePIC.

- ePIC is the first experiment at the EIC, formed to design, build and operate it; "ePIC" and "EIC" are not interchangeable (C01).
- The design uses a 1.7 tesla superconducting magnet; this is a design value, not a measured field map (C03).
- Subsystems named qualitatively: silicon detectors for tracking; calorimeters for electromagnetic energy; particle-identification technologies; dense calorimetry for jets; far-forward silicon detectors in the beam pipe and inside one of the EIC collider magnets, with calorimetry for photons and neutrons (C04).
- Readout: a streaming data-acquisition system without a traditional hardware trigger is planned, with machine learning and AI described as key for processing and analysis; this is a plan, not a tested system (C05).

**No performance number is shipped.** Resolution, efficiency, PID separation and acceptance values for ePIC are either simulation projections tied to a geometry release or future measurements. When asked, say that none is in the profile, then ask: which detector concept (ePIC or another), which geometry release and configuration (species, E_e x E_h), and whether a projection or a measurement is meant. A projection quoted later must carry its release and the word "projection" in its claim.

General method lives with the owner: how to measure an efficiency or resolution, how to build a response matrix, how to compare data with simulation are in detector-response's references, not here.
