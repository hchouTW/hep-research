# ePIC readout and data acquisition

> Scope: ePIC experiment readout architecture only (no software, no rates, no performance).
> Method owner: [hep-detector](../../../../../skills/hep-detector/SKILL.md) for front-end electronics, readout and digitization methods; this module adds only what ePIC sources state about the ePIC architecture.

- ePIC plans a streaming data-acquisition system without a traditional hardware trigger (eic:C05).
- There is no global trigger system: each front-end board self-triggers and provides a stream of hit data (PDR draft, Dec 2024) (eic:C79).
- Front end, calorimeters: the CALOROC1B ASIC, 36 channels with 3 amplification paths each, two ADCs for the energy, a TDC for the time of arrival, and a streaming readout (eic:C73).
- Front end, dRICH: SiPMs read out by the ALCOR mixed-signal ASIC (eic:C81).
- Data flow: the reconstruction is being adapted to streaming readout by splitting the data into timeframes; this is context, and the reconstruction software itself is out of this profile's scope (eic:C89).

Data rates, buffer sizes and computing models are not in the profile. Software entry points are in [epic-software-entry-points.md](epic-software-entry-points.md).

## General method

Front-end electronics, digitization and readout belong to hep-detector (`<plugin root>/skills/hep-detector/references/front-end-electronics-and-signal-processing.md`, `<plugin root>/skills/hep-detector/references/readout-digitization-and-overlay.md`).
