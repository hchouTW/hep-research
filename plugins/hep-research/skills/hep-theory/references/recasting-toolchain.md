# Recasting toolchain: generators, particle-level analyses, fast detector simulation, reinterpretation tools

Status: **documented**. The templates in `<plugin root>/adapters/recasting/assets/` were written without the tools
installed; none has been run by this plugin. Treat each as a starting point and validate it as described below before
any number from it is reported.

## Which route

| Situation | Route | Template |
|---|---|---|
| The search publishes efficiency maps or a likelihood (HEPData, pyhf) | fold the prediction with the published map, or use the published likelihood; no detector simulation | `examples/recasting/`, `adapters/pyhf-combine/` |
| A simplified-model topology the database covers | SModelS against its database of simplified-model results | `smodels_parameters.ini` |
| A search implemented in the Public Analysis Database | MadAnalysis 5 recast with its Delphes card | `ma5_recast.ma5` |
| A particle-level measurement or a search with a Rivet implementation | Rivet, at particle level | `rivet_template_analysis.cc` |
| Nothing above fits | generate (MadGraph5_aMC@NLO), shower, Delphes with the experiment's card, then your own selection | `mg5_proc_card.dat`, `delphes_efficiency_override.tcl` |

Prefer the route with the least simulated detector: a published efficiency map or likelihood beats a fast simulation,
which beats a hand-tuned one.

## What every recast records

- Generator: version, model (UFO) and its version, process, PDF set, scale choice and its variation, seed, number of
  events, matching or merging scheme. These go into a `computational-run` artifact (hep-computing).
- Particle-level analysis: the paper and its cutflow, object definitions, overlap removal and signal regions as
  implemented; the Rivet or MA5 version.
- Detector: the Delphes version and the exact card (copied, not referenced by name), or the published efficiency map
  and its validity range (detector-response); never both for the same effect.
- Statistics: how the limit was set (the tool's own CLs, a published likelihood, or core.stats) and the background and
  its uncertainty taken from the paper (hep-statistics).

## Validation before use

1. Reproduce the published cutflow for the benchmark point the paper gives, within the tolerance the paper or its
   auxiliary material implies (often 10-20% per step for a fast simulation); record the comparison.
2. Reproduce one published limit or expected yield at a benchmark point.
3. Only then scan the model; points outside the validated kinematic range are reported as extrapolations or refused.
A template that has not passed 1 and 2 stays `documented`; one that has, in a declared environment, can be raised to
`demonstrated-on-synthetic-data` or `tested-in-declared-environment` in `adapters/recasting/adapter.json`.

## Common pitfalls

- Applying an efficiency twice: once inside Delphes and again from the paper's map.
- Mixing generator-level cuts in the MadGraph run card with the analysis selection without accounting for them.
- Using a Delphes card from another experiment or version than the analysis assumed.
- Comparing a leading-order cross section with a search interpreted at higher order without a K-factor or a stated
  uncertainty (hep-theory owns that prescription).
