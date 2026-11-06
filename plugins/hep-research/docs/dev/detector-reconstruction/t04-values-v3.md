# T04: proposed values, version 3 (draft, nothing frozen)

Replaces t04-values-v2.md, after the second review (t04-review.md). Proposals for the user: K09, K12 and K16 freeze only on the user's word (R02). Until then, no pass or fail claim.

## Two-step freeze

- **Freeze A, before any development run:** this document's rules, tolerances and fixture definitions.
- **Freeze B, after development samples, before any evaluation sample exists:** bin edges, valid ranges, and the noise-fixture fake ceiling. Only the items listed here may be set at Freeze B, each by its stated rule, never to make a result pass.

## What these gates can show

All inputs for now are synthetic. These are **closure gates**: did the recipe recover what the fixture generated, and are its uncertainties honest? A pass supports exactly this statement: *no discrepancy above the stated tolerance was found, on this fixture*. It does not show the code is correct, and it is not a performance claim, an instrument result or T3-C (R23). Every fixture shares something with its reconstruction: geometry in T07 and T08, the light model as well in T09. A shared model error cannot be seen here.

## Statistical design

Calculations: `<private>/evidence/t04-v2/` and `<private>/evidence/t04-v3/` (`t04_v3.py`, SHA-256 `0bc99da430eb22be…`), scripts `t04_v2_a.py` (SHA-256 `2e0e1e4d118cb849…`) and `t04_v2_b.py` (`94dd93af40a56d08…`), seeded. The error budget is a union bound, so it needs no independence between tests.

| Item | Proposal |
| --- | --- |
| Statistical unit | The event. Every uncertainty comes from a bootstrap over events, or the effective count below, never from counting objects as independent |
| Bins | 12 per fixture (4 x 3). Truth objects bin in truth. Fakes have no truth, so they bin in reconstructed quantities. Vertices bin in event-level quantities. Edges set at Freeze B |
| Generation | Stratified: 12,000 events generated in each bin, a 20 % margin, so bins do not fall short at random |
| Robust centre | 10 % trimmed mean of pulls. It is not the mean: the mean and RMS are always reported beside it. Design `se` about `1.03/sqrt(n)` |
| Core width | `sigma_68`, half the central 68.27 % interval. Design `se` about `0.953/sqrt(n)` |
| `se` used in a gate | The event-bootstrap value for that statistic in that bin. The formulas above are for design only |
| Precision minimum | A bin is inconclusive, never pass, if its bootstrap `se` exceeds 0.0129 (centre) or 0.0119 (width), which is 25 % above the design value. This replaces any count-based minimum, because a design effect differs between statistics |
| Pull population | All matched objects, wrong minima included. Objects with no result count in a gated failure rate |
| Tolerance | 0.10 on centre and on width |
| Pass rule | The one-sided 95 % bound lies inside the tolerance: `|estimate| <= 0.10 - 1.645 se`, per bin |
| Rates | Clopper-Pearson on effective counts: `DEFF` from the between-event variance of that rate, floor 1, `n_eff = n/DEFF`, `k_eff = k n_eff/n`. With zero events observed, `1 - 0.05^(1/N_events)` on events |
| Paired comparisons | Bootstrap over events of the paired difference, one-sided 95 % |

The effective-count rule was simulated at 10 objects per event and a true rate equal to the limit: it passes 4.2-5.7 % of the time at intra-event correlation 0 to 0.5. Plain Clopper-Pearson on objects passes 4.3-24.7 %.

### Error budget

Every gate counts: mean, width and tail for each parameter, plus every rate.

| Workflow | Tests | Composition |
| --- | --- | --- |
| T07 | 864 | 12 bins x 2 fixtures x (8 parameters x 3 + 6 rates + `q/p` per charge, 2 x 3) |
| T08 | 132 | 12 bins x (3 parameters x 3 + 2 rates) |
| T09 | 288 | 12 bins x (7 parameters x 3 + 3 rates) |

Family target: at most 1 % false failure per workflow, using T07's largest count for all: per-test alpha 1.16e-5, z = 4.38.

### Why tolerance 0.10 and 10,000

A correct fit has small real biases, so the design needs slack: the largest true error that still meets the family target. Rows other than the proposal were computed with the earlier `se` and test count and differ slightly.

