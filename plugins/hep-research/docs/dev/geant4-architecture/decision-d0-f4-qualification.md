# Decision record D0: how a detector-level Geant4 study qualifies as F4

Status: **open — awaiting the maintainer** (prepared 2026-10-24 by the agent; an agent-written record is not
approval). Programme: `geant4-program.md` (§P.7 item 1, B2.8; English translation `geant4-program.en.md`).
Baseline: `main` `5584927` (0.38.0, contracts 3.12.0). Labels: **Confirmed** (checked in code), **Inferred**,
**Unresolved**.

## Decision question

The detector system design loop accepts a Geant4 study as F4 evidence only when the study record has been re-issued
`validated-in-scope` by `check_geant4_study.py label --upgrade`. No detector-level study (momentum resolution, charge
confusion, shower containment) can reach that label today, because no reference benchmark covers detector-level
observables. Should the programme (a) add a qualification path so such studies can be upgraded, keeping one meaning of
`validated-in-scope` across the plugin, or (b) let `design.py` use un-upgraded F4 studies for screening only? And, in
either case, what uncertainty may an F4 evaluation carry?

The user chose direction (a) on 2026-10-24. This record asks the maintainer to approve or change that direction and to
decide the three sub-questions below.

## Why it matters

| Fact | Label | Evidence |
| --- | --- | --- |
| F4 needs a study re-issued `validated-in-scope`; otherwise the evaluation is unqualified | Confirmed | `contracts/design.py:1003-1005` |
| `label --upgrade` needs a passed reference benchmark whose scope contains the study's declared scope | Confirmed | `check_geant4_study.py:535-543`, `561-563`; `geant4-study-protocol.md` |
| Existing benchmarks cover MeV-scale energy loss and showers in thin slabs (particle, material, energy, thickness), not detector-level observables | Confirmed | `contracts/validate.py:351-367`; `geant4_benchmarks.py` |
| Several figures of merit are `capability.unavailable` below F4 (shower containment, tracking and selection efficiency, hadronic resolution, trigger efficiency, pileup robustness); charge-confusion and PID-rejection compliance need F4 | Confirmed | `contracts/rules/design_adequacy.json` |
| An F4 `estimate` whose uncertainty is below `min_relative_uncertainty` × value is treated as having no usable uncertainty (inconclusive). The minima are 0.2 (resolution), 0.3 (charge confusion), 0.1 (containment); F4's uncertainty is the study's statistical error (FID-01), typically 1–3 % | Confirmed | `design.py:1300-1309`, `1050-1054`; adequacy table (values labelled placeholders) |

So without a decision the plugin's highest simulated rung cannot produce a verdict for any detector-level figure of
merit, and with direction (a) alone it still cannot, because of the last row.

## Options

