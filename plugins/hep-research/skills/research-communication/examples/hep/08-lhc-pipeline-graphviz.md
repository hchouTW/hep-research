# HEP 8: LHC-style pipeline, three representations and a two-lane variant

**Request:** "Draw the event-processing pipeline for an LHC-style analysis" - primary output in Graphviz DOT, then the same graph as Mermaid and TikZ (multiple-representation mode), then a variant that separates data and simulation lanes.
**Diagram type:** analysis pipeline, paper level, left-to-right. Arrows = data flow; dashed nodes = simulation-only steps; dotted arrow = systematic-uncertainty input (nuisance parameters).

**Assumptions:** conceptual pipeline, not a specific experiment's software (Known: no experiment named; Inferred: the standard stages; Assumed: signal region is blinded until the background model is frozen). One logical graph, three renderings: node identity is the same in all of them (see the table).

| id | node | level | in data | in simulation |
|---|---|---|---|---|
| trg | Trigger and DAQ | detector | yes | (emulated) |
| gen | Event generation | generator / truth | - | yes |
| dsim | Detector simulation | detector | - | yes |
| rec | Event reconstruction | detector to objects | yes | yes |
| obj | Object calibration | reconstructed objects | yes | yes |
| sel | Event selection | analysis | yes | yes |
| cr / sr | Control / signal regions | analysis | yes | yes |
| bkg | Background estimation | analysis | yes | yes |
| fit | Likelihood fit | statistical | combined | combined |
| sys | Systematic uncertainties | statistical | - | - |

## 1. Graphviz DOT (primary; compiled with `dot`)

```dot
digraph lhc {
    rankdir=LR; nodesep=0.3; ranksep=0.45; compound=true;
    graph [fontname="Helvetica", fontsize=11];
    node  [shape=box, style="rounded", fontname="Helvetica", fontsize=11];
    edge  [fontname="Helvetica", fontsize=9, arrowsize=0.8];

    subgraph cluster_data { label="Collision data"; trg [label="Trigger and DAQ"]; }
    subgraph cluster_mc {
        label="Simulation"; style=dashed;
        gen  [label="Event generation", style="rounded,dashed"];
        dsim [label="Detector simulation", style="rounded,dashed"];
    }
    rec [label="Event reconstruction"];
    obj [label="Object calibration"];
    sel [label="Event selection"];
    cr  [label="Control regions"];
    sr  [label="Signal region"];
    bkg [label="Background estimation"];
    sys [label="Systematic\nuncertainties", shape=ellipse];
    fit [label="Likelihood fit"];
    res [label="Limit / significance\n/ measurement", shape=box, style="rounded,bold"];

    trg -> rec; gen -> dsim -> rec;
    rec -> obj -> sel; sel -> cr; sel -> sr;
    cr -> bkg; bkg -> fit; sr -> fit;
    sys -> fit [style=dotted, label="nuisance\nparameters"];
    fit -> res;
}
```

## 2. Mermaid (same graph, for README/docs)

```mermaid
flowchart LR
    subgraph DATA[Collision data]
        TRG[Trigger and DAQ]
    end
    subgraph MC[Simulation]
        GEN[Event generation] --> DSIM[Detector simulation]
    end
    TRG --> REC[Event reconstruction]
    DSIM --> REC
    REC --> OBJ[Object calibration] --> SEL[Event selection]
    SEL --> CR[Control regions] --> BKG[Background estimation] --> FIT
    SEL --> SR[Signal region] --> FIT[Likelihood fit]
    SYS(Systematic uncertainties) -.->|nuisance parameters| FIT
    FIT --> RES([Limit / significance / measurement])
    classDef sim stroke-dasharray: 5 3;
    class GEN,DSIM sim;
```

## 3. TikZ (same graph, for the paper; not compiled here)

Packages: `tikz` with libraries `positioning, arrows.meta, fit, backgrounds`; engine pdfLaTeX or LuaLaTeX.

```latex
\tikzset{
  proc/.style = {draw, rounded corners=2pt, minimum height=7mm, align=center, font=\footnotesize},
  sim/.style  = {proc, dashed},
  flow/.style = {-{Stealth[length=2mm]}},
  syst/.style = {-{Stealth[length=2mm]}, dotted},
}
\begin{tikzpicture}[node distance=6mm and 7mm]
  \node[proc]              (trg) {Trigger\\and DAQ};
  \node[sim, below=of trg] (gen) {Event\\generation};
  \node[sim, right=of gen] (dsim){Detector\\simulation};
  \node[proc, right=of trg, xshift=18mm] (rec) {Event\\reconstruction};
  \node[proc, right=of rec] (obj) {Object\\calibration};
  \node[proc, right=of obj] (sel) {Event\\selection};
  \node[proc, above right=3mm and 8mm of sel] (sr) {Signal\\region};
  \node[proc, below right=3mm and 8mm of sel] (cr) {Control\\regions};
  \node[proc, right=of cr] (bkg) {Background\\estimation};
  \node[proc, right=of sr, xshift=16mm] (fit) {Likelihood\\fit};
  \node[proc, above=of fit] (sys) {Systematic\\uncertainties};
  \draw[flow] (trg) -- (rec);  \draw[flow] (gen) -- (dsim);  \draw[flow] (dsim) -| (rec);
  \draw[flow] (rec) -- (obj);  \draw[flow] (obj) -- (sel);
  \draw[flow] (sel) -- (sr);   \draw[flow] (sel) -- (cr);    \draw[flow] (cr) -- (bkg);
  \draw[flow] (sr) -- (fit);   \draw[flow] (bkg) -| (fit);
  \draw[syst] (sys) -- node[right, font=\scriptsize]{nuisance parameters} (fit);
\end{tikzpicture}
```
Absolute `xshift` values are layout guesses; compile and adjust, or switch to a matrix of nodes.

## 4. Variant: separate data and simulation lanes (Mermaid)

Use when the point is that the two lanes run the *same* reconstruction and merge only at the analysis level.

```mermaid
flowchart LR
    subgraph DATA[Data lane]
        direction LR
        D0[(Collisions)] --> D1[Trigger and DAQ] --> D2[Reconstruction] --> D3[Calibrated objects]
    end
    subgraph SIM[Simulation lane]
        direction LR
        S0[Event generation] --> S1[Detector simulation] --> S2[Reconstruction] --> S3[Calibrated objects]
    end
    D3 --> A[Event selection and regions]
    S3 --> A
    S3 -.->|scale factors, corrections| D3
    A --> F[Likelihood fit] --> R([Result])
    classDef sim stroke-dasharray: 5 3;
    class S0,S1,S2,S3 sim;
```

**Validation:** trigger precedes offline reconstruction; simulation goes through the *same* reconstruction (data-side trigger is emulated, not drawn); truth information does not reach selection; control regions feed the background estimate and both feed the fit; systematics enter as nuisance parameters, not as a processing step; the DOT graph was compiled, the Mermaid graphs were rendered with `mmdc`, the TikZ was not compiled. The dotted "scale factors" edge in the variant is a correction, not data flow - it is labeled for that reason.
**Caption:** Event-processing workflow of the analysis. Collision data (trigger, reconstruction) and simulated events (generation, detector simulation, dashed) are reconstructed and calibrated identically, then selected into signal and control regions. Control regions determine the background estimate; both enter the likelihood fit together with the systematic uncertainties (nuisance parameters, dotted). Arrows denote data flow.
