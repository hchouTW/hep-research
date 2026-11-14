# ePIC particle identification detectors

> Scope: ePIC experiment particle-identification design: construction parameters only, no performance.
> Method owner: [hep-detector](../../../../../skills/hep-detector/SKILL.md) for particle identification, Cherenkov imaging and timing methods; this module adds only what ePIC sources state about the ePIC detectors.

By region: the pfRICH in the backward endcap, the hpDIRC in the barrel, the dRICH in the forward endcap, and AC-LGAD time-of-flight layers in the barrel and the forward endcap.

- pfRICH (backward): a proximity-focusing RICH covering -3.5 ≲ η ≲ -1.5, with an aerogel radiator, conical mirrors and a plane of HRPPD photosensors (eic:C63).
- pfRICH geometry: a cylindrical vessel 1.3 m in diameter and about 49 cm long, 123.6 cm from the interaction point, 2.5 cm thick aerogel tiles of nominal refractive index 1.040, and 68 HRPPD photosensors (PDR draft, Dec 2024) (eic:C64).
- hpDIRC (barrel): a DIRC with a compound lens and small-pixel photosensors; its design is advancing toward production, with legacy BaBar DIRC radiator bars being refurbished at Jefferson Lab (eic:C80).
- hpDIRC layout: twelve optically isolated sectors, each with a bar box of ten fused-silica radiator bars and a readout box; each fused-silica prism has a 32° opening angle, measures 237 mm × 350 mm × 300 mm and carries 24 sensors (PDR draft, Dec 2024) (eic:C67).
- dRICH (forward): an aerogel radiator of refractive index 1.026 (the current default, replacing 1.019), planned 4 cm thick, and a C2F6 gas radiator, in six identical sectors of spherical mirrors and SiPM photosensors (eic:C65).
- dRICH geometry and readout: a ring-shaped detector 1.27 m long and 3.6 m in diameter with 6 sectors, its SiPMs read out by ALCOR chips (PDR draft, Dec 2024) (eic:C66).
- The dRICH photodetector uses SiPMs, read out by the ALCOR mixed-signal ASIC developed for it (eic:C81).
- Time of flight: AC-LGAD strips of 500 μm × 1 cm pitch on 3.2x2 cm sensors 50 μm thick in the barrel, pixels of 500 μm × 500 μm on 1.6x1.6 cm sensors 20 μm thick in the endcap and the B0 trackers; the barrel has 144 tilted staves about 270 cm long (PDR draft, Dec 2024) (eic:C68).
- Conference overviews describe the same division by region and the AC-LGAD strips and pixels (eic:C86).

The draft states the hpDIRC bar length and radius, the barrel time-of-flight radius, the forward time-of-flight channel count and the dRICH channel and chip counts inconsistently; those values are not given here. An earlier proceedings value of the dRICH aerogel index is superseded by the value above.

## General method

Cherenkov and time-of-flight identification methods belong to hep-detector (`<plugin root>/skills/hep-detector/references/particle-identification.md`, `<plugin root>/skills/hep-detector/references/cherenkov-imaging-variants-and-photosensors.md`, `<plugin root>/skills/hep-detector/references/timing-detectors.md`).
