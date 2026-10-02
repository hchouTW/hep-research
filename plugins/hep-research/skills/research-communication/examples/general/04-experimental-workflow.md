# General 4: Experimental workflow

**Request:** "Laboratory measurement workflow with calibration and repeats."
**Type:** experimental workflow with loops. Steps from the user's protocol only.

```mermaid
flowchart TB
    P[Prepare sample] --> C[Calibrate instrument]
    C --> M[Measure]
    M --> QC{Within QC limits?}
    QC -- no --> C
    QC -- yes --> R{Repeats complete? n = 5}
    R -- no --> M
    R -- yes --> A[Analyze: mean and uncertainty]
    A --> REP[/Report result/]
```
**Caption:** Measurement protocol. After calibration each measurement must pass quality-control limits, otherwise the instrument is recalibrated; five accepted repeats are averaged to obtain the result and its uncertainty.
