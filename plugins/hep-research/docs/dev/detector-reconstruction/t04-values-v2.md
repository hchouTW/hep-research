# T04: proposed values, version 2 (draft, nothing frozen)

> **Replaced by t04-values-v3.md. Kept as reviewed.** Second review verdict: freeze-ready after fixes.

Replaces t04-values-draft.md. Proposals for the user: K09, K12 and K16 freeze only on the user's word (R02), before any run of the recipe concerned. Until then, no pass or fail claim.

## What these gates can show

All inputs for now are synthetic. These are **closure gates**: did the recipe recover what the fixture generated, and are its uncertainties honest? A pass supports exactly this statement: *no discrepancy above the stated tolerance was found, on this fixture*. It does not show the code is correct, and it is not a performance claim, an instrument result or T3-C (R23). Every fixture shares something with its reconstruction: geometry in T07 and T08, the light model as well in T09. A shared model error cannot be seen here.

## Statistical design

Calculations: `<private>/evidence/t04-v2/`, scripts `t04_v2_a.py` (SHA-256 `2e0e1e4d118cb849…`) and `t04_v2_b.py` (`94dd93af40a56d08…`), seeded. Tests are treated as independent in the error budget.

| Item | Proposal |
| --- | --- |
| Statistical unit | The event. Quantities are binned in **truth**. Uncertainties come from a bootstrap over events, never from counting objects as independent |
| Effective events | `n_eff = n / DEFF`, with the design effect measured by that bootstrap. With one object per event, `n_eff = n` |
| Minimum | `n_eff` at least 10,000 in each required bin, on that gate's actual denominator. Below it the bin is inconclusive, never pass |
| Bins | 12 per fixture (4 x 3); edges fixed with each fixture before its first run |
| Location | 10 % trimmed mean of pulls: measured `se = 1.012/sqrt(n)` |
| Core width | `sigma_68`, half the central 68.27 % interval: measured `se = 0.953/sqrt(n)` |
| Pull population | All matched objects, wrong minima included. Objects with no result count against efficiency |
| Tolerance | 0.10 on location and on width |
| Pass rule | The one-sided 95 % bound lies inside the tolerance: `|estimate| <= 0.10 - 1.645 se`, per bin |
| Rates | One-sided 95 % Clopper-Pearson, computed from the actual denominator |

### Error budget

Every gate counts: mean, width and tail for each parameter, plus every rate.

| Workflow | Tests | Composition |
| --- | --- | --- |
| T07 | 696 | 12 bins x 2 fixtures x (8 parameters x 3 + 5 rates) |
| T08 | 132 | 12 bins x (3 parameters x 3 + 2 rates) |
| T09 | 276 | 12 bins x (7 parameters x 3 + 2 rates) |

Family target: at most 1 % false failure per workflow, using T07's largest count for all: per-test alpha 1.44e-5, z = 4.34.

### Why tolerance 0.10 and 10,000

A correct fit has small real biases, so the design needs slack: the largest true error that still meets the family target.

| Tolerance | Events per bin | Slack, location | Slack, width |
| --- | --- | --- | --- |
| 0.05 | 15,000 | 0.001 | 0.004 |
| 0.05 | 30,000 | 0.015 | 0.017 |
| 0.075 | 15,000 | 0.026 | 0.029 |
| 0.075 | 30,000 | 0.040 | 0.042 |
| **0.10** | **10,000** | **0.040** | **0.043** |
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
| Width 1.10 | 6.8 %, above the nominal 5 % |
| Bias 0.12 | 0.07 % |
| Width 1.12 | 0.13 % |

So: errors of 0.10 or more in any one bin are found about 93-95 % of the time or better; errors of 0.04 or less pass; between them the outcome is uncertain, and analytically a true error of 0.06 passes a bin 99 % of the time and 0.08 passes 63 %. That band is accepted, not hidden.

### Valid range of pull gates

Pulls assume the asymptotic regime. In a toy Poisson fit with Hessian uncertainty, a correct estimator has pull mean -0.051 at mu = 100, -0.036 at 200, -0.025 at 400. Mean bias must stay within the 0.04 slack, so outside a declared range a pull is **reported, not gated**:

- T09: gated at expected photon count at least 200 per event. This number comes from the toy; development samples check it for the real fit, before freezing.
- T07: `q/p` gated where `sigma(q/p)/|q/p|` is at most 0.1.
- T08: energy pulls gated above the threshold bin, where cell thresholds do not truncate the shower.

Bins outside the range stay listed as ungated, with the reason. They are never counted as passing.

## Common gates

| Gate | Proposal |
| --- | --- |
| Location | Pass rule above, on the trimmed mean |
| Width | Pass rule above, on `|sigma_68 - 1|` |
| Tail | `P(|pull| > 3)` upper bound at most 1 %: at most 83 of 10,000. Gaussian expectation 0.27 %. Unit-variance Student-t (5 d.o.f.) pulls fail the width gate (`sigma_68` = 0.86) |

## T07 tracking, vertexing (8 parameters: 5 track, 3 vertex)

| Item | Proposal |
| --- | --- |
| Bins | 4 true momentum x 3 occupancy |
| Matching | More than 50 % of a track's measurements from one particle; repeated at 70 % as a sensitivity check. A reasoned proposal, not from a source |
| Reconstructable | Truth particles leaving at least the recipe's minimum number of measurements |
| Efficiency reference | Clean fixture: analytic, from the fixture's definition. Noise fixture: truth-seeded run of the same recipe on the same events, used as a comparator only |
| Efficiency gate | Lower bound at least reference minus 0.01. Reference 1.0: observed at least 0.9917. A true loss of 0.01 passes a bin 4.6 % of the time; 0.015 passes below 1e-8 |
| Fakes, duplicates | Upper bound at most 1 %: at most 83 of 10,000 |
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
| Wrong minimum | Defined before running as a fit more than 5 sigma from truth. Upper bound at most 1 % |
| Topology mis-ID | Upper bound at most 1 % where the expected log-likelihood difference is at least 10; reported elsewhere. A proposal, to be checked on development samples |
| Fit parameters | Pull gates inside the valid range |

## Sample roles

Development samples use one seed range. Evaluation samples use another, generated only after freezing. Bootstrap by event removes correlation within events; shared conditions between samples are excluded by construction, since fixture conditions are fixed and separately generated. Tuning on an evaluation sample uses it up (A54).

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

T07: 240,000 effective events per evaluation sample set; T08 and T09: 120,000. Cost unknown until a recipe has run.

## Known limits

- The error budget assumes independent tests. Parameters of one track are correlated; for positive correlation this should be conservative, but it was not simulated.
- `sigma_68` was simulated above its nominal false-pass rate at width 1.10 (6.8 %).
- The valid-range numbers come from a one-parameter toy.
- Efficiency at a low reference: at reference 0.95 a correct bin fails 0.3 % of the time, about 3.7 % over 12 bins, above the family target. References below 0.98 need a larger sample or a wider margin.
