# Mermaid Patterns

Best for editable, GitHub/README-rendered flowcharts, pipelines, sequence and state diagrams.
Weak for: plates, precise layout control, Feynman diagrams, publication typography - use
Graphviz/TikZ for those. Syntax below is standard Mermaid; verify with a renderer
(`mmdc -i f.mmd -o f.svg`, or mermaid.live) since versions differ. `mmdc` renders through a headless Chrome
that some installs (Homebrew `mermaid-cli`, checked 2026-10-04 with 12.0.0) do not include. If every render fails
with "Could not find chrome-headless-shell (ver. N)", install that version once:
`npx @puppeteer/browsers install chrome-headless-shell@N --path ~/.cache/puppeteer`.

## Pipeline (LR) with groups and edge semantics

```mermaid
flowchart LR
    subgraph DATA[Data]
        D[(Collision data)]:::obs
        S[(Simulation)]:::sim
    end
    D --> R[Reconstruction]
    S --> R
    R --> SEL[Event selection]
    SEL --> STAT[Statistical analysis]
    STAT --> RES([Result])
    classDef obs fill:#fff,stroke:#000,stroke-width:2px;
    classDef sim fill:#eee,stroke:#000,stroke-dasharray: 5 3;
```
Use `classDef` with stroke style plus fill so it survives grayscale.

## Edge styles

```text
A --> B        solid arrow (data flow)
A -.-> B       dotted arrow (control / assumed / optional)
A ==> B        thick arrow (main path)
A -- label --> B     labeled edge     (also A -->|label| B)
A --- B        line without head
```
Declare in a legend subgraph or the caption: e.g. solid = data flow, dashed = control.

## Flowchart with decision and loop

```mermaid
flowchart TD
    A[/Input x_0/] --> B[Update x_k+1]
    B --> C{"‖x_k+1 − x_k‖ < ε ?"}
    C -- yes --> D[/Output x*/]
    C -- no --> E{"k < k_max ?"}
    E -- yes --> B
    E -- no --> F[/Report non-convergence/]
```
Shapes: `[/ /]` parallelogram (I/O), `{ }` decision, `([ ])` terminator, `[[ ]]` subroutine, `[( )]` store.
Quote labels containing special characters or math-like text.

## Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant T as Tool API
    U->>O: request
    activate O
    loop until verified or max 3 retries
        O->>T: call(args)
        T-->>O: result
    end
    O--)U: async notification
    O-->>U: answer
    deactivate O
```
`->>` sync call, `-->>` return, `-)` / `--)` async. Frames: `loop`, `alt/else`, `opt`, `par/and`, `critical`, `Note over`.

## State

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Running: start
    Running --> Idle: done
    Running --> Failed: error
    Failed --> Idle: reset
```

## ER

```mermaid
erDiagram
    RUN ||--o{ EVENT : contains
    EVENT ||--|{ TRACK : has
    RUN { int run_id PK  string period }
```

## Pitfalls

- Node ids with spaces/keywords (`end`, `graph`) break parsing; use short ids + quoted labels.
- Unbalanced quotes/brackets in labels; `;` and `#` in labels need quoting.
- No math typesetting by default (KaTeX support is renderer-dependent, `$$...$$`); single-`$...$` is not recognised, so write `$$...$$` (rendered as KaTeX by `mmdc`, checked 2026-10-02: `\hat{}`, `\mathcal{}`, `\mid` all correct) or plain Unicode (θ, α, ≥, √) in labels; a combining hat (θ̂) renders badly, so use `$$\hat\theta$$` or write "theta-hat"; use Graphviz/TikZ when real LaTeX is needed.
- Layout is automatic: long chains wrap unpredictably; use subgraphs and `direction` inside them, or switch tools when placement matters.
- Comments: `%% comment`. Keep the diagram source in the repo next to the paper.
- Mermaid has no plate notation or Feynman lines; do not fake them.

## Line breaks in labels

Use `<br/>` inside a quoted label (`A["Line one<br/>line two"]`); it is the most portable form. A literal `\n`
inside a quoted label also rendered as a line break in the Mermaid CLI used to validate this bundle, but support
varies by host (GitHub, Obsidian, older versions), so prefer `<br/>`. Unquoted labels with parentheses or `<`
need quotes.
