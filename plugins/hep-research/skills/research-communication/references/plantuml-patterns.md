# PlantUML Patterns

Best for UML-flavored software documentation: component, sequence, class, deployment, and state diagrams
where the reader expects UML notation. For flowcharts and pipelines prefer Mermaid; for dense graphs prefer
Graphviz. Render: `plantuml f.puml` (needs a Java runtime) or `plantuml -tsvg f.puml`; text-only
diagram sources go between `@startuml` and `@enduml`.

> Every PlantUML block in this bundle was rendered with PlantUML 1.2026.8 on OpenJDK and inspected (2026-09-25);
> `${CLAUDE_PLUGIN_ROOT}/skills/research-communication/scripts/check_diagram_sources.py` compiles ```plantuml fences when `plantuml` is on PATH. Render and inspect your own before publishing.

## Baseline style

```plantuml
@startuml
skinparam monochrome true
skinparam shadowing false
skinparam defaultFontName Helvetica
skinparam defaultFontSize 11
skinparam ArrowFontSize 10
left to right direction
' ...diagram body...
@enduml
```
`skinparam monochrome true` gives a grayscale-safe default; distinguish kinds by shape and line style, not color.

## Component diagram

```plantuml
component "API service" as api
database  "Job store"  as db
queue     "Job queue"  as q
component "Worker"     as w
cloud     "External API" as ext

api --> q  : enqueue
q   ..> w  : deliver (async)
api --> db : read / write
w   --> db : write result
w   --> ext : call
```
Solid `-->` = synchronous call or data; dotted `..>` = asynchronous event or optional dependency. Say so in the legend.
Group with `package "Name" { ... }` or `rectangle "Name" { ... }`.

## Sequence diagram

```plantuml
participant Client
participant "API service" as API
Client -> API : POST /jobs
activate API
API --> Client : 202 Accepted
deactivate API
loop until status == done
  Client -> API : GET /jobs/id
  API --> Client : status
end
alt failure
  API --> Client : 500 + error
else success
  API --> Client : 200 + result
end
```
`->` synchronous, `-->` return/dashed, `->>` asynchronous (open head). Use `activate`/`deactivate` for lifelines only
when the duration matters; use `note over A, B : ...` for assumptions.

## Class / ER-like

```plantuml
class Sample {
  +id : int
  +energy : float
}
class Track
Sample "1" *-- "many" Track
```
Put each member on its own line: a one-line body such as `class Sample { +id : int  +energy : float }` is a syntax error
(PlantUML then guesses a sequence diagram and fails). Do not draw inheritance or composition unless the source has it (`<|--` inheritance, `*--` composition, `o--` aggregation, `-->` association).

## Pitfalls

- A `title` line and `legend ... end legend` block are part of the source, but the caption belongs in the manuscript.
- Direction: `left to right direction` for pipelines; the default is top-to-bottom.
- Quote names with spaces or punctuation and give them an alias (`as`); refer to the alias afterwards.
- Layout is automatic and needs Graphviz (`dot`) for some diagram types; long labels widen boxes.
- Keep sequence diagrams to one scenario; put failure paths in `alt` or a second diagram.
- A fence with no `@startuml` renders as nothing, silently, with `plantuml -pipe`: always include the markers in a real file.
- Do not invent components: the same Known / Inferred / Assumed rule as for every other format.

## Checks

Every participant and component exists in the source system; async vs synchronous arrows are consistent with
the code or API; return arrows are dashed; no lifeline is activated and never deactivated; the `alt` branches
are mutually exclusive.
