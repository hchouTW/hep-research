# ePIC far-forward and far-backward detectors

> Scope: ePIC experiment detectors along the outgoing beams: construction parameters only, no performance.
> Method owner: [hep-detector](../../../../../skills/hep-detector/SKILL.md) for tracking, calorimetry and luminosity methods; this module adds only what ePIC sources state about these detectors.

The facility envelope of these regions (their extent along the beam lines) is in the facility module [interaction-region.md](../facility/interaction-region.md).

- Overview: the far-forward array comprises the B0 detector inside the B0 dipole, off-momentum detectors and Roman pots with AC-LGAD tracking planes in the machine vacuum, and a zero-degree calorimeter; the far-backward region holds a luminosity monitor with a pair spectrometer and a direct-photon calorimeter (conference-level context) (eic:C88).
- B0: four silicon tracking layers between 590 and 690 cm from the interaction point and a calorimeter of PbWO4 crystals of 2 x 2 x 20 cm3 (PDR draft, Dec 2024) (eic:C74).
- Roman pots and off-momentum detectors: vacuum-based AC-LGAD silicon sensors in two stations; the low-Q² tagger has two trackers of four layers of Timepix4 pixel sensors (PDR draft, Dec 2024) (eic:C78).
- Zero-degree calorimeter, crystal layer: 2 × 2 cm2 LYSO crystals in a 30 × 30 grid (PDR draft, Dec 2024) (eic:C75).
- Zero-degree calorimeter, SiPM-on-tile design that its authors state was incorporated into the ePIC baseline (the tile layout may have changed since): overall dimensions 60 × 60 × 162 cm3, iron absorber blocks of 96 mm × 98 mm × 20 mm, and 25 cm2 hexagonal scintillator tiles 3 mm thick read out by SiPMs (eic:C76).
- The zero-degree calorimeter uses SiPM-on-tile technology, as do the central and forward calorimeters, and its final readout is based on the CALOROC ASIC (eic:C77).
- No peer-reviewed design paper of the B0 detector was found; the search is limited and does not prove absence (eic:C92).
- No peer-reviewed design paper of the luminosity monitor or the low-Q² tagger was found; the search is limited and does not prove absence (eic:C93).

The geometry-case claims of the zero-degree calorimeter (prototype and predecessor designs, added for `reference:geometry-cases`) are not used here, and the draft design report gives no positions for the Roman pots or the zero-degree calorimeter.

## General method

Far-forward tracking, calorimetry and luminosity measurement belong to hep-detector (`<plugin root>/skills/hep-detector/references/tracking-and-vertexing.md`, `<plugin root>/skills/hep-detector/references/calorimetry-ecal-hcal.md`, `<plugin root>/skills/hep-detector/references/triggers-luminosity-pileup.md`).
