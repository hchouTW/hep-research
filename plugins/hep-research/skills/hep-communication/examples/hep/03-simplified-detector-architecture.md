# HEP 3: Simplified detector architecture

**Request:** "Give me a simple collider detector schematic."
**Type:** conceptual layered schematic. **Assumption:** generic multipurpose collider detector; no dimensions, not any specific experiment; solenoid placement varies between experiments and is omitted.

```text
                beam axis  <------------------------------>
   +--------------------------------------------------------+
   |  Muon system                                           |
   |  +--------------------------------------------------+  |
   |  |  Hadronic calorimeter (HCAL)                     |  |
   |  |  +--------------------------------------------+  |  |
   |  |  |  Electromagnetic calorimeter (ECAL)        |  |  |
   |  |  |  +--------------------------------------+  |  |  |
   |  |  |  |  Tracking detector                   |  |  |  |
   |  |  |  |            (x) interaction point     |  |  |  |
   |  |  |  +--------------------------------------+  |  |  |
   |  |  +--------------------------------------------+  |  |
   |  +--------------------------------------------------+  |
   +--------------------------------------------------------+
         Trigger / DAQ: readout path from all subsystems (not geometry)
```
TikZ version: concentric rectangles (barrel cross-section) plus endcap blocks and a beam-axis arrow; see `../../references/tikz-patterns.md`.
**Caption:** Schematic cross-section of a generic collider detector (not to scale). Subsystems are arranged outward from the interaction point: tracker, electromagnetic and hadronic calorimeters, and muon system. The trigger and data-acquisition system reads out all subsystems and is not part of the detector geometry.