| Tolerance | Events per bin | Slack, location | Slack, width |
| --- | --- | --- | --- |
| 0.05 | 15,000 | 0.001 | 0.004 |
| 0.05 | 30,000 | 0.015 | 0.017 |
| 0.075 | 15,000 | 0.026 | 0.029 |
| 0.075 | 30,000 | 0.040 | 0.042 |
| **0.10** | **10,000** | **0.038** | **0.043** |
| 0.10 | 30,000 | 0.065 | 0.067 |

The user may prefer 0.075 with 30,000 per bin: three times the events for a tighter gate. Its cost is unknown until a recipe has run.

### Behaviour of one bin, directly simulated

3,000 trials, n = 10,000, Gaussian pulls unless stated. A single bad bin is what these numbers describe.

| True state | Passes |
| --- | --- |
| Correct | 100 % |
| Bias 0.04, or width 1.04 | 100 % |
| 1 % of entries at pull 20 | 100 % core gates; the tail gate judges them |
| Bias 0.10 | 5.1 % |
| Width 1.10 | 6.8 % with the design `se`; the second review measured 5.0 % with an event-bootstrap `se`, which is what the gate uses |
| Bias 0.12 | 0.07 % |
| Width 1.12 | 0.13 % |

So: errors of 0.10 or more in any one bin are found about 93-95 % of the time or better; errors of 0.04 or less pass; between them the outcome is uncertain, and analytically a true error of 0.06 passes a bin 99 % of the time and 0.08 passes 63 %. That band is accepted, not hidden.

### Valid range of pull gates

Pulls assume the asymptotic regime. In a toy Poisson fit with Hessian uncertainty, a correct estimator has pull mean -0.051 at mu = 100, -0.036 at 200, -0.025 at 400. Mean bias must stay within the 0.04 slack, so outside a declared range a pull is **reported, not gated**. Ranges are set at Freeze B:

- T09: gated at expected photon count at least 200 per event. This number comes from the toy (the trimmed centre there is -0.022); development samples check it for the real fit.
- T07: `q/p` gated where `sigma(q/p)/|q/p|` is at most 0.1.
- T08: energy pulls gated above the threshold bin, where cell thresholds do not truncate the shower.

Bins outside the range stay listed as ungated, with the reason. They are never counted as passing.

## Common gates

| Gate | Proposal |
| --- | --- |
| Location | Pass rule above, on the trimmed mean |
| Width | Pass rule above, on `|sigma_68 - 1|` |
| Tail | `P(|pull| > 3)` upper bound at most 1 %: at most 83 of 10,000 for independent objects. Gaussian expectation 0.27 %, so this leaves room for about 0.55 % of other entries. Unit-variance Student-t (5 d.o.f.) pulls fail the width gate (`sigma_68` = 0.86) |
| Reported beside every gate | Mean and RMS of pulls. A skewed pull distribution, or 0.5 % of entries at pull 20, can pass these gates; the mean and RMS show it, and a reader must not treat a pass as Gaussian behaviour |

## T07 tracking, vertexing (8 parameters: 5 track, 3 vertex)

| Item | Proposal |
| --- | --- |
| Bins | 4 true momentum x 3 occupancy. `q/p` pulls are also gated per charge sign, because a charge-dependent bias of plus or minus 0.40 cancels in the mixed sample and passed the width gate 66 % of the time |
| One-dimensional diagnostics | Angle, material and particle type, reported per fixture. Required by t04-prereg.md, not gated here, because these fixtures do not vary them enough |
| Matching | More than 50 % of a track's measurements from one particle; repeated at 70 % as a sensitivity check. A reasoned proposal, not from a source |
| Reconstructable | Truth particles leaving at least the recipe's minimum number of measurements |
| Efficiency reference | Clean fixture: analytic, from the fixture's definition. Noise fixture: truth-seeded run of the same recipe on the same events, a comparator only. It carries its own sampling noise, so the comparison is paired |
| Efficiency gate | Lower bound of (reconstructed minus reference) at least -0.01. Clean: Clopper-Pearson on effective counts. Noise: paired bootstrap. Simulated at reference 0.98: a true loss of 0.01 passes 6.1 %, 0.015 passes 0 of 2,000, 0.005 passes all |
| Fakes, duplicates | Clean fixture: upper bound at most 1 %. Noise fixture: a correct recipe can make fakes from noise, so the ceiling is set at Freeze B as the development-sample rate plus 0.01 |
| Vertex finding | As efficiency, for vertices with at least the fixture's minimum track count |
| Vertex assignment | Wrong-assignment upper bound at most 1 %, for vertices separated by at least 5 resolution units. Closer ones reported |
| Charge sign | Upper bound at most 1 % where the `q/p` pull is gated; reported elsewhere |