| Option | What changes | For | Against |
| --- | --- | --- | --- |
| **(a) Qualification path** (user's choice) | CV-B2: new benchmark classes and a per-class scope model in `label` and `validate.py`; four conditions below | One meaning of `validated-in-scope`; F4 stays evidence of physics validity | More contract work; covers only what a reference benchmark exists for (resolution core first) |
| (b) Screening-only F4 | `design.py`: an un-upgraded study may exclude a candidate but never approve one | Small change; useful at once for figures of merit whose screening fidelity is F4 (e.g. shower containment) | Two kinds of F4 evidence; a study with a wrong physics label could still steer screening |
| (c) Both | (a) for compliance, (b) as a complement where no reference exists (D0-d) | Covers shower containment while (a) is incomplete | Both costs |

## The qualification path (direction (a), as revised after the independent review)

A detector-level study is upgraded only when all four conditions hold, each matched by its own key:

| Condition | Matched by | State | Notes |
| --- | --- | --- | --- |
| 1. Material definition: composition and density of every material from a recorded independent source, and a geantino scan reproducing the candidate's declared X/X₀ within tolerance | materials of the realized geometry | Proposed (B2.8) | Replaces "materials inside passed A1 benchmarks", which J15 could never meet (Pb and PVT have no benchmark; J14 uses `Si_study`, not `G4_Si`; A1 scopes are MeV-scale) — Confirmed by the review |
| 2. Field: the analytic-helix verification passed | field-configuration hash | Proposed (B1, B2.8) | — |
| 3. Reconstruction: `reco-closure` passed | reco-spec hash | Proposed (B2.7) | — |
| 4. Tracking reference: multiple-scattering core width in an isolated Si slab against Lynch–Dahl (F = 98 %), scope material, thickness, rigidity, species | benchmark scope | Proposed (B2.7) | Qualifies `momentum-resolution-core` only; point resolution stays a declared input that no benchmark validates (at 100 GV it dominates the core). Lynch–Dahl's published accuracy: Unresolved |

**Scope model** (part of CV-B2). Today `label` adds a gap for every evidence benchmark that does not contain the whole
declared scope, and `_study_upgrade` needs only one benchmark to contain it. The path needs a conjunction over
benchmark classes, each covering its own keys, with field and reco matched by hash and external benchmark records
entering through `--reference-record` and re-derived by `contracts/dependencies.py`. Existing (J14-type) studies must
keep their current behaviour (Confirmed requirement; implementation Unresolved).

## Sub-decisions for the maintainer

| Id | Question | Recommendation |
| --- | --- | --- |
| **D0-a** | Approve direction (a)? | Approve **conditionally** on the revised B2.8 (scope model, material-definition condition, charge confusion only with a tail benchmark) and on D0-c |
| **D0-b** | How does charge confusion qualify? A core-width benchmark does not validate the tails (single large-angle scattering, nuclear interactions, mis-association) that drive it away from the MDR | Only with a **tail benchmark** (fraction of scattering angles beyond ≈3θ₀ against single-scattering/Molière theory or published data); until one exists, charge confusion stays unqualified |
| **D0-c** | What uncertainty may an F4 evaluation carry? With FID-01 every upgraded F4 `estimate` is inconclusive (`uncertainty.missing`) | **(a) change FID-01 in CV-B2**: F4 uncertainty = statistical ⊕ tail-replica spread (≥ 20 reconstruction replicas with independent misalignment draws) ⊕ model-envelope half-width. A statistical-only error understates F4's real uncertainty. Alternatively the maintainer revises the F4 minima (placeholders today), or both. Either way, require an end-to-end test that reaches a decisive verdict row, not only the inconclusive one |
| **D0-d** | Add screening-only F4 (option (b)) as a complement for figures of merit with no reference (shower containment)? | Offer, not chosen: decide after D0-a and D0-c |

## What the decision unblocks

| Approved | Unblocks |
| --- | --- |
| D0-a and D0-c | B2.8 rules take effect; B3 (J15 as a design project) produces decisive F4 resolution evaluations; C2's F4 confirmation of search finalists |
| D0-b | F4 charge-confusion evaluations (still needing the data-validation and rigidity-scale-offset upstreams the adequacy table requires) |
| D0-d | Screening of candidates on shower containment at F4 |

Until D0 is approved, B2 may merge with the qualification rules present but inactive (gate G-D0), B3 and C2's
confirmation do not start, and confirmation studies stay `unvalidated`.

## Related problems found on `main` (fixed in A1, reported here for awareness)

1. `evaluate_design.py f4 --label-spec` never passes run records to `label --upgrade`, so that path always refuses
   (Confirmed: `evaluate_design.py:503-506`; `check_geant4_study.py:544-569`); `label` also rebuilds the record
   without `results` and tail sources (`check_geant4_study.py:584-617`). A1.17 and B2.6 fix this.
2. The convergence gate takes the two finest values among the supplied run summaries, so a missing finest run lets it
   pass on coarser ones (Confirmed: `check_geant4_study.py:341-348`; the protocol documents it). A1.16 fixes it (D11).

## Decision

_To be filled in by the maintainer: D0-a, D0-b, D0-c, D0-d, date, and any conditions._
