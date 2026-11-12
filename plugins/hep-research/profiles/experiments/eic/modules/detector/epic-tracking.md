# ePIC tracking subsystems

> Scope: ePIC experiment tracking design: construction parameters only, no performance.
> Method owner: [hep-detector](../../../../../skills/hep-detector/SKILL.md) for tracking and vertexing methods; this module adds only what ePIC sources state about the ePIC trackers.

- The tracking system occupies a volume of radius 75 cm and -165 cm < z < 200 cm along the beam axis, inside the MARCO magnet with a reference field of 1.7 T and up to 2 T (PDR draft, Dec 2024) (eic:C58).
- Silicon vertex tracker (SVT): the Inner Barrel has three MAPS layers at radii of 38, 50 and 125 mm and the Outer Barrel two layers at 270 and 420 mm; the SVT active volume is -105 < z < 135 cm within a radius of about 50 cm (eic:C59).
- SVT sensors: the ALICE ITS3 MOSAIX MAPS in 65 nm CMOS, thinned to 50 μm, pixel size 21 × 23 μm², twelve stitched units over about 27 cm; the Outer Barrel uses a modified version, the EIC Large Area Sensor (eic:C60).
- The SVT also has endcap disks, five per side, and is air-cooled thanks to the low sensor power; this is conference-level context (eic:C85).
- Barrel MPGDs: CyMBaL in a radial envelope between 55 cm and 60 cm over -105 cm < z < 143 cm, and a μRWELL layer at a radius of 72.5 cm in front of the hpDIRC, built of 12 rectangular modules per z-sector (PDR draft, Dec 2024) (eic:C61).
- Endcap MPGDs: four G-RWELL disks (a GEM pre-amplification stage over a μ-RWELL), two on each side, covering |η| > 2 over the full azimuth with a two-dimensional strip readout of 600 μm pitch (eic:C62).
- AC-LGAD layers serve both timing and tracking; their parameters are in [epic-pid.md](epic-pid.md) (eic:C68).

Sources disagree on some details (an endcap MPGD paper gives a different field value, the PDR draft gives different inner SVT radii and disk coverage); the values above follow the cited claims.

## General method

Track and vertex reconstruction belong to hep-detector (`<plugin root>/skills/hep-detector/references/tracking-and-vertexing.md`, `<plugin root>/skills/hep-detector/references/gaseous-and-specialized-tracking-technologies.md`).
