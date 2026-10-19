# HEP 6: Signal / control region workflow with simultaneous fit

**Request:** "Create a diagram showing signal regions, control regions, and a simultaneous likelihood fit."
**Type:** workflow + statistical architecture. Assumption: one signal region, two control regions, a validation region; user did not give numbers, so regions are generic.

```mermaid
flowchart LR
    EV[Selected events] --> SPLIT{Region definition}
    SPLIT --> SR["Signal region (SR)"]
    SPLIT --> CR1["Control region 1 (CR1)<br/>enriched in background A"]
    SPLIT --> CR2["Control region 2 (CR2)<br/>enriched in background B"]
    SPLIT --> VR["Validation region (VR)"]
    CR1 --> FIT
    CR2 --> FIT
    SR --> FIT["Simultaneous likelihood fit<br/>shared parameters: μ, background normalizations, θ<br/>CR→SR transfer factors inside the model"]
    SYS[Systematic uncertainties] -.->|nuisance parameters| FIT
    FIT --> RES(["Result: fitted μ"])
    FIT -.->|post-fit prediction, not fitted| VR
```
**Checks:** regions are mutually exclusive selections; CRs constrain background normalization through transfer factors that are part of the fit model, so the result comes from the fit (μ), not from a separate extrapolation step; VR is not in the fit (dashed post-fit check); SR data blinded until the fit is frozen (state if true); shared, not duplicated, parameters across regions.
**Caption:** Region-based analysis strategy. Events passing the preselection are divided into a signal region, two background-enriched control regions, and a validation region. The signal and control regions are fitted simultaneously with shared background normalizations and nuisance parameters; the validation region, which is not included in the fit, checks the background extrapolation.
