---
name: hep-theory
description: "Use when the deliverable is a theoretical or phenomenological result in particle, nuclear or astroparticle physics: conventions (units, constants, couplings, schemes, scales), derivations, amplitudes, cross sections, decay rates and widths, neutrino oscillations, nuclear decays, whether a process or Feynman diagram is allowed (selection rules), approximations and validity domains, theory uncertainties (scale envelopes, truncation, PDFs, model alternatives), event-generation physics, SMEFT conventions, consistency checks, predictions for comparing a model with an experiment's published data, and recasting a published analysis. Works with no experiment. Load it first even for a quick derivation, cross section or recast, and for topics outside v1 (lattice QCD and its global analyses, EFT global fits), where it says what it cannot cover. Not for: measurement design (hep-measurement), detector response (hep-detector), fits and limits (hep-statistics), code (hep-computing), manuscripts (hep-communication)."
---

# hep-theory: models, derivations, predictions

**Owns:** models, assumptions, conventions, derivations, predictions, event-generation physics, approximations, validity, theory-uncertainty prescriptions, consistency checks; definitions of units, constants and generic kinematics.
**Typical artifacts:** `theory-spec` (with a Markdown derivation record carrying a JSON header), `prediction` (JSON plus CSV for grids, explicit units).
**Never:** require experiment, detector, data or blinding fields; claim support for a domain because a tool ran; report numerical agreement as proof.

## Invariants

- Every result carries a derivation status from the core vocabulary: formal proof, analytic derivation, perturbative argument (state the order), asymptotic argument (state the limit), heuristic argument, numerical evidence, empirical observation, conjecture, not derived. Never upgrade a status when reusing a result.
- A conventions block travels with every derivation and prediction: unit system, whether hbar = c = 1, metric signature, coupling normalization, scheme, scales, energy variable, frame, angle definition, spin treatment, mass approximation.
- State the validity domain and what was neglected. Inapplicable fields are marked `not-applicable`, not left blank.
- Independent checks are listed as run or not run: units and dimensions, known limits, symmetries, normalization, analytic vs numerical integration with a stated tolerance and convergence study. Termination of a computation is not convergence.
- Benchmarks cite an authoritative source that was actually read, with its exact location.
- Scale envelopes, truncation estimates and model alternatives are distinct uncertainty objects and are never turned into Gaussians without a stated prescription.
- A request outside the validated theory profiles gets an explicit "no validated domain profile" notice, then general discipline.

## Workflow

1. Resolve context (stanza below). Load a theory-domain profile only if one is named or configured.
2. Write the theory spec: model, assumptions, conventions, order, parameters, scales, validity domain.
3. Derive (symbolically where useful), recording status and each check. Before SymPy work, run `python3 "<plugin root>/skills/hep-computing/scripts/find_python.py"` and use the interpreter it returns; if it reports `failed`, say so and never install anything without approval. Record that interpreter and its Python and SymPy versions with the derivation (`tools` and `environment` of a `computational-run`). Use hep-computing for heavy numerics.
4. Produce the prediction in the observable space it will be compared in, with uncertainties by type and allowed transformations.
5. For comparisons with data, state the dataset record and hand the inference to hep-statistics.

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

`<plugin root>` is the folder two levels above this `SKILL.md`.

1. Before any answer, even a quick one: use the profiles the user names, else those bound in `hep-research.project.json` at the project root; read a bound profile before answering about its experiment. Never infer an experiment or a model from vague wording; if a needed profile cannot be determined, ask which one.
2. Only when a profile is needed, read `<plugin root>/profiles/registry.json`, then that profile's `index.md`, then only the modules or dataset records the task needs. Never load an unrelated experiment or theory profile.
3. Local profiles live in the project (`local_profile_paths`), never in the plugin; check them with `python3 "<plugin root>/contracts/project.py" <project-dir>`. A bound profile in neither place, or at a local path known to be a companion's, is used only via the installed `<plugin>:profile` skill that names it, after its preflight, from its folder; never scan for companions. If none is installed, the preflight fails, or a non-public profile lacks `agent_policy` approval for this host (none has it yet), say it is unavailable, do other work; never answer its topics from memory.
4. No profile needed: use general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, global cosmic-ray propagation fits): say so, then apply this skill's general discipline.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never in the plugin; check them with `python3 "<plugin root>/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
6. Answer in the user's language; keep artifact fields, identifiers and file names in English.
<!-- END context-resolution -->

## Resources

| Request | Read or run |
|---|---|
| Derivation status, proof, approximation validity, checks | [mathematical reasoning and proof](references/mathematical-reasoning-and-proof.md) |
| NLO/NNLO predictions, scale envelopes, truncation | [higher-order predictions](references/higher-order-predictions.md) |
| PDF sets, LHAPDF, PDF uncertainty from members | [PDFs and LHAPDF](references/pdfs-and-lhapdf.md); `pdf_uncertainty.py` |
| SMEFT and EFT conventions, truncation | [SMEFT and EFT](references/smeft-and-eft.md); `eft_truncation.py` |
| Cosmic-ray propagation models, degeneracies (fits outside v1) | [cosmic-ray propagation](references/cosmic-ray-propagation.md) |
| Event-generation physics (ME order, shower, matching), event weights | [event generation](references/event-generation.md); `event_weights.py` |
| Recasting a published analysis (MadGraph, Rivet, Delphes, SModelS) | [recasting toolchain](references/recasting-toolchain.md) (documented, not run) |
| DIS invariants, beam relations, Jacobians, frames | [DIS kinematics](references/dis-kinematics.md); `dis_kinematics.py` |
| Constants, particle masses and lifetimes, nuclide masses and half-lives, unit conversions, decay Q values (with source and edition) | `physical_data.py` (`core/constants`: CODATA 2022, PDG 2026 subset, AME2020/NUBASE2020) |
| Phase space, decay widths, narrow width, Breit-Wigner | [amplitudes and widths](references/amplitudes-and-widths.md); `kinematics.py` (two-body, boosts, Mandelstam, thresholds, Dalitz, rapidity, width/lifetime/c tau) |
| Is a process or diagram allowed | [selection rules](references/selection-rules.md) |
| Schemes, running masses, regularization | [schemes](references/regularization-and-schemes.md) |
| HEPData table to a dataset record, or a record back to HEPData | `<plugin root>/adapters/hepdata/assets/hepdata_record.py`, `<plugin root>/adapters/hepdata/assets/hepdata_export.py` |
| Scientific-ML boundaries (surrogates of a theory) | `<plugin root>/skills/hep-ml/references/scientific-machine-learning.md` |
| Shipped theory-domain profiles | `<plugin root>/profiles/registry.json` |
| Outside v1 (lattice QCD, EFT global fits, global propagation fits) | say so; general discipline; full list: `<plugin root>/docs/routing-contract.md`, Scope of v1 |

Folder guide for people: [README.md](README.md).

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Fit, interval, limit, model comparison | hep-statistics | `prediction` + dataset record |
| Numerical convergence, symbolic/numeric cross-check code | hep-computing | `computational-run` |
| Folding into detector space | hep-detector then hep-statistics | `prediction` |
| Surrogate of an expensive prediction | hep-ml | `prediction` (validity domain) |
| Paper section or Feynman diagram rendering | hep-communication | `communication` |
