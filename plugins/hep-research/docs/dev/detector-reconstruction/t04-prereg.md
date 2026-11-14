# T04: quality and resource preregistration

State: frozen at Freeze A with t04-values-v4.md; K09 and K16 values are in that document, except the `element_sim` spec, which is frozen before T15b. K12 targets are not frozen here: they are drafted after P2 from recorded costs (U10), and until then no speed or cost claim is made. This file fixes the structure, so that values can be frozen before any result exists. Thresholds are in t04-values-v4.md, frozen at Freeze A by SHA-256. Entries marked `<freeze>` are the user's (R02). None may be set after seeing results (Section 1.3 item 8), with these exceptions only, each bounded by its rule in t04-values-v4.md, section 2.2: recipe, configuration and budget hashes, and `r_dev`.

## Per workflow

| Field | Tracking, vertexing | Calorimetry | Photon likelihood |
| --- | --- | --- | --- |
| Primary quantities | Efficiency, fake rate, duplicate rate, charge sign, track-state residual core and tails; vertex finding, assignment, position | Named energy kind: scale, core, tails; containment (edge control), linearity (centre per energy bin); merge rate gated; split rate reported | Vertex, time, direction, visible energy; fit failure, wrong minimum, topology mis-ID |
| Bins | Momentum, occupancy (bins); angle (pooled slices). Material: not tested, obligation open | Energy, overlap. Particle type, angle: not tested, obligation open | Photon count, position. Medium: not tested, obligation open |
| Denominators (11.3.1) | Fiducial truth objects for efficiency; reconstructed objects for fakes; resolution on matches only, reported with efficiency; duplicates on the reconstructed convention | Same definition of selection as the response; full efficiency reported | Full population, with wrong-minimum rate reported beside resolution |
| Matching | t04-values-v4.md, section 7 | t04-values-v4.md, section 7 | t04-values-v4.md, section 7 |
| Failure classes (11.4) | Seed or finding, fit, ambiguity, branch or resource truncation | Clustering, leakage, threshold, double counting | Wrong minimum, reversed track, multiple events, model mismatch |
| Required negative case | Wrong hits, branch explosion, seed failure | Digital read as analog; deposited energy used as incident | Live-unhit against dead channels; first-time readout under a single-photon density |
| Tolerances, directions | t04-values-v4.md | t04-values-v4.md | t04-values-v4.md |

## Rules for every workflow

- **Sample roles:** tuning, calibration, selection and confirmation are separate, grouped by run, conditions source, noise realization and fixture derivation (K08). For fixtures, t04-values-v4.md section 3.1 applies.
- **Sample size:** set from the claim to be supported, with hep-statistics. No universal number exists. Too few events in a required bin gives inconclusive, never pass.
- **Results:** pass, fail, inconclusive, not-applicable.
- **Weighted data:** an explicit statistical method; binomial only for unweighted independent trials with negligible background.
- **Budgets:** Algorithmic budgets frozen by hash at Freeze B; wall time, memory and retries at each job's approval (K10). Hitting a limit is recorded; truncated candidates are marked as such.
- **Reproducibility:** each recipe declares byte, numerical or statistical (Section 14.1).

## Critical false success

An observed case blocks the capability named. Zero observations do not establish zero risk.

| False success | Blocked capability |
| --- | --- |
| Reports a backend run that did not happen, or a fabricated command | Every execution claim for that recipe |
| Truth reaches a data-side recipe | That recipe |
| Refit of a known hit set reported as finding | Tracking workflow |
| Absent data reported as zero | Count and threshold delivery |
| Unidentifiable quantity reported with precision | The affected BP |
| Failed or unroutable observations dropped from a denominator | Selection policy and its quality claim |

## AI task stratification

| Group | Content | Minimum coverage |
| --- | --- | --- |
| Executable | Each required recipe, genuinely run | One or more per recipe |
| Insufficient information | Alternative constraints, missing retention | Each BP |
| Missing dependency, out of domain | No backend, unknown format | Each F-ID and required variant, routing or feasibility |
| Runtime or quality failure | Injected failures | Representative A01-A60 counterexamples |

Distinct tasks are the unit; counts are designed in K11 from the claim, not from "30 tasks x 3 repeats" (Section 14.3). The holdout is not established (R22).

## Resources

Stage cost measurement follows K12: initialization, I/O, conditions, conversion, compute, checks, failed trials; cold and warm separate. Targets are `<freeze>`. Until then no speed or cost claim is made.
