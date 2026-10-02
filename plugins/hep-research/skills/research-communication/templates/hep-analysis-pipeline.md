# Template: HEP Analysis Pipeline

**Use for:** collider analysis workflow, data + simulation chains, region-based analyses.
**Assumption line (always):** conceptual event-processing diagram, not a specific experiment's software.

## Levels to keep separate

| Level | Objects | Belongs to |
|---|---|---|
| generator / truth | partons, stable particles | simulation only |
| detector-level | hits, tracks, clusters | data and simulation |
| reconstructed objects | jets, e, mu, gamma, MET | data and simulation |
| analysis-level | selected events, regions, yields | data and simulation |
| statistical | likelihood, nuisances, results | combined |

## Mermaid skeleton

```mermaid
flowchart LR
    subgraph DATA[Collision data]
        T[Trigger and DAQ] --> RD[Event reconstruction]
    end
    subgraph MC[Simulation]
        G[Event generation] --> DS[Detector simulation] --> RM[Event reconstruction]
    end
    RD --> OBJ[Object reconstruction and calibration]
    RM --> OBJ
    OBJ --> SEL[Event selection]
    SEL --> SR[Signal region]
    SEL --> CR[Control regions]
    CR --> BKG[Background estimation]
    SR --> FIT[Likelihood fit]
    BKG --> FIT
    SYS[Systematic uncertainties] -.->|nuisance parameters| FIT
    FIT --> RES([Limit / significance / measurement])
    classDef sim stroke-dasharray: 5 3;
    class G,DS,RM sim;
```

## Checks

Data vs simulation (dashed) merge only after the same reconstruction; truth not used in selection;
CR/SR/VR roles stated; systematics enter the fit as nuisance parameters, propagated from objects;
selection order physically sensible; blinding noted if SR data is used. Load
`../references/high-energy-physics.md`.
