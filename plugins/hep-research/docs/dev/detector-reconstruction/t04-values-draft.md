# T04: proposed values (draft, nothing frozen)

> **Do not freeze. Review verdict: redesign needed (t04-review.md).** Four blockers, confirmed by recomputation. In particular, "caught 100 %" below holds only when all 12 bins shift, and the 1 % family rate covers one parameter. Kept as reviewed, for the record. Replaced by t04-values-v2.md.

Proposals for the user. K09, K12 and K16 freeze only on the user's word (R02), and before any run of the recipe concerned. Until then, no pass or fail claim.

## What these gates can mean

All inputs for now are synthetic, so absolute numbers such as a resolution in micrometres would describe the fixture and nothing else. These gates are **closure gates**: did the recipe recover what the fixture generated, and is its uncertainty honest? Passing supports "the code is correct for this fixture". It is not a performance claim, not an instrument result, and not T3-C (R23). Results are labelled synthetic.

## Shared statistical design

Basis: one-sided 95 % Clopper-Pearson bounds, `1 - 0.05^(1/N)` for zero observed events (`hep-statistics` core guide), and Sidak control across bins. Script `<private>/evidence/t04-oc/t04_oc.py`, SHA-256 `39a62e5f42a999b0b0b768a1c3b967e7e8857a681eb435e0e6fb3d526be009c6`, seeded. These are design calculations, with Gaussian assumptions unless stated; hep-statistics should review them before freezing.

| Item | Proposal | Reason |
| --- | --- | --- |
| Bins per workflow | 12 (4 x 3) | Enough to see a dependence; sets the multiplicity below. Edges are fixed with each fixture, before its first run |
| Events per bin | 5,000; 60,000 per sample | See below |
| Family false-failure target | 1 % over 24 pull tests | Per-test alpha 4.19e-4, z = 3.53 |

Operating characteristics for pull mean and width gates of 0.05, 12 bins:

| Events per bin | Correct estimator fails | Width 1.06 caught | Bias 0.06 caught |
| --- | --- | --- | --- |
| 2,500 | 14.5 % | 100 % | 100 % |
| **5,000** | **0.3 %** | **100 %** | **100 %** |
| 10,000 | 0 of 4,000 trials | 100 % | 100 % |

A correct estimator with unit-variance Student-t (5 d.o.f.) pulls failed these two gates in 10 % of 200 trials, so they do not reliably find heavy tails. The tail gate does: such a bin passes it with probability 0.3 %, and a Gaussian bin passes with probability above 99.9 %.

## Common gates

| Gate | Proposal | Applies to |
| --- | --- | --- |
| Pull mean | `|mean| <= 0.05` in every bin | Each fitted parameter with a reported uncertainty |
| Pull width | `|sd - 1| <= 0.05` in every bin | Same |
| Pull tails | Upper bound on `P(|pull| > 3)` at most 1 %: at most 38 of 5,000 | Same |
| Too few events in a bin | Inconclusive, never pass | All |

Pulls use the correct residual and covariance (`performance-metrics-and-residual-diagnostics.md`).

## T07 tracking, vertexing

| Item | Proposal | Reason |
| --- | --- | --- |
| Bins | 4 momentum x 3 occupancy | Section 11.4 panel |
| Matching | One track matches a particle when more than 50 % of its measurements come from it; repeated at 50 % and 70 % as the sensitivity check | Above 50 %, only one particle can match, which makes the rule unambiguous. Not taken from a source: a proposal |
| Efficiency, clean fixture | Lower bound at least 0.99 in every bin: observed at least 0.9924 | True 0.995 passes all 12 bins with probability 93.5 % |
| Efficiency, noise fixture | Lower bound at least 0.95: observed at least 0.9552 | True 0.9625 passes all 12 with probability 95.7 % |
| Fakes, duplicates | Upper bound at most 1 %: at most 38 of 5,000 per bin | |
| Charge sign | Measured and reported, no gate until a momentum range is fixed | Depends on the fixture's curvature resolution |
| Vertex | Pull gates on position; finding efficiency as above | |

If a fixture's true efficiency is below these values, the gate fails correctly. The value is not lowered afterwards.

## T08 calorimetry

| Item | Proposal | Reason |
| --- | --- | --- |
| Bins | 4 energy x 3 overlap | Section 11.4 panel |
| Matching | A cluster matches the shower giving it more than 50 % of its energy; repeated at 50 % and 70 % | As T07 |
| Energy closure | Mean of `(E_reco - E_gen)/sigma_E` within 0.05, using the fixture's known contained energy | In resolution units, so it needs no absolute target |
| Double counting | Sharing fractions sum to 1 per cell, within 1e-12 | Deterministic; a failure blocks the recipe |
| Isolated shower efficiency | Lower bound at least 0.99 | As T07 |
| Split, merge | Measured and reported per separation bin; no gate until K09 sets a separation | Depends on the fixture's shower size |

## T09 photon likelihood

| Item | Proposal | Reason |
| --- | --- | --- |
| Bins | 4 photon count x 3 radial position | Section 11.4 panel; boundary bias is the reference's named failure |
| Probabilities | Hit and no-hit sum to 1 per channel, within 1e-12 | Deterministic |
| Fit parameters | Common pull gates on vertex, time, direction, energy | |
| Wrong minimum | Upper bound at most 1 % per bin: at most 38 of 5,000 | Reported beside resolution |
| Low photon count | That bin may be inconclusive; zero failures in few events is not a pass | Section 11.3.2 |

This fixture shares its model with the fit, so passing tests the code alone (Section 11.1).

## Sample roles

Development samples use one seed range. Evaluation samples use another, generated only after freezing. Grouped by seed, so no noise realization is shared. Tuning on an evaluation sample uses it up (A54).

## K12: performance

**Proposal: no targets yet.** With no recorded cost, a target would be a guess. T07-T09 record cost per stage, cold and warm; targets are drafted from those records after P2. No speed claim until then.

## K16: selection, for T15b

| Item | Proposal |
| --- | --- |
| Hard gates | All T07 closure gates, on the same events at the same stage |
| Candidates | `simreco-pr-a`: code defaults, window 1 mm, `chi2_per_ndof_cut` 50, minimum 4 hits. `simreco-pr-b`: window 0.5 mm, other values the same |
| Objective | Lowest total CPU time per event, subject to the gates, including failed events and I/O |
| Comparison | Paired events, one population and denominator |
| Tie rule | If the paired cost difference is not resolved, keep `simreco-pr-a`, called a "qualified default choice" |
| None passes | "No qualified candidate"; gates are not lowered |

## K09 budgets

Wall time, memory and retries become Slurm requests, so they are set at each job's approval (R02). Tolerances in `CAI-` items are set from fixture statistics and recorded before the run (R37); they do not wait for K09.

## Not settled here

- Bin edges, which depend on each fixture.
- hep-statistics review of this design.
