# Worked Examples

Illustrative, not verified against any named experiment, codebase, or venue template. Each
file shows: request, diagram type, assumptions, source (Mermaid/DOT/TikZ/ASCII), validation
checks, caption. Mermaid sources were rendered with `mmdc`, DOT compiled with `dot`, and the SVG
example rasterized and inspected, and the TikZ sources (`hep/07`, `hep/08`, `statistics/02`) compiled with LuaLaTeX by `check_diagram_sources.py` on 2026-10-14 (LuaHBTeX 1.24, TeX Live 2026; compiled, not inspected in that run; `hep/07` was earlier also compiled with Tectonic and pdfLaTeX and inspected); the PlantUML sources (`computer-science/09-10`) were rendered with PlantUML and inspected. Render and inspect before publishing.

| Dir | Files |
|---|---|
| `general/` | research workflow, methodology pipeline (from a Methods excerpt), conceptual framework, experimental workflow, repository architecture (read a real repo first), Methods text -> workflow with the Known/Inferred/Assumed table, SVG-spec figure |
| `hep/` | collider pipeline, MC chain, detector schematic, likelihood architecture, decay tree, SR/CR workflow, Feynman-style, LHC pipeline in DOT + Mermaid + TikZ with a two-lane variant, stacked space spectrometer (`09`), cosmic-ray flux chain (`10`), neutrino near/far oscillation chain (`11`) |
| `statistics/` | Bayesian workflow, hierarchical model (plates), causal DAG, MCMC, hypothesis test, bootstrap, HMM |
| `prose/` | writing, not diagrams: three weak-versus-better examples (a results paragraph with real hedges and significance wording, a review synthesis with a referee handoff, a review talk checked with `check_adaptation.py`); index in [prose/README.md](prose/README.md) |
| `computer-science/` | microservices, Transformer, RAG, agentic AI, distributed pipeline, API sequence, database platform, ML training pipeline, PlantUML component diagram, PlantUML sequence diagram |

Repository architecture extraction is shown in `general/05` (a real repository, evidence table first).