No fixed efficiency floor applies: the gate measures loss against a reference, so a fixture that limits efficiency does not fail correct code.

## T08 calorimetry (3 parameters: energy, x, y)

| Item | Proposal |
| --- | --- |
| Bins | 4 true energy x 3 separation |
| Matching | Cluster matches the shower giving it more than 50 % of its energy; repeated at 70 % |
| Energy | Pull gates, against the fixture's known contained energy |
| Conservation | Clustered plus unclustered energy equals the input, within 1e-9 relative. Sharing fractions sum to 1 for clustered cells and 0 for unclustered |
| Efficiency | Against the analytic reference, as T07 |
| Merge | Upper bound at most 1 % for showers separated by at least 3 fixture shower widths; closer ones reported |
| Split | Reported |

## T09 photon likelihood (7 parameters)

| Item | Proposal |
| --- | --- |
| Bins | 4 true photon count x 3 radial position |
| Likelihood check | Coded likelihood agrees with an independently written numerical evaluation, within 1e-9. A sum-to-1 test alone could pass by construction |
| Wrong minimum | Defined before running as a fit more than 5 sigma from truth. Upper bound at most 0.5 %: at most 38 of 10,000, consistent with the tail gate |
| Fit failure | Fits with no result, over the full population of generated events: upper bound at most 1 %. T09 has no efficiency gate, so without this failed fits would vanish from the record |
| Topology mis-ID | Upper bound at most 1 % where the expected log-likelihood difference is at least 10; reported elsewhere. A proposal, to be checked on development samples |
| Fit parameters | Pull gates inside the valid range |

## Sample roles

Development samples use one seed range. Evaluation samples use another, generated only after Freeze B. A bootstrap by event accounts for correlation within events. Development and evaluation samples still share the fixture's geometry and conditions, so they are not independent in the sense of Section 11.3.2, and these results support no claim beyond the fixture. Tuning on an evaluation sample uses it up (A54).

## K12: performance

**No targets yet.** With no recorded cost, a target would be a guess. T07-T09 record cost per stage, cold and warm; targets are drafted from those records after P2.

## K16: selection, for T15b

| Item | Proposal |
| --- | --- |
| Hard gates | All T07 closure gates on the shared events and stage |
| Candidates | `simreco-pr-a`: code defaults, window 1 mm, `chi2_per_ndof_cut` 50, minimum 4 hits. `simreco-pr-b`: window 0.5 mm, otherwise the same |
| Objective | Lowest total CPU time per event subject to the gates, failed events and I/O included |
| Comparison | Paired events, one population and denominator |
| Tie rule | If the two-sided 95 % bootstrap interval of the mean paired cost difference, resampling events, includes 0, keep `simreco-pr-a`, called a "qualified default choice" |
| None passes | "No qualified candidate"; gates are not lowered |

## K10 budgets

Wall time, memory and retries become Slurm requests, set at each job's approval. `CAI-` tolerances are set from fixture statistics and recorded before each run (R37).

## Sample sizes

T07: 288,000 generated events per evaluation sample set (24 bins x 12,000); T08 and T09: 144,000. Cost unknown until a recipe has run.

## Known limits

- The union-bound budget covers false failures for true errors within the slack. Above it, failure is the intended outcome.
- Rates have no slack calculation of their own: the 1 % family target for them assumes true rates well below their limits. At a true rate of half the limit and intra-event correlation 0.5, a bin passed only 74 % of the time, so high-occupancy bins with strong correlation may fail correct code.
- Skewed pulls can pass or fail these gates for reasons other than bias; the reported mean and RMS exist for this.
- The valid-range numbers come from a one-parameter toy, until development samples check them.
- Efficiency at a low reference: at reference 0.95 a correct bin fails 0.3 % of the time, about 3.7 % over 12 bins, above the family target. References below 0.98 need more events or a wider margin.
- Split rate is reported only, with no gate: its correct value depends on the fixture's splitting definition, and no closure reference exists for it.
