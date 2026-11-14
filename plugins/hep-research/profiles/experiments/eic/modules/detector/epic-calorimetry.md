# ePIC calorimeters

> Scope: ePIC experiment calorimetry design: construction parameters only, no performance.
> Method owner: [hep-detector](../../../../../skills/hep-detector/SKILL.md) for electromagnetic and hadronic calorimetry methods; this module adds only what ePIC sources state about the ePIC calorimeters.

ePIC has distinct electromagnetic and hadronic calorimeters in the backward, barrel and forward regions; the barrel imaging calorimeter combines AstroPix silicon imaging layers with a Pb/SciFi bulk section read out by SiPMs (conference-level context, eic:C87).

## Electromagnetic

- Backward (EEEMCal): lead tungstate (PWO) crystals of 2 × 2 cm2 transverse size and 20 cm length (22 X0), at 175 cm from the interaction point, read out by SiPMs (PDR draft, Dec 2024) (eic:C69).
- No peer-reviewed design paper of the backward calorimeter was found; the search is limited and does not prove absence (eic:C90).
- Barrel (BIC): active length 435 cm, inner radius 82.5 cm, 48 sectors, coverage -1.71 ≲ η ≲ 1.31 (PDR draft, Dec 2024) (eic:C70).
- Forward: tungsten powder and scintillating fibres, coverage 1.4 ≲ η ≲ 3.9, outer radius about 190 cm, front face at about 341 cm, 18320 towers of 2.5 cm × 2.5 cm, each read out by four 6 × 6 mm2 SiPMs (PDR draft, Dec 2024) (eic:C71).

## Hadronic

- Backward (nHCal): 10 layers of 4 cm steel and 0.4 cm scintillator between radii 14 cm and 276 cm, at -395 cm; barrel: based on the sPHENIX outer HCal, steel within envelope radii of 1820 mm and 2700 mm; forward (LFHCal): at z = 3.68 m, radius about 2.7 m, depth 1.32 m, layers of 1.52 cm steel and 0.4 cm scintillator (PDR draft, Dec 2024) (eic:C72).
- No peer-reviewed design paper of the forward calorimeters (forward electromagnetic, LFHCal and its insert) was found; the search is limited and does not prove absence (eic:C91).

## Readout

- The CALOROC1B front-end ASIC reads large-area SiPMs for the calorimeters: 36 channels, each with 3 amplification paths (four gains), two ADCs for the energy and a TDC for the time of arrival, with a streaming readout (eic:C73).

## General method

Calorimeter calibration and energy reconstruction belong to hep-detector (`<plugin root>/skills/hep-detector/references/calorimetry-ecal-hcal.md`).
